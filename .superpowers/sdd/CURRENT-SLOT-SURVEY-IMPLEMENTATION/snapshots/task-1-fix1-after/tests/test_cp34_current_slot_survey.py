import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "re" / "cp34_current_slot_survey.py"


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
