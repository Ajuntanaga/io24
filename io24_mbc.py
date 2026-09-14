"""Host-side multiband compressor for the io24.

The device cannot do this: the firmware capability sweep in PROTOCOL.md is a
clean, measured negative — no `multiband`, `crossover` or `fft` vocabulary
exists anywhere in it. So this is not a device feature and never pretends to
be one. It is a PipeWire filter-chain running on the computer. Since
2026-09-11 it is the Fat Channel's fourth compressor type, Multiband: the
input insert below takes each input from USB capture, right after the unit's
Fat Channel, and plays it back into the unit in place of the input's own feed.
The older sink form (`Chain`, "io24 Multiband" for application playback) is
kept for the command line; the GTK Host no longer offers it. This module also
owns two distinct passive capture-bus sources; those paths never route
themselves to playback or pretend to be device DSP.

Topology of one channel's graph, all standard pieces:

    in -> [LR4 low     ] -> sc3 -> \\
       -> [LR4 low-mid ] -> sc3 ->  mixer -> out
       -> [LR4 high-mid] -> sc3 ->
       -> [LR4 high    ] -> sc3 -> /

* The crossover is Linkwitz-Riley 4th order, built from PipeWire's builtin
  biquads (two cascaded Butterworth 2nd-order sections per leg — that IS an
  LR4), and each band also passes the all-pass of the splits it does not
  use, so the four bands sum flat (CROSSOVER_LEGS).
* The per-band compressor is `sc3` from swh-plugins, the LADSPA stereo
  compressor with a sidechain input (see SC3_SO). PipeWire 1.6's filter-chain
  hosts LADSPA and builtins only (no LV2).
* The chain runs in PipeWire's own process graph (C, realtime scheduled), not
  in this Python process — enabling it costs the app nothing.

Runtime model: the chain is hosted by a child `pipewire -c <ourconf>` process,
which is the documented way to run an on-demand filter-chain; killing the
child removes the sink cleanly. Parameters are changed live with
`pw-cli set-param <node> Props`.
"""

import json
import math
import os
import shutil
import subprocess
import tempfile
import time

SINK_NAME = "io24-multiband"
SINK_DESC = "io24 Multiband"
BUS_CAPTURE_PAIRS = {"mixa": (2, 3), "mixb": (4, 5)}
BUS_SOURCE_NAMES = {
    "mixa": "io24-host-mixa",
    "mixb": "io24-host-mixb",
}
BUS_SOURCE_DESCRIPTIONS = {
    "mixa": "io24 Host Mix A",
    "mixb": "io24 Host Mix B",
}
CAPTURE_POSITIONS = ("FL", "FR", "FC", "LFE", "RL", "RR")

# sc3 (swh-plugins, LADSPA 1427): stereo compressor with a dedicated mono
# SIDECHAIN input and a "Chain balance" control — 0 means the detector reads
# the band itself, 1 means it reads the sidechain. That is what makes per-band
# key filtering and key listen possible. Port names read from the plugin's own
# descriptor via ctypes, not guessed.
SC3_SO = "sc3_1427"

BANDS = ("low", "lowmid", "highmid", "high")

DEFAULTS = {
    "xovers": [150.0, 800.0, 4500.0],
    "low":     {"threshold": -18.0, "ratio": 3.0, "attack": 20.0,
                "release": 200.0, "knee": 6.0, "makeup": 0.0, "key": 100.0},
    "lowmid":  {"threshold": -20.0, "ratio": 2.5, "attack": 12.0,
                "release": 150.0, "knee": 6.0, "makeup": 0.0, "key": 400.0},
    "highmid": {"threshold": -20.0, "ratio": 2.5, "attack": 6.0,
                "release": 100.0, "knee": 6.0, "makeup": 0.0, "key": 2000.0},
    "high":    {"threshold": -22.0, "ratio": 3.0, "attack": 3.0,
                "release": 80.0, "knee": 6.0, "makeup": 0.0, "key": 8000.0},
}

# Per-band character presets, mapped onto what sc3 actually has (it exposes no
# RMS/peak switch, so the three types are shaped with time constants and knee):
#   Standard — the balanced starting point
#   Tube     — slow, soft-kneed, LA-2A-ish; Limit mode = steep ratio + faster grab
#   FET      — fast and hard-kneed, 1176-ish
TYPES = {
    "standard": {"attack": 15.0, "release": 150.0, "knee": 3.0},
    "tube":     {"attack": 30.0, "release": 300.0, "knee": 9.0},
    "fet":      {"attack": 1.5,  "release": 80.0,  "knee": 1.0},
}
TUBE_LIMIT = {"ratio": 20.0, "attack": 8.0}

SNAPSHOT_VERSION = 1
BUS_SOURCE_KEYS = ("mixa", "mixb")
_BAND_RANGES = {
    "threshold": (-40.0, 0.0),
    "ratio": (1.0, 20.0),
    "attack": (1.0, 100.0),
    "release": (10.0, 800.0),
    "knee": (0.0, 12.0),
    "makeup": (0.0, 24.0),
    "key": (30.0, 16000.0),
}
_BAND_FIELDS = frozenset({
    "type", "threshold", "ratio", "attack", "release", "knee",
    "makeup", "auto", "limit", "key_filter", "key", "listen",
})


def _finite_number(value, name, low, high):
    if isinstance(value, bool):
        raise ValueError("multiband %s must be numeric" % name)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("multiband %s must be numeric" % name) from error
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(
            "multiband %s must be in [%s, %s]" % (name, low, high))
    return number


def default_snapshot(enabled=False):
    """Return the complete computer-side state shown by the GTK controls."""
    return {
        "version": SNAPSHOT_VERSION,
        "enabled": bool(enabled),
        "xovers": list(DEFAULTS["xovers"]),
        "bands": {
            band: {
                "type": "standard",
                "threshold": float(DEFAULTS[band]["threshold"]),
                "ratio": float(DEFAULTS[band]["ratio"]),
                "attack": float(DEFAULTS[band]["attack"]),
                "release": float(DEFAULTS[band]["release"]),
                "knee": float(DEFAULTS[band]["knee"]),
                "makeup": float(DEFAULTS[band]["makeup"]),
                "auto": False,
                "limit": False,
                "key_filter": False,
                "key": float(DEFAULTS[band]["key"]),
                "listen": False,
            }
            for band in BANDS
        },
    }


def validate_snapshot(state):
    """Validate and normalize one complete Host-only multiband snapshot."""
    if not isinstance(state, dict):
        raise ValueError("multiband state must be an object")
    expected = {"version", "enabled", "xovers", "bands"}
    if set(state) != expected:
        raise ValueError("multiband state fields must be %s" %
                         ", ".join(sorted(expected)))
    if state["version"] != SNAPSHOT_VERSION:
        raise ValueError("multiband snapshot version must be 1")
    if not isinstance(state["enabled"], bool):
        raise ValueError("multiband enabled must be Boolean")
    xovers = state["xovers"]
    if not isinstance(xovers, list) or len(xovers) != 3:
        raise ValueError("multiband xovers must contain three values")
    ranges = ((40.0, 400.0), (300.0, 2500.0), (2000.0, 12000.0))
    xovers = [_finite_number(value, "xover %d" % (index + 1), *ranges[index])
              for index, value in enumerate(xovers)]
    if not xovers[0] < xovers[1] < xovers[2]:
        raise ValueError("multiband xovers must be strictly increasing")

    raw_bands = state["bands"]
    if not isinstance(raw_bands, dict) or set(raw_bands) != set(BANDS):
        raise ValueError("multiband bands must contain low/lowmid/highmid/high")
    bands = {}
    for band in BANDS:
        raw = raw_bands[band]
        if not isinstance(raw, dict) or set(raw) != _BAND_FIELDS:
            raise ValueError("multiband %s fields are incomplete or unknown" % band)
        kind = raw["type"]
        if kind not in TYPES:
            raise ValueError("multiband %s type is invalid" % band)
        normalized = {"type": kind}
        for key, (low, high) in _BAND_RANGES.items():
            normalized[key] = _finite_number(
                raw[key], "%s %s" % (band, key), low, high)
        for key in ("auto", "limit", "key_filter", "listen"):
            if not isinstance(raw[key], bool):
                raise ValueError("multiband %s %s must be Boolean" % (band, key))
            normalized[key] = raw[key]
        bands[band] = normalized
    return {
        "version": SNAPSHOT_VERSION,
        "enabled": state["enabled"],
        "xovers": xovers,
        "bands": bands,
    }


def auto_makeup(threshold, ratio):
    """Gain compensation from the settings, like the device compressors do.

    The same shape the FET model uses: the deeper the threshold and the
    steeper the ratio, the more static gain is returned. 0.7 rather than 1.0
    because full-theoretical makeup overshoots on programme material.
    """
    return max(0.0, min(24.0, -threshold * (1.0 - 1.0 / max(1.0, ratio)) * 0.7))


def sc4_available():
    """Path of the sc4 LADSPA library, or None.

    Checked, not assumed: the UI uses this to say plainly what is missing
    ('sudo apt install swh-plugins') instead of failing at load time.
    """
    for d in ("/usr/lib/ladspa", "/usr/lib/x86_64-linux-gnu/ladspa",
              "/usr/local/lib/ladspa"):
        p = os.path.join(d, SC3_SO + ".so")
        if os.path.exists(p):
            return p
    return None


def pipewire_available():
    return (shutil.which("pipewire") is not None
            and shutil.which("pw-cli") is not None)


# Q of one Butterworth section, and of the all-pass a Linkwitz-Riley pair's
# low and high halves sum to. Set on every crossover biquad rather than left to
# the builtin's default.
BUTTERWORTH_Q = 1.0 / math.sqrt(2.0)

# Each band as a cascade of (biquad, split index). A Linkwitz-Riley half is
# two Butterworth sections at its split, and LP + HP of one pair is an
# all-pass A. So low = LP0.A1.A2, low-mid = HP0.LP1.A2, high-mid = HP0.HP1.LP2
# and high = HP0.HP1.HP2 sum to A0.A1.A2: a flat magnitude. The earlier
# parallel legs (LP0 | HP0.LP1 | HP1.LP2 | HP2) lacked those phase terms and
# summed to a dip of about 1.2 dB near the middle split at the defaults.
CROSSOVER_LEGS = (
    (("bq_lowpass", 0), ("bq_lowpass", 0),
     ("bq_allpass", 1), ("bq_allpass", 2)),
    (("bq_highpass", 0), ("bq_highpass", 0),
     ("bq_lowpass", 1), ("bq_lowpass", 1), ("bq_allpass", 2)),
    (("bq_highpass", 0), ("bq_highpass", 0),
     ("bq_highpass", 1), ("bq_highpass", 1),
     ("bq_lowpass", 2), ("bq_lowpass", 2)),
    (("bq_highpass", 0), ("bq_highpass", 0),
     ("bq_highpass", 1), ("bq_highpass", 1),
     ("bq_highpass", 2), ("bq_highpass", 2)),
)


def crossover_nodes():
    """For each split, every biquad tuned to it (its filters and the
    all-passes that compensate for it), so a split moves as one."""
    nodes = ([], [], [])
    for band, leg in enumerate(CROSSOVER_LEGS):
        for index, (_label, split) in enumerate(leg):
            nodes[split].append("b%d_%d" % (band, index))
    return tuple(tuple(names) for names in nodes)


def _bq(name, label, freq):
    return {"type": "builtin", "name": name, "label": label,
            "control": {"Freq": float(freq), "Q": BUTTERWORTH_Q}}


def _sc3(name, band, values=None):
    b = values or DEFAULTS[band]
    return {"type": "ladspa", "name": name, "plugin": SC3_SO, "label": "sc3",
            "control": {
                "Attack time (ms)": b["attack"],
                "Release time (ms)": b["release"],
                "Threshold level (dB)": b["threshold"],
                "Ratio (1:n)": b["ratio"],
                "Knee radius (dB)": b["knee"],
                "Makeup gain (dB)": b["makeup"],
                "Chain balance": 1.0 if b.get("key_filter", False) else 0.0,
            }}                            # filter is engaged (balance -> 1)


def _lin(name, mult):
    return {"type": "builtin", "name": name, "label": "linear",
            "control": {"Mult": float(mult), "Add": 0.0}}


def build_graph(xovers, with_comp, state=None):
    """One channel of the 4-band graph; the module clones it per channel.

    Per band i:  band signal -> sc3 (both stereo inputs)
                 band signal -> bq_bandpass (the KEY filter) -> sc3 sidechain
                 sc3 out  -> linear lc_i (1 normally, 0 in key-listen)
                 key path -> linear lk_i (0 normally, 1 in key-listen)
                 both linears -> the master mixer (8 inputs: exactly 4 bands x 2)

    Chain balance decides what the detector hears: 0 = the band, 1 = the key
    filter. Key LISTEN swaps the audible path to the key signal itself, done
    with the two linear gains because a filter-chain topology cannot be
    rewired at runtime — but control values can move.

    with_comp=False: crossover legs straight into the mixer (transparent).
    """
    state = validate_snapshot(state) if state is not None else None
    f0, f1, f2 = state["xovers"] if state is not None else xovers
    nodes = [{"type": "builtin", "name": "split", "label": "copy"}]
    links = []

    def leg(prefix, kinds):
        """A cascade of biquads; returns (entry_port, exit_name)."""
        prev = None
        for i, (label, freq) in enumerate(kinds):
            nm = "%s%d" % (prefix, i)
            nodes.append(_bq(nm, label, freq))
            if prev is not None:
                links.append({"output": prev + ":Out", "input": nm + ":In"})
            prev = nm
        return "%s0:In" % prefix, prev

    # Linkwitz-Riley crossover, all-pass compensated (CROSSOVER_LEGS)
    band_tails = []
    splits = (f0, f1, f2)
    legs = [[(label, splits[split]) for label, split in leg]
            for leg in CROSSOVER_LEGS]
    for bi, kinds in enumerate(legs):
        entry, tail = leg("b%d_" % bi, kinds)
        links.append({"output": "split:Out", "input": entry})
        band_tails.append(tail)

    nodes.append({"type": "builtin", "name": "sum", "label": "mixer"})
    mix_in = 1

    for bi, band in enumerate(BANDS):
        tail = band_tails[bi]
        if with_comp:
            values = state["bands"][band] if state is not None else DEFAULTS[band]
            key = "k%d" % bi
            nodes.append({"type": "builtin", "name": key,
                          "label": "bq_bandpass",
                          # Q matters: at the builtin's default the passband is
                          # so broad that a key at 150 Hz still heard a 1 kHz
                          # tone — measured as "key filter does nothing"
                          "control": {"Freq": values["key"],
                                      "Q": 1.5}})
            links.append({"output": tail + ":Out", "input": key + ":In"})
            comp = "c%d" % bi
            nodes.append(_sc3(comp, band, values))
            links.append({"output": tail + ":Out",
                          "input": comp + ":Left input"})
            links.append({"output": tail + ":Out",
                          "input": comp + ":Right input"})
            links.append({"output": key + ":Out",
                          "input": comp + ":Sidechain"})
            lc, lk = "lc%d" % bi, "lk%d" % bi
            listening = bool(values.get("listen", False))
            nodes.append(_lin(lc, 0.0 if listening else 1.0))
            nodes.append(_lin(lk, 1.0 if listening else 0.0))
            links.append({"output": comp + ":Left output", "input": lc + ":In"})
            links.append({"output": key + ":Out", "input": lk + ":In"})
            for nm in (lc, lk):
                links.append({"output": nm + ":Out",
                              "input": "sum:In %d" % mix_in})
                mix_in += 1
        else:
            links.append({"output": tail + ":Out",
                          "input": "sum:In %d" % mix_in})
            mix_in += 1

    return {"nodes": nodes, "links": links,
            "inputs": ["split:In"], "outputs": ["sum:Out"]}


def build_conf(target=None, xovers=None, with_comp=None, state=None):
    """A complete pipewire.conf hosting the chain as a sink."""
    if with_comp is None:
        with_comp = sc4_available() is not None
    graph = build_graph(xovers or DEFAULTS["xovers"], with_comp, state=state)
    playback = {"node.passive": True}
    if target:
        playback["target.object"] = target
    args = {
        "node.description": SINK_DESC,
        "media.name": SINK_DESC,
        "filter.graph": graph,
        "audio.channels": 2,
        "audio.position": ["FL", "FR"],
        "capture.props": {
            "node.name": SINK_NAME,
            "media.class": "Audio/Sink",
        },
        "playback.props": playback,
    }
    return ("context.properties = { log.level = 2 }\n"
            "context.modules = [\n"
            "  { name = libpipewire-module-filter-chain\n"
            "    args = %s\n"
            "  }\n"
            "]\n" % json.dumps(args, indent=2))


def _validate_bus(bus):
    if bus not in BUS_SOURCE_KEYS:
        raise ValueError("bus source must be mixa or mixb")
    return bus


def build_bus_source_graph(bus):
    """Select one exact capture pair and expose it at fixed unity gain."""
    bus = _validate_bus(bus)
    nodes = [
        {"type": "builtin", "name": "src%d" % index, "label": "copy"}
        for index in range(len(CAPTURE_POSITIONS))
    ]
    nodes.extend((_lin("source_l", 1.0), _lin("source_r", 1.0)))
    left_index, right_index = BUS_CAPTURE_PAIRS[bus]
    return {
        "nodes": nodes,
        "links": [
            {"output": "src%d:Out" % left_index,
             "input": "source_l:In"},
            {"output": "src%d:Out" % right_index,
             "input": "source_r:In"},
        ],
        "inputs": ["src%d:In" % index
                   for index in range(len(CAPTURE_POSITIONS))],
        "outputs": ["source_l:Out", "source_r:Out"],
    }


def build_bus_source_conf(bus, capture_target):
    """PipeWire config for one passive Mix A or Mix B virtual source."""
    bus = _validate_bus(bus)
    if not capture_target:
        raise ValueError("bus source needs a capture target")
    name = BUS_SOURCE_NAMES[bus]
    description = BUS_SOURCE_DESCRIPTIONS[bus]
    args = {
        "node.description": description,
        "media.name": description,
        "filter.graph": build_bus_source_graph(bus),
        "capture.props": {
            "node.name": name + "-capture",
            "media.class": "Stream/Input/Audio",
            "target.object": capture_target,
            "node.passive": True,
            "stream.dont-remix": True,
            "audio.channels": len(CAPTURE_POSITIONS),
            "audio.position": list(CAPTURE_POSITIONS),
        },
        "playback.props": {
            "node.name": name,
            "node.description": description,
            "media.class": "Audio/Source",
            "node.passive": True,
            "stream.dont-remix": True,
            "audio.channels": 2,
            "audio.position": ["FL", "FR"],
        },
    }
    return ("context.properties = { log.level = 2 }\n"
            "context.modules = [\n"
            "  { name = libpipewire-module-filter-chain\n"
            "    args = %s\n"
            "  }\n"
            "]\n" % json.dumps(args, indent=2))


# --------------------------------------------------------------------------
# Multiband as a compressor type: the input insert.
#
# Asked for on 2026-09-11: the multiband as "just another type of compression
# that can be selected, replacing the normal compressor block", and, since the
# unit's own chain cannot be split, "immediately" after the Fat Channel. The
# io24 delivers each input to USB capture after the whole Fat Channel, limiter
# included (its manual: it records "just as you hear it in your headphones,
# complete with the Fat Channel preset"; firmware 0128 has no parameter that
# changes that). So the insert takes the input there:
#
#   capture 1 -> [in1_ 4-band] -> out1 \  Audio/Source "io24 Input 1+2
#   capture 2 -> [in2_ 4-band] -> out2 /  Multiband" (left Input 1, right 2)
#   that source -> [mixer: channels with Multiband] -> USB playback 1-2
#
# An input without Multiband passes through untouched, so the published source
# stands in for capture 1+2 whichever channels are processed. The return is
# centred, both legs at unity, as a mono input sits in the unit's mixer. It
# arrives on USB playback 1-2, the user's choice, so it shares that fader with
# computer audio. route_insert then takes the input's own feed out of each bus
# it was in and makes USB playback 1-2 audible there; unroute_insert undoes
# exactly that.
# --------------------------------------------------------------------------
INSERT_VERSION = 1
INSERT_CHANNELS = (1, 2)
INSERT_CAPTURE_INDEX = {1: 0, 2: 1}      # USB capture channel of each input
INSERT_PROCESS_NAME = "io24-input-multiband-process"
INSERT_SOURCE_NAME = "io24-input-multiband"
INSERT_SOURCE_DESC = "io24 Input 1+2 Multiband"
INSERT_RETURN_NAME = "io24-input-multiband-return"
INSERT_RETURN_SOURCE = "return/ch1"      # the mixer's USB playback 1-2
INSERT_BUSES = ("main", "mixa", "mixb")
# Monitoring now goes to the computer and back, so the buffer is held small
# while an insert runs (GUIDE.md: latency is quantum / rate).
INSERT_QUANTUM = 128


def insert_prefix(channel):
    """Node-name prefix of one channel's 4-band graph inside the insert."""
    return "in%d_" % channel


def _prefixed(graph, prefix):
    """The same graph with every node renamed, so two fit in one chain."""
    def port(ref):
        node, _sep, rest = ref.partition(":")
        return "%s%s:%s" % (prefix, node, rest)
    return {
        "nodes": [dict(node, name=prefix + node["name"])
                  for node in graph["nodes"]],
        "links": [{"output": port(link["output"]),
                   "input": port(link["input"])} for link in graph["links"]],
        "inputs": [port(name) for name in graph["inputs"]],
        "outputs": [port(name) for name in graph["outputs"]],
    }


def _insert_states(states):
    """{channel: snapshot} for the channels with Multiband, validated."""
    if not isinstance(states, dict) or not states:
        raise ValueError("the multiband insert needs at least one channel")
    normalized = {}
    for channel, state in states.items():
        if isinstance(channel, bool) or channel not in INSERT_CHANNELS:
            raise ValueError("multiband insert channel must be 1 or 2")
        normalized[channel] = validate_snapshot(state)
    return normalized


def build_insert_graph(states, with_comp=True):
    """Both inputs from the six-channel capture, each through its own 4-band
    graph when its channel has Multiband, otherwise straight through."""
    states = _insert_states(states)
    nodes = [{"type": "builtin", "name": "src%d" % index, "label": "copy"}
             for index in range(len(CAPTURE_POSITIONS))]
    links = []
    for channel in INSERT_CHANNELS:
        tap = "src%d:Out" % INSERT_CAPTURE_INDEX[channel]
        out = "out%d" % channel
        nodes.append({"type": "builtin", "name": out, "label": "copy"})
        if channel in states:
            sub = _prefixed(build_graph(None, with_comp, state=states[channel]),
                            insert_prefix(channel))
            nodes.extend(sub["nodes"])
            links.extend(sub["links"])
            links.append({"output": tap, "input": sub["inputs"][0]})
            links.append({"output": sub["outputs"][0], "input": out + ":In"})
        else:
            links.append({"output": tap, "input": out + ":In"})
    return {"nodes": nodes, "links": links,
            "inputs": ["src%d:In" % index
                       for index in range(len(CAPTURE_POSITIONS))],
            "outputs": ["out%d:Out" % channel for channel in INSERT_CHANNELS]}


def build_insert_return_graph(channels):
    """Only the processed inputs, centred, for USB playback 1-2."""
    channels = tuple(channels)
    if not channels or any(isinstance(channel, bool) or
                           channel not in INSERT_CHANNELS
                           for channel in channels):
        raise ValueError("the multiband return needs channel 1 and/or 2")
    gains = {"Gain %d" % (index + 1): 1.0 if channel in channels else 0.0
             for index, channel in enumerate(INSERT_CHANNELS)}
    return {
        "nodes": [
            {"type": "builtin", "name": "take1", "label": "copy"},
            {"type": "builtin", "name": "take2", "label": "copy"},
            {"type": "builtin", "name": "mix", "label": "mixer",
             "control": gains},
            {"type": "builtin", "name": "ret_l", "label": "copy"},
            {"type": "builtin", "name": "ret_r", "label": "copy"},
        ],
        "links": [
            {"output": "take1:Out", "input": "mix:In 1"},
            {"output": "take2:Out", "input": "mix:In 2"},
            {"output": "mix:Out", "input": "ret_l:In"},
            {"output": "mix:Out", "input": "ret_r:In"},
        ],
        "inputs": ["take1:In", "take2:In"],
        "outputs": ["ret_l:Out", "ret_r:Out"],
    }


def build_insert_conf(states, capture_target, playback_target, with_comp=None):
    """PipeWire config for the insert: the processing, published as a source,
    and its return into the io24's USB playback 1-2.

    Every device-facing stream names its node and may not fall back to another
    device: an insert that lost the io24 must go quiet, not process the
    laptop's microphone into its speakers.
    """
    states = _insert_states(states)
    if not capture_target or not playback_target:
        raise ValueError("the multiband insert needs the io24's capture and "
                         "playback nodes")
    if with_comp is None:
        with_comp = sc4_available() is not None
    process = {
        "node.description": INSERT_SOURCE_DESC,
        "media.name": INSERT_SOURCE_DESC,
        "filter.graph": build_insert_graph(states, with_comp),
        "capture.props": {
            "node.name": INSERT_PROCESS_NAME,
            "media.class": "Stream/Input/Audio",
            "target.object": capture_target,
            "node.dont-fallback": True,
            "stream.dont-remix": True,
            "audio.channels": len(CAPTURE_POSITIONS),
            "audio.position": list(CAPTURE_POSITIONS),
        },
        "playback.props": {
            "node.name": INSERT_SOURCE_NAME,
            "node.description": INSERT_SOURCE_DESC,
            "media.class": "Audio/Source",
            "stream.dont-remix": True,
            "audio.channels": 2,
            "audio.position": ["FL", "FR"],
        },
    }
    ret = {
        "node.description": "io24 Multiband return",
        "media.name": "io24 Multiband return",
        "filter.graph": build_insert_return_graph(sorted(states)),
        "capture.props": {
            "node.name": INSERT_RETURN_NAME + "-in",
            "media.class": "Stream/Input/Audio",
            "target.object": INSERT_SOURCE_NAME,
            "node.dont-fallback": True,
            "stream.dont-remix": True,
            "audio.channels": 2,
            "audio.position": ["FL", "FR"],
        },
        "playback.props": {
            "node.name": INSERT_RETURN_NAME,
            "media.class": "Stream/Output/Audio",
            "target.object": playback_target,
            "node.dont-fallback": True,
            "channelmix.upmix": False,
            "audio.channels": 2,
            "audio.position": ["FL", "FR"],
        },
    }
    modules = "\n".join(
        "  { name = libpipewire-module-filter-chain\n"
        "    args = %s\n"
        "  }" % json.dumps(args, indent=2) for args in (process, ret))
    return ("context.properties = { log.level = 2 }\n"
            "context.modules = [\n%s\n]\n" % modules)


def default_insert_state():
    """Both inputs' Multiband settings, neither selected, nothing rerouted."""
    return {"version": INSERT_VERSION,
            "channels": {str(channel): default_snapshot()
                         for channel in INSERT_CHANNELS},
            "routing": None, "quantum_before": None}


def _validate_routing(routing):
    """A copy of what route_insert changed in the mixer, or None."""
    if routing is None:
        return None
    if not isinstance(routing, dict) or \
            set(routing) != {"moved", "return_prior"}:
        raise ValueError("multiband routing must hold moved and return_prior")
    moved = routing["moved"]
    if not isinstance(moved, dict) or \
            not set(moved) <= {str(c) for c in INSERT_CHANNELS}:
        raise ValueError("multiband routing moved channels must be 1 or 2")
    normalized = {"moved": {}, "return_prior": {}}
    for key, buses in moved.items():
        if not isinstance(buses, list) or len(set(buses)) != len(buses) or \
                not set(buses) <= set(INSERT_BUSES):
            raise ValueError("multiband routing buses must be main/mixa/mixb")
        normalized["moved"][key] = [bus for bus in INSERT_BUSES if bus in buses]
    prior = routing["return_prior"]
    if not isinstance(prior, dict) or not set(prior) <= set(INSERT_BUSES):
        raise ValueError("multiband routing return buses must be main/mixa/mixb")
    for bus, was in prior.items():
        if not isinstance(was, dict) or set(was) != {"assigned", "off"} or \
                not all(isinstance(was[k], bool) for k in was):
            raise ValueError("multiband routing return state is invalid")
        normalized["return_prior"][bus] = dict(was)
    return normalized


def validate_insert_state(state):
    """Validate and normalize the Host-only Multiband compressor state."""
    if not isinstance(state, dict):
        raise ValueError("multiband insert state must be an object")
    expected = {"version", "channels", "routing", "quantum_before"}
    if set(state) != expected:
        raise ValueError("multiband insert fields must be %s" %
                         ", ".join(sorted(expected)))
    if state["version"] != INSERT_VERSION:
        raise ValueError("multiband insert version must be 1")
    channels = state["channels"]
    if not isinstance(channels, dict) or \
            set(channels) != {str(c) for c in INSERT_CHANNELS}:
        raise ValueError("multiband insert channels must be 1 and 2")
    quantum = state["quantum_before"]
    if quantum is not None and (isinstance(quantum, bool) or
                                not isinstance(quantum, int) or
                                not 0 <= quantum <= 8192):
        raise ValueError("multiband insert quantum_before must be 0..8192")
    return {"version": INSERT_VERSION,
            "channels": {key: validate_snapshot(channels[key])
                         for key in sorted(channels)},
            "routing": _validate_routing(state["routing"]),
            "quantum_before": quantum}


def _audible(dev, source, bus):
    return (dev.send_assigned(source, bus) and dev.has_send_level(source, bus)
            and dev.send_db(source, bus) is not None)


def route_insert(dev, channel, routing=None):
    """Put one input's Multiband return in place of its own feed.

    `dev` is the Io24 driver. In every bus the input is assigned to, USB
    playback 1-2 is made audible (and how it was is noted when it was
    unassigned or off), then the input's send is switched off with its fader
    position kept. Returns the new routing record; `routing` is not changed.
    """
    routing = _validate_routing(routing) or {"moved": {}, "return_prior": {}}
    key = str(channel)
    if key in routing["moved"]:
        return routing
    source = "line/ch%d" % channel
    ret = INSERT_RETURN_SOURCE
    moved = []
    for bus in INSERT_BUSES:
        if not dev.send_assigned(source, bus):
            continue
        if bus not in routing["return_prior"] and not _audible(dev, ret, bus):
            was = {"assigned": bool(dev.send_assigned(ret, bus)),
                   "off": bool(dev.has_send_level(ret, bus) and
                               dev.send_db(ret, bus) is None)}
            if not was["assigned"] or was["off"]:
                routing["return_prior"][bus] = was
            if was["off"] or not dev.has_send_level(ret, bus):
                dev.set_send_db(ret, bus, dev.DEFAULT_SEND_DB)
            if not was["assigned"]:
                dev.set_send_assigned(ret, bus, True)
        dev.set_send_assigned(source, bus, False)
        moved.append(bus)
    routing["moved"][key] = moved
    return routing


def unroute_insert(dev, channel, routing):
    """Undo route_insert for one input. USB playback 1-2 goes back to how it
    was in a bus only once no other input's return still needs it there."""
    routing = _validate_routing(routing) or {"moved": {}, "return_prior": {}}
    for bus in routing["moved"].pop(str(channel), []):
        dev.set_send_assigned("line/ch%d" % channel, bus, True)
    still = {bus for buses in routing["moved"].values() for bus in buses}
    for bus in INSERT_BUSES:
        if bus in still or bus not in routing["return_prior"]:
            continue
        was = routing["return_prior"].pop(bus)
        if was["off"]:
            dev.set_send_db(INSERT_RETURN_SOURCE, bus, None)
        if not was["assigned"]:
            dev.set_send_assigned(INSERT_RETURN_SOURCE, bus, False)
    return routing


def _find_io24_node(direction):
    """Find a PipeWire ALSA input/output node for the connected io24."""
    token = "alsa_%s" % direction
    try:
        out = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True,
                             text=True, timeout=5).stdout
    except Exception:
        return None
    # pw-cli indents real global-id lines with a tab. Split after stripping
    # each line instead of assuming an unindented "\nid "; otherwise the
    # whole listing becomes one block and a laptop ALSA node before the io24
    # can be returned merely because the later io24 marker is also present.
    blocks, current = [], []
    for line in out.splitlines():
        value = line.strip()
        if value.startswith("id ") and "," in value:
            if current:
                blocks.append("\n".join(current))
            current = [value]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    for block in blocks:
        folded = block.casefold()
        if token not in folded or not any(
                marker in folded for marker in ("presonus", "revelator", "io24")):
            continue
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("node.name"):
                name = line.split("=", 1)[1].strip().strip('"')
                if token in name.casefold():
                    return name
    return None


def find_io24_sink():
    """Node name of the io24's playback sink, or None while unplugged."""
    return _find_io24_node("output")


def find_io24_capture_source():
    """Node name of the io24's physical capture source, or None."""
    return _find_io24_node("input")


def node_id(node_name):
    """PipeWire global id for an exact node name, or None."""
    if not node_name:
        return None
    try:
        out = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True,
                             text=True, timeout=5).stdout
    except Exception:
        return None
    current = None
    for line in out.splitlines():
        value = line.strip()
        if value.startswith("id ") and "," in value:
            current = value.split()[1].rstrip(",")
        elif value == 'node.name = "%s"' % node_name:
            return current
    return None


def set_default_output(node_name):
    """Make an existing PipeWire sink the default for new playback."""
    nid = node_id(node_name)
    if nid is None or shutil.which("wpctl") is None:
        return False
    try:
        result = subprocess.run(["wpctl", "set-default", str(nid)],
                                capture_output=True, text=True, timeout=5)
    except Exception:
        return False
    return result.returncode == 0


class Chain:
    """Owns the child pipewire process hosting the sink."""

    NODE_NAME = SINK_NAME
    CONF_PREFIX = "io24-mbc-"
    FRAGMENT = "io24-mbc.conf"
    START_TIMEOUT_S = 2.0

    def __init__(self):
        self.proc = None
        self.conf_path = None
        self.last_error = None

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, target=None, with_comp=None, state=None):
        configured = target is not None or with_comp is not None or state is not None
        # Validate and render before creating any private filesystem state.
        # Invalid saved settings must fail closed without leaving a directory.
        configuration = build_conf(
            target=target, with_comp=with_comp, state=state)
        self.last_error = None
        if not self._launch(configuration, configured):
            self.last_error = "PipeWire process could not start"
            return False
        deadline = time.monotonic() + self.START_TIMEOUT_S
        while self.running:
            if self.node_id() is not None:
                return True
            if time.monotonic() >= deadline:
                self.last_error = "io24 Multiband output node did not appear"
                break
            time.sleep(0.05)
        if self.last_error is None:
            self.last_error = "PipeWire process exited before its output node appeared"
        self.stop()
        return False

    def _launch(self, configuration, configured=True):
        if self.running and not configured:
            return True
        # A configured start means "run this exact graph", not merely "some
        # graph is alive". Replace an existing or crashed child so a True
        # return never hides stale target/settings, and collect stale temp state.
        if self.proc is not None or self.conf_path is not None:
            self.stop()
        # A bare conf with only the filter module dies at startup: a standalone
        # `pipewire -c` needs the whole client stack (protocol-native,
        # client-node, adapter...). Rather than maintain a copy of that
        # boilerplate, use the mechanism PipeWire documents for exactly this:
        # the shipped filter-chain.conf as the base, our chain as a .conf.d
        # fragment, and PIPEWIRE_CONFIG_DIR pointing at a private config dir so
        # nothing leaks into the user's real configuration.
        base = "/usr/share/pipewire/filter-chain.conf"
        if not os.path.exists(base):
            return False
        self.conf_path = tempfile.mkdtemp(prefix=self.CONF_PREFIX)
        try:
            shutil.copy(base, os.path.join(self.conf_path, "filter-chain.conf"))
            frag_dir = os.path.join(self.conf_path, "filter-chain.conf.d")
            os.mkdir(frag_dir)
            with open(os.path.join(frag_dir, self.FRAGMENT), "w") as f:
                f.write(configuration)
            env = dict(os.environ)
            env["PIPEWIRE_CONFIG_DIR"] = self.conf_path
            self.proc = subprocess.Popen(
                ["pipewire", "-c", "filter-chain.conf"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        except (OSError, subprocess.SubprocessError):
            self.proc = None
            shutil.rmtree(self.conf_path, ignore_errors=True)
            self.conf_path = None
            return False
        return True

    def stop(self):
        proc, self.proc = self.proc, None
        try:
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except (OSError, subprocess.SubprocessError):
                        pass
                except (OSError, subprocess.SubprocessError):
                    pass
        finally:
            if self.conf_path:
                shutil.rmtree(self.conf_path, ignore_errors=True)
                self.conf_path = None

    def node_id(self):
        """The chain sink's node id, for set-param. None until it appears."""
        return node_id(self.NODE_NAME)

    def set_controls(self, controls):
        """Live parameter changes: {'c_low:Ratio (1:n)': 4.0, ...}.

        Silently no-ops when the chain is down — a slider moved while the
        sink is off should not raise, it should just have nothing to do.
        """
        nid = self.node_id()
        if nid is None:
            return False
        params = []
        for k, v in controls.items():
            params += [json.dumps(k), str(float(v))]
        body = "{ params = [ %s ] }" % " ".join(params)
        try:
            r = subprocess.run(["pw-cli", "set-param", nid, "Props", body],
                               capture_output=True, text=True, timeout=5)
            # returncode checked: an earlier version returned True whenever
            # pw-cli merely ran, which reported success for writes that never
            # landed — the exact failure mode the audio test had to unmask
            return r.returncode == 0
        except Exception:
            return False


class BusSourceChain(Chain):
    """Own one independent passive Mix A or Mix B source process."""

    def __init__(self, bus):
        super().__init__()
        self.bus = _validate_bus(bus)
        self.NODE_NAME = BUS_SOURCE_NAMES[bus]
        self.CONF_PREFIX = self.NODE_NAME + "-"
        self.FRAGMENT = self.NODE_NAME + ".conf"
        self._configuration = None

    def start(self, capture_target=None):
        configuration = build_bus_source_conf(self.bus, capture_target)
        if self.running and configuration == self._configuration:
            return True
        started = self._launch(configuration, configured=True)
        if started:
            self._configuration = configuration
        return started

    def node_id(self):
        """Return only the public Audio/Source node, never its capture side."""
        try:
            output = subprocess.run(
                ["pw-cli", "ls", "Node"], capture_output=True,
                text=True, timeout=5).stdout
        except Exception:
            return None
        node_id = None
        expected = 'node.name = "%s"' % self.NODE_NAME
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("id ") and "," in stripped:
                node_id = stripped.split()[1].rstrip(",")
            elif stripped == expected and node_id is not None:
                return node_id
        return None


class BusSourceManager:
    """Reconcile two separately owned bus sources without coupled failure."""

    START_TIMEOUT_S = 5.0

    def __init__(self, chains=None):
        self.chains = chains or {
            bus: BusSourceChain(bus) for bus in BUS_SOURCE_KEYS
        }
        if set(self.chains) != set(BUS_SOURCE_KEYS):
            raise ValueError("bus source manager needs mixa and mixb chains")
        self.statuses = {bus: "unavailable" for bus in BUS_SOURCE_KEYS}
        self._started_at = {bus: None for bus in BUS_SOURCE_KEYS}

    def reconcile(self, capture_target, now=None):
        """Start, observe, and independently classify both virtual sources."""
        now = time.monotonic() if now is None else float(now)
        if not capture_target:
            self.stop()
            return dict(self.statuses)

        for bus in BUS_SOURCE_KEYS:
            chain = self.chains[bus]
            if not chain.running:
                if not chain.start(capture_target):
                    self.statuses[bus] = "failed"
                    self._started_at[bus] = None
                    continue
                self._started_at[bus] = now

            if chain.node_id() is not None:
                self.statuses[bus] = "ready"
                self._started_at[bus] = None
                continue

            started_at = self._started_at[bus]
            if started_at is None:
                self._started_at[bus] = now
                started_at = now
            if now - started_at >= self.START_TIMEOUT_S:
                chain.stop()
                self.statuses[bus] = "failed"
                self._started_at[bus] = None
            else:
                self.statuses[bus] = "starting"
        return dict(self.statuses)

    def stop(self):
        for bus in BUS_SOURCE_KEYS:
            self.chains[bus].stop()
            self.statuses[bus] = "unavailable"
            self._started_at[bus] = None


def set_default_input(node_name):
    """Make an existing PipeWire source the default for new recording.
    `wpctl set-default` picks sink or source from the node itself."""
    return set_default_output(node_name)


def _present_nodes():
    """Every PipeWire node name present now, from one listing."""
    try:
        out = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True,
                             text=True, timeout=5).stdout
    except Exception:
        return set()
    names = set()
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("node.name = "):
            names.add(line.split("=", 1)[1].strip().strip('"'))
    return names


class InsertChain(Chain):
    """Owns the input insert: one child process with the processing and its
    return. The processed channels are fixed per process, so changing which
    channels have Multiband restarts it with the current settings; control
    moves in between are live."""

    NODE_NAME = INSERT_PROCESS_NAME
    CONF_PREFIX = "io24-insert-"
    FRAGMENT = "io24-insert.conf"
    START_TIMEOUT_S = 3.0
    READY_NODES = (INSERT_PROCESS_NAME, INSERT_SOURCE_NAME, INSERT_RETURN_NAME)

    def __init__(self):
        super().__init__()
        self.channels = ()
        self._configuration = None

    def start(self, states, capture_target=None, playback_target=None,
              with_comp=None):
        """Run the insert for exactly these channels. True once all three of
        its nodes are present; anything short of that stops it again."""
        configuration = build_insert_conf(
            states, capture_target, playback_target, with_comp=with_comp)
        channels = tuple(sorted(states))
        if self.running and configuration == self._configuration:
            return True
        self.last_error = None
        if not self._launch(configuration, configured=True):
            self.channels = ()
            self.last_error = "PipeWire process could not start"
            return False
        self._configuration = configuration
        deadline = time.monotonic() + self.START_TIMEOUT_S
        while self.running:
            if set(self.READY_NODES) <= _present_nodes():
                self.channels = channels
                return True
            if time.monotonic() >= deadline:
                self.last_error = "the io24 Input Multiband nodes did not appear"
                break
            time.sleep(0.05)
        if self.last_error is None:
            self.last_error = "PipeWire process exited before its nodes appeared"
        self.stop()
        return False

    def stop(self):
        super().stop()
        self.channels = ()
        self._configuration = None

    def set_channel_controls(self, channel, controls):
        """Live moves for one channel's graph, keyed as for Chain."""
        if channel not in self.channels:
            return False
        prefix = insert_prefix(channel)
        return self.set_controls(
            {prefix + key: value for key, value in controls.items()})


if __name__ == "__main__":
    import sys
    print("sc4:", sc4_available() or "not installed (sudo apt install swh-plugins)")
    print("pipewire:", pipewire_available())
    print("io24 sink:", find_io24_sink() or "not present")
    if "--run" in sys.argv:
        import time
        c = Chain()
        c.start(with_comp=sc4_available() is not None)
        time.sleep(2)
        print("node id:", c.node_id())
        print("running:", c.running)
        c.stop()
        print("stopped")
