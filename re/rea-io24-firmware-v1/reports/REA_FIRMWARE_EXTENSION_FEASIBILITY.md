# io24 firmware-extension feasibility

Date: 2026-10-14

## Scope and safety

This investigation evaluates whether the recovered io24 application can safely
carry a firmware extension. All binary inspection used REA 6.4.0 with its
Ghidra 12.1.4 provider and the preserved Universal Control 4.7.2 artifacts.
The initial static pass did not open the connected io24. Later, separately
authorized bounded compatibility probes used only the exact requests recorded
below; no DFU download block, firmware payload, upload, or modified image was
sent.

The analyzed application envelope has SHA-256
`9603830a27f480011a29924d4cfef552185024a9b1f9b7dc39e82a6462320e14` and
contains the immutable vendor package with SHA-256
`790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`.

## Result

A firmware extension is technically plausible, but the current image does not
provide a linker-supported extension region. REA observes one contiguous,
initialized, loaded segment from `0x60020000` through `0x6014a693`, with entry
point `0x60020334` and no relocation records. The segment is exactly the
1,222,292-byte vendor package. Evidence:
`ev_a7b3cd3a179562e20d0d6f9fa0067074bbfa539521bc4df22662ffec9d707079`.

The last 256 loaded bytes are not an empty append area. They contain data and
pointers, an `0xff` run, two `ASCII` markers, and the final validation fields,
including stored CRC32 `0xed65737c`. Evidence:
`ev_3cec1833b5610062651e07f220a72eff96ffedaa68c6a36c9952dfc199d282a3`.

Therefore the first extension cannot safely be implemented by appending code
after the current image. It requires either a proved internal code/data cave or
a deliberate package-layout change accepted by both the host validator and the
device-side bootloader.

## Package metadata and integrity boundary

The 192-byte metadata object begins at package offset `0x205e0`, mapped at
`0x600405e0`. REA reads the metadata marker, target `0x194f0407`, image ID 1,
format version 1, protected length `0x12a68d`, build timestamp, release label,
and mapped address descriptors directly from that block. Evidence:
`ev_ab12d231b82752f846328eeb10dab4ce0bb7535905f2f695c9829bc884799824`.

The full package length is `0x12a694`, seven bytes longer than the protected
length. The tail evidence shows those ending bytes are part of the validation
trailer rather than spare extension capacity. Universal Control's recovered
validator checks the metadata bounds and recomputes the table-driven CRC32;
changing protected bytes therefore requires regenerating the protected length,
mapped descriptors where applicable, and CRC consistently.

Host-side acceptance alone is not sufficient. The device compatibility request
and application-external DFU bootloader may impose an additional maximum image
length or address policy that cannot be recovered from the application package.

## Persistent-storage attachment boundary

The preset-storage object is embedded at byte offset `0x1240` in the main
device object. `FUN_600506bc` constructs its storage-interface member with a
null backend pointer; the main device constructor `FUN_6005c890` owns that
object. Evidence:
`ev_dc384356a2e3c950519219e46a518fff753898d9d7ebd37a6189b4f7f379fc45`
and `ev_d5a8b790c41039447784735b7a9d3a7510c62f1ae86470b708f1fdc934a804db`.

The storage vtable at `0x600874f8` places the backend setter thunk
`0x600506b5` in slot `+0x0c`; that thunk forwards to `FUN_6004c1c0` and stores
the supplied backend pointer. Evidence:
`ev_8ce2d81275841b1e8fb2385509e8013ca4899b85ffa9cea0e27d9afea5b40d7e`.

The recovered outer lifecycle method `FUN_6005ad54` propagates a generic
service pointer to three sibling components but does not bind this storage
backend. Evidence:
`ev_cb9f821de5b4779188ee837333e478c0828264863b5436fa327c405f0c0bd0c5`.
The concrete nonvolatile provider is therefore still supplied through an
unresolved indirect call. Calling the medium flash or EEPROM would remain a
guess.

## Smallest viable first extension

The safest first functional extension remains shared reverb persistence because
block 202 already implements both sides of a bounded state contract:

- writer `0x6006faa0` emits one `0x2c`-byte body;
- loader `FUN_60076edc` requires exactly `0x2c` and reapplies it;
- the existing DSP reconfiguration path currently restores default `Setu`
  state instead of invoking the loader.

A firmware implementation should add a versioned global record containing the
44-byte body, write it through the existing bounded/checksummed storage
abstraction, and invoke the loader only after block 202 has been constructed and
sample-rate initialization has completed. An invalid, absent, or older record
must fall back to the current defaults.

This design is not yet ready to compile or flash. The following prerequisites
remain load-bearing:

1. Resolve the concrete nonvolatile backend and its erase/write granularity,
   capacity, atomicity, and interrupted-write behavior.
2. Prove an internal executable/data placement or prove that the bootloader
   accepts a larger mapped image.
3. Reconstruct the exact package rewrite operation and independently validate
   metadata, protected length, address descriptors, and CRC.
4. Acquire or otherwise establish a recovery image and a verified DFU rollback
   procedure before the first modified package is transferred.
5. Add a format version and fail-closed parser so stock presets and firmware
   remain readable.

Multiband compression should follow this persistence proof, not precede it. It
adds real-time CPU, state, coefficient, buffer, and UI/protocol requirements;
the 44-byte reverb record exercises code placement, package reconstruction,
nonvolatile storage, boot restore, and rollback with the smallest state change.

## Internal-placement audit

REA inventoried every recovered procedure entry in the loaded segment. Evidence:
`ev_d3a7582868145eb09c07a7054166e88e46e9f3197c18d1f53052d93f841e9673`.
The largest apparent procedure-free interval begins after the two-byte terminal
function at `0x60085aa4` and ends at the external-thunk table at `0x6012d758`.
It is not blank: a complete REA byte measurement shows densely structured data
with many zero-filled fields and asset/table payloads.

The two largest continuous zero runs in that interval are 3,201 bytes at
`0x60115e7c` and 2,321 bytes at `0x600dc6ec`. Their surrounding bytes have the
same sparse record pattern, including repeated nonzero boundary fields. That is
evidence of structured payload capacity, not linker padding. Ghidra reports no
exact reference to `0x600dc6ac`, but absence of a reference to one interior
address does not prove that the enclosing object is unused. Exact-reference
evidence: `ev_afc25345191158543f579cc81a28aa89cf2e3528d0ddaf8d04e6d2d4a9ec2cd1`.

Neither run is accepted as a code cave. Reclaiming one would first require
identifying its enclosing object, its length owner, and every base/offset
consumer. The current evidence supports no safe internal placement candidate.

## Static-analysis boundary

The backend setter is a four-byte operation reached through a Thumb-tagged
vtable thunk. The provider graph contains the vtable data reference but no
direct call edge to the setter; bounded REA value-flow cannot traverse the
targetless indirect dispatch. Consequently another decompiler pass over the
same application bytes cannot identify the concrete medium by call xrefs alone.

The next material evidence must come from one of these sources:

- a read-only capture of the platform-service/backend pointer during normal
  initialization;
- a separately acquired device-side bootloader or complete flash image; or
- a second authenticated firmware version whose changed storage wiring or
  layout exposes the provider and placement policy by comparison.

The first two are hardware-facing and require a separate explicit gate. No
modified package should be generated or transferred before one of them also
establishes recovery and maximum accepted image extent.

## Read-only runtime USB capability result

With explicit authorization, the connected unit was enumerated through standard
USB descriptor reads only. It is runtime device `194f:0422`, product
`Revelator IO 24`, `bcdDevice 1.28`, with serial `AB7C22200355`. It exposes one
configuration with seven interfaces at USB high speed. No interface was claimed
or detached, and the device was not reset or placed into DFU mode.

This corrects an important identifier ambiguity: package metadata target
`0x194f0407` is an image/compatibility target selector, not the unit's normal
runtime USB VID:PID. The application-mode unit observed by Linux is
`194f:0422`.

Interface 6 is a DFU 1.10 runtime interface (`fe/01/01`) with these declared
capabilities:

- attributes `0x0d`: Will Detach, Manifestation Tolerant, Download Supported,
  Upload Unsupported;
- detach timeout: 2,000 ms;
- transfer size: 4,096 bytes;
- no kernel driver attached in the observed runtime state.

The descriptor confirms the host-side updater's `0x1000` transfer-block size.
It does **not** establish maximum accepted image length. More importantly,
`Upload Unsupported` closes standard DFU as a read-only bootloader or flash
acquisition route. Entering DFU, detaching the runtime interface, sending a
vendor compatibility request, or downloading any block remains outside this
read-only pass.

The device also exposes unclaimed vendor-control interface 5 (`ff/00/00`) with
bulk endpoints in alternate setting 1. Its mere presence does not authorize or
identify a readback command.

REA reconstruction of the shipped `dspusbdevice.dll` now identifies the
updater's compatibility helper precisely. `FUN_1800a0b40` builds a four-byte
vendor/interface control-IN request with `bmRequestType=0xc1`,
`bRequest=0xd2`, `wIndex` equal to the selected DFU interface number, and
`wLength=4`; `wValue` is supplied by its caller. A successful nonzero reply is
mapped to the updater's `0xee000000 | (reply & 0x3fff)` status namespace.
REA evidence: `ev_d1cc4aa413a236113c9050563ea6e7152a9076a7c0ff1856f41cfdff8ba29059`.

The helper occupies slot `0x98` of
`thesycon::DfuDevicePortUsbDfu::vftable`. The second apparent reference at
`0x1804ab944` is PE unwind metadata, not another caller. REA resolved the
indirect call through `thesycon::DfuDevice::CheckImageCompatibility`: the
method receives the same one-byte target selected by `TLDFU_StartUpgrade` and
passes it unchanged as the request's `wValue`. Evidence:
`ev_08d407f325a58ad0a1bd6758f03d9314115ade80fd8b23f6902c2c2fceb73b90`.

The complete argument chain is now known. `DfuDevice::StartUpgrade` rejects
targets above `0xff`, stores its target argument at object offset `+0xb4`, and
the compatibility method later reads that exact byte. Evidence:
`ev_a229243b56e53175f75340853e6eb4942a97c9a0a3553c6c1429f33ee3e8c848`.
PreSonus's `DeviceFirmwareUpdate::DoUpgrade` supplies the target from its own
field `+0x12c` to `TLDFU_StartUpgrade`; `StartImpl` fills that field from the
second word of the selected 16-byte target-info record. Evidence:
`ev_c6b933ccb8508367743c336622ee4488455deef3d44ab11b2f5a6061fa5293c9`
and `ev_619d73316427c67f132610f83acdf84e3a3d7501f451471c13f272ceeca7fa3b`.

REA also recovered the io24 target-info table from the shipped registry
initializer. Its three 16-byte records begin with these four-word tuples:
`(0,0,0,1)`, `(1,1,1,1)`, and `(3,2,1,1)`. `FUN_1800844d0` copies that range
in 16-byte units, confirming the record boundaries. Evidence:
`ev_2df4cc5eb4ef2ab5a086b105c26629a970c319881357377048a9022dc79bc968`
and `ev_97cfc08161a587e9961dcce88fdc18130b7be21024f41f5306d8fb8b4f2f0cb6`.
Because `StartImpl` matches the first word (image ID) and takes the second word
as the DFU target, the shipped package's image ID 1 maps to target 1.

The exact compatibility request for this package is therefore
`bmRequestType=0xc1`, `bRequest=0xd2`, `wValue=1`, `wIndex=6`, `wLength=4`.
The configuration identity `0x194f0407` is a separate field and is not placed
in this setup packet.

With exact authorization, this request was issued exactly once while the io24
remained in its normal `194f:0422` runtime state. libusb returned `EPIPE`
(`USBError: [Errno 32] Pipe error`), which records a control-pipe STALL and no
response payload. The request was not retried. No interface was claimed or
detached, and no reset, DFU transition, upload, download, or device write took
place. Passive postflight retained the same high-speed topology: audio
interfaces 0-4 bound to `snd-usb-audio`, interfaces 5-6 unclaimed. Battery was
100 percent and Full. A direct VID:PID listing was unavailable during that
postflight because this process could not initialize libusb, but the kernel
USB topology retained device 003 on bus 003 with the identical seven-interface
layout and driver bindings.

This result does not overturn the statically recovered setup packet. In the
REA call path, `DfuDevice::StartUpgrade` requires bootloader run mode before it
invokes `CheckImageCompatibility`; the application-mode STALL is consequently
consistent with the vendor request being implemented only by the bootloader.
It does prove that the normal runtime device does not return the compatibility
word for this request as issued.

## Bootloader identity and recovery boundary

The bootloader USB identity is not hypothetical. Two earlier device incidents
recorded the same unit re-enumerating as `194f:0405`, product `Revelator IO 24
BOOTLOADER`, with only DFU interfaces and no ALSA card. In both cases the unit
returned intact to application identity `194f:0422` after a true cold power
cycle that removed device power; a logical USB replug through a powered hub was
not sufficient. The application flash, serial identity, and readable control
state were retained. This is observed recovery evidence, not a claim that a
failed download would be equally recoverable.

REA places a hard boundary around the host updater. `DeviceFirmwareUpdate::
DoUpgrade`/`FUN_1800815a0` enumerates DFU-mode devices and requires exactly one
before it calls `TLDFU_StartUpgrade`. The recovered download state machine does
not perform the application-to-bootloader transition. The Cortex-M application
does contain a controlled-reset primitive and a mode-controlled caller, but
REA has not assigned the mode field a DFU semantic. Therefore neither that
private reset path nor a guessed vendor command is an acceptable transition.

The runtime descriptor itself supplies the only currently grounded transition
mechanism: interface 6 is DFU runtime protocol `fe/01/01`, advertises Will
Detach, and declares a 2,000 ms detach timeout. Under USB DFU 1.10 this
corresponds to one standard class/interface `DFU_DETACH` request:
`bmRequestType=0x21`, `bRequest=0x00`, `wValue=2000`, `wIndex=6`, `wLength=0`,
followed by passive enumeration for `194f:0405`. This conclusion combines the
observed descriptor with the standard protocol; it is not a decompiled
vendor-specific transition.

The bounded recovery plan for any future transition is consequently:

1. require runtime `194f:0422`, interface 6, exact serial `AB7C22200355`, and
   battery above the project stop threshold;
2. send at most one standard `DFU_DETACH` to interface 6 and wait passively for
   `194f:0405`; do not claim audio interfaces or send a download block;
3. if bootloader enumeration appears, read descriptors and issue at most the
   already recovered four-byte `c1/d2` compatibility query for target 1;
4. return to runtime by removing device power and cold reconnecting, then
   verify `194f:0422`, serial, audio interfaces, and readable state;
5. stop immediately on any different identity, timeout, battery threshold, or
   inability to remove device power. Do not improvise a reset or transfer.

This plan still requires a new exact hardware authorization. It does not
authorize detachment, reset, compatibility retry, or firmware transfer.

## Live bootloader compatibility result

With exact authorization, the bounded sequence above was executed once on
serial `AB7C22200355`. Runtime preflight was `194f:0422`, firmware 1.28,
interface 6 DFU runtime, battery 100 percent/Full. The standard
`21/00/07d0/0006/0000` detach was acknowledged, and the unit re-enumerated on
the same port as `194f:0405`, product `Revelator IO 24 BOOTLOADER`, bootloader
version 1.15, with the same serial.

The bootloader has one DFU interface numbered 0, exposed through alternate
settings 0, 1, and 2. Therefore the bootloader request correctly differs from
the earlier runtime probe in `wIndex`: the single authorized query was
`bmRequestType=0xc1`, `bRequest=0xd2`, `wValue=1`, `wIndex=0`, `wLength=4`.
It returned bytes `62 00 00 e0`, little-endian `0xe0000062`. The recovered host
helper treats a nonzero reply as a device status and maps its low 14 bits into
the updater namespace, yielding `0xee000062`. Later REA status-map recovery
identifies it as `TLSTATUS_MAGIC_MISMATCH`. This is not an acceptance result
and does not authorize a download.

Post-run REA analysis establishes why that isolated result is not an image
compatibility verdict. `DfuDevice::CheckImageCompatibility` at `0x18009dc60`
calls vtable slot `+0x90` before slot `+0x98` and immediately returns any
nonzero compatibility status. Slot `+0x90` resolves to
`PrivStoreImageMetadataHeader` at `0x1800a09d0`; slot `+0x98` is the already
identified compatibility helper. Evidence:
`ev_08ba12e0b146e11e780eea8b57703703e56f6ac2d4a7853f4a548ca1bd01f171`
and `ev_58746db298a9034cb38bb7c6e5a23a3d94b272816fa5968cca0577de9bf17816`.

`PrivStoreImageMetadataHeader` sends exactly 60 bytes with a vendor/interface
control-OUT request: `bmRequestType=0x41`, `bRequest=0xd1`, zero `wValue`, the
selected DFU interface in `wIndex`, and `wLength=0x3c`. It requires all 60 bytes
to transfer before compatibility is queried. Evidence:
`ev_69902780371a4abe296cc0ae7c7c68edacdca25820d1c010753f4d655611e290`.
The authorized live run intentionally sent no control-OUT payload. Status
`0x62` therefore establishes that the bootloader rejects a bare target-1 query
without the stock metadata prerequisite; it does not establish that the stock
package, its target, or a modified package is incompatible.

Two preliminary local scripts failed before reaching `ctrl_transfer`—first on
a redundant string-descriptor lookup and then on bootloader usbfs permissions.
Consequently the compatibility request itself executed exactly once. A
temporary ACL was applied only to the bootloader node and removed immediately
afterward.

The user then removed device power and cold-reconnected it. Postflight restored
`194f:0422`, firmware 1.28, the same serial, all five `snd-usb-audio`
interfaces, and no `194f:0405` device. A bounded native status read succeeded
with protocol 1 and 2,048-byte command/response limits. No interface was
claimed by the compatibility probe, no kernel driver was detached, and no DFU
upload, download block, firmware write, or reset command occurred. The complete
machine-readable record is
`evidence/20261014T0615-0700-bootloader-compatibility/RESULT.json`.

## Interim verdict after the first bootloader probe

The extension objective is feasible enough to continue engineering, but not yet
safe enough to produce a device-bound image. The static application pass did
not establish a safe internal placement or concrete nonvolatile provider. The
runtime descriptor pass proves download capability and a `0x1000` block size,
but standard DFU explicitly forbids upload and exposes no maximum image extent.
The bounded live probe and its post-run REA analysis are complete. Runtime
correctly STALLed; the bare bootloader query returned `0xe0000062`, mapped by
the host to `0xee000062`; cold-power recovery passed. REA proves the query was
missing the stock updater's prior 60-byte metadata control-OUT stage, so the
reply is not an image incompatibility verdict. The next material gate is a new
exact authorization to send the immutable stock package's authenticated
60-byte metadata header and then repeat the four-byte query—still with no DFU
download block—or acquisition of the bootloader by another authorized method.
No metadata write, firmware download, modified-image transfer, reset, or
further hardware operation is authorized by this result.

## Stock metadata compatibility result and target-selection correction

With a second exact authorization, the immutable 60-byte metadata header from
the pinned stock package was sent once in bootloader mode, followed by one
four-byte target-1 compatibility query. The metadata transfer completed all 60
bytes. The reply was `3e 00 00 e0` (`0xe000003e`), mapped by the updater to
`0xee00003e`. REA resolved that status as `TLSTATUS_NOT_COMPATIBLE`; status
`0x62` from the preceding bare query is `TLSTATUS_MAGIC_MISMATCH`. Evidence:
`ev_639e37da82ea81f449df1fe8fcb3fe69ab0a2337fd12a869a30ce145f5d64ff9`.

Post-run REA analysis found one earlier stock-path prerequisite. Before the
metadata write and compatibility query, `DfuDevice::CheckImageCompatibility`
calls `SelectTarget` through vtable slot `+0x60`. `SelectTarget` at
`0x1800a0310` uses USB `SET_INTERFACE` when flags bit 0 is clear, and uses the
XMOS `0xf4` vendor path only when that bit is set. Evidence:
`ev_4e66aca05716737a58e8cf02b64a4528bb2aeb8af740b2091cab914f659d7360`
and `ev_ec9363af02b9923d66ba2a211fe54e8bb9f66a1da2fe3783405e716dcaf1311a`.

The exact PreSonus flag is now bounded without inference. `DoUpgrade` passes
`(field_130 & 1) * 2` to `TLDFU_StartUpgrade`, so its value is either 0 or 2
and bit 0 is always clear. The stock io24 target-1 path therefore selects USB
alternate setting 1 before sending `41/d1` metadata and `c1/d2`
compatibility. Evidence:
`ev_c6b933ccb8508367743c336622ee4488455deef3d44ab11b2f5a6061fa5293c9`.

The authorized live probe stayed on alternate setting 0. Its
`TLSTATUS_NOT_COMPATIBLE` result therefore does not test the complete stock
sequence and is not evidence that the pinned stock image itself is rejected.
No DFU download block or firmware payload was sent. After cold-power reconnect,
runtime `194f:0422`, firmware 1.28, the original serial, all five audio
interfaces, and the native protocol-1 status read were restored at 99 percent
battery. Exact evidence is in
`evidence/20261014T0700-stock-metadata-compatibility/RESULT.json`.

The next material gate is a new exact authorization for: detach, require the
known bootloader identity, select alternate setting 1, send the same immutable
60-byte metadata, issue one four-byte target-1 compatibility query, then
cold-power recover. It still excludes every DFU download block, firmware
payload, and modified image.

## Alternate-setting-1 compatibility result

That final bounded sequence was separately authorized and completed. Runtime
identity, serial, native status, and 99 percent battery passed preflight. The
known bootloader enumerated at `194f:0405`, alternate setting 1 was selected,
the pinned stock 60-byte metadata header transferred once, and one target-1
compatibility query returned `3e 00 00 e0` again:
`TLSTATUS_NOT_COMPATIBLE`. No DFU download block, firmware payload, upload, or
modified image was sent. The temporary node ACL was removed immediately.

Cold-power recovery passed: runtime `194f:0422`, firmware 1.28, serial
`AB7C22200355`, all five audio interfaces, protocol-1 native status, and 99
percent battery were restored. Exact evidence is in
`evidence/20261014T0714-alt1-stock-compatibility/RESULT.json`.

This materially closes the alternate-setting hypothesis. REA confirms that
the stock compatibility path first ensures standard `dfuIDLE`, then selects
the target, then sends metadata and compatibility for the TL-binary image.
Evidence: `ev_84c6bd8d29abd2d692765bcb225b2b7b92f5550d9db3d74e3557835da0a1809b`
and `ev_08ba12e0b146e11e780eea8b57703703e56f6ac2d4a7853f4a548ca1bd01f171`.
The fresh bootloader did not expose evidence of a non-idle recovery condition,
and the corrected target sequence still returned the same status.

The pinned package and installed application are both version 1.28. Refusal of
an equal-version reinstall is therefore the leading supported explanation for
`TLSTATUS_NOT_COMPATIBLE`, but it remains an inference: the device-side
bootloader implementation has not been acquired, so the precise comparison
that emits status `0x3e` is not statically proved. Repeating the same package
cannot add a material result. The next firmware-extension gate is offline:
construct a minimally changed, internally consistent metadata candidate and
validate its host-side integrity without sending it to the device. Any future
compatibility submission of changed metadata remains a separate hardware gate.
