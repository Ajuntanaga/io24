#!/usr/bin/env python3
"""Hardware-free contracts for the block-201 shared-return probe.

The point of these tests is that the verdict is trustworthy before the probe
ever touches the unit: a synthetic device that really echoes into the gaps must
read as processing, an inert one must read as no effect, and neither answer may
come out of a run whose reverb control put no tail in the gap.
"""

import importlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _directory in (ROOT, ROOT / "re"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

probe = importlib.import_module("io24_fx_shared_return_probe")


RATE = probe.RATE


def _write_capture(path, mono, rate=RATE, channels=probe.CHANNELS):
    """Put one mono signal on the Mix A legs and a noise floor on the rest."""
    frames = np.zeros((mono.size, channels), dtype=np.float64)
    rng = np.random.default_rng(7)
    for index in range(channels):
        frames[:, index] = rng.normal(0.0, 1e-6, mono.size)
    for index in probe.MIX_A_CHANNELS:
        frames[:, index] += mono
    pcm = np.rint(np.clip(frames, -1.0, 1.0) * (2 ** 31 - 1)).astype("<i4")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(4)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    return path


def _stimulus_mono(tmpdir):
    """The probe's own stimulus, as the device would receive it."""
    path = probe.build_stimulus(Path(tmpdir) / "stimulus.wav")
    _rate, frames = probe.read_capture(path)
    return frames[:, 0], path


class StimulusTests(unittest.TestCase):
    def test_the_stimulus_is_gated_and_its_bursts_are_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            mono, _path = _stimulus_mono(tmp)
        bursts, score = probe.align_bursts(mono)
        self.assertEqual(len(bursts), probe.CYCLES)
        self.assertGreater(score, 0.0)
        for start, stop in bursts:
            self.assertAlmostEqual((stop - start) / RATE,
                                   probe.BURST_SECONDS, delta=0.01)
        gaps = probe.gap_slices(mono, bursts)
        self.assertGreater(gaps.size, 0)
        # The gaps of the stimulus itself are silent: that is the whole basis
        # of the measurement.
        self.assertLess(probe.rms_dbfs(gaps), -120.0)

    def test_a_tail_in_the_gaps_does_not_move_the_burst_windows(self):
        """The regression that made the delay unreadable: an envelope threshold
        absorbs an effect's repeats into a longer "burst" and pushes the tap
        windows into the next cycle. The windows come from the known gate."""
        with tempfile.TemporaryDirectory() as tmp:
            mono, _path = _stimulus_mono(tmp)
        clean, _score = probe.align_bursts(mono)
        tailed = mono.copy()
        for tap in (1, 2, 3):
            lag = int(round(tap * 0.25 * RATE))
            tailed[lag:] += mono[:-lag] * (0.7 ** tap)
        filled, _score2 = probe.align_bursts(tailed)
        self.assertEqual(len(filled), len(clean))
        for (start, stop), (other_start, other_stop) in zip(clean, filled):
            self.assertEqual((start, stop), (other_start, other_stop))

    def test_the_stimulus_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = probe.build_stimulus(Path(tmp) / "a.wav").read_bytes()
            second = probe.build_stimulus(Path(tmp) / "b.wav").read_bytes()
        self.assertEqual(first, second)

    def test_rebuilding_over_an_existing_stimulus_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = probe.build_stimulus(Path(tmp) / "s.wav")
            with self.assertRaises(probe.FxReturnProbeError):
                probe.build_stimulus(path)


class SynthDevice:
    """A device whose audible behaviour is decided by the writes it receives."""

    def __init__(self, mono, block201_processes=True, reverb_works=True):
        self.mono = mono
        self.block201_processes = block201_processes
        self.reverb_works = reverb_works
        self.calls = []
        self.fx = None
        self.reverb_on = False
        self.transport_log = []

    def set_send_db(self, source, bus, gain_db):
        self.calls.append(("set_send_db", source, bus, gain_db))

    def set_send_assigned(self, source, bus, on=True):
        self.calls.append(("set_send_assigned", source, bus, on))

    def set_reverb(self, on=True, **kwargs):
        self.calls.append(("set_reverb", on))
        self.reverb_on = bool(on)

    def reverb_off(self):
        self.calls.append(("reverb_off",))
        self.reverb_on = False

    def set_fx(self, model, **kwargs):
        self.calls.append(("set_fx", model, kwargs.get("on")))
        self.fx = (model, dict(kwargs)) if kwargs.get("on") else None

    def _echo(self, mono, lag_s, gain, repeats=3):
        out = mono.copy()
        for tap in range(1, repeats + 1):
            lag = int(round(tap * lag_s * RATE))
            if lag >= mono.size:
                break
            out[lag:] += mono[:-lag] * (gain ** tap)
        return out

    def render(self):
        mono = self.mono.copy()
        if self.fx is not None and self.block201_processes:
            model, kwargs = self.fx
            if model == "ringmod":
                t = np.arange(mono.size) / float(RATE)
                mono = mono * np.cos(
                    2.0 * math.pi * kwargs["carrier_hz"] * t)
            elif model == "detuner":
                # A crude shift: resample the burst content down in pitch.
                shifted = np.interp(
                    np.arange(mono.size) * probe.DETUNE_RATIO,
                    np.arange(mono.size), mono)
                mono = mono + shifted
            elif model == "delay":
                mono = self._echo(mono, kwargs["time_s"], 0.7)
            elif model == "transformer":
                mono = mono * 2.0
        if self.reverb_on and self.reverb_works:
            # A tail, which is what a reverb puts into a gap.
            mono = self._echo(mono, 0.013, 0.85, repeats=60)
        return mono


def _run(device, tmpdir, stimulus):
    def capture(label, output_dir, _stimulus, **_kwargs):
        path = Path(output_dir) / ("%s.wav" % label)
        return _write_capture(path, device.render())

    stages, trials = probe.run_sequence(
        device, tmpdir, stimulus, capture=capture, settle=lambda _s: None)
    return probe.classify_run(stages, trials), stages, trials


class SequenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.mono, cls.stimulus = _stimulus_mono(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_a_processing_device_reads_as_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            device = SynthDevice(self.mono)
            verdict, _stages, _trials = _run(device, Path(tmp), self.stimulus)
        self.assertEqual(
            verdict["status"],
            "BLOCK201_PROCESSING_DETECTED_ON_THE_SHARED_RETURN")
        self.assertTrue(verdict["run_valid"])
        self.assertTrue(verdict["reverb_control"]["fired"])
        for name in ("ringmod_146p85", "ringmod_313p70", "detuner", "delay"):
            self.assertTrue(verdict["models"][name]["processing_detected"],
                            "%s should have been detected" % name)

    def test_the_gated_stimulus_makes_the_delay_read_at_its_own_taps(self):
        """What the gaps are for: each repeat lands in silence, so a rise
        there is a copy of the burst arriving late and can be nothing else."""
        with tempfile.TemporaryDirectory() as tmp:
            device = SynthDevice(self.mono)
            verdict, _stages, _trials = _run(device, Path(tmp), self.stimulus)
        taps = verdict["models"]["delay"]["tests"]["repeat_taps"]
        self.assertTrue(taps["detected"])
        self.assertGreaterEqual(taps["max_rise_db"], probe.TAP_MIN_RISE_DB)
        for tap in ("1", "2"):
            self.assertGreater(taps["taps"][tap]["delta_db"],
                               probe.TAP_MIN_RISE_DB)
        self.assertIn("repeat_taps",
                      verdict["models"]["delay"]["fired_tests"])

    def test_an_inert_block_reads_as_no_effect_in_a_valid_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            device = SynthDevice(self.mono, block201_processes=False)
            verdict, _stages, _trials = _run(device, Path(tmp), self.stimulus)
        self.assertEqual(verdict["status"],
                         "NO_BLOCK201_EFFECT_ON_THE_SHARED_RETURN")
        self.assertTrue(verdict["run_valid"])
        self.assertTrue(verdict["reverb_control"]["fired"])
        self.assertEqual(verdict["inconclusive_models"], [])

    def test_a_dead_control_invalidates_the_run_rather_than_proving_a_null(self):
        """The failure this probe exists to prevent: reporting a null taken on
        a path that was never carrying anything."""
        with tempfile.TemporaryDirectory() as tmp:
            device = SynthDevice(self.mono, block201_processes=False,
                                 reverb_works=False)
            verdict, _stages, _trials = _run(device, Path(tmp), self.stimulus)
        self.assertEqual(verdict["status"],
                         "INVALID_REVERB_CONTROL_PUT_NO_TAIL_IN_THE_GAP")
        self.assertFalse(verdict["run_valid"])

    def test_the_sequence_opens_the_return_before_arming_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            device = SynthDevice(self.mono)
            _run(device, Path(tmp), self.stimulus)
        names = [call[0] for call in device.calls]
        self.assertEqual(names[:2], ["set_send_db", "set_send_assigned"])
        self.assertLess(names.index("set_send_assigned"),
                        names.index("set_fx"))

    def test_the_sequence_writes_nothing_that_feeds_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            device = SynthDevice(self.mono)
            _run(device, Path(tmp), self.stimulus)
        for call in device.calls:
            if call[0] in ("set_send_db", "set_send_assigned"):
                self.assertEqual(call[1], probe.RETURN_SOURCE)
                self.assertEqual(call[2], probe.RETURN_BUS)
        names = [call[0] for call in device.calls]
        for forbidden in ("set_fx_mix", "set_gain", "set_main_volume",
                          "set_processing_channel", "set_preset_slot"):
            self.assertNotIn(forbidden, names)

    def test_every_armed_model_is_turned_off_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            device = SynthDevice(self.mono)
            _run(device, Path(tmp), self.stimulus)
        armed = [call for call in device.calls if call[0] == "set_fx"]
        self.assertTrue(armed)
        self.assertEqual(len([c for c in armed if c[2]]),
                         len([c for c in armed if not c[2]]))
        self.assertIsNone(device.fx)
        self.assertFalse(device.reverb_on)


class AnalysisTests(unittest.TestCase):
    def test_a_level_change_is_not_mistaken_for_ring_modulation(self):
        """The discriminator has to be spectral: a gain change lifts the guard
        bands with everything else and must not qualify."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mono, _path = _stimulus_mono(tmp)
            t = np.arange(mono.size) / float(RATE)
            off = probe.analyse_stage(_write_capture(tmp / "off.wav", mono))
            on = probe.analyse_stage(_write_capture(
                tmp / "on.wav", mono * np.cos(2.0 * math.pi * 146.85 * t)))
            louder = probe.analyse_stage(
                _write_capture(tmp / "loud.wav", mono * 4.0))
            partial = off["dominant_partial"]["hz"]
            real = probe.classify_sidebands(off, on, partial, 146.85)
            fake = probe.classify_sidebands(off, louder, partial, 146.85)
        self.assertTrue(real["detected"])
        self.assertLessEqual(real["max_guard_rise_db"], probe.GUARD_MAX_DB)
        self.assertFalse(fake["detected"])

    def test_gap_energy_sees_a_tail_and_ignores_a_louder_burst(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mono, _path = _stimulus_mono(tmp)
            off = probe.analyse_stage(_write_capture(tmp / "off.wav", mono))
            louder = probe.analyse_stage(
                _write_capture(tmp / "loud.wav", mono * 4.0))
            # Longer than the gap guard, which deliberately excludes the
            # burst's own release and the analog loop's short decay.
            tailed = mono.copy()
            for tap in (1, 2, 3):
                lag = int(round(tap * 0.2 * RATE))
                tailed[lag:] += mono[:-lag] * (0.6 ** tap)
            tail = probe.analyse_stage(_write_capture(tmp / "tail.wav",
                                                      tailed))
            quiet = probe.classify_gap_energy(off, louder)
            loud = probe.classify_gap_energy(off, tail)
        self.assertFalse(quiet["detected"])
        self.assertTrue(loud["detected"])

    def test_a_silent_return_blocks_the_run_instead_of_reporting_a_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            quiet = np.zeros(int(6.0 * RATE)) + 1e-9
            stage = probe.analyse_stage(_write_capture(tmp / "q.wav", quiet))
            verdict = probe.classify_run(
                {"return_open": stage, "control_off": stage,
                 "control_reverb": stage}, {})
        self.assertEqual(verdict["status"],
                         "BLOCKED_NO_USABLE_STIMULUS_ON_THE_RETURN")
        self.assertFalse(verdict["run_valid"])

    def test_autocorrelation_reports_a_tonal_stimulus_as_inconclusive(self):
        """A continuous tone is already self-similar at every lag that is a
        whole number of its periods, so an echo cannot change it."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            t = np.arange(int(3.0 * RATE)) / float(RATE)
            tone = 0.05 * np.sin(2.0 * math.pi * 800.0 * t)
            stage = probe.analyse_stage(_write_capture(tmp / "t.wav", tone))
            result = probe.classify_autocorrelation(stage, stage)
        self.assertTrue(result["stimulus_too_tonal"])
        self.assertTrue(result["inconclusive"])
        self.assertFalse(result["detected"])


class SafetyTests(unittest.TestCase):
    def test_a_bypassed_channel1_refuses_instead_of_being_un_bypassed(self):
        with self.assertRaises(probe.FxReturnProbeError) as caught:
            probe.assert_guards({
                "input1_phantom": False, "input2_phantom": False,
                "channel_linked": False, "input1_processing_channel": 0,
                "input2_processing_channel": 1,
                "input1_processing_enabled": False})
        self.assertIn("bypassed", str(caught.exception))

    def test_guards_pass_on_the_expected_rig(self):
        probe.assert_guards({
            "input1_phantom": False, "input2_phantom": False,
            "channel_linked": False, "input1_processing_channel": 0,
            "input2_processing_channel": 1,
            "input1_processing_enabled": True})

    def test_an_appl_write_fails_the_transport_validation(self):
        clean = probe.validate_transport_log([
            {"command": "SetP", "block": 100, "block_index": 1},
            {"command": "SetP", "block": 201, "block_index": 0},
            {"command": "SetP", "block": 202, "block_index": 0},
        ])
        dirty = probe.validate_transport_log([
            {"command": "SetP", "block": 201, "block_index": 0},
            {"command": "SetP", "block": 0, "block_index": 0},
        ])
        self.assertTrue(clean["main_path_untouched"])
        self.assertFalse(dirty["main_path_untouched"])
        self.assertEqual(len(dirty["offending_frames"]), 1)

    def test_a_mixer_write_into_main_fails_the_transport_validation(self):
        """Block 100 at bus index 0 is Main: the one mixer frame that would
        change what the user hears and the gain of their loop."""
        result = probe.validate_transport_log([
            {"command": "SetP", "block": 100, "block_index": 0}])
        self.assertFalse(result["main_path_untouched"])
        self.assertEqual(result["mixer_bus_indexes"], [0])

    def test_restoration_returns_the_send_and_says_what_it_could_not_know(self):
        device = SynthDevice(np.zeros(16))
        notes = probe.restore(device, {"fx": None, "reverb": None,
                                       "return_send": None})
        self.assertIn(("set_send_db", probe.RETURN_SOURCE, probe.RETURN_BUS,
                       None), device.calls)
        self.assertTrue(any("write-only" in note for note in notes))
        self.assertTrue(any("left off" in note for note in notes))

    def test_restoration_resends_an_exact_host_known_state(self):
        device = SynthDevice(np.zeros(16))
        probe.restore(device, {
            "fx": {"model": "delay", "kwargs": {"on": True, "time_s": 0.1,
                                                "feedback": 0.2, "mix": 0.3}},
            "reverb": {"on": True, "size": 0.4, "mix": 0.5},
            "return_send": {"source": probe.RETURN_SOURCE,
                            "bus": probe.RETURN_BUS, "gain_db": -6.0}})
        self.assertIn(("set_fx", "delay", True), device.calls)
        self.assertIn(("set_reverb", True), device.calls)
        self.assertIn(("set_send_db", probe.RETURN_SOURCE, probe.RETURN_BUS,
                       -6.0), device.calls)

    def test_the_playback_sink_must_be_the_expected_unit(self):
        """Never fall back to a default sink. Playing the stimulus into the
        laptop's own output would make every model read as a confident null."""
        dump = json.dumps([
            {"info": {"props": {"media.class": "Audio/Sink",
                                "node.name": "alsa_output.pci-0000_04_00.6"}}},
            {"info": {"props": {"media.class": "Audio/Sink",
                                "node.name": "alsa_output.usb-PreSonus_"
                                             "Revelator_IO_24_AB7C22200355-00"
                                             ".analog-surround-21"}}},
        ])
        self.assertIn("AB7C22200355", probe.resolve_playback_sink(dump=dump))

        with self.assertRaises(probe.FxReturnProbeError):
            probe.resolve_playback_sink(dump=json.dumps([
                {"info": {"props": {"media.class": "Audio/Sink",
                                    "node.name": "alsa_output.pci-0000"}}}]))

    def test_a_sustained_loop_blocks_instead_of_reading_as_a_null(self):
        """Gaps that are not silent have nothing to measure in: the verdict must
        name the feedback loop, not report that block 201 does nothing."""
        stage = {"bursts_found": probe.CYCLES, "gate_alignment_score": 1.0,
                 "burst_rms_dbfs": -20.0, "gap_rms_dbfs": -21.0,
                 "dominant_partial": {"hz": 800.0, "dbfs": -25.0},
                 "tap_rms_dbfs": {}}
        verdict = probe.classify_run(
            {"return_open": stage, "control_off": stage,
             "control_reverb": stage}, {})
        self.assertEqual(verdict["status"],
                         "BLOCKED_GAPS_NOT_SILENT_BREAK_THE_FEEDBACK_LOOP")
        self.assertFalse(verdict["run_valid"])

    def test_capture_closes_both_streams_before_returning(self):
        """Serialised by construction: a control write must never overlap a
        stream, which is how this unit has been dropped to its bootloader."""
        started, finished = [], []

        class FakeProc:
            def __init__(self, argv):
                self.argv = argv
                self.returncode = 0
                started.append(argv[0])

            def poll(self):
                return None

            def communicate(self, timeout=None):
                finished.append(self.argv[0])
                return ("", "")

        with tempfile.TemporaryDirectory() as tmp:
            probe.capture_stage("s", Path(tmp), Path(tmp) / "stim.wav",
                                playback_sink="io24",
                                popen=lambda argv, **_k: FakeProc(argv),
                                sleep=lambda _s: None)
        self.assertEqual(started, ["arecord", "pw-play"])
        self.assertEqual(sorted(finished), ["arecord", "pw-play"])

    def test_a_capture_that_cannot_start_fails_closed(self):
        class DeadProc:
            returncode = 1

            def __init__(self, argv):
                self.argv = argv

            def poll(self):
                return 1

            def communicate(self, timeout=None):
                return ("", "device busy")

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(probe.FxReturnProbeError) as caught:
                probe.capture_stage("s", Path(tmp), Path(tmp) / "stim.wav",
                                    playback_sink="io24",
                                    popen=lambda argv, **_k: DeadProc(argv),
                                    sleep=lambda _s: None)
        self.assertIn("device busy", str(caught.exception))

    def test_restoration_is_required_only_after_a_real_write(self):
        """A run that failed its guards must not "restore" state it never
        disturbed; an interrupted one must still be put back."""
        self.assertFalse(probe.needs_restoration([]))
        self.assertFalse(probe.needs_restoration(
            [{"command": "GetP", "block": 0}]))
        self.assertTrue(probe.needs_restoration(
            [{"command": "SetP", "block": 100, "block_index": 1}]))

    def test_the_plan_names_what_is_never_written(self):
        plan = probe.plan()
        self.assertEqual(plan["allowed_blocks"], [100, 201, 202])
        self.assertEqual(plan["allowed_mixer_bus_index"], 1)
        joined = " ".join(plan["never_written"])
        self.assertIn("processing scalar", joined)
        self.assertIn("processingChannel", joined)
        self.assertEqual(plan["stimulus"]["shape"], "GATED_BURSTS")

    def test_live_execution_requires_an_explicit_flag(self):
        self.assertEqual(probe.main([]), 0)


if __name__ == "__main__":
    unittest.main()
