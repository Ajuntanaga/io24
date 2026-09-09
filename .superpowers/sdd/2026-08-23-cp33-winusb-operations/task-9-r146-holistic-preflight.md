# Task 9 R146 holistic and cybersecurity preauthorization review

Timestamp: 2026-08-25

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: three.

Material Minor findings: one.

## Important 1: self-referential device-handle authority

`expect_control_endpoint_reject()` compares the journaled handle with
`f->device.handle` only after production returns. It neither snapshots the
authoritative pre-call handle nor requires the fixture device to remain
unchanged.

In disposable `/tmp/io24-r146-holistic.hgCKjQ`, production first replaced
`params->device->handle` with non-null `0x4444`, then used that handle for
the retained three-call validator. The mutated fixture and journal agreed
after return, so actual copied production passed focused execution at exit 0
with `failures=0`.

## Important 2: descriptor use-after-free

The reviewer independently moved the correct descriptor free to immediately
after lookup and left descriptor traversal afterward. Call counts, order, and
pointer lineage remained exact. Fake free did not invalidate the descriptor,
so copied production compiled and passed at exit 0 with zero failures.

## Important 3: reject helpers omit caller-visible preservation

The endpoint and generic rejection helpers do not snapshot or assert
`UrbHeader.Status`, `TransferBufferLength`, or caller storage/guards.

Two independent copied-production mutants retained the expected return and
backend behavior while writing caller byte `0x6d`, changing transfer length
from 0 to 1, and setting URB status to `USBD_STATUS_SUCCESS`:

- endpoint rejection after the correct three-call authority sequence;
- oversized generic pre-backend rejection.

Both compiled actual production through fake libusb and passed focused
execution at exit 0 with zero failures.

## Material Minor: active-config witness is not first executable operation

The fake initializes `result=NULL` before
`IO24_FAKE_API_CALL()`. Independent disassembly confirmed the stack zero
store occurs before the global counter increment. The dedicated increment is
immediately after the witness, but the implementation does not meet the sealed
first-executable-operation requirement.

## Strengths and checks

The reviewer verified the 12/12 manifest, exact patch hash and scope, patch
dry-run, live R139/fake identities, disposable candidate hashes, active/pre-edit
production lineage, focused and retained baselines, identical count/record
layouts and reset, 32 compiled fake exports, 33 macro references including the
definition, and correct rejection of mutants 17-19. No secret, dependency,
network, device, prefix, staging, firmware, preset/effect, or deployed surface
was added.

Commands included `sha256sum -c`, direct hashes, patch dry-run/path/numstat,
disposable application, harness replays, `nm`, `rg`, `objdump`, bounded
surface scans, and six independent production mutations. Final disposable
production was restored to `ba3172e...d53051`; no workspace file was edited.

