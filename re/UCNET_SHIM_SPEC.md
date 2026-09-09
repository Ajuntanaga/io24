# UCNET shim specification (generated, verified)

## UDP discovery
## 1. UDP discovery — the "DA" announce datagram

Sent to **127.0.0.1:47809**, once per second, one datagram per device.
The client (`BroadcastService.cs`) binds `0.0.0.0:47809` on Unix with `SO_REUSEADDR` and only
listens — it never sends. The shim therefore does **not** need to bind 47809 at all; it just
`sendto()`s. (Binding it would fight the client for the port.)

### Byte layout

```
off  size  field                       source of truth
0    2     "UC"                        ucnet.dll writer 0x18001a38f: mov word [buf], 0x4355
2    2     u16le 0x0100  (=256)        ucnet.dll: mov eax,0x100 / mov word [buf+2], ax
4    2     u16le TCP PORT of this server   <-- NOT a length. See note below.
6    2     "DA"                        record tag; 'DL'=leave, 'DQ'=query also exist
8    4     u32le device id             clients read only the low u16
12   20    address/flags block         NOT fully decoded — zeros are accepted
32   ..    NUL-terminated ASCII strings, in order:
             [0] "<model>/<firmwareWord>"
             [1] "AUD"                 ("DAW" = OBSRemoteAdapter, rejected by the client)
             [2] "<serial>"            must be non-empty
             [3] "<display name>"      optional; oddbear ignores it
```

**The offset-4 quirk is real and proven from the sender, not inferred.** In the TCP writer
(`ucnet.dll` 0x180009900) offset 4 gets the payload length; in the UDP writer (0x18001a350) the
same slot is filled from `[[obj+0x60]+0x30]` — the local TCP port — never a length. Any parser
that treats a UDP UCNET datagram as length-prefixed will be wrong.

### Client-side acceptance rules you must satisfy (`DeviceMetadata.TryParseDeviceMetadata`)

- magic must be exactly `55 43 00 01`; type must be `"DA"`.
- `segments[0].split('/')` must yield **exactly 2** parts and part 0 must start with `"Revelator"`.
- `segments[1]` must be exactly `"AUD"`.
- `segments[2]` (serial) must be non-empty.
- the firmware word is `ushort.Parse`d — it must be a **decimal integer ≤ 65535** or the client throws.
  It is BCD-ish nibbles: `value 0x0128 = 296` renders as **"1.28"**, which matches the io24's
  `bcdDevice 1.28`. (Cross-checks: 281→1.19, 289→1.21, 290→1.22, 343→1.57.)
- **Do not use serial `JM1C20474458`** — `BroadcastService.cs` hardcodes a `continue` for it.

### Worked io24 example (92 bytes, TCP port 50925, device id 107)

```
0000  55 43 00 01 ed c6 44 41 6b 00 00 00 00 00 00 00  |UC....DAk.......|
0010  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|
0020  52 65 76 65 6c 61 74 6f 72 20 49 4f 20 32 34 2f  |Revelator IO 24/|
0030  32 39 36 00 41 55 44 00 4c 49 4e 55 58 49 4f 32  |296.AUD.LINUXIO2|
0040  34 30 30 31 00 52 65 76 65 6c 61 74 6f 72 20 69  |4001.Revelator i|
0050  6f 32 34 20 28 4c 69 6e 75 78 29 00              |o24 (Linux).|
```

Verified: this parses to `{name: 'Revelator IO 24', serial: 'LINUXIO24001', firmware: '1.28',
device_id: 107, tcp_port: 50925}` through a line-for-line port of the C#.

### How the 12..32 block was scoped

The in-memory DA record (built at `ucnet.dll` 0x18000dc60) is 0x124 bytes:
`+0x00 u32 'DA' | +0x04 u32 0x124 size | +0x08 u32 id | +0x0c u32 0 | +0x10 20-byte addr/flags |
+0x24,+0x64,+0xa4,+0xe4 four 0x40-byte strings`. On the wire the 2-byte type and the id line up
with client offsets 6 and 8, and the four strings land at 32 — which pins the intervening 20 bytes
to record `+0x10..+0x24`. The receiver reads `[rec+0x10]` as a flags dword
("Server flags changed via UDP discovery %s : 0x%08x"). I did not decode the remaining 16 bytes.
Zeros work because no client in scope reads them.


## TCP flow
## 2. The TCP conversation

Server listens on the port advertised at datagram offset 4 (an ephemeral port is fine).
Bind loopback only.

### Framing — every TCP message

```
off  size  field
0    2     "UC"
2    2     u16le 0x0100
4    2     u16le length = total - 6      (counts message type + from + to + payload)
6    2     message type, 2 ASCII chars
8    2     u16le from
10   2     u16le to
12   ..    payload
```

Confirmed on both sides of `ucnet.dll`: writer 0x180009900 does
`mov word[buf],0x4355 / mov eax,0x100 / mov word[buf+2],ax / mov word[buf+4],bx / add ebx,6`;
reader 0x180009370 byte-swaps and checks `cmp dword[rdi+0x1f0], 0x5543`, then
`cmp word[rdi+0x1f4], 0x100`, then **`cmp word[rbx], 0x4000 / ja reject`**.

> **Hard limit: a message body must be ≤ 0x4000 (16384) bytes** or the real service drops the link.
> Keep to it so a shim-tested client behaves the same against real hardware.

`from`/`to`: the client always sends `from=104`, `to=<deviceId from the DA>`. The client ignores
both fields on inbound messages, so the shim can simply mirror them (`from=deviceId, to=104`).

### Ordering

```
client ──TCP connect──▶ server
client ──▶ UM   (one write also carrying the JM below — MessageWriter concatenates them)
client ──▶ JM {"id":"Subscribe", ...}
server ──▶ JM {"id":"SubscriptionReply", ...}          (content ignored by the client)
server ──▶ JM {"id":"Synchronize", ...}                 (the whole state tree — see §3)
server ──▶ PL  per preset-list route                    (optional)
client ──▶ KA                                           every 1 s, forever
client ──▶ PV / PS                                      on every user write
server ──▶ PV / PS                                      echo + unsolicited state change
```

**Two non-obvious obligations:**

1. **Echo every accepted PV/PS back.** `RawService.SetValue` sends and does **not** update its own
   `_values` cache (the local-update code is commented out in the shipped source). Without a server
   echo the plugin's own UI never reflects its own write. Same for `SetString`.
2. **Emit each UCNET message in exactly one `write()`.** `CommunicationService.Listener` does a bare
   `networkStream.Read(...)` and hands the result to `PackageHelper.ChunksByIndicator`, which splits
   on the `"UC\0\x01"` magic and **never reassembles**. A message split across two reads is silently
   lost and the JSON parse of the partial chunk throws (caught and logged). Corollary: keep the
   Synchronize JSON small — mine is 2903 bytes, safely inside one loopback read.

`KA` needs no reply: the client has no watchdog and logs a warning for any type it does not know,
so replying to KA only produces log noise. The *server* is the side that times clients out.

### Message payloads (offset 12 onward)

```
UM   u16le monitorPort                       client's UDP port for meters (see §6)
JM   i32le jsonLen | jsonLen bytes ASCII     uncompressed JSON
ZM   i32le jsonLen | zlib-deflate stream     same JSON, compressed
KA   (empty)
PV   route ASCII | 00 00 00 | f32le value
PS   route ASCII | 00 00 00 | value ASCII | 00
PL   route ASCII | 00 00 00 | f32le selected | "a\nb\nc" ASCII | 00
```

Note the route is **not** NUL-terminated in its own right — the three zero bytes serve as both
terminator and padding. `SetFloatValue` slices `data[12..^7]`, so a PV payload is exactly
`len(route) + 7`.

**Prefer JM over ZM for Synchronize.** JSON is printable ASCII and therefore cannot contain a
`00` byte, so it can never accidentally contain the `"UC\0\x01"` magic and confuse the client's
chunker. A zlib payload can (probability ~5e-7 for a 2 KB blob, but it is a real nondeterministic
failure mode). The client handles JM and ZM identically.

### Worked examples

UM welcome, client→server, monitor port 51000, deviceId 107:
```
0000  55 43 00 01 08 00 55 4d 68 00 6b 00 38 c7        |UC....UMh.k.8.|
      └magic────┘ └len┘ └"UM"┘ └104┘└107┘ └51000┘
```

PV write, client→server, `line/ch1/preampgain = 0.5`:
```
0000  55 43 00 01 20 00 50 56 68 00 6b 00 6c 69 6e 65  |UC.. .PVh.k.line|
0010  2f 63 68 31 2f 70 72 65 61 6d 70 67 61 69 6e 00  |/ch1/preampgain.|
0020  00 00 00 00 00 3f                                |.....?|
                  └f32 0.5┘
```

JM SubscriptionReply, server→client:
```
0000  55 43 00 01 57 00 4a 4d 6b 00 68 00 4d 00 00 00  |UC..W.JMk.h.M...|
0010  7b 22 69 64 22 3a 22 53 75 62 73 63 72 69 70 74  |{"id":"Subscript|
0020  69 6f 6e 52 65 70 6c 79 22 2c 22 63 6c 69 65 6e  |ionReply","clien|
...
```


## Synchronize JSON
## 3. The "Synchronize" JSON tree

The shape is dictated entirely by `RawService.Synchronize` + `Traverse`/`TraverseObject`.

### Mandatory top-level keys

```json
{
  "id": "Synchronize",
  "children": { ... },
  "shared": { "strings": [ [ "" ] ] }
}
```

All three are read unconditionally. `shared.strings` is dereferenced as
`.EnumerateArray().First().EnumerateArray()`, so it must be an **array of arrays with at least one
inner array**, and every inner element must be a JSON string. If any of the three is missing the
client throws, the exception is swallowed by `Listener`'s catch, the `Synchronized` event never
fires, and the plugin sits with an empty state and no error. (The `shared` value is then assigned
to a local variable and never used — it is dead code, but it must parse.)

### Path construction

`Traverse` walks `children` with an accumulating path:

| JSON value kind | effect |
|---|---|
| number | `_values[path] = float` |
| string | `_string[path] = s` |
| array  | `_strings[path] = [non-empty strings]` |
| object | recurse per property |
| **true / false** | **falls through to `default:` and is silently DROPPED** |

Property names `children`, `values`, `ranges`, `strings` recurse **without extending the path**;
every other property name appends `/name`. Leading `/` is never produced.

> **Emit `0.0` / `1.0` for booleans, never `true` / `false`.** JSON booleans are ignored outright,
> so a `"mute": false` leaves the route absent from the client's cache.

### Canonical shape

```json
{
  "id": "Synchronize",
  "children": {
    "global": {
      "values": { "phonesVolume": 0.5, "mainOutVolume": 0.5, "monitorBlend": 0.5,
                  "phonesSrc": 0.0, "phonesMute": 0.0, "outputDelay": 0.0,
                  "outputDelayBus": 0.0, "presetButtonMode": 1.0,
                  "aux1_mirror_main": 0.0, "aux2_mirror_main": 0.0,
                  "auxMuteMode": 0.0, "enableChannelAssign": 1.0 }
    },
    "line": {
      "children": {
        "ch1": {
          "values": { "preampgain": 0.0, "48v": 0.0, "hardwareMute": 0.0, "mute": 0.0,
                      "volume": 0.75, "solo": 0.0, "lr": 1.0, "assign_aux1": 1.0,
                      "assign_aux2": 1.0, "aux1": 0.75, "aux2": 0.75, "FXA": 0.0,
                      "link": 0.0, "pan": 0.5, "processingChannel": 0.5,
                      "activePresetSlotIndex": 0.0, "autogain": 0.0, "autogainmode": 0.0 },
          "strings": { "chnum": "1", "username": "Mic 1" },
          "children": {
            "filter": { "values": { "hpf": 0.0 } },
            "limit":  { "values": { "limiteron": 0.0, "threshold": 1.0 } },
            "opt":    { "values": { "swapcompeq": 0.0, "eqmodel": 0.0, "compmodel": 0.0 } }
          }
        },
        "ch2": { ... }
      }
    },
    "return":   { "children": { "ch1": {...}, "ch2": {...}, "ch3": {...} } },
    "fxreturn": { "children": { "ch1": {...} } },
    "aux":      { "children": { "ch1": {...}, "ch2": {...} } },
    "main":     { "children": { "ch1": {...} } },
    "fx":       { "children": { "ch1": { "children": { "reverb": { "values": {...} } } } } }
  },
  "shared": { "strings": [ [ "" ] ] }
}
```

`children.line.children.ch1.values.preampgain` → path `line/ch1/preampgain`. Verified by running
the tree through a port of `Traverse`: 131 value routes and 11 string routes populate correctly.

### Values are NORMALIZED 0..1

Every numeric route carries a normalized position, not the engineering value. Cross-checks from the
client itself: `DeviceRoutingBase.GetVolume` returns `round(v * 100)`; `Global.SetHeadphoneSource`
writes `0.0 / 0.5 / 1.0` for a `[0,2]` enum; `MonitorBlend` is documented "0.5 is balanced" for a
`[-1,1]` parameter. Denormalize with the descriptor min/max in §4 before writing native.

### Preset lists

`MicrophoneChannel.Presets` reads route `line/chN/presets/preset` as a **string array**, while
`Preset` reads the **same route** as a float index. The array does not arrive in Synchronize — it
comes over a `PL` message (`SetList` only accepts routes ending `/presets/preset`). We have no
preset files on Linux, so the honest behaviour is: publish the float route with value 0.0, send no
PL, and let `Presets` stay empty (`GetPresetName()` then returns null, which the client handles).


## Route table
## 4. Route → native operation

Wire message for every NATIVE row:
`SetP | 'Appl' | blockIndex 0 | blob{tag, size 0x14, index, paramId, value}`,
blob tag `'Para'` for f32 and `'Pari'` for i32. `v` is the normalized 0..1 UCNET value.

Descriptor min/max/kind below were re-extracted from `dspusbdevice.dll` in this session
(tables 0x1800e9660, 0x1800ea880, 0x1800ea330, 0x1800e9a80, 0x1800eb140, 0x1800eb060, 0x1800ea810)
and agree with the prior analysis.

### 4a. NATIVE — forwarded to the device (14 routes)

| Route | blob | wire id | index | encode | descriptor |
|---|---|---|---|---|---|
| `global/phonesVolume` | Para | 1 | 0 | **v** (pass-through) | float [-96,0] dB, taper exp, `'NPar'` wrapped |
| `global/mainOutVolume` | Para | 2 | 0 | **v** (pass-through) | float [-96,0] dB, taper exp, `'NPar'` wrapped |
| `global/monitorBlend` | Para | 10 | 0 | `2v-1` | float [-1,1] |
| `global/outputDelay` | Para | 14 | 0 | `0.5v` | float [0,0.5] s |
| `global/phonesSrc` | Pari | 11 | 0 | `round(2v)` | enum [0,2] = Main / Stream Mix A / Stream Mix B |
| `global/phonesMute` | Pari | 6 | 0 | `v>0.5` | bool |
| `global/presetButtonMode` | Pari | 17 | 0 | `round(2v)` | int [0,2] |
| `global/outputDelayBus` | Pari | 13 | 0 | `round(4v)` | enum [0,4] = None / USB 1/2 / 3/4 / 5/6 / 7/8 |
| `line/chN/preampgain` | Para | 3 | N-1 | `60v` | float [0,60] dB, taper **linear** |
| `line/chN/48v` | Pari | 0 | N-1 | `v>0.5` | bool |
| `line/chN/hardwareMute` | Pari | 7 | N-1 | `v>0.5` | bool — **the device input mute** |
| `line/chN/link` | Pari | 9 | N-1 | `v>0.5` | bool (single param; firmware ignores index) |
| `line/chN/processingChannel` | Pari | 12 | N-1 | `round(2v-1)` | int [-1,1]; firmware clamps to 0..1 |
| `line/chN/activePresetSlotIndex` | Pari | 16 | N-1 | `round(3v)` | int [0,3] |

Two encoding notes: the host truncates float→int with `cvttss2si`; **round instead**, because
`trunc(2 × 0.4999)` = 0 where the user meant 1. And `phonesSrc` is write-only — the firmware stores
it directly at `device+0x1100` (handler 0x6004e6b4) and it never appears in the `JaSt` dump, so it
cannot be read back.

### 4b. Read-back — only these six survive a round trip

`JaSt` (GetP / `'Appl'`) exposes slots 0–50. Usable for state refresh on connect:

| Route | JaSt slot | normalize |
|---|---|---|
| `global/phonesVolume` | 43 | as-is (already 0..1) |
| `global/mainOutVolume` | 44 | as-is |
| `global/monitorBlend` | 45 | `(x+1)/2` |
| `line/chN/preampgain` | 46 / 47 | `x/60` |
| `line/chN/48v` | 50 byte0 / byte1 | bool |
| `line/chN/activePresetSlotIndex` | 40 / 41 | `x/3` |

Everything else must be shadowed host-side.

### 4c. INERT — accept, keep shadow state, emit nothing

- `line/chN/autogain` → `'Pari'` 15 → firmware internal ids 21/22 — **no descriptor record** → silent no-op.
- `line/chN/autogainmode` → `'Pari'` 19 → internal id 25 — no descriptor → silent no-op.

Autogain is a **host feature**, not a device feature. To implement it for real, poll `JaSt` slots
4 (in1) and 6 (in2) and drive `'Para'` 3.

### 4d. BLOCKED — must never be forwarded (new finding, see §6)

- `line/chN/pan` — host binds **block 0**, wire 2
- `line/chN/dawpostdsp` — host binds **block 0**, wire 3

Block 0 resolves to the **device object itself** — the same object `'Appl'` addresses
(firmware 0x6005ceec: `cbz r3 → mov r3, r0`). On that object `'Para'` wire 2 is `mainVolume` and
wire 3 is `inputNGain`. Forwarding a pan write would therefore slam the main output volume.
Shadow these routes; never send them.

### 4e. MIXER — reachable, not implemented (largest gap)

Affects every `line|return|fxreturn /chN/ {volume, mute, solo, lr, assign_aux1, assign_aux2,
aux1, aux2, monitorBlend, FXA}` plus `main/ch1/mono` and `aux/chN/mono`.

Wire form (host side fully recovered):
```
SetP | block 100 (0x00000064) | blockIndex B | 'Para' size 0x14 | index 0 | paramId S | f32 gainDb
  B = 0 main, 1 Mix A (aux/ch1), 2 Mix B (aux/ch2)
  S = line/ch1=3 line/ch2=4 return/ch1..3=0,1,2 fxreturn/ch1=5
batch form: blob 'mprm', 0x1f0 bytes, 60 × {u32 paramId, f32 gainDb} at +0x0c, count at +0x1ec
```
5–7 UCNET routes collapse into that one float. See §6 for what is and is not known about it.

### 4f. SHADOW — no device binding at all

`global/{aux1_mirror_main, aux2_mirror_main, auxMuteMode, enableChannelAssign}`,
`main/ch1/hardwareMute` (read-only on output channels — oddbear's own comment is correct),
`*/chN/{chnum, name, username, preset_name}` (strings, PS transport),
`*/chN/{select, clip, linkmaster, stereopan, bypassDSP, dspAmount, presetHotKey*, presetSlotTitle*}`,
`line/chN/presets/*`, `line/chN/cache/*`, `/presets`, `diagnostics/*`.

Descriptors with `flags & 0x20` are skipped by the host's own push routine and confirmed in the
tables I dumped: per-channel `monitorBlend` (107, flags 0x0020), `clip` (108, 0x0028),
`presetHotKeyTitle` (152), `presetSlotTitle1..4` (153–156).

### 4g. DSP sub-blocks — coefficient blobs, not wire params

| Route | block | status |
|---|---|---|
| `line/chN/filter/hpf` | `'filt'` | **implementable** — `'Bqdf'` RBJ high-pass, log taper 24..1000 Hz (24 = bypass); maths in `io24.py` |
| `line/chN/limit/*` | `'lim '` | **implementable** — 0x18 blob, `invThreshold = 10^(-dB/20)` |
| `line/chN/opt/swapcompeq` | `'opt '` | **implementable** — `'Pari'` id 0, the only wire param on the chain |
| `line/chN/gate/*` | `'gate'` | partial — 0x48 blob laid out, unit conversions not derived |
| `line/chN/eq/*` | `'eq  '` | partial — `'Bqdf'` per band (band index at blob+0x0c), band maths not derived |
| `line/chN/comp/*` | `'comp'` | no — three interchangeable `'cpxt'` encoders selected by a GUID-keyed model enum |
| `line/chN/{opt/eqmodel, opt/compmodel, voicefx*}` | — | no — GUID-keyed plugin models |
| `fx/ch1/reverb/*` | `'vrvb'` | no — 0x38 blob = 11 f32 coefficients (builder 0x1800207f0), maths not recovered |

The chain resolver's accepted FourCC set is now exhaustively enumerated (see §6): exactly
`'opt '`, `'filt'`, `'gate'`, `'comp'`, `'eq  '`, `'lim '`, at container offsets
+0x000, +0x058, +0x204, +0x454, +0x6d4, +0xc40. `'IFac'` must never be sent over USB.

### 4h. The mute problem — a design decision the shim must make

`ChannelBase.Mute` — the single most-used control in any stream-deck plugin — binds to
`line/chN/mute`, which is a **mixer** route (host id 104, flags 0x000a, consumed only by the
mix-link builder). It has no device binding, so a faithful shim leaves every plugin's mute button
inert. The io24's only real input mute is `hardwareMute` (`'Pari'` 7).

The skeleton therefore aliases `line/chN/mute` → `'Pari'` 7 by default (`--no-mute-alias` to
disable), echoing **both** routes so the client cache stays coherent. This is a deliberate
semantic deviation and should be documented to users: the mixer mute is per-destination-bus,
the hardware mute kills the input on every bus at once.


## Python skeleton
Full runnable server at **`ucnet_shim.py`** (571 lines), validated by
**`the oddbear client test`** (290 lines).
Both are in the session scratchpad — copy them into the repo before it is cleaned up.

```
$ python3 ucnetshim.py --backend null -v &     # no hardware needed
$ python3 test_oddbear_client.py
[1] UDP discovery            PASS  DA parses as DeviceMetadata / model / firmware 1.28 / serial / port
[2] TCP session              PASS  JM sent, Synchronize parsed, 131 values + 11 strings populated
                             PASS  13 spot-checked routes present
[3] write echo               PASS  PV write is echoed back
[4] keepalive                PASS  session survives KA
[5] mixer degradation        PASS  accepted into shadow state, no USB traffic
[6] mute alias               PASS  reaches Pari 7 idx 1, both routes echoed
ALL CHECKS PASSED
```

The test harness is a line-for-line port of `PackageHelper`, `DeviceMetadata`, `MessageWriter` and
`RawService` from the C#, including the quirks (no reassembly across reads, booleans dropped by
`Traverse`, the `shared.strings[0]` dereference, the offset-4 port). It is the regression gate:
if a change breaks the client contract it fails there rather than in a plugin.

### Structure

```
frame(msg_type, src, dst, payload)     -> bytes      6-byte header + type/from/to + payload
class FrameReader                                   proper length-prefixed reassembly (inbound)
discovery_datagram(port, id, model, fwWord, serial, display) -> bytes
class Announcer                                     1 Hz sendto 127.0.0.1:47809
class Route                                         kind + blob op + wire id + index + encoder
build_routes() -> {route: Route}                    the whole §4 table as data
class NullBackend / Io24Backend                     swap in io24.py or a daemon client
class Shim
    synchronize_tree()                              builds the §3 JSON from the route table
    apply(route, value) -> disposition              the one place a write is classified
    on_message / on_json                            UM, JM, ZM, KA, PV, PS
    refresh_from_device()                           JaSt -> normalized, for the six readable routes
    serve(host, port)                               asyncio.start_server + announcer
```

### The three things that make it work with unmodified clients

```python
def _send(self, writer, data: bytes):
    # one message per write(): oddbear's reader does not reassemble
    writer.write(data)
```

```python
elif mtype == "PV":
    route = payload[:-7].decode("ascii", "replace")
    (value,) = struct.unpack_from("<f", payload, len(payload) - 4)
    how = self.apply(route, value)
    # echo: the client never updates its own cache on write
    self.send_value(writer, route, self.values.get(route, value))
```

```python
return {"id": "Synchronize", "children": tree, "shared": {"strings": [[""]]}}
# every leaf emitted as float() -- JSON booleans are dropped by Traverse
```

### Wiring to the real driver

`Io24Backend` calls `io24.Io24.set_param(wire, value, index=, as_int=)` directly, which means the
shim process holds the USB interface exclusively. If `io24d.py` is already running, write a third
backend that speaks its newline-delimited JSON socket instead — the `set_para`/`set_pari`/
`read_params` surface is all the shim needs:

```python
class DaemonBackend:
    def __init__(self, path="/run/user/1000/io24d.sock"): ...
    def set_para(self, wire, value, index): self._rpc({"cmd":"setp","tag":"Para","id":wire,
                                                       "index":index,"value":float(value)})
    def set_pari(self, wire, value, index): self._rpc({"cmd":"setp","tag":"Pari","id":wire,
                                                       "index":index,"value":int(value)})
    def read_params(self):                  return self._rpc({"cmd":"status"}).get("params")
```
`io24d.py` currently exposes a named-parameter API (`{"cmd":"set","param":"gain",...}`), not raw
wire ids — adding a raw `setp` command is the smallest change that keeps the shim's route table as
the single source of truth.

### Operational notes

- Bind loopback only. UCNET has no authentication whatsoever; anything that can reach the TCP port
  gets full control of the device.
- Do not bind UDP 47809 — the client binds it. Send only.
- `--enable-mixer` currently logs and drops rather than guessing; see §6 before changing that.
- The Synchronize frame is 2903 bytes against a 16384-byte protocol cap, leaving room to grow the
  tree ~5×. If it ever approaches ~8 KB, switch to ZM or reduce the tree — do not let it split.


## Unknowns
## 6. What is genuinely uncertain

Ordered by how much it costs the user.

### 6.1 Meters and gain reduction — protocol unknown, feature absent

The `UM` welcome carries a client UDP port (`_monitorService.Port`) and the real service presumably
streams level data to it. `MonitorService.cs` was not in the source set, so the datagram format is
**completely unknown**. The shim parses the port, logs it, and sends nothing. Any plugin feature
that draws meters or gain reduction will show nothing — it will not show wrong values.

This is the largest *undiscovered* area, as opposed to the largest *unimplemented* one. Note the
data itself is available on our side: `JaSt` slots 0–37 carry the meter block and `'Redu'` gives
per-stage gain reduction, so only the wire format is missing. A capture of the real service on
Windows would close it in one session.

### 6.2 The mixer — status materially better than previously believed, still not safe to ship

Two corrections to the prior analysis came out of this session:

**(a) The io24 firmware does route numeric block ids.** The non-`'Appl'` dispatcher is
**0x6005ce98**, not 0x6005cef0:

```
r1 = &{blockFourCC, blockIndex}, r2 = device base
  fourcc == 0     -> device object itself                       (0x6005ceec)
  fourcc == 100   -> dev + 0x3e28 + 0x74*blockIndex,  index 0..2 (0x6005cec0)  <-- THE MIXER
  fourcc == 201   -> dev + 0x11e0
  fourcc == 202   -> dev + 0x3a70
  fourcc == 203   -> dev + 0x3f84 + 0x4c*blockIndex,  index 0..2
  otherwise       -> 0x6005cef0 -> chain resolver 0x6006efe8, blockIndex <= 1 only
```

So block 100 with blockIndex 0/1/2 is a real, bounds-checked object — exactly matching the host's
main / Mix A / Mix B model. "Device-side handler unidentified" should be downgraded to "the object
is identified at `dev+0x3e28+0x74*i`; its accepted blob tags and param-id space are not". What that
object does with a `'Para'` blob is still unread.

While there I also enumerated the DSP chain resolver exhaustively — it derives four of its six
FourCCs arithmetically from two stored literals, which is why byte-searching missed `'comp'` and
`'eq  '`:

```
'gate' 0x67617465 -> +0x204     'eq  ' 0x65712020 -> +0x6d4     'filt' 0x66696c74 -> +0x058
'comp' 0x636f6d70 -> +0x454     'lim ' 0x6c696d20 -> +0xc40     'opt ' 0x6f707420 -> +0x000
```
Anything else returns NULL. This reproduces PROTOCOL.md §9a exactly and rules out any seventh block.

**(b) The mixer value is a dB float, not a linear gain.** From `0x1800570e0`:

```
if (source is muted / unassigned / not soloed)   return -145.0f      # the "off" sentinel
g  = (vol_dB < -144) ? 10^(-144/20) : powf(10, vol_dB * 0.05)        # dB -> linear
g *= blendFactor                                                     # linear multiply
g  = (g < 10^(-144/20)) ? -144.0f : 20*log10f(g)                     # linear -> dB
g += aux_dB
g += panTerm_dB                                                      # mode 1 or 2, polynomial
return (g < -144.0f) ? -144.0f : g
```
Constants read directly: `-145.0`, `-144.0`, `6.309573e-08` (=10^(-144/20)), `0.05`, `10.0`, `20.0`,
`0.5`. Net effect is essentially `volume_dB + aux_dB + 20·log10(blend) + pan_dB`, floored at −144,
with −145 meaning off.

**Why it still must not ship enabled.** Three gaps remain: the exact param→slot assignment inside
the 0x88-byte link object, the pan law's two modes, and — the one that actually bites — the
`volume` descriptor's taper is **`fader`**, not linear, over `[-96, +10] dB`. Without that curve a
normalized 0.5 maps to the wrong level. And none of it has touched hardware. The skeleton accepts
mixer writes into shadow state and emits nothing; `--enable-mixer` is a stub that logs rather than
guesses. Turning it on is a hardware-session decision, and the cheapest first experiment is a
single message with `gainDb = -145` vs `0` on block 100 / index 0 / paramId 3 while listening.

### 6.3 Discovery datagram bytes 12..32

Twenty bytes, from record `+0x10..+0x24`. `+0x10` is a flags dword (the receiver logs it as
`0x%08x`); the remaining 16 bytes were not decoded. Zeros are accepted by every client in scope
because oddbear slices `data[32..]` and ignores the gap entirely. If another UCNET consumer is ever
targeted, this is the first thing to re-derive.

### 6.4 `'NPar'` pass-through for the two volume routes

`global/phonesVolume` and `global/mainOutVolume` are float `[-96, 0] dB` with taper `exp` on the
UCNET side, wrapped in an `'NPar'` (normalized-parameter) adapter, while the device parameters are
plain `0..1`. Passing the normalized value straight through is coherent — the adapter exists to
expose fader position, and the device applies its own curve — and it is what the prior analysis
verified at 0x180036940 / 0x1800369b7. But it is the one NATIVE route where a wrong model produces
a plausible-looking result rather than an obvious failure. **Confirm on hardware**: set
`global/phonesVolume` to 0.25 / 0.5 / 0.75 and read `JaSt` slot 43; the pass-through model predicts
0.25 / 0.5 / 0.75 exactly. A `dB` interpretation would predict something near 0.001 / 0.03 / 0.18.

Related and cosmetic: a plugin that displays dB will need the `exp` taper to render a label, and it
has no way to get it from us. Nothing in oddbear's provided sources does this.

### 6.5 `global/phonesSrc` (`'Pari'` 11) — write-only, never read back

New in this analysis, absent from PROTOCOL.md §6a. The firmware stores it directly at
`device+0x1100` (handler 0x6004e6b4, reached via the io24 `'Pari'` vtable override at 0x6005bc5c),
bypassing `setParam`, which is exactly why it has no internal-id table entry. It cannot be observed
in `JaSt`, so a write is unverifiable from software — it needs one listening test.

### 6.6 Client bugs the shim cannot fix, and must not paper over

- `DeviceMetadata.TryParseDeviceMetadata` switches on `deviceTypeString` (= `segments[1]` = `"AUD"`)
  against `"Revelator IO 24"` / `"Revelator IO 44"`. Those never match, so `DeviceType` is **always**
  `RevelatorUsb`. Any plugin gating behaviour on device type will take the USB branch. Sending a
  different string in `segments[1]` does not help — the client rejects anything but `"AUD"`.
- `BroadcastService` hardcodes `if (metadata.SerialNumber == "JM1C20474458") continue;`. Avoid that
  serial.
- The no-reassembly reader (§2) is a latent failure that only appears under load or with a larger
  state tree. The shim's one-write-per-message discipline avoids it; a future contributor who adds
  buffering to the send path will reintroduce it silently.

### 6.7 Degradation policy — what the shim promises

For INERT, SHADOW, MIXER and BLOCKED routes: accept the `SetValue`, update shadow state so the
plugin's UI stays self-consistent, emit **no** USB traffic, and log the disposition. `SetP` is
fire-and-forget with no acknowledgement, so a shim that forwarded guesses would be indistinguishable
from one that worked — which is precisely why guessing is not acceptable here. Every route in §4 is
tagged with its disposition in the code, and `apply()` is the single choke point where that decision
is made.
