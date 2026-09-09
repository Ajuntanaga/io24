#!/usr/bin/env python3
"""Apply a Universal Control `.scene` file to the io24 from Linux.

Universal Control saves the whole device state as JSON, in
`Documents/PreSonus/Revelator IO/Scene/*.scene`. The field names are PreSonus's
own, and nearly all of them map straight onto setters this driver already has --
so a scene authored in UC on Windows or macOS can be applied here without
using the device-slot transaction.

    python3 io24_scene.py "B A S E.scene"
    python3 io24_scene.py --dry-run Main.scene

What a scene contains, and what happens to each part:

  global      outputDelay, outputDelayBus, phonesSrc    -> applied
              aux1_mirror_main, auxMuteMode,
              presetButtonMode                          -> host-side action or
                                                           separate device path
  line/chN    preampgain, 48v, mute, link,
              processingChannel, volume, aux1, aux2,
              assign_aux1, assign_aux2                  -> applied
              filter.hpf, gate, comp, limit             -> applied
              eq                                        -> SKIPPED, see below
              voicefx                                   -> SKIPPED, see below
  presets     slots 0..3, userpresets                   -> read and reported;
                                                           slots are complete
                                                           channel/effect records

UC 4.7.2's slot-save representation is now decoded: scene slots 0/1 are the two
records for channel 1, slots 2/3 are the two for channel 2, and the same JSON
object serializes into a ``SetP/Appl(0)/MemP/Stat`` record. The serializer,
frame builder, and explicit device-slot save method live in
``io24_preset_record.py`` and ``io24.py``. This scene-import script deliberately
does not overwrite device slots as a side effect of applying a scene.

A channel's EQ comes in one of two forms and they are treated differently:

  * the **Standard** model stores real Hz, Q and gain per band (`eqfreq1..4`
    etc.), tagged with the same class GUID the firmware's factory presets use.
    That is the device's native representation and it is applied as-is.
  * the **Vintage 1970s** model stores `lowgain/lowfreq`, `lowmidgain/
    lowmidfreq`, `himidgain/himidfreq`, `higain`, where the `*freq` values are
    small integers selecting switch positions, not Hz. UC 4.7.2's own
    `fatchannelxt.xml` gives their exact display frequencies. The direct device
    coefficient builder for the Vintage model is still not recovered, so this
    form is always SKIPPED. The former `--vintage-eq` Standard-biquad
    approximation is disabled and cannot produce a direct-live call.

**voicefx** is skipped only by this script's direct-live apply path. Its JSON is
preserved in a complete slot object and is valid input to the pure
``MemP/Stat`` serializer. UC restores the selected model/class before applying
that model's fields. A slot object for either channel can carry its own
VoiceFX choice, but every recall configures the same singleton block-201 model
and state; different slot values do not create independent processors.
Transformer/Doubler has two structural private-reverb lanes with one shared
parameter set, but stock simultaneous routing of those lanes remains unproved.
It does not store block-202 reverb/send fields.

Everything skipped is reported rather than silently dropped.
"""
import json
import os
import sys

SOURCE = {1: "line/ch1", 2: "line/ch2"}

# UC tags each processing block with a class GUID, and the compressor GUID says
# which MODEL is in use. The two channels can differ, and the models do not share
# a parameter set -- Standard has threshold/ratio/gain, FET has input/output and
# a ratio index -- so the GUID has to be honoured or the values land in the wrong
# maths. Observed in the recovered scenes; the Tube id has not been seen yet.
COMP_MODELS = {
    "{870D04F7-212E-4F9C-ADBB-39A97216433F}": 0,     # Standard
    "{7F8A4262-D377-48E3-9D48-15D82C400A71}": 1,     # Tube
    "{1F831EC1-B8AC-4EE9-AD53-54227AF53D58}": 2,     # FET (input/output/ratio index)
}
# The full parametric EQ carries this class; it is the same GUID the firmware's
# own factory presets use, i.e. the device's native EQ representation.
EQ_PARAMETRIC = "{A0A8A068-14F0-4B04-BB6F-AF8329D0E8EE}"
EQ_PASSIVE = "{C0730CBB-5135-4558-9222-C40BDBA036ED}"
EQ_VINTAGE = "{E1C5E024-C5CD-473C-B08A-6EC177812E01}"

# ---------------------------------------------------------------------------
# UC 4.7.2 `fatchannelxt.xml` names these exact switch positions.  The values
# are no longer a Neve-based guess.  What remains unresolved is the proprietary
# Vintage coefficient builder: feeding these values to the Standard biquad
# path is only an approximation, so it is never executable as a live call.
VINTAGE_LOW_HZ = (35.0, 60.0, 110.0, 220.0)
VINTAGE_LOWMID_HZ = (360.0, 700.0, 1600.0)
VINTAGE_HIMID_HZ = (3200.0, 4800.0, 7200.0)
VINTAGE_HIGH_HZ = 12000.0


def load(path):
    # UC writes these with a BOM on some systems.
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _num(d, key, default=None):
    v = d.get(key, default)
    return None if v is None else float(v)


def plan(scene, vintage=False):
    """Work out every call, without touching the device. Returns (calls, skips).

    A call is (method_name, args, kwargs, human description).
    """
    calls, skips = [], []
    g = scene.get("global", {})

    od, odb = _num(g, "outputDelay"), g.get("outputDelayBus")
    if od is not None:
        if odb is not None:
            calls.append(("set_output_delay_bus", (int(odb),), {},
                          "output delay bus = %d" % int(odb)))
        calls.append(("set_output_delay", (od,), {},
                      "output delay = %.0f ms" % (od * 1000.0)))
    if "phonesSrc" in g:
        calls.append(("set_phones_source", (g["phonesSrc"],), {},
                      "headphones source = %s" % g["phonesSrc"]))
    for k in ("aux1_mirror_main", "aux2_mirror_main",
              "auxMuteMode", "presetButtonMode"):
        if k in g:
            skips.append("global.%s = %s (host-side in UC; no device parameter)"
                         % (k, g[k]))

    line = scene.get("line", {})
    # link is one device-wide setting; take it from channel 1
    if "link" in line.get("ch1", {}):
        on = bool(line["ch1"]["link"])
        calls.append(("set_channel_link", (on,), {}, "stereo link = %s" % on))

    for ch in (1, 2):
        c = line.get("ch%d" % ch)
        if not c:
            continue
        pre = "ch%d" % ch
        if "preampgain" in c:
            calls.append(("set_gain", (ch, float(c["preampgain"])), {},
                          "%s preamp gain = %.1f dB" % (pre, c["preampgain"])))
        if "48v" in c:
            calls.append(("set_phantom", (ch, bool(c["48v"])), {},
                          "%s phantom = %s" % (pre, bool(c["48v"]))))
        if "mute" in c:
            calls.append(("set_mute", (ch, bool(c["mute"])), {},
                          "%s mute = %s" % (pre, bool(c["mute"]))))
        if "processingChannel" in c:
            src = int(c["processingChannel"]) + 1
            calls.append(("set_processing_channel", (ch, src), {},
                          "%s DSP fed by input %d" % (pre, src)))

        # Sends. UC keeps a level and a separate assign flag per bus, which is
        # exactly the send model this driver grew for the aux buses.
        for key, bus, assign in (("volume", "main", "lr"),
                                 ("aux1", "mixa", "assign_aux1"),
                                 ("aux2", "mixb", "assign_aux2")):
            if key in c:
                calls.append(("set_send_db", (SOURCE[ch], bus, float(c[key])), {},
                              "%s -> %s = %.1f dB" % (pre, bus, c[key])))
            if assign in c:
                calls.append(("set_send_assigned",
                              (SOURCE[ch], bus, bool(c[assign])), {},
                              "%s -> %s assigned = %s" % (pre, bus, bool(c[assign]))))

        f = c.get("filter", {})
        if "hpf" in f:
            calls.append(("set_highpass_freq", (ch, float(f["hpf"])), {},
                          "%s high-pass = %.0f Hz" % (pre, f["hpf"])))

        gt = c.get("gate")
        if gt:
            calls.append(("set_gate", (ch,), dict(
                on=bool(gt.get("on", 1)),
                threshold_db=float(gt.get("threshold", -40.0)),
                range_db=float(gt.get("range", -60.0)),
                attack_s=float(gt.get("attack", 0.01)),
                release_s=float(gt.get("release", 0.3)),
                keyfilter_hz=float(gt.get("keyfilter", 0.0)),
                expander=bool(gt.get("expander", 1)),
                keylisten=bool(gt.get("keylisten", 0))),
                "%s gate on=%s thr=%.1f dB" % (pre, bool(gt.get("on", 1)),
                                               gt.get("threshold", -40.0))))

        cp = c.get("comp")
        if cp:
            # The channels can be running DIFFERENT compressor models, and the
            # __classid says which. They do not share a parameter set: Standard
            # has threshold/ratio/gain, FET has input/output and a ratio INDEX.
            # Feeding FET's `ratio: 0` to the Standard maths as a ratio would be
            # nonsense, so dispatch on the class.
            class_id = cp.get("__classid")
            model = COMP_MODELS.get(class_id)
            if model is None:
                skips.append("%s compressor class %s is unknown; skipped before "
                             "any model-specific write" %
                             (pre, class_id or "<missing>"))
            elif model == 2:
                kw = dict(on=bool(cp.get("on", 1)),
                          input_db=float(cp.get("input", 0.0)),
                          output_db=float(cp.get("output", 0.0)),
                          attack_s=float(cp.get("attack", 0.02)),
                          release_s=float(cp.get("release", 0.15)),
                          ratio_index=int(cp.get("ratio", 0)),
                          keyfilter_hz=float(cp.get("keyfilter", 0.0)),
                          keylisten=bool(cp.get("keylisten", 0)))
                desc = "%s comp FET on=%s in=%.1f out=%.1f ratio_idx=%d" % (
                    pre, bool(cp.get("on", 1)), cp.get("input", 0.0),
                    cp.get("output", 0.0), int(cp.get("ratio", 0)))
                kw["model"] = model
                calls.append(("set_compressor", (ch,), kw, desc))
            elif model == 1:
                kw = dict(on=bool(cp.get("on", 1)),
                          peak=float(cp.get("peak", 0.0)),
                          gain=float(cp.get("gain", 40.0)),
                          limit_mode=bool(cp.get("mode", 0)),
                          keyfilter_hz=float(cp.get("keyfilter", 0.0)),
                          keylisten=bool(cp.get("keylisten", 0)),
                          model=model)
                desc = "%s comp Tube on=%s peak=%.1f gain=%.1f mode=%s" % (
                    pre, bool(cp.get("on", 1)), cp.get("peak", 0.0),
                    cp.get("gain", 40.0),
                    "limit" if cp.get("mode", 0) else "compress")
                calls.append(("set_compressor", (ch,), kw, desc))
            else:
                kw = dict(on=bool(cp.get("on", 1)),
                          threshold_db=float(cp.get("threshold", -24.0)),
                          ratio=max(1.0, float(cp.get("ratio", 3.0))),
                          attack_s=float(cp.get("attack", 0.02)),
                          release_s=float(cp.get("release", 0.15)),
                          gain_db=float(cp.get("gain", 0.0)),
                          softknee=bool(cp.get("softknee", 0)),
                          automode=bool(cp.get("automode", 0)),
                          keyfilter_hz=float(cp.get("keyfilter", 0.0)),
                          keylisten=bool(cp.get("keylisten", 0)))
                desc = "%s comp Standard on=%s thr=%.1f ratio=%.1f" % (
                    pre, bool(cp.get("on", 1)), cp.get("threshold", -24.0),
                    kw["ratio"])
                kw["model"] = model
                calls.append(("set_compressor", (ch,), kw, desc))

        lm = c.get("limit")
        if lm:
            calls.append(("set_limiter", (ch, bool(lm.get("limiteron", 0)),
                                          float(lm.get("threshold", -28.0))), {},
                          "%s limiter on=%s thr=%.1f dBFS" % (
                              pre, bool(lm.get("limiteron", 0)),
                              lm.get("threshold", -28.0))))

        eq = c.get("eq")
        if eq and "eqgain1" in eq and eq.get("__classid", EQ_PARAMETRIC) == EQ_PARAMETRIC:
            # The FULL parametric form: real Hz, real Q, per band. Its class GUID
            # is the same one the firmware's factory presets carry, so this is
            # the device's native EQ representation and maps straight across.
            if not eq.get("eqallon", 1):
                calls.append(("eq_off", (ch,), {}, "%s eq bypassed" % pre))
            else:
                for n, band in enumerate(("low", "lowmid", "himid", "high"), 1):
                    if not eq.get("eqbandon%d" % n, 1):
                        calls.append(("set_eq_band", (ch, band), {"shape": "off"},
                                      "%s eq %s off" % (pre, band)))
                        continue
                    # `eqbandopN` exists only for the outer bands and selects
                    # shelf vs peaking there. Treated as shelf when set; the
                    # middle bands have no such field and are always peaking.
                    op = eq.get("eqbandop%d" % n)
                    if n == 1:
                        shape = "lowshelf" if op else "peaking"
                    elif n == 4:
                        shape = "highshelf" if op else "peaking"
                    else:
                        shape = "peaking"
                    calls.append(("set_eq_band", (ch, band), dict(
                        shape=shape,
                        freq_hz=float(eq["eqfreq%d" % n]),
                        gain_db=float(eq.get("eqgain%d" % n, 0.0)),
                        q=float(eq.get("eqq%d" % n, 0.7))),
                        "%s eq %s %s %.0f Hz %+.1f dB Q%.2f" % (
                            pre, band, shape, eq["eqfreq%d" % n],
                            eq.get("eqgain%d" % n, 0.0), eq.get("eqq%d" % n, 0.7))))
        elif eq:
            suffix = ("; --vintage-eq is disabled" if vintage and
                      eq.get("__classid") == EQ_VINTAGE else "")
            skips.append("%s eq (%s, class=%s) — alternate-model state is "
                         "preserved but direct replay is fail-closed because its "
                         "exact coefficient builder is not recovered%s"
                         % (pre, "on" if eq.get("eqallon") else "off",
                            eq.get("__classid", "unknown"), suffix))
        vf = c.get("voicefx")
        if vf:
            skips.append("%s voicefx (class=%s on=%s mix=%s) — preserved for "
                         "native Stat save/recall; omitted from direct setter replay"
                         % (pre, vf.get("__classid", "unknown"), vf.get("on"),
                            vf.get("mix")))
        for k in ("pan", "stereopan", "FXA", "solo", "dawpostdsp", "dspAmount"):
            if k in c:
                skips.append("%s.%s = %s (no driver support yet)" % (pre, k, c[k]))
    return calls, skips


def describe_presets(scene):
    pr = scene.get("presets", {})
    out = []
    slots = pr.get("slots", {})
    for k in sorted(slots, key=lambda x: int(x)):
        s = slots[k]
        vfx = s.get("voicefx", {})
        out.append("  slot %s (%s): %-18r voicefx.on=%s"
                   % (k, "ch1" if int(k) < 2 else "ch2",
                      s.get("preset_name"), vfx.get("on")))
    up = list(pr.get("userpresets", {}))
    return out, up


def apply(dev, calls):
    done = failed = 0
    for name, args, kwargs, desc in calls:
        fn = getattr(dev, name, None)
        if fn is None:
            print("    ! no such setter: %s" % name)
            failed += 1
            continue
        try:
            fn(*args, **kwargs)
            done += 1
        except Exception as e:
            print("    ! %s: %s" % (desc, e))
            failed += 1
    return done, failed


def main():
    argv = sys.argv[1:]
    dry = "--dry-run" in argv or "-n" in argv
    vintage = "--vintage-eq" in argv
    argv = [a for a in argv if not a.startswith("-")]
    if not argv:
        print(__doc__)
        return
    path = argv[0]
    if not os.path.exists(path):
        raise SystemExit("no such scene file: %s" % path)
    scene = load(path)
    calls, skips = plan(scene, vintage=vintage)

    print("scene: %s" % os.path.basename(path))
    slots, up = describe_presets(scene)
    if slots:
        print("\ndevice preset slots recorded in this scene:")
        for s in slots:
            print(s)
    if up:
        print("user presets in the library: %s" % ", ".join(up))

    print("\n%d setting(s) to apply:" % len(calls))
    for _, _, _, desc in calls:
        print("    %s" % desc)
    if skips:
        print("\n%d not applied:" % len(skips))
        for s in skips:
            print("    - %s" % s)

    if dry:
        print("\n(dry run — nothing sent)")
        return

    from io24 import Io24
    dev = Io24()
    try:
        print("\napplying...")
        done, failed = apply(dev, calls)
        print("applied %d, failed %d" % (done, failed))
    finally:
        dev.close()


if __name__ == "__main__":
    main()
