# WineUSB exact captured RANGE v2

## Scope and authorization

This checkpoint implements the offline-only step authorized after CP10. It
does not open the io24, access a USB node, start Wine or Universal Control,
claim or detach an interface, select an alternate setting, issue a USB write,
touch the protected Wine prefix, or modify the staged class-IN-v1 triplet or
its sandbox selector.

The implementation is deliberately device-specific and sandbox-only. It must
not be installed as a general WineUSB replacement. Any later staging must
remain behind the existing exact-device containment gate.

## Captured evidence and accepted tuple

CP10 passively captured the owned io24 returning this byte-identical response
twice with status zero. The pcap SHA-256 is:

    194a4b2619e0bddcdeef2108b0969cf13c029b3d2516309123c6567437b2922d

The PaeDSPUSB request accepted by this overlay remains exactly:

    function=URB_FUNCTION_CLASS_INTERFACE (0x1b)
    flags=USBD_TRANSFER_DIRECTION_IN | USBD_SHORT_TRANSFER_OK (0x3)
    reserved=0 request=0x02 value=0x0100 index=0x0500
    receive_capacity=256

The synchronous 50-byte response is:

    040044ac000044ac00000000000080bb000080bb000000000000885801008858010000000000007701000077010000000000

It is UAC2 `wNumSubRanges=4`: 44100, 48000, 88200, and 96000 Hz,
each encoded as minimum=maximum and resolution zero.

## Behavior

For only the accepted tuple, the Unix backend copies those 50 captured bytes,
sets `TransferBufferLength=50`, sets `USBD_STATUS_SUCCESS`, clears the unused
cancel handle, and returns synchronous `STATUS_SUCCESS`. It performs no
libusb allocation, submission, cancellation, or device I/O.

The Windows side retains the full v1 tuple validation and buffer mapping.
OUT direction, missing short-transfer permission, unknown flags, changed
request/value/index/capacity, reserved bits, a short header, and a missing
buffer still fail before any backend action. Select-interface remains on the
observation-only `STATUS_NOT_IMPLEMENTED` path. There is no class OUT, claim,
detach, alternate-setting, timeout-change, or write path.

## TDD and contained validation

The new v2 contract first ran against preserved class-IN v1. It failed with
eight expected assertions: pending status, unset USBD status, length 256,
missing captured payload, one libusb allocation, one libusb submission, a
pending transfer, and a cancel handle. Exit status was 1 with clean teardown.

After the minimal implementation, the real compiled WineUSB Unix call table
passed the v2 behavioral and source/binary contract. The exact response,
reported length, status, untouched tail and guard bytes, zero libusb activity,
and ten fail-closed variants all passed. The existing USB-DI v1 contract also
passed.

Both GREEN contracts were rerun in Bubblewrap with user/PID/network/IPC/UTS/
cgroup namespaces, all capabilities dropped, a private `/dev`, empty host
home, `/sys`, `/run`, and `/tmp`, and the project read-only. Each exited 0.

Contract inputs are:

    c04391b8e0156ea3a4ffeeff69d76862976ffa922394d95712b96db268a5878c  tests/wineusb_class_interface_range_contract.c
    6b1ccba2f22a749052e88f179c55fb7a6d9e71a6eed1dfa99ca63f451a7f22b3  tests/wineusb_class_interface_range_contract.sh
    f70f767da5d1d3475e44694eeec73d6a9290fce72c333f8f856706d2642067bd  tests/wineusb_class_interface_in_fake_libusb.c

The original v1 contract files were restored byte-for-byte and the preserved
v1 build still passes them.

## Patch and development build

The full replacement patch for Wine 11.15 layered with USB-DI v1 and
observation v2 is:

    461f68de736ddba876cfaa4d0e385c8eaa0002bd22df05932987ad3f4fe7fe8f  re/wine-11.15-wineusb-class-interface-range-v2.patch

It is not applied on top of class-interface-IN v1. A zero-fuzz application to
the preserved pre-class-IN baseline produced all three changed files
byte-for-byte. The development build recompiled only `unixlib.c`, without a
warning. Its temporary outputs were:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  wineusb.sys
    404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  wineusb.sys.so
    9518320f495ace5cabc27ef4e740f182b3840700fba3e9371b36b7e12538dea2  wineusb.so

The unchanged builtin build ID was
`e599b02a315eeee14ddf1285d1d995cde15f43c7`; the development Unix library
build ID was `8bf9a581c36824d5df469ab6ccc9a38974aab73a`.

No development binary is staged. After patch extraction and validation, the
class-IN-v1 development source and build outputs were restored to their prior
hashes. CP8 still verifies in full.

CP10 was made immutable before the active handoff advanced: its former live
handoff entry now points to byte-identical `CP10_HANDOFF_SNAPSHOT.md`. The
revised CP10 manifest verifies all entries.

## Gate

Stop at CP11. The next offline-only gate is two independent clean builds from
the hash-pinned Wine 11.15 archive plus USB-DI v1, observation v2, and this v2
patch, followed by both contract suites and byte-for-byte artifact comparison.
Do not stage binaries or change the sandbox selector until that succeeds.

No live Wine run is authorized. Device-node access, class OUT,
select-interface semantics, claims/detach, alternate settings, USB writes,
Universal Control, Voice FX, and the protected prefix remain out of scope.

## CP12 independent clean-build seal

Two independent source trees were freshly extracted from the hash-pinned Wine
11.15 archive. USB-DI v1, observation v2, and exact captured RANGE v2 were
applied separately with fuzz zero. The complete 12,445-file trees compare
identical, contain zero symbolic links, and have no patch leftovers.

Each tree was configured and built in a separate hardware-hidden, networkless
Bubblewrap invocation using identical virtual paths, pinned tool inputs,
SOURCE_DATE_EPOCH=1787101002, and make -j1. The resulting three-file
candidate triplets are byte-for-byte identical:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  wineusb.sys.so
    9518320f495ace5cabc27ef4e740f182b3840700fba3e9371b36b7e12538dea2  wineusb.so

Generated Makefiles, compile databases, and ELF build IDs also match. Both
the exact-RANGE and retained USB-DI contracts passed independently against A
and B in fresh hardware-hidden namespaces.

The full result is recorded in checkpoints/CP12_REPRODUCIBLE_BUILDS.md, with
summaries under logs/cp12-*. CP11 was made immutable first by preserving its
former manifest as CP11_MANIFEST_SNAPSHOT.md.

Stop at CP12. No v2 binary is staged, the sandbox selector still pins
class-IN v1, and the protected prefix contents were neither opened nor
modified. A later offline staging/driver-load gate must use only this exact
triplet and a fresh disposable sandbox. No live or hardware operation is
authorized.

## CP13 staged offline gate

CP12 was frozen before active files advanced. Its former manifest and harness
are preserved byte-for-byte as CP12_MANIFEST_SNAPSHOT.md and
CP12_HARNESS_SNAPSHOT.sh, and CP12 continues to verify.

The exact CP12 triplet is now staged beneath this directory. A real-harness
selector contract first failed because driver-load still pointed at
class-IN v1, then passed after the minimal RANGE-v2 selector and hash update.
The staged triplet passed exact-RANGE behavior/source/binary and USB-DI v1
contracts inside hardware-hidden containment and byte-matches clean build B.

The updated harness SHA-256 is:

    7a6beb27534114bdc125bc498d5a13fba13b6609a0545dc073081ef013da15e1

A fresh disposable sandbox clone was verified and promoted to:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.range-v2-20260821

Exactly one USB-hidden driver-load succeeded there. The transient unit used
the RANGE-v2 overlay, passed isolation and registry/NT-DDI/SSE2 gates, loaded
WineUSB and PaeDSPUSB, reported PaeDSPUSB RUNNING, and unloaded it during
cleanup. It ran 12.924 seconds, peaked at 112 MiB, and used zero swap.

There was no USB PDO in the hidden namespace, so no class or RANGE marker
executed. This is offline staging/load evidence only. The complete evidence
manifest has SHA-256
45087b770cdb8bf2405423b7a8a0183497881039f08c96a83b0c49da2988cfba
and CP13 is recorded in checkpoints/CP13_STAGED_OFFLINE.md.

Stop at CP13. No live Wine run or device access occurred. Any future
RANGE-v2 live-read needs a fresh full preflight and new explicit one-run
authorization. Class OUT, select-interface semantics, claim/detach, alternate
settings, USB writes, Universal Control, Voice FX, and protected-prefix
access remain out of scope.

## CP14 one bounded RANGE-v2 live-read

CP13 was made immutable before the live gate: its prior active manifest and
harness are now fixed snapshots, and its revised 18-entry checksum seal
verifies.

After new explicit one-run authorization, two complete preflight passes
bracketed a successful non-opening `live-audit`. They verified all seals and
hashes, no conflicting process/unit, and one exact io24 at
`/dev/bus/usb/003/004`, serial `AB7C22200355`, with interface 5 unclaimed.

Exactly one live-read ran as `io24-wine-live-read-903434.service`, invocation
`9b2b5f66d03b43fbba457abead1c3701`. It exited status 1 after 22.301 seconds,
used 3.661 CPU seconds, peaked at 116.4 MiB, and used zero swap. The service
reported `RUNNING`, but no UCNET `DA` announcement arrived and no
synchronization result was produced.

High-confidence structural comparison shows that the staged exact-RANGE path
cleared the prior error boundary: the same IRP now completes without either
the observation failure or its 120-byte driver error allocation, and the
driver advances. The next direct boundary is three four-byte request-`0x01`
class-IN tuples, each repeated in two device cycles and rejected fail-closed:

    value=0x0100 index=0x0500
    value=0x0700 index=0x0200
    value=0x0700 index=0x0300

The 276,104-byte capture has SHA-256
`8e8b62209d8cec8838b686e0da0b9851b4af992361acc9f62b8db699bbcbd93e`.
All 172 submissions have status-zero callbacks and are standard control-IN
descriptor reads. There is no control OUT, bulk, interrupt, claim/detach,
alternate-setting or configuration change, or immediate-submit error.

Postflight found the unit collected, no surviving candidate process, the
device/interface bindings intact, and the protected prefix and source sandbox
unchanged. Full interpretation and the 47-entry evidence seal are in
`checkpoints/CP14_LIVE_READ.md`; the evidence `SHA256SUMS` hash is
`cb18c9f9706038d61257df69c1279461a2fe184c7c900f431c391ca8ab01dfed`.

Stop at CP14. The one-run authorization is consumed. Do not retry or broaden
live behavior without new explicit authorization and a fresh full preflight.

## CP15 offline class-IN and pipe-path evidence

No new live action occurred. A test-first analyzer applied to the sealed
passive reconnect pcap found 14 successful clock-source sampling-frequency
`CUR` responses: 11 at 48 kHz and three at 96 kHz. The response is therefore
state-dependent. The capture contains no terminal-latency request, while the
complete io24 UAC2 descriptor advertises `bmControls=0x0000` for terminal
entities 2 and 3, meaning latency selector 7 is not present.

The CP14 log and exact Wine source also show that the driver continues beyond
all six fail-closed class-IN rejects, and WineUSB returns `STATUS_SUCCESS`
after logging each clear-halt failure. The more relevant unresolved path is
pipe/stream setup: no bulk or interrupt submission was captured, Wine's MDL
mapping and DPC paths are stubs, `SELECT_CONFIGURATION` initializes only its
first interface record, and the io24 vendor bulk endpoints belong to
interface 5 alternate setting 1 while passive sysfs remains at alternate 0.

The reproducible evidence and cautious causal classification are recorded in
`checkpoints/CP15_OFFLINE_EVIDENCE.md` and `logs/cp15-*.txt`. No WineUSB
behavior or staged artifact changed. A future observation-only patch remains
offline work; any live validation still needs new explicit authorization.
