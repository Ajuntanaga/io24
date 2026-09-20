#!/usr/bin/env python3
"""Hardware-free contracts for the UC-derived Multiband compressor engine."""

import ctypes
import math
from pathlib import Path
import struct
import tempfile
import unittest
from types import SimpleNamespace

import io24
import io24_dsp
import io24_mbc
import io24gtk


def legacy_snapshot():
    state = {
        "version": 1,
        "enabled": True,
        "xovers": [150.0, 800.0, 4500.0],
        "bands": {},
    }
    for band in io24_mbc.BANDS:
        state["bands"][band] = {
            "type": "standard",
            "threshold": -24.0,
            "ratio": 4.0,
            "attack": 10.0,
            "release": 200.0,
            "knee": 3.0,
            "makeup": 6.0,
            "auto": False,
            "limit": False,
            "key_filter": True,
            "key": 730.0,
            "listen": False,
        }
    return state


class UcModelControlTests(unittest.TestCase):
    def _blob_controls(self, blob):
        values = struct.unpack_from("<11f", blob, 0x0c)
        _on, listen = struct.unpack_from("<II", blob, 0x38)
        return {
            "Biquad b0": values[0],
            "Biquad -a1": values[1],
            "Biquad b1": values[2],
            "Biquad -a2": values[3],
            "Biquad b2": values[4],
            "Attack time (s)": values[5],
            "Release time (s)": values[6],
            "Slope": values[7],
            "Knee width (dB)": values[8],
            "Threshold level (dB)": values[9],
            "Makeup gain (linear)": values[10],
            "Key listen": float(listen),
        }

    def test_standard_band_uses_the_exact_uc_builder_tuple(self):
        import io24_uc_comp

        params = {
            "threshold_db": -24.0,
            "ratio": 4.0,
            "attack_s": 0.01,
            "release_s": 0.2,
            "gain_db": 6.0,
            "softknee": True,
            "automode": False,
        }
        expected = self._blob_controls(io24_dsp.cpxt_comp(
            on=True, keyfilter_hz=730.0, keylisten=True, fs=96000.0,
            **params))
        self.assertEqual(io24_uc_comp.model_controls(
            "standard", params, 730.0, True, 96000.0), expected)

    def test_tube_band_keeps_uc_fixed_release_and_sidechain_emphasis(self):
        import io24_uc_comp

        params = {"peak": 50.0, "gain": 55.0, "limit_mode": True}
        expected = self._blob_controls(io24_dsp.cpxt_tube(
            on=True, keyfilter_hz=0.0, keylisten=False, fs=48000.0,
            **params))
        controls = io24_uc_comp.model_controls(
            "tube", params, 0.0, False, 48000.0)
        self.assertEqual(controls, expected)
        self.assertEqual(controls["Release time (s)"], io24_dsp.TUBE_RELEASE)
        self.assertNotEqual(controls["Biquad b0"], 1.0)

    def test_fet_band_keeps_uc_all_buttons_timing_and_gain_law(self):
        import io24_uc_comp

        params = {
            "input_db": -20.0,
            "output_db": -10.0,
            "attack_s": 0.0001,
            "release_s": 0.25,
            "ratio_index": 4,
        }
        expected = self._blob_controls(io24_dsp.cpxt_fet(
            on=True, keyfilter_hz=1200.0, keylisten=False, fs=44100.0,
            **params))
        self.assertEqual(io24_uc_comp.model_controls(
            "fet", params, 1200.0, False, 44100.0), expected)


class MultibandSchemaTests(unittest.TestCase):
    def test_each_band_retains_every_uc_model_parameter_set(self):
        state = io24_mbc.default_snapshot()
        self.assertEqual(state["version"], 2)
        low = state["bands"]["low"]
        self.assertEqual(set(low), {
            "type", "standard", "tube", "fet",
            "key_filter", "key", "listen",
        })
        self.assertEqual(set(low["standard"]), {
            "threshold_db", "ratio", "attack_s", "release_s", "gain_db",
            "softknee", "automode",
        })
        self.assertEqual(set(low["tube"]), {"peak", "gain", "limit_mode"})
        self.assertEqual(set(low["fet"]), {
            "input_db", "output_db", "attack_s", "release_s", "ratio_index",
        })

    def test_legacy_generic_band_state_migrates_without_becoming_invalid(self):
        migrated = io24_mbc.validate_snapshot(legacy_snapshot())
        self.assertEqual(migrated["version"], 2)
        self.assertEqual(migrated["bands"]["low"]["standard"], {
            "threshold_db": -24.0,
            "ratio": 4.0,
            "attack_s": 0.01,
            "release_s": 0.2,
            "gain_db": 6.0,
            "softknee": True,
            "automode": False,
        })

    def test_host_normalizer_reports_the_schema_migration(self):
        state = {
            "version": 1,
            "channels": {"1": legacy_snapshot(), "2": legacy_snapshot()},
            "routing": None,
            "quantum_before": None,
        }
        normalized, migrations = io24._normalise_host_features(
            {"multiband_insert": state})
        self.assertEqual(normalized["multiband_insert"]["version"], 2)
        self.assertTrue(all(
            channel["version"] == 2
            for channel in normalized["multiband_insert"]["channels"].values()))
        self.assertEqual(migrations, [
            "legacy Host multiband insert migrated to UC model schema v2",
        ])

    def test_graph_hosts_one_uc_processor_per_band_without_sc3(self):
        graph = io24_mbc.build_graph(
            None, True, state=io24_mbc.default_snapshot(),
            sample_rate=96000.0, plugin="/tmp/io24_uc_comp")
        compressors = [node for node in graph["nodes"]
                       if node.get("label") == "io24_uc_comp"]
        self.assertEqual(len(compressors), 4)
        self.assertTrue(all(node["plugin"] == "/tmp/io24_uc_comp"
                            for node in compressors))
        self.assertFalse(any(node.get("label") == "sc3"
                             for node in graph["nodes"]))
        self.assertEqual(compressors[0]["control"],
                         __import__("io24_uc_comp").model_controls(
                             "standard",
                             io24_mbc.default_snapshot()["bands"]["low"]["standard"],
                             0.0, False, 96000.0))

    def test_live_band_edit_sends_each_common_control_to_its_own_port(self):
        class Insert:
            running = True

            def __init__(self):
                self.updates = []

            def set_channel_controls(self, channel, controls):
                self.updates.append((channel, controls))

        band = io24_mbc.default_band("highmid")
        band["type"] = "tube"
        band["tube"] = {"peak": 61.0, "gain": 52.0, "limit_mode": True}
        band["key_filter"] = True
        band["key"] = 1300.0
        insert = Insert()
        host = SimpleNamespace(
            _fs=96000.0,
            link_both=True,
            insert=insert,
            _mbc_band_state=lambda _channel, _band: band,
        )
        host._mbc_targets = io24gtk.Win._mbc_targets.__get__(host)

        io24gtk.Win._mbc_push_band(host, 1, 2)

        expected = {
            "c2:%s" % key: value for key, value in
            io24_mbc.compressor_controls(band, 96000.0).items()
        }
        self.assertEqual(insert.updates, [(1, expected), (2, expected)])
        self.assertTrue(all(not isinstance(value, tuple)
                            for value in expected.values()))

    def test_model_edit_uses_the_slider_callback_signature(self):
        calls = []
        host = SimpleNamespace(
            _mbc_mute=False,
            _mbc_mirror=lambda channel, control: calls.append(
                ("mirror", channel, control)),
            _mbc_push_band=lambda channel, band: calls.append(
                ("push", channel, band)),
        )

        io24gtk.Win._mbc_model_edit(host, 1, 3, "s_thr")

        self.assertEqual(calls, [
            ("mirror", 1, (3, "s_thr")),
            ("push", 1, 3),
        ])


class NativePluginTests(unittest.TestCase):
    def test_pipewire_plugin_reference_is_a_ladspa_basename(self):
        import io24_uc_comp

        with tempfile.TemporaryDirectory(prefix="io24-uc-ref-test-") as directory:
            reference = io24_uc_comp.plugin_reference(Path(directory))

            self.assertEqual(reference, io24_uc_comp.plugin_name())
            self.assertNotIn("/", reference)
            self.assertTrue(
                (Path(directory) / (reference + ".so")).is_file())

    def test_ladspa_descriptor_matches_the_real_32_bit_abi(self):
        import io24_uc_comp

        class PortRangeHint(ctypes.Structure):
            _fields_ = [
                ("descriptor", ctypes.c_int),
                ("lower", ctypes.c_float),
                ("upper", ctypes.c_float),
            ]

        class Descriptor(ctypes.Structure):
            _fields_ = [
                ("unique_id", ctypes.c_ulong),
                ("label", ctypes.c_char_p),
                ("properties", ctypes.c_int),
                ("name", ctypes.c_char_p),
                ("maker", ctypes.c_char_p),
                ("copyright", ctypes.c_char_p),
                ("port_count", ctypes.c_ulong),
                ("port_descriptors", ctypes.POINTER(ctypes.c_int)),
                ("port_names", ctypes.POINTER(ctypes.c_char_p)),
                ("port_hints", ctypes.POINTER(PortRangeHint)),
                ("implementation_data", ctypes.c_void_p),
            ]

        with tempfile.TemporaryDirectory(prefix="io24-uc-abi-test-") as directory:
            library = io24_uc_comp.build_plugin(Path(directory))
            dll = ctypes.CDLL(str(library))
            descriptor = dll.ladspa_descriptor
            descriptor.argtypes = [ctypes.c_ulong]
            descriptor.restype = ctypes.POINTER(Descriptor)
            self.assertFalse(descriptor(1))
            plugin = descriptor(0).contents

            self.assertEqual(plugin.unique_id, 422024)
            self.assertEqual(plugin.label, b"io24_uc_comp")
            self.assertEqual(plugin.port_count, 14)
            self.assertEqual(
                tuple(plugin.port_names[index].decode()
                      for index in range(plugin.port_count)),
                io24_uc_comp.CONTROL_PORTS + ("Input", "Output"))
            self.assertEqual(
                tuple(plugin.port_descriptors[index]
                      for index in range(plugin.port_count)),
                (0x5,) * 12 + (0x9, 0xA))
            self.assertTrue(plugin.port_hints[11].descriptor & 0x4)

    def test_plugin_builds_and_matches_the_measured_standard_transfer(self):
        import io24_uc_comp

        with tempfile.TemporaryDirectory(prefix="io24-uc-comp-test-") as directory:
            library = io24_uc_comp.build_plugin(Path(directory))
            self.assertTrue(library.is_file())
            dll = ctypes.CDLL(str(library))
            process = dll.io24_uc_comp_process
            process.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_ulong,
                ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_float),
            ]
            process.restype = ctypes.c_int

            sample_rate = 48000
            frames = sample_rate * 3
            amplitude = 10.0 ** (-7.3 / 20.0)
            source = (ctypes.c_float * frames)(*(
                amplitude * math.sin(2.0 * math.pi * 1000.0 * n / sample_rate)
                for n in range(frames)))
            output = (ctypes.c_float * frames)()
            params = {
                "threshold_db": -20.0,
                "ratio": 4.0,
                "attack_s": 0.0002,
                "release_s": 0.15,
                "gain_db": 0.0,
                "softknee": False,
                "automode": False,
            }
            controls = io24_uc_comp.model_controls(
                "standard", params, 0.0, False, sample_rate)
            ordered = (ctypes.c_float * len(io24_uc_comp.CONTROL_PORTS))(*(
                controls[name] for name in io24_uc_comp.CONTROL_PORTS))

            self.assertEqual(process(source, output, frames, sample_rate, ordered), 0)
            start = frames - sample_rate // 2
            in_rms = math.sqrt(sum(float(source[n]) ** 2
                                   for n in range(start, frames)) /
                               (frames - start))
            out_rms = math.sqrt(sum(float(output[n]) ** 2
                                    for n in range(start, frames)) /
                                (frames - start))
            reduction_db = 20.0 * math.log10(out_rms / in_rms)
            # Hardware measured -7.30 dB at this exact level/threshold/ratio;
            # the RMS ratio law predicts -7.27 dB.
            self.assertAlmostEqual(reduction_db, -7.30, delta=0.08)

    def test_soft_knee_uses_the_firmware_derived_half_width(self):
        """Firmware stores 0.5/sqrt(K) and 0.5*sqrt(K), so K is the
        half-width: at threshold the curve reduces by slope*K/4."""
        import io24_uc_comp

        with tempfile.TemporaryDirectory(prefix="io24-uc-knee-test-") as directory:
            library = io24_uc_comp.build_plugin(Path(directory))
            dll = ctypes.CDLL(str(library))
            process = dll.io24_uc_comp_process
            process.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_ulong,
                ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_float),
            ]
            process.restype = ctypes.c_int

            sample_rate = 48000
            frames = sample_rate * 3
            threshold = -20.0
            amplitude = math.sqrt(2.0) * 10.0 ** (threshold / 20.0)
            source = (ctypes.c_float * frames)(*(
                amplitude * math.sin(2.0 * math.pi * 1000.0 * n / sample_rate)
                for n in range(frames)))
            output = (ctypes.c_float * frames)()
            controls = io24_uc_comp.model_controls("standard", {
                "threshold_db": threshold,
                "ratio": 4.0,
                "attack_s": 0.0002,
                "release_s": 0.15,
                "gain_db": 0.0,
                "softknee": True,
                "automode": False,
            }, 0.0, False, sample_rate)
            ordered = (ctypes.c_float * len(io24_uc_comp.CONTROL_PORTS))(*(
                controls[name] for name in io24_uc_comp.CONTROL_PORTS))

            self.assertEqual(process(source, output, frames, sample_rate, ordered), 0)
            start = frames - sample_rate // 2
            in_rms = math.sqrt(sum(float(source[n]) ** 2
                                   for n in range(start, frames)) /
                               (frames - start))
            out_rms = math.sqrt(sum(float(output[n]) ** 2
                                    for n in range(start, frames)) /
                                (frames - start))
            reduction_db = 20.0 * math.log10(out_rms / in_rms)
            self.assertAlmostEqual(reduction_db, -(0.75 * 3.0 / 4.0),
                                   delta=0.03)


if __name__ == "__main__":
    unittest.main()
