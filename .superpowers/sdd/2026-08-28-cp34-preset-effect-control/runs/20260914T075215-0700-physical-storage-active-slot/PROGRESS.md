# CP34 physical storage and active-slot discriminator - progress

Timestamp: 2026-09-14T07:52:15-07:00
Status: complete; active-slot native writer is a measured negative

## Live result

After explicit approval of the unreadable-body restoration risk, the active-
slot native gate probe completed `MEASURED_AND_RESTORED`. Every gate off / on /
off body was written while global slot 3 was active, followed by a forced
2 -> 3 recall edge. Classification:
`NO_NATIVE_ACTIVE_SLOT_GATE_EFFECT_DETECTED`.

Gate-on changed the stable Main/Input-2 ratio by -0.068913 dB; off-to-off drift
was +0.112856 dB and maximum window MAD was 0.349676 dB. The pinned native
Piano body was rewritten while slot 3 was active. All readable controls match
before/after exactly, battery remained 99%, and postflight identity remained
`194f:0422`, firmware `0x0128`. The stored body remains unreadable, so its
restoration is write-sent, not read-back proven. Report SHA-256:
`be5e19f27c703368a52ca3a0e460872fb3ae80b9baba1dff07040de22cc6d46d`.

Inactive-slot timing is therefore rejected as the explanation for the earlier
native nulls. Stop `Stat` body variants; continue with UC's distinct explicit
Store/assignment route (`PrsM`) or a newly captured known command.

## Static result

Firmware storage boundary is now source-bound through the concrete physical
interface. The device initialization path passes `device+8` into the singleton
used by the `Stat` write adapter; the adapter reloads the same stored pointer
before device-vtable query `0x20808`, which resolves the physical interface.
Backend flag `1` means compare-before-program. Changed bytes run through
program transaction `0x526dc` and then ready poll `0x52a70` before the write
can return success. No separate post-write commit edge exists on this path.

Independent review found that the initial analyzer pinned the adapter and
physical-interface halves without pinning their receiver-data-flow join. The
correction now anchors `0x20d3c -> 0x3d4bc`, singleton field `+0x38`, and
`0x316dc/0x316b0 -> device vtable +0x10` with exact slices, instructions,
literal, and branch targets.

Result:
`FIRMWARE_STAT_PHYSICAL_BACKEND_SOURCE_BOUND_SYNCHRONOUS_COMPARE_PROGRAM_NO_SEPARATE_COMMIT`.

The remaining live boundary is narrower: `SetP` exposes no readable storage
result, so transport completion does not reveal whether the firmware's physical
write returned success or what bytes are actually stored.

## Verification so far

- physical-backend analyzer TDD: 2/2 passed;
- independent-review receiver-join correction: 2/2 passed;
- direct analyzer execution on the pinned application: passed;
- active-slot runner TDD: 3/3 passed;
- dry-run: passed;
- final six-module focused regression: 18/18 passed;
- direct analyzer, bytecode compile, and `git diff --check`: passed;
- preflight battery: 99%, not charging;
- pinned firmware image: exact SHA-256 match.

## Superseded live gate record

The execution request was rejected before process launch because the device
cannot read slot bodies back. Selecting slot 3 and overwriting it while active
would therefore have only a pinned-body rewrite—not verified restoration—if
the test failed. No USB write or other device mutation occurred. `lsusb`
read-only identity was `194f:0422` immediately before the rejected request.
A subsequent read-only Host status succeeded at protocol 1 and showed Channel
2 gain 24.29 dB, main 0.760, headphones 0.510, and both phantom supplies off.

Exact approval would need to acknowledge this risk: overwrite global slot 3
while it is active with native gate-off/on/off bodies, then restore it by
writing the pinned native Piano body while active, despite unavailable slot-body
readback.

The user supplied that exact approval and the result is recorded above. This
section is retained as pre-execution provenance.
