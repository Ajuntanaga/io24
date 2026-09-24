# re/ — reverse-engineering inputs

This private research tree includes material recovered or transcribed from
PreSonus software. It is not covered by the repository's GPL, is not included in
the Python wheel, and needs an explicit redistribution decision before any
public source release:

* `param_consumers.txt` — Ghidra decompiler output for 20 functions of
  `dspusbdevice.dll`. The parameter tables and route strings are unreadable
  without the code that consumes them.
* `uc_factory_presets.json` — 41 factory Fat Channel preset records lifted
  verbatim from the Universal Control installer payload.
* `uc_component_model/dsp_fx_params.xml` and
  `uc_component_model/dspusb_component_model.xml` — component-model XML
  extracted from `studiolivepanel.dll`.
* `uc_component_model/fatchannelxt_eq_contract.xml` and
  `uc_component_model/fatchannelxt_alternate_eq_contract.xml` — bounded
  transcriptions of embedded component contracts.

The default public-source boundary excludes these files. The runtime works
without them; the factory-preset browser reports unavailable until a user
regenerates its optional data from a local Universal Control installer. See
the top-level README and `PUBLICATION.md`.


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
