"""Host-side multiband compressor for the io24's monitor path.

The device cannot do this: the firmware capability sweep in PROTOCOL.md is a
clean, measured negative — no `multiband`, `crossover` or `fft` vocabulary
exists anywhere in it. So this is not a device feature and never pretends to
be one. It is a PipeWire filter-chain running on the computer, presented as a
sink called "io24 Multiband": point an application (or the system default) at
that sink and its audio passes through a 4-band compressor on its way to the
interface. This module also owns two distinct passive capture-bus sources;
those paths never route themselves to playback or pretend to be device DSP.

Topology, all standard pieces:

    in -> [LR4 low  ] -> sc4 -> \\
       -> [LR4 mid  ] -> sc4 ->  mixer -> out (the io24's sink)
       -> [LR4 high ] -> sc4 -> /

* The crossover is Linkwitz-Riley 4th order, built from PipeWire's builtin
  biquads (two cascaded Butterworth 2nd-order sections per leg — that IS an
  LR4). LR4 legs sum flat, which is the whole point of using them.
* The per-band compressor is `sc4` from swh-plugins — the standard LADSPA
  stereo compressor. PipeWire 1.6's filter-chain hosts LADSPA and builtins
  only (no LV2), and sc4 is the canonical choice it can host.
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
PAN_SNAPSHOT_VERSION = 2
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


def default_pan_snapshot():
    """Return neutral Host-only Mix A/B balance state."""
    return {
        "version": PAN_SNAPSHOT_VERSION,
        "balances": {bus: 0.5 for bus in BUS_SOURCE_KEYS},
    }


def validate_pan_snapshot(state):
    """Strictly validate current Host-only Mix A/B balance state."""
    if not isinstance(state, dict) or set(state) != {"version", "balances"}:
        raise ValueError("pan state fields must be balances, version")
    if state["version"] != PAN_SNAPSHOT_VERSION:
        raise ValueError("pan snapshot version must be 2")
    raw = state["balances"]
    if not isinstance(raw, dict) or set(raw) != set(BUS_SOURCE_KEYS):
        raise ValueError("pan balances must contain mixa and mixb")
    return {
        "version": PAN_SNAPSHOT_VERSION,
        "balances": {
            bus: _finite_number(raw[bus], "%s balance" % bus, 0.0, 1.0)
            for bus in BUS_SOURCE_KEYS
        },
    }


def normalise_pan_snapshot(state):
    """Return current bus balance state plus explicit migration notices."""
    if isinstance(state, dict) and state.get("version") == 1:
        if set(state) != {"version", "enabled", "positions"}:
            raise ValueError(
                "legacy pan fields must be enabled, positions, version")
        if not isinstance(state["enabled"], bool):
            raise ValueError("legacy pan enabled must be Boolean")
        positions = state["positions"]
        if not isinstance(positions, list) or len(positions) != 2:
            raise ValueError("legacy pan positions must contain two values")
        for value in positions:
            _finite_number(value, "legacy pan position", 0.0, 1.0)
        return default_pan_snapshot(), [
            "legacy input pan was not applied; Mix A/B balances centered",
        ]
    return validate_pan_snapshot(state), []


def balance_coefficients(position):
    """Stereo balance gains: center is unity and no channel crosses sides."""
    position = _finite_number(position, "balance position", 0.0, 1.0)
    if position <= 0.5:
        return 1.0, math.sin(math.pi * position)
    return math.sin(math.pi * (1.0 - position)), 1.0


def balance_controls(position):
    """Live controls for one stereo bus-source balance stage."""
    left, right = balance_coefficients(position)
    return {"balance_l:Mult": left, "balance_r:Mult": right}


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


def _bq(name, label, freq):
    return {"type": "builtin", "name": name, "label": label,
            "control": {"Freq": float(freq)}}


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

    # LR4 crossover tree: each 2x cascade of same-frequency Butterworth 2nd
    band_tails = []
    legs = [
        [("bq_lowpass", f0)] * 2,                              # low
        [("bq_highpass", f0)] * 2 + [("bq_lowpass", f1)] * 2,  # low-mid
        [("bq_highpass", f1)] * 2 + [("bq_lowpass", f2)] * 2,  # high-mid
        [("bq_highpass", f2)] * 2,                             # high
    ]
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


def build_bus_source_graph(bus, balance):
    """Select one exact capture pair and expose it through stereo balance."""
    bus = _validate_bus(bus)
    left, right = balance_coefficients(balance)
    nodes = [
        {"type": "builtin", "name": "src%d" % index, "label": "copy"}
        for index in range(len(CAPTURE_POSITIONS))
    ]
    nodes.extend((_lin("balance_l", left), _lin("balance_r", right)))
    left_index, right_index = BUS_CAPTURE_PAIRS[bus]
    return {
        "nodes": nodes,
        "links": [
            {"output": "src%d:Out" % left_index,
             "input": "balance_l:In"},
            {"output": "src%d:Out" % right_index,
             "input": "balance_r:In"},
        ],
        "inputs": ["src%d:In" % index
                   for index in range(len(CAPTURE_POSITIONS))],
        "outputs": ["balance_l:Out", "balance_r:Out"],
    }


def build_bus_source_conf(bus, capture_target, balance):
    """PipeWire config for one passive Mix A or Mix B virtual source."""
    bus = _validate_bus(bus)
    if not capture_target:
        raise ValueError("bus source needs a capture target")
    name = BUS_SOURCE_NAMES[bus]
    description = BUS_SOURCE_DESCRIPTIONS[bus]
    args = {
        "node.description": description,
        "media.name": description,
        "filter.graph": build_bus_source_graph(bus, balance),
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


def _find_io24_node(direction):
    """Find a PipeWire ALSA input/output node for the connected io24."""
    token = "alsa_%s" % direction
    try:
        out = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True,
                             text=True, timeout=5).stdout
    except Exception:
        return None
    blocks = ("\nid " + out).split("\nid ")
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


class Chain:
    """Owns the child pipewire process hosting the sink."""

    NODE_NAME = SINK_NAME
    CONF_PREFIX = "io24-mbc-"
    FRAGMENT = "io24-mbc.conf"

    def __init__(self):
        self.proc = None
        self.conf_path = None

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, target=None, with_comp=None, state=None):
        configured = target is not None or with_comp is not None or state is not None
        # Validate and render before creating any private filesystem state.
        # Invalid saved settings must fail closed without leaving a directory.
        configuration = build_conf(
            target=target, with_comp=with_comp, state=state)
        return self._launch(configuration, configured)

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
        try:
            out = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True,
                                 text=True, timeout=5).stdout
        except Exception:
            return None
        nid = None
        for line in out.splitlines():
            ls = line.strip()
            if ls.startswith("id ") and "," in ls:
                nid = ls.split()[1].rstrip(",")
            if self.NODE_NAME in ls and nid is not None:
                return nid
        return None

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

    def start(self, capture_target=None, balance=0.5):
        configuration = build_bus_source_conf(
            self.bus, capture_target, balance)
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

    def reconcile(self, capture_target, balances, now=None):
        """Start, observe, and independently classify both virtual sources."""
        state = validate_pan_snapshot({
            "version": PAN_SNAPSHOT_VERSION,
            "balances": balances,
        })
        now = time.monotonic() if now is None else float(now)
        if not capture_target:
            self.stop()
            return dict(self.statuses)

        for bus in BUS_SOURCE_KEYS:
            chain = self.chains[bus]
            if not chain.running:
                if not chain.start(capture_target, state["balances"][bus]):
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

    def set_balance(self, bus, position):
        bus = _validate_bus(bus)
        if self.statuses[bus] != "ready":
            return False
        chain = self.chains[bus]
        if chain.set_controls(balance_controls(position)):
            return True
        chain.stop()
        self.statuses[bus] = "failed"
        self._started_at[bus] = None
        return False

    def stop(self):
        for bus in BUS_SOURCE_KEYS:
            self.chains[bus].stop()
            self.statuses[bus] = "unavailable"
            self._started_at[bus] = None


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
