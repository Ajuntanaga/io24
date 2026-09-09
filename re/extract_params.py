#!/usr/bin/env python3
"""
Extract the native parameter descriptor records from dspusbdevice.dll.

Observed record shape in .rdata:  [u32 kind][u32 id][inline ASCII name ...]
e.g. (3,1,"size") (3,2,"mix") (3,3,"hp_freq") (3,4,"predelay")

Scan the data sections for that pattern and report every (kind,id,name) found,
grouped by kind — this is the native parameter-ID <-> name map.
"""
import struct, re, sys, collections

PATH = "uc/hwaccess/dspusbdevice.dll"
data = open(PATH, "rb").read()
pe = struct.unpack_from("<I", data, 0x3c)[0]; coff = pe+4
nsec = struct.unpack_from("<H", data, coff+2)[0]
optsz = struct.unpack_from("<H", data, coff+16)[0]; opt = coff+20
imgbase = struct.unpack_from("<Q", data, opt+24)[0]
secs = []
for i in range(nsec):
    b = opt+optsz+i*40
    name = data[b:b+8].rstrip(b"\0").decode("latin1")
    vsize, va, rawsz, raw = struct.unpack_from("<IIII", data, b+8)
    secs.append((name, va, vsize, raw, rawsz))
def off2va(off):
    for n,sva,vs,raw,rs in secs:
        if raw <= off < raw+rs: return imgbase+sva+(off-raw)
    return None

NAME_RE = re.compile(rb"^[a-z][a-z0-9_.]{1,23}\0")

records = []
for name, sva, vs, raw, rs in secs:
    if name not in (".rdata", ".data", "_RDATA"): continue
    off = raw
    end = raw+rs-40
    while off < end:
        kind, pid = struct.unpack_from("<II", data, off)
        # plausible: small kind, small id, followed immediately by a lowercase name
        if 0 < kind <= 32 and 0 < pid <= 4096:
            m = NAME_RE.match(data[off+8:off+8+26])
            if m:
                nm = m.group()[:-1].decode("ascii")
                records.append((off, off2va(off), kind, pid, nm))
        off += 4

print("records found: %d\n" % len(records))
bykind = collections.defaultdict(list)
for off, va, kind, pid, nm in records:
    bykind[kind].append((pid, nm, va))

for kind in sorted(bykind):
    rows = sorted(set(bykind[kind]))
    # only show groups that look like real tables (several sequential ids)
    ids = sorted({r[0] for r in rows})
    if len(rows) < 3: continue
    print("=== kind=%d : %d entries, ids %s..%s ===" % (kind, len(rows), ids[0], ids[-1]))
    for pid, nm, va in rows[:60]:
        print("    id=%-4d %-24s @0x%x" % (pid, nm, va))
    print()
