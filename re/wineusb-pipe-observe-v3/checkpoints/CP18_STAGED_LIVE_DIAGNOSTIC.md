# CP18 — staged pipe observation and one live diagnostic

Reached at 2026-08-21T05:38:16-07:00 after the complete staging, USB-hidden
load, authorized live diagnostic, and postflight gates. This is the third and
final checkpoint requested in this run. Battery was discharging at 45% during
postflight and 43% when the evidence seal was verified, above the mandatory
10% pause threshold.

## Staging and selector

CP17's prior harness was preserved byte-for-byte as
`../CP17_HARNESS_SNAPSHOT.sh`, and the revised 38-entry CP17 checksum chain
verifies. A new real-harness selector contract was written first. RED exited 1
only because the harness still selected RANGE v2. The exact CP17 triplet was
then atomically staged:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  x86_64-unix/wineusb.sys.so
    90d060571d9f8a56aea8d91485802fe500920f741fb5787543a8c141ae104eb9  x86_64-unix/wineusb.so

The minimal harness change now hash-pins and mounts only pipe-observe v3. The
selector became GREEN, shell syntax passed, staged bytes matched clean builds A
and B, and the pipe-observe, exact RANGE-v2, and USB-DI contracts all passed
again in hardware-hidden, networkless containment.

Current harness and selector hashes are:

    3e41a3dd9c2205dfa1d53374a1f3533934829702b741fa416316b5cc39ef5b8e  tests/uc_wine_sandbox.sh
    97587106a3a8889102fd6a3d2d4912aff26aade5be64eb049844e06165d23c45  tests/uc_wine_sandbox_pipe_observe_v3_selector_contract.sh

## Fresh disposable clone and offline load

A bounded transient service copied the unchanged observation-v2 baseline into
a partial path with archive/reflink/sparse semantics. Full content and a
path/type/mode/owner/group/size/mtime/link-target manifest matched; counts were
5,097 files, 41 symlinks, 708 directories, and no special files. The clone's
registry had independent storage and it was atomically promoted to:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.pipe-observe-v3-20260821

One USB-hidden driver-load ran as `io24-wine-driver-load-212427.service`,
invocation `d600b869c0d148b6b6b67d9564e4479f`. Systemd recorded success after
17.909 seconds, with 3.362 CPU seconds, 119.5 MiB peak memory, and zero swap.
The registry-handle, Windows 7 NT DDI, and SSE2 gates passed; start/query both
returned zero and PaeDSPUSB reported RUNNING. The namespace contained no USB
PDO, and postflight was clean. The enclosing terminal wrapper reported status
1 after logging `driver_load_exit=0`; the run was not retried. The systemd
journal, driver status/query files, and postflight independently establish the
driver-load result.

## One authorized live diagnostic

The user's connected-device authorization is preserved in the runtime evidence.
The inherited observation-v2 capture was renamed within the new disposable
clone and preserved byte-for-byte. Two full preflight passes bracketed a
successful 579 ms non-opening live-audit. Each pass verified the revised CP17
seal, current hashes, official driver/runtime inputs, no conflicting process or
unit, battery, protected prefix, source sandbox, and exactly one io24 with
serial `AB7C22200355`, sysfs `3-1`, host node `/dev/bus/usb/003/002`,
configuration 1, and interface 5 unclaimed.

Exactly one live-read ran:

    unit=io24-wine-live-read-230235.service
    invocation=458992c0b9484d138d0c4e32d0ed707d
    result=exit-code
    status=1
    runtime=29.729s
    cpu=5.584s
    memory_peak=112.4M
    swap=0B

Containment exposed only that io24 node and hid host audio, GPU, home, session
bus, protected prefix, and external networking. The PreSonus service registered
and reached RUNNING, but the bounded read-only UCNET probe received no `DA`
announcement and produced no synchronization document. The live run was not
retried.

## Decisive pipe evidence

The two device cycles each supplied one valid 256-byte
SELECT_CONFIGURATION containing all seven interfaces. Only interface 4 had
pipes: two bulk pipes, endpoints `0x02` and `0x82`, maximum packet 512 and
maximum transfer 4,096. WineUSB's backend logged that it processed only first
interface 0, which had zero pipes. It generated zero handle markers, and every
interface-4 pipe handle remained null after the Unix call.

PaeDSPUSB then issued eight 512-byte bulk/interrupt URBs. Every request had a
non-null MDL but a null mapped buffer, a null pipe handle, decoded endpoint 0,
decoded control type 0, and route `invalid`. There are zero transfer-submit
markers. Thus none reached `libusb_submit_transfer`.

This resolves CP15 to at least two independent pre-libusb blockers:

1. SELECT_CONFIGURATION initializes only the first embedded interface, so the
   actual interface-4 bulk pipes get no handles.
2. `MmMapLockedPagesSpecifyCache` returns null for all eight MDLs.

The same log also retains eight non-dispatching `KeInsertQueueDpc` stubs. Fixing
only one blocker is not evidence that transfer or synchronization will work.
All four clear-halt calls also used the null handle, decoded endpoint 0/control,
received libusb `-5`, and were returned to Wine as success.

## Capture and postflight

The 178,467-byte capture has SHA-256:

    80dd4b39dc35bed5e33551186a6abbb013518a160855558cdd112fe94f8b3d4f

It has 105 submissions and 105 status-zero completions, all standard
endpoint-zero descriptor control-IN. It contains no bulk, interrupt, control
OUT, claim, detach, alternate-setting change, configuration change, synchronous
control API, or capture error.

Postflight found no active io24 Wine unit or surviving candidate process. The
device retained its identity, configuration, node inode, all alternate settings
0, snd-usb-audio bindings on interfaces 0–4, and unclaimed interfaces 5–6. Its
node mtime advanced to run-end time; the filtered kernel window is empty, so no
cause is assigned. The protected `.wine-io24` prefix and source sandbox stayed
unchanged. Only the disposable clone's registry and outputs changed.

The complete 65-entry runtime evidence verifies at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.pipe-observe-v3-20260821/out/checkpoints/live-read-pipe-observe-v3-20260821T053410PDT/

Its `SHA256SUMS` SHA-256 is:

    ff38e017ec8c554af08d0357c88bf583c7be743ffd834b134c3bfd807a4af87d

## Stop after requested checkpoint

Stop at CP18. The next safe work is offline, test-first implementation of
full variable-length interface handle population and, separately, the MDL/DPC
kernel compatibility paths. Do not infer synchronization from service RUNNING
or attempt another live run as part of this three-checkpoint request. Firmware,
full Universal Control, Voice FX, and the protected prefix remain untouched.

