#!/usr/bin/env python3
"""Hardware-free contracts for clock-correct DSP writes and effect state.

The device stores coefficients, not the Hz and seconds they were computed
from, so every write is a function of the clock. The Host used to pass none,
which left every biquad and time constant built for 48 kHz whatever the
interface was running at. These tests pin the rate through the write path,
the limiter release the page never exposed, and Host-only reverb movement.

Nothing here opens USB.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

import io24gtk
import io24_rack_reference


class _Value:
    def __init__(self, value=0.0):
        self.value = value

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def get_active(self):
        return bool(self.value)

    def set_active(self, value):
        self.value = bool(value)

    def get_selected(self):
        return int(self.value)

    def set_selected(self, value):
        self.value = int(value)


class _Adjustment:
    def __init__(self, lower, upper):
        self._lower, self._upper = lower, upper

    def get_lower(self):
        return self._lower

    def get_upper(self):
        return self._upper


class _Depth(_Value):
    def get_adjustment(self):
        return _Adjustment(0.0, 0.30)


class _Draws:
    def queue_draw(self):
        pass


class _Ctl:
    def __init__(self, dev=None):
        self.dev = dev
        self.sent = []

    def submit(self, fn):
        self.sent.append(fn)

    def run(self, dev):
        for fn in self.sent:
            fn(dev)


class _Device:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return record


def _window():
    window = io24gtk.Win.__new__(io24gtk.Win)
    window._fs = 48000.0
    window._fs_seen = False
    window._adopt_mute = False
    window._rev_mute = False
    window.link_both = False
    window.racks = {}
    window.messages = []
    window.say = window.messages.append
    window.hpf_by_ch = {1: 80.0, 2: 24.0}
    window.dyn_by_ch = {1: {"gate": False, "comp": False, "lim": True},
                        2: {"gate": False, "comp": False, "lim": False}}
    window.bands_by_ch = {
        ch: [{"shape": "peaking", "freq": 1000.0, "gain": 0.0, "q": 0.7}
             for _ in range(4)]
        for ch in (1, 2)
    }
    window.w = {
        ch: {"lth": _Value(-28.0), "lrel": _Value(0.4),
             "gth": _Value(-40.0), "grange": _Value(-60.0),
             "gatk": _Value(0.01), "grel": _Value(0.3),
             "gkey": _Value(24.0), "gklisten": _Value(False),
             "gexp": _Value(True),
             "comp_curve": _Draws(), "curve": _Draws(),
             "lim_on": _Value(False)}
        for ch in (1, 2)
    }
    window._compressor_kwargs = lambda ch: (0, {"threshold_db": -24.0})
    window.ctl = _Ctl()
    return window


class DeviceClockTests(unittest.TestCase):
    def test_fresh_hosts_start_at_the_native_safe_48khz_clock(self):
        self.assertEqual(io24gtk.DEFAULT_SAMPLE_RATE, 48000)
        self.assertEqual(
            io24gtk.audio_clock_preference({})["sample_rate"], 48000)

    def test_first_sighting_is_adopted_without_a_resend(self):
        window = _window()
        # Nothing has been pushed yet, so there is nothing built at 48 kHz.
        self.assertFalse(window._set_device_fs(96000))
        self.assertEqual(window._fs, 96000.0)

    def test_a_later_change_asks_for_a_resend(self):
        window = _window()
        window._set_device_fs(48000)
        self.assertTrue(window._set_device_fs(44100))
        self.assertEqual(window._fs, 44100.0)

    def test_an_unchanged_rate_never_resends(self):
        window = _window()
        window._set_device_fs(48000)
        for _ in range(5):
            self.assertFalse(window._set_device_fs(48000))

    def test_an_implausible_rate_is_ignored(self):
        window = _window()
        window._set_device_fs(48000)
        for bad in (0, -1, "not a rate", None, 7999, 192001):
            self.assertFalse(window._set_device_fs(bad))
        self.assertEqual(window._fs, 48000.0)

    def test_resend_is_a_no_op_without_a_device(self):
        window = _window()
        window.ctl.dev = None
        self.assertFalse(window._resend_rate_dependent_state())
        self.assertEqual(window.ctl.sent, [])


class RateTransitionSafetyTests(unittest.TestCase):
    def test_882khz_transition_uses_the_same_delay_safety_preflight(self):
        window = _window()
        window._selected_rate = 48000
        window._rates = [48000, 88200, 96000]
        window._host_delay_quiesced_device = None
        events = []

        class Device:
            def quiesce_voicefx_for_host_delay(self, fs, quantum=512):
                events.append(("quiesce", fs, quantum))

        device = Device()
        window.ctl = SimpleNamespace(
            dev=device, submit=lambda function: function(device))
        with mock.patch.object(io24gtk, "pw_settings", return_value={
                "clock.allowed-rates": "[ 48000, 88200, 96000 ]",
        }), mock.patch.object(
                io24gtk, "pw_set",
                side_effect=lambda key, value:
                (events.append((key, value)) or (True, ""))), \
                mock.patch.object(io24gtk, "alsa_live", return_value={}), \
                mock.patch.object(
                    io24gtk.GLib, "idle_add",
                    side_effect=lambda function, *args: function(*args)):
            window._rate_changed(_Value(1), None)

        self.assertEqual(events, [
            ("quiesce", 48000.0, 512),
            ("clock.force-rate", 88200),
        ])
        self.assertEqual(window._selected_rate, 88200)

    def test_safe_staging_rate_never_uses_882khz(self):
        window = _window()
        self.assertEqual(
            window._safe_delay_transition_rate({44100, 88200, 96000}),
            44100)

    def test_pending_96khz_transition_routes_delay_to_host_immediately(self):
        window = _window()
        window._selected_rate = 48000
        window._rates = [48000, 96000]
        queued = []
        device = object()
        window.ctl = SimpleNamespace(
            dev=device, submit=queued.append)

        with mock.patch.object(io24gtk, "pw_settings", return_value={
                "clock.allowed-rates": "[ 48000, 96000 ]",
                "clock.rate": "48000",
                "clock.quantum": "512",
        }), mock.patch.object(io24gtk, "alsa_live", return_value={}):
            window._rate_changed(_Value(1), None)

        self.assertEqual(window._selected_rate, 96000)
        self.assertEqual(window._voicefx_effective_rate(), 96000.0)
        self.assertEqual(len(queued), 1)

    def test_96khz_transition_quiesces_hardware_before_pipewire_moves(self):
        window = _window()
        window._selected_rate = 48000
        window._rates = [48000, 96000]
        window._host_delay_quiesced_device = None
        events = []

        class Device:
            def quiesce_voicefx_for_host_delay(self, fs, quantum=512):
                events.append(("quiesce", fs, quantum))

        device = Device()
        window.ctl = SimpleNamespace(
            dev=device, submit=lambda function: function(device))
        row = _Value(1)
        with mock.patch.object(io24gtk, "pw_settings", return_value={
                "clock.allowed-rates": "[ 48000, 96000 ]",
        }), mock.patch.object(
                io24gtk, "pw_set",
                side_effect=lambda key, value:
                (events.append((key, value)) or (True, ""))), \
                mock.patch.object(io24gtk, "alsa_live", return_value={}), \
                mock.patch.object(
                    io24gtk.GLib, "idle_add",
                    side_effect=lambda function, *args: function(*args)):
            window._rate_changed(row, None)

        self.assertEqual(events, [
            ("quiesce", 48000.0, 512),
            ("clock.force-rate", 96000),
        ])
        self.assertEqual(window._selected_rate, 96000)
        self.assertIs(window._host_delay_quiesced_device, device)

    def test_failed_safety_bypass_prevents_the_rate_change(self):
        window = _window()
        window._selected_rate = 48000
        window._rates = [48000, 96000]
        window._host_delay_quiesced_device = None
        pipewire = []

        class Device:
            def quiesce_voicefx_for_host_delay(self, _fs, quantum=512):
                _ = quantum
                raise RuntimeError("transport stopped")

        device = Device()
        window.ctl = SimpleNamespace(
            dev=device, submit=lambda function: function(device))
        with mock.patch.object(io24gtk, "pw_settings", return_value={
                "clock.allowed-rates": "[ 48000, 96000 ]",
        }), mock.patch.object(
                io24gtk, "pw_set",
                side_effect=lambda *args: pipewire.append(args)), \
                mock.patch.object(io24gtk, "alsa_live", return_value={}), \
                mock.patch.object(
                    io24gtk.GLib, "idle_add",
                    side_effect=lambda function, *args: function(*args)):
            window._rate_changed(_Value(1), None)

        self.assertEqual(pipewire, [])
        self.assertEqual(window._selected_rate, 48000)
        self.assertIn("safety bypass failed", window.messages[-1])

    def test_offline_96khz_selection_stays_at_48khz_until_attach(self):
        window = _window()
        window._selected_rate = 48000
        window._rates = [48000, 96000]
        events = []
        with mock.patch.object(io24gtk, "pw_settings", return_value={
                "clock.allowed-rates": "[ 48000, 96000 ]",
        }), mock.patch.object(
                io24gtk, "pw_set",
                side_effect=lambda key, value:
                (events.append((key, value)) or (True, ""))):
            window._rate_changed(_Value(1), None)

        self.assertEqual(events, [("clock.force-rate", 48000)])
        self.assertEqual(window._selected_rate, 96000)
        self.assertTrue(window._audio_clock_restore_deferred)
        self.assertIn("after the io24 connects", window.messages[-1])

    def test_live_period_is_the_old_rate_barrier_quantum(self):
        window = _window()
        window._fs_seen = False
        rate, quantum = window._transition_clock({
            "clock.force-rate": "48000",
            "clock.force-quantum": "512",
        }, {"capture": {"rate": "44100 Hz", "period_size": "1024"}})

        self.assertEqual((rate, quantum), (44100.0, 1024))

    def test_delay_stays_hosted_until_a_downshift_is_observed(self):
        window = _window()
        window._fs = 96000.0
        window._selected_rate = 48000
        self.assertEqual(window._voicefx_effective_rate(), 96000.0)
        window._fs = 48000.0
        self.assertEqual(window._voicefx_effective_rate(), 48000.0)

    def test_full_setup_load_uses_the_conservative_pending_rate(self):
        calls = []

        class Backend:
            _last_preset_load_report = {"host_features": {}}

            @staticmethod
            def load_preset(path, sample_rate_hz=None):
                calls.append((path, sample_rate_hz))
                return 1, 2

        window = _window()
        window._fs = 48000.0
        window._selected_rate = 96000

        result, report = window._load_full_host_setup(
            Backend(), "/tmp/io24-host-setup.json")

        self.assertEqual(result, (1, 2))
        self.assertEqual(report, {"host_features": {}})
        self.assertEqual(calls, [("/tmp/io24-host-setup.json", 96000.0)])


class RateDependentWriteTests(unittest.TestCase):
    def test_every_resent_write_carries_the_new_rate(self):
        window = _window()
        window.ctl.dev = object()
        window._fs = 96000.0
        window._push_reverb = lambda *a, **k: None
        window._push_fx = lambda *a, **k: None
        window._adopt_band = lambda ch: None
        window.invalidate_curve = lambda: None
        window._resend_rate_dependent_state()

        device = _Device()
        window.ctl.run(device)
        rate_bearing = [call for call in device.calls if "fs" in call[2]]
        self.assertTrue(rate_bearing)
        for name, _args, kwargs in rate_bearing:
            self.assertEqual(kwargs["fs"], 96000.0,
                             "%s was sent at the wrong rate" % name)
        names = {call[0] for call in device.calls}
        self.assertIn("set_eq_band", names)
        self.assertIn("set_highpass_freq", names)
        self.assertIn("set_limiter", names)
        # All four bands of both channels, not just the selected one.
        self.assertEqual(
            len([c for c in device.calls if c[0] == "set_eq_band"]), 8)

    def test_the_limiter_now_sends_its_release_and_rate(self):
        window = _window()
        window._fs = 44100.0
        window.w[1]["lrel"].set_value(0.75)
        window.w[1]["lth"].set_value(-12.0)
        window._dyn_push("lim", 1)

        device = _Device()
        window.ctl.run(device)
        name, args, kwargs = device.calls[0]
        self.assertEqual(name, "set_limiter")
        self.assertEqual(args[0], 1)
        self.assertTrue(args[1])
        self.assertAlmostEqual(args[2], -12.0)
        self.assertAlmostEqual(kwargs["release_s"], 0.75)
        self.assertEqual(kwargs["fs"], 44100.0)


class ReverbRateTests(unittest.TestCase):
    def test_the_reverb_engine_is_built_at_the_device_clock(self):
        window = _window()
        window._fs = 88200.0
        window._adopt_mute = False
        window.rev_on = _Value(True)
        window.s_rsize = _Value(0.5)
        window.s_rmix = _Value(0.3)
        window.s_rhp = _Value(200.0)
        window.s_rpre = _Value(0.02)
        window.processing_mix_controls = {1: _Value(1.0)}
        window.rev_return_controls = {"main": _Value(0.0)}
        window._push_reverb()

        device = _Device()
        window.ctl.run(device)
        name, _args, kwargs = device.calls[-1]
        self.assertEqual(name, "set_reverb")
        self.assertEqual(kwargs["fs"], 88200.0)


class ReverbMovementTests(unittest.TestCase):
    def _reverb_window(self):
        window = _window()
        window.rev_mod = _Value(False)
        window.s_rmoddep = _Depth(0.08)
        return window

    def test_movement_state_captures_the_host_only_half(self):
        window = self._reverb_window()
        window.rev_mod.set_active(True)
        window.s_rmoddep.set_value(0.12)
        state = window._reverb_movement_state()
        self.assertEqual(state["version"], 1)
        self.assertTrue(state["enabled"])
        self.assertAlmostEqual(state["depth"], 0.12)

    def test_movement_round_trips_through_adoption(self):
        window = self._reverb_window()
        window.rev_mod.set_active(True)
        window.s_rmoddep.set_value(0.2)
        saved = window._reverb_movement_state()

        window.rev_mod.set_active(False)
        window.s_rmoddep.set_value(0.0)
        self.assertIsNone(window._adopt_reverb_movement(saved))
        self.assertTrue(window.rev_mod.get_active())
        self.assertAlmostEqual(window.s_rmoddep.get_value(), 0.2)

    def test_adoption_leaves_the_mutes_as_it_found_them(self):
        window = self._reverb_window()
        window._adopt_reverb_movement(window._reverb_movement_state())
        self.assertFalse(window._rev_mute)
        self.assertFalse(window._adopt_mute)

    def test_an_unknown_version_is_refused_with_a_notice(self):
        window = self._reverb_window()
        notice = window._adopt_reverb_movement(
            {"version": 99, "enabled": True, "depth": 0.1})
        self.assertIn("unknown version", notice)
        self.assertFalse(window.rev_mod.get_active())

    def test_an_out_of_range_depth_is_refused_with_a_notice(self):
        window = self._reverb_window()
        notice = window._adopt_reverb_movement(
            {"version": 1, "enabled": True, "depth": 0.9})
        self.assertIn("outside the control", notice)
        self.assertAlmostEqual(window.s_rmoddep.get_value(), 0.08)

    def test_incomplete_saved_values_are_refused_with_a_notice(self):
        window = self._reverb_window()
        notice = window._adopt_reverb_movement({"version": 1})
        self.assertIn("incomplete", notice)

    def test_a_missing_section_is_silent(self):
        window = self._reverb_window()
        self.assertIsNone(window._adopt_reverb_movement(None))

    def test_a_manual_room_size_edit_moves_the_movement_centre(self):
        window = self._reverb_window()
        window.rev_mod.set_active(True)
        window._rev_mod_base = 0.4
        pushed = []
        window._push_reverb = lambda: pushed.append(True)

        window._reverb_size_changed(0.73)

        self.assertAlmostEqual(window._rev_mod_base, 0.73)
        self.assertEqual(pushed, [True])

    def test_a_movement_step_uses_a_nonpersistent_reverb_write(self):
        window = self._reverb_window()
        window.rev_on = _Value(True)
        window.s_rsize = _Value(0.6)
        window.s_rmix = _Value(0.3)
        window.s_rhp = _Value(200.0)
        window.s_rpre = _Value(0.02)
        window.processing_mix_controls = {1: _Value(1.0)}
        window.rev_return_controls = {"main": _Value(0.0)}
        window._rev_mute = True

        window._push_reverb()
        device = _Device()
        window.ctl.run(device)

        self.assertEqual(device.calls[-1][0], "set_reverb_transient")

    def test_movement_does_not_write_while_reverb_is_off(self):
        window = self._reverb_window()
        window.rev_mod.set_active(True)
        window.rev_on = _Value(False)
        window.s_rsize = _Value(0.6)
        window._rev_mod_t = 0.0
        window._rev_mod_base = 0.6

        self.assertTrue(window._reverb_mod_step())
        self.assertAlmostEqual(window.s_rsize.get_value(), 0.6)

    def test_room_movement_leaves_pre_delay_fixed(self):
        window = self._reverb_window()
        window.rev_mod.set_active(True)
        window.rev_on = _Value(True)
        window.s_rsize = _Value(0.6)
        window.s_rpre = _Value(0.037)
        window._rev_mod_t = 0.0
        window._rev_mod_base = 0.6

        self.assertTrue(window._reverb_mod_step())
        self.assertNotAlmostEqual(window.s_rsize.get_value(), 0.6)
        self.assertAlmostEqual(window.s_rpre.get_value(), 0.037)


class ReverbRackTests(unittest.TestCase):
    def test_layout_keeps_every_control_inside_the_faceplate(self):
        for width in (600, 680, 1040):
            layout = io24gtk.reverb_rack_layout(width, 220)
            fx, fy, fw, fh = layout["face"]
            for field in ("power", "predelay", "size", "hp", "mix",
                          "movement", "motion_power"):
                cx, cy, radius = layout[field]
                self.assertGreaterEqual(cx - radius, fx)
                self.assertLessEqual(cx + radius, fx + fw)
                self.assertGreaterEqual(cy - radius, fy)
                self.assertLessEqual(cy + radius, fy + fh)

    def test_display_sits_between_the_left_and_right_knobs(self):
        for width in (600, 680, 1040):
            layout = io24gtk.reverb_rack_layout(width, 220)
            dx, _dy, dw, _dh = layout["display"]
            left_edge = layout["size"][0] + layout["size"][2]
            right_edge = layout["hp"][0] - layout["hp"][2]
            self.assertGreater(dx, left_edge)
            self.assertLess(dx + dw, right_edge)
            self.assertGreaterEqual(dw, 160)

    def test_size_motion_switch_is_separate_from_its_depth_knob(self):
        for width in (600, 680, 1040):
            layout = io24gtk.reverb_rack_layout(width, 220)
            tx, ty, tr = layout["motion_power"]
            kx, ky, kr = layout["movement"]
            self.assertEqual(tx, kx)
            self.assertLess(ty + tr, ky - kr)

    def test_rack_readouts_use_the_existing_control_units(self):
        text = io24gtk.ReverbRack._value_text
        self.assertEqual(text("predelay", .02), "20 ms")
        self.assertEqual(text("size", .5), "50 %")
        self.assertEqual(text("mix", 1.0), "100 %")
        self.assertEqual(text("hp", 0.0), "OFF")
        self.assertEqual(text("hp", 200.0), "200 Hz")
        self.assertEqual(text("movement", .08), "±8 %")

    def test_acoustic_field_keeps_pre_delay_as_a_fixed_ignition_gap(self):
        still = io24gtk.reverb_field_profile(.5, .8, .04, 180, phase=0.0)
        moving = io24gtk.reverb_field_profile(.5, .8, .04, 180, phase=2.0)
        self.assertEqual(still["gap"], moving["gap"])
        self.assertEqual(still["reflections"], moving["reflections"])
        self.assertNotEqual(still["particles"], moving["particles"])

    def test_acoustic_field_maps_room_and_high_pass_to_real_dimensions(self):
        small = io24gtk.reverb_field_profile(.2, .8, .02, 60)
        large = io24gtk.reverb_field_profile(.9, .8, .02, 420)
        self.assertLess(small["decay"], large["decay"])
        self.assertLess(len(small["reflections"]),
                        len(large["reflections"]))
        self.assertGreater(small["low_body"], large["low_body"])

    def test_kinetic_mesh_propagates_without_moving_its_ignition(self):
        profile = io24gtk.reverb_field_profile(.7, .8, .04, 180)
        first = io24gtk.reverb_mesh_geometry(profile, phase=0.0)
        later = io24gtk.reverb_mesh_geometry(profile, phase=1.0)
        self.assertEqual(first["rows"][0][0][0], profile["gap"])
        self.assertEqual(later["rows"][0][0][0], profile["gap"])
        self.assertNotEqual(first["rows"], later["rows"])

    def test_size_motion_adds_torsion_to_the_mesh(self):
        profile = io24gtk.reverb_field_profile(.7, .8, .04, 180)
        stable = io24gtk.reverb_mesh_geometry(
            profile, phase=.6, movement_depth=0.0)
        drifting = io24gtk.reverb_mesh_geometry(
            profile, phase=.6, movement_depth=.20)
        self.assertNotEqual(stable["rows"], drifting["rows"])
        self.assertEqual(stable["rows"][0][0][0],
                         drifting["rows"][0][0][0])

    def test_mesh_is_a_connected_alternating_triangular_lattice(self):
        profile = io24gtk.reverb_field_profile(.7, .8, .04, 180)
        mesh = io24gtk.reverb_mesh_geometry(
            profile, phase=.4, rows=7, columns=12)
        triangles = io24gtk.reverb_mesh_triangles(mesh)
        self.assertEqual(len(triangles), (7 - 1) * (12 - 1) * 2)
        self.assertTrue(all(len(triangle) == 3 for triangle in triangles))
        # Adjacent cells use opposite diagonals, preventing a directional fan.
        first_cell = triangles[:2]
        second_cell = triangles[2:4]
        self.assertIn(mesh["rows"][0][0], first_cell[0])
        self.assertIn(mesh["rows"][1][1], first_cell[0])
        self.assertIn(mesh["rows"][0][2], second_cell[1])
        self.assertIn(mesh["rows"][1][1], second_cell[1])


class ReferenceRackTests(unittest.TestCase):
    def _rack(self, threshold=-28.0, release=0.4, power=False):
        rack = io24gtk.ReferenceRack.__new__(io24gtk.ReferenceRack)
        rack.win = SimpleNamespace(messages=[])
        rack.win.say = rack.win.messages.append
        rack.rack_id = "limiter"
        rack.spec = io24_rack_reference.rack("limiter")
        rack.bindings = {
            "threshold": {
                "widget": _Value(threshold),
                "format": lambda value: "%.2f dB" % value,
            },
            "release": {
                "widget": _Value(release),
                "format": lambda value: "%.2f s" % value,
            },
            "power": {"widget": _Value(power)},
        }
        rack.selected_field = None
        rack.hover_field = None
        rack.drag_field = None
        rack.drag_fraction = 0.0
        rack._asset_error_reported = False
        rack.queue_draw = lambda: None
        rack.grab_focus = lambda: None
        rack.get_width = lambda: 700
        rack.get_height = lambda: 210
        return rack

    def test_drag_fraction_changes_only_the_backing_widget(self):
        rack = self._rack(threshold=-28.0, release=0.4)

        self.assertTrue(rack._set_fraction("threshold", 0.5))

        self.assertAlmostEqual(
            rack.bindings["threshold"]["widget"].get_value(), -20.0)
        self.assertAlmostEqual(
            rack.bindings["release"]["widget"].get_value(), 0.4)

    def test_double_click_restores_the_manifest_default(self):
        rack = self._rack(threshold=-6.0)
        layout = io24_rack_reference.control_layout(
            "limiter", rack.get_width(), rack.get_height())
        x, y, _radius = layout["threshold"]

        rack._clicked(SimpleNamespace(set_state=lambda _state: None),
                      2, x, y)

        self.assertAlmostEqual(
            rack.bindings["threshold"]["widget"].get_value(), -28.0)

    def test_hit_testing_and_focus_use_manifest_geometry(self):
        rack = self._rack()
        layout = io24_rack_reference.control_layout(
            "limiter", rack.get_width(), rack.get_height())

        self.assertEqual(rack._control_at(*layout["threshold"][:2]),
                         "threshold")
        self.assertEqual(rack._control_at(*layout["release"][:2]),
                         "release")
        lamp = rack._lamp_layout()
        self.assertEqual(rack._control_at(*lamp[:2]), "power")
        self.assertIsNone(rack._control_at(-100, -100))

        rack._focus_enter()
        self.assertEqual(rack.selected_field, "power")

    def test_keyboard_wheel_and_drag_mutate_the_selected_live_widget(self):
        rack = self._rack(threshold=-28.0, release=0.4)
        rack.selected_field = "threshold"
        self.assertTrue(rack._key_pressed(
            None, io24gtk.Gdk.KEY_Up, None, None))
        self.assertAlmostEqual(
            rack.bindings["threshold"]["widget"].get_value(), -27.99)

        rack.hover_field = "release"
        self.assertTrue(rack._scroll(None, 0.0, -1.0))
        self.assertAlmostEqual(
            rack.bindings["release"]["widget"].get_value(), 0.41)

        cx, cy, _radius = io24_rack_reference.control_layout(
            "limiter", rack.get_width(), rack.get_height())["threshold"]
        rack._drag_begin(None, cx, cy)
        rack._drag_update(None, 0.0, -70.0)
        self.assertAlmostEqual(
            rack.bindings["threshold"]["widget"].get_value(), -7.99)
        rack._drag_end()
        self.assertIsNone(rack.drag_field)

    def test_keyboard_navigation_and_power_use_the_bound_switch(self):
        rack = self._rack(power=False)
        rack.selected_field = "power"

        self.assertTrue(rack._key_pressed(
            None, io24gtk.Gdk.KEY_space, None, None))
        self.assertTrue(rack.bindings["power"]["widget"].get_active())
        self.assertTrue(rack._key_pressed(
            None, io24gtk.Gdk.KEY_Right, None, None))
        self.assertEqual(rack.selected_field, "threshold")

    def test_asset_failure_reports_once_without_mutating_bound_state(self):
        rack = self._rack(threshold=-17.0, release=0.73, power=True)
        before = rack._state()

        with mock.patch.object(
                io24gtk, "eq_reference_texture",
                side_effect=FileNotFoundError("missing generated asset")):
            self.assertIsNone(rack._texture("limiter-faceplate.png"))
            self.assertIsNone(rack._texture("limiter-knob.png"))

        self.assertEqual(rack._state(), before)
        self.assertEqual(len(rack.win.messages), 1)
        self.assertIn("limiter", rack.win.messages[0].lower())

    def test_any_missing_asset_uses_the_complete_vector_fallback(self):
        rack = self._rack(power=True)
        rack.display_draw = mock.Mock()
        rack._texture = mock.Mock(
            side_effect=lambda filename:
            object() if filename == "limiter-faceplate.png" else None)
        rack._draw_fallback_faceplate = mock.Mock()
        snapshot = SimpleNamespace(append_texture=mock.Mock())

        with mock.patch.object(io24gtk, "dot"), \
                mock.patch.object(io24gtk, "polyline"), \
                mock.patch.object(io24gtk, "centred_faceplate_label"):
            rack.paint(snapshot, 700, 210)

        rack._draw_fallback_faceplate.assert_called_once_with(
            snapshot, 700, 210)
        snapshot.append_texture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
