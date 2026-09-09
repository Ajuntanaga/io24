#!/usr/bin/env python3
"""Behavioral contracts for the CP34 hardware-free live-matrix gates."""

import json
import hashlib
import importlib.util
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "re", "cp34_live_matrix.py")
RATE = 48000
LIVE_SPEC = importlib.util.spec_from_file_location("cp34_live_matrix", SCRIPT)
LIVE = importlib.util.module_from_spec(LIVE_SPEC)
LIVE_SPEC.loader.exec_module(LIVE)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_impulses(path, echo_gain=0.0, tail_gains=(),
                    origins=(0.4, 1.1, 1.8, 2.5, 3.2), direct_gain=0.4):
    """Write a hand-derived 32-bit mono fixture; no production helper used."""
    frames = [0.0] * (RATE * 4)
    for second in origins:
        origin = int(second * RATE)
        frames[origin] = direct_gain
        if echo_gain:
            frames[origin + int(0.15 * RATE)] += direct_gain * echo_gain
        for offset, gain in tail_gains:
            frames[origin + int(offset * RATE)] += direct_gain * gain

    encoded = bytearray()
    for sample in frames:
        encoded += struct.pack("<i", round(sample * 2147483647.0))
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(4)
        handle.setframerate(RATE)
        handle.writeframes(bytes(encoded))


def _valid_ledger():
    shadow_hash = "a" * 64
    return {
        "schema": "cp34-restoration-ledger-v1",
        "run_id": "cp34-fixture-run",
        "device_serial": "TEST-SERIAL",
        "target_title": "Slap Echo",
        "shadow": {"sha256": shadow_hash, "current_attested": True},
        "actions": [
            {
                "id": "mixa-fx-return",
                "kind": "mapped_write",
                "method": "set_send_db",
                "forward": {
                    "source": "fxreturn/ch1", "bus": "mixa", "gain_db": 0.0,
                },
                "inverse": {
                    "source": "fxreturn/ch1", "bus": "mixa", "gain_db": -12.0,
                },
                "write_only": True,
                "baseline_source": "shadow:" + shadow_hash,
            },
            {
                "id": "reverb-positive-control",
                "kind": "mapped_write",
                "method": "set_reverb",
                "forward": {
                    "on": True, "size": 0.9, "mix": 1.0,
                    "hp_freq": 0.0, "predelay": 0.05,
                },
                "inverse": {
                    "on": False, "size": 0.1, "mix": 0.0,
                    "hp_freq": 200.0, "predelay": 0.02,
                },
                "write_only": True,
                "baseline_source": "shadow:" + shadow_hash,
            },
            {
                "id": "front-panel-enable",
                "kind": "manual_front_panel",
                "forward": "long press channel 1 Preset to enable Slap Echo",
                "inverse": "long press channel 1 Preset to restore bypass",
                "write_only": False,
                "baseline_source": "read_params and device screen",
            },
        ],
    }


class AudioAnalyzerTests(unittest.TestCase):
    def test_generate_stimulus_writes_the_fixed_safe_impulse_train(self):
        """Wrong level, timing, rate, or format must change this fixture."""
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "slap-impulses.wav")
            result = subprocess.run(
                [sys.executable, SCRIPT, "generate-stimulus", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with wave.open(path, "rb") as handle:
                channels = handle.getnchannels()
                width = handle.getsampwidth()
                rate = handle.getframerate()
                count = handle.getnframes()
                samples = struct.unpack("<%di" % count,
                                        handle.readframes(count))
            with open(path, "rb") as handle:
                expected_hash = hashlib.sha256(handle.read()).hexdigest()

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "GENERATED")
        self.assertEqual(report["sha256"], expected_hash)
        self.assertEqual((channels, width, rate, count), (1, 4, 48000, 192000))
        nonzero = [(index, value) for index, value in enumerate(samples) if value]
        self.assertEqual(
            nonzero,
            [(19200, 270352173), (52800, 270352173),
             (86400, 270352173), (120000, 270352173),
             (153600, 270352173)],
        )

    def test_generate_stimulus_refuses_to_overwrite_evidence(self):
        """Regeneration must not replace a file that may already be pinned."""
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "existing.wav")
            with open(path, "wb") as handle:
                handle.write(b"do not overwrite")
            result = subprocess.run(
                [sys.executable, SCRIPT, "generate-stimulus", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            with open(path, "rb") as handle:
                after = handle.read()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(after, b"do not overwrite")
        report = json.loads(result.stdout)
        self.assertIn("output already exists", report["reasons"])

    def test_analyze_accepts_repeatable_slap_echo_with_reverb_positive_control(self):
        """Wrong delay/delta logic must fail this known 150 ms A/B fixture."""
        with tempfile.TemporaryDirectory() as temporary:
            dry1 = os.path.join(temporary, "dry-1.wav")
            dry2 = os.path.join(temporary, "dry-2.wav")
            active1 = os.path.join(temporary, "active-1.wav")
            active2 = os.path.join(temporary, "active-2.wav")
            reverb = os.path.join(temporary, "reverb.wav")
            _write_impulses(dry1)
            _write_impulses(dry2)
            _write_impulses(active1, echo_gain=0.5)
            _write_impulses(active2, echo_gain=0.5)
            _write_impulses(
                reverb,
                tail_gains=((0.03, 0.7), (0.06, 0.7),
                            (0.09, 0.7), (0.12, 0.7)),
            )

            result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT,
                    "analyze",
                    "--target-title", "Slap Echo",
                    "--audible-attested",
                    "--dry", dry1,
                    "--dry", dry2,
                    "--active", active1,
                    "--active", active2,
                    "--reverb", reverb,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "PASS")
        self.assertGreaterEqual(report["reverb_delta_db"], 3.0)
        self.assertEqual(len(report["dry"]), 2)
        self.assertEqual(len(report["active"]), 2)
        self.assertTrue(all(row["echo_delta_db"] >= 6.0
                            for row in report["active"]))

    def test_analyze_hashes_every_input_evidence_file(self):
        """Dropping a source hash must make the evidence report incomplete."""
        with tempfile.TemporaryDirectory() as temporary:
            paths = {
                "dry-1": os.path.join(temporary, "dry-1.wav"),
                "dry-2": os.path.join(temporary, "dry-2.wav"),
                "active-1": os.path.join(temporary, "active-1.wav"),
                "active-2": os.path.join(temporary, "active-2.wav"),
                "reverb": os.path.join(temporary, "reverb.wav"),
            }
            _write_impulses(paths["dry-1"])
            _write_impulses(paths["dry-2"])
            _write_impulses(paths["active-1"], echo_gain=0.5)
            _write_impulses(paths["active-2"], echo_gain=0.5)
            _write_impulses(
                paths["reverb"],
                tail_gains=((0.03, 0.7), (0.06, 0.7),
                            (0.09, 0.7), (0.12, 0.7)),
            )
            result = subprocess.run(
                [
                    sys.executable, SCRIPT, "analyze",
                    "--target-title", "Slap Echo",
                    "--audible-attested",
                    "--dry", paths["dry-1"], "--dry", paths["dry-2"],
                    "--active", paths["active-1"],
                    "--active", paths["active-2"],
                    "--reverb", paths["reverb"],
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            expected = {path: _sha256_file(path) for path in paths.values()}

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        rows = report["dry"] + report["active"] + [report["reverb"]]
        self.assertEqual({row["path"]: row["sha256"] for row in rows}, expected)

    def test_analyze_rejects_a_different_impulse_train(self):
        """An extra active impulse must not masquerade as a repeatable A/B."""
        with tempfile.TemporaryDirectory() as temporary:
            dry1 = os.path.join(temporary, "dry-1.wav")
            dry2 = os.path.join(temporary, "dry-2.wav")
            active1 = os.path.join(temporary, "active-1.wav")
            active2 = os.path.join(temporary, "active-2.wav")
            reverb = os.path.join(temporary, "reverb.wav")
            _write_impulses(dry1)
            _write_impulses(dry2)
            _write_impulses(active1, echo_gain=0.5)
            _write_impulses(
                active2,
                echo_gain=0.5,
                origins=(0.25, 0.8, 1.35, 1.9, 2.45, 3.0),
            )
            _write_impulses(
                reverb,
                tail_gains=((0.03, 0.7), (0.06, 0.7),
                            (0.09, 0.7), (0.12, 0.7)),
            )
            result = subprocess.run(
                [
                    sys.executable, SCRIPT, "analyze",
                    "--target-title", "Slap Echo",
                    "--audible-attested",
                    "--dry", dry1, "--dry", dry2,
                    "--active", active1, "--active", active2,
                    "--reverb", reverb,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("impulse counts differ across captures", report["reasons"])

    def test_analyze_rejects_changed_relative_impulse_timing(self):
        """Equal counts with a different stimulus cadence are not the same A/B."""
        with tempfile.TemporaryDirectory() as temporary:
            dry1 = os.path.join(temporary, "dry-1.wav")
            dry2 = os.path.join(temporary, "dry-2.wav")
            active1 = os.path.join(temporary, "active-1.wav")
            active2 = os.path.join(temporary, "active-2.wav")
            reverb = os.path.join(temporary, "reverb.wav")
            _write_impulses(dry1)
            _write_impulses(dry2)
            _write_impulses(active1, echo_gain=0.5)
            _write_impulses(
                active2,
                echo_gain=0.5,
                origins=(0.3, 0.9, 1.5, 2.1, 2.7),
            )
            _write_impulses(
                reverb,
                tail_gains=((0.03, 0.7), (0.06, 0.7),
                            (0.09, 0.7), (0.12, 0.7)),
            )
            result = subprocess.run(
                [
                    sys.executable, SCRIPT, "analyze",
                    "--target-title", "Slap Echo",
                    "--audible-attested",
                    "--dry", dry1, "--dry", dry2,
                    "--active", active1, "--active", active2,
                    "--reverb", reverb,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("impulse timing differs across captures", report["reasons"])

    def test_analyze_requires_audible_operator_attestation(self):
        """Signal metrics alone must not satisfy an explicitly audible outcome."""
        with tempfile.TemporaryDirectory() as temporary:
            dry1 = os.path.join(temporary, "dry-1.wav")
            dry2 = os.path.join(temporary, "dry-2.wav")
            active1 = os.path.join(temporary, "active-1.wav")
            active2 = os.path.join(temporary, "active-2.wav")
            reverb = os.path.join(temporary, "reverb.wav")
            _write_impulses(dry1)
            _write_impulses(dry2)
            _write_impulses(active1, echo_gain=0.5)
            _write_impulses(active2, echo_gain=0.5)
            _write_impulses(
                reverb,
                tail_gains=((0.03, 0.7), (0.06, 0.7),
                            (0.09, 0.7), (0.12, 0.7)),
            )
            result = subprocess.run(
                [
                    sys.executable, SCRIPT, "analyze",
                    "--target-title", "Slap Echo",
                    "--dry", dry1, "--dry", dry2,
                    "--active", active1, "--active", active2,
                    "--reverb", reverb,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("audible result was not attested", report["reasons"])

    def test_analyze_rejects_a_louder_dry_signal_as_reverb_control(self):
        """A level jump without a late tail is not a working DSP control."""
        with tempfile.TemporaryDirectory() as temporary:
            dry1 = os.path.join(temporary, "dry-1.wav")
            dry2 = os.path.join(temporary, "dry-2.wav")
            active1 = os.path.join(temporary, "active-1.wav")
            active2 = os.path.join(temporary, "active-2.wav")
            fake_reverb = os.path.join(temporary, "fake-reverb.wav")
            _write_impulses(dry1)
            _write_impulses(dry2)
            _write_impulses(active1, echo_gain=0.5)
            _write_impulses(active2, echo_gain=0.5)
            _write_impulses(fake_reverb, direct_gain=0.8)
            result = subprocess.run(
                [
                    sys.executable, SCRIPT, "analyze",
                    "--target-title", "Slap Echo",
                    "--audible-attested",
                    "--dry", dry1, "--dry", dry2,
                    "--active", active1, "--active", active2,
                    "--reverb", fake_reverb,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "reverb positive control has no late energy",
            report["reasons"],
        )


class SlotSurveyAnalyzerTests(unittest.TestCase):
    def test_analyze_slot_scopes_repeat_signature_without_claiming_title_or_live_readiness(self):
        """A 150 ms A/B signature is evidence, not preset identity or live authority."""
        with tempfile.TemporaryDirectory() as temporary:
            dry1 = os.path.join(temporary, "dry-1.wav")
            dry2 = os.path.join(temporary, "dry-2.wav")
            active1 = os.path.join(temporary, "active-1.wav")
            active2 = os.path.join(temporary, "active-2.wav")
            _write_impulses(dry1)
            _write_impulses(dry2)
            _write_impulses(active1, echo_gain=0.5)
            _write_impulses(active2, echo_gain=0.5)

            self.assertTrue(hasattr(LIVE, "analyze_slot_bytes"))
            byte_report = LIVE.analyze_slot_bytes(
                [
                    ("evidence/dry-1.wav", Path(dry1).read_bytes()),
                    ("evidence/dry-2.wav", Path(dry2).read_bytes()),
                ],
                [
                    ("evidence/active-1.wav", Path(active1).read_bytes()),
                    ("evidence/active-2.wav", Path(active2).read_bytes()),
                ],
                "ch1-slot1",
                audible_attested=True,
            )

            result = subprocess.run(
                [
                    sys.executable, SCRIPT, "analyze-slot",
                    "--candidate", "ch1-slot1",
                    "--audible-attested",
                    "--dry", dry1, "--dry", dry2,
                    "--active", active1, "--active", active2,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "SIGNATURE_PRESENT")
        self.assertEqual(report["classification"], "REPEAT_150MS_SIGNATURE")
        self.assertEqual(report["candidate"], "ch1-slot1")
        self.assertEqual(report["model_identity"], "UNRESOLVED")
        self.assertFalse(report["title_verified"])
        self.assertFalse(report["live_ready"])
        self.assertFalse(report["restoration_verified"])
        self.assertEqual(byte_report["status"], "SIGNATURE_PRESENT")
        self.assertEqual(
            [row["path"] for row in byte_report["dry"]],
            ["evidence/dry-1.wav", "evidence/dry-2.wav"],
        )
        self.assertEqual(
            [row["path"] for row in byte_report["active"]],
            ["evidence/active-1.wav", "evidence/active-2.wav"],
        )

    def test_analyze_slot_keeps_a_non_specific_late_tail_inconclusive(self):
        """A late tail alone cannot identify either its source or the loaded model."""
        with tempfile.TemporaryDirectory() as temporary:
            dry1 = os.path.join(temporary, "dry-1.wav")
            dry2 = os.path.join(temporary, "dry-2.wav")
            active1 = os.path.join(temporary, "active-1.wav")
            active2 = os.path.join(temporary, "active-2.wav")
            tail = ((0.03, 0.5), (0.06, 0.4), (0.09, 0.3), (0.12, 0.2))
            _write_impulses(dry1)
            _write_impulses(dry2)
            _write_impulses(active1, tail_gains=tail)
            _write_impulses(active2, tail_gains=tail)

            result = subprocess.run(
                [
                    sys.executable, SCRIPT, "analyze-slot",
                    "--candidate", "ch2-slot2",
                    "--audible-attested",
                    "--dry", dry1, "--dry", dry2,
                    "--active", active1, "--active", active2,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "INCONCLUSIVE")
        self.assertEqual(report["classification"], "NON_SPECIFIC_LATE_TAIL")
        self.assertTrue(report["reverb_like_observed"])
        self.assertIn(
            "repeatable late tail observed; source and loaded effect model are unresolved",
            report["reasons"],
        )

    def test_analyze_slot_does_not_classify_a_tail_when_capture_cadence_differs(self):
        """A tail with a changed impulse train is not repeatable A/B evidence."""
        with tempfile.TemporaryDirectory() as temporary:
            dry1 = os.path.join(temporary, "dry-1.wav")
            dry2 = os.path.join(temporary, "dry-2.wav")
            active1 = os.path.join(temporary, "active-1.wav")
            active2 = os.path.join(temporary, "active-2.wav")
            tail = ((0.03, 0.5), (0.06, 0.4), (0.09, 0.3), (0.12, 0.2))
            _write_impulses(dry1)
            _write_impulses(dry2)
            _write_impulses(active1, tail_gains=tail)
            _write_impulses(
                active2,
                tail_gains=tail,
                origins=(0.41, 1.12, 1.83, 2.54, 3.25),
            )

            result = subprocess.run(
                [
                    sys.executable, SCRIPT, "analyze-slot",
                    "--candidate", "ch1-slot2",
                    "--audible-attested",
                    "--dry", dry1, "--dry", dry2,
                    "--active", active1, "--active", active2,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["classification"], "NO_DISTINCTIVE_SIGNATURE")
        self.assertFalse(report["reverb_like_observed"])
        self.assertIn("impulse timing differs across captures", report["reasons"])


class RestorationLedgerTests(unittest.TestCase):
    def test_validate_ledger_rejects_a_non_object_root(self):
        """Malformed JSON structure must close the gate without a traceback."""
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump([], handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("ledger root must be an object", report["reasons"])

    def test_validate_ledger_rejects_a_non_object_action(self):
        """One malformed row must invalidate the ledger without a traceback."""
        ledger = _valid_ledger()
        ledger["actions"] = ["not an action"]
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("action #1 must be an object", report["reasons"])

    def test_validate_ledger_accepts_narrow_actions_with_predeclared_inverses(self):
        """Rejecting this fixture would block a fully reversible approved run."""
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(_valid_ledger(), handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            with open(path, "rb") as handle:
                expected_hash = hashlib.sha256(handle.read()).hexdigest()

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "VALID")
        self.assertEqual(report["actions"], 3)
        self.assertEqual(report["sha256"], expected_hash)

    def test_validate_ledger_rejects_an_action_without_an_inverse(self):
        """Removing one inverse must close the live gate before any write."""
        ledger = _valid_ledger()
        del ledger["actions"][0]["inverse"]
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "INVALID")
        self.assertIn("action mixa-fx-return has no inverse", report["reasons"])

    def test_validate_ledger_rejects_direct_voice_fx_or_preset_writes(self):
        """A direct block-201 or slot write must never enter the approved set."""
        ledger = _valid_ledger()
        ledger["actions"][0]["method"] = "set_fx"
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "action mixa-fx-return uses prohibited method set_fx",
            report["reasons"],
        )

    def test_validate_ledger_rejects_write_only_actions_with_stale_shadow(self):
        """A stale mirror cannot supply restoration values for device writes."""
        ledger = _valid_ledger()
        ledger["shadow"]["current_attested"] = False
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "write-only actions require a current-attested shadow",
            report["reasons"],
        )

    def test_validate_ledger_requires_boolean_shadow_attestation(self):
        """A truthy string is not an explicit current-state attestation."""
        ledger = _valid_ledger()
        ledger["shadow"]["current_attested"] = "yes"
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "write-only actions require a current-attested shadow",
            report["reasons"],
        )

    def test_validate_ledger_rejects_wrong_shadow_provenance(self):
        """An inverse copied from a different mirror hash is not restoration."""
        ledger = _valid_ledger()
        ledger["actions"][0]["baseline_source"] = "shadow:" + "b" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "action mixa-fx-return baseline does not match the pinned shadow",
            report["reasons"],
        )

    def test_validate_ledger_rejects_duplicate_action_ids(self):
        """Duplicate IDs make reverse-order restoration ambiguous."""
        ledger = _valid_ledger()
        ledger["actions"][1]["id"] = ledger["actions"][0]["id"]
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("duplicate action id mixa-fx-return", report["reasons"])

    def test_validate_ledger_requires_run_and_device_identity(self):
        """A reversible plan for an unnamed device is not target-specific."""
        ledger = _valid_ledger()
        del ledger["run_id"]
        del ledger["device_serial"]
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("run_id is required", report["reasons"])
        self.assertIn("device_serial is required", report["reasons"])

    def test_validate_ledger_requires_a_real_shadow_hash(self):
        """A label that is not a SHA-256 digest cannot pin restoration state."""
        ledger = _valid_ledger()
        ledger["shadow"]["sha256"] = "not-a-hash"
        for action in ledger["actions"]:
            if action["write_only"]:
                action["baseline_source"] = "shadow:not-a-hash"
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("shadow.sha256 must be 64 lowercase hex digits",
                      report["reasons"])

    def test_validate_ledger_rejects_an_unknown_action_kind(self):
        """A shell or free-form action must not bypass the narrow allowlist."""
        ledger = _valid_ledger()
        ledger["actions"][0]["kind"] = "shell"
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("action mixa-fx-return has unknown kind shell",
                      report["reasons"])

    def test_validate_ledger_requires_structured_mapped_write_arguments(self):
        """Free-form write text cannot be replayed as an exact inverse call."""
        ledger = _valid_ledger()
        ledger["actions"][0]["forward"] = "turn the FX return up"
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "mapped action mixa-fx-return needs object forward and inverse",
            report["reasons"],
        )

    def test_validate_ledger_rejects_unexpected_write_arguments(self):
        """An allowlisted method must not smuggle an unsafe or extra argument."""
        ledger = _valid_ledger()
        ledger["actions"][0]["forward"]["unsafe"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "action mixa-fx-return forward has unexpected keys: unsafe",
            report["reasons"],
        )

    def test_validate_ledger_requires_all_exact_inverse_arguments(self):
        """A partial inverse call cannot restore the addressed mixer value."""
        ledger = _valid_ledger()
        del ledger["actions"][0]["inverse"]["bus"]
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "action mixa-fx-return inverse is missing keys: bus",
            report["reasons"],
        )

    def test_validate_ledger_inverse_must_address_the_same_control(self):
        """Restoring a different source leaves the forward write unrestored."""
        ledger = _valid_ledger()
        ledger["actions"][0]["inverse"]["source"] = "line/ch1"
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "action mixa-fx-return inverse addresses a different control",
            report["reasons"],
        )

    def test_validate_ledger_limits_mixer_writes_to_mix_a(self):
        """The positive-control route must not touch Main or Mix B."""
        ledger = _valid_ledger()
        ledger["actions"][0]["forward"]["bus"] = "main"
        ledger["actions"][0]["inverse"]["bus"] = "main"
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("action mixa-fx-return must use bus mixa",
                      report["reasons"])

    def test_validate_ledger_rejects_clamped_mixer_levels(self):
        """An out-of-range level would not be the exact forward value recorded."""
        ledger = _valid_ledger()
        ledger["actions"][0]["forward"]["gain_db"] = 99.0
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("action mixa-fx-return forward has invalid gain_db",
                      report["reasons"])

    def test_validate_ledger_accepts_declared_mixer_clamp_probe(self):
        """A clamp probe pins the requested and expected wire values."""
        ledger = _valid_ledger()
        action = ledger["actions"][0]
        action["kind"] = "clamp_probe"
        action["forward"]["gain_db"] = 20.0
        action["expected_wire_db"] = 10.0
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["status"], "VALID")

    def test_validate_ledger_rejects_wrong_clamp_probe_wire_value(self):
        ledger = _valid_ledger()
        action = ledger["actions"][0]
        action["kind"] = "clamp_probe"
        action["forward"]["gain_db"] = -200.0
        action["expected_wire_db"] = -145.0
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(
            "action mixa-fx-return clamp expected_wire_db does not match",
            json.loads(result.stdout)["reasons"],
        )

    def test_validate_ledger_rejects_clamped_gain_values(self):
        """A mapped readable write still needs an in-range exact value."""
        ledger = _valid_ledger()
        ledger["actions"].append({
            "id": "input-gain",
            "kind": "mapped_write",
            "method": "set_gain",
            "forward": {"channel": 1, "db": 99.0},
            "inverse": {"channel": 1, "db": 5.0},
            "write_only": False,
            "baseline_source": "read_params",
        })
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("action input-gain forward has invalid db",
                      report["reasons"])

    def test_validate_ledger_rejects_clamped_fx_mix_values(self):
        """The dry/wet route cannot depend on driver clamping."""
        ledger = _valid_ledger()
        ledger["actions"].append({
            "id": "channel-fx-mix",
            "kind": "mapped_write",
            "method": "set_fx_mix",
            "forward": {"channel": 1, "value": 2.0},
            "inverse": {"channel": 1, "value": 0.25},
            "write_only": False,
            "baseline_source": "read_params",
        })
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("action channel-fx-mix forward has invalid value",
                      report["reasons"])

    def test_validate_ledger_pins_the_reverb_positive_control(self):
        """Changing the control parameters would invalidate its fixed threshold."""
        ledger = _valid_ledger()
        ledger["actions"][1]["forward"]["mix"] = 0.5
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "reverb positive control parameters do not match the matrix",
            report["reasons"],
        )

    def test_validate_ledger_rejects_out_of_range_reverb_inverse(self):
        """A clamped inverse value would not restore the recorded baseline."""
        ledger = _valid_ledger()
        ledger["actions"][1]["inverse"]["mix"] = 99.0
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "action reverb-positive-control inverse has invalid mix",
            report["reasons"],
        )

    def test_validate_ledger_requires_exactly_one_reverb_control(self):
        """The matrix is ineligible without its device-DSP positive control."""
        ledger = _valid_ledger()
        del ledger["actions"][1]
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("ledger requires exactly one reverb positive control",
                      report["reasons"])

    def test_validate_ledger_requires_the_front_panel_toggle(self):
        """A run with no hardware preset action cannot answer the matrix question."""
        ledger = _valid_ledger()
        ledger["actions"] = ledger["actions"][:2]
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("ledger requires one front-panel-enable action",
                      report["reasons"])

    def test_validate_ledger_requires_explicit_manual_inverse_text(self):
        """A non-text manual inverse cannot guide physical restoration."""
        ledger = _valid_ledger()
        ledger["actions"][2]["inverse"] = {"press": "later"}
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "manual action front-panel-enable needs text forward and inverse",
            report["reasons"],
        )

    def test_validate_ledger_cannot_mislabel_reverb_as_readable(self):
        """A false write_only flag must not bypass shadow provenance."""
        ledger = _valid_ledger()
        ledger["actions"][1]["write_only"] = False
        ledger["actions"][1]["baseline_source"] = "operator guess"
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "ledger.json")
            with open(path, "w") as handle:
                json.dump(ledger, handle)
            result = subprocess.run(
                [sys.executable, SCRIPT, "validate-ledger", path],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "action reverb-positive-control method set_reverb is write-only",
            report["reasons"],
        )


if __name__ == "__main__":
    unittest.main()
