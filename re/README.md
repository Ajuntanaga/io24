# re/ — reverse-engineering inputs

**Two files here are PreSonus's, not this project's**, and are not covered by the
repository's GPL:

* `param_consumers.txt` — Ghidra decompiler output for 20 functions of
  `dspusbdevice.dll`. The parameter tables and route strings are unreadable
  without the code that consumes them.
* `uc_factory_presets.json` — 41 factory Fat Channel preset records lifted
  verbatim from the Universal Control installer payload.

Delete both if you are repackaging; everything except the factory-preset browser
works without them. See the licence section of the top-level README.


`dspusbdevice.dll` is not committed here (it is PreSonus's binary). Recover it
from the Universal Control installer with Python alone — no 7-Zip needed:

```python
import zlib
raw = open("Fender_Universal_Control_v5_0_0_110112.exe","rb").read()
payload = zlib.decompressobj(-15).decompress(raw[0x1601c:])   # deflate, not LZMA
open("dspusbdevice.dll","wb").write(payload[0x922fdc7:0x922fdc7+0x4be600])
```

0x1601c is just past the NSIS first header (find the `NullsoftInst` signature).
The DLL has imagebase 0x180000000, and the io24's Cortex-M firmware is embedded
in its `.rdata` at file 0x216030..0x323a70, load VA 0x60020000.
