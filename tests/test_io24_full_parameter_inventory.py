#!/usr/bin/env python3
"""Completeness contracts for the exhaustive Host parameter campaign."""

import inspect
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import io24
import io24_fx
import io24gtk


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "runs" / "20260906T165749-0700-host-live-routing-repair" / "PARAMETER-INVENTORY.json"
MATRIX = INVENTORY.with_name("PARAMETER-VERIFICATION-MATRIX.json")
MATRIX_BUILDER = INVENTORY.with_name("build_parameter_matrix.py")


class FullParameterInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads(INVENTORY.read_text())

    def test_mixer_inventory_expands_every_source_bus_cell(self):
        dims = self.inventory["dimensions"]
        cells = {(source, bus) for source in dims["mixer_sources"]
                 for bus in dims["mixer_buses"]}
        expected = {(source, bus) for source in io24.Io24.MIXER_SOURCES
                    for bus in io24.Io24.MIXER_BUSES}
        self.assertEqual(cells, expected)
        self.assertEqual(len(cells), self.inventory["mixer_expansion"]
                         ["generic_backend_cartesian_cells"])
        host_cells = {(source, bus)
                      for source in dims["linux_host_mixer_sources"]
                      for bus in dims["mixer_buses"]}
        self.assertEqual(len(host_cells), self.inventory["mixer_expansion"]
                         ["linux_host_cartesian_cells"])

    def test_voicefx_inventory_matches_every_serialized_builder_field(self):
        common = set(self.inventory["voicefx"]["common"])
        self.assertIn("on", common)
        for model, fields in io24_fx._VOICEFX_PRESET_FIELDS.items():
            serialized = {target for _source, target, _kind in fields}
            inventoried = set(self.inventory["voicefx"][model]) | {"on"}
            self.assertEqual(inventoried, serialized, model)

    def test_gtk_exposes_every_adjustable_voicefx_builder_field(self):
        for model, fields in io24_fx._VOICEFX_PRESET_FIELDS.items():
            required = {target for _source, target, _kind in fields
                        if target != "on"}
            exposed = {row[0] for row in io24gtk.Win.FX_PARAMS[model]}
            self.assertEqual(exposed, required, model)

    def test_gtk_voicefx_ranges_do_not_expose_unverified_extensions(self):
        specs = {model: {row[0]: row for row in rows}
                 for model, rows in io24gtk.Win.FX_PARAMS.items()}
        self.assertEqual(specs["detuner"]["detune"][2:4], (0, 8))
        self.assertEqual(specs["delay"]["time_s"][2:4], (0.0001, 0.25))

    def test_gtk_compressor_contract_is_model_specific_and_complete(self):
        common = set(io24gtk.Win.COMPRESSOR_COMMON_FIELDS)
        self.assertEqual(common, {"on", "model", "keyfilter_hz", "keylisten"})
        expected = {
            0: {"threshold_db", "ratio", "attack_s", "release_s", "gain_db",
                "softknee", "automode"},
            1: {"peak", "gain", "limit_mode"},
            2: {"input_db", "output_db", "attack_s", "release_s",
                "ratio_index"},
        }
        self.assertEqual({model: set(fields) for model, fields in
                          io24gtk.Win.COMPRESSOR_MODEL_FIELDS.items()}, expected)

    def test_compressor_widget_values_reach_exact_selected_builder_fields(self):
        class Value:
            def __init__(self, value):
                self.value = value

            def get_value(self):
                return self.value

            def get_active(self):
                return bool(self.value)

            def get_selected(self):
                return int(self.value)

        base = {
            "ckey": Value(1250.0), "cklisten": Value(True),
            "cth": Value(-19.0), "rat": Value(4.5), "catk": Value(0.011),
            "crel": Value(0.27), "mk": Value(3.25), "knee": Value(True),
            "auto": Value(False), "tpeak": Value(63.0), "tgain": Value(57.0),
            "climit": Value(True), "finput": Value(-31.0),
            "foutput": Value(-12.0), "fatk": Value(0.00023),
            "frel": Value(0.81), "fratio": Value(4),
        }
        host = SimpleNamespace(w={1: dict(base)})
        for model in range(3):
            host.w[1]["model"] = Value(model)
            selected, kwargs = io24gtk.Win._compressor_kwargs(host, 1)
            self.assertEqual(selected, model)
            self.assertEqual(set(kwargs),
                             set(io24gtk.Win.COMPRESSOR_MODEL_FIELDS[model]) |
                             {"on", "keyfilter_hz", "keylisten"})
        self.assertEqual(io24gtk.Win._compressor_kwargs(host, 1)[1]["output_db"],
                         -12.0)

    def test_manual_fx_write_sends_one_global_complete_model_state(self):
        class Value:
            def __init__(self, value):
                self.value = value

            def get_value(self):
                return self.value

            def get_active(self):
                return bool(self.value)

            def get_selected(self):
                return int(self.value)

        queued = []
        host = SimpleNamespace(
            _fx_mute=False,
            ctl=SimpleNamespace(dev=object(), submit=queued.append),
            fx_arm=Value(True), fx_model=Value(5),
            fx_params={"delay": {
                "time_s": Value(0.173), "feedback": Value(0.82),
                "mix": Value(1.0)}},
            FX_ORDER=io24gtk.Win.FX_ORDER,
            say=lambda _message: None,
        )
        io24gtk.Win._push_fx(host)
        self.assertEqual(len(queued), 1)

        class Device:
            def __init__(self):
                self.calls = []

            def set_fx(self, model, **kwargs):
                self.calls.append(("state", model, kwargs))
                return 2

        dev = Device()
        with mock.patch.object(io24gtk.GLib, "idle_add", return_value=1):
            queued[0](dev)
        self.assertEqual(dev.calls, [
            ("state", "delay", {
                "on": True, "time_s": 0.173, "feedback": 0.82, "mix": 1.0}),
        ])

    def test_unlinked_order_selector_targets_only_visible_channel(self):
        calls = []
        host = SimpleNamespace(
            _order_mute=False, _adopt_mute=False, link_both=False,
            order_by_ch={1: False, 2: False},
            _current_channel=lambda: 2,
            set_order=lambda channel, eq_first: calls.append((channel, eq_first)),
            say=lambda _message: None,
        )
        row = SimpleNamespace(get_selected=lambda: 1)
        io24gtk.Win._order_changed(host, row, None)
        self.assertEqual(calls, [(2, True)])
        self.assertEqual(host.order_by_ch, {1: False, 2: True})

    def test_programmatic_link_sync_cannot_clear_main_balance(self):
        class Column:
            def set_sensitive(self, _value):
                pass

        class Label:
            def set_label(self, _value):
                pass

        writes = []
        host = SimpleNamespace(
            _link_mute=True, ctl=SimpleNamespace(submit=writes.append),
            pan_knobs={}, pan_labels={}, columns={2: Column()},
            col_titles={2: Label()}, say=lambda _message: None,
            _rebuild_chains=lambda: None,
        )
        row = SimpleNamespace(get_active=lambda: False)
        io24gtk.Win._link_changed(host, row, None)
        self.assertEqual(writes, [])

    def test_host_preset_shadow_translates_every_effect_layer_for_ui_adoption(self):
        shadow = {
            "owner": {"fn": "set_processing_channel",
                      "kwargs": {"channel": 1, "source_input": 2}},
            "fx": {"fn": "set_fx", "kwargs": {
                "model": "vocoder", "on": True, "vol": 0.7,
                "carrier_type": 2, "carrier_freq": 180.0, "mix": 0.8}},
            "reverb": {"fn": "set_reverb", "kwargs": {
                "on": True, "size": 0.9, "mix": 1.0,
                "hp_freq": 0.0, "predelay": 0.05}},
            "send": {"fn": "set_fx_mix",
                     "kwargs": {"channel": 2, "value": 0.95}},
            "return": {"fn": "set_send_db", "kwargs": {
                "source": "fxreturn/ch1", "bus": "aux1", "gain_db": -3.0}},
            "comp": {"fn": "set_compressor", "kwargs": {
                "channel": 2, "model": 2, "on": True, "input_db": -31.0,
                "output_db": -12.0, "attack_s": 0.00023,
                "release_s": 0.81, "ratio_index": 4}},
            "mute_mode": {"fn": "set_mute_mode", "kwargs": {"mode": True}},
        }
        state = io24gtk.shadow_ui_state(shadow)
        self.assertNotIn("voicefx_target", state)
        self.assertEqual(state["voicefx"]["model"], "vocoder")
        self.assertEqual(state["processing_mix"], {2: 0.95})
        self.assertEqual(state["reverb_return"], {"mixa": -3.0})
        self.assertEqual(state["compressor"][2]["output_db"], -12.0)
        self.assertTrue(state["mute_mode"])

    def test_all_safe_public_control_entrypoints_are_inventory_backed(self):
        required = {
            "set_hp_volume", "set_main_volume", "set_gain", "set_fx_mix",
            "set_phones_source",
            "set_output_delay", "set_output_delay_bus", "set_monitor_mix",
            "set_phantom", "set_highpass", "set_mute", "set_hp_mute",
            "set_mute_mode",
            "set_channel_link", "set_processing_channel", "set_voicefx_channel",
            "set_limiter", "set_compressor", "set_gate", "set_highpass_freq",
            "set_send_db", "set_send_assigned", "set_bus_master",
            "set_source_mute", "set_bus_mute",
            "set_pair_pan", "mirror_main", "set_fx", "set_preset_mode",
            "set_preset_enabled", "set_preset_slot", "set_reverb",
            "set_eq_band", "set_comp_eq_order", "save_preset", "load_preset",
            "reapply_shadow", "clear_shadow",
        }
        public = {name for name, member in inspect.getmembers(
            io24.Io24, inspect.isfunction) if name in required}
        self.assertEqual(public, required)

    def test_inventory_preserves_forbidden_blind_write_boundary(self):
        self.assertEqual(
            set(self.inventory["never_blind_write"]),
            {"unmapped_Para_or_Pari", "IFac", "FRst", "firmware", "DFU"},
        )

    def test_supported_host_capabilities_are_positively_inventoried(self):
        supported = self.inventory["supported_host_capabilities"]
        self.assertEqual(supported["phones_source"], {
            "route": "global/phonesSrc",
            "readback": "write_only_host_shadow",
            "entrypoints": [
                "io24.set_phones_source", "io24d.phonesrc", "io24_scene",
                "io24gtk.phones_source_row", "ucnet_shim.global/phonesSrc",
            ],
        })
        # Removed at the user's request (2026-09-11): no Host A/B preview.
        self.assertNotIn("host_hot_key", supported)


class AtomicParameterMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "io24_full_parameter_matrix", MATRIX_BUILDER)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.generated = cls.module.build()
        cls.module.validate(cls.generated)
        cls.saved = json.loads(MATRIX.read_text())
        cls.rows = cls.generated["rows"]

    def test_saved_matrix_is_exact_deterministic_generator_output(self):
        self.assertEqual(self.saved, self.generated)

    def test_matrix_is_atomic_pending_and_restoration_gated(self):
        # 719 after the UC parity closure: the decoded Channel Mute Sync,
        # return/output mutes, Device Presets Store, and Host component names
        # all have concrete implementations and individual reconciliation rows.
        self.assertEqual(self.generated["coverage"]["total_rows"], 719)
        self.assertEqual(len(self.rows), 719)
        self.assertEqual(len({row["id"] for row in self.rows}), 719)
        ids = {row["id"] for row in self.rows}
        self.assertIn("native.global.mute_mode", ids)
        self.assertIn("native.channel1.processing_mix", ids)
        self.assertIn("native.channel2.processing_mix", ids)
        self.assertNotIn("native.channel1.reverb_send", ids)
        self.assertNotIn("native.channel1.preset_enabled", ids)
        self.assertTrue(all(row["result"]["status"] == "PENDING"
                            for row in self.rows))
        self.assertTrue(all(not row["result"]["restored"]
                            for row in self.rows))
        for profile in self.generated["profiles"].values():
            self.assertIn("oracle", profile)
            self.assertIn("guard", profile)
            self.assertIn("restoration", profile)

    def test_audio_rig_authority_is_cold_started_and_batch_scoped(self):
        authority = self.generated["authority"]
        self.assertIn("cold_start_before_measurement_session",
                      authority["preconditions"])
        self.assertIn("bootloader_194f_0405", authority["stop_recovery"])
        audio_rows = [row for row in self.rows
                      if any("audio_rig" in requirement
                             for requirement in row["requires"])]
        self.assertTrue(audio_rows)
        self.assertTrue(all(
            "deterministic_audio_rig" not in row["requires"]
            for row in audio_rows
        ))
        self.assertTrue(any(
            "deterministic_audio_rig@batch" in row["requires"]
            for row in audio_rows
        ))

    def test_mixer_clamp_oracle_distinguishes_floor_from_off(self):
        profile = self.generated["profiles"]["mixer_level"]
        self.assertIn("-144.0", profile["clamp_oracle"])
        self.assertIn("-145.0 off sentinel", profile["clamp_oracle"])

    def test_front_panel_mode_has_its_own_terminal_status(self):
        row = next(row for row in self.rows
                   if row["id"] == "native.global.preset_mode")
        self.assertEqual(
            self.generated["profiles"][row["profile"]]["terminal_pass"],
            "PASS_FRONT_PANEL",
        )
        self.assertIn("PASS_FRONT_PANEL", self.generated["terminal_statuses"])

    def test_slot_and_processing_rows_record_known_interpretation_boundaries(self):
        for channel in (1, 2):
            slot = next(row for row in self.rows
                        if row["id"] == "native.channel%d.preset_slot" % channel)
            self.assertIn("selector claim only", slot["note"])
            processing = next(
                row for row in self.rows
                if row["id"] == "native.channel%d.processing_channel" % channel
            )
            self.assertIn("values exchanged", processing["expected_side_effect"])
        profile = self.generated["profiles"]["readback_enum"]
        self.assertIn("not evidence", profile["oracle"])
        self.assertIn("unexplained", profile["guard"])

    def test_voicefx_and_persistence_rows_retain_prior_negative(self):
        rows = [row for row in self.rows if row["family"] == "voicefx"]
        rows += [row for row in self.rows
                 if row["id"].startswith("persistence.channel2.")]
        self.assertEqual(len(rows), 37)
        self.assertTrue(all("2026-08-11 fx_gate_probe" in row["prior_evidence"][0]
                            for row in rows))
        persistence = [row for row in rows
                       if row["id"].startswith("persistence.channel2.")]
        self.assertTrue(all("same-path positive control" in row["note"]
                            for row in persistence))

    def test_slot_write_retains_native_acceptance_boundaries(self):
        row = next(row for row in self.rows
                   if row["id"] == "state.channel2_slot3_write")
        self.assertIn("save_known_device_slot", row["api"])
        self.assertIn("native_current_slot_body_unreadable",
                      row["blockers"])
        self.assertIn("native_writer_unvalidated_live", row["blockers"])
        self.assertIn("old tagged writer", row["note"])
        self.assertIn("refused before transport", row["note"])

    def test_every_legacy_vendor_descriptor_has_its_own_row(self):
        catalog = json.loads((ROOT / "re" / "io24_params.json").read_text())
        rows = [row for row in self.rows
                if row["family"] == "vendor_descriptor"]
        self.assertEqual(len(rows), 117)
        self.assertEqual([row["scope"]["catalog_index"] for row in rows],
                         list(range(117)))
        self.assertEqual([row["scope"]["va"] for row in rows],
                         [entry["va"] for entry in catalog])

    def test_every_exact_component_route_is_individually_reconciled(self):
        rows = [row for row in self.rows
                if row["family"] == "component_route"]
        self.assertEqual(len(rows), 211)
        params = {row["parameter"] for row in rows}
        for route in ("line/ch1/presetHotKey", "line/ch2/presetHotKey",
                      "line/ch1/voicefxopt/fxmodel",
                      "line/ch2/voicefxopt/fxmodel",
                      "global/phonesSrc"):
            self.assertIn(route, params)

    def test_generic_line3_cells_are_visible_but_blocked_on_applicability(self):
        rows = [row for row in self.rows
                if row["family"] == "mixer_cell"]
        self.assertEqual(len(rows), 42)
        line3 = [row for row in rows if row["scope"]["source"] == "line/ch3"]
        self.assertEqual(len(line3), 6)
        self.assertTrue(all("prove_line_ch3_io24_applicability" in row["blockers"]
                            for row in line3))
        operational = [row for row in rows
                       if row["scope"]["source"] != "line/ch3"]
        self.assertEqual(len(operational), 36)

    def test_voicefx_has_every_model_field_once_for_the_global_engine(self):
        rows = [row for row in self.rows if row["family"] == "voicefx"]
        self.assertEqual(len(rows), 30)
        for model, fields in io24_fx._VOICEFX_PRESET_FIELDS.items():
            expected = {target for _source, target, _kind in fields}
            actual = {row["parameter"] for row in rows
                      if row["scope"] == {"model": model}}
            self.assertEqual(actual, expected, model)

    def test_alternate_eq_fields_are_present_on_exact_live_routes(self):
        expected = {
            "passive": {"eqallon", "bboost", "batten", "bfreq", "mboost",
                        "bbwidth", "mfreq", "hatten", "hsfreq"},
            "vintage": {"eqallon", "lowgain", "lowfreq", "lowmidgain",
                        "lowmidfreq", "himidgain", "himidfreq", "higain"},
        }
        rows = [row for row in self.rows
                if row["family"] == "fat_eq_alternate"]
        self.assertEqual(len(rows), 34)
        for channel in (1, 2):
            for model, fields in expected.items():
                actual = {row["parameter"] for row in rows
                          if row["scope"] == {"channel": channel, "model": model}}
                self.assertEqual(actual, fields, (channel, model))
                selected = [row for row in rows
                            if row["scope"] == {"channel": channel, "model": model}]
                expected_profile = {
                    "eqallon": "dsp_audio_toggle",
                    **{field: "dsp_audio_enum" for field in fields
                       if field.endswith("freq")},
                }
                self.assertTrue(all(
                    row["profile"] == expected_profile.get(
                        row["parameter"], "dsp_audio_scalar")
                    for row in selected))
                self.assertTrue(all(row["api"] == ["set_alternate_eq"]
                                    for row in selected))
                self.assertTrue(all(not row["blockers"] for row in selected))

    def test_every_safe_public_control_api_is_accounted_for(self):
        self.assertEqual(
            self.module._safe_public_api() - set(self.generated["api_index"]),
            set(),
        )

    def test_forbidden_operations_are_not_relaxed_by_full_authorization(self):
        forbidden = set(self.generated["authority"]["forbidden"])
        self.assertIn("Wine or .wine-io24", forbidden)
        self.assertIn("unknown/unmapped writes", forbidden)
        self.assertIn("firmware", forbidden)
        self.assertIn("Channel 1 slot-body writes", forbidden)
        self.assertIn("global slot 0 overwrite", forbidden)


if __name__ == "__main__":
    unittest.main()
