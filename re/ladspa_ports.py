#!/usr/bin/env python3
"""Read a LADSPA plugin's exact label, ports and ranges straight from its ABI.

PipeWire's filter-chain addresses control ports by their exact plugin-declared
names, and `analyseplugin` is not installed here. Guessing those names produces
a chain that loads and silently does nothing, so read them from the descriptor
the plugin itself exports.

    python3 re/ladspa_ports.py lcr_delay_1436 ringmod_1188 ...
"""

import ctypes
import sys
from pathlib import Path

LADSPA_DIRS = ("/usr/lib/ladspa", "/usr/lib/x86_64-linux-gnu/ladspa",
               "/usr/local/lib/ladspa")

PORT_INPUT = 0x1
PORT_OUTPUT = 0x2
PORT_CONTROL = 0x4
PORT_AUDIO = 0x8

HINT_BOUNDED_BELOW = 0x1
HINT_BOUNDED_ABOVE = 0x2
HINT_TOGGLED = 0x4
HINT_SAMPLE_RATE = 0x8
HINT_LOGARITHMIC = 0x10
HINT_INTEGER = 0x20


class PortRangeHint(ctypes.Structure):
    _fields_ = [("HintDescriptor", ctypes.c_int),
                ("LowerBound", ctypes.c_float),
                ("UpperBound", ctypes.c_float)]


class Descriptor(ctypes.Structure):
    _fields_ = [
        ("UniqueID", ctypes.c_ulong),
        ("Label", ctypes.c_char_p),
        ("Properties", ctypes.c_int),
        ("Name", ctypes.c_char_p),
        ("Maker", ctypes.c_char_p),
        ("Copyright", ctypes.c_char_p),
        ("PortCount", ctypes.c_ulong),
        ("PortDescriptors", ctypes.POINTER(ctypes.c_int)),
        ("PortNames", ctypes.POINTER(ctypes.c_char_p)),
        ("PortRangeHints", ctypes.POINTER(PortRangeHint)),
        ("ImplementationData", ctypes.c_void_p),
        # The remaining members are function pointers this tool never calls.
    ]


def library_path(name):
    """Resolve a bare plugin name, with or without its .so suffix."""
    candidate = name if name.endswith(".so") else name + ".so"
    if "/" in name:
        return Path(name)
    for directory in LADSPA_DIRS:
        path = Path(directory) / candidate
        if path.is_file():
            return path
    raise SystemExit("no LADSPA library named %s in %s"
                     % (candidate, ", ".join(LADSPA_DIRS)))


def _kind(flags):
    parts = []
    parts.append("audio" if flags & PORT_AUDIO else "control")
    parts.append("in" if flags & PORT_INPUT else "out")
    return " ".join(parts)


def _range(hint):
    bits = hint.HintDescriptor
    pieces = []
    if bits & HINT_TOGGLED:
        pieces.append("toggle")
    if bits & HINT_INTEGER:
        pieces.append("int")
    if bits & HINT_LOGARITHMIC:
        pieces.append("log")
    if bits & HINT_SAMPLE_RATE:
        pieces.append("xrate")
    low = "%.4g" % hint.LowerBound if bits & HINT_BOUNDED_BELOW else "-inf"
    high = "%.4g" % hint.UpperBound if bits & HINT_BOUNDED_ABOVE else "+inf"
    return "%s..%s%s" % (low, high,
                         "  [%s]" % ", ".join(pieces) if pieces else "")


def describe(name):
    """Every plugin in one library, as plain dictionaries."""
    path = library_path(name)
    library = ctypes.CDLL(str(path))
    library.ladspa_descriptor.restype = ctypes.POINTER(Descriptor)
    library.ladspa_descriptor.argtypes = [ctypes.c_ulong]
    plugins = []
    index = 0
    while True:
        pointer = library.ladspa_descriptor(index)
        if not pointer:
            break
        descriptor = pointer.contents
        ports = []
        for port in range(descriptor.PortCount):
            ports.append({
                "name": descriptor.PortNames[port].decode("utf-8", "replace"),
                "kind": _kind(descriptor.PortDescriptors[port]),
                "range": _range(descriptor.PortRangeHints[port]),
            })
        plugins.append({
            "library": path.name,
            "unique_id": int(descriptor.UniqueID),
            "label": descriptor.Label.decode("utf-8", "replace"),
            "name": descriptor.Name.decode("utf-8", "replace"),
            "ports": ports,
        })
        index += 1
    return plugins


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    for name in argv:
        for plugin in describe(name):
            print("%s  id=%d  label=%s" % (plugin["library"],
                                           plugin["unique_id"],
                                           plugin["label"]))
            print("  %s" % plugin["name"])
            for port in plugin["ports"]:
                print("    %-13s %-24s %s"
                      % (port["kind"], port["name"], port["range"]))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
