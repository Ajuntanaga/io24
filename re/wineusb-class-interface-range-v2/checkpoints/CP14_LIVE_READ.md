# CP14 — one RANGE-v2 live-read, new class-IN boundary

Reached at 2026-08-21T03:54:01-07:00 after exactly one newly authorized,
bounded live-read and complete postflight. The run was not retried.

## Frozen predecessor and preflight

Before advancing, CP13's active manifest and harness were preserved
byte-for-byte as `CP13_MANIFEST_SNAPSHOT.md` and
`CP13_HARNESS_SNAPSHOT.sh`. The revised 18-entry CP13 checksum seal has
SHA-256:

    4bad0a5d0f5f5a0a392d0d1a9b40283c03be14ff6a27c5143f35a7b910853ddb

Two complete preflight passes bracketed a successful 348 ms non-opening
`live-audit`. They verified both prior seals, all staged/runtime hashes, the
preserved inherited capture, no conflicting process or live unit, and exactly
one io24: `194f:0422`, serial `AB7C22200355`, sysfs `3-1`, node
`/dev/bus/usb/003/004`, configuration 1, speed 480, seven interfaces, and
interface 5 unclaimed.

## One live-read

The sole run was:

    unit=io24-wine-live-read-903434.service
    invocation=9b2b5f66d03b43fbba457abead1c3701
    start=2026-08-21T03:52:39.441062-07:00
    end=2026-08-21T03:53:01.743180-07:00
    result=exit-code
    status=1
    runtime=22.301s
    cpu=3.661s
    memory_peak=116.4M
    swap=0B

Containment exposed only the exact io24 node, kept project/driver inputs
read-only, and hid host audio, GPU, home, session bus, protected prefix, and
external networking. The service registered and reported `RUNNING`, but the
bounded probe received no UCNET `DA` announcement within eight seconds and
produced no synchronization result. `RUNNING` is not synchronization.

## RANGE-v2 result

The Unix RANGE-success marker is a disabled `TRACE`, so success is supported
by high-confidence structural evidence rather than a direct marker. The new
log follows the prior observation log through the exact same first
`IofCallDriver`. Where the prior log printed the exact RANGE tuple and then
allocated a 120-byte driver error entry, the new IRP completes immediately,
allocates no error entry, and the driver advances. The same changed path
occurs in the second device cycle. This matches the staged implementation,
whose only silent class-interface success is the exact captured RANGE tuple.

The next fail-closed boundary is directly logged twice per cycle:

    flags=0x3 length=4 request=0x01 value=0x0100 index=0x0500
    flags=0x3 length=4 request=0x01 value=0x0700 index=0x0200
    flags=0x3 length=4 request=0x01 value=0x0700 index=0x0300

There are six `IO24_CLASS_IN reject` lines, zero driver error-log allocations,
zero select-interface observation markers, and four `Failed to clear halt:
Entity not found` errors. The response values for these three newly exposed
reads are not established.

## Capture and postflight

The capture is 2,662 lines and 276,104 bytes, SHA-256:

    8e8b62209d8cec8838b686e0da0b9851b4af992361acc9f62b8db699bbcbd93e

It records 172 accepted submissions and 172 status-zero callbacks. Every
transfer is a standard endpoint-zero control-IN descriptor read. There is no
control OUT, bulk, interrupt, interface claim, driver detach,
alternate-setting change, configuration change, or immediate-submit error.
The captured RANGE response is internal to WineUSB and therefore absent from
libusb traffic.

Postflight found the unit collected and no surviving candidate process. The
same device identity, configuration, node inode, and interface bindings
remained, with interface 5 unclaimed. The node mtime advanced to run-end time;
the filtered kernel journal contains no reset, disconnect, reconnect, or
binding event, so the metadata change is preserved without assigning a
cause. The protected prefix and observation source sandbox remained
unchanged.

The complete 47-entry evidence seal verifies at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.range-v2-20260821/out/checkpoints/live-read-range-v2-20260821T035239PDT/

Its `SHA256SUMS` SHA-256 is:

    cb18c9f9706038d61257df69c1279461a2fe184c7c900f431c391ca8ab01dfed

## Required stop

Stop at CP14. The one-run authorization is consumed and no retry occurred.
Any query for the three new response values, another live-read, interface
claim/detach, alternate-setting change, class OUT, USB write, full Universal
Control, Voice FX, or protected-prefix access requires separate explicit
authorization and a fresh complete preflight.
