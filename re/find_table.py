#!/usr/bin/env python3
"""
Hunt for a static parameter table in dspusbdevice.dll.

Hypothesis: the DLL translates native device parameter IDs <-> UCNET route names,
so there is likely a static table of {char* name; uint32 id; ...} entries. Find it
by locating route-like strings, then scanning data sections for arrays of pointers
to them and inferring the record stride + neighbouring integer fields.
"""
import struct, sys, re, collections

PATH = sys.argv[1] if len(sys.argv) > 1 else "uc/hwaccess/dspusbdevice.dll"
data = open(PATH, "rb").read()

# ---- PE parse ----
pe = struct.unpack_from("<I", data, 0x3c)[0]
assert data[pe:pe+4] == b"PE\0\0"
coff = pe + 4
nsec = struct.unpack_from("<H", data, coff+2)[0]
optsz = struct.unpack_from("<H", data, coff+16)[0]
opt = coff + 20
magic = struct.unpack_from("<H", data, opt)[0]
imgbase = struct.unpack_from("<Q", data, opt+24)[0] if magic == 0x20b else struct.unpack_from("<I", data, opt+28)[0]
secs = []
for i in range(nsec):
    b = opt + optsz + i*40
    name = data[b:b+8].rstrip(b"\0").decode("latin1")
    vsize, va, rawsz, raw = struct.unpack_from("<IIII", data, b+8)
    secs.append((name, va, vsize, raw, rawsz))

def va2off(va):
    rva = va - imgbase
    for n, sva, vs, raw, rs in secs:
        if sva <= rva < sva + max(vs, rs):
            o = raw + (rva - sva)
            return o if o < len(data) else None
    return None

def off2va(off):
    for n, sva, vs, raw, rs in secs:
        if raw <= off < raw + rs:
            return imgbase + sva + (off - raw)
    return None

def sec_of(off):
    for n, sva, vs, raw, rs in secs:
        if raw <= off < raw + rs:
            return n
    return "?"

print("imagebase=0x%x  sections=%s" % (imgbase, [(s[0], hex(s[1])) for s in secs]))

# ---- collect ASCII strings ----
STR_RE = re.compile(rb"[\x20-\x7e]{3,120}\x00")
strings = {}   # va -> text
for m in STR_RE.finditer(data):
    off = m.start()
    va = off2va(off)
    if va:
        strings[va] = m.group()[:-1].decode("latin1")

# route-like: contains '/', or is a known parameter word
PARAM_WORDS = {"volume","mute","gain","pan","solo","link","phase","phantom","preset",
               "level","meter","comp","eq","gate","reverb","fx","mix","assign","enable",
               "bypass","threshold","ratio","attack","release","freq","q","boost","blend"}
def route_like(s):
    if len(s) < 3 or len(s) > 64: return False
    if "/" in s and re.fullmatch(r"[A-Za-z0-9_./%\-]+", s): return True
    return s.lower() in PARAM_WORDS

cand = {va: s for va, s in strings.items() if route_like(s)}
print("route-like strings: %d" % len(cand))
for va, s in sorted(cand.items())[:40]:
    print("   0x%x  %r" % (va, s))

# ---- scan data sections for pointers to those strings ----
ptr_hits = []   # (offset, va_pointed, text)
for name, sva, vs, raw, rs in secs:
    if name not in (".rdata", ".data", "_RDATA"): continue
    end = raw + rs
    off = raw
    while off + 8 <= end:
        v = struct.unpack_from("<Q", data, off)[0]
        if v in cand:
            ptr_hits.append((off, v, cand[v]))
        off += 8
print("\npointers to route-like strings found: %d" % len(ptr_hits))

# ---- infer tables: group hits by stride ----
ptr_hits.sort()
if ptr_hits:
    strides = collections.Counter()
    for a, b in zip(ptr_hits, ptr_hits[1:]):
        d = b[0] - a[0]
        if 0 < d <= 128:
            strides[d] += 1
    print("common strides between consecutive string-pointers: %s" % strides.most_common(6))

    # print runs
    runs = []
    cur = [ptr_hits[0]]
    for a, b in zip(ptr_hits, ptr_hits[1:]):
        if 0 < b[0]-a[0] <= 128 and (len(cur) < 2 or (b[0]-a[0]) == (cur[1][0]-cur[0][0])):
            cur.append(b)
        else:
            if len(cur) >= 3: runs.append(cur)
            cur = [b]
    if len(cur) >= 3: runs.append(cur)
    print("\ntables (>=3 entries, regular stride): %d" % len(runs))
    for r in runs[:12]:
        stride = r[1][0]-r[0][0]
        print("\n  TABLE @ file 0x%x (VA 0x%x) in %s : %d entries, stride %d" %
              (r[0][0], off2va(r[0][0]) or 0, sec_of(r[0][0]), len(r), stride))
        for off, va, text in r[:14]:
            extra = data[off+8:off+min(stride, 8+24)]
            ints = struct.unpack_from("<II", data, off+8) if stride >= 16 else ()
            print("     %-38r  trailing=%s %s" % (text, extra.hex(), ints))
