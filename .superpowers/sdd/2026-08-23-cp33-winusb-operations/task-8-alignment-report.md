# CP33 Task 8 predecessor correction — packed snapshot alignment

## Purpose and scope

Task 9 consumes the public alternate/endpoint map while completing the WinUSB
observation path needed to capture Universal Control's still-unknown
preset/effect/firmware traffic.  A pre-Task-9 audit found that three helpers in
`dlls/winusb/io.c` cast byte-packed snapshot arrays at the retained unaligned
offsets to structure pointers.  That violated R38 and would make Task 9 build
on undefined behavior.

The correction owns exactly two paths:

1. `.io24-build/winusb-api-v1/dev-source/dlls/winusb/io.c`
2. `tests/winusb_user_api_contract.sh`

No Task 9 production path was changed.  No Wine, prefix, contained build,
staging, network, USB/device, alternate-setting, transfer, or firmware action
occurred.  The interface remained unplugged.

## Frozen base

`task-8-alignment-base.sha256` verifies the exact two-path Gate-2 input:

```text
057a862f69b310688f7c2e11f88dbcf2f60aefc5525d0604cbdf727236b563dd  dlls/winusb/io.c
781989250735120f7f4eb60d347c13d18541be652d6c07f97ec98ecfc87f6a4b  tests/winusb_user_api_contract.sh
```

The base-manifest SHA-256 is
`052536ad557626014d91f7914b53f4392a875f0cbdb4769ce69f19d577485d73`.

## Test-first RED

The wrapper extends its existing alignment/undefined-behavior sanitizer from
`--initialize` to `--alternate` and `--policy`, and makes sanitizer-enabled
invocations deterministic with `UBSAN_OPTIONS=halt_on_error=1` while preserving
pre-existing caller options.

Against the unchanged base production:

```text
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
EXIT=1; first diagnostic io.c:43, misaligned wine_winusb_interface_snapshot access

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --policy
EXIT=1; first diagnostic io.c:75, misaligned wine_winusb_interface_snapshot access
```

Both commands compiled and entered actual production.  Neither was a harness
exit 2, compiler failure, text scan, or unused-object result.

## Production correction

`has_alternate()`, `current_pipe()`, and `set_current_alternate()` now retain
the existing overflow-safe `snapshot_array()` bounds checks and copy each
packed interface, alternate, and endpoint record into an aligned local with
`memcpy` before field access.  `set_current_alternate()` also rejects a
malformed alternate span before indexing it.  No direct snapshot-record pointer
cast remains in these helpers.

Final owned-path hashes:

```text
c432df873bb71b6dc4e48787ae8187f0a0de9391604f22dd47f90837c8a165c7  dlls/winusb/io.c
b549bf225b46d5695717bb789853e66062a2d81d9b0e073b764e5f74c7e2348a  tests/winusb_user_api_contract.sh
```

`task-8-alignment-head.sha256` verifies both copied head paths; its own hash is
`1f51a79c63c934aee19fdc3dec7b680fe2595a6b76823a875056f13e3fd969b0`.

## Independent review

The independent Sol review returned PASS with no Critical, Important, or
material Minor finding.  It independently verified both manifests, reproduced
the base RED for `--alternate` and `--policy`, and ran current `--initialize`,
`--alternate`, `--policy`, `--handles`, and `--descriptors` to exit 0.  A
disposable one-site mutant restoring a direct record load exited feature 1 on
the alignment diagnostic with no `HARNESS:` marker.

Battery ended at 47% and charging during review, above the 10% stop boundary.

## Gate 2 reseal

The original 29-entry seal was preserved verbatim as
`re/winusb-api-v1/logs/gate-2-pre-alignment-function-pipe-state.sha256`, with
SHA-256
`63127db956be81f5c51a396967009276a12cbe4b7f9daebca6f02e5ed8c7cd36`.

Eight fresh focused logs all record `EXIT=0` under the repaired head:

```text
gate-2-alignment-function-alternate.log
gate-2-alignment-function-policy.log
gate-2-alignment-lower-alternate.log
gate-2-alignment-lower-claims.log
gate-2-alignment-public-alternate.log
gate-2-alignment-public-handles.log
gate-2-alignment-public-initialize.log
gate-2-alignment-public-policy.log
```

The replacement `gate-2-function-pipe-state.sha256` contains 29 unique,
non-self entries and verifies 29/29.  Its finalized SHA-256 is
`431d7e0d885f80d10aaa70907b61b2a7ff2f4066a5b3204a8988fcf6f908e421`.

This remains offline host-contract evidence only.  It authorizes Task 9 to
start from the repaired Gate-2 boundary; it makes no Wine runtime, Universal
Control synchronization, physical-interface, preset/effect capture, or
firmware claim.
