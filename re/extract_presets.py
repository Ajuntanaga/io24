#!/usr/bin/env python3
"""Extract Universal Control's factory Fat Channel presets.

They are embedded in the installer in a small tagged binary format:

    {                     begin dict
    }                     end dict
    i <len> <chars>       a length-prefixed name (used for every key)
    S i <len> <chars>     a string value
    d <4 bytes>           a float, BIG-endian
    i <byte>              an integer value (in value position)

Whether `i` means "name" or "integer" is decided by position: inside a dict the
parser alternates key, value, and a key is always a length-prefixed name.

Usage:  python3 re/extract_presets.py <nsis_payload.bin> [out.json]
"""
import json
import struct
import sys


class P:
    def __init__(self, b, i=0):
        self.b, self.i = b, i

    def name(self):
        if self.b[self.i:self.i + 1] != b"i":
            raise ValueError("expected a name at 0x%x" % self.i)
        n = self.b[self.i + 1]
        s = self.b[self.i + 2:self.i + 2 + n]
        self.i += 2 + n
        return s.decode("latin1")

    def value(self):
        t = self.b[self.i:self.i + 1]
        if t == b"{":
            self.i += 1
            return self.dict()
        if t == b"S":
            self.i += 1
            return self.name()
        if t == b"d":
            v = struct.unpack(">f", self.b[self.i + 1:self.i + 5])[0]
            self.i += 5
            return round(v, 6)
        if t == b"i":
            v = self.b[self.i + 1]
            self.i += 2
            return v - 256 if v > 127 else v
        raise ValueError("bad tag %r at 0x%x" % (t, self.i))

    def dict(self):
        out = {}
        while True:
            c = self.b[self.i:self.i + 1]
            if c == b"}":
                self.i += 1
                return out
            if c == b"" or len(out) > 400:
                raise ValueError("unterminated dict")
            k = self.name()
            out[k] = self.value()


def extract(data):
    presets, i = [], 0
    key = b"{i\x0bpreset_name"
    while True:
        i = data.find(key, i)
        if i < 0:
            break
        try:
            p = P(data, i + 1)
            d = p.dict()
            if d.get("preset_name"):
                d["_offset"] = i
                presets.append(d)
        except Exception:
            pass
        i += 1
    return presets


if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    ps = extract(data)
    seen, uniq = set(), []
    for p in ps:
        k = (p["preset_name"], json.dumps(p, sort_keys=True)[:400])
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    print("found %d preset records (%d unique)" % (len(ps), len(uniq)))
    for p in uniq:
        print("   %-22s modules: %s" % (
            p["preset_name"],
            ", ".join(k for k in p if not k.startswith(("_", "preset_", "icon")))))
    if len(sys.argv) > 2:
        json.dump(uniq, open(sys.argv[2], "w"), indent=1)
        print("wrote %s" % sys.argv[2])
