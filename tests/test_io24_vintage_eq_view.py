#!/usr/bin/env python3
"""Hardware-free contracts for recalled Passive/Vintage EQ bodies.

The Host has no exact live builder for either model and no Standard-band form
for them. After a recall it shows the rest of the chain, lists the stored EQ
read-only, pauses the Standard editor on that channel, and carries the stored
EQ through a save verbatim instead of replacing it with four Standard bands.

Nothing here opens USB.
"""

import unittest
from types import SimpleNamespace

import io24_presets
import io24gtk


VINTAGE = {
    "__classid": "{E1C5E024-C5CD-473C-B08A-6EC177812E01}",
    "eqallon": 1, "lowgain": 1.76, "lowfreq": 0, "lowmidgain": -3.84,
    "lowmidfreq": 0, "himidgain": 1.6, "himidfreq": 1, "higain": 0.96,
}

PASSIVE = {
    "__classid": "{C0730CBB-5135-4558-9222-C40BDBA036ED}",
    "eqallon": 1, "bboost": 3.899999, "batten": 0.0, "bfreq": 3,
    "mboost": 1.8, "bbwidth": 4.55, "mfreq": 6, "hatten": 0.0,
    "hsfreq": 2,
}

FLAT = [{"shape": "off", "freq": f, "gain": 0.0, "q": 0.7}
        for f in (120.0, 600.0, 2500.0, 8000.0)]


def _slot_kwargs(**extra):
    kwargs = dict(
        bands=[dict(band) for band in FLAT], hpf_hz=24.0, eq_first=False,
        gate={"on": True, "threshold_db": -48.7, "range_db": -60.0,
              "attack_s": .005, "release_s": .3, "keyfilter_hz": 325.0,
              "keylisten": False, "expander": True},
        compressor_model=2,
        compressor={"on": True, "input_db": -30.0, "output_db": -3.0,
                    "attack_s": .0001, "release_s": .25, "ratio_index": 3,
                    "keyfilter_hz": 0.0, "keylisten": False},
        limiter={"on": True, "threshold_db": -.8},
        voicefx_model="delay",
        voicefx={"on": False, "time_s": .0351, "feedback": .25, "mix": .4})
    kwargs.update(extra)
    return kwargs


class AlternateEqViewTests(unittest.TestCase):
    def test_a_vintage_body_is_listed_as_stored(self):
        view = io24_presets.alternate_eq_view({"eq": dict(VINTAGE)})
        self.assertEqual(view["model"], "vintage")
        self.assertTrue(view["on"])
        self.assertEqual(view["rows"], [
            ("Low shelf", "position 1 of 4 (35 Hz)", "+1.8 dB"),
            ("Low mid", "position 1 of 3 (360 Hz)", "-3.8 dB"),
            ("High mid", "position 2 of 3 (4800 Hz)", "+1.6 dB"),
            ("High shelf", "fixed frequency", "+1.0 dB"),
        ])
        self.assertEqual(view["eq"], VINTAGE)
        self.assertIsNot(view["eq"], VINTAGE)

    def test_a_passive_body_uses_the_recovered_switch_labels(self):
        view = io24_presets.alternate_eq_view({"eq": dict(PASSIVE)})
        self.assertEqual(view["model"], "passive")
        self.assertEqual(view["rows"], [
            ("Low boost", "position 4 of 4 (100 Hz)", "3.9 / 10"),
            ("Low attenuation", "position 4 of 4 (100 Hz)", "0.0 / 10"),
            ("High boost", "position 7 of 7 (16000 Hz)",
             "1.8 / 10; bandwidth 4.5 / 10"),
            ("High attenuation", "position 3 of 3 (20000 Hz)", "0.0 / 10"),
        ])

    def test_standard_and_absent_eq_have_no_alternate_view(self):
        base = io24_presets.load()["Broadcast"]
        self.assertEqual(io24_presets.eq_model(base["eq"]), "standard")
        self.assertIsNone(io24_presets.alternate_eq_view(base))
        self.assertIsNone(io24_presets.alternate_eq_view({}))
        self.assertIsNone(io24_presets.alternate_eq_view({"eq": {}}))

    def test_an_out_of_range_switch_is_reported_not_guessed(self):
        view = io24_presets.alternate_eq_view(
            {"eq": dict(VINTAGE, lowfreq=7)})
        self.assertEqual(view["rows"][0][1],
                         "position 8 (outside the 4-way switch)")

    def test_saving_carries_the_stored_vintage_eq_verbatim(self):
        base = io24_presets.load()["Broadcast"]
        kept = io24_presets.current_slot_record(
            base, "MAIN", **_slot_kwargs(alternate_eq=dict(VINTAGE)))
        self.assertEqual(kept["eq"], VINTAGE)
        rebuilt = io24_presets.current_slot_record(base, "MAIN", **_slot_kwargs())
        self.assertEqual(io24_presets.eq_model(rebuilt["eq"]), "standard")

    def test_a_standard_section_is_refused_as_alternate_eq(self):
        base = io24_presets.load()["Broadcast"]
        with self.assertRaises(ValueError):
            io24_presets.current_slot_record(
                base, "MAIN", **_slot_kwargs(alternate_eq=dict(base["eq"])))


class _Widget:
    def __init__(self):
        self.sensitive, self.visible, self.text, self.draws = True, None, "", 0

    def set_sensitive(self, value):
        self.sensitive = bool(value)

    def set_visible(self, value):
        self.visible = bool(value)

    def set_text(self, text):
        self.text = text

    def queue_draw(self):
        self.draws += 1


class _Value:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def get_active(self):
        return bool(self.value)

    def get_selected(self):
        return int(self.value)


def _eq_widgets():
    W = {key: _Widget() for key in io24gtk.Win._ALT_EQ_CONTROLS}
    W["bands"] = [_Widget() for _ in range(4)]
    W["alt_eq_note"] = _Widget()
    W["alt_eq_release"] = _Widget()
    return W


def _window():
    window = io24gtk.Win.__new__(io24gtk.Win)
    window.messages = []
    window.say = window.messages.append
    window.link_both = False
    window.racks = {}
    window.w = {}
    window.submitted = []
    window.ctl = SimpleNamespace(submit=window.submitted.append)
    return window


class RecalledVintageBodyHostTests(unittest.TestCase):
    def test_a_recall_shows_the_rest_and_lists_the_eq(self):
        record = {"preset_name": "MAIN", "eq": dict(VINTAGE),
                  "voicefx": {"on": 0}}
        window = _window()
        window.PR = io24_presets
        window._host_slot_entry = lambda slot: {"record": record}
        adopted = []
        window._adopt_preset_record = \
            lambda rec, chans, fx_channel=None: adopted.append(
                (rec, chans, fx_channel)) or True
        self.assertTrue(window._adopt_recalled_slot(1, 0))
        self.assertEqual(len(adopted), 1)
        shown, chans, fx_channel = adopted[0]
        self.assertNotIn("eq", shown)
        self.assertEqual((chans, fx_channel), ((1,), 1))
        self.assertEqual(window._alt_eq(1)["eq"], VINTAGE)
        self.assertIsNone(window._alt_eq(2))
        self.assertIn("Vintage EQ the Host can show but not draw",
                      window.messages[-1])
        self.assertEqual(record["eq"], VINTAGE)      # the entry is untouched

    def test_the_standard_editor_pauses_then_releases_without_a_write(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        view = io24_presets.alternate_eq_view({"eq": dict(VINTAGE)})
        window._show_alternate_eq(1, view)
        W = window.w[1]
        for key in io24gtk.Win._ALT_EQ_CONTROLS:
            self.assertFalse(W[key].sensitive, key)
        self.assertFalse(any(b.sensitive for b in W["bands"]))
        self.assertTrue(W["alt_eq_note"].visible)
        self.assertIn("Vintage EQ from the recalled preset", W["alt_eq_note"].text)
        self.assertIn("Low shelf: position 1 of 4 (35 Hz), +1.8 dB",
                      W["alt_eq_note"].text)
        self.assertIn("switch frequencies are decoded",
                      W["alt_eq_note"].text)
        self.assertNotIn("not decoded", W["alt_eq_note"].text)
        self.assertTrue(W["alt_eq_release"].visible)

        window._release_alternate_eq(1)
        self.assertIsNone(window._alt_eq(1))
        self.assertTrue(all(W[key].sensitive
                            for key in io24gtk.Win._ALT_EQ_CONTROLS))
        self.assertTrue(all(b.sensitive for b in W["bands"]))
        self.assertFalse(W["alt_eq_note"].visible)
        self.assertFalse(W["alt_eq_release"].visible)
        self.assertIn("Nothing was sent", window.messages[-1])
        self.assertEqual(window.submitted, [])

    def test_clearing_a_channel_that_was_never_marked_touches_nothing(self):
        window = _window()
        window.w = {1: _eq_widgets()}
        window._show_alternate_eq(1, None)
        self.assertEqual(window.w[1]["curve"].draws, 0)
        self.assertIsNone(window.w[1]["alt_eq_note"].visible)

    def test_linked_edits_skip_a_held_channel_and_say_so_once(self):
        window = _window()
        window.link_both = True
        window._show_alternate_eq(
            2, io24_presets.alternate_eq_view({"eq": dict(VINTAGE)}))
        self.assertEqual(window._eq_write_targets(1), (1,))
        self.assertEqual(window._eq_write_targets(1), (1,))
        self.assertEqual(len(window.messages), 1)
        self.assertIn("Channel 2 keeps its recalled Vintage EQ",
                      window.messages[0])

    def test_saving_passes_the_stored_eq_through(self):
        window = _window()
        window.fx_target = _Value(0)
        window.w = {1: {"gth": _Value(-48.7), "grange": _Value(-60.0),
                        "gatk": _Value(.005), "grel": _Value(.3),
                        "gkey": _Value(325.0), "gklisten": _Value(False),
                        "gexp": _Value(True), "lth": _Value(-.8)}}
        window.dyn_by_ch = {1: {"gate": True, "comp": True, "lim": True}}
        window._compressor_kwargs = lambda target: (2, {})
        window.fx_model = _Value(0)
        window._fx_live_params = lambda: {}
        window.fx_arm = _Value(False)
        window.bands_by_ch = {1: [dict(band) for band in FLAT]}
        window.hpf_by_ch = {1: 24.0}
        window.order_by_ch = {1: False}
        seen = []
        window.PR = SimpleNamespace(
            load=lambda: {"base": {}},
            current_slot_record=lambda base, name, **kw: seen.append(kw) or kw)

        window._current_slot_record("base", 1, "MAIN")
        self.assertIsNone(seen[-1]["alternate_eq"])
        window.alt_eq_by_ch = {
            1: io24_presets.alternate_eq_view({"eq": dict(VINTAGE)}), 2: None}
        window._current_slot_record("base", 1, "MAIN")
        self.assertEqual(seen[-1]["alternate_eq"], VINTAGE)


if __name__ == "__main__":
    unittest.main()
