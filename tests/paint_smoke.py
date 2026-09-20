#!/usr/bin/env python3
"""Paint smoke test: launch the GTK app against a STUB device, cycle every page.

Run it with the interface UNPLUGGED:  python3 tests/paint_smoke.py
Exits non-zero if any draw callback raised.

Why a stub: main() exits when no io24 is present, so the app cannot be launched
unplugged. Why unplugged at all: the ch page starts the spectrum, which opens the
sound card — the condition associated with the device dropping to its bootloader.
With no device there is no card to open, so every paint path can be exercised at
zero risk to the hardware.

What this actually tests: GTK swallows exceptions raised inside a draw callback,
which is exactly why 13 stale attribute reads in EQCurve/CompCurve/Rack went
unnoticed for so long — the frames just came out half-drawn. Python still prints
the traceback to stderr, so cycling every page and watching stderr is a real
regression test for that whole class of bug.
"""
import os
import json
import struct
import sys
import threading
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import io24gtk as G                                          # noqa: E402
import io24_mbc                                              # noqa: E402
from gi.repository import GLib, Graphene, Gsk, Gtk          # noqa: E402


def bits(v):
    """An int bit pattern as the float the device would have put in that slot."""
    return struct.unpack("<f", struct.pack("<I", v))[0]


class FakeInner:
    """Stands in for Io24: plausible state, and every setter is a no-op."""

    def read_state(self, n=0x7EC):
        return b"\x00" * 2040

    def floats(self, rsp):
        f = [0.0] * 512
        f[4], f[6] = 0.06, 0.03                    # input meters
        f[12] = f[13] = 0.12                       # main L/R
        f[14] = f[15] = 0.09                       # mix A
        f[16] = f[17] = 0.02                       # mix B
        f[40] = bits(0)                            # selected slot / preset slot
        f[41] = bits(1)
        f[42] = bits(0x0181)                       # the slot-42 flag bitfield
        f[43], f[44], f[45] = 0.55, 0.43, 0.50     # hp vol, main vol, blend
        f[46], f[47] = 33.0, 12.0                  # preamp gains
        f[50] = bits(0x0000)                       # phantom off both
        return f

    def read_reduction(self, block, channel=1):
        return [1.0, 0.87]

    def read_params(self):
        return {"flags": 0x0181, "hpVolume": 0.55, "mainVolume": 0.43,
                "monitorMix": 0.5, "input1Gain": 33.0, "input2Gain": 12.0,
                "input1Level": 0.06, "input2Level": 0.03,
                "input1PhantomPower": 0.0, "input2PhantomPower": 0.0,
                "input1ProcessingChannel": 1, "input2ProcessingChannel": 2,
                "input1SlotIndex": 0, "input2SlotIndex": 0}

    def channel_names(self):
        return {0: "Input 1", 1: "Monitor Left"}

    def bus_master(self, _bus):
        return 0.0

    def __getattr__(self, name):
        # every setter/getter the UI reaches for that is not modelled above
        return lambda *a, **k: None


class FakeDev:
    def __init__(self):
        self.lock = threading.Lock()
        self.dev = FakeInner()

    def close(self):
        pass


class FakeSpectrum:
    """Paint data without ever opening ALSA during a visual-only review."""

    def __init__(self, *_args, **_kwargs):
        self.mag = [None, None]
        self.ok = False
        self.error = None
        self.running = False
        self.last_data = 0.0

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def stop(self):
        self.running = False

    def stalled(self):
        return False


def capture_window(win, output_path):
    """Render the realized GTK window to PNG without a desktop screenshot API."""
    content = win.get_content()
    width, height = content.get_width(), content.get_height()
    paintable = Gtk.WidgetPaintable.new(content)
    snapshot = Gtk.Snapshot()
    paintable.snapshot(snapshot, float(width), float(height))
    node = snapshot.to_node()
    if node is None:
        raise RuntimeError("GTK produced no render node")
    renderer = Gsk.Renderer.new_for_surface(win.get_surface())
    try:
        texture = renderer.render_texture(
            node, Graphene.Rect().init(0, 0, width, height))
        if not texture.save_to_png(str(output_path)):
            raise RuntimeError("GTK could not save %s" % output_path)
    finally:
        renderer.unrealize()


def scroll_page(widget, fraction=1.0):
    """Move the first page scroller through its range for section captures."""
    pending = [widget]
    while pending:
        current = pending.pop()
        if isinstance(current, Gtk.ScrolledWindow):
            adjustment = current.get_vadjustment()
            extent = adjustment.get_upper() - adjustment.get_page_size()
            adjustment.set_value(max(0.0, min(extent, extent * fraction)))
            return True
        child = current.get_first_child()
        while child is not None:
            pending.append(child)
            child = child.get_next_sibling()
    return False


def main():
    # This harness exists to inspect rendering, not audio capture. Keeping the
    # real Spectrum constructor here would make visiting the Channel page open
    # ALSA whenever an interface happened to be attached.
    G.Spectrum = FakeSpectrum
    # A visual test must neither adopt nor overwrite the user's real session.
    G.load_last_session = lambda path=None: None
    G.Win._save_last_session = lambda self, path=None: None
    # Keep the Device page synthetic too.  Reading sysfs or ALSA would make a
    # paint-only run observe an attached interface even though all control and
    # audio paths below are already stubbed.
    G.Win._usb_serial = lambda self: "PAINT-STUB"
    G.Win._bcd_device = lambda self: "0128 (stub)"
    G.alsa_rates = lambda card=G.CARD: list(G.SUPPORTED_SAMPLE_RATES)
    G.alsa_live = lambda card=G.CARD: {}
    # Apply requested dimensions while the window is being constructed, before
    # App.do_activate presents it. set_default_size after mapping does not
    # resize an existing GTK4 window and made desktop/narrow captures identical.
    original_win_init = G.Win.__init__

    def paint_win_init(self, app, ctl):
        original_win_init(self, app, ctl)
        self.set_default_size(
            int(os.environ.get("IO24_PAINT_WIDTH", "1040")),
            int(os.environ.get("IO24_PAINT_HEIGHT", "800")))

    G.Win.__init__ = paint_win_init
    # PipeWire is the same problem by another route: the Mixer page's watchdog
    # looks for the io24's nodes and starts the real bus-source chains, and
    # Multiband would look for its own, whenever an interface happened to be
    # attached. A rendering harness must not touch the audio graph at all.
    io24_mbc.find_io24_sink = lambda: None
    io24_mbc.find_io24_capture_source = lambda: None
    io24_mbc.node_id = lambda node_name: None
    io24_mbc.set_default_output = lambda node_name: False
    io24_mbc.set_default_input = lambda node_name: False
    io24_mbc._present_nodes = lambda: set()
    G.pw_settings = lambda: {"clock.rate": "96000", "clock.quantum": "512"}
    G.pw_set = lambda key, value: (True, "")
    ctl = G.Ctl(FakeDev())
    app = G.App(ctl)
    # A unique id per run: sharing org.io24.Mixer with an already-running
    # copy makes GTK forward the activation to that instance, so
    # do_activate never fires here and the test reports success having
    # drawn nothing at all. That silently invalidated a whole evening of
    # 'passes' while a preview window happened to be open.
    app.set_application_id('org.io24.PaintSmoke%d' % os.getpid())

    state = {"i": 0, "pages": None, "seen": [], "capture_pending": None,
             "scroll_settled": False, "eq_model_set": False,
             "comp_model_set": False, "fx_model_set": False,
             "wheel_tested": False}
    capture_dir = os.environ.get("IO24_PAINT_CAPTURE_DIR")
    if capture_dir:
        capture_dir = Path(capture_dir)
        capture_dir.mkdir(parents=True, exist_ok=True)

    def drive():
        win = app.win
        if win is None:
            return True
        st = win.stack
        if state["pages"] is None:
            state["pages"] = [c.get_name() for c in st.get_pages()] \
                if hasattr(st, "get_pages") else None
            if not state["pages"]:
                state["pages"] = ["mix", "ch", "fx", "route", "dev", "presets"]
            only_page = os.environ.get("IO24_PAINT_PAGE")
            if only_page:
                state["pages"] = [only_page]
            print("PAGES: %s" % state["pages"], flush=True)
        if not state["eq_model_set"]:
            model_name = os.environ.get("IO24_PAINT_EQ_MODEL", "").lower()
            if model_name:
                try:
                    model_index = G.Win.EQ_MODELS.index(model_name)
                except ValueError:
                    raise RuntimeError(
                        "IO24_PAINT_EQ_MODEL must be standard, passive, or vintage")
                win.w[1]["eq_model"].set_selected(model_index)
                print("EQ MODEL -> %s" % model_name, flush=True)
            state["eq_model_set"] = True
        if not state["comp_model_set"]:
            model_name = os.environ.get("IO24_PAINT_COMP_MODEL", "").lower()
            if model_name:
                try:
                    model_index = G.COMP_MODELS.index(model_name)
                except ValueError:
                    raise RuntimeError(
                        "IO24_PAINT_COMP_MODEL must be standard, tube, fet, "
                        "or multiband")
                win.w[1]["model"].set_selected(model_index)
                win.show_module(1, "COMP")
                print("COMP MODEL -> %s" % model_name, flush=True)
            state["comp_model_set"] = True
        if not state["fx_model_set"]:
            model_name = os.environ.get("IO24_PAINT_FX_MODEL", "").lower()
            if model_name:
                try:
                    model_index = G.Win.FX_ORDER.index(model_name)
                except ValueError:
                    raise RuntimeError(
                        "IO24_PAINT_FX_MODEL must be transformer, detuner, "
                        "vocoder, ringmod, filters, or delay")
                win.fx_model.set_selected(model_index)
                win.fx_power[model_name].set_value(True)
                values = json.loads(os.environ.get(
                    "IO24_PAINT_FX_PARAMS", "{}"))
                unknown = set(values) - set(win.fx_params[model_name])
                if unknown:
                    raise RuntimeError(
                        "unknown %s parameter(s): %s" % (
                            model_name, ", ".join(sorted(unknown))))
                for name, value in values.items():
                    win.fx_params[model_name][name].set_value(value)
                print("FX MODEL -> %s %s" % (model_name, values), flush=True)
            state["fx_model_set"] = True
        pending = state["capture_pending"]
        if pending is not None:
            page_number, page_name = pending
            if os.environ.get("IO24_PAINT_WHEEL_TEST") == "1" and \
                    not state["wheel_tested"]:
                scroller = G.first_descendant(
                    st.get_visible_child(), Gtk.ScrolledWindow)
                if scroller is None:
                    raise RuntimeError("visible page has no vertical scroller")
                adjustment = scroller.get_vadjustment()
                adjustment.set_value(adjustment.get_lower())
                before = adjustment.get_value()
                handled = win.fx_scroll_controller.emit(
                    "scroll", 0.0, 1.0)
                after = adjustment.get_value()
                if not handled or after <= before:
                    raise RuntimeError(
                        "Effects wheel capture did not advance the page")
                print("WHEEL SCROLL -> %.1f to %.1f" % (before, after),
                      flush=True)
                state["wheel_tested"] = True
                return True
            if state["scroll_settled"] is False and \
                    os.environ.get("IO24_PAINT_MBC_BAND") is not None:
                band = int(os.environ["IO24_PAINT_MBC_BAND"])
                if not 0 <= band < len(io24_mbc.BANDS):
                    raise RuntimeError("IO24_PAINT_MBC_BAND must be 0..3")
                win.mbc_ctl[1][(band, "expander")].set_expanded(True)
                # Exercise a connected model fader too. This caught a callback
                # arity error that a static paint alone could not expose.
                threshold = win.mbc_ctl[1][(band, "s_thr")]
                threshold.set_value(threshold.get_value() + 0.01)
                state["scroll_settled"] = "expanded"
                # Let GTK allocate and paint the newly visible children before
                # measuring its new scroll range.
                return True
            if state["scroll_settled"] == "expanded":
                # Moving GTK focus from this idle callback can temporarily
                # leave WidgetPaintable without a render node under Xvfb, so
                # scroll explicitly after the expanded row has been allocated.
                scroll_page(st.get_visible_child())
                state["scroll_settled"] = True
                return True
            fraction = os.environ.get("IO24_PAINT_SCROLL_FRACTION")
            if ((os.environ.get("IO24_PAINT_SCROLL_END") == "1" or fraction)
                    and not state["scroll_settled"]):
                scroll_page(st.get_visible_child(),
                            float(fraction) if fraction else 1.0)
                state["scroll_settled"] = True
                return True
            for _ in range(3):
                win.queue_draw()
                while GLib.MainContext.default().pending():
                    GLib.MainContext.default().iteration(False)
            if capture_dir:
                path = capture_dir / (
                    "%02d-%s.png" % (page_number, page_name))
                capture_window(win, path)
                print("CAPTURE -> %s" % path, flush=True)
            state["capture_pending"] = None
            state["scroll_settled"] = False
        i = state["i"]
        if i >= len(state["pages"]):
            print("CYCLED ALL PAGES", flush=True)
            app.quit()
            return False
        name = state["pages"][i]
        state["i"] += 1
        try:
            st.set_visible_child_name(name)
            state["seen"].append(name)
            state["capture_pending"] = (i + 1, name)
            print("PAGE -> %s" % name, flush=True)
        except Exception as e:
            print("PAGE %s failed: %s" % (name, e), flush=True)
        # force every canvas on screen to repaint a few times
        for _ in range(3):
            win.queue_draw()
            while GLib.MainContext.default().pending():
                GLib.MainContext.default().iteration(False)
        return True

    interval_ms = int(os.environ.get("IO24_PAINT_INTERVAL_MS", "1200"))
    GLib.timeout_add(interval_ms, drive)
    GLib.timeout_add(40000, lambda: (app.quit(), False)[1])   # hard stop
    rc = app.run([])
    ctl.close()
    print("VISITED: %s" % state["seen"], flush=True)
    if not state["seen"]:
        print("FAIL: no page was ever shown", flush=True)
        return 1
    return rc


if __name__ == "__main__":
    sys.exit(main() or 0)
