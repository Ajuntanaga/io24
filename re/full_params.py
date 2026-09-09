#!/usr/bin/env python3
"""
Walk the 104-byte parameter descriptor records in dspusbdevice.dll and emit the
complete native parameter dictionary for the Revelator io24 (Jackson).

Record (0x68 bytes):
  +0x00 u32 kind (1=int,2=enum,3=float,4=string)
  +0x04 u32 id
  +0x08 char name[24] inline
  +0x2c f32 max   +0x30 f32 default   +0x34 f32 step   +0x38 u32 flags
  +0x40.. pointers (display names etc)
"""
import struct, re, json, collections

PATH = "uc/hwaccess/dspusbdevice.dll"
data = open(PATH, "rb").read()
pe = struct.unpack_from("<I", data, 0x3c)[0]; coff = pe+4
nsec = struct.unpack_from("<H", data, coff+2)[0]
optsz = struct.unpack_from("<H", data, coff+16)[0]; opt = coff+20
imgbase = struct.unpack_from("<Q", data, opt+24)[0]
secs = []
for i in range(nsec):
    b = opt+optsz+i*40
    nm = data[b:b+8].rstrip(b"\0").decode('latin1')
    vs, va, rs, raw = struct.unpack_from("<IIII", data, b+8)
    secs.append((nm, va, vs, raw, rs))
def va2off(va):
    r = va-imgbase
    for n,sva,vs,raw,rs in secs:
        if sva <= r < sva+max(vs,rs):
            o = raw+(r-sva)
            return o if 0 <= o < len(data) else None
    return None
def off2va(off):
    for n,sva,vs,raw,rs in secs:
        if raw <= off < raw+rs: return imgbase+sva+(off-raw)
    return None
def cstr(o, mx=48):
    if o is None: return None
    e = data.find(b"\0", o, o+mx)
    if e < 0: return None
    try: return data[o:e].decode('ascii')
    except: return None

STRIDE = 0x68
NAME_RE = re.compile(rb"^[a-z][a-z0-9_.]{1,22}\0")
KIND = {1:"int",2:"enum",3:"float",4:"string"}

def parse(off):
    kind, pid = struct.unpack_from("<II", data, off)
    if kind not in KIND or not (0 < pid <= 4096): return None
    m = NAME_RE.match(data[off+8:off+8+24])
    if not m: return None
    name = m.group()[:-1].decode('ascii')
    mx, dflt, step = struct.unpack_from("<fff", data, off+0x2c)
    flags, = struct.unpack_from("<I", data, off+0x38)
    disp = None
    for p in (0x40,0x48,0x50,0x58):
        ptr, = struct.unpack_from("<Q", data, off+p)
        s = cstr(va2off(ptr)) if imgbase <= ptr < imgbase+0x600000 else None
        if s and 1 < len(s) < 40 and s[0].isupper():
            disp = s; break
    return dict(va=off2va(off), kind=KIND[kind], id=pid, name=name,
                max=round(mx,6), default=round(dflt,6), step=round(step,6),
                flags=flags, display=disp)

# find all seed records, then walk backwards/forwards in 0x68 steps to get whole tables
seeds = []
for name, sva, vs, raw, rs in secs:
    if name not in (".rdata",".data","_RDATA"): continue
    for off in range(raw, raw+rs-STRIDE, 4):
        if parse(off): seeds.append(off)

tables = []
seen = set()
for s in sorted(seeds):
    if s in seen: continue
    start = s
    while parse(start-STRIDE): start -= STRIDE
    recs = []
    o = start
    while True:
        r = parse(o)
        if not r: break
        recs.append(r); seen.add(o); o += STRIDE
    if len(recs) >= 2: tables.append(recs)

print("parameter tables found: %d\n" % len(tables))
total = 0
allrecs = []
for t in sorted(tables, key=lambda t: -len(t)):
    total += len(t)
    allrecs.extend(t)
    print("=== table @0x%x : %d params ===" % (t[0]['va'], len(t)))
    for r in t:
        print("   %-6s id=%-4d %-18s max=%-10g def=%-10g step=%-8g flags=0x%-4x %s" % (
            r['kind'], r['id'], r['name'], r['max'], r['default'], r['step'], r['flags'],
            r['display'] or ''))
    print()
print("TOTAL parameters: %d" % total)
json.dump(allrecs, open("io24_params.json","w"), indent=1)
print("written -> io24_params.json")
