#!/usr/bin/env python3
"""Offline validator for CP34 current-slot survey plans."""

import hashlib
import io
import json
import math
import os
import re
import stat
import sys
import wave
from pathlib import Path, PurePosixPath


EXPECTED_SERIAL = "AB7C22200355"
EXPECTED_CANDIDATES = (
    {"label": "ch1-slot1", "channel": 1, "numeric_slot": 0, "physical_input": 1},
    {"label": "ch2-slot1", "channel": 2, "numeric_slot": 2, "physical_input": 2},
)
EXPECTED_PROHIBITED = frozenset({
    "slot_selection", "mapped_write", "device_output_playback",
    "io24_monitoring", "wine", "network", "firmware", "reset", "dfu",
    "install", "stage", "usb_detach", "guessed_packet",
})

_EVIDENCE_PREFIX = ".superpowers/sdd/2026-08-28-cp34-preset-effect-control/runs/"
_STIMULUS_HASH = re.compile(r"[0-9a-f]{64}\Z")

RATE = 48000
CHANNELS = 6
MIN_INPUT_PEAK_DB = -36.0
MAX_INPUT_PEAK_DB = -12.0
MAX_ANY_PEAK_DB = -3.0
MIN_MAP_CORRELATION = 0.80
MAX_LAG_SAMPLES = 12000
MIX_CHANNELS = (3, 4)
_IMPULSE_OFFSETS = (0, 33600, 67200, 100800, 134400)
_IMPULSE_TOLERANCE_SAMPLES = 96
_INT32_FULL_SCALE = (1 << 31) - 1
_WINDOW_RADIUS = 8

STABLE_STATE_KEYS = (
    "selected_slot", "processing_channel_1", "processing_channel_2",
    "phantom_1", "phantom_2", "gain_1", "gain_2", "headphone",
    "main", "monitor_blend",
)
EXPECTED_EVENTS = (
    ("P0", "state_read"), ("M0", "audio_capture"),
    ("S1", "audio_capture"), ("T1", "manual_preset_toggle"),
    ("P1", "state_read"), ("S2", "audio_capture"),
    ("S3", "audio_capture"), ("T2", "manual_preset_toggle"),
    ("P2", "state_read"), ("S4", "audio_capture"),
)
JA_ST_LIMITATION = "JaSt cannot prove every internal DSP byte."
_MANIFEST_ROW = re.compile(r"([0-9a-f]{64})  ([^\r\n]+)\Z")
_EXCLUDED_INPUT_PATHS = frozenset({
    "EVIDENCE-SHA256SUMS", "RESTORATION.json", "REPORT.md", "SHA256SUMS",
})
_AB_TOP_LEVEL_FIELDS = frozenset({
    "schema", "status", "classification", "reverb_like_observed",
    "candidate", "model_identity", "title_verified", "live_ready",
    "restoration_verified", "audible_attested", "expected_delay_s",
    "dry", "active", "reasons",
})
_AB_BASE_METRIC_FIELDS = frozenset({
    "path", "sha256", "impulses", "arrival_offsets_samples", "peak",
    "rms_db", "echo_ratio_db", "late_ratio_db",
})
_AB_ACTIVE_METRIC_FIELDS = _AB_BASE_METRIC_FIELDS | frozenset({
    "echo_delta_db", "late_delta_db",
})


def _has_exact_s32_pcm_semantics(raw):
    """Check the RIFF fmt declaration, including extensible valid-bit depth."""
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        return False
    offset = 12
    while offset + 8 <= len(raw):
        chunk_id = raw[offset:offset + 4]
        chunk_size = int.from_bytes(raw[offset + 4:offset + 8], "little")
        chunk_end = offset + 8 + chunk_size
        if chunk_end > len(raw):
            return False
        if chunk_id == b"fmt ":
            if chunk_size < 16:
                return False
            format_tag = int.from_bytes(raw[offset + 8:offset + 10], "little")
            bits_per_sample = int.from_bytes(raw[offset + 22:offset + 24], "little")
            if format_tag == 1:
                return bits_per_sample == 32
            if format_tag != 0xFFFE or chunk_size < 40:
                return False
            valid_bits = int.from_bytes(raw[offset + 26:offset + 28], "little")
            pcm_subformat = bytes.fromhex("0100000000001000800000aa00389b71")
            return bits_per_sample == 32 and valid_bits == 32 and raw[offset + 32:offset + 48] == pcm_subformat
        offset = chunk_end + (chunk_size & 1)
    return False


def _read_six_channel_wav(raw):
    """Return six signed-32-bit PCM channels, rejecting other WAV shapes."""
    try:
        with wave.open(io.BytesIO(raw), "rb") as source:
            if (source.getcomptype() != "NONE" or source.getsampwidth() != 4
                    or source.getframerate() != RATE or source.getnchannels() != CHANNELS
                    or not _has_exact_s32_pcm_semantics(raw)):
                raise ValueError("wav_must_be_six_channel_s32_le_48khz_pcm")
            frame_count = source.getnframes()
            payload = source.readframes(frame_count)
    except (OSError, EOFError, wave.Error) as exc:
        raise ValueError("wav_unreadable_or_invalid") from exc
    if len(payload) != frame_count * CHANNELS * 4:
        raise ValueError("wav_payload_length_invalid")
    samples = tuple(
        int.from_bytes(payload[offset:offset + 4], "little", signed=True)
        for offset in range(0, len(payload), 4)
    )
    return tuple(samples[channel::CHANNELS] for channel in range(CHANNELS))


def _normalized_impulse_correlation(raw_input, candidate, arrivals, lag):
    """Correlate 17-sample arrival windows at one non-negative candidate lag."""
    dot = input_energy = candidate_energy = 0
    for arrival in arrivals:
        for offset in range(-_WINDOW_RADIUS, _WINDOW_RADIUS + 1):
            input_index = arrival + offset
            candidate_index = arrival + lag + offset
            source_sample = raw_input[input_index] if 0 <= input_index < len(raw_input) else 0
            candidate_sample = candidate[candidate_index] if 0 <= candidate_index < len(candidate) else 0
            dot += source_sample * candidate_sample
            input_energy += source_sample * source_sample
            candidate_energy += candidate_sample * candidate_sample
    if not input_energy or not candidate_energy:
        return 0.0
    return abs(dot) / math.sqrt(input_energy * candidate_energy)


def _dbfs(peak):
    return None if not peak else 20.0 * math.log10(peak / _INT32_FULL_SCALE)


def _arrival_samples(raw_input):
    peak = max((abs(sample) for sample in raw_input), default=0)
    if not peak:
        return []
    threshold = peak // 2
    arrivals = []
    index = 0
    while index < len(raw_input):
        if abs(raw_input[index]) < threshold:
            index += 1
            continue
        start = index
        while index < len(raw_input) and abs(raw_input[index]) >= threshold:
            index += 1
        arrivals.append(max(range(start, index), key=lambda item: abs(raw_input[item])))
    return arrivals


def _unavailable(raw_sha256, input_channel, reason, *, input_metrics=None, scores=None):
    return {
        "schema": "cp34-current-slot-map-v1",
        "status": "UNAVAILABLE",
        "raw_sha256": raw_sha256,
        "input_metrics": input_metrics or {"input_channel": input_channel, "peak_dbfs": None, "arrivals": []},
        "scores": scores or {str(channel): 0.0 for channel in MIX_CHANNELS},
        "frozen_mix_channel": None,
        "reasons": [reason],
    }


def analyze_map(path: str, input_channel: int) -> dict:
    """Map a recorded input to the preplanned Mix A candidates, offline only."""
    try:
        raw = open(path, "rb").read()
    except (OSError, TypeError, ValueError):
        raw = b""
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    if input_channel not in (1, 2):
        return _unavailable(raw_sha256, input_channel, "input_channel_must_be_1_or_2")
    try:
        audio = _read_six_channel_wav(raw)
    except (TypeError, ValueError):
        return _unavailable(raw_sha256, input_channel, "wav_must_be_six_channel_s32_le_48khz_pcm")
    raw_input = audio[input_channel - 1]
    input_peak = max((abs(sample) for sample in raw_input), default=0)
    arrivals = _arrival_samples(raw_input)
    input_metrics = {
        "input_channel": input_channel,
        "peak_dbfs": _dbfs(input_peak),
        "arrivals": arrivals,
    }
    if (input_metrics["peak_dbfs"] is None
            or not MIN_INPUT_PEAK_DB <= input_metrics["peak_dbfs"] <= MAX_INPUT_PEAK_DB):
        return _unavailable(raw_sha256, input_channel, "input_peak_outside_safe_window", input_metrics=input_metrics)
    any_peak = max(abs(sample) for channel in audio for sample in channel)
    if _dbfs(any_peak) > MAX_ANY_PEAK_DB:
        return _unavailable(raw_sha256, input_channel, "any_channel_above_minus_3_dbfs", input_metrics=input_metrics)
    if len(arrivals) != len(_IMPULSE_OFFSETS):
        return _unavailable(raw_sha256, input_channel, "input_must_contain_exactly_five_impulses", input_metrics=input_metrics)
    relative_arrivals = tuple(arrival - arrivals[0] for arrival in arrivals)
    if any(abs(actual - expected) > _IMPULSE_TOLERANCE_SAMPLES
           for actual, expected in zip(relative_arrivals, _IMPULSE_OFFSETS)):
        return _unavailable(raw_sha256, input_channel, "input_impulse_cadence_invalid", input_metrics=input_metrics)
    scores = {}
    for channel in MIX_CHANNELS:
        candidate = audio[channel - 1]
        scores[str(channel)] = max(
            _normalized_impulse_correlation(raw_input, candidate, arrivals, lag)
            for lag in range(MAX_LAG_SAMPLES + 1)
        )
    best_score = max(scores.values())
    if best_score < MIN_MAP_CORRELATION:
        return _unavailable(raw_sha256, input_channel, "no_usable_mix_a_channel", input_metrics=input_metrics, scores=scores)
    rounded_scores = {channel: round(score, 6) for channel, score in scores.items()}
    if rounded_scores["3"] == rounded_scores["4"]:
        frozen_mix_channel = 3
    else:
        frozen_mix_channel = 3 if scores["3"] > scores["4"] else 4
    return {
        "schema": "cp34-current-slot-map-v1",
        "status": "MAPPED",
        "raw_sha256": raw_sha256,
        "input_metrics": input_metrics,
        "scores": scores,
        "frozen_mix_channel": frozen_mix_channel,
        "reasons": [],
    }


def _contains_unrecorded(value):
    if isinstance(value, str):
        return "UNRECORDED" in value
    if isinstance(value, list):
        return any(_contains_unrecorded(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_unrecorded(item) for item in value.values())
    return False


def _load(path):
    try:
        raw = open(path, "rb").read()
    except (OSError, TypeError, ValueError) as exc:
        return b"", None, "plan_unreadable"
    try:
        return raw, _strict_json_loads(raw), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw, None, "plan_invalid_json"


def _strict_json_loads(raw):
    def reject_constant(value):
        raise json.JSONDecodeError("non-standard JSON constant", value, 0)

    return json.loads(raw.decode("utf-8"), parse_constant=reject_constant)


def _candidate_reasons(candidates):
    if not isinstance(candidates, list) or len(candidates) != len(EXPECTED_CANDIDATES):
        return ["candidates_must_be_exactly_current_slots"]
    reasons = []
    candidate_fields = frozenset({
        "label", "channel", "numeric_slot", "physical_input", "connection",
        "restore_connection", "actions",
    })
    action_fields = frozenset({"id", "kind", "press"})
    for index, (candidate, expected) in enumerate(zip(candidates, EXPECTED_CANDIDATES), 1):
        if not isinstance(candidate, dict) or any(candidate.get(key) != value for key, value in expected.items()):
            reasons.append("candidate_%d_must_match_fixed_order" % index)
            continue
        if frozenset(candidate) != candidate_fields:
            reasons.append("candidate_%d_has_unrecognized_fields" % index)
        if not isinstance(candidate.get("connection"), str) or not candidate["connection"].strip():
            reasons.append("candidate_%d_missing_connection" % index)
        if not isinstance(candidate.get("restore_connection"), str) or not candidate["restore_connection"].strip():
            reasons.append("candidate_%d_missing_restore_connection" % index)
        actions = candidate.get("actions")
        if not isinstance(actions, list) or len(actions) != 2:
            reasons.append("candidate_%d_requires_two_toggles" % index)
            continue
        for action_index, (action, action_id) in enumerate(zip(actions, ("T1", "T2")), 1):
            if isinstance(action, dict) and frozenset(action) != action_fields:
                reasons.append("candidate_%d_action_%d_has_unrecognized_fields" % (index, action_index))
            if not isinstance(action, dict) or action.get("id") != action_id:
                reasons.append("candidate_%d_action_%d_id_invalid" % (index, action_index))
            if not isinstance(action, dict) or action.get("kind") != "manual_preset_toggle":
                reasons.append("candidate_%d_action_%d_must_be_manual_toggle" % (index, action_index))
            if not isinstance(action, dict) or action.get("press") != "long":
                reasons.append("candidate_%d_action_%d_must_be_long_press" % (index, action_index))
    return reasons


def _validate_plan_raw(raw, plan=None, load_error=None):
    if plan is None and load_error is None:
        try:
            plan = _strict_json_loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            load_error = "plan_invalid_json"
    result = {
        "schema": "cp34-current-slot-survey-plan-validation-v1",
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "status": "INVALID",
        "reasons": [],
        "candidates": [],
    }
    if load_error:
        result["reasons"].append(load_error)
        return result
    if not isinstance(plan, dict):
        result["reasons"].append("plan_must_be_json_object")
        return result
    result["candidates"] = plan.get("candidates", [])
    reasons = result["reasons"]
    if plan.get("schema") != "cp34-current-slot-survey-plan-v1":
        reasons.append("schema_must_match_cp34_current_slot_survey_v1")
    if not isinstance(plan.get("run_id"), str) or not plan["run_id"].strip():
        reasons.append("run_id_required")
    if plan.get("device_serial") != EXPECTED_SERIAL:
        reasons.append("device_serial_must_match_expected")
    if plan.get("authorization_status") != "EXACT_AUTHORIZATION_RECORDED":
        reasons.append("authorization_status_must_be_exactly_recorded")
    if plan.get("stop_on_first_positive") is not True:
        reasons.append("stop_on_first_positive_must_be_true")
    battery = plan.get("battery_stop_percent")
    if not isinstance(battery, int) or isinstance(battery, bool) or battery < 10:
        reasons.append("battery_stop_percent_must_be_at_least_10")
    evidence_dir = plan.get("evidence_dir")
    run_id = plan.get("run_id")
    if not isinstance(evidence_dir, str) or not evidence_dir.startswith(_EVIDENCE_PREFIX):
        reasons.append("evidence_dir_must_be_under_active_runs")
    elif ".." in PurePosixPath(evidence_dir).parts or not isinstance(run_id, str) or PurePosixPath(evidence_dir).name != run_id:
        reasons.append("evidence_dir_basename_must_match_run_id")
    if _contains_unrecorded(plan):
        reasons.append("unrecorded_value_prohibited")
    source = plan.get("source")
    if not isinstance(source, dict) or source.get("kind") != "external_line_level":
        reasons.append("source_must_be_external_line_level")
    else:
        for field in ("device", "power", "stimulus_path", "cable", "volume"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                reasons.append("source_%s_required" % field)
        if not isinstance(source.get("stimulus_sha256"), str) or not _STIMULUS_HASH.fullmatch(source["stimulus_sha256"]):
            reasons.append("source_stimulus_sha256_must_be_lowercase_hex")
    expected_audio = {"device": "hw:CARD=R24,DEV=0", "format": "S32_LE", "rate": 48000, "channels": 6, "effect_candidates": [3, 4]}
    audio = plan.get("audio")
    if not isinstance(audio, dict) or any(audio.get(key) != value for key, value in expected_audio.items()):
        reasons.append("audio_must_match_fixed_six_channel_shape")
    if plan.get("state_reads") != ["P0", "P1", "P2"]:
        reasons.append("state_reads_must_be_P0_P1_P2")
    if plan.get("continuous_interface_claim") is not False:
        reasons.append("continuous_interface_claim_must_be_false")
    prohibited = plan.get("prohibited_actions")
    if not isinstance(prohibited, list) or frozenset(prohibited) != EXPECTED_PROHIBITED or len(prohibited) != len(EXPECTED_PROHIBITED):
        reasons.append("prohibited_actions_must_match_complete_set")
    reasons.extend(_candidate_reasons(plan.get("candidates")))
    result["status"] = "VALID" if not reasons else "INVALID"
    return result


def validate_plan(path: str) -> dict:
    """Validate one CP34 survey-plan JSON object without touching hardware."""
    raw, plan, load_error = _load(path)
    return _validate_plan_raw(raw, plan, load_error)


def _read_regular_file_once(path):
    """Read one non-symlink regular file and reject an in-read mutation."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise OSError("not a regular file")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
        )
        identity_after = (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
        )
        if identity_before != identity_after:
            raise OSError("file changed while read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _snapshot_inputs(run_dir):
    """Return every pre-verification input as one immutable byte buffer."""
    root = Path(run_dir)
    reasons = []
    inputs = {}
    if root.is_symlink():
        return inputs, ["run_dir_symlink_prohibited"]
    if not root.is_dir():
        return inputs, ["run_dir_unreadable"]

    def visit(directory, relative):
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError:
            reasons.append("input_directory_unreadable:%s" % (relative or "."))
            return
        for entry in entries:
            child_relative = entry.name if not relative else relative + "/" + entry.name
            try:
                if entry.is_symlink():
                    reasons.append("input_symlink_prohibited:%s" % child_relative)
                elif entry.is_dir(follow_symlinks=False):
                    visit(entry.path, child_relative)
                elif entry.is_file(follow_symlinks=False):
                    if child_relative in _EXCLUDED_INPUT_PATHS:
                        continue
                    try:
                        inputs[child_relative] = _read_regular_file_once(entry.path)
                    except OSError:
                        reasons.append("input_unreadable_or_changed:%s" % child_relative)
                else:
                    reasons.append("input_special_file_prohibited:%s" % child_relative)
            except OSError:
                reasons.append("input_unreadable_or_changed:%s" % child_relative)

    visit(str(root), "")
    return inputs, reasons


def _verify_input_manifest(run_dir, inputs=None):
    """Verify an exact, normalized manifest against snapshotted input bytes."""
    if inputs is None:
        inputs, snapshot_reasons = _snapshot_inputs(run_dir)
    else:
        snapshot_reasons = []
    reasons = list(snapshot_reasons)
    if Path(run_dir).is_symlink() or not Path(run_dir).is_dir():
        return {}, reasons + ["evidence_manifest_not_checked_for_unsafe_run_dir"]
    manifest_path = Path(run_dir) / "EVIDENCE-SHA256SUMS"
    try:
        manifest_raw = _read_regular_file_once(str(manifest_path))
    except OSError:
        return {}, reasons + ["evidence_manifest_missing_or_unreadable"]
    try:
        manifest_text = manifest_raw.decode("utf-8")
    except UnicodeDecodeError:
        return {}, reasons + ["evidence_manifest_not_utf8"]

    rows = {}
    for line_number, line in enumerate(manifest_text.splitlines(), 1):
        match = _MANIFEST_ROW.fullmatch(line)
        if not match:
            reasons.append("evidence_manifest_row_invalid:%d" % line_number)
            continue
        expected_hash, relative_text = match.groups()
        if not _is_safe_relative_path(relative_text):
            reasons.append("evidence_manifest_path_unsafe:%d" % line_number)
            continue
        if relative_text in rows:
            reasons.append("evidence_manifest_duplicate:%s" % relative_text)
            continue
        rows[relative_text] = expected_hash

    actual_paths = set(inputs)
    row_paths = set(rows)
    for relative in sorted(actual_paths - row_paths):
        reasons.append("evidence_manifest_omits_input:%s" % relative)
    for relative in sorted(row_paths - actual_paths):
        reasons.append("evidence_manifest_file_missing:%s" % relative)
    actual_hashes = {
        relative: hashlib.sha256(raw).hexdigest()
        for relative, raw in sorted(inputs.items())
    }
    for relative in sorted(actual_paths & row_paths):
        if rows[relative] != actual_hashes[relative]:
            reasons.append("evidence_manifest_hash_mismatch:%s" % relative)
    return actual_hashes, reasons


def _json_input(inputs, relative, reasons):
    raw = inputs.get(relative)
    if raw is None:
        reasons.append("required_input_missing:%s" % relative)
        return None
    try:
        value = _strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        reasons.append("input_invalid_json:%s" % relative)
        return None
    if not isinstance(value, dict):
        reasons.append("input_must_be_json_object:%s" % relative)
        return None
    return value


def _action_log_input(inputs, relative, reasons):
    raw = inputs.get(relative)
    if raw is None:
        reasons.append("required_input_missing:%s" % relative)
        return []
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        reasons.append("action_log_not_utf8")
        return []
    events = []
    for line_number, line in enumerate(lines, 1):
        try:
            event = _strict_json_loads(line.encode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            reasons.append("action_log_invalid_json:%d" % line_number)
            continue
        if not isinstance(event, dict):
            reasons.append("action_log_event_must_be_object:%d" % line_number)
            continue
        events.append(event)
    return events


def _scope_reasons(value, candidate_spec, prefix):
    if not isinstance(value, dict):
        return []
    reasons = []
    if (type(value.get("candidate")) is not type(candidate_spec["label"])
            or value.get("candidate") != candidate_spec["label"]):
        reasons.append("%s_candidate_mismatch" % prefix)
    if (type(value.get("channel")) is not type(candidate_spec["channel"])
            or value.get("channel") != candidate_spec["channel"]):
        reasons.append("%s_channel_mismatch" % prefix)
    return reasons


def _is_safe_relative_path(value):
    if not isinstance(value, str):
        return False
    relative = PurePosixPath(value)
    return not (
        relative.is_absolute() or value != relative.as_posix()
        or value in ("", ".") or ".." in relative.parts
    )


def _same_json_scalar(first, second):
    return type(first) is type(second) and first == second


def _is_finite_numeric(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _state_type_reasons(state, prefix):
    reasons = []
    for key in ("selected_slot", "processing_channel_1", "processing_channel_2"):
        value = state.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            reasons.append("%s_%s_must_be_integer" % (prefix, key))
    for key in ("enabled", "phantom_1", "phantom_2"):
        if not isinstance(state.get(key), bool):
            reasons.append("%s_%s_must_be_boolean" % (prefix, key))
    for key in ("gain_1", "gain_2", "headphone", "main", "monitor_blend"):
        value = state.get(key)
        if (not isinstance(value, (int, float)) or isinstance(value, bool)
                or not math.isfinite(value)):
            reasons.append("%s_%s_must_be_finite_numeric" % (prefix, key))
    return reasons


def _is_mono_s32_48khz_wav(raw):
    try:
        with wave.open(io.BytesIO(raw), "rb") as source:
            return (
                source.getcomptype() == "NONE"
                and source.getnchannels() == 1
                and source.getsampwidth() == 4
                and source.getframerate() == RATE
                and _has_exact_s32_pcm_semantics(raw)
                and len(source.readframes(source.getnframes()))
                    == source.getnframes() * 4
            )
    except (OSError, EOFError, wave.Error):
        return False


def _verify_ab_metric_bindings(ab_result, candidate, frozen_channel,
                               p0_enabled, inputs, reasons):
    if (not isinstance(frozen_channel, int) or isinstance(frozen_channel, bool)
            or frozen_channel not in MIX_CHANNELS):
        reasons.append("ab_metric_frozen_channel_invalid")
        return
    if p0_enabled is True:
        expected = {"dry": ("S2", "S3"), "active": ("S1", "S4")}
    else:
        expected = {"dry": ("S1", "S4"), "active": ("S2", "S3")}
    seen_paths = []
    role_binding_valid = True
    for role in ("dry", "active"):
        rows = ab_result.get(role)
        if not isinstance(rows, list) or len(rows) != 2:
            reasons.append("ab_metric_count_invalid:%s" % role)
            role_binding_valid = False
            continue
        actual_paths = []
        for index, (row, capture) in enumerate(zip(rows, expected[role]), 1):
            if not isinstance(row, dict):
                reasons.append("ab_metric_row_invalid:%s:%d" % (role, index))
                role_binding_valid = False
                continue
            expected_fields = (
                _AB_ACTIVE_METRIC_FIELDS if role == "active"
                else _AB_BASE_METRIC_FIELDS
            )
            if frozenset(row) != expected_fields:
                reasons.append("ab_metric_fields_invalid:%s:%d" % (role, index))
            impulses = row.get("impulses")
            if (not isinstance(impulses, int) or isinstance(impulses, bool)
                    or impulses != 5):
                reasons.append("ab_metric_impulses_invalid:%s:%d" % (role, index))
            offsets = row.get("arrival_offsets_samples")
            if (not isinstance(offsets, list) or len(offsets) != 5
                    or any(not isinstance(value, int) or isinstance(value, bool)
                           for value in offsets)
                    or not offsets or offsets[0] != 0):
                reasons.append(
                    "ab_metric_arrival_offsets_invalid:%s:%d" % (role, index),
                )
            numeric_fields = ["peak", "rms_db", "echo_ratio_db", "late_ratio_db"]
            if role == "active":
                numeric_fields.extend(("echo_delta_db", "late_delta_db"))
            for field in numeric_fields:
                if not _is_finite_numeric(row.get(field)):
                    reasons.append(
                        "ab_metric_%s_must_be_finite_numeric:%s:%d"
                        % (field, role, index),
                    )
            path = row.get("path")
            expected_path = "%s/%s.mix%d.mono.wav" % (
                candidate, capture, frozen_channel,
            )
            if not _is_safe_relative_path(path):
                reasons.append("ab_metric_path_unsafe:%s:%d" % (role, index))
                role_binding_valid = False
                continue
            actual_paths.append(path)
            seen_paths.append(path)
            if path != expected_path:
                reasons.append("ab_metric_path_mismatch:%s:%d" % (role, index))
                role_binding_valid = False
            derivative = inputs.get(path)
            if derivative is None:
                reasons.append("ab_metric_input_missing:%s:%d" % (role, index))
                continue
            declared_hash = row.get("sha256")
            if (not isinstance(declared_hash, str)
                    or not _STIMULUS_HASH.fullmatch(declared_hash)):
                reasons.append("ab_metric_sha256_invalid:%s:%d" % (role, index))
            elif hashlib.sha256(derivative).hexdigest() != declared_hash:
                reasons.append("ab_metric_hash_mismatch:%s:%d" % (role, index))
            if not _is_mono_s32_48khz_wav(derivative):
                reasons.append("ab_metric_wav_invalid:%s:%d" % (role, index))
        if tuple(actual_paths) != tuple(
                "%s/%s.mix%d.mono.wav" % (candidate, capture, frozen_channel)
                for capture in expected[role]):
            role_binding_valid = False
    if len(seen_paths) != 4 or len(set(seen_paths)) != 4:
        reasons.append("ab_metric_paths_must_be_four_distinct_inputs")
        role_binding_valid = False
    if not role_binding_valid:
        reasons.append("ab_metric_role_binding_invalid")


def _deduplicate(reasons):
    return list(dict.fromkeys(reasons))


def verify_restoration(run_dir: str, candidate: str) -> dict:
    """Verify completed CP34 evidence offline without mutating its run tree."""
    reasons = []
    inputs, snapshot_reasons = _snapshot_inputs(run_dir)
    reasons.extend(snapshot_reasons)
    input_hashes, manifest_reasons = _verify_input_manifest(run_dir, inputs)
    reasons.extend(manifest_reasons)
    candidate_spec = next(
        (item for item in EXPECTED_CANDIDATES if item["label"] == candidate), None,
    )
    result = {
        "schema": "cp34-current-slot-restoration-v1",
        "status": "RESTORATION_FAILED",
        "survey_outcome": "INCONCLUSIVE",
        "candidate": candidate,
        "channel": candidate_spec["channel"] if candidate_spec else None,
        "selected_slot": candidate_spec["numeric_slot"] if candidate_spec else None,
        "frozen_mix_channel": None,
        "input_hashes": input_hashes,
        "ja_st_limitation": JA_ST_LIMITATION,
        "reasons": reasons,
    }
    if candidate_spec is None:
        reasons.append("candidate_must_be_exact_current_slot")
        result["reasons"] = _deduplicate(reasons)
        return result

    plan_raw = inputs.get("PLAN.json")
    if plan_raw is None:
        reasons.append("required_input_missing:PLAN.json")
        plan = None
    else:
        plan_validation = _validate_plan_raw(plan_raw)
        if plan_validation["status"] != "VALID":
            reasons.extend("plan_invalid:%s" % reason for reason in plan_validation["reasons"])
        try:
            plan = _strict_json_loads(plan_raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            plan = None
    plan_candidate = None
    if isinstance(plan, dict) and isinstance(plan.get("candidates"), list):
        plan_candidate = next(
            (item for item in plan["candidates"]
             if isinstance(item, dict) and item.get("label") == candidate),
            None,
        )
    if not isinstance(plan_candidate, dict):
        reasons.append("candidate_missing_from_plan")
    elif any(
            not _same_json_scalar(plan_candidate.get(key), expected)
            for key, expected in candidate_spec.items()):
        reasons.append("plan_candidate_scope_mismatch")
    if isinstance(plan, dict) and Path(run_dir).name != plan.get("run_id"):
        reasons.append("run_dir_basename_must_match_plan_run_id")

    prefix = candidate + "/"
    states = {
        checkpoint: _json_input(inputs, prefix + checkpoint + ".json", reasons)
        for checkpoint in ("P0", "P1", "P2")
    }
    raw_snapshot_paths = []
    for checkpoint, state_value in states.items():
        reasons.extend(_scope_reasons(state_value, candidate_spec, checkpoint.lower()))
        if isinstance(state_value, dict):
            checkpoint_prefix = checkpoint.lower()
            reasons.extend(_state_type_reasons(state_value, checkpoint_prefix))
            if state_value.get("schema") != "cp34-current-slot-jast-summary-v1":
                reasons.append("%s_jast_summary_schema_invalid" % checkpoint_prefix)
            if state_value.get("checkpoint") != checkpoint:
                reasons.append("%s_checkpoint_mismatch" % checkpoint_prefix)
            if not _same_json_scalar(
                    state_value.get("selected_slot"), candidate_spec["numeric_slot"]):
                reasons.append("%s_selected_slot_mismatch" % checkpoint_prefix)
            if not isinstance(state_value.get("enabled"), bool):
                reasons.append("%s_enabled_must_be_boolean" % checkpoint_prefix)
            raw_path = state_value.get("raw_snapshot_path")
            raw_hash = state_value.get("raw_snapshot_sha256")
            if (not _is_safe_relative_path(raw_path)
                    or PurePosixPath(raw_path).parts[0] != candidate
                    or len(PurePosixPath(raw_path).parts) < 2):
                reasons.append("%s_raw_snapshot_path_invalid" % checkpoint_prefix)
            else:
                raw_snapshot_paths.append(raw_path)
                raw_bytes = inputs.get(raw_path)
                if raw_bytes is None:
                    reasons.append("%s_raw_snapshot_missing" % checkpoint_prefix)
                elif (not isinstance(raw_hash, str)
                        or not _STIMULUS_HASH.fullmatch(raw_hash)):
                    reasons.append("%s_raw_snapshot_sha256_invalid" % checkpoint_prefix)
                elif hashlib.sha256(raw_bytes).hexdigest() != raw_hash:
                    reasons.append("%s_raw_snapshot_hash_mismatch" % checkpoint_prefix)
            if (not isinstance(raw_hash, str)
                    or not _STIMULUS_HASH.fullmatch(raw_hash)):
                reasons.append("%s_raw_snapshot_sha256_invalid" % checkpoint_prefix)
    if len(raw_snapshot_paths) != len(set(raw_snapshot_paths)):
        reasons.append("jast_raw_snapshots_must_be_distinct")

    p0, p1, p2 = states["P0"], states["P1"], states["P2"]
    if isinstance(p0, dict) and isinstance(p1, dict):
        if isinstance(p0.get("enabled"), bool) and p1.get("enabled") is not (not p0["enabled"]):
            reasons.append("p1_enabled_must_invert_p0")
    if isinstance(p0, dict) and isinstance(p2, dict):
        if isinstance(p0.get("enabled"), bool) and p2.get("enabled") is not p0["enabled"]:
            reasons.append("p2_enabled_must_equal_p0")
        for key in STABLE_STATE_KEYS:
            if key not in p0 or key not in p2:
                reasons.append("stable_state_key_missing:%s" % key)
            elif not _same_json_scalar(p2[key], p0[key]):
                reasons.append("p2_stable_state_mismatch:%s" % key)

    events = _action_log_input(inputs, prefix + "ACTION-LOG.jsonl", reasons)
    event_shape = tuple((event.get("id"), event.get("kind")) for event in events)
    if event_shape != EXPECTED_EVENTS:
        reasons.append("action_log_event_sequence_mismatch")
    timestamps = []
    for index, event in enumerate(events, 1):
        reasons.extend(_scope_reasons(event, candidate_spec, "event_%d" % index))
        expected_fields = {"candidate", "channel", "id", "kind", "monotonic_ns"}
        if event.get("kind") == "manual_preset_toggle":
            expected_fields.add("press")
        if event.get("kind") == "audio_capture":
            expected_fields.add("frozen_mix_channel")
        if set(event) != expected_fields:
            reasons.append("action_log_event_fields_invalid:%d" % index)
        timestamp = event.get("monotonic_ns")
        if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool) or not math.isfinite(timestamp):
            reasons.append("action_log_timestamp_invalid:%d" % index)
        else:
            timestamps.append(timestamp)
        if event.get("kind") == "mapped_write" or "mapped_write" in event:
            reasons.append("mapped_write_prohibited")
    if len(timestamps) != len(events) or any(
            current <= previous for previous, current in zip(timestamps, timestamps[1:])):
        reasons.append("action_log_timestamps_not_strictly_increasing")
    toggles = [event for event in events if event.get("kind") == "manual_preset_toggle"]
    if len(toggles) != 2:
        reasons.append("exactly_two_manual_toggles_required")
    for toggle in toggles:
        if toggle.get("press") != "long":
            reasons.append("manual_toggle_must_be_long_press")

    map_result = _json_input(inputs, prefix + "MAP.json", reasons)
    frozen_channel = map_result.get("frozen_mix_channel") if isinstance(map_result, dict) else None
    result["frozen_mix_channel"] = frozen_channel
    if isinstance(map_result, dict):
        if map_result.get("schema") != "cp34-current-slot-map-v1":
            reasons.append("map_schema_invalid")
        if map_result.get("status") != "MAPPED":
            reasons.append("map_status_must_be_mapped")
        input_metrics = map_result.get("input_metrics")
        if (not isinstance(input_metrics, dict)
                or not _same_json_scalar(
                    input_metrics.get("input_channel"), candidate_spec["physical_input"]
                )):
            reasons.append("map_input_channel_mismatch")
        if not any(_same_json_scalar(frozen_channel, channel) for channel in MIX_CHANNELS):
            reasons.append("map_frozen_channel_invalid")
        map_raw = inputs.get(prefix + "MAP.raw.wav")
        if map_raw is None:
            reasons.append("required_input_missing:%sMAP.raw.wav" % prefix)
        elif map_result.get("raw_sha256") != hashlib.sha256(map_raw).hexdigest():
            reasons.append("map_raw_hash_mismatch")

    for event in events:
        if (event.get("kind") == "audio_capture"
                and not _same_json_scalar(
                    event.get("frozen_mix_channel"), frozen_channel
                )):
            reasons.append(
                "audio_capture_frozen_channel_mismatch:%s" % event.get("id"),
            )

    s4_raw = inputs.get(prefix + "S4.raw.wav")
    if s4_raw is None:
        reasons.append("required_input_missing:%sS4.raw.wav" % prefix)
    else:
        try:
            _read_six_channel_wav(s4_raw)
        except (TypeError, ValueError):
            reasons.append("s4_wav_invalid")
    s4_events = [event for event in events if event.get("id") == "S4"]
    if len(s4_events) != 1 or s4_events[0].get("frozen_mix_channel") != frozen_channel:
        reasons.append("s4_must_use_frozen_mix_channel")

    ab_result = _json_input(inputs, prefix + "AB.json", reasons)
    ab_status = None
    if isinstance(ab_result, dict):
        if frozenset(ab_result) != _AB_TOP_LEVEL_FIELDS:
            reasons.append("ab_top_level_fields_invalid")
        if any(not isinstance(ab_result.get(field), str) for field in (
                "schema", "status", "classification", "candidate",
                "model_identity")):
            reasons.append("ab_top_level_string_types_invalid")
        if any(not isinstance(ab_result.get(field), bool) for field in (
                "reverb_like_observed", "title_verified", "live_ready",
                "restoration_verified", "audible_attested")):
            reasons.append("ab_top_level_boolean_types_invalid")
        if not _same_json_scalar(ab_result.get("expected_delay_s"), 0.15):
            reasons.append("ab_expected_delay_must_be_0_15")
        ab_reasons = ab_result.get("reasons")
        if (not isinstance(ab_reasons, list)
                or any(not isinstance(reason, str) for reason in ab_reasons)):
            reasons.append("ab_reasons_must_be_string_list")
        if ab_result.get("schema") != "cp34-slot-survey-audio-v1":
            reasons.append("ab_schema_invalid")
        if not _same_json_scalar(ab_result.get("candidate"), candidate):
            reasons.append("ab_candidate_mismatch")
        if ab_result.get("model_identity") != "UNRESOLVED":
            reasons.append("ab_model_identity_must_be_unresolved")
        for field in ("title_verified", "live_ready", "restoration_verified"):
            if ab_result.get(field) is not False:
                reasons.append("ab_%s_must_be_false" % field)
        ab_status = ab_result.get("status")
        classification = ab_result.get("classification")
        positive_classifier = (
            ab_status == "SIGNATURE_PRESENT"
            and classification == "REPEAT_150MS_SIGNATURE"
            and ab_result.get("reverb_like_observed") is False
            and ab_result.get("audible_attested") is True
            and ab_result.get("reasons") == []
        )
        inconclusive_classifier = (
            ab_status == "INCONCLUSIVE"
            and classification in (
                "NO_DISTINCTIVE_SIGNATURE", "NON_SPECIFIC_LATE_TAIL",
            )
            and isinstance(ab_result.get("audible_attested"), bool)
            and isinstance(ab_result.get("reasons"), list)
            and (
                (classification == "NON_SPECIFIC_LATE_TAIL"
                 and ab_result.get("reverb_like_observed") is True)
                or (classification == "NO_DISTINCTIVE_SIGNATURE"
                    and ab_result.get("reverb_like_observed") is False)
            )
        )
        if not positive_classifier and not inconclusive_classifier:
            reasons.append("ab_status_classification_inconsistent")
        _verify_ab_metric_bindings(
            ab_result, candidate, frozen_channel,
            p0.get("enabled") if isinstance(p0, dict) else None,
            inputs, reasons,
        )

    audible = _json_input(inputs, prefix + "AUDIBLE-ATTESTATION.json", reasons)
    audible_positive = False
    if isinstance(audible, dict):
        reasons.extend(_scope_reasons(audible, candidate_spec, "audible_attestation"))
        if audible.get("schema") != "cp34-current-slot-audible-attestation-v1":
            reasons.append("audible_attestation_schema_invalid")
        if audible.get("phase") != "POST_RESTORATION":
            reasons.append("audible_attestation_phase_invalid")
        if not _same_json_scalar(audible.get("frozen_mix_channel"), frozen_channel):
            reasons.append("audible_attestation_frozen_channel_mismatch")
        audible_positive = (
            audible.get("operator_attested") is True
            and _same_json_scalar(audible.get("active_repeats_heard"), 2)
            and _same_json_scalar(audible.get("dry_repeats_heard"), 0)
        )

    physical = _json_input(inputs, prefix + "PHYSICAL-RESTORATION.json", reasons)
    if isinstance(physical, dict):
        reasons.extend(_scope_reasons(physical, candidate_spec, "physical_restoration"))
        if physical.get("schema") != "cp34-current-slot-physical-restoration-v1":
            reasons.append("physical_restoration_schema_invalid")
        if physical.get("restored") is not True or physical.get("operator_attested") is not True:
            reasons.append("physical_restoration_not_attested")
        expected_connection = plan_candidate.get("restore_connection") if isinstance(plan_candidate, dict) else None
        if not expected_connection or physical.get("restored_connection") != expected_connection:
            reasons.append("physical_restoration_connection_mismatch")

    if candidate == "ch2-slot1":
        first_result = _json_input(
            inputs, "ch1-slot1/RESTORATION.json", reasons,
        )
        if not (isinstance(first_result, dict)
                and first_result.get("schema") == "cp34-current-slot-restoration-v1"
                and _same_json_scalar(first_result.get("candidate"), "ch1-slot1")
                and _same_json_scalar(first_result.get("channel"), 1)
                and first_result.get("status") == "RESTORED"
                and first_result.get("survey_outcome") == "INCONCLUSIVE"):
            reasons.append("second_candidate_requires_restored_inconclusive_first")

    result["reasons"] = _deduplicate(reasons)
    if not result["reasons"]:
        result["status"] = "RESTORED"
        if (ab_status == "SIGNATURE_PRESENT"
                and ab_result.get("classification") == "REPEAT_150MS_SIGNATURE"
                and audible_positive):
            result["survey_outcome"] = "SIGNATURE_PRESENT"
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "validate-plan":
        result = validate_plan(argv[1])
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0 if result["status"] == "VALID" else 2
    if len(argv) == 4 and argv[0] == "map-channel" and argv[2] == "--input-channel":
        try:
            input_channel = int(argv[3])
        except ValueError:
            input_channel = 0
        result = analyze_map(argv[1], input_channel)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0 if result["status"] == "MAPPED" else 2
    if len(argv) == 4 and argv[0] == "verify-restoration" and argv[2] == "--candidate":
        result = verify_restoration(argv[1], argv[3])
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0 if result["status"] == "RESTORED" else 2
    result = {"schema": "cp34-current-slot-survey-plan-validation-v1", "status": "INVALID", "plan_sha256": hashlib.sha256(b"").hexdigest(), "reasons": ["usage: validate-plan PLAN.json | map-channel MAP.raw.wav --input-channel 1 | verify-restoration RUN_DIR --candidate ch1-slot1"], "candidates": []}
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 2


if __name__ == "__main__":
    sys.exit(main())
