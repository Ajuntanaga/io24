#!/usr/bin/env python3
"""UC-derived Host compressor mapping and local LADSPA build.

The io24 exposes one common ``cpxt`` representation after Universal Control
has translated the distinct Standard, Tube and FET public controls.  This
module reuses those byte-exact builders as the parameter compiler for the
computer-side multiband processor.  No USB or device operation occurs here.
"""

import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sysconfig
import tempfile

import io24_dsp


PLUGIN_LABEL = "io24_uc_comp"
SOURCE_NAME = "io24_uc_comp.c"
CONTROL_PORTS = (
    "Biquad b0",
    "Biquad -a1",
    "Biquad b1",
    "Biquad -a2",
    "Biquad b2",
    "Attack time (s)",
    "Release time (s)",
    "Slope",
    "Knee width (dB)",
    "Threshold level (dB)",
    "Makeup gain (linear)",
    "Key listen",
)

MODEL_BUILDERS = {
    "standard": io24_dsp.cpxt_comp,
    "tube": io24_dsp.cpxt_tube,
    "fet": io24_dsp.cpxt_fet,
}


class PluginBuildError(RuntimeError):
    pass


def model_controls(model, parameters, keyfilter_hz=0.0, keylisten=False,
                   sample_rate=48000.0):
    """Compile one model's public controls into the exact common cpxt tuple."""
    if model not in MODEL_BUILDERS:
        raise ValueError("compressor model must be standard, tube or fet")
    if not isinstance(parameters, dict):
        raise ValueError("compressor model parameters must be an object")
    blob = MODEL_BUILDERS[model](
        index=0, on=True, keyfilter_hz=keyfilter_hz,
        keylisten=keylisten, fs=sample_rate, **parameters)
    values = struct.unpack_from("<11f", blob, 0x0c)
    _on, listen = struct.unpack_from("<II", blob, 0x38)
    controls = dict(zip(CONTROL_PORTS[:-1], values))
    controls[CONTROL_PORTS[-1]] = float(listen)
    return controls


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
    """Content-addressed library name, without PipeWire's appended suffix."""
    digest = hashlib.sha256(source_path().read_bytes()).hexdigest()[:16]
    return PLUGIN_LABEL + "-" + digest


def build_plugin(cache_dir=None, compiler=None):
    """Build the tiny self-contained LADSPA plugin once, atomically.

    ``cache_dir`` is injectable so the full compiler/ABI test stays in a
    temporary directory.  The running Host uses the user's cache and never
    needs sudo or a system-wide LADSPA install.
    """
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
        raise PluginBuildError("cannot create compressor cache: %s" % error) from error

    descriptor, temporary = tempfile.mkstemp(
        prefix="." + PLUGIN_LABEL + "-", suffix=".so", dir=directory)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        result = subprocess.run(
            [cc, "-std=c11", "-O2", "-fPIC", "-shared",
             "-Wall", "-Wextra", "-Werror", "-Wl,-z,defs",
             str(source), "-lm", "-o", str(temporary)],
            capture_output=True, text=True, timeout=60, check=False)
        if result.returncode:
            detail = (result.stderr or result.stdout or "compiler failed").strip()
            raise PluginBuildError("compressor plugin build failed: %s" % detail)
        os.chmod(temporary, 0o755)
        os.replace(temporary, target)
    except (OSError, subprocess.SubprocessError) as error:
        raise PluginBuildError("compressor plugin build failed: %s" % error) from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return target


def plugin_reference(cache_dir=None):
    """PipeWire LADSPA basename after ensuring the library is built.

    PipeWire resolves LADSPA plugins by basename through ``LADSPA_PATH``.  It
    does not accept an absolute path here, even when the trailing ``.so`` is
    omitted.
    """
    build_plugin(cache_dir)
    return plugin_name()
