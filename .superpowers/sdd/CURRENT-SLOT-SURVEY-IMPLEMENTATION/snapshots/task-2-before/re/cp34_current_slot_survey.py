#!/usr/bin/env python3
"""Offline validator for CP34 current-slot survey plans."""

import hashlib
import json
import re
import sys
from pathlib import PurePosixPath


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
        return raw, json.loads(raw.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw, None, "plan_invalid_json"


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


def validate_plan(path: str) -> dict:
    """Validate one CP34 survey-plan JSON object without touching hardware."""
    raw, plan, load_error = _load(path)
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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "validate-plan":
        result = {"schema": "cp34-current-slot-survey-plan-validation-v1", "status": "INVALID", "plan_sha256": hashlib.sha256(b"").hexdigest(), "reasons": ["usage: validate-plan PLAN.json"], "candidates": []}
    else:
        result = validate_plan(argv[1])
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "VALID" else 2


if __name__ == "__main__":
    sys.exit(main())
