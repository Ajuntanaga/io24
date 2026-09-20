#!/usr/bin/env python3
"""Apply a Universal Control `.scene` file with the native Linux Host.

The importer follows UC 4.7.2's component model rather than treating a scene
as a channel preset. It restores global settings, both Fat Channels, the full
mixer matrix, output masters and mutes, shared reverb, and the one shared
VoiceFX processor. Passive and Vintage EQ use the exact retained UC 4.7.2
coefficient designers already used by the Host.

    python3 io24_scene.py "B A S E.scene"
    python3 io24_scene.py --dry-run --sample-rate 96000 Main.scene

Device-resident preset blocks are listed but never overwritten by scene load.
Fields that the io24 protocol cannot faithfully represent are reported with a
specific reason: mono-source pan/stereo width, FXA, DAW post-DSP capture tap,
output mono fold-down, text labels, and UC's live mirror latch. A true mirror
request is restored as the Host's documented one-shot copy.
"""
import argparse
import json
import math
import os

import io24_alt_eq
import io24_dsp
import io24_fx
import io24_presets


SOURCE = {1: "line/ch1", 2: "line/ch2"}

# Public compatibility constants used by protocol tests and by people
# inspecting scene files. Model dispatch itself is centralized in
# ``io24_presets`` so the importer cannot drift from the preset loader.
COMP_MODELS = {
    "{870D04F7-212E-4F9C-ADBB-39A97216433F}": 0,
    "{7F8A4262-D377-48E3-9D48-15D82C400A71}": 1,
    "{1F831EC1-B8AC-4EE9-AD53-54227AF53D58}": 2,
}
EQ_PARAMETRIC = "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}"
EQ_PASSIVE = "{C0730CBB-5135-4558-9222-C40BDBA036ED}"
EQ_VINTAGE = "{E1C5E024-C5CD-473C-B08A-6EC177812E01}"

VINTAGE_LOW_HZ = (35.0, 60.0, 110.0, 220.0)
VINTAGE_LOWMID_HZ = (360.0, 700.0, 1600.0)
VINTAGE_HIMID_HZ = (3200.0, 4800.0, 7200.0)
VINTAGE_HIGH_HZ = 12000.0
PASSIVE_LOW_HZ = (20.0, 30.0, 60.0, 100.0)
PASSIVE_HIGH_BOOST_HZ = (3000.0, 4000.0, 5000.0, 8000.0,
                         10000.0, 12000.0, 16000.0)
PASSIVE_HIGH_ATTEN_HZ = (5000.0, 10000.0, 20000.0)


def load(path):
    """Read one UC scene, accepting the BOM emitted by some UC versions."""
    with open(path, encoding="utf-8-sig") as handle:
        scene = json.load(handle)
    if not isinstance(scene, dict):
        raise ValueError("scene root must be an object")
    return scene


def _object(value, label):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("%s must be an object" % label)
    return value


def _number(value, label, low=None, high=None):
    if isinstance(value, bool):
        raise ValueError("%s must be a finite number" % label)
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("%s must be a finite number" % label)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    if (low is not None and value < low) or \
            (high is not None and value > high):
        raise ValueError("%s must be in [%s, %s]" % (label, low, high))
    return value


def _integer(value, label, low=None, high=None):
    number = _number(value, label, low, high)
    if not number.is_integer():
        raise ValueError("%s must be an integer" % label)
    return int(number)


def _toggle(value, label):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool) and \
            math.isfinite(float(value)) and float(value) in (0.0, 1.0):
        return bool(value)
    raise ValueError("%s must be boolean or 0/1" % label)


def _call(calls, method, args, kwargs, description):
    calls.append((method, tuple(args), dict(kwargs), description))


def _unknown_fields(component, known, prefix, skips):
    for field in sorted(set(component) - set(known)):
        skips.append("%s.%s is not in the UC 4.7.2 io24 component model" %
                     (prefix, field))


def _routing_calls(component, source, prefix, calls):
    for field, bus, assign in (
            ("volume", "main", "lr"),
            ("aux1", "mixa", "assign_aux1"),
            ("aux2", "mixb", "assign_aux2")):
        if field in component:
            level = _number(component[field], "%s.%s" % (prefix, field),
                            -145.0, 10.0)
            _call(calls, "set_send_db", (source, bus, level), {},
                  "%s -> %s = %.1f dB" % (prefix, bus, level))
        if assign in component:
            on = _toggle(component[assign], "%s.%s" % (prefix, assign))
            _call(calls, "set_send_assigned", (source, bus, on), {},
                  "%s -> %s assigned = %s" % (prefix, bus, on))


def _plan_standard_eq(channel, eq, prefix, fs, calls):
    bands = io24_presets._standard_eq_bands(eq)
    for index, values in enumerate(bands):
        kwargs = {
            "shape": values["shape"], "freq_hz": values["freq"],
            "gain_db": values["gain"], "q": values["q"], "fs": fs,
        }
        _call(calls, "set_eq_band", (channel, index), kwargs,
              "%s Standard EQ band %d %s %.0f Hz %+.1f dB Q%.2f" %
              (prefix, index + 1, values["shape"], values["freq"],
               values["gain"], values["q"]))


def _plan_processing(channel, component, prefix, fs, calls, voicefx, skips):
    opt = _object(component.get("opt"), "%s.opt" % prefix)
    if "swapcompeq" in opt:
        eq_first = _toggle(opt["swapcompeq"], "%s.opt.swapcompeq" % prefix)
        _call(calls, "set_comp_eq_order", (channel, eq_first), {},
              "%s order = %s" %
              (prefix, "EQ then compressor" if eq_first
               else "compressor then EQ"))
    _unknown_fields(opt, {"swapcompeq"}, "%s.opt" % prefix, skips)

    filt = _object(component.get("filter"), "%s.filter" % prefix)
    if "hpf" in filt:
        hpf = _number(filt["hpf"], "%s.filter.hpf" % prefix, 24.0, 1000.0)
        _call(calls, "set_highpass_freq", (channel, hpf), {"fs": fs},
              "%s Fat Channel HPF = %.0f Hz" % (prefix, hpf))
    _unknown_fields(filt, {"hpf"}, "%s.filter" % prefix, skips)

    gate = _object(component.get("gate"), "%s.gate" % prefix)
    if gate:
        kwargs = {
            "on": _toggle(gate.get("on", 1), "%s.gate.on" % prefix),
            "threshold_db": _number(gate.get("threshold", -40.0),
                                    "%s.gate.threshold" % prefix),
            "range_db": _number(gate.get("range", -60.0),
                                "%s.gate.range" % prefix),
            "attack_s": _number(gate.get("attack", 0.01),
                                "%s.gate.attack" % prefix, 0.0),
            "release_s": _number(gate.get("release", 0.3),
                                 "%s.gate.release" % prefix, 0.0),
            "keyfilter_hz": _number(gate.get("keyfilter", 0.0),
                                    "%s.gate.keyfilter" % prefix, 0.0),
            "expander": _toggle(gate.get("expander", 1),
                                "%s.gate.expander" % prefix),
            "keylisten": _toggle(gate.get("keylisten", 0),
                                 "%s.gate.keylisten" % prefix),
            "fs": fs,
        }
        io24_dsp.gate_blob(
            0, kwargs["on"], kwargs["threshold_db"], kwargs["range_db"],
            kwargs["attack_s"], kwargs["release_s"], kwargs["keyfilter_hz"],
            kwargs["expander"], kwargs["keylisten"], fs)
        _call(calls, "set_gate", (channel,), kwargs,
              "%s gate on=%s threshold=%.1f dB" %
              (prefix, kwargs["on"], kwargs["threshold_db"]))
    _unknown_fields(gate, {
        "on", "threshold", "range", "attack", "release", "keyfilter",
        "expander", "keylisten",
    }, "%s.gate" % prefix, skips)

    comp = _object(component.get("comp"), "%s.comp" % prefix)
    if comp:
        decoded = io24_presets._compressor_call(comp)
        if decoded is not None:
            model, kwargs = decoded
            kwargs = dict(kwargs, model=model, fs=fs)
            _call(calls, "set_compressor", (channel,), kwargs,
                  "%s %s compressor on=%s" %
                  (prefix, io24_presets.compressor_model(comp).title(),
                   kwargs["on"]))

    limiter = _object(component.get("limit"), "%s.limit" % prefix)
    if limiter:
        on = _toggle(limiter.get("limiteron", 0),
                     "%s.limit.limiteron" % prefix)
        threshold = _number(limiter.get("threshold", -28.0),
                            "%s.limit.threshold" % prefix, -56.0, 0.0)
        _call(calls, "set_limiter", (channel, on, threshold), {"fs": fs},
              "%s limiter on=%s threshold=%.1f dBFS" %
              (prefix, on, threshold))
    _unknown_fields(limiter, {"limiteron", "threshold"},
                    "%s.limit" % prefix, skips)

    eq = _object(component.get("eq"), "%s.eq" % prefix)
    if eq:
        model = io24_presets.eq_model(eq)
        if model == "standard":
            _plan_standard_eq(channel, eq, prefix, fs, calls)
        elif model in ("passive", "vintage"):
            normalized = io24_alt_eq.validate_eq(eq)
            # Missing retained source material or invalid coefficients fail
            # here, before the first device call can be made.
            io24_alt_eq.design_live_sections(normalized, rate_hz=fs)
            _call(calls, "set_alternate_eq", (channel, normalized), {"fs": fs},
                  "%s exact %s EQ on=%s" %
                  (prefix, model.title(), bool(normalized["eqallon"])))
        else:
            raise ValueError("%s EQ has no selected model" % prefix)

    fx = _object(component.get("voicefx"), "%s.voicefx" % prefix)
    if fx:
        model, kwargs = io24_fx.voicefx_preset_call(fx)
        kwargs = dict(kwargs)
        if model in ("transformer", "detuner", "vocoder"):
            kwargs["fs"] = fs
        # Materialize the exact model transaction offline, including its own On.
        getattr(io24_fx, "set_fx_" + model)(**kwargs)
        voicefx.append((prefix, model, kwargs))


def plan(scene, vintage=False, sample_rate_hz=48000.0):
    """Return ``(calls, skips)`` without touching USB or the device.

    ``vintage`` is accepted for source compatibility. Alternate EQ no longer
    needs an opt-in: exact Passive and Vintage replay is the normal path.
    """
    _ = vintage
    scene = _object(scene, "scene")
    fs = _number(sample_rate_hz, "sample rate", 8000.0, 192000.0)
    calls, skips, mirrors, solos, mutes, voicefx = [], [], [], [], [], []

    global_state = _object(scene.get("global"), "global")
    if "outputDelayBus" in global_state:
        bus = _integer(global_state["outputDelayBus"],
                       "global.outputDelayBus", -1, 4)
        _call(calls, "set_output_delay_bus", (bus,), {},
              "output delay bus = %d" % bus)
    if "outputDelay" in global_state:
        seconds = _number(global_state["outputDelay"],
                          "global.outputDelay", 0.0, 0.5)
        _call(calls, "set_output_delay", (seconds,), {},
              "output delay = %.0f ms" % (seconds * 1000.0))
    if "phonesSrc" in global_state:
        source = _integer(global_state["phonesSrc"], "global.phonesSrc", 0, 2)
        _call(calls, "set_phones_source", (source,), {},
              "headphones source = %d" % source)
    if "auxMuteMode" in global_state:
        mode = _toggle(global_state["auxMuteMode"], "global.auxMuteMode")
        _call(calls, "set_mute_mode", (mode,), {},
              "Channel Mute Sync = %s (UC value mapping)" % mode)
    if "presetButtonMode" in global_state:
        mode = _integer(global_state["presetButtonMode"],
                        "global.presetButtonMode", 0, 2)
        _call(calls, "set_preset_mode", (mode,), {},
              "preset button mode = %d" % mode)
    for field, bus in (("aux1_mirror_main", "mixa"),
                       ("aux2_mirror_main", "mixb")):
        if field in global_state and _toggle(
                global_state[field], "global.%s" % field):
            mirrors.append(("mirror_main", (bus,), {},
                            "%s one-shot copy from Main" % bus))
    _unknown_fields(global_state, {
        "phonesSrc", "aux1_mirror_main", "aux2_mirror_main",
        "outputDelay", "outputDelayBus", "presetButtonMode", "auxMuteMode",
    }, "global", skips)

    line = _object(scene.get("line"), "line")
    ch1 = _object(line.get("ch1"), "line.ch1")
    if "link" in ch1:
        linked = _toggle(ch1["link"], "line.ch1.link")
        _call(calls, "set_channel_link", (linked,), {},
              "input stereo link = %s" % linked)
    for channel in (1, 2):
        key = "ch%d" % channel
        component = _object(line.get(key), "line.%s" % key)
        if not component:
            continue
        prefix, source = "line.%s" % key, SOURCE[channel]
        if "preampgain" in component:
            gain = _number(component["preampgain"],
                           "%s.preampgain" % prefix, 0.0, 60.0)
            _call(calls, "set_gain", (channel, gain), {},
                  "%s preamp gain = %.1f dB" % (prefix, gain))
        if "48v" in component:
            phantom = _toggle(component["48v"], "%s.48v" % prefix)
            _call(calls, "set_phantom", (channel, phantom), {},
                  "%s phantom = %s" % (prefix, phantom))
        if "mute" in component:
            muted = _toggle(component["mute"], "%s.mute" % prefix)
            _call(calls, "set_mute", (channel, muted), {},
                  "%s input mute = %s" % (prefix, muted))
        if "processingChannel" in component:
            processing = _integer(component["processingChannel"],
                                  "%s.processingChannel" % prefix, 0, 1) + 1
            _call(calls, "set_processing_channel", (channel, processing), {},
                  "%s DSP source = input %d" % (prefix, processing))
        _routing_calls(component, source, prefix, calls)
        if "dspAmount" in component:
            amount = _number(component["dspAmount"],
                             "%s.dspAmount" % prefix, 0.0, 1.0)
            _call(calls, "set_fx_mix", (channel, amount), {},
                  "%s DSP amount = %.3f" % (prefix, amount))
        if "solo" in component:
            on = _toggle(component["solo"], "%s.solo" % prefix)
            for bus in ("main", "mixa", "mixb"):
                solos.append(("set_solo", (source, bus, on), {},
                              "%s solo in %s = %s" % (prefix, bus, on)))
        _plan_processing(channel, component, prefix, fs, calls, voicefx, skips)
        for field, reason in (
                ("pan", "mono-source pan is not representable by block 100"),
                ("stereopan", "stereo width/mono collapse is not representable"),
                ("FXA", "no exact io24 wire mapping exists"),
                ("dawpostdsp", "DAW capture-tap selection is Host-bound"),
                ("username", "text label is not writable on this protocol"),
                ("preset_name", "display metadata is not a live parameter"),
                ("linkmaster", "UC component-tree metadata")):
            if field in component:
                skips.append("%s.%s = %r (%s)" %
                             (prefix, field, component[field], reason))
        known = {
            "username", "mute", "volume", "link", "linkmaster",
            "preset_name", "solo", "lr", "assign_aux1", "assign_aux2",
            "aux1", "aux2", "preampgain", "pan", "stereopan", "FXA",
            "dawpostdsp", "dspAmount", "processingChannel", "48v", "opt",
            "filter", "gate", "comp", "eq", "limit", "voicefx",
        }
        _unknown_fields(component, known, prefix, skips)

    if len(voicefx) > 1:
        first = voicefx[0][1:]
        if any(item[1:] != first for item in voicefx[1:]):
            raise ValueError(
                "scene contains conflicting per-channel VoiceFX records, but "
                "the io24 has one shared VoiceFX processor")
    if voicefx:
        prefix, model, kwargs = voicefx[0]
        _call(calls, "set_fx", (model,), kwargs,
              "shared VoiceFX from %s = %s, on=%s" %
              (prefix, model, kwargs["on"]))

    for section in ("return", "fxreturn"):
        group = _object(scene.get(section), section)
        for key, component in group.items():
            component = _object(component, "%s.%s" % (section, key))
            source = "%s/%s" % (section, key)
            prefix = "%s.%s" % (section, key)
            if source not in ("return/ch1", "return/ch2", "return/ch3",
                              "fxreturn/ch1"):
                skips.append("%s has no io24 mixer source" % prefix)
                continue
            _routing_calls(component, source, prefix, calls)
            if "mute" in component:
                on = _toggle(component["mute"], "%s.mute" % prefix)
                mutes.append(("set_source_mute", (source, on), {},
                              "%s source mute = %s" % (prefix, on)))
            if "solo" in component:
                on = _toggle(component["solo"], "%s.solo" % prefix)
                for bus in ("main", "mixa", "mixb"):
                    solos.append(("set_solo", (source, bus, on), {},
                                  "%s solo in %s = %s" %
                                  (prefix, bus, on)))
            for field, reason in (
                    ("username", "text label is not writable"),
                    ("preset_name", "display metadata is not live state"),
                    ("link", "USB-return stereo linking has no exact wire"),
                    ("linkmaster", "UC component-tree metadata")):
                if field in component:
                    skips.append("%s.%s = %r (%s)" %
                                 (prefix, field, component[field], reason))
            _unknown_fields(component, {
                "username", "mute", "volume", "link", "linkmaster",
                "preset_name", "solo", "lr", "assign_aux1", "assign_aux2",
                "aux1", "aux2",
            }, prefix, skips)

    output_map = {("aux", "ch1"): "mixa", ("aux", "ch2"): "mixb",
                  ("main", "ch1"): "main"}
    for section in ("aux", "main"):
        group = _object(scene.get(section), section)
        for key, component in group.items():
            prefix = "%s.%s" % (section, key)
            component = _object(component, prefix)
            bus = output_map.get((section, key))
            if bus is None:
                skips.append("%s has no io24 output bus" % prefix)
                continue
            if "volume" in component:
                gain = _number(component["volume"], "%s.volume" % prefix,
                               -96.0, 10.0)
                _call(calls, "set_bus_master", (bus, gain), {},
                      "%s master = %.1f dB" % (prefix, gain))
            if "mute" in component:
                on = _toggle(component["mute"], "%s.mute" % prefix)
                mutes.append(("set_bus_mute", (bus, on), {},
                              "%s output mute = %s" % (prefix, on)))
            for field, reason in (
                    ("mono", "output mono fold-down is not representable"),
                    ("username", "text label is not writable"),
                    ("preset_name", "display metadata is not live state"),
                    ("link", "output link is component-tree metadata"),
                    ("linkmaster", "UC component-tree metadata")):
                if field in component:
                    skips.append("%s.%s = %r (%s)" %
                                 (prefix, field, component[field], reason))
            _unknown_fields(component, {
                "username", "mute", "volume", "link", "linkmaster",
                "preset_name", "mono",
            }, prefix, skips)

    fx_group = _object(scene.get("fx"), "fx")
    fx_ch1 = _object(fx_group.get("ch1"), "fx.ch1")
    reverb = _object(fx_ch1.get("reverb"), "fx.ch1.reverb")
    if reverb:
        on = _toggle(reverb.get("on", 1), "fx.ch1.reverb.on")
        size = _number(reverb.get("size", 0.5),
                       "fx.ch1.reverb.size", 0.0, 1.0)
        mix = _number(reverb.get("mix", 0.3),
                      "fx.ch1.reverb.mix", 0.0, 1.0)
        hp = _number(reverb.get("hp_freq", 200.0),
                     "fx.ch1.reverb.hp_freq", 0.0, 500.0)
        predelay = _number(reverb.get("predelay", 0.02),
                           "fx.ch1.reverb.predelay", 0.0001, 0.25)
        _call(calls, "set_reverb", (), {
            "on": on, "size": size, "mix": mix, "hp_freq": hp,
            "predelay": predelay, "fs": fs,
        }, "shared reverb on=%s size=%.3f mix=%.3f" % (on, size, mix))
    _unknown_fields(reverb, {"on", "size", "mix", "hp_freq", "predelay"},
                    "fx.ch1.reverb", skips)
    _unknown_fields(fx_ch1, {"reverb"}, "fx.ch1", skips)
    _unknown_fields(fx_group, {"ch1"}, "fx", skips)

    if "presets" in scene:
        slots, users = describe_presets(scene)
        skips.append(
            "presets library retained and reported (%d device block%s, %d user "
            "preset%s); scene load never overwrites device-resident blocks" %
            (len(slots), "" if len(slots) == 1 else "s", len(users),
             "" if len(users) == 1 else "s"))

    _unknown_fields(scene, {
        "global", "line", "return", "fxreturn", "aux", "main", "fx",
        "presets",
    }, "scene", skips)

    # Routing first, then a requested one-shot mirror, then solo/mute gates.
    # This matches UC's resulting state and ensures the final gate always wins.
    calls.extend(mirrors)
    calls.extend(solos)
    calls.extend(mutes)
    return calls, skips


def describe_presets(scene):
    presets = _object(scene.get("presets"), "presets")
    slots = _object(presets.get("slots"), "presets.slots")
    output = []
    for key in sorted(slots, key=lambda value: int(value)):
        record = _object(slots[key], "presets.slots.%s" % key)
        fx = _object(record.get("voicefx"),
                     "presets.slots.%s.voicefx" % key)
        output.append("  slot %s (%s): %-18r voicefx.on=%s" %
                      (key, "ch1" if int(key) < 2 else "ch2",
                       record.get("preset_name"), fx.get("on")))
    users = list(_object(presets.get("userpresets"),
                         "presets.userpresets"))
    return output, users


def apply(dev, calls):
    """Apply a validated plan, stopping on the first transport/runtime error."""
    missing = sorted({name for name, _args, _kwargs, _desc in calls
                      if not callable(getattr(dev, name, None))})
    if missing:
        raise AttributeError("device backend is missing setter%s: %s" %
                             ("" if len(missing) == 1 else "s",
                              ", ".join(missing)))
    done = 0
    for name, args, kwargs, description in calls:
        try:
            getattr(dev, name)(*args, **kwargs)
            done += 1
        except Exception as error:
            print("    ! %s: %s" % (description, error))
            return done, 1
    return done, 0


def _parser():
    parser = argparse.ArgumentParser(
        description="Apply a Universal Control `.scene` file to the io24")
    parser.add_argument("scene", nargs="?", help="path to the .scene JSON file")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="validate and print the complete plan without USB")
    parser.add_argument("--sample-rate", type=float, default=48000.0,
                        help="device sample rate for DSP coefficients (default 48000)")
    parser.add_argument("--vintage-eq", action="store_true",
                        help=argparse.SUPPRESS)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if not args.scene:
        _parser().print_help()
        return 0
    if not os.path.exists(args.scene):
        raise SystemExit("no such scene file: %s" % args.scene)
    scene = load(args.scene)
    calls, skips = plan(scene, vintage=args.vintage_eq,
                        sample_rate_hz=args.sample_rate)

    print("scene: %s" % os.path.basename(args.scene))
    slots, users = describe_presets(scene)
    if slots:
        print("\ndevice preset blocks recorded in this scene:")
        for description in slots:
            print(description)
    if users:
        print("user presets in the library: %s" % ", ".join(users))
    print("\n%d setting(s) to apply:" % len(calls))
    for _name, _args, _kwargs, description in calls:
        print("    %s" % description)
    if skips:
        print("\n%d not applied:" % len(skips))
        for skipped in skips:
            print("    - %s" % skipped)
    if args.dry_run:
        print("\n(dry run — nothing sent)")
        return 0

    from io24 import Io24
    device = Io24()
    try:
        print("\napplying...")
        done, failed = apply(device, calls)
        print("applied %d, failed %d" % (done, failed))
        return 1 if failed else 0
    finally:
        device.close()


if __name__ == "__main__":
    raise SystemExit(main())
