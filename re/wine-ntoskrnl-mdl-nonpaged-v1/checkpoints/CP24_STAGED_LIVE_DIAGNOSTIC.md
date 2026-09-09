# CP24 — staged nonpaged-MDL kernel and one live diagnostic

Reached on 2026-08-22. CP24 staged the exact CP23 kernel pair, retained the
sealed CP21 WineUSB triplet, validated both overlays in a fresh disposable
clone, ran one USB-hidden driver load, and then consumed the existing
authorization for one bounded non-mutating live diagnostic. It was not
retried. Battery stayed above the mandatory pause threshold: 71% and
discharging at the final live gate, 69% immediately after the run, and 76%
and charging at final postflight.

## Exact staged overlays

Only the CP23-reproduced kernel artifacts were staged:

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  x86_64-unix/ntoskrnl.exe.so

The active WineUSB artifacts remained the exact CP21 triplet:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  x86_64-unix/wineusb.sys.so
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  x86_64-unix/wineusb.so

The real-harness kernel selector recorded RED against the pre-CP24 harness
and GREEN after adding the kernel root, bind mounts, exact hashes, builtin
override, and combined kernel/WineUSB `WINEDLLPATH`. The prior WineUSB
selector was updated to require the same combined path. Both selectors then
passed against the clone. The exact executed harness is frozen as
`CP24_HARNESS_SNAPSHOT.sh`; it and the active harness have SHA-256
`720a780bb9bde1c24064ad848b86472dde66e19a230920402ab2d589c765304a`.

The contained multi-interface handle/safety, pipe-observe, captured RANGE,
USB-DI, and class-IN evidence contracts all passed with USB hidden. An initial
aggregate invocation accidentally supplied Wine's PE stub where the
code-bearing Unix builtin was required; it failed before device exposure, is
diagnosed in the retained logs, and the corrected full aggregate passed.

## Fresh clone and USB-hidden load

The observation-v2 baseline was cloned to:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.ntoskrnl-mdl-nonpaged-v1-20260822

Two wrapper attempts failed before copying because their private namespace
lacked `/run`; both left the collision-free target empty and are retained.
The corrected clone unit `io24-sandbox-clone-mdl-nonpaged-v1-20260822.service`,
invocation `145e647a11ff45caa21359ecdf097512`, then succeeded in 8.128 seconds.
`rsync -aHAXnic --delete --numeric-ids` reported no difference across 5,097
files, 41 symlinks, and 708 directories. The target has independent root and
registry inodes. Its inherited capture was moved without content change to
the explicitly historical name
`inherited-live-service-usb-observe-v2-20260819T194220PDT.txt`, freeing the
collision-sensitive live capture path.

Exactly one USB-hidden driver load ran as
`io24-wine-driver-load-178058.service`, invocation
`31e47b47f6ed4f24af0cf80a4540aa0e`. Registry probe, PaeDSPUSB start, and
query returned zero; the captured state was RUNNING. The unit succeeded in
17.132 seconds, used 3.211 CPU seconds, peaked at 54.1 MiB, and used no swap.
Because USB was hidden, it was expected not to exercise the MDL path.

## Live gate and consumed run

Two complete live preflights bracketed a successful 606 ms non-opening audit.
They reverified the CP23 and CP21 project/runtime chains, all offline gates,
the staged hashes, the absent capture collision, the official driver hash,
the source clone hashes, battery, serial, node, configuration, alternate
settings, bindings, and protected-prefix metadata. CP21's sealed trace and
the unchanged driver established that all eight prior transfer URBs were
bulk-IN on endpoint `0x82`; none targeted endpoint OUT.

The one authorized live-read ran as
`io24-wine-live-read-197499.service`, invocation
`8f9790c96bc84b8a9d331c11949d15e4`. Isolation exposed only sysfs device
`3-1` and `/dev/bus/usb/003/002`; home, audio, GPU, user bus, and external
network remained hidden. The service reported RUNNING, but the UCNET probe
received no `DA` announcement within eight seconds and no `synchronize.json`
exists. The unit exited 1 after 29.906 seconds, used 5.654 CPU seconds,
peaked at 102.8 MiB, and used no swap. It was not retried.

## MDL result and next software boundary

The live trace validates the CP22 compatibility change. Two complete
256-byte SELECT_CONFIGURATION requests were validated and populated without
rejection. Interface 4 received stable handles `0x202` for endpoint `0x02`
and `0x282` for endpoint `0x82`. The kernel built 24 nonpaged-pool MDLs. All
eight later 512-byte URBs carried handle `0x282`, flags `0x3`, and a non-null
MDL source; all eight mapped directly to their nonpaged source address.
There was no null mapping and the WineUSB null-buffer guard did not reject
them.

All eight routed to bulk endpoint `0x82`, then `libusb_submit_transfer()`
failed immediately with errno 16 because host interface 4 remained bound to
`snd-usb-audio` and was not claimed. WineUSB logged `libusb_status=-1` but
returned `STATUS_PENDING` (`0x103`) for every one.

Source inspection identifies the corresponding control-flow defect. The
bulk path stores the transfer in `irp->Tail.Overlay.DriverContext[0]` before
submission. On immediate submission failure it only logs, then
unconditionally returns pending; it does not clear DriverContext, set a
failure status, free the transfer/context, or return a non-pending status.
Because no transfer was accepted, no completion callback can run. CP24
therefore records zero `KeInsertQueueDpc` calls: immediate-submit cleanup and
status propagation, not DPC execution, is the first newly demonstrated
software blocker. GET_DESCRIPTOR and vendor-control paths contain the same
pattern and need an offline audit; class-interface IN already has the needed
cleanup shape.

Interface routing remains independent. The selected endpoints belong to host
interface 4, while prior descriptor evidence placed the vendor pair on
interface 5 alternate 1. CP24 does not authorize or test a claim, detach, or
alternate-setting change.

## USB and final-state evidence

The new capture is 1,793 lines and 187,249 bytes with SHA-256:

    ab998beda7e6544cf56d574b66212ee3129d17e4f7b97cf3378582d5ef105da8

It records 109 successful submissions and 109 status-zero completions, all
control-IN. Eight additional calls reached libusb's bulk submit path but all
failed before usbfs accepted an URB, so there is no bulk bus transaction.
Four clear-halt calls against endpoints `0x82`/`0x02` also failed `EBUSY`
without a bus transaction. There is no bulk, interrupt, or control-OUT event
and no claim, release, detach, automatic detach, alternate-setting change, or
configuration change. The kernel window independently contains twelve
interface-4-not-claimed messages and no reset, disconnect, reconnect, or
binding event.

Immediate and final postflight found no candidate Wine process or test unit.
The standing `io24-crashwatch.service` is the pre-existing low-priority
power/load/thermal telemetry monitor and was left untouched. Serial
`AB7C22200355` remained at sysfs `3-1` and `/dev/bus/usb/003/002`,
configuration 1, speed 480, alternate 0 everywhere; interfaces 0-4 remained
on `snd-usb-audio` and interfaces 5-6 remained unclaimed. The source clone's
three pinned hashes were unchanged. The protected `.wine-io24` prefix
retained inode 3427833 and timestamp
`2026-08-12 00:31:35.825186221 -0700`.

## Evidence and stop boundary

The read-only analysis contract recomputed every critical count and passed.
The complete 110-entry runtime chain verifies at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.ntoskrnl-mdl-nonpaged-v1-20260822/out/checkpoints/live-read-ntoskrnl-mdl-nonpaged-v1-20260822T145019PDT/

Its `SHA256SUMS` SHA-256 is
`2717a3f6cabfaf65acccbc03a6b8b1e540620cce82e9ecc0b7dbd0b688591807`.

Stop at CP24. The one live authorization is consumed, and service RUNNING is
not synchronization. Safe next work is offline and test-first: reproduce the
immediate-submit error, implement cleanup/status propagation, audit the two
sibling paths, and separately analyze interface routing. Any future
device-visible action requires new explicit authorization and a fresh full
preflight. Firmware, full Universal Control, Voice FX, class-OUT, protected
prefix access, claim/detach, alternate-setting changes, and configuration
changes remain out of scope. Pause at 10% battery or lower.
