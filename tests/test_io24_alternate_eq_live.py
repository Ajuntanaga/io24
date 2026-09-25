#!/usr/bin/env python3
"""Hardware-free contracts for exact Passive/Vintage live EQ routing."""

import json
import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

import io24
import io24_alt_eq
import io24_presets


ROOT = Path(__file__).resolve().parents[1]
PRESETS = ROOT / "re" / "uc_factory_presets.json"
ROUTE_ANALYZER = ROOT / "re" / "uc472_alt_eq_live_route.py"


class WireDevice(io24.Io24):
    def __init__(self):
        self.payloads = []
        self._shadow = {}
        self._shadow_dirty = False
        self._shadow_flushed = 0.0
        self._shadow_persist = False

    def _exec(self, payload, wait=1.5):
        self.payloads.append(bytes(payload))
        return b""


def _preset(class_id):
    records = json.loads(PRESETS.read_text())
    return next(record for record in records
                if (record.get("eq") or {}).get("__classid") == class_id)


def _packet(payload):
    command, block, channel = struct.unpack_from("<III", payload, 0)
    tag, size, reserved, index = struct.unpack_from("<IIII", payload, 12)
    count = 7 if tag == io24.LFDF else 5
    coefficients = struct.unpack_from("<%df" % count, payload, 28)
    return command, block, channel, tag, size, reserved, index, coefficients


class AlternateEqSchemaTests(unittest.TestCase):
    def test_retained_xml_declares_both_exact_parameter_lists(self):
        import xml.etree.ElementTree as ET
        contract = ROOT / "re" / "uc_component_model" / \
            "fatchannelxt_alternate_eq_contract.xml"
        root = ET.parse(contract).getroot()
        ns = {"uc": "urn:presonus-universal-control"}
        lists = {
            node.attrib["id"]: {
                child.attrib["id"]: child.attrib
                for child in node.findall("uc:Param", ns)
            }
            for node in root.findall(".//uc:ParamList", ns)
        }
        self.assertEqual(set(lists["PassiveEQ"]), {
            "eqallon", "bboost", "batten", "bfreq", "mboost", "bbwidth",
            "mfreq", "hatten", "hsfreq"})
        self.assertEqual(set(lists["VintageEQ"]), {
            "eqallon", "lowgain", "lowfreq", "lowmidgain", "lowmidfreq",
            "himidgain", "himidfreq", "higain"})
        self.assertEqual(lists["PassiveEQ"]["eqallon"]["def"], "0")
        self.assertEqual(lists["VintageEQ"]["eqallon"]["def"], "0")

    def test_defaults_are_the_exact_uc_xml_defaults(self):
        self.assertEqual(io24_alt_eq.default_eq("passive"), {
            "__classid": io24_alt_eq.PASSIVE_CLASS_ID,
            "eqallon": 0, "bboost": 0.0, "batten": 0.0, "bfreq": 0,
            "mboost": 1.5, "bbwidth": 10.0, "mfreq": 4,
            "hatten": 1.5, "hsfreq": 2,
        })
        self.assertEqual(io24_alt_eq.default_eq("vintage"), {
            "__classid": io24_alt_eq.VINTAGE_CLASS_ID,
            "eqallon": 0, "lowgain": 0.0, "lowfreq": 1,
            "lowmidgain": 0.0, "lowmidfreq": 2,
            "himidgain": 0.0, "himidfreq": 2, "higain": 0.0,
        })

    def test_all_switches_and_amounts_are_strictly_validated(self):
        for model, field, value in (
                ("passive", "bfreq", 1.5),
                ("passive", "mfreq", 7),
                ("passive", "bboost", 10.1),
                ("vintage", "lowfreq", True),
                ("vintage", "himidfreq", -1),
                ("vintage", "higain", float("nan"))):
            with self.subTest(model=model, field=field):
                state = io24_alt_eq.default_eq(model)
                state[field] = value
                with self.assertRaises(ValueError):
                    io24_alt_eq.validate_eq(state)

    def test_disabled_models_are_exact_identity_without_a_vendor_artifact(self):
        for model in ("passive", "vintage"):
            sections = io24_alt_eq.design_live_sections(
                io24_alt_eq.default_eq(model), dll_path="/definitely/missing")
            self.assertEqual([item[:2] for item in sections],
                             [("wide", 0), ("biquad", 1),
                              ("biquad", 2), ("biquad", 3)])
            self.assertEqual(sections[0][2], io24_alt_eq.WIDE_IDENTITY)
            self.assertTrue(all(item[2] == io24_alt_eq.IDENTITY
                                for item in sections[1:]))

    def test_default_resolution_skips_an_invalid_cache_copy(self):
        with tempfile.TemporaryDirectory(prefix="io24-alt-eq-") as temp:
            root = Path(temp)
            invalid = root / "invalid.dll"
            retained = root / "retained.dll"
            invalid.write_bytes(b"wrong")
            retained.write_bytes(b"right")

            def validate(path):
                if Path(path) == invalid:
                    raise io24_alt_eq.AlternateEqUnavailable("wrong build")
                return object()

            with mock.patch.dict(os.environ, {}, clear=False), \
                    mock.patch.object(io24_alt_eq, "DEFAULT_DLL", invalid), \
                    mock.patch.object(
                        io24_alt_eq, "PROJECT_RETAINED_DLL", retained), \
                    mock.patch.object(
                        io24_alt_eq, "_image", side_effect=validate):
                os.environ.pop("IO24_UC472_DSPUSBDEVICE", None)
                self.assertEqual(io24_alt_eq.resolve_dll(), retained.resolve())

    def test_every_alternate_parameter_moves_the_responsive_preview(self):
        frequencies = (25.0, 60.0, 100.0, 400.0, 1000.0, 4000.0,
                       8000.0, 16000.0, 22000.0)
        cases = {
            "passive": dict(
                io24_alt_eq.default_eq("passive", on=True),
                bboost=3.0, batten=2.0, bfreq=1, mboost=4.0,
                bbwidth=5.0, mfreq=3, hatten=2.0, hsfreq=1),
            "vintage": dict(
                io24_alt_eq.default_eq("vintage", on=True),
                lowgain=4.0, lowfreq=1, lowmidgain=-4.0,
                lowmidfreq=1, himidgain=5.0, himidfreq=1, higain=3.0),
        }
        changes = {
            "passive": {
                "bboost": 8.0, "batten": 7.0, "bfreq": 3,
                "mboost": 8.0, "bbwidth": 9.0, "mfreq": 6,
                "hatten": 7.0, "hsfreq": 2,
            },
            "vintage": {
                "lowgain": -5.0, "lowfreq": 3,
                "lowmidgain": 6.0, "lowmidfreq": 2,
                "himidgain": -6.0, "himidfreq": 2, "higain": -4.0,
            },
        }
        for model, base in cases.items():
            reference = tuple(io24_alt_eq.preview_response_db(
                base, frequency) for frequency in frequencies)
            for field, value in changes[model].items():
                changed = dict(base, **{field: value})
                response = tuple(io24_alt_eq.preview_response_db(
                    changed, frequency) for frequency in frequencies)
                with self.subTest(model=model, field=field):
                    self.assertNotEqual(response, reference)


@unittest.skipUnless(io24_alt_eq.designer_status()[0],
                     "exact UC 4.7.2 DLL is not present")
class AlternateEqWireTests(unittest.TestCase):
    def test_uc_source_binds_every_designer_to_the_live_tag_and_index(self):
        spec = importlib.util.spec_from_file_location(
            "uc472_alt_eq_live_route", ROUTE_ANALYZER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = module.analyze(io24_alt_eq.resolve_dll())
        self.assertEqual(
            report["status"],
            "UC472_ALTERNATE_EQ_LIVE_ROUTE_SOURCE_BOUND")
        self.assertEqual(
            [(row["section"], row["packet"]["tag"],
              row["packet"]["index"])
             for row in report["models"]["passive"]],
            [("identity-2", "Bqdf", 2), ("identity-3", "Bqdf", 3),
             ("high", "Lfdf", 0), ("low", "Bqdf", 1)])
        self.assertEqual(
            [(row["section"], row["packet"]["tag"],
              row["packet"]["index"])
             for row in report["models"]["vintage"]],
            [("low", "Lfdf", 0), ("high", "Bqdf", 1),
             ("hi-mid", "Bqdf", 2), ("low-mid", "Bqdf", 3)])

    def assert_route(self, model, eq, expected):
        sections = io24_alt_eq.design_live_sections(eq, 48000.0)
        self.assertEqual([(kind, index) for kind, index, _ in sections], expected)

        device = WireDevice()
        device.set_alternate_eq(2, eq, fs=48000.0)
        self.assertEqual(len(device.payloads), 4)
        self.assertEqual(
            device._last_alternate_eq_sections[2],
            tuple(io24_alt_eq.design_live_sections(eq, 48000.0)))
        packets = [_packet(payload) for payload in device.payloads]
        self.assertEqual([(packet[3], packet[4], packet[6]) for packet in packets],
                         [(io24.LFDF, 0x2C, 0),
                          (io24.BQDF, 0x24, 1),
                          (io24.BQDF, 0x24, 2),
                          (io24.BQDF, 0x24, 3)])
        self.assertTrue(all(packet[:3] == (io24.SETP, io24.EQ, 1)
                            for packet in packets))
        self.assertEqual([packet[7] for packet in packets],
                         [tuple(section[2]) for section in sections])
        shadow = device._shadow["set_alternate_eq#channel=2"]
        self.assertEqual(shadow["kwargs"]["eq"],
                         io24_alt_eq.validate_eq(eq))
        self.assertEqual(shadow["kwargs"]["fs"], 48000.0)

    def test_passive_uses_uc_live_order_and_exact_factory_coefficients(self):
        eq = dict(_preset(io24_alt_eq.PASSIVE_CLASS_ID)["eq"], eqallon=1)
        self.assert_route("passive", eq,
                          [("wide", 0), ("biquad", 1),
                           ("biquad", 2), ("biquad", 3)])
        sections = io24_alt_eq.design_live_sections(eq, 48000.0)
        self.assertEqual(sections[0][2], (
            0.7912453413009644, 0.2167043685913086,
            -0.022251157090067863, -0.4968438148498535,
            0.36978256702423096, 0.2143542468547821,
            -0.07308901101350784))
        self.assertEqual(sections[1][2], (
            1.0225366353988647, 0.2282530814409256,
            -0.16702279448509216, 0.7338700294494629,
            -0.697493851184845))

    def test_vintage_uses_uc_live_order(self):
        eq = dict(_preset(io24_alt_eq.VINTAGE_CLASS_ID)["eq"], eqallon=1)
        self.assert_route("vintage", eq,
                          [("wide", 0), ("biquad", 1),
                           ("biquad", 2), ("biquad", 3)])

    def test_direct_factory_apply_dispatches_alternate_eq(self):
        preset = _preset(io24_alt_eq.PASSIVE_CLASS_ID)
        calls = []

        class Device:
            def set_alternate_eq(self, channel, eq, fs=48000.0):
                calls.append((channel, eq, fs))

        done = io24_presets.apply_preset(
            Device(), {"eq": preset["eq"]}, channel=2, fs=96000.0)
        self.assertEqual(done, ["eq(passive)"])
        self.assertEqual(calls[0][0], 2)
        self.assertEqual(calls[0][1],
                         io24_alt_eq.validate_eq(preset["eq"]))
        self.assertEqual(calls[0][2], 96000.0)

    def test_wide_stability_guard_rejects_before_transport(self):
        device = WireDevice()
        with self.assertRaisesRegex(ValueError, "unstable wide EQ"):
            device.set_wide_eq(
                1, (1.0, 3.0, 0.0, 3.0, 0.0, 3.0, 0.0), band=0)
        self.assertEqual(device.payloads, [])

    def test_shadow_keeps_only_the_selected_eq_model_per_channel(self):
        device = WireDevice()
        device.set_eq_band(1, 0, "peaking", 1000.0, 2.0, 0.7)
        self.assertIn("set_eq_band#channel=1,band=0", device._shadow)

        state = dict(io24_alt_eq.default_eq("vintage", on=True),
                     lowgain=2.0)
        device.set_alternate_eq(1, state)
        self.assertEqual(set(device._shadow),
                         {"set_alternate_eq#channel=1"})

        device.set_eq_band(1, 0, "peaking", 1000.0, 2.0, 0.7)
        self.assertNotIn("set_alternate_eq#channel=1", device._shadow)
        self.assertIn("set_eq_band#channel=1,band=0", device._shadow)


if __name__ == "__main__":
    unittest.main()
