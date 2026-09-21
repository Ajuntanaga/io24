#!/usr/bin/env python3
"""Hardware-free contracts for the UC 4.7.2 four-band Standard EQ.

These tests keep the complete-EQ switch, each band's own switch, and the two
outer shelf selectors independent.  Nothing here opens USB.
"""

import copy
from pathlib import Path
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

import io24
import io24_presets
import io24gtk


ROOT = Path(__file__).resolve().parents[1]
EQ_XML = ROOT / "re" / "uc_component_model" / \
    "fatchannelxt_eq_contract.xml"


def _standard_section(eq_on=0):
    eq = {
        "__classid": "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}",
        "eqallon": eq_on,
        "eqbandop1": 1,
        "eqbandop4": 0,
    }
    for index, (freq, gain, q, on) in enumerate((
            (130.0, 2.0, 0.6, 1),
            (320.0, -3.0, 1.2, 0),
            (1400.0, 1.5, 2.4, 1),
            (5000.0, 4.0, 0.8, 1)), 1):
        eq["eqbandon%d" % index] = on
        eq["eqfreq%d" % index] = freq
        eq["eqgain%d" % index] = gain
        eq["eqq%d" % index] = q
    return eq


class _Switch:
    def __init__(self, active=False):
        self.active = bool(active)
        self.title = ""
        self.visible = True

    def get_active(self):
        return self.active

    def set_active(self, active):
        self.active = bool(active)

    def set_title(self, title):
        self.title = title

    def set_visible(self, visible):
        self.visible = bool(visible)


class _Value:
    def __init__(self, value=0.0):
        self.value = value

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value


class _Draw:
    def __init__(self):
        self.draws = 0

    def queue_draw(self):
        self.draws += 1


class _Ctl:
    def __init__(self):
        self.jobs = []

    def submit(self, job):
        self.jobs.append(job)

    def run(self, device):
        jobs, self.jobs = self.jobs, []
        for job in jobs:
            job(device)


class _Device:
    def __init__(self):
        self.calls = []

    def set_eq_band(self, channel, band, shape, freq, gain, q, fs):
        self.calls.append(("band", channel, band, shape, freq, gain, q, fs))

    def eq_off(self, channel):
        self.calls.append(("off", channel))


def _controls():
    return {
        "eq_on": _Switch(),
        "band_on": _Switch(),
        "shelf": _Switch(),
        "freq": _Value(),
        "gain": _Value(),
        "q": _Value(),
        "curve": _Draw(),
    }


def _window():
    window = io24gtk.Win.__new__(io24gtk.Win)
    window._adopt_mute = False
    window._fs = 96000.0
    window.link_both = False
    window.alt_eq_by_ch = {1: None, 2: None}
    window._alt_eq_warned = None
    window.eq_on_by_ch = {1: False, 2: False}
    window.bands_by_ch = {
        channel: io24_presets.default_standard_eq_bands()
        for channel in (1, 2)
    }
    window.cur_band_by_ch = {1: 0, 2: 0}
    window.w = {1: _controls(), 2: _controls()}
    window.racks = {}
    window.ctl = _Ctl()
    window.messages = []
    window.say = window.messages.append
    window._curves = {}
    return window


class ExactUcXmlContractTests(unittest.TestCase):
    @unittest.skipUnless(
        EQ_XML.is_file(),
        "requires privately retained UC component-model XML",
    )
    def test_retained_eqxt4_contract_has_the_independent_power_fields(self):
        root = ET.parse(EQ_XML).getroot()
        ns = {"uc": "urn:presonus-universal-control"}
        params = {
            node.attrib["id"]: node.attrib
            for node in root.findall(".//uc:ParamList[@id='Eqxt4']/uc:Param", ns)
        }
        self.assertEqual(params["eqallon"]["def"], "0")
        self.assertEqual([params["eqbandon%d" % band]["def"]
                          for band in range(1, 5)], ["1"] * 4)
        self.assertIn("storable", params["eqbandop1"]["flags"])
        self.assertIn("storable", params["eqbandop4"]["flags"])
        self.assertEqual(params["eqbandop2"]["flags"], "")
        self.assertEqual(params["eqbandop3"]["flags"], "")

    def test_ranges_defaults_and_band_modes_match_eqxt4(self):
        self.assertEqual(io24_presets.STANDARD_EQ_FREQ_RANGE,
                         (36.0, 18000.0))
        self.assertEqual(io24_presets.STANDARD_EQ_GAIN_RANGE, (-15.0, 15.0))
        self.assertEqual(io24_presets.STANDARD_EQ_Q_RANGE, (0.1, 10.0))
        self.assertEqual(io24_presets.STANDARD_EQ_DEFAULT_Q, 0.6)
        self.assertEqual(
            [(spec["default_freq"], spec["default_shape"], spec["shapes"])
             for spec in io24_presets.STANDARD_EQ_BAND_SPECS],
            [(130.0, "lowshelf", ("peaking", "lowshelf")),
             (320.0, "peaking", ("peaking",)),
             (1400.0, "peaking", ("peaking",)),
             (5000.0, "highshelf", ("peaking", "highshelf"))])

    def test_complete_bypass_does_not_erase_band_power_or_shape(self):
        preset = {"eq": _standard_section(eq_on=0)}
        effective = io24_presets._standard_eq_bands(preset["eq"])
        self.assertEqual([band["shape"] for band in effective],
                         ["off", "off", "off", "off"])
        self.assertEqual([band["mode"] for band in effective],
                         ["lowshelf", "peaking", "peaking", "peaking"])
        self.assertEqual([band["on"] for band in effective],
                         [True, False, True, True])

        editable = io24_presets.to_bands(preset)
        self.assertEqual([band["shape"] for band in editable],
                         ["lowshelf", "off", "peaking", "peaking"])
        rebuilt = io24_presets._standard_slot_eq(editable, eq_on=False)
        self.assertEqual(rebuilt["eqallon"], 0)
        self.assertEqual([rebuilt["eqbandon%d" % band]
                          for band in range(1, 5)], [1, 0, 1, 1])
        self.assertEqual((rebuilt["eqbandop1"], rebuilt["eqbandop4"]),
                         (1, 0))


class IndependentPowerRoutingTests(unittest.TestCase):
    def test_global_power_preserves_bands_and_replays_the_right_channel(self):
        window = _window()
        window.eq_on_by_ch[1] = True
        window.bands_by_ch[1][1]["on"] = False
        window.bands_by_ch[1][1]["shape"] = "off"
        before = copy.deepcopy(window.bands_by_ch)

        window._set_eq_enabled(1, False)
        device = _Device()
        window.ctl.run(device)
        self.assertEqual(device.calls, [("off", 1)])
        self.assertEqual(window.bands_by_ch, before)
        self.assertFalse(window.w[1]["eq_on"].get_active())

        window._set_eq_enabled(1, True)
        window.ctl.run(device)
        resent = device.calls[1:]
        self.assertEqual([call[1] for call in resent], [1, 1, 1, 1])
        self.assertEqual([call[2] for call in resent], [0, 1, 2, 3])
        self.assertEqual([call[3] for call in resent],
                         ["lowshelf", "off", "peaking", "highshelf"])
        self.assertTrue(window.w[1]["eq_on"].get_active())
        self.assertFalse(window.eq_on_by_ch[2])

    def test_linked_global_power_uses_each_channels_own_values(self):
        window = _window()
        window.link_both = True
        window.bands_by_ch[1][0]["gain"] = 2.0
        window.bands_by_ch[2][0]["gain"] = -5.0
        window._set_eq_enabled(1, True)
        device = _Device()
        window.ctl.run(device)

        self.assertEqual(len(device.calls), 8)
        low = {(call[1], call[5]) for call in device.calls if call[2] == 0}
        self.assertEqual(low, {(1, 2.0), (2, -5.0)})
        self.assertEqual(window.eq_on_by_ch, {1: True, 2: True})

    def test_band_power_and_outer_shelf_are_independent(self):
        window = _window()
        window.eq_on_by_ch[1] = True
        row = window.w[1]["band_on"]
        row.set_active(False)
        window._band_power_changed(row, None, 1)
        device = _Device()
        window.ctl.run(device)
        band = window.bands_by_ch[1][0]
        self.assertEqual((band["mode"], band["on"], band["shape"]),
                         ("lowshelf", False, "off"))
        self.assertEqual(device.calls[-1][3], "off")

        row.set_active(True)
        window._band_power_changed(row, None, 1)
        window.ctl.run(device)
        self.assertEqual(device.calls[-1][3], "lowshelf")

        shelf = window.w[1]["shelf"]
        shelf.set_active(False)
        window._shelf_changed(shelf, None, 1)
        window.ctl.run(device)
        self.assertEqual(device.calls[-1][3], "peaking")
        self.assertTrue(window.bands_by_ch[1][0]["on"])


class SemanticPersistenceTests(unittest.TestCase):
    def test_disabled_eq_round_trips_without_flattening_hidden_controls(self):
        source = _window()
        source.eq_on_by_ch = {1: False, 2: True}
        source.bands_by_ch[1][0].update(
            {"freq": 87.0, "gain": 6.5, "q": 1.7})
        source.bands_by_ch[1][2].update(
            {"on": False, "shape": "off", "mode": "peaking"})
        state = source._standard_eq_state()

        normalized, migrations = io24._normalise_host_features(
            {"standard_eq": state})
        self.assertEqual(migrations, [])
        target = _window()
        message = target._adopt_standard_eq_state(
            normalized["standard_eq"])
        self.assertEqual(target.eq_on_by_ch, {1: False, 2: True})
        self.assertEqual(target.bands_by_ch[1][0]["freq"], 87.0)
        self.assertEqual(target.bands_by_ch[1][0]["gain"], 6.5)
        self.assertFalse(target.bands_by_ch[1][2]["on"])
        self.assertIn("Input 1 and 2", message)
        self.assertEqual(target.ctl.jobs, [])

    def test_alternate_model_channel_is_not_serialized_as_standard(self):
        window = _window()
        window.alt_eq_by_ch[2] = {"model": "vintage", "on": True}
        state = window._standard_eq_state()
        self.assertEqual(set(state["channels"]), {"1"})

    def test_reconnect_carries_semantic_eq_beside_the_effective_shadow(self):
        state = _window()._standard_eq_state()
        adopted = []

        class Backend:
            _shadow = {}

            @staticmethod
            def reapply_shadow(skip=(), sample_rate_hz=None):
                self.assertEqual(sample_rate_hz, io24gtk.DEFAULT_SAMPLE_RATE)
                return {"applied": 4}

        window = io24gtk.Win.__new__(io24gtk.Win)
        window._standard_eq_state = lambda: state
        window._after_load = lambda mirror, features, migrations, message: \
            adopted.append((mirror, features, message))
        window.say = lambda _message: None
        window.ctl = type("Ctl", (), {
            "submit": staticmethod(lambda job: job(Backend())),
        })()
        with mock.patch.object(
                io24gtk.GLib, "idle_add",
                side_effect=lambda function, *args: function(*args)):
            window._resume_session(first=False)

        self.assertEqual(adopted[0][1], {"standard_eq": state})
        self.assertEqual(adopted[0][2], "Picked up where you left off")


if __name__ == "__main__":
    unittest.main()
