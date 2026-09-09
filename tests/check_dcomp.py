#!/usr/bin/env python3
"""Does this Universal Control build need DirectComposition?

UC 5.x cannot start under Wine because `cclgui.dll` statically imports
`dcomp.dll` and calls `DCompositionCreateDevice`, which Ubuntu's Wine 10.0
implements as a stub returning E_NOTIMPL (PROTOCOL §13w, §13x). An older UC
that predates the DirectComposition renderer would run.

Rather than guess which version that is, check. Point this at any UC
installation (or at an extracted `cclgui.dll`) and it reports whether the
build needs DComp:

    python3 tests/check_dcomp.py "~/Documents/Universal Control"
    python3 tests/check_dcomp.py /path/to/cclgui.dll

A build that does NOT import dcomp.dll is a candidate for the Wine capture.
"""

import os
import struct
import sys


def imports(path):
    """DLL names in a PE's import table."""
    d = open(path, "rb").read()
    if d[:2] != b"MZ":
        return None
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    if d[pe:pe + 4] != b"PE\0\0":
        return None
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    magic = struct.unpack_from("<H", d, pe + 24)[0]
    # data directory: entry 0 is the export table, entry 1 (at +8) is the
    # import table. Reading +0 silently yields exports and finds nothing.
    dd = pe + 24 + (112 if magic == 0x20B else 96) + 8
    secs = []
    so = pe + 24 + optsz
    for i in range(nsec):
        o = so + i * 40
        vsz, va, rsz, ro = struct.unpack_from("<IIII", d, o + 8)
        secs.append((va, vsz, ro, rsz))

    def v2f(r):
        for va, vsz, ro, rsz in secs:
            if va <= r < va + vsz:
                return ro + (r - va)
        return None

    imp_rva = struct.unpack_from("<I", d, dd)[0]
    if not imp_rva:
        return []
    f = v2f(imp_rva)
    out = []
    while f is not None:
        try:
            ol, tds, fc, nrva, ft = struct.unpack_from("<IIIII", d, f)
        except struct.error:
            break
        if nrva == 0:
            break
        nf = v2f(nrva)
        if nf is None:
            break
        e = d.find(b"\0", nf)
        out.append(d[nf:e].decode(errors="replace"))
        f += 20
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = os.path.expanduser(sys.argv[1])
    files = []
    if os.path.isdir(target):
        for root, _, names in os.walk(target):
            for n in names:
                if n.lower().endswith((".dll", ".exe")):
                    files.append(os.path.join(root, n))
    else:
        files = [target]

    needs = []
    checked = 0
    for f in files:
        try:
            imp = imports(f)
        except Exception:
            continue
        if imp is None:
            continue
        checked += 1
        if any(i.lower() == "dcomp.dll" for i in imp):
            needs.append(f)

    print("checked %d PE files under %s\n" % (checked, target))
    if needs:
        print("NEEDS DirectComposition — will NOT start under Wine 10.0:")
        for f in needs:
            print("   %s" % os.path.relpath(f, target if os.path.isdir(target) else "."))
        print("\nThis build is not usable for the capture. Try an older UC.")
        return 1
    print("No dcomp.dll import found.")
    print("This build is a CANDIDATE — worth trying under Wine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
