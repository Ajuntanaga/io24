#!/usr/bin/env python3
"""Exercise the real GTK dynamics racks with the paint harness's fake backend.

Run: xvfb-run -a env GDK_BACKEND=x11 GSK_RENDERER=cairo \
    GSETTINGS_BACKEND=memory python3 tests/dynamics_rack_smoke.py
Requires xdotool for genuine pointer/keyboard delivery, not signal emulation.
No USB, ALSA, PipeWire changes, or user-session writes occur.
"""
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import paint_smoke as H
import gi

gi.require_version("GdkX11", "4.0")
from gi.repository import GdkX11, GLib, Graphene  # noqa: E402, F401


def settle(seconds=.12):
    end = time.monotonic() + seconds
    context = GLib.MainContext.default()
    while time.monotonic() < end:
        while context.pending():
            context.iteration(False)
        time.sleep(.005)


def near(actual, expected, message):
    assert math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6), (
        message, actual, expected)


def check(win):
    W = win.w[1]
    gate, comp = W["gate_rack"], W["comp_curve"]
    xid = str(win.get_surface().get_xid())

    def input_event(*args):
        process = subprocess.Popen(["xdotool", *map(str, args)])
        deadline = time.monotonic() + 5
        while process.poll() is None and time.monotonic() < deadline:
            settle(.01)
        if process.poll() is None:
            process.kill()
            raise AssertionError("xdotool did not finish")
        assert process.returncode == 0
        settle()

    def point(widget):
        ok, position = widget.compute_point(win, Graphene.Point().init(
            widget.get_width() / 2, widget.get_height() / 2))
        assert ok and widget.get_mapped(), "control is not reachable"
        return round(position.x), round(position.y)

    def click(widget, count=1):
        x, y = point(widget)
        input_event("mousemove", "--window", xid, x, y,
                    "click", "--repeat", count, "--delay", 80, 1)

    def capture(name):
        directory = os.environ.get("IO24_PAINT_CAPTURE_DIR")
        if directory:
            for attempt in range(5):
                win.queue_draw()
                settle(.2)
                try:
                    H.capture_window(win, Path(directory) / (name + ".png"))
                    break
                except RuntimeError as exc:
                    if str(exc) != "GTK produced no render node" or attempt == 4:
                        raise

    input_event("windowfocus", "--sync", xid)
    # One adjustment means edits and preset adoption cannot drift apart.
    knob = gate.targets["gth"]
    assert knob.get_adjustment() == W["gth"].get_adjustment()
    W["gth"].set_value(-38)
    near(knob.get_value(), -38, "canonical -> rack")
    click(knob)
    near(knob.get_value(), -38, "a single click must not jump the value")
    assert knob.has_focus(), "mouse click must focus the knob"
    input_event("key", "Up")
    near(knob.get_value(), -37.16, "keyboard step")
    input_event("key", "shift+Up")
    near(knob.get_value(), -37.076, "fine keyboard step")
    input_event("key", "Home")
    near(knob.get_value(), -84, "lower bound")
    input_event("key", "End")
    near(knob.get_value(), 0, "upper bound")
    W["gth"].set_value(-40)
    x, y = point(knob)
    input_event("mousemove", "--window", xid, x, y, "mousedown", 1,
                "mousemove", "--sync", "--window", xid, x, y - 18,
                "mouseup", 1)
    near(W["gth"].get_value(), -31.6, "vertical drag updates canonical value")
    click(knob, 2)
    near(W["gth"].get_value(), -40, "double-click reset")
    input_event("click", 4)
    near(W["gth"].get_value(), -39.16, "focused wheel step")

    W["gth"].set_value(-33)
    before = W["gate_on"].get_active()
    click(gate.targets["power"])
    assert W["gate_on"].get_active() != before
    click(gate.targets["power"])
    assert W["gate_on"].get_active() == before
    near(W["gth"].get_value(), -33, "power preserves threshold")
    click(gate.targets["gate_mode"])
    assert not W["gexp"].get_active()
    click(gate.targets["expander"])
    assert W["gexp"].get_active()
    click(gate.targets["gklisten"])
    assert W["gklisten"].get_active()
    click(gate.targets["gklisten"])

    # Link uses the existing write path and updates the second visible rack.
    win.link_both = True
    knob.set_value(-32)
    near(win.w[2]["gate_rack"].targets["gth"].get_value(), -32,
         "stereo-linked gate")
    win.link_both = False
    win.show_module(1, "COMP")
    settle()
    for model, field, value in ((0, "cth", -18), (1, "tpeak", 37),
                                (2, "finput", -23)):
        click(comp.targets["model_" + str(model)])
        assert W["model"].get_selected() == model
        assert comp.targets[field].get_mapped()
        comp.targets[field].set_value(value)
        near(W[field].get_value(), value, "model parameter binding")
        capture(("standard", "tube", "fet")[model])
    comp.targets["fratio"].set_value(4)
    assert W["fratio"].get_selected() == 4
    W["fratio"].set_selected(2)
    near(comp.targets["fratio"].get_value(), 2, "FET ratio adoption")
    click(comp.targets["model_3"])
    assert not W["comp_param_stack"].get_visible()
    assert W["comp_param_stack"].get_visible_child_name() == "multiband"
    assert W["mbc_rack"].get_visible()
    assert not comp.targets["cklisten"].get_visible()
    ctl = win.mbc_ctl[1]
    assert comp.targets["x0"].get_adjustment() == ctl["x0"].get_adjustment()
    click(comp.targets["x0"])
    input_event("key", "Up")
    assert ctl["x0"].get_value() > 150, "logarithmic crossover keyboard move"
    ctl["x1"].set_value(300)
    comp.targets["x0"].set_value(400)
    near(ctl["x0"].get_value(), 299, "crossovers must stay ordered")
    win._mbc_snapshot_state(1)  # the edited state must remain saveable
    ctl["x1"].set_value(800)
    ctl["x0"].set_value(150)
    capture("multiband-overview")

    H.scroll_page(win.stack.get_visible_child(), 1)
    settle()
    band = W["mbc_rack"].get_visible_child()
    assert band.band == 0 and band.get_mapped()
    for index in range(4):
        click(band.targets["band_" + str(index)])
        band = W["mbc_rack"].get_visible_child()
        assert band.band == index and band.get_mapped()
        assert "power" not in band.targets, "multiband has one master power switch"
        band.targets["cth"].set_value(-24 - index)
        near(ctl[(index, "s_thr")].get_value(), -24 - index,
             "band threshold reaches canonical control")
    win.link_both = True
    band.targets["catk"].set_value(.013)
    near(win.mbc_ctl[2][(3, "s_attack")].get_value(), .013,
         "linked band attack")
    win.link_both = False
    click(band.targets["keyon"])
    assert ctl[(3, "keyon")].get_active()
    band.targets["ckey"].set_value(40)
    assert ctl[(3, "keyon")].get_active(), "40 Hz is a live band filter value"
    assert band.targets["ckey"].spec.text(40) != "OFF"
    click(band.targets["cklisten"])
    assert ctl[(3, "listen")].get_active()
    click(band.targets["cklisten"])
    capture("multiband-standard")
    for model, key, cid, value in ((1, "tpeak", "t_peak", 43),
                                    (2, "finput", "f_input", -29)):
        click(band.targets["model_" + str(model)])
        assert ctl[(3, "type")].get_selected() == model
        assert band.targets[key].get_mapped()
        band.targets[key].set_value(value)
        near(ctl[(3, cid)].get_value(), value, "band model parameter binding")
        capture("multiband-" + ("tube" if model == 1 else "fet"))
    band.targets["fratio"].set_value(4)
    assert ctl[(3, "f_ratio")].get_selected() == 4
    ctl[(3, "f_ratio")].set_selected(1)
    near(band.targets["fratio"].get_value(), 1, "band FET ratio adoption")
    click(band.targets["model_0"])
    near(band.targets["cth"].get_value(), -27, "model switch retains band state")
    for key, cid in (("knee", "s_knee"), ("auto", "s_auto")):
        before = ctl[(3, cid)].get_active()
        click(band.targets[key])
        assert ctl[(3, cid)].get_active() != before
        click(band.targets[key])
    before = W["comp_on"].get_active()
    H.scroll_page(win.stack.get_visible_child(), 0)
    settle()
    click(comp.targets["power"])
    assert W["comp_on"].get_active() != before
    click(comp.targets["power"])
    near(band.targets["cth"].get_value(), -27, "master power retains band settings")
    H.scroll_page(win.stack.get_visible_child(), 1)
    settle()
    click(band.targets["cth"], 2)
    near(ctl[(3, "s_thr")].get_value(), -22, "reset uses the selected band's default")
    state = win._mbc_snapshot_state(1)
    state["xovers"] = [170, 900, 5100]
    state["bands"]["high"]["type"] = "tube"
    state["bands"]["high"]["tube"]["peak"] = 57
    with patch.object(win, "_mbc_push") as split_push, \
            patch.object(win, "_mbc_push_band") as band_push:
        win._adopt_mbc_controls(1, state)
        split_push.assert_not_called()
        band_push.assert_not_called()
    near(comp.targets["x1"].get_value(), 900, "preset adopts crossover")
    assert band.model == 1
    near(band.targets["tpeak"].get_value(), 57, "preset adopts selected band model")
    H.scroll_page(win.stack.get_visible_child(), 0)
    settle()
    click(comp.targets["model_0"])
    assert not W["comp_param_stack"].get_visible()
    assert not W["mbc_rack"].get_visible()
    W["comp_on"].set_active(True)
    for field in ("knee", "auto", "cklisten"):
        old = W[field].get_active()
        click(comp.targets[field])
        assert W[field].get_active() != old
        click(comp.targets[field])
    click(comp.targets["power"])
    click(comp.targets["power"])
    near(W["cth"].get_value(), -18, "compressor power preserves threshold")

    with patch.object(win.ctl, "submit") as submit:
        win._adopt_dynamics(1, {"gate": {"threshold": -47, "attack": .012},
                                "comp": {"threshold": -21, "ratio": 5}})
        submit.assert_not_called()
    near(knob.get_value(), -47, "preset adoption reaches gate")
    near(comp.targets["rat"].get_value(), 5, "preset adoption reaches comp")

    snapshot = {"alive": True, "in": [-20, -30],
                "gr": {1: {"gate": -12, "comp": -6}}}
    comp.tick(snapshot)
    assert comp.history[-1] == (-20, -6)
    W["comp_on"].set_active(False)
    comp.tick(snapshot)
    assert comp.history[-1] == (-20, 0), "bypassed GR must be zero"
    comp.tick({"alive": False})
    assert not comp.online and not comp.history, "disconnect clears telemetry"
    comp.tick(snapshot)
    W["model"].set_selected(1)
    assert not comp.history, "new model must not inherit old gain reduction"

    # Return to a useful final screenshot with the real controls in operation.
    W["model"].set_selected(0)
    W["cth"].set_value(-18)
    W["rat"].set_value(4)
    W["mk"].set_value(3)
    W["comp_on"].set_active(True)
    capture("compressor")
    win.show_module(1, "GATE")
    W["gth"].set_value(-40)
    W["gkey"].set_value(120)
    W["gexp"].set_active(False)
    W["gate_on"].set_active(True)
    settle()
    capture("gate")
    print("DYNAMICS CONTROLS: pointer, keyboard, presets, link, models, crossovers, bands, telemetry PASS",
          flush=True)


if __name__ == "__main__":
    os.environ.setdefault("IO24_PAINT_WIDTH", "1440")
    os.environ.setdefault("IO24_PAINT_HEIGHT", "900")
    os.environ["IO24_PAINT_PAGE"] = "ch"
    os.environ["IO24_PAINT_DYNAMICS"] = "gate"
    os.environ["IO24_PAINT_DYNAMICS_ON"] = "1"
    sys.exit(H.main(check=check))
