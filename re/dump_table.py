#!/usr/bin/env python3
"""
Dump and decode the parameter descriptor tables found in dspusbdevice.dll.
Records appear to be 104 (0x68) bytes containing C++ std::string fields (with
small-string optimisation, so short names are stored INLINE) plus integer IDs.
"""
import struct, sys, re

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
def va2off(va):
    rva = va-imgbase
    for n,sva,vs,raw,rs in secs:
        if sva <= rva < sva+max(vs,rs):
            o = raw+(rva-sva)
            if o < len(data): return o
    return None
def rd_cstr(off, maxlen=64):
    e = data.find(b"\0", off, off+maxlen)
    if e < 0: return None
    try: return data[off:e].decode("ascii")
    except: return None

def read_stdstring(off):
    """MSVC std::string: [ptr|inline buf 16][size 8][cap 8] = 32 bytes.
    If cap < 16 the text is inline at `off`, else pointer at `off`."""
    size = struct.unpack_from("<Q", data, off+16)[0]
    cap  = struct.unpack_from("<Q", data, off+24)[0]
    if cap < 16 and size <= 15:
        raw = data[off:off+size]
        try: return raw.decode("ascii"), size, cap
        except: return None, size, cap
    ptr = struct.unpack_from("<Q", data, off)[0]
    o = va2off(ptr)
    if o is None: return None, size, cap
    raw = data[o:o+min(size,120)]
    try: return raw.decode("ascii"), size, cap
    except: return None, size, cap

def dump_region(start_va, nrec=24, stride=0x68):
    off0 = va2off(start_va)
    print("\n=== region VA 0x%x (file 0x%x) stride=%d ===" % (start_va, off0, stride))
    for i in range(nrec):
        o = off0 + i*stride
        if o+stride > len(data): break
        chunk = data[o:o+stride]
        # try to interpret leading std::strings
        s1 = read_stdstring(o)
        s2 = read_stdstring(o+32)
        ints = struct.unpack_from("<8I", data, o+64)
        print("  [%2d] +0x%04x  s1=%-22r s2=%-22r ints=%s" % (
            i, i*stride, s1[0], s2[0], [hex(x) for x in ints]))

# regions discovered by find_table.py
for va in (0x1800ecbe0, 0x1800eaf18, 0x1800e9c60):
    dump_region(va, nrec=16)
