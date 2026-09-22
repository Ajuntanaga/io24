#!/usr/bin/env python3
"""Safe Host implementation of the io24 Voice FX Delay at 96 kHz.

Firmware 1.28 doubles two private Delay histories when its ``Setu`` record
changes from 48 to 96 kHz.  If either resize allocation fails, the traced
failure branch leaves a zero history length that the audio loop subsequently
uses as a divisor; whether that allocation actually fails is unproved.  The
Linux Host therefore never selects the hardware Delay at 96 kHz.  It runs
this small LADSPA processor in the existing per-input PipeWire insert instead.

The public state is deliberately the same four controls as UC's ``VocalEcho``
component: On, Time, Feedback and WetDry.  No function here opens USB.
"""

import hashlib
import math
import os
from pathlib import Path
import shutil
import subprocess
import sysconfig
import tempfile


PLUGIN_LABEL = "io24_voicefx_delay"
SOURCE_NAME = "io24_voicefx_delay.c"
PLUGIN_UNIQUE_ID = 422026
CONTROL_PORTS = ("On", "Time (s)", "Feedback", "WetDry")
MAX_TIME_S = 0.25
HOST_FEATURE_VERSION = 1


class PluginBuildError(RuntimeError):
    pass


def _number(value, name, low, high):
    if isinstance(value, bool):
        raise ValueError("Delay %s must be numeric" % name)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Delay %s must be numeric" % name) from error
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError("Delay %s must be in [%s, %s]" %
                         (name, low, high))
    return number


def default_state(enabled=True):
    return {
        "on": bool(enabled),
        "time_s": 0.125,
        "feedback": 0.5,
        "mix": 0.5,
    }


def validate_state(state):
    if not isinstance(state, dict) or set(state) != set(default_state()):
        raise ValueError("Delay state must contain on, time_s, feedback and mix")
    if not isinstance(state["on"], bool):
        raise ValueError("Delay on must be boolean")
    return {
        "on": state["on"],
        "time_s": _number(state["time_s"], "time", 0.0001, MAX_TIME_S),
        "feedback": _number(state["feedback"], "feedback", 0.0, 1.0),
        "mix": _number(state["mix"], "WetDry", 0.0, 1.0),
    }


def validate_host_feature(feature):
    """Validate the durable Host-only owner and exact Delay controls."""
    if not isinstance(feature, dict) or set(feature) != {
            "version", "target", "state"}:
        raise ValueError(
            "Host Delay must contain version, target and state")
    version = feature["version"]
    if type(version) is not int or version != HOST_FEATURE_VERSION:
        raise ValueError("unknown Host Delay version")
    target = feature["target"]
    if type(target) is not int or target not in (1, 2):
        raise ValueError("Host Delay target must be Input 1 or Input 2")
    return {
        "version": HOST_FEATURE_VERSION,
        "target": int(target),
        "state": validate_state(feature["state"]),
    }


def plugin_controls(state):
    state = validate_state(state)
    return {
        "On": 1.0 if state["on"] else 0.0,
        "Time (s)": state["time_s"],
        "Feedback": state["feedback"],
        "WetDry": state["mix"],
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
    """Build the self-contained delay once into a content-addressed cache."""
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
        raise PluginBuildError("cannot create Delay cache: %s" % error) from error
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
            raise PluginBuildError("Delay plugin build failed: %s" % detail)
        os.chmod(temporary, 0o755)
        os.replace(temporary, target)
    except (OSError, subprocess.SubprocessError) as error:
        raise PluginBuildError("Delay plugin build failed: %s" % error) from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return target


def plugin_reference(cache_dir=None):
    build_plugin(cache_dir)
    return plugin_name()
