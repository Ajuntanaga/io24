import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "re" / "cp34_current_slot_survey.py"
SURVEY_SPEC = importlib.util.spec_from_file_location("cp34_current_slot_survey", CLI)
SURVEY = importlib.util.module_from_spec(SURVEY_SPEC)
SURVEY_SPEC.loader.exec_module(SURVEY)


def _write_six_channel_map_wav(
    path,
    *,
    input_channel=1,
    responses=None,
    arrivals=(0, 33600, 67200, 100800, 134400),
    input_amplitude=135000000,
    noise_amplitude=31,
):
    """Write a hand-defined six-channel S32_LE map-analysis fixture."""
    if responses is None:
        responses = {3: (480, (0, 1, 2, 3, 4))}
    frame_count = max(arrivals) + 13000
    frames = [[noise_amplitude if (frame + channel) % 2 else -noise_amplitude
               for channel in range(6)] for frame in range(frame_count)]
    for arrival in arrivals:
        frames[arrival][input_channel - 1] = input_amplitude
    for channel, (lag, response_indices) in responses.items():
        for index in response_indices:
            frames[arrivals[index] + lag][channel - 1] = input_amplitude
    with wave.open(str(path), "wb") as output:
        output.setnchannels(6)
        output.setsampwidth(4)
        output.setframerate(48000)
        output.setcomptype("NONE", "not compressed")
        output.writeframes(b"".join(
            int(sample).to_bytes(4, "little", signed=True)
            for frame in frames for sample in frame
        ))


def _write_six_channel_extensible_24_valid_bits_wav(path):
    """Write a PCM-subtype 32-bit container whose declared valid bits are 24."""
    fmt = struct.pack(
        "<HHIIHHHHI16s",
        0xFFFE, 6, 48000, 48000 * 6 * 4, 6 * 4, 32, 22, 24, 0x3F,
        bytes.fromhex("0100000000001000800000aa00389b71"),
    )
    payload = b"\0" * (6 * 4)
    path.write_bytes(
        b"RIFF" + struct.pack("<I", 4 + 8 + len(fmt) + 8 + len(payload))
        + b"WAVEfmt " + struct.pack("<I", len(fmt)) + fmt
        + b"data" + struct.pack("<I", len(payload)) + payload
    )


def _valid_plan():
    return {
        "schema": "cp34-current-slot-survey-plan-v1",
        "run_id": "20260829T120000-0700-current-slot-survey",
        "device_serial": "AB7C22200355",
        "authorization_status": "EXACT_AUTHORIZATION_RECORDED",
        "stop_on_first_positive": True,
        "battery_stop_percent": 10,
        "evidence_dir": (
            ".superpowers/sdd/2026-08-28-cp34-preset-effect-control/"
            "runs/20260829T120000-0700-current-slot-survey"
        ),
        "source": {
            "kind": "external_line_level",
            "device": "offline-fixture-player",
            "power": "isolated-battery",
            "stimulus_path": "/offline/slap-impulses.wav",
            "stimulus_sha256": "a" * 64,
            "cable": "balanced-line-fixture",
            "volume": "fixed-mark-4",
        },
        "audio": {
            "device": "hw:CARD=R24,DEV=0",
            "format": "S32_LE",
            "rate": 48000,
            "channels": 6,
            "effect_candidates": [3, 4],
        },
        "state_reads": ["P0", "P1", "P2"],
        "continuous_interface_claim": False,
        "candidates": [
            {
                "label": "ch1-slot1", "channel": 1, "numeric_slot": 0,
                "physical_input": 1,
                "connection": "player line out to io24 input 1",
                "restore_connection": "remove cable from io24 input 1",
                "actions": [
                    {"id": "T1", "kind": "manual_preset_toggle", "press": "long"},
                    {"id": "T2", "kind": "manual_preset_toggle", "press": "long"},
                ],
            },
            {
                "label": "ch2-slot1", "channel": 2, "numeric_slot": 2,
                "physical_input": 2,
                "connection": "player line out to io24 input 2",
                "restore_connection": "remove cable from io24 input 2",
                "actions": [
                    {"id": "T1", "kind": "manual_preset_toggle", "press": "long"},
                    {"id": "T2", "kind": "manual_preset_toggle", "press": "long"},
                ],
            },
        ],
        "prohibited_actions": [
            "slot_selection", "mapped_write", "device_output_playback",
            "io24_monitoring", "wine", "network", "firmware", "reset",
            "dfu", "install", "stage", "usb_detach", "guessed_packet",
        ],
    }


EXPECTED_EVENTS = (
    ("P0", "state_read"), ("M0", "audio_capture"),
    ("S1", "audio_capture"), ("T1", "manual_preset_toggle"),
    ("P1", "state_read"), ("S2", "audio_capture"),
    ("S3", "audio_capture"), ("T2", "manual_preset_toggle"),
    ("P2", "state_read"), ("S4", "audio_capture"),
)


def _write_minimal_six_channel_wav(path):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(6)
        output.setsampwidth(4)
        output.setframerate(48000)
        output.writeframes(b"\0" * 24)


def _write_minimal_mono_wav(path):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(4)
        output.setframerate(48000)
        output.writeframes(b"\0" * 4)


def _refresh_evidence_manifest(run_dir):
    excluded = {"EVIDENCE-SHA256SUMS", "RESTORATION.json", "REPORT.md", "SHA256SUMS"}
    rows = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        if relative not in excluded:
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n")
    (run_dir / "EVIDENCE-SHA256SUMS").write_text("".join(rows), encoding="utf-8")


def _build_restoration_run(base, *, candidate="ch1-slot1", enabled=True,
                           outcome="SIGNATURE_PRESENT", include_first_result=False):
    run_id = "20260829T120000-0700-current-slot-survey"
    run_dir = Path(base) / run_id
    run_dir.mkdir()
    plan = _valid_plan()
    (run_dir / "PLAN.json").write_text(json.dumps(plan), encoding="utf-8")

    candidate_spec = next(item for item in plan["candidates"] if item["label"] == candidate)
    candidate_dir = run_dir / candidate
    candidate_dir.mkdir()
    stable = {
        "selected_slot": candidate_spec["numeric_slot"],
        "processing_channel_1": 1,
        "processing_channel_2": 2,
        "phantom_1": False,
        "phantom_2": False,
        "gain_1": 37.0,
        "gain_2": 0.0,
        "headphone": 0.25,
        "main": 0.5,
        "monitor_blend": 0.0,
    }
    scope = {
        "candidate": candidate,
        "channel": candidate_spec["channel"],
    }
    for checkpoint, checkpoint_enabled in (
        ("P0", enabled), ("P1", not enabled), ("P2", enabled),
    ):
        raw_path = candidate_dir / f"{checkpoint}.raw.jast"
        raw_path.write_bytes((checkpoint + " immutable raw JaSt fixture\n").encode("ascii"))
        payload = dict(
            scope,
            schema="cp34-current-slot-jast-summary-v1",
            checkpoint=checkpoint,
            enabled=checkpoint_enabled,
            raw_snapshot_path=raw_path.relative_to(run_dir).as_posix(),
            raw_snapshot_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            **stable,
        )
        (candidate_dir / f"{checkpoint}.json").write_text(
            json.dumps(payload), encoding="utf-8",
        )

    events = []
    for timestamp, (event_id, kind) in enumerate(EXPECTED_EVENTS, 1):
        event = dict(scope, id=event_id, kind=kind, monotonic_ns=timestamp)
        if event_id in ("T1", "T2"):
            event["press"] = "long"
        if event_id in ("M0", "S1", "S2", "S3", "S4"):
            event["frozen_mix_channel"] = 3
        events.append(event)
    (candidate_dir / "ACTION-LOG.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8",
    )

    _write_minimal_six_channel_wav(candidate_dir / "MAP.raw.wav")
    for capture in ("S1", "S2", "S3", "S4"):
        _write_minimal_six_channel_wav(candidate_dir / f"{capture}.raw.wav")
    map_hash = hashlib.sha256((candidate_dir / "MAP.raw.wav").read_bytes()).hexdigest()
    (candidate_dir / "MAP.json").write_text(json.dumps({
        "schema": "cp34-current-slot-map-v1",
        "status": "MAPPED",
        "raw_sha256": map_hash,
        "input_metrics": {
            "input_channel": candidate_spec["physical_input"],
            "peak_dbfs": -24.0,
            "arrivals": [0, 33600, 67200, 100800, 134400],
        },
        "scores": {"3": 1.0, "4": 0.0},
        "frozen_mix_channel": 3,
        "reasons": [],
    }), encoding="utf-8")
    active_ids = ("S1", "S4") if enabled else ("S2", "S3")
    dry_ids = ("S2", "S3") if enabled else ("S1", "S4")
    metric_rows = {}
    for capture in ("S1", "S2", "S3", "S4"):
        derivative = candidate_dir / f"{capture}.mix3.mono.wav"
        _write_minimal_mono_wav(derivative)
        relative = derivative.relative_to(run_dir).as_posix()
        metric_rows[capture] = {
            "path": relative,
            "sha256": hashlib.sha256(derivative.read_bytes()).hexdigest(),
            "impulses": 5,
            "arrival_offsets_samples": [0, 33600, 67200, 100800, 134400],
            "peak": 0.125,
            "rms_db": -40.0,
            "echo_ratio_db": -6.0 if capture in active_ids else -40.0,
            "late_ratio_db": -40.0,
        }
    for capture in active_ids:
        metric_rows[capture]["echo_delta_db"] = 34.0
        metric_rows[capture]["late_delta_db"] = 0.0
    classifier_positive = outcome == "SIGNATURE_PRESENT"
    (candidate_dir / "AB.json").write_text(json.dumps({
        "schema": "cp34-slot-survey-audio-v1",
        "status": "SIGNATURE_PRESENT" if classifier_positive else "INCONCLUSIVE",
        "classification": (
            "REPEAT_150MS_SIGNATURE" if classifier_positive
            else "NO_DISTINCTIVE_SIGNATURE"
        ),
        "reverb_like_observed": False,
        "candidate": candidate,
        "model_identity": "UNRESOLVED",
        "title_verified": False,
        "live_ready": False,
        "restoration_verified": False,
        "audible_attested": classifier_positive,
        "expected_delay_s": 0.15,
        "dry": [metric_rows[capture] for capture in dry_ids],
        "active": [metric_rows[capture] for capture in active_ids],
        "reasons": [] if classifier_positive else ["audible result was not attested"],
    }), encoding="utf-8")
    (candidate_dir / "AUDIBLE-ATTESTATION.json").write_text(json.dumps({
        "schema": "cp34-current-slot-audible-attestation-v1",
        "phase": "POST_RESTORATION",
        **scope,
        "frozen_mix_channel": 3,
        "active_repeats_heard": 2,
        "dry_repeats_heard": 0,
        "operator_attested": True,
    }), encoding="utf-8")
    (candidate_dir / "PHYSICAL-RESTORATION.json").write_text(json.dumps({
        "schema": "cp34-current-slot-physical-restoration-v1",
        **scope,
        "restored": True,
        "operator_attested": True,
        "restored_connection": candidate_spec["restore_connection"],
    }), encoding="utf-8")
    if include_first_result:
        first_dir = run_dir / "ch1-slot1"
        first_dir.mkdir(exist_ok=True)
        (first_dir / "RESTORATION.json").write_text(json.dumps({
            "schema": "cp34-current-slot-restoration-v1",
            "status": "RESTORED",
            "survey_outcome": "INCONCLUSIVE",
            "candidate": "ch1-slot1",
            "channel": 1,
        }), encoding="utf-8")
    _refresh_evidence_manifest(run_dir)
    return run_dir


class PlanValidatorTests(unittest.TestCase):
    def _invoke(self, plan):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PLAN.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(CLI), "validate-plan", str(path)],
                text=True, capture_output=True, check=False,
            )
        return completed

    def _assert_invalid(self, plan, reason):
        completed = self._invoke(plan)
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn("Traceback", completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "INVALID")
        self.assertIn(reason, result["reasons"])

    def test_accepts_exact_current_slot_plan(self):
        completed = self._invoke(_valid_plan())
        self.assertEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertEqual(result["schema"], "cp34-current-slot-survey-plan-validation-v1")
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(
            [candidate["label"] for candidate in result["candidates"]],
            ["ch1-slot1", "ch2-slot1"],
        )

    def test_rejects_non_object_plan(self):
        self._assert_invalid([], "plan_must_be_json_object")

    def test_rejects_wrong_serial_or_authorization_status(self):
        plan = _valid_plan(); plan["device_serial"] = "wrong"
        self._assert_invalid(plan, "device_serial_must_match_expected")
        plan = _valid_plan(); plan["authorization_status"] = "UNRECORDED"
        self._assert_invalid(plan, "authorization_status_must_be_exactly_recorded")

    def test_rejects_reordered_or_changed_candidates(self):
        plan = _valid_plan(); plan["candidates"].reverse()
        self._assert_invalid(plan, "candidate_1_must_match_fixed_order")
        plan = _valid_plan(); plan["candidates"][0]["numeric_slot"] = 1
        self._assert_invalid(plan, "candidate_1_must_match_fixed_order")

    def test_rejects_false_stop_on_first_positive(self):
        plan = _valid_plan(); plan["stop_on_first_positive"] = False
        self._assert_invalid(plan, "stop_on_first_positive_must_be_true")

    def test_rejects_device_output_or_unrecorded_source(self):
        plan = _valid_plan(); plan["source"]["kind"] = "device_output_playback"
        self._assert_invalid(plan, "source_must_be_external_line_level")
        plan = _valid_plan(); plan["source"]["device"] = "UNRECORDED"
        self._assert_invalid(plan, "unrecorded_value_prohibited")

    def test_rejects_wrong_audio_shape_or_effect_channels(self):
        plan = _valid_plan(); plan["audio"]["channels"] = 2
        self._assert_invalid(plan, "audio_must_match_fixed_six_channel_shape")
        plan = _valid_plan(); plan["audio"]["effect_candidates"] = [4, 3]
        self._assert_invalid(plan, "audio_must_match_fixed_six_channel_shape")

    def test_rejects_continuous_or_missing_state_reads(self):
        plan = _valid_plan(); plan["continuous_interface_claim"] = True
        self._assert_invalid(plan, "continuous_interface_claim_must_be_false")
        plan = _valid_plan(); plan["state_reads"] = ["P0", "P1"]
        self._assert_invalid(plan, "state_reads_must_be_P0_P1_P2")

    def test_rejects_wrong_toggle_count_short_press_or_mapped_action(self):
        plan = _valid_plan(); plan["candidates"][0]["actions"].pop()
        self._assert_invalid(plan, "candidate_1_requires_two_toggles")
        plan = _valid_plan(); plan["candidates"][0]["actions"][0]["press"] = "short"
        self._assert_invalid(plan, "candidate_1_action_1_must_be_long_press")
        plan = _valid_plan(); plan["candidates"][0]["actions"][0]["kind"] = "mapped_write"
        self._assert_invalid(plan, "candidate_1_action_1_must_be_manual_toggle")
        plan = _valid_plan(); plan["candidates"][0]["slot_selection"] = "modeled-mutation"
        self._assert_invalid(plan, "candidate_1_has_unrecognized_fields")
        plan = _valid_plan(); plan["candidates"][0]["actions"][0]["mapped_write"] = "modeled-mutation"
        self._assert_invalid(plan, "candidate_1_action_1_has_unrecognized_fields")

    def test_rejects_unsafe_path_battery_floor_or_missing_prohibitions(self):
        plan = _valid_plan(); plan["schema"] = "wrong"
        self._assert_invalid(plan, "schema_must_match_cp34_current_slot_survey_v1")
        plan = _valid_plan(); plan["evidence_dir"] = "/tmp/outside"
        self._assert_invalid(plan, "evidence_dir_must_be_under_active_runs")
        plan = _valid_plan(); plan["battery_stop_percent"] = 9
        self._assert_invalid(plan, "battery_stop_percent_must_be_at_least_10")
        plan = _valid_plan(); plan["prohibited_actions"].remove("wine")
        self._assert_invalid(plan, "prohibited_actions_must_match_complete_set")


class SurveyTemplateContractTests(unittest.TestCase):
    def test_checked_in_template_is_rejected_as_unrecorded_and_unauthorized(self):
        """Catches accidental shipment of a live-ready survey template."""
        template = ROOT / ".superpowers" / "sdd" / "2026-08-28-cp34-preset-effect-control" / "CURRENT-SLOT-SURVEY-PLAN.template.json"
        procedure = (ROOT / ".superpowers" / "sdd"
                     / "2026-08-28-cp34-preset-effect-control"
                     / "CURRENT-SLOT-SURVEY.md").read_text(encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(CLI), "validate-plan", str(template)],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn("Traceback", completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "INVALID")
        self.assertTrue(any("authorization_status" in reason for reason in result["reasons"]))
        self.assertTrue(any("UNRECORDED" in reason.upper() for reason in result["reasons"]))
        self.assertLess(
            procedure.index("1. `P0`:"),
            procedure.index("ALSA capture streams and interface-5 claims never overlap."),
        )
        self.assertIn("A null signal is `INCONCLUSIVE`, never a negative.", procedure)
        self.assertIn("-print0 | LC_ALL=C sort -z | xargs -0r sha256sum --", procedure)
        self.assertIn("set -o pipefail && find", procedure)
        self.assertIn('ln "$tmpdir/SHA256SUMS" SHA256SUMS', procedure)
        self.assertNotIn("> SHA256SUMS", procedure)


class MappingAnalyzerTests(unittest.TestCase):
    def _invoke_map(self, path, input_channel=1):
        return subprocess.run(
            [sys.executable, str(CLI), "map-channel", str(path),
             "--input-channel", str(input_channel)],
            text=True, capture_output=True, check=False,
        )

    def _assert_unavailable(self, path, reason, input_channel=1):
        completed = self._invoke_map(path, input_channel)
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn("Traceback", completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn(reason, result["reasons"])

    def test_selects_channel_3_for_correlated_five_impulse_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            _write_six_channel_map_wav(path)
            completed = self._invoke_map(path)
        self.assertEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "MAPPED")
        self.assertEqual(result["frozen_mix_channel"], 3)
        self.assertEqual(len(result["input_metrics"]["arrivals"]), 5)
        self.assertIn("3", result["scores"])
        self.assertIn("4", result["scores"])
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.wav"
            second_path = Path(directory) / "second.wav"
            _write_six_channel_map_wav(first_path)
            _write_six_channel_map_wav(second_path, responses={
                3: (480, (0, 1, 2, 3)), 4: (760, (0, 1, 2, 3, 4)),
            })
            first_raw = first_path.read_bytes()
            original_open = open
            calls = 0

            def changing_path_open(candidate, *args, **kwargs):
                nonlocal calls
                if candidate == str(first_path) and args and args[0] == "rb":
                    calls += 1
                    target = first_path if calls == 1 else second_path
                    return original_open(target, *args, **kwargs)
                return original_open(candidate, *args, **kwargs)

            with patch("builtins.open", side_effect=changing_path_open):
                analyzed = SURVEY.analyze_map(str(first_path), 1)
        self.assertEqual(analyzed["status"], "MAPPED")
        self.assertEqual(analyzed["frozen_mix_channel"], 3)
        self.assertEqual(analyzed["raw_sha256"], hashlib.sha256(first_raw).hexdigest())

    def test_selects_channel_4_when_its_score_is_higher(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            _write_six_channel_map_wav(path, responses={
                3: (480, (0, 1, 2, 3)), 4: (760, (0, 1, 2, 3, 4)),
            })
            completed = self._invoke_map(path)
        self.assertEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertEqual(result["frozen_mix_channel"], 4)
        self.assertGreater(result["scores"]["4"], result["scores"]["3"])

    def test_equal_six_decimal_scores_choose_channel_3(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            _write_six_channel_map_wav(path, responses={
                3: (480, (0, 1, 2, 3, 4)), 4: (760, (0, 1, 2, 3, 4)),
            })
            completed = self._invoke_map(path)
        self.assertEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertEqual(round(result["scores"]["3"], 6), round(result["scores"]["4"], 6))
        self.assertEqual(result["frozen_mix_channel"], 3)

    def test_no_usable_mix_a_channel_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            _write_six_channel_map_wav(path, responses={
                3: (480, (0,)), 4: (760, (1,)),
            })
            self._assert_unavailable(path, "no_usable_mix_a_channel")

    def test_changed_impulse_cadence_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            _write_six_channel_map_wav(
                path, arrivals=(0, 33697, 67200, 100800, 134400),
            )
            self._assert_unavailable(path, "input_impulse_cadence_invalid")

    def test_any_channel_above_minus_3_dbfs_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            _write_six_channel_map_wav(path)
            with wave.open(str(path), "rb") as source:
                params = source.getparams()
                payload = bytearray(source.readframes(source.getnframes()))
            payload[(130000 * 6 + 5) * 4:(130000 * 6 + 6) * 4] = (2000000000).to_bytes(
                4, "little", signed=True,
            )
            with wave.open(str(path), "wb") as output:
                output.setparams(params)
                output.writeframes(payload)
            self._assert_unavailable(path, "any_channel_above_minus_3_dbfs")

    def test_input_peak_outside_safe_window_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            _write_six_channel_map_wav(path, input_amplitude=3000000)
            self._assert_unavailable(path, "input_peak_outside_safe_window")
            _write_six_channel_map_wav(
                path, input_amplitude=0, noise_amplitude=0, responses={},
            )
            completed = self._invoke_map(path)
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn("Infinity", completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIsNone(result["input_metrics"]["peak_dbfs"])

    def test_wrong_wav_format_is_unavailable_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            with wave.open(str(path), "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(b"\0\0\0\0" * 16)
            self._assert_unavailable(path, "wav_must_be_six_channel_s32_le_48khz_pcm")
            _write_six_channel_extensible_24_valid_bits_wav(path)
            self._assert_unavailable(path, "wav_must_be_six_channel_s32_le_48khz_pcm")


class RestorationVerifierTests(unittest.TestCase):
    def _invoke_restoration(self, run_dir, candidate="ch1-slot1"):
        return subprocess.run(
            [sys.executable, str(CLI), "verify-restoration", str(run_dir),
             "--candidate", candidate],
            text=True, capture_output=True, check=False,
        )

    def _result(self, run_dir, candidate="ch1-slot1"):
        completed = self._invoke_restoration(run_dir, candidate)
        self.assertNotIn("Traceback", completed.stderr)
        return completed, json.loads(completed.stdout)

    def _mutate_json(self, path, mutate):
        value = json.loads(path.read_text(encoding="utf-8"))
        mutate(value)
        path.write_text(json.dumps(value), encoding="utf-8")

    def _mutate_action_log(self, path, mutate):
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        mutate(events)
        path.write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8",
        )

    def test_enabled_first_restores_with_signature_present(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            before = {
                path.relative_to(run_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in run_dir.rglob("*") if path.is_file()
            }
            completed = self._invoke_restoration(run_dir)
            after = {
                path.relative_to(run_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in run_dir.rglob("*") if path.is_file()
            }
            ab = run_dir / "ch1-slot1" / "AB.json"
            self._mutate_json(ab, lambda value: value.pop("expected_delay_s"))
            self._mutate_json(ab, lambda value: value["dry"][0].pop("impulses"))
            self._mutate_json(
                ab,
                lambda value: value["dry"][1].update(
                    arrival_offsets_samples=[1, 2, 3, 4, 5], peak=True,
                ),
            )
            self._mutate_json(
                ab, lambda value: value["active"][0].pop("echo_delta_db"),
            )
            self._mutate_json(
                ab,
                lambda value: value["active"][1].update(
                    echo_ratio_db=10 ** 1000,
                    late_delta_db="bad",
                ),
            )
            _refresh_evidence_manifest(run_dir)
            malformed_completed, malformed_result = self._result(run_dir)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(after, before)
        self.assertNotIn("Traceback", completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["schema"], "cp34-current-slot-restoration-v1")
        self.assertEqual(result["status"], "RESTORED")
        self.assertEqual(result["survey_outcome"], "SIGNATURE_PRESENT")
        self.assertEqual(result["frozen_mix_channel"], 3)
        self.assertEqual(
            result["input_hashes"],
            {relative: digest for relative, digest in before.items()
             if relative not in {
                 "EVIDENCE-SHA256SUMS", "RESTORATION.json", "REPORT.md", "SHA256SUMS",
             }},
        )
        self.assertEqual(
            result["ja_st_limitation"],
            "JaSt cannot prove every internal DSP byte.",
        )
        self.assertEqual(malformed_completed.returncode, 2)
        self.assertIn("ab_top_level_fields_invalid", malformed_result["reasons"])
        self.assertIn("ab_metric_fields_invalid:dry:1", malformed_result["reasons"])
        self.assertIn(
            "ab_metric_arrival_offsets_invalid:dry:2",
            malformed_result["reasons"],
        )
        self.assertIn(
            "ab_metric_peak_must_be_finite_numeric:dry:2",
            malformed_result["reasons"],
        )
        self.assertIn("ab_metric_fields_invalid:active:1", malformed_result["reasons"])
        self.assertIn(
            "ab_metric_late_delta_db_must_be_finite_numeric:active:2",
            malformed_result["reasons"],
        )
        self.assertIn(
            "ab_metric_echo_ratio_db_must_be_finite_numeric:active:2",
            malformed_result["reasons"],
        )

    def test_bypassed_first_restores_with_inconclusive_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(
                directory, enabled=False, outcome=None,
            )
            audible = run_dir / "ch1-slot1" / "AUDIBLE-ATTESTATION.json"
            self._mutate_json(audible, lambda value: value.update({
                "active_repeats_heard": None,
                "dry_repeats_heard": None,
            }))
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(result["status"], "RESTORED")
        self.assertEqual(result["survey_outcome"], "INCONCLUSIVE")

    def test_selected_slot_drift_fails_restoration(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            p2 = run_dir / "ch1-slot1" / "P2.json"
            self._mutate_json(p2, lambda value: value.update(selected_slot=1))
            p0 = run_dir / "ch1-slot1" / "P0.json"
            self._mutate_json(
                p0, lambda value: value.update(raw_snapshot_sha256="0" * 64),
            )
            (run_dir / "ch1-slot1" / "P1.raw.jast").unlink()
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(result["status"], "RESTORATION_FAILED")
        self.assertIn("p2_selected_slot_mismatch", result["reasons"])
        self.assertIn("p0_raw_snapshot_hash_mismatch", result["reasons"])
        self.assertIn("p1_raw_snapshot_missing", result["reasons"])

    def test_p1_must_invert_the_initial_enable_state(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            p1 = run_dir / "ch1-slot1" / "P1.json"
            self._mutate_json(p1, lambda value: value.update(enabled=True))
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("p1_enabled_must_invert_p0", result["reasons"])

    def test_p2_stable_field_mismatch_fails_restoration(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            p2 = run_dir / "ch1-slot1" / "P2.json"
            self._mutate_json(p2, lambda value: value.update(gain_1=36.5, main=0.25))
            p0 = run_dir / "ch1-slot1" / "P0.json"
            invalid_equal = {
                "processing_channel_1": True,
                "phantom_2": 0,
                "gain_2": [],
                "monitor_blend": None,
            }
            self._mutate_json(p0, lambda value: value.update(invalid_equal))
            self._mutate_json(p2, lambda value: value.update(invalid_equal))
            physical = run_dir / "ch1-slot1" / "PHYSICAL-RESTORATION.json"
            self._mutate_json(physical, lambda value: value.update(restored=False))
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("p2_stable_state_mismatch:gain_1", result["reasons"])
        self.assertIn("p2_stable_state_mismatch:main", result["reasons"])
        self.assertIn("physical_restoration_not_attested", result["reasons"])
        self.assertIn("p0_processing_channel_1_must_be_integer", result["reasons"])
        self.assertIn("p2_phantom_2_must_be_boolean", result["reasons"])
        self.assertIn("p0_gain_2_must_be_finite_numeric", result["reasons"])
        self.assertIn("p2_monitor_blend_must_be_finite_numeric", result["reasons"])

    def test_extra_toggle_or_event_fails_restoration(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            action_log = run_dir / "ch1-slot1" / "ACTION-LOG.jsonl"
            self._mutate_action_log(action_log, lambda events: events.append({
                "candidate": "ch1-slot1", "channel": 1, "id": "T3",
                "kind": "manual_preset_toggle", "press": "long", "monotonic_ns": 11,
            }))
            self._mutate_action_log(
                action_log,
                lambda events: events[2].update(frozen_mix_channel=4),
            )
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("action_log_event_sequence_mismatch", result["reasons"])
        self.assertIn("exactly_two_manual_toggles_required", result["reasons"])
        self.assertIn("audio_capture_frozen_channel_mismatch:S1", result["reasons"])

    def test_short_press_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            action_log = run_dir / "ch1-slot1" / "ACTION-LOG.jsonl"
            self._mutate_action_log(
                action_log,
                lambda events: events[3].update(press="short"),
            )
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("manual_toggle_must_be_long_press", result["reasons"])

    def test_mapped_write_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            action_log = run_dir / "ch1-slot1" / "ACTION-LOG.jsonl"
            self._mutate_action_log(
                action_log,
                lambda events: events[3].update(mapped_write=True),
            )
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("mapped_write_prohibited", result["reasons"])

    def test_missing_s4_fails_restoration(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            (run_dir / "ch1-slot1" / "S4.raw.wav").unlink()
            ab = run_dir / "ch1-slot1" / "AB.json"
            self._mutate_json(ab, lambda value: value.update(schema="wrong"))
            self._mutate_json(
                ab, lambda value: value["dry"][0].update(path="../outside.wav"),
            )
            self._mutate_json(
                ab, lambda value: value["dry"][1].update(sha256="0" * 64),
            )
            self._mutate_json(
                ab,
                lambda value: value["active"][0].update(
                    path="ch1-slot1/S1.mix4.mono.wav",
                ),
            )
            self._mutate_json(
                ab,
                lambda value: value["active"][1].update(
                    path="ch1-slot1/S2.mix3.mono.wav",
                ),
            )
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("required_input_missing:ch1-slot1/S4.raw.wav", result["reasons"])
        self.assertIn("ab_schema_invalid", result["reasons"])
        self.assertIn("ab_metric_path_unsafe:dry:1", result["reasons"])
        self.assertIn("ab_metric_hash_mismatch:dry:2", result["reasons"])
        self.assertIn("ab_metric_path_mismatch:active:1", result["reasons"])
        self.assertIn("ab_metric_role_binding_invalid", result["reasons"])

    def test_incomplete_or_mismatched_evidence_manifest_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            manifest = run_dir / "EVIDENCE-SHA256SUMS"
            rows = manifest.read_text(encoding="utf-8").splitlines()
            (run_dir / "unlisted.bin").write_bytes(b"not in the sealed manifest")
            manifest.write_text(
                "\n".join([
                    rows[0],
                    rows[0],
                    "0" * 64 + "  ../outside",
                    "0" * 64 + "  absent.json",
                    "0" * 64 + "  " + rows[1].split("  ", 1)[1],
                    *rows[2:],
                ]) + "\n",
                encoding="utf-8",
            )
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertTrue(any(reason.startswith("evidence_manifest_duplicate:")
                            for reason in result["reasons"]))
        self.assertTrue(any(reason.startswith("evidence_manifest_path_unsafe:")
                            for reason in result["reasons"]))
        self.assertIn("evidence_manifest_file_missing:absent.json", result["reasons"])
        self.assertTrue(any(reason.startswith("evidence_manifest_hash_mismatch:")
                            for reason in result["reasons"]))
        self.assertIn("evidence_manifest_omits_input:unlisted.bin", result["reasons"])

    def test_missing_physical_restoration_attestation_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(directory)
            physical = run_dir / "ch1-slot1" / "PHYSICAL-RESTORATION.json"
            self._mutate_json(physical, lambda value: value.pop("operator_attested"))
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("physical_restoration_not_attested", result["reasons"])

    def test_second_candidate_requires_a_restored_inconclusive_first_result(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(
                directory, candidate="ch2-slot1", enabled=True,
                outcome="INCONCLUSIVE", include_first_result=True,
            )
            completed, result = self._result(run_dir, "ch2-slot1")
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(result["status"], "RESTORED")
            first_result = run_dir / "ch1-slot1" / "RESTORATION.json"
            self._mutate_json(
                first_result,
                lambda value: value.update(reasons=["stale swapped bytes"]),
            )
            completed, result = self._result(run_dir, "ch2-slot1")
            self.assertEqual(completed.returncode, 2)
            self.assertIn(
                "evidence_manifest_hash_mismatch:ch1-slot1/RESTORATION.json",
                result["reasons"],
            )

        with tempfile.TemporaryDirectory() as directory:
            run_dir = _build_restoration_run(
                directory, candidate="ch2-slot1", enabled=True,
                outcome="INCONCLUSIVE", include_first_result=True,
            )
            nested = run_dir / "ch1-slot1" / "RESTORATION.json"
            root_result = run_dir / "RESTORATION.json"
            root_result.write_bytes(nested.read_bytes())
            nested.unlink()
            _refresh_evidence_manifest(run_dir)
            completed, result = self._result(run_dir, "ch2-slot1")
        self.assertEqual(completed.returncode, 2)
        self.assertIn(
            "second_candidate_requires_restored_inconclusive_first",
            result["reasons"],
        )
