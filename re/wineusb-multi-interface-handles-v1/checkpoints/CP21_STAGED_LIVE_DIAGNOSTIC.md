# CP21 — staged multi-interface handles and one live diagnostic

Reached on 2026-08-22. Battery stayed above the mandatory 10% pause boundary;
it was 63% and charging at the live gate and 70% and charging at final
postflight. This is the third and final checkpoint requested in this run.

## Exact staging and selector

The CP20 reproducible-build seal reverified. Only its byte-identical candidate
triplet was staged:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  x86_64-unix/wineusb.sys.so
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  x86_64-unix/wineusb.so

A real-harness selector contract first failed because `WINEDLLPATH` still
selected pipe-observe v3. It passed after the minimal hash-pinned
multi-interface-handles v1 selector change. The new handle/safety contract,
pipe-observe contract, exact RANGE-v2 contract, USB-DI contract, and CP15
evidence analyzer all passed against the staged artifacts in hardware-hidden,
networkless containment.

## Fresh clone and hidden driver load

The unchanged observation-v2 source sandbox was independently cloned to:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.multi-interface-handles-v1-20260822

Full content and metadata comparisons matched across 5,097 files, 41
symlinks, and 708 directories, with independent registry storage.

The first `driver-load` wrapper invocation stopped before creating a systemd
unit because its outer shell lacked the user-session DBus environment. The
unit did not exist, its journal was empty, no candidate process ran, and the
device was unchanged. This prelaunch failure is retained and was not counted
as candidate execution.

After restoring only that outer environment, one USB-hidden driver-load ran as
`io24-wine-driver-load-435682.service`, invocation
`0a2500d4972c4e1da3402e3ab6e21f54`. The exact registry probe returned zero;
PaeDSPUSB start and query both returned zero and the query reported `RUNNING`.
The unit succeeded after 14.562 seconds, used 2.454 CPU seconds, peaked at
55.9 MiB, and used zero swap. Postflight found no surviving candidate process
or test unit and no device or protected-prefix change.

## One live run

Two complete live preflights bracketed a successful 488 ms non-opening audit.
They reverified the CP20 seal, active selector, staged triplet, disposable
prefix, source baseline, preserved inherited capture, process/unit gates, and
the same connected device:

    vendor:product=194f:0422
    serial=AB7C22200355
    sysfs=3-1
    node=/dev/bus/usb/003/004
    configuration=1
    speed=480
    interfaces=7
    interface-5=unclaimed

Exactly one live-read ran as `io24-wine-live-read-464970.service`, invocation
`59fd56a3262a46d5b59922ce0600257b`. The registered PreSonus Hardware Access
Service reached state 4 `RUNNING`, but the bounded probe received no UCNET `DA`
announcement within eight seconds. No `synchronize.json` exists. The unit
therefore exited 1 after 25.639 seconds, used 4.492 CPU seconds, peaked at
103.8 MiB, used zero swap, and was not retried.

## Handle population and next blocker

The live markers directly validate the new behavior. Two valid 256-byte
`SELECT_CONFIGURATION` requests each contained seven interfaces and two
pipes. Both passed complete-request validation and population with no reject.
Interface 4, alternate 0, class 1/subclass 3 received stable bulk handles:

    endpoint 0x02 -> handle 0x202
    endpoint 0x82 -> handle 0x282

The driver then issued four 512-byte bulk-IN URBs per device cycle. All eight
carried handle `0x282` and decoded correctly to endpoint `0x82`, but all eight
non-null MDLs passed through Wine's `MmMapLockedPagesSpecifyCache` stub and
mapped to null. The candidate emitted eight fail-closed null-buffer rejections,
zero libusb allocations, and zero WineUSB transfer submissions. Eight
`KeInsertQueueDpc` stubs remain as a separate completion-path boundary.

This clears CP18's missing-handle blocker; it does not demonstrate a working
bulk path. The selected endpoints belong to host interface 4, which remains
bound to `snd-usb-audio`, while prior descriptor evidence placed the vendor
bulk pair on interface 5 alternate 1. MDL mapping, DPC dispatch, and
interface/alternate routing therefore remain separate offline questions.

## Direct USB and postflight evidence

The new capture is 2,283 lines and 237,649 bytes, SHA-256:

    db25dc188d5cd568fc2082eb8cf34912b12eb3b8b7aabb10cad53a494817e6f9

It contains 146 accepted submissions and 146 status-zero completions, all
control-IN. There is no bulk, interrupt, or control-OUT bus transaction and no
libusb claim, detach, alternate-setting change, or configuration change.

Libusb made six clear-halt attempts against endpoints `0x82` and `0x02`; all
six failed with `EBUSY`. The kernel window independently reports six attempts
to use interface 4 without a claim and contains no reset, disconnect,
reconnect, or binding event. These failed ioctls produced no successful USB
transaction.

Immediate and final postflight found no candidate process or active test unit.
The device retained the same identity, configuration, alternate settings, and
bindings: interfaces 0 through 4 remained on `snd-usb-audio`, and interfaces 5
and 6 remained unclaimed. The protected `.wine-io24` prefix retained inode
3427833 and timestamp `2026-08-12 00:31:35.825186221 -0700`; the source clone's
three pinned artifacts remained hash-identical.

## Evidence boundary

The complete 77-entry runtime chain verifies at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.multi-interface-handles-v1-20260822/out/checkpoints/live-read-multi-interface-handles-v1-20260822T103059PDT/

Its `SHA256SUMS` SHA-256 is
`38061a271ece0f9d4d90d6c11ec467fdef79c7ca1e8395ac42ab0264ed1ec026`.
The exact executed harness is frozen as `CP21_HARNESS_SNAPSHOT.sh`.

Stop at CP21. CP19, CP20, and CP21 complete the requested three checkpoints.
No further live run is needed. Safe next work is offline, test-first analysis
of MDL mapping, DPC semantics, and interface/alternate routing. Firmware, full
Universal Control, Voice FX, the protected prefix, interface claim/detach, and
alternate-setting changes remain untouched.
