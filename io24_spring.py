#!/usr/bin/env python3
"""Host-side spring reverb for the Revelator io24.

This is deliberately separate from block 202, the unit's shared digital
reverb.  It takes physical Inputs 1 and 2 from the io24 capture stream,
produces a wet-only stereo spring model in PipeWire, and returns it through
the best stereo playback pair exposed by the active profile.  A dedicated
USB pair is reserved for Main only while enabled; a two/three-channel profile
uses the normal Main playback pair without rewriting its mixer routes.

No function in this module opens USB or talks to the device by itself.  The
GTK Host supplies an already-open mixer object only when the user enables or
disables the return route.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sysconfig
import tempfile
import time

import io24_mbc


PLUGIN_LABEL = "io24_spring"
SOURCE_NAME = "io24_spring.c"
PLUGIN_UNIQUE_ID = 422025
CONTROL_PORTS = (
    "Input 1 gain",
    "Input 2 gain",
    "Dwell",
    "Tone",
    "Drip",
    "Width",
    "Pre-delay (s)",
    "Output gain (dB)",
)

# Version 2 moves Spring return level into the wet processor. Version 1 used
# the device mixer fader for the fixed USB 5-6 return.
VERSION = 2
RETURN_SOURCE = "return/ch3"
RETURN_BUSES = ("main", "mixa", "mixb")
DEFAULT_RETURN_DB = -12.0
NODE_NAME = "io24-spring-return"
NODE_DESCRIPTION = "io24 Host Spring Reverb"


class PluginBuildError(RuntimeError):
    pass


def default_state(enabled=False):
    return {
        "version": VERSION,
        "enabled": bool(enabled),
        "input1_db": -6.0,
        "input2_db": -6.0,
        "dwell": 0.64,
        "tone": 0.55,
        "drip": 0.42,
        "width": 0.82,
        "predelay_s": 0.008,
        "output_db": DEFAULT_RETURN_DB,
        "routing": None,
    }


def _number(value, name, low, high):
    if isinstance(value, bool):
        raise ValueError("spring %s must be numeric" % name)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("spring %s must be numeric" % name) from error
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError("spring %s must be in [%s, %s]" %
                         (name, low, high))
    return number


def _validate_bus_routing(routing, buses):
    if not isinstance(routing, dict) or set(routing) != set(buses):
        raise ValueError("spring routing buses are invalid")
    result = {}
    for bus in buses:
        prior = routing[bus]
        if not isinstance(prior, dict) or set(prior) != {
                "assigned", "known", "level_db"}:
            raise ValueError("spring %s routing state is invalid" % bus)
        if not isinstance(prior["assigned"], bool) or \
                not isinstance(prior["known"], bool):
            raise ValueError("spring %s routing flags must be boolean" % bus)
        level = prior["level_db"]
        if prior["known"] and level is not None:
            level = _number(level, "%s routing level" % bus, -60.0, 10.0)
        elif not prior["known"] and level is not None:
            raise ValueError("spring unknown routing level must be null")
        result[bus] = {
            "assigned": prior["assigned"],
            "known": prior["known"],
            "level_db": level,
        }
    return result


def _validate_routing(routing):
    if routing is None:
        return None
    if not isinstance(routing, dict) or set(routing) != {
            "source", "exclusive", "buses"}:
        raise ValueError("spring routing must hold source, exclusive and buses")
    source = routing["source"]
    if source not in ("return/ch1", "return/ch2", "return/ch3"):
        raise ValueError("spring routing has an unknown playback source")
    if not isinstance(routing["exclusive"], bool):
        raise ValueError("spring routing exclusive flag must be boolean")
    buses = RETURN_BUSES if routing["exclusive"] else ()
    return {
        "source": source,
        "exclusive": routing["exclusive"],
        "buses": _validate_bus_routing(routing["buses"], buses),
    }


def _migrate_v1_state(state):
    expected = {
        "version", "enabled", "input1_db", "input2_db", "dwell", "tone",
        "drip", "width", "predelay_s", "routing",
    }
    if set(state) != expected:
        raise ValueError("spring version 1 fields are invalid")
    routing = state["routing"]
    if routing is not None:
        routing = {
            "source": RETURN_SOURCE,
            "exclusive": True,
            "buses": _validate_bus_routing(routing, RETURN_BUSES),
        }
    return dict(state, version=VERSION, output_db=DEFAULT_RETURN_DB,
                routing=routing)


def validate_state(state):
    if not isinstance(state, dict):
        raise ValueError("spring state must be an object")
    if state.get("version") == 1:
        state = _migrate_v1_state(state)
    expected = set(default_state())
    if set(state) != expected:
        raise ValueError("spring fields must be %s" %
                         ", ".join(sorted(expected)))
    if state["version"] != VERSION:
        raise ValueError("spring version must be %d" % VERSION)
    if not isinstance(state["enabled"], bool):
        raise ValueError("spring enabled must be boolean")
    return {
        "version": VERSION,
        "enabled": state["enabled"],
        "input1_db": _number(state["input1_db"], "input1_db", -60.0, 0.0),
        "input2_db": _number(state["input2_db"], "input2_db", -60.0, 0.0),
        "dwell": _number(state["dwell"], "dwell", 0.0, 1.0),
        "tone": _number(state["tone"], "tone", 0.0, 1.0),
        "drip": _number(state["drip"], "drip", 0.0, 1.0),
        "width": _number(state["width"], "width", 0.0, 1.0),
        "predelay_s": _number(
            state["predelay_s"], "predelay_s", 0.0, 0.1),
        "output_db": _number(
            state["output_db"], "output_db", -60.0, 10.0),
        "routing": _validate_routing(state["routing"]),
    }


def plugin_controls(state):
    state = validate_state(state)
    return {
        "Input 1 gain": 10.0 ** (state["input1_db"] / 20.0),
        "Input 2 gain": 10.0 ** (state["input2_db"] / 20.0),
        "Dwell": state["dwell"],
        "Tone": state["tone"],
        "Drip": state["drip"],
        "Width": state["width"],
        "Pre-delay (s)": state["predelay_s"],
        "Output gain (dB)": state["output_db"],
    }


def playback_lane(playback_positions):
    """Choose a stereo return pair without demanding a six-channel profile."""
    positions = tuple(playback_positions or ())
    if len(positions) >= 6:
        pair, source, exclusive = positions[4:6], "return/ch3", True
        label = "USB 5-6"
    elif len(positions) >= 4:
        pair, source, exclusive = positions[2:4], "return/ch2", True
        label = "USB 3-4"
    elif len(positions) >= 2:
        pair, source, exclusive = positions[:2], "return/ch1", False
        label = "USB 1-2"
    else:
        raise ValueError("spring needs a stereo playback pair")
    return {
        "positions": tuple(pair),
        "source": source,
        "exclusive": exclusive,
        "label": label,
    }


def source_path():
    candidates = (
        Path(__file__).resolve().with_name(SOURCE_NAME),
        Path(sysconfig.get_path("data")) / "share" / "io24" / SOURCE_NAME,
    )
    for path in candidates:
        if path.is_file():
            return path
    raise PluginBuildError(
        "missing %s (checked source tree and installed share/io24)" %
        SOURCE_NAME)


def default_cache_dir():
    root = os.environ.get("XDG_CACHE_HOME")
    if root:
        return Path(root) / "io24" / "ladspa"
    return Path.home() / ".cache" / "io24" / "ladspa"


def plugin_name():
    digest = hashlib.sha256(source_path().read_bytes()).hexdigest()[:16]
    return PLUGIN_LABEL + "-" + digest


def build_plugin(cache_dir=None, compiler=None):
    source = source_path()
    directory = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    target = directory / (plugin_name() + ".so")
    if target.is_file():
        return target
    cc = shutil.which(compiler or "cc")
    if cc is None:
        raise PluginBuildError("no C compiler found (install build-essential)")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise PluginBuildError("cannot create spring cache: %s" % error) from error
    descriptor, temporary = tempfile.mkstemp(
        prefix="." + PLUGIN_LABEL + "-", suffix=".so", dir=directory)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        result = subprocess.run(
            [cc, "-std=c11", "-O2", "-fPIC", "-shared", "-Wall",
             "-Wextra", "-Werror", "-Wl,-z,defs", str(source), "-lm",
             "-o", str(temporary)],
            capture_output=True, text=True, timeout=60, check=False)
        if result.returncode:
            detail = (result.stderr or result.stdout or "compiler failed").strip()
            raise PluginBuildError("spring plugin build failed: %s" % detail)
        os.chmod(temporary, 0o755)
        os.replace(temporary, target)
    except (OSError, subprocess.SubprocessError) as error:
        raise PluginBuildError("spring plugin build failed: %s" % error) from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return target


def plugin_reference(cache_dir=None):
    build_plugin(cache_dir)
    return plugin_name()


def build_graph(state, positions=io24_mbc.CAPTURE_POSITIONS, plugin=None):
    state = validate_state(state)
    if len(positions) < 2:
        raise ValueError("spring needs physical Inputs 1 and 2")
    nodes = [
        {"type": "builtin", "name": "src%d" % index, "label": "copy"}
        for index in range(len(positions))
    ]
    nodes.append({
        "type": "ladspa",
        "name": "tank",
        "plugin": plugin or plugin_reference(),
        "label": PLUGIN_LABEL,
        "control": plugin_controls(state),
    })
    return {
        "nodes": nodes,
        "links": [
            {"output": "src0:Out", "input": "tank:Input 1"},
            {"output": "src1:Out", "input": "tank:Input 2"},
        ],
        "inputs": ["src%d:In" % index for index in range(len(positions))],
        "outputs": ["tank:Output L", "tank:Output R"],
    }


def build_conf(state, capture_target, playback_target,
               capture_positions=io24_mbc.CAPTURE_POSITIONS,
               playback_positions=io24_mbc.CAPTURE_POSITIONS, plugin=None):
    if not capture_target or not playback_target:
        raise ValueError("spring needs the io24 capture and playback nodes")
    lane = playback_lane(playback_positions)
    args = {
        "node.description": NODE_DESCRIPTION,
        "media.name": NODE_DESCRIPTION,
        "filter.graph": build_graph(state, capture_positions, plugin),
        "capture.props": {
            "node.name": "io24-spring-capture",
            "media.class": "Stream/Input/Audio",
            "target.object": capture_target,
            "node.dont-fallback": True,
            "stream.dont-remix": True,
            "audio.channels": len(capture_positions),
            "audio.position": list(capture_positions),
        },
        "playback.props": {
            "node.name": NODE_NAME,
            "node.description": NODE_DESCRIPTION,
            "media.class": "Stream/Output/Audio",
            "target.object": playback_target,
            "node.dont-fallback": True,
            "stream.dont-remix": True,
            "channelmix.upmix": False,
            "audio.channels": 2,
            "audio.position": list(lane["positions"]),
        },
    }
    return ("context.properties = { log.level = 2 }\n"
            "context.modules = [\n"
            "  { name = libpipewire-module-filter-chain\n"
            "    args = %s\n"
            "  }\n"
            "]\n" % json.dumps(args, indent=2))


def route_main_only(dev, routing=None, lane=None):
    """Reserve a dedicated return, or leave shared Main playback untouched."""
    lane = playback_lane(("0", "1", "2", "3", "4", "5")) \
        if lane is None else dict(lane)
    source = lane.get("source")
    exclusive = lane.get("exclusive")
    if source not in ("return/ch1", "return/ch2", "return/ch3") or \
            not isinstance(exclusive, bool):
        raise ValueError("spring playback lane is invalid")
    prior = _validate_routing(routing)
    if prior is not None and (prior["source"] != source or
                              prior["exclusive"] != exclusive):
        restore_routes(dev, prior)
        prior = None
    if not exclusive:
        # USB 1-2 is ordinary desktop playback. The filter stream is mixed into
        # that PipeWire sink, so borrowing or rewriting its device routes would
        # also move every other application using the pair.
        return {"source": source, "exclusive": False, "buses": {}}
    if prior is None:
        buses = {}
        for bus in RETURN_BUSES:
            known = bool(dev.has_send_level(source, bus))
            buses[bus] = {
                "assigned": bool(dev.send_assigned(source, bus)),
                "known": known,
                "level_db": dev.send_db(source, bus) if known else None,
            }
        prior = {"source": source, "exclusive": True, "buses": buses}
    # The wet processor owns output_db. Keep a dedicated hardware return at
    # unity so one visible control has one meaning and can be restored exactly.
    dev.set_send_db(source, "main", 0.0)
    dev.set_send_assigned(source, "main", True)
    for bus in ("mixa", "mixb"):
        dev.set_send_assigned(source, bus, False)
    return _validate_routing(prior)


def restore_routes(dev, routing):
    routing = _validate_routing(routing)
    if routing is None:
        return None
    source = routing["source"]
    for bus, prior in routing["buses"].items():
        if prior["known"]:
            dev.set_send_db(source, bus, prior["level_db"])
        dev.set_send_assigned(source, bus, prior["assigned"])
    return None


class SpringChain(io24_mbc.Chain):
    NODE_NAME = NODE_NAME
    CONF_PREFIX = "io24-spring-"
    FRAGMENT = "io24-spring.conf"

    def __init__(self):
        super().__init__()
        self._configuration = None
        self._lane = None

    @property
    def return_lane(self):
        return dict(self._lane) if self._lane is not None else None

    def ladspa_paths(self):
        return (io24_mbc.io24_uc_comp.default_cache_dir(), default_cache_dir())

    def start(self, state, capture_target, playback_target,
              capture_positions=None, playback_positions=None):
        state = validate_state(state)
        capture_positions = capture_positions or \
            io24_mbc.capture_positions(capture_target)
        playback_positions = playback_positions or \
            io24_mbc.capture_positions(playback_target)
        lane = playback_lane(playback_positions)
        configuration = build_conf(
            state, capture_target, playback_target,
            capture_positions=capture_positions,
            playback_positions=playback_positions,
            plugin=plugin_reference())
        if self.running and configuration == self._configuration:
            self._lane = lane
            return True
        self.last_error = None
        if not self._launch(configuration, configured=True):
            self.last_error = "PipeWire process could not start"
            return False
        deadline = time.monotonic() + self.START_TIMEOUT_S
        while self.running:
            if self.node_id() is not None:
                self._configuration = configuration
                self._lane = lane
                return True
            if time.monotonic() >= deadline:
                self.last_error = "spring return node did not appear"
                break
            time.sleep(0.05)
        if self.last_error is None:
            self.last_error = "spring process exited before its return appeared"
        self.stop()
        return False

    def stop(self):
        super().stop()
        self._configuration = None
        self._lane = None

    def set_state(self, state):
        return self.set_controls({
            "tank:%s" % name: value
            for name, value in plugin_controls(state).items()
        })


def available():
    if not io24_mbc.pipewire_available():
        return "needs PipeWire (pipewire and pw-cli)"
    try:
        plugin_reference()
    except PluginBuildError as error:
        return str(error)
    return None
