import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "re" / "cp34_current_slot_survey.py"


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

    def test_wrong_wav_format_is_unavailable_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MAP.raw.wav"
            with wave.open(str(path), "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(b"\0\0\0\0" * 16)
            self._assert_unavailable(path, "wav_must_be_six_channel_s32_le_48khz_pcm")
