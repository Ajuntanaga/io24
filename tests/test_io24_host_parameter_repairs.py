"""Hardware-free contracts for the P1 Host parameter repairs."""

import copy
import gc
import hashlib
import inspect
import json
import math
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock
import warnings

import io24
import io24_mbc
import io24_presets
import io24_scene
import io24d
import io24gtk
import ucnet_shim


class ProtocolDevice(io24.Io24):
    def __init__(self):
        self.payloads = []
        self._shadow = {}
        self._shadow_dirty = False
        self._shadow_flushed = 0.0
        self._shadow_persist = False

    def _exec(self, payload, wait=1.5):
        self.payloads.append(bytes(payload))
        return b""


class CallDevice:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("set_") or name.endswith("_off"):
            def call(*args, **kwargs):
                self.calls.append((name, args, kwargs))
            return call
        raise AttributeError(name)


class PhonesSourceTests(unittest.TestCase):
    def test_public_setter_emits_exact_pari_11_and_is_shadowed(self):
        dev = ProtocolDevice()

        dev.set_phones_source("Mix B")

        self.assertEqual(len(dev.payloads), 1)
        payload = dev.payloads[0]
        self.assertEqual(len(payload), 32)
        self.assertEqual(struct.unpack_from("<III", payload),
                         (io24.SETP, io24.APPL, 0))
        self.assertEqual(struct.unpack_from("<IIIII", payload, 12),
                         (io24.PARI, 0x14, 0, 11, 2))
        self.assertEqual(io24.Io24.KNOWN_PARI[11], "phonesSource")
        self.assertEqual(dev._shadow, {
            "set_phones_source": {
                "fn": "set_phones_source", "kwargs": {"source": "Mix B"},
            },
        })

    def test_all_aliases_map_and_invalid_or_ambiguous_values_emit_nothing(self):
        for source, expected in (("main", 0), ("aux1", 1), ("stream mix b", 2),
                                 (0, 0), (1.0, 1), ("2", 2)):
            with self.subTest(source=source):
                dev = ProtocolDevice()
                dev.set_phones_source(source)
                self.assertEqual(struct.unpack_from("<i", dev.payloads[0], 28)[0],
                                 expected)
        for source in (True, -1, 3, 0.5, float("nan"), "unknown"):
            with self.subTest(source=source):
                dev = ProtocolDevice()
                with self.assertRaises(ValueError):
                    dev.set_phones_source(source)
                self.assertEqual(dev.payloads, [])
                self.assertEqual(dev._shadow, {})

    def test_daemon_scene_shadow_and_ucnet_paths_reach_the_public_setter(self):
        fake = CallDevice()
        daemon = object.__new__(io24d.Device)
        daemon.lock = threading.RLock()
        daemon.dev = fake
        daemon.apply("phonesrc", 1, "mixa", {})
        self.assertEqual(fake.calls, [("set_phones_source", ("mixa",), {})])

        calls, skips = io24_scene.plan({"global": {"phonesSrc": 2}})
        self.assertEqual(calls, [
            ("set_phones_source", (2,), {}, "headphones source = 2"),
        ])
        self.assertFalse(any("phonesSrc" in skip for skip in skips))

        state = io24gtk.shadow_ui_state({
            "phones": {"fn": "set_phones_source", "kwargs": {"source": "aux1"}},
        })
        self.assertEqual(state["phones_source"], 1)

        shim = object.__new__(ucnet_shim.Shim)
        shim.state = SimpleNamespace(values={})
        shim.dry_run = False
        shim.dev = fake = CallDevice()
        shim.usb_lock = threading.Lock()
        shim.apply("global/phonesSrc", 1.0)
        self.assertEqual(fake.calls, [("set_phones_source", (2,), {})])

    def test_programmatic_gtk_adoption_is_silent(self):
        writes = []
        messages = []
        host = SimpleNamespace(
            _phones_source_mute=True,
            _set=lambda *args: writes.append(args),
            say=messages.append,
        )
        row = SimpleNamespace(get_selected=lambda: 2)
        io24gtk.Win._phones_source_changed(host, row, None)
        self.assertEqual(writes, [])
        self.assertEqual(messages, [])

        host._phones_source_mute = False
        io24gtk.Win._phones_source_changed(host, row, None)
        self.assertEqual(writes, [("phonesrc", None, "mixb")])

    def test_ucnet_does_not_publish_a_fabricated_phones_source(self):
        state = ucnet_shim.State(None)
        self.assertNotIn("global/phonesSrc", state.values)

        dev = SimpleNamespace(_shadow={"phones": {
            "fn": "set_phones_source", "kwargs": {"source": "aux1"},
        }})
        shadowed = ucnet_shim.State(dev)
        self.assertEqual(shadowed.values["global/phonesSrc"], 0.5)


class FactoryPresetDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.presets = io24_presets.load()

    def _by_class(self, component, class_id):
        return next(copy.deepcopy(p) for p in self.presets.values()
                    if (p.get(component) or {}).get("__classid") == class_id)

    def test_all_three_compressor_classes_dispatch_to_their_own_builder(self):
        expected = {
            "{870D04F7-212E-4F9C-ADBB-39A97216433F}": (0, "threshold_db"),
            "{7F8A4262-D377-48E3-9D48-15D82C400A71}": (1, "peak"),
            "{1F831EC1-B8AC-4EE9-AD53-54227AF53D58}": (2, "input_db"),
        }
        for class_id, (model, diagnostic) in expected.items():
            with self.subTest(class_id=class_id):
                preset = self._by_class("comp", class_id)
                preset = {"comp": preset["comp"]}
                dev = CallDevice()
                io24_presets.apply_preset(dev, preset, channel=2)
                name, args, kwargs = dev.calls[0]
                self.assertEqual((name, args, kwargs["model"]),
                                 ("set_compressor", (2,), model))
                self.assertIn(diagnostic, kwargs)

    def test_standard_outer_band_toggle_true_means_shelf(self):
        preset = self._by_class(
            "eq", "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}")
        eq = preset["eq"]
        eq["eqallon"] = 1
        eq["eqbandon1"] = eq["eqbandon4"] = 1
        eq["eqbandop1"] = 1
        eq["eqbandop4"] = 0

        bands = io24_presets.to_bands({"eq": eq})

        self.assertEqual(bands[0]["shape"], "lowshelf")
        self.assertEqual(bands[3]["shape"], "peaking")

    def test_alternate_eq_is_rejected_atomically_instead_of_flattened(self):
        for class_id, model in (
                ("{C0730CBB-5135-4558-9222-C40BDBA036ED}", "Passive"),
                ("{E1C5E024-C5CD-473C-B08A-6EC177812E01}", "Vintage")):
            with self.subTest(model=model):
                preset = self._by_class("eq", class_id)
                preset["opt"] = {"swapcompeq": 1}
                dev = CallDevice()
                with self.assertRaisesRegex(
                        io24_presets.UnsupportedPresetModel,
                        "%s EQ has no exact direct-live builder" % model):
                    io24_presets.apply_preset(dev, preset, channel=2)
                self.assertEqual(dev.calls, [])
                with self.assertRaises(io24_presets.UnsupportedPresetModel):
                    io24_presets.to_bands(preset)
                supported, reason = io24_presets.direct_apply_support(preset)
                self.assertFalse(supported)
                self.assertIn("device-slot only", reason)

    def test_malformed_standard_eq_fails_before_an_order_write(self):
        preset = self._by_class(
            "eq", "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}")
        preset["opt"] = {"swapcompeq": 1}
        del preset["eq"]["eqfreq2"]
        dev = CallDevice()

        with self.assertRaisesRegex(ValueError, "Standard EQ missing field"):
            io24_presets.apply_preset(dev, preset)

        self.assertEqual(dev.calls, [])

    def test_malformed_compressors_fail_before_every_device_call(self):
        cases = (
            ("{870D04F7-212E-4F9C-ADBB-39A97216433F}",
             "threshold", math.nan),
            ("{870D04F7-212E-4F9C-ADBB-39A97216433F}",
             "softknee", 2),
            ("{7F8A4262-D377-48E3-9D48-15D82C400A71}",
             "peak", 101.0),
            ("{7F8A4262-D377-48E3-9D48-15D82C400A71}",
             "mode", 2),
            ("{1F831EC1-B8AC-4EE9-AD53-54227AF53D58}",
             "ratio", 1.5),
            ("{1F831EC1-B8AC-4EE9-AD53-54227AF53D58}",
             "release", math.inf),
        )
        for class_id, field, value in cases:
            with self.subTest(class_id=class_id, field=field, value=value):
                preset = self._by_class("comp", class_id)
                preset["opt"] = {"swapcompeq": 1}
                preset["filter"] = {"hpf": 80.0}
                preset["gate"] = {"on": 0}
                preset["comp"][field] = value
                dev = CallDevice()

                with self.assertRaises(ValueError):
                    io24_presets.apply_preset(dev, preset, channel=2)

                self.assertEqual(dev.calls, [])

    def test_below_minimum_compressor_keyfilters_fail_before_every_device_call(self):
        for class_id, model in (
                ("{870D04F7-212E-4F9C-ADBB-39A97216433F}", "Standard"),
                ("{7F8A4262-D377-48E3-9D48-15D82C400A71}", "Tube"),
                ("{1F831EC1-B8AC-4EE9-AD53-54227AF53D58}", "FET")):
            with self.subTest(model=model):
                preset = self._by_class("comp", class_id)
                preset = {"comp": preset["comp"]}
                preset["opt"] = {"swapcompeq": 1}
                preset["filter"] = {"hpf": 80.0}
                preset["gate"] = {"on": 0}
                preset["comp"]["keyfilter"] = 1.0
                dev = CallDevice()

                with self.assertRaisesRegex(
                        ValueError, r"off sentinel or in \[40.0, 16000.0\]"):
                    io24_presets.apply_preset(dev, preset, channel=2)

                self.assertEqual(dev.calls, [])

    def test_selected_compressor_builder_serializes_before_device_calls(self):
        preset = self._by_class(
            "comp", "{7F8A4262-D377-48E3-9D48-15D82C400A71}")
        preset["opt"] = {"swapcompeq": 1}
        preset["filter"] = {"hpf": 80.0}
        dev = CallDevice()

        with mock.patch.object(
                io24_presets.io24_dsp, "cpxt_tube",
                side_effect=ValueError("serialization refused")):
            with self.assertRaisesRegex(ValueError, "serialization refused"):
                io24_presets.apply_preset(dev, preset, channel=2)

        self.assertEqual(dev.calls, [])

    def test_gtk_compressor_adoption_uses_the_dispatch_model_resolver(self):
        class Value:
            def __init__(self):
                self.value = None

            def set_value(self, value):
                self.value = value

            def set_active(self, value):
                self.value = value

            def set_selected(self, value):
                self.value = value

        class Stack:
            def __init__(self):
                self.name = None

            def set_visible_child_name(self, name):
                self.name = name

        widgets = {name: Value() for name in (
            "gth", "grange", "gatk", "grel", "gkey", "gklisten", "gexp",
            "model", "ckey", "cklisten", "cth", "rat", "catk", "crel",
            "mk", "knee", "auto", "tpeak", "tgain", "climit", "finput",
            "foutput", "fatk", "frel", "fratio", "lth",
        )}
        widgets["comp_param_stack"] = Stack()
        host = SimpleNamespace(w={1: widgets}, _adopt_mute=False)
        preset = {"comp": {
            "__classid": "{870D04F7-212E-4F9C-ADBB-39A97216433F}",
            "on": 1, "threshold": -24.0, "ratio": 3.0,
            "attack": 0.02, "release": 0.15, "gain": 4.0,
            "softknee": 1, "automode": 0,
            "keyfilter": 40.0, "keylisten": 0,
            # A misleading foreign-model field must not override the class ID.
            "input": -31.0,
        }}

        io24gtk.Win._adopt_dynamics(host, 1, preset)

        self.assertEqual(widgets["model"].value, 0)
        self.assertEqual(widgets["comp_param_stack"].name, "standard")
        self.assertEqual(widgets["cth"].value, -24.0)

    def test_scene_vintage_frequency_tables_are_exact_uc_lists(self):
        self.assertEqual(io24_scene.VINTAGE_LOW_HZ, (35.0, 60.0, 110.0, 220.0))
        self.assertEqual(io24_scene.VINTAGE_LOWMID_HZ, (360.0, 700.0, 1600.0))
        self.assertEqual(io24_scene.VINTAGE_HIMID_HZ, (3200.0, 4800.0, 7200.0))
        self.assertEqual(io24_scene.VINTAGE_HIGH_HZ, 12000.0)

    def test_scene_vintage_opt_in_cannot_emit_standard_biquad_calls(self):
        scene = {"line": {"ch1": {"eq": {
            "__classid": io24_scene.EQ_VINTAGE,
            "eqallon": 1,
            "lowgain": 4.0, "lowfreq": 2,
            "lowmidgain": -2.0, "lowmidfreq": 1,
            "himidgain": 3.0, "himidfreq": 2,
            "higain": 1.0,
        }}}}

        calls, skips = io24_scene.plan(scene, vintage=True)

        self.assertFalse(any(call[0] == "set_eq_band" for call in calls))
        self.assertTrue(any("exact coefficient builder" in skip for skip in skips))


class ArtifactAndResourceTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    RUN = ROOT / "runs" / "20260906T165749-0700-host-live-routing-repair"

    def test_matrix_hash_inventory_binds_all_dispatch_sources(self):
        matrix = json.loads((self.RUN / "PARAMETER-VERIFICATION-MATRIX.json")
                            .read_text())
        for name in ("io24d.py", "io24_scene.py", "ucnet_shim.py"):
            with self.subTest(name=name):
                expected = hashlib.sha256((self.ROOT / name).read_bytes()).hexdigest()
                self.assertEqual(matrix["source_sha256"].get(name), expected)

    def test_inventory_records_implemented_host_routes_and_fail_closed_eq(self):
        inventory = json.loads((self.RUN / "PARAMETER-INVENTORY.json").read_text())
        unresolved = set(inventory["known_unimplemented_or_unresolved"])
        self.assertNotIn("global/phonesSrc", unresolved)
        self.assertNotIn("line/ch1/presetHotKey", unresolved)
        self.assertNotIn("line/ch2/presetHotKey", unresolved)
        policy = inventory["alternate_eq_per_physical_channel"]["direct_live_policy"]
        self.assertIn("fail-closed", policy)
        self.assertIn("no Standard-biquad approximation", policy)
        supported = inventory["supported_host_capabilities"]
        self.assertEqual(supported["phones_source"]["route"],
                         "global/phonesSrc")
        self.assertEqual(supported["phones_source"]["readback"],
                         "write_only_host_shadow")
        self.assertEqual(set(supported["host_hot_key"]), {
            "channel1_snapshot_override",
            "channel2_snapshot_override",
            "release_restores_normal_snapshot",
        })

    def test_factory_preset_load_closes_its_input_file(self):
        records = [{"preset_name": "test", "comp": {}}]
        with tempfile.NamedTemporaryFile("w", suffix=".json") as stream:
            json.dump(records, stream)
            stream.flush()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                self.assertIn("test", io24_presets.load(stream.name))
                gc.collect()
        self.assertFalse([warning for warning in caught
                          if issubclass(warning.category, ResourceWarning)])


class HostRefinementTests(unittest.TestCase):
    @staticmethod
    def _multiband_state():
        bands = {}
        for index, name in enumerate(io24_mbc.BANDS):
            bands[name] = {
                "type": ("standard", "tube", "fet", "standard")[index],
                "threshold": -18.0 - index,
                "ratio": 2.0 + index,
                "attack": 4.0 + index,
                "release": 90.0 + index * 10.0,
                "knee": 2.0 + index,
                "makeup": 1.0 + index,
                "auto": index == 0,
                "limit": index == 1,
                "key_filter": index == 2,
                "key": 120.0 * (index + 1),
                "listen": index == 3,
            }
        return {
            "version": 1,
            "enabled": True,
            "xovers": [140.0, 900.0, 4200.0],
            "bands": bands,
        }

    def test_multiband_state_round_trips_in_host_file_only(self):
        class SnapshotIo24(io24.Io24):
            def __init__(self):
                self._shadow = {}
                self._shadow_dirty = False
                self._shadow_flushed = 0.0
                self._shadow_persist = False
                self.applied = []

            def read_params(self):
                return {}

            def set_gain(self, channel, db):
                self.applied.append((channel, db))

        state = self._multiband_state()
        pan = {"version": 2,
               "balances": {"mixa": 0.25, "mixb": 0.75}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "host.json"
            source = SnapshotIo24()
            saved = source.save_preset(
                path, host_features={"multiband": state, "pan": pan})
            self.assertEqual(saved["host_features"]["multiband"], state)
            self.assertEqual(saved["host_features"]["pan"], pan)
            self.assertNotIn("host_features", source.snapshot())

            restored = SnapshotIo24()
            restored.load_preset(path)
            self.assertEqual(
                restored._last_preset_load_report["host_features"],
                {"multiband": state, "pan": pan})

    def test_bus_balance_state_is_strict_and_defaults_centered(self):
        expected = {
            "version": 2,
            "balances": {"mixa": 0.5, "mixb": 0.5},
        }

        self.assertEqual(io24_mbc.default_pan_snapshot(), expected)
        self.assertEqual(io24_mbc.validate_pan_snapshot(expected), expected)
        invalid_states = (
            {"version": 2, "balances": {"mixa": 0.5}},
            {"version": 2,
             "balances": {"mixa": True, "mixb": 0.5}},
            {"version": 2,
             "balances": {"mixa": 0.5, "mixb": 1.1}},
            {"version": 2,
             "balances": {"mixa": 0.5, "mixb": float("nan")}},
        )
        for state in invalid_states:
            with self.subTest(state=state), self.assertRaises(ValueError):
                io24_mbc.validate_pan_snapshot(state)

    def test_legacy_input_pan_migrates_to_neutral_bus_balance(self):
        legacy = {
            "version": 1,
            "enabled": True,
            "positions": [0.2, 0.85],
        }

        state, notices = io24_mbc.normalise_pan_snapshot(legacy)

        self.assertEqual(state, io24_mbc.default_pan_snapshot())
        self.assertEqual(notices, [
            "legacy input pan was not applied; Mix A/B balances centered",
        ])

    def test_legacy_input_pan_is_validated_before_migration(self):
        with self.assertRaisesRegex(ValueError, "legacy pan position"):
            io24_mbc.normalise_pan_snapshot({
                "version": 1,
                "enabled": True,
                "positions": [0.5, 1.2],
            })

    def test_host_file_migrates_legacy_pan_and_reports_the_discard(self):
        class SnapshotIo24(io24.Io24):
            def __init__(self):
                self._shadow = {}
                self._shadow_dirty = False
                self._shadow_flushed = 0.0
                self._shadow_persist = False
                self.applied = []

            def set_gain(self, channel, db):
                self.applied.append((channel, db))

        legacy = {"version": 1, "enabled": True,
                  "positions": [0.2, 0.85]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-host.json"
            path.write_text(json.dumps({
                "version": 1,
                "live": {"input1Gain": 31.0},
                "calls": {},
                "host_features": {"pan": legacy},
            }))
            device = SnapshotIo24()

            device.load_preset(path)

        report = device._last_preset_load_report
        self.assertEqual(device.applied, [(1, 31.0)])
        self.assertEqual(
            report["host_features"]["pan"],
            io24_mbc.default_pan_snapshot())
        self.assertEqual(report["host_feature_migrations"], [
            "legacy input pan was not applied; Mix A/B balances centered",
        ])

    def test_malformed_legacy_pan_fails_before_device_state_is_applied(self):
        class SnapshotIo24(io24.Io24):
            def __init__(self):
                self._shadow = {}
                self._shadow_dirty = False
                self._shadow_flushed = 0.0
                self._shadow_persist = False
                self.applied = []

            def set_gain(self, channel, db):
                self.applied.append((channel, db))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-legacy-host.json"
            path.write_text(json.dumps({
                "version": 1,
                "live": {"input1Gain": 31.0},
                "calls": {},
                "host_features": {"pan": {
                    "version": 1,
                    "enabled": True,
                    "positions": [0.5, 1.2],
                }},
            }))
            device = SnapshotIo24()

            with self.assertRaisesRegex(ValueError, "legacy pan position"):
                device.load_preset(path)

        self.assertEqual(device.applied, [])

    def test_saving_legacy_pan_emits_only_version_two_bus_balance(self):
        class SnapshotIo24(io24.Io24):
            def __init__(self):
                self._shadow = {}
                self._shadow_dirty = False
                self._shadow_flushed = 0.0
                self._shadow_persist = False

            def read_params(self):
                return {}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "normalized-host.json"
            device = SnapshotIo24()

            saved = device.save_preset(path, host_features={"pan": {
                "version": 1,
                "enabled": False,
                "positions": [0.1, 0.9],
            }})

        self.assertEqual(
            saved["host_features"]["pan"],
            io24_mbc.default_pan_snapshot())

    def test_bus_balance_is_center_unity_without_crossfeed(self):
        self.assertEqual(io24_mbc.balance_coefficients(0.0), (1.0, 0.0))
        self.assertEqual(io24_mbc.balance_coefficients(0.5), (1.0, 1.0))
        self.assertEqual(io24_mbc.balance_coefficients(1.0), (0.0, 1.0))
        quarter = io24_mbc.balance_coefficients(0.25)
        three_quarter = io24_mbc.balance_coefficients(0.75)
        self.assertEqual(quarter[0], 1.0)
        self.assertEqual(three_quarter[1], 1.0)
        self.assertAlmostEqual(quarter[1], math.sqrt(0.5))
        self.assertAlmostEqual(quarter[1], three_quarter[0])

    def test_bus_graph_selects_only_its_exact_capture_pair(self):
        mixa = io24_mbc.build_bus_source_graph("mixa", 0.5)
        mixb = io24_mbc.build_bus_source_graph("mixb", 0.5)

        self.assertEqual(mixa["inputs"], [
            "src0:In", "src1:In", "src2:In",
            "src3:In", "src4:In", "src5:In",
        ])
        self.assertEqual(mixb["inputs"], mixa["inputs"])
        self.assertEqual(mixa["outputs"],
                         ["balance_l:Out", "balance_r:Out"])
        self.assertEqual(mixb["outputs"], mixa["outputs"])
        mixa_routes = {(link["output"], link["input"])
                       for link in mixa["links"]}
        mixb_routes = {(link["output"], link["input"])
                       for link in mixb["links"]}
        self.assertIn(("src2:Out", "balance_l:In"), mixa_routes)
        self.assertIn(("src3:Out", "balance_r:In"), mixa_routes)
        self.assertIn(("src4:Out", "balance_l:In"), mixb_routes)
        self.assertIn(("src5:Out", "balance_r:In"), mixb_routes)
        self.assertFalse(any(route[0] in {"src0:Out", "src1:Out"}
                             for route in mixa_routes | mixb_routes))

    def test_bus_source_conf_is_passive_source_without_playback_target(self):
        for bus, label in (("mixa", "io24 Host Mix A"),
                           ("mixb", "io24 Host Mix B")):
            with self.subTest(bus=bus):
                conf = io24_mbc.build_bus_source_conf(
                    bus, "alsa_input.usb-PreSonus_io24", 0.5)
                self.assertIn(
                    '"target.object": "alsa_input.usb-PreSonus_io24"', conf)
                self.assertIn('"media.class": "Stream/Input/Audio"', conf)
                self.assertIn('"media.class": "Audio/Source"', conf)
                self.assertIn('"node.description": "%s"' % label, conf)
                self.assertEqual(conf.count('"stream.dont-remix": true'), 2)
                self.assertEqual(conf.count('"node.passive": true'), 2)
                self.assertNotIn('"media.class": "Audio/Sink"', conf)
                self.assertNotIn("alsa_output", conf)

    def test_io24_audio_node_discovery_keeps_input_and_output_distinct(self):
        listing = """id 42, type PipeWire:Interface:Node/3
            node.name = \"alsa_input.usb-PreSonus_Revelator_io24-00.pro-input-0\"
            node.description = \"Revelator io24 Pro Input\"
        id 43, type PipeWire:Interface:Node/3
            node.name = \"alsa_output.usb-PreSonus_Revelator_io24-00.pro-output-0\"
            node.description = \"Revelator io24 Pro Output\"
        """
        completed = SimpleNamespace(stdout=listing)
        with mock.patch.object(io24_mbc.subprocess, "run",
                               return_value=completed):
            self.assertEqual(
                io24_mbc.find_io24_capture_source(),
                "alsa_input.usb-PreSonus_Revelator_io24-00.pro-input-0")
            self.assertEqual(
                io24_mbc.find_io24_sink(),
                "alsa_output.usb-PreSonus_Revelator_io24-00.pro-output-0")

    def test_invalid_multiband_file_fails_before_device_state_is_applied(self):
        class SnapshotIo24(io24.Io24):
            def __init__(self):
                self._shadow = {}
                self._shadow_dirty = False
                self._shadow_flushed = 0.0
                self._shadow_persist = False
                self.applied = []

            def set_gain(self, channel, db):
                self.applied.append((channel, db))

        bad = self._multiband_state()
        bad["bands"]["low"]["ratio"] = 0.5
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({
                "version": 1,
                "live": {"input1Gain": 31.0},
                "calls": {},
                "host_features": {"multiband": bad},
            }))
            device = SnapshotIo24()
            with self.assertRaisesRegex(ValueError, "multiband.*ratio"):
                device.load_preset(path)
            self.assertEqual(device.applied, [])

    def test_multiband_graph_starts_from_every_saved_audible_value(self):
        state = self._multiband_state()
        normalized = io24_mbc.validate_snapshot(state)
        graph = io24_mbc.build_graph(
            normalized["xovers"], True, state=normalized)
        nodes = {node["name"]: node for node in graph["nodes"]}

        low = nodes["c0"]["control"]
        self.assertEqual(low["Threshold level (dB)"], -18.0)
        self.assertEqual(low["Ratio (1:n)"], 2.0)
        self.assertEqual(low["Attack time (ms)"], 4.0)
        self.assertEqual(nodes["k2"]["control"]["Freq"], 360.0)
        self.assertEqual(nodes["c2"]["control"]["Chain balance"], 1.0)
        self.assertEqual(nodes["lc3"]["control"]["Mult"], 0.0)
        self.assertEqual(nodes["lk3"]["control"]["Mult"], 1.0)

    def test_spectrum_uses_overlapping_windows_and_time_based_release(self):
        frame, remainder = io24gtk.Spectrum._take_window(
            b"0123456789", need=8, hop=2)
        self.assertEqual(frame, b"01234567")
        self.assertEqual(remainder, b"23456789")
        self.assertEqual(io24gtk.Spectrum.BINS, 256)
        self.assertGreaterEqual(48000 / io24gtk.Spectrum.HOP, 40.0)
        self.assertAlmostEqual(
            io24gtk.Spectrum._release_alpha(
                io24gtk.Spectrum.RELEASE_TAU_S), math.exp(-1.0), places=7)

    def test_curve_drag_publishes_one_coherent_band_update(self):
        class Value:
            def __init__(self, host, key):
                self.host = host
                self.key = key

            def set_value(self, value):
                self.host.band[self.key] = value
                if not self.host._adopt_mute:
                    self.host.pushes.append(dict(self.host.band))

        host = SimpleNamespace(
            band={"shape": "peaking", "freq": 100.0,
                  "gain": 0.0, "q": 0.7},
            _adopt_mute=False,
            pushes=[],
            invalidate_curve=lambda: None,
            racks={},
        )
        curve = SimpleNamespace(
            win=host,
            channel=1,
            drag_band=0,
            _start=(10.0, 10.0, 100.0, 0.0),
            bands=[host.band],
            wid=lambda key: Value(host, key),
            get_width=lambda: 200,
            get_height=lambda: 100,
            _f_from_x=lambda x, _w: x * 10.0,
            queue_draw=lambda: None,
            _drag_push=lambda: host.pushes.append(dict(host.band)),
        )

        io24gtk.EQCurve._drag_update(curve, None, 20.0, -10.0)

        self.assertEqual(host.pushes, [{
            "shape": "peaking", "freq": 300.0,
            "gain": 3.6, "q": 0.7,
        }])

    def test_continuous_hpf_move_uses_inline_feedback_without_toast(self):
        messages = []
        submitted = []
        host = SimpleNamespace(
            link_both=False,
            _adopt_mute=False,
            hpf_by_ch={1: 24.0, 2: 24.0},
            ctl=SimpleNamespace(submit=submitted.append),
            _adopt_hpf_controls=lambda _ch, _hz: None,
            racks={},
            say=messages.append,
        )

        io24gtk.Win.set_hpf(host, 1, 347.0)

        self.assertEqual(len(submitted), 1)
        self.assertEqual(messages, [])

    def test_preset_indicator_identifies_slot_and_respects_reduced_motion(self):
        visual = getattr(
            io24gtk, "preset_indicator_visual",
            lambda *_args: {"glyph": None, "opacity": None, "radius": None})
        slow_a = visual(True, 0, 0.0, True)
        slow_b = visual(True, 0, 0.8, True)
        fast_b = visual(True, 1, 0.8, True)

        self.assertEqual(slow_a["glyph"], "●")
        self.assertEqual(fast_b["glyph"], "●")
        self.assertNotEqual(slow_a["opacity"], slow_b["opacity"])
        # Internal slot index 0 is user-facing Slot 1 (slow); index 1 is
        # user-facing Slot 2 (twice the breathing rate).
        self.assertGreater(fast_b["opacity"], slow_b["opacity"])
        reduced_slow = visual(True, 0, 0.8, False)
        reduced_fast = visual(True, 1, 0.8, False)
        self.assertEqual(reduced_slow["opacity"], 1.0)
        self.assertEqual(reduced_fast["opacity"], 1.0)
        self.assertLess(reduced_slow["radius"], reduced_fast["radius"])
        bypassed = visual(False, 1, 0.8, True)
        self.assertEqual(bypassed["glyph"], "○")
        self.assertEqual(bypassed["opacity"], 0.28)

    def test_bus_meter_columns_have_exact_compact_labels(self):
        columns = getattr(io24gtk, "bus_meter_columns", lambda: ())
        self.assertEqual(columns(), (
            ("main", "Main", "Main output"),
            ("mixa", "Mix A", "USB capture channels 3–4"),
            ("mixb", "Mix B", "USB capture channels 5–6"),
        ))

    def test_mixer_removes_input_pan_and_builds_aligned_bus_knobs(self):
        input_source = inspect.getsource(io24gtk.Win._input_strip)
        bus_source = inspect.getsource(io24gtk.Win._bus_strip)

        self.assertNotIn("Knob(", input_source)
        self.assertNotIn("Host input pan", input_source + bus_source)
        self.assertNotIn("Gtk.ToggleButton", bus_source)
        self.assertIn("self.bus_balance_knobs", bus_source)
        self.assertIn("Main is not exposed by USB capture", bus_source)
        self.assertIn("knob.set_sensitive(False)", bus_source)

    def test_bus_balance_move_updates_only_selected_bus_without_routine_toast(self):
        class Label:
            def set_text(self, value):
                self.value = value

        class Sources:
            def __init__(self):
                self.calls = []

            def set_balance(self, bus, value):
                self.calls.append((bus, value))
                return True

        sources = Sources()
        host = SimpleNamespace(
            _pan_mute=False,
            pan_state=io24_mbc.default_pan_snapshot(),
            bus_balance_labels={"mixa": Label(), "mixb": Label()},
            bus_sources=sources,
        )

        io24gtk.Win._bus_balance_moved(host, "mixa", 0.8)

        self.assertEqual(host.pan_state["balances"],
                         {"mixa": 0.8, "mixb": 0.5})
        self.assertEqual(sources.calls, [("mixa", 0.8)])
        self.assertNotIn("self.say", inspect.getsource(
            io24gtk.Win._bus_balance_moved))

    def test_failed_bus_balance_move_disables_only_that_source_and_toasts_once(self):
        class Widget:
            def set_text(self, value):
                self.value = value

            def set_sensitive(self, value):
                self.sensitive = value

        messages = []
        host = SimpleNamespace(
            _pan_mute=False,
            pan_state=io24_mbc.default_pan_snapshot(),
            bus_balance_labels={"mixa": Widget(), "mixb": Widget()},
            bus_balance_knobs={"mixa": Widget(), "mixb": Widget()},
            bus_sources=SimpleNamespace(
                set_balance=lambda _bus, _value: False),
            _bus_source_status={"mixa": "ready", "mixb": "ready"},
            say=messages.append,
        )
        host._set_bus_source_status = lambda bus, status, notify=False: (
            io24gtk.Win._set_bus_source_status(
                host, bus, status, notify=notify))

        io24gtk.Win._bus_balance_moved(host, "mixa", 0.7)
        io24gtk.Win._bus_balance_moved(host, "mixa", 0.8)

        self.assertFalse(host.bus_balance_knobs["mixa"].sensitive)
        self.assertNotEqual(
            getattr(host.bus_balance_knobs["mixb"], "sensitive", None), False)
        self.assertEqual(messages, ["io24 Host Mix A source failed to start"])

    def test_bus_source_watchdog_silently_disables_absent_sources(self):
        class Knob:
            def set_sensitive(self, value):
                self.sensitive = value

        class Sources:
            def reconcile(self, capture, balances):
                self.call = (capture, balances)
                return {"mixa": "unavailable", "mixb": "unavailable"}

        messages = []
        sources = Sources()
        host = SimpleNamespace(
            pan_state=io24_mbc.default_pan_snapshot(),
            bus_sources=sources,
            bus_balance_knobs={"mixa": Knob(), "mixb": Knob()},
            _bus_source_status={"mixa": "ready", "mixb": "ready"},
            say=messages.append,
        )
        host._set_bus_source_status = lambda bus, status, notify=False: (
            io24gtk.Win._set_bus_source_status(
                host, bus, status, notify=notify))
        with mock.patch.object(io24_mbc, "find_io24_capture_source",
                               return_value=None):
            keep = io24gtk.Win._bus_source_watchdog(host)

        self.assertTrue(keep)
        self.assertEqual(messages, [])
        self.assertFalse(host.bus_balance_knobs["mixa"].sensitive)
        self.assertFalse(host.bus_balance_knobs["mixb"].sensitive)

    def test_bus_source_failure_toasts_once_and_recovers_independently(self):
        class Knob:
            def set_sensitive(self, value):
                self.sensitive = value

        class Sources:
            def __init__(self):
                self.results = [
                    {"mixa": "failed", "mixb": "ready"},
                    {"mixa": "failed", "mixb": "ready"},
                    {"mixa": "ready", "mixb": "unavailable"},
                ]

            def reconcile(self, _capture, _balances):
                return self.results.pop(0)

        messages = []
        host = SimpleNamespace(
            pan_state=io24_mbc.default_pan_snapshot(),
            bus_sources=Sources(),
            bus_balance_knobs={"mixa": Knob(), "mixb": Knob()},
            _bus_source_status={"mixa": "starting", "mixb": "starting"},
            say=messages.append,
        )
        host._set_bus_source_status = lambda bus, status, notify=False: (
            io24gtk.Win._set_bus_source_status(
                host, bus, status, notify=notify))
        with mock.patch.object(io24_mbc, "find_io24_capture_source",
                               return_value="capture-node"):
            io24gtk.Win._bus_source_watchdog(host)
            io24gtk.Win._bus_source_watchdog(host)
            io24gtk.Win._bus_source_watchdog(host)

        self.assertEqual(messages, ["io24 Host Mix A source failed to start"])
        self.assertTrue(host.bus_balance_knobs["mixa"].sensitive)
        self.assertFalse(host.bus_balance_knobs["mixb"].sensitive)

    def test_bus_snapshot_adoption_does_not_touch_source_lifecycle(self):
        class Knob:
            def set_value(self, value, notify=True):
                self.value = value
                self.notify = notify

        class Label:
            def set_text(self, value):
                self.value = value

        host = SimpleNamespace(
            _pan_mute=False,
            pan_state=io24_mbc.default_pan_snapshot(),
            bus_balance_knobs={"mixa": Knob(), "mixb": Knob()},
            bus_balance_labels={"mixa": Label(), "mixb": Label()},
        )
        state = {"version": 2, "balances": {"mixa": 0.2, "mixb": 0.9}}

        message = io24gtk.Win._adopt_pan_state(host, state)

        self.assertEqual(host.pan_state, state)
        self.assertFalse(host.bus_balance_knobs["mixa"].notify)
        self.assertFalse(host.bus_balance_knobs["mixb"].notify)
        self.assertEqual(message, "Mix A/B balances restored (Host only)")

    def test_legacy_notice_is_appended_only_to_completed_load_message(self):
        notice = "legacy input pan was not applied; Mix A/B balances centered"
        append = getattr(io24gtk, "append_host_migration_notices", None)

        self.assertIsNotNone(append)
        self.assertEqual(append("Loaded 4 host-file settings", [notice]),
                         "Loaded 4 host-file settings; " + notice)
        self.assertIsNone(append(None, [notice]))

    def test_application_shutdown_stops_both_bus_sources(self):
        stopped = []
        app = SimpleNamespace(win=SimpleNamespace(
            mbc=None,
            bus_sources=SimpleNamespace(stop=lambda: stopped.append(True))))
        with mock.patch.object(io24gtk.Adw.Application, "do_shutdown"):
            io24gtk.App.do_shutdown(app)
        self.assertEqual(stopped, [True])

    def test_user_docs_describe_passive_bus_sources_and_unavailable_main(self):
        for filename in ("README.md", "GUIDE.md"):
            with self.subTest(filename=filename):
                content = Path(filename).read_text()
                self.assertIn("io24 Host Mix A", content)
                self.assertIn("io24 Host Mix B", content)
                self.assertIn("USB capture 3–4", content)
                self.assertIn("USB capture 5–6", content)
                self.assertIn("Main is not exposed by USB capture", content)
                self.assertIn("route nowhere by default", content)
                self.assertIn("version 2", content)
                self.assertNotIn("Host input pan", content)
                self.assertNotIn("capture→playback", content)

    def test_spectrum_resolves_low_guitar_without_slower_updates(self):
        spectrum = io24gtk.Spectrum(autostart=False)

        resolution = getattr(spectrum, "frequency_resolution_hz",
                             lambda: float("inf"))
        interval = getattr(spectrum, "update_interval_seconds",
                           lambda: float("inf"))
        self.assertLessEqual(resolution(), 6.0)
        self.assertLessEqual(interval(), 0.022)

    def test_reconnect_ui_keeps_connection_banner_without_reapply_prompt(self):
        init_source = inspect.getsource(io24gtk.Win.__init__)
        window_source = inspect.getsource(io24gtk.Win)

        self.assertIn("self.offline_banner", init_source)
        self.assertNotIn("reconcile_banner", window_source)
        self.assertNotIn("def _reapply_cached", window_source)
        self.assertNotIn("def _forget_cached", window_source)

    def test_routine_control_changes_across_tabs_do_not_toast(self):
        messages = []
        submitted = []

        phones = SimpleNamespace(
            _phones_source_mute=False,
            _set=lambda *args: submitted.append(args),
            say=messages.append,
        )
        io24gtk.Win._phones_source_changed(
            phones, SimpleNamespace(get_selected=lambda: 1), None)

        presets = SimpleNamespace(
            _preset_sync=False,
            PRESET_BASE=io24gtk.Win.PRESET_BASE,
            ctl=SimpleNamespace(submit=submitted.append),
            say=messages.append,
        )
        io24gtk.Win._preset_mode_changed(
            presets, SimpleNamespace(get_selected=lambda: 1), None)
        io24gtk.Win._slot_changed(presets, 1, 1)

        order = SimpleNamespace(
            _order_mute=False, _adopt_mute=False, link_both=False,
            order_by_ch={1: False, 2: False},
            _current_channel=lambda: 1,
            set_order=lambda *args: submitted.append(args),
            say=messages.append,
        )
        io24gtk.Win._order_changed(
            order, SimpleNamespace(get_selected=lambda: 1), None)

        delay_scale = SimpleNamespace(
            get_value=lambda: 12.0,
            set_sensitive=lambda _sensitive: None,
        )
        device_page = SimpleNamespace(
            _dev_mute=False, _delay_mute=False,
            _quanta=[128], _delay_buses=[("main", "Main")],
            delay_scale=delay_scale,
            ctl=SimpleNamespace(submit=submitted.append),
            say=messages.append,
        )
        with mock.patch.object(io24gtk, "pw_set", return_value=(True, "ok")):
            io24gtk.Win._quantum_changed(
                device_page, SimpleNamespace(get_selected=lambda: 0), None)
        io24gtk.Win._delay_bus_changed(
            device_page, SimpleNamespace(get_selected=lambda: 0), None)

        self.assertEqual(messages, [])

    def test_voice_fx_parameter_success_and_offline_state_are_silent(self):
        class Value:
            def __init__(self, value):
                self.value = value

            def get_value(self):
                return self.value

            def get_active(self):
                return bool(self.value)

            def get_selected(self):
                return int(self.value)

        class Device:
            def __init__(self):
                self.fail = False

            def set_voicefx_channel(self, _channel):
                pass

            def set_fx(self, _model, **_params):
                if self.fail:
                    raise RuntimeError("broken transport")
                return 3

        class Controller:
            def __init__(self, device):
                self.dev = device

            def submit(self, callback):
                callback(self.dev)

        device = Device()
        messages = []
        host = SimpleNamespace(
            _fx_mute=False,
            FX_ORDER=io24gtk.Win.FX_ORDER,
            _fx_last_sent_device=None,
            _fx_last_sent_target=None,
            ctl=Controller(device),
            fx_arm=Value(True), fx_model=Value(0), fx_target=Value(0),
            fx_params={"transformer": {
                name: Value(default)
                for name, _title, _lo, _hi, _step, default, _fmt
                in io24gtk.Win.FX_PARAMS["transformer"]
            }},
            say=messages.append,
        )
        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            io24gtk.Win._push_fx(host)
            self.assertEqual(messages, [])

            device.fail = True
            io24gtk.Win._push_fx(host)
            self.assertEqual(messages, [
                "Voice FX send failed: broken transport",
            ])

            host.ctl.dev = None
            io24gtk.Win._push_fx(host)
            self.assertEqual(messages, [
                "Voice FX send failed: broken transport",
            ])

    def test_preview_hold_uses_inline_status_without_bottom_toast(self):
        class PreviewRow:
            def __init__(self):
                self.subtitle = None

            def set_subtitle(self, subtitle):
                self.subtitle = subtitle

        class Hotkeys:
            def press(self, _dev, _channel):
                return {"status": "PREVIEW_ACTIVE"}

            def release(self, _dev, _channel):
                return {"status": "NORMAL_RESTORED"}

        class Controller:
            dev = object()

            def submit(self, callback):
                callback(self.dev)

        row = PreviewRow()
        messages = []
        host = SimpleNamespace(
            _hotkey_sync=False, hotkeys=Hotkeys(), ctl=Controller(),
            hotkey_rows={1: (row, object(), object())},
            say=messages.append,
        )
        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            io24gtk.Win._hotkey_pressed(host, None, 1, 0, 0, 1)
            self.assertEqual(row.subtitle, "Preview active; release to restore")
            io24gtk.Win._hotkey_released(host, None, 1, 0, 0, 1)

        self.assertEqual(row.subtitle, "Normal sound restored")
        self.assertEqual(messages, [])

    def test_factory_load_reports_worker_completion_not_early_queueing(self):
        class Toggle:
            def set_active(self, _active):
                pass

            def queue_draw(self):
                pass

        class Presets:
            def __init__(self):
                self.fail = False

            def load(self):
                return {"Clean": {
                    "filter": {"hpf": 24.0}, "gate": {}, "comp": {},
                    "limit": {}, "opt": {}, "voicefx": {},
                }}

            def direct_apply_support(self, _preset):
                return True, ""

            def to_bands(self, _preset):
                return []

            def apply_preset(self, _dev, _preset, _channel, with_fx=False):
                if self.fail:
                    raise RuntimeError("apply broke")

        class Controller:
            def __init__(self):
                self.pending = []

            def submit(self, callback):
                self.pending.append(callback)

        messages = []
        presets = Presets()
        ctl = Controller()
        toggle = Toggle()
        host = SimpleNamespace(
            PR=presets, ctl=ctl, link_both=False,
            _factory_target_channel=lambda: 1,
            _current_channel=lambda: 1,
            bands_by_ch={1: []}, dyn_by_ch={1: {}},
            hpf_by_ch={1: 24.0}, order_by_ch={1: False},
            invalidate_curve=lambda: None, _adopt_mute=False,
            _adopt_band=lambda _ch: None,
            _adopt_hpf_controls=lambda _ch, _hz: None,
            _adopt_dynamics=lambda _ch, _preset: None,
            _sync_order_row=lambda _ch: None,
            w={1: {"gate_on": toggle, "comp_on": toggle,
                   "lim_on": toggle, "curve": toggle}},
            racks={}, say=messages.append,
        )

        io24gtk.Win._load_factory(host, None, "Clean", False)
        self.assertEqual(messages, [])
        self.assertEqual(len(ctl.pending), 1)

        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            ctl.pending.pop()(object())
        self.assertEqual(messages, ["Loaded Clean on Channel 1"])

        presets.fail = True
        io24gtk.Win._load_factory(host, None, "Clean", False)
        with mock.patch.object(io24gtk.GLib, "idle_add",
                               side_effect=lambda fn, *args: fn(*args)):
            ctl.pending.pop()(object())
        self.assertEqual(messages[-1], "Clean load failed: apply broke")

    def test_mixer_layout_fits_width_instead_of_enabling_horizontal_scroll(self):
        class Box:
            def __init__(self, **kwargs):
                self.homogeneous = kwargs.get("homogeneous", False)
                self.children = []

            def set_margin_start(self, value):
                self.margin_start = value

            def set_margin_end(self, value):
                self.margin_end = value

            def append(self, child):
                self.children.append(child)

        class Strip:
            def set_hexpand(self, value):
                self.hexpand = value

        class Scrolled:
            def set_child(self, child):
                self.child = child

            def set_policy(self, horizontal, vertical):
                self.policy = (horizontal, vertical)

        strips = [Strip() for _ in range(4)]
        host = SimpleNamespace(
            _input_strip=lambda ch: strips[ch - 1],
            _bus_strip=lambda: strips[2],
            _master_strip=lambda: strips[3],
        )
        with mock.patch.object(io24gtk.Gtk, "Box", Box), \
                mock.patch.object(io24gtk.Gtk, "ScrolledWindow", Scrolled):
            page = io24gtk.Win._mixer_page(host)

        self.assertFalse(page.child.homogeneous)
        self.assertEqual(
            page.policy[0], io24gtk.Gtk.PolicyType.NEVER)
        self.assertEqual([strip.hexpand for strip in strips],
                         [True, True, False, False])

    def test_factory_sound_filter_matches_name_and_description(self):
        self.assertTrue(io24gtk.factory_preset_matches(
            "guitar", "Bright Guitar", "Open modern instrument curve"))
        self.assertTrue(io24gtk.factory_preset_matches(
            "modern", "Bright Guitar", "Open modern instrument curve"))
        self.assertFalse(io24gtk.factory_preset_matches(
            "vocal", "Bright Guitar", "Open modern instrument curve"))

    def test_eq_drag_throttle_keeps_the_final_coherent_update(self):
        sent = []
        callbacks = []
        now = [1.0]
        throttle = io24gtk.Throttle(sent.append, interval=0.012)

        def timeout_add(_wait, callback):
            callbacks.append(callback)
            return len(callbacks)

        with mock.patch.object(io24gtk.time, "monotonic",
                               side_effect=lambda: now[0]), \
                mock.patch.object(io24gtk.GLib, "timeout_add",
                                  side_effect=timeout_add):
            throttle({"freq": 100.0, "gain": 0.0})
            now[0] = 1.004
            throttle({"freq": 200.0, "gain": 1.0})
            now[0] = 1.009
            throttle({"freq": 300.0, "gain": 2.0})
            now[0] = 1.012
            callbacks[0]()

        self.assertEqual(sent, [
            {"freq": 100.0, "gain": 0.0},
            {"freq": 300.0, "gain": 2.0},
        ])

    def test_multiband_controls_capture_and_restore_one_exact_chain(self):
        class Control:
            def __init__(self, value=0.0, active=False, selected=0):
                self.value = value
                self.active = active
                self.selected = selected
                self.sensitive = True

            def get_value(self):
                return self.value

            def set_value(self, value):
                self.value = value

            def get_active(self):
                return self.active

            def set_active(self, active):
                self.active = active

            def get_selected(self):
                return self.selected

            def set_selected(self, selected):
                self.selected = selected

            def set_sensitive(self, sensitive):
                self.sensitive = sensitive

        class Chain:
            def __init__(self):
                self.stops = 0
                self.starts = []

            def stop(self):
                self.stops += 1

            def start(self, **kwargs):
                self.starts.append(kwargs)
                return True

        state = self._multiband_state()
        controls = {"x%d" % index: Control(value)
                    for index, value in enumerate(state["xovers"])}
        for index, band in enumerate(io24_mbc.BANDS):
            values = state["bands"][band]
            controls[(index, "type")] = Control(
                selected=("standard", "tube", "fet").index(values["type"]))
            for key, field in (("thr", "threshold"), ("ratio", "ratio"),
                               ("attack", "attack"),
                               ("release", "release"), ("knee", "knee"),
                               ("makeup", "makeup"), ("keyf", "key")):
                controls[(index, key)] = Control(values[field])
            for key, field in (("auto", "auto"), ("limit", "limit"),
                               ("keyon", "key_filter"),
                               ("listen", "listen")):
                controls[(index, key)] = Control(active=values[field])
        chain = Chain()
        host = SimpleNamespace(
            mbc_widget=object(), mbc_row=Control(active=True),
            mbc_ctl=controls, mbc=chain, _mbc_mute=False)

        self.assertEqual(io24gtk.Win._mbc_snapshot_state(host), state)
        for control in controls.values():
            control.value = 0.0
            control.active = False
            control.selected = 0
        with mock.patch.object(io24_mbc, "sc4_available",
                               return_value="/usr/lib/ladspa/sc3_1427.so"), \
                mock.patch.object(io24_mbc, "find_io24_sink",
                                  return_value="alsa_output.io24"):
            status = io24gtk.Win._adopt_mbc_state(host, state)

        self.assertEqual(status, "multiband restored on (Host only)")
        self.assertEqual(chain.stops, 1)
        self.assertEqual(chain.starts, [{
            "target": "alsa_output.io24", "state": state,
        }])
        self.assertTrue(host.mbc_row.active)
        self.assertEqual(io24gtk.Win._mbc_snapshot_state(host), state)
        self.assertFalse(controls[(0, "makeup")].sensitive)

    def test_multiband_restore_never_claims_enabled_after_chain_failure(self):
        state = self._multiband_state()

        class Control:
            def __init__(self):
                self.value = 0.0
                self.active = False
                self.selected = 0

            def set_value(self, value):
                self.value = value

            def set_active(self, active):
                self.active = active

            def get_active(self):
                return self.active

            def set_selected(self, selected):
                self.selected = selected

            def set_sensitive(self, _sensitive):
                pass

        class Chain:
            def stop(self):
                pass

            def start(self, **_kwargs):
                return False

        controls = {"x%d" % index: Control() for index in range(3)}
        for index in range(4):
            controls[(index, "type")] = Control()
            for key in ("thr", "ratio", "attack", "release", "knee",
                        "makeup", "keyf", "auto", "limit", "keyon",
                        "listen"):
                controls[(index, key)] = Control()
        host = SimpleNamespace(
            mbc_widget=object(), mbc_row=Control(), mbc_ctl=controls,
            mbc=Chain(), _mbc_mute=False)
        with mock.patch.object(io24_mbc, "sc4_available",
                               return_value="/usr/lib/ladspa/sc3_1427.so"), \
                mock.patch.object(io24_mbc, "find_io24_sink",
                                  return_value="alsa_output.io24"):
            status = io24gtk.Win._adopt_mbc_state(host, state)

        self.assertIn("did not start", status)
        self.assertFalse(host.mbc_row.active)
        self.assertFalse(host._mbc_mute)

    def test_host_file_worker_uses_its_serialized_device_argument(self):
        source = inspect.getsource(io24gtk.Win._pick)

        self.assertIn("dev.save_preset(", source)
        self.assertIn("dev.load_preset(", source)
        self.assertNotIn("self.ctl.dev.save_preset(", source)
        self.assertNotIn("self.ctl.dev.load_preset(", source)

    def test_preview_copy_drops_the_hotkey_metaphor(self):
        source = "\n".join(inspect.getsource(method) for method in (
            io24gtk.Win._host_hotkey_group,
            io24gtk.Win._hotkey_capture,
            io24gtk.Win._hotkey_pressed,
            io24gtk.Win._hotkey_released,
        ))

        self.assertNotIn("Hot Key", source)
        self.assertIn("Temporary A/B previews (Host only)", source)
        self.assertIn("Hold to preview", source)

    def test_multiband_chain_start_failure_cleans_private_config(self):
        with tempfile.TemporaryDirectory() as parent:
            config = Path(parent) / "chain"
            config.mkdir()
            chain = io24_mbc.Chain()
            with mock.patch.object(io24_mbc.os.path, "exists",
                                   return_value=True), \
                    mock.patch.object(io24_mbc.tempfile, "mkdtemp",
                                      return_value=str(config)), \
                    mock.patch.object(io24_mbc.shutil, "copy"), \
                    mock.patch.object(io24_mbc.subprocess, "Popen",
                                      side_effect=OSError("spawn failed")):
                started = chain.start(
                    target="alsa_output.io24",
                    state=self._multiband_state())

            self.assertFalse(started)
            self.assertFalse(config.exists())
            self.assertIsNone(chain.proc)
            self.assertIsNone(chain.conf_path)

    def test_multiband_stop_cleans_config_when_kill_loses_exit_race(self):
        class Process:
            def poll(self):
                return None

            def terminate(self):
                pass

            def wait(self, timeout):
                raise io24_mbc.subprocess.TimeoutExpired("pipewire", timeout)

            def kill(self):
                raise ProcessLookupError("already exited")

        with tempfile.TemporaryDirectory() as parent:
            config = Path(parent) / "old-chain"
            config.mkdir()
            chain = io24_mbc.Chain()
            chain.proc = Process()
            chain.conf_path = str(config)

            chain.stop()

            self.assertFalse(config.exists())
            self.assertIsNone(chain.proc)
            self.assertIsNone(chain.conf_path)

    def test_configured_start_replaces_a_running_stale_chain(self):
        class OldProcess:
            stopped = False

            def poll(self):
                return None

            def terminate(self):
                self.stopped = True

            def wait(self, timeout):
                return 0

        class NewProcess:
            def poll(self):
                return None

        with tempfile.TemporaryDirectory() as parent:
            old_config = Path(parent) / "old-chain"
            new_config = Path(parent) / "new-chain"
            old_config.mkdir()
            new_config.mkdir()
            old_process = OldProcess()
            chain = io24_mbc.Chain()
            chain.proc = old_process
            chain.conf_path = str(old_config)
            with mock.patch.object(io24_mbc.os.path, "exists",
                                   return_value=True), \
                    mock.patch.object(io24_mbc.tempfile, "mkdtemp",
                                      return_value=str(new_config)), \
                    mock.patch.object(io24_mbc.shutil, "copy"), \
                    mock.patch.object(io24_mbc.subprocess, "Popen",
                                      return_value=NewProcess()) as spawn:
                started = chain.start(
                    target="alsa_output.io24",
                    state=self._multiband_state())

            self.assertTrue(started)
            self.assertTrue(old_process.stopped)
            self.assertFalse(old_config.exists())
            self.assertEqual(spawn.call_count, 1)
            self.assertEqual(chain.conf_path, str(new_config))

    def test_repeated_identical_bus_source_start_is_idempotent(self):
        class RunningProcess:
            def poll(self):
                return None

        chain = io24_mbc.BusSourceChain("mixa")
        launches = []

        def launch(configuration, configured=True):
            launches.append((configuration, configured))
            chain.proc = RunningProcess()
            return True

        with mock.patch.object(chain, "_launch", side_effect=launch):
            self.assertTrue(chain.start("capture-node", 0.5))
            self.assertTrue(chain.start("capture-node", 0.5))

        self.assertEqual(len(launches), 1)

    @staticmethod
    def _fake_bus_chain(started=True, node_id="42"):
        class FakeChain:
            def __init__(self):
                self.running = False
                self.starts = []
                self.stops = 0
                self.controls = []

            def start(self, capture_target, balance):
                self.starts.append((capture_target, balance))
                self.running = bool(started)
                return bool(started)

            def node_id(self):
                return node_id if self.running else None

            def set_controls(self, controls):
                self.controls.append(controls)
                return True

            def stop(self):
                self.stops += 1
                self.running = False

        return FakeChain()

    def test_bus_source_manager_isolates_partial_start_failure(self):
        mixa = self._fake_bus_chain(started=False)
        mixb = self._fake_bus_chain(started=True, node_id="84")
        manager = io24_mbc.BusSourceManager(
            chains={"mixa": mixa, "mixb": mixb})

        statuses = manager.reconcile(
            "capture-node", {"mixa": 0.25, "mixb": 0.75}, now=10.0)

        self.assertEqual(statuses, {"mixa": "failed", "mixb": "ready"})
        self.assertEqual(mixa.starts, [("capture-node", 0.25)])
        self.assertEqual(mixb.starts, [("capture-node", 0.75)])

    def test_bus_source_manager_times_out_missing_public_node(self):
        mixa = self._fake_bus_chain(started=True, node_id=None)
        mixb = self._fake_bus_chain(started=True, node_id="84")
        manager = io24_mbc.BusSourceManager(
            chains={"mixa": mixa, "mixb": mixb})
        balances = {"mixa": 0.5, "mixb": 0.5}

        first = manager.reconcile("capture-node", balances, now=10.0)
        expired = manager.reconcile("capture-node", balances, now=15.1)

        self.assertEqual(first["mixa"], "starting")
        self.assertEqual(expired["mixa"], "failed")
        self.assertEqual(expired["mixb"], "ready")
        self.assertEqual(mixa.stops, 1)

    def test_bus_source_manager_updates_only_selected_ready_source(self):
        mixa = self._fake_bus_chain(started=True, node_id="42")
        mixb = self._fake_bus_chain(started=True, node_id="84")
        manager = io24_mbc.BusSourceManager(
            chains={"mixa": mixa, "mixb": mixb})
        manager.reconcile(
            "capture-node", {"mixa": 0.5, "mixb": 0.5}, now=10.0)

        self.assertTrue(manager.set_balance("mixa", 0.8))

        self.assertEqual(len(mixa.controls), 1)
        self.assertEqual(mixb.controls, [])
        self.assertEqual(
            set(mixa.controls[0]), {"balance_l:Mult", "balance_r:Mult"})

    def test_bus_source_manager_stops_both_sources(self):
        mixa = self._fake_bus_chain()
        mixb = self._fake_bus_chain()
        manager = io24_mbc.BusSourceManager(
            chains={"mixa": mixa, "mixb": mixb})

        manager.stop()

        self.assertEqual(mixa.stops, 1)
        self.assertEqual(mixb.stops, 1)


if __name__ == "__main__":
    unittest.main()
