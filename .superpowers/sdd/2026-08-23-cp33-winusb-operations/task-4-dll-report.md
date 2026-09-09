# Task 4 DLL half report

## Frozen base

`sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/reviews/task-4-base.sha256`
verified the controller-expanded twelve frozen present paths before this half was edited.

## TDD

Feature RED, after expanding the compiled host fake to require the two-step
initialize path:

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x4 missing-mask=0x80 fake-events=0 submits=0 releases=0 completions=0 failures=2
```

This is a feature exit 1 from the absent `WinUsb_Initialize`, not a harness
failure. `--surface-only` remained green before implementation.

## Current implementation boundary

The DLL half adds a private root object, overlapped-handle mode query, private
event/local OVERLAPPED submission, the exact 72 then 211 initialize shape,
fixed MI05 snapshot validation, one postcommit release, and minimal valid
default-handle free/release cleanup.

The prescribed GREEN is currently blocked at the pre-existing unowned wrapper
link boundary: it builds `main.c` as a standalone shared object before the
host fake is linked, while Wine declarations give `DeviceIoControl`, heap,
event, and `NtQueryInformationFile` hidden import visibility. The ELF linker
therefore rejects their currently-unresolved hidden references. No wrapper was
edited because DLL ownership excludes it; controller ruling is required for a
narrow host-fake/link arrangement.

`--surface-only` still reports:

```
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

## Correction chunk A

The fake now constructs the unaligned wire records in aligned local ABI
objects and copies their bytes into the R27 offsets; it no longer writes
through unaligned typed pointers. `--initialize` compiles and links with the
mode-scoped undefined/alignment sanitizer and completed without a sanitizer
diagnostic:

```
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=3 completions=0 failures=0
```

`submit_request` captures errors before wait/completion/close, requires a
signaled private event for pending calls, and only admits a false,
insufficient-buffer, 72-byte size completion. Normal and release requests
require true completion.

## R32 link arrangement and focused rerun

R32 adds the user wrapper to this half. It now compiles the real production
`dlls/winusb/main.c` and the existing host-fake contract as objects in the
same executable, links that executable with `-rdynamic`, and loads its own
global symbol table with `dlopen(NULL, ...)`. Thus the actual production
exports execute against the existing fake Win32/NT functions; no production
seam, omitted source, source scan, or unresolved shared object is accepted.

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=11 submits=3 releases=2 completions=0 failures=0

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

## DLL fix round 2 (R53-R55)

The sizing header restores the exact `72 + UINT16_MAX` cap. Full-request
transport errors are saved before `HeapFree` and restored afterwards; the host
heap/close fakes deliberately clobber last error to prove that boundary. A
pending sizing completion that unexpectedly succeeds maps to the local
protocol error `ERROR_BAD_DEVICE`.

The initialize matrix now includes a self-consistent over-cap header, raw
alt1-before-alt0 and matched raw/packed duplicate-endpoint counterexamples,
NT-success with bad `IO_STATUS_BLOCK` status/information, immediate and
pending full failures/success, and immediate/pending/event/wait release paths.
Each observed release is checked for the original device, exact live request,
private event/overlapped identity, and one matching close.

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=0

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

Changed owned paths are the DLL Makefile/main/private header, user contract,
user wrapper, and this report.

## Historical residual review blockers (superseded)

The focused host command is green, but independent audit findings remain to be
corrected before controller acceptance: the size-query fake/submit path must
model the expected false insufficient-buffer result, release must use the
private synchronous event/OVERLAPPED path, and snapshot validation must become
generic checked bounded validation rather than fixing all MI05 fixture values.

## Correction round R36-R38

The sizing fake now returns false with `ERROR_INSUFFICIENT_BUFFER` while
retaining the 72-byte header and completion count; production accepts that
outcome only for the size query. Private RELEASE now reuses the local-event
submission helper for both rollback and `WinUsb_Free`. Snapshot validation now
uses ABI-provided bounded fields rather than fixed fixture size/speed/offset
values, and copies unaligned record bytes into aligned locals before reading
them.

The focused rerun remained:

```
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=3 completions=0 failures=0
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

## Release and ownership accounting

Precommit failures (mode validation, size-query validation, full IOCTL
failure) send no release. After the second response, validation or root
allocation failure emits exactly one `IOCTL_WINE_WINUSB_RELEASE` with the
returned session. The caller handle is never duplicated or closed; the private
event alone is closed. The minimal `WinUsb_Free` sends one release for a valid
published default object, then frees snapshot/object storage.

## Correction round R39-R45

The private helper captures the error before any wait, completion, or close.
An immediate failed sizing request reads completion information from local
`OVERLAPPED.InternalHigh`, not `lpBytesReturned`; a pending request requires
`WAIT_OBJECT_0` and successful completion. Only false
`ERROR_INSUFFICIENT_BUFFER` with exactly 72 bytes is accepted for sizing.

The validator is now generic and bounded: full response information must match
the header allocation total, only canonical low/high speeds are accepted, all
packed records are copied with `memcpy`, and descriptor/region/alternate/
endpoint relationships are cross-checked. The fixture uses bulk type `2` and
512-byte packets. The executable matrix mutates header, region, descriptor,
interface, alternate, endpoint, and raw endpoint fields; it also distinguishes
first and second allocation failures, with the latter rolling back once while
preserving `ERROR_NOT_ENOUGH_MEMORY`. A separate valid non-MI05 low-speed
fixture (interface 2, interrupt endpoint `0x82`, 64-byte packet) proves that
the validator is not tied to the retained MI05 topology.

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=14 submits=3 releases=0 completions=1 failures=0

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

No Wine process, prefix, device, sysfs, build, or live interface action was
used.

## DLL fix round 1 (R49-R52)

Private transport errors now survive private-event cleanup: creation, immediate
IOCTL, wait, and pending-completion failures retain their meaningful error;
only local protocol/snapshot failures map to `ERROR_BAD_DEVICE`. The 72-byte
header is independently validated before allocation and frozen; the full body
must match every sizing metadata field except its nonzero session. Raw USB
interface records are consumed in configuration order, with strict alternate
order/default-zero and per-alternate endpoint-address uniqueness.

The initialize contract now exercises header-only precommit mutations, both
synchronous file flags and `INVALID_HANDLE_VALUE`, event/IOCTL/wait/pending
failures, and exact private RELEASE shape. The wrapper compiles every collected
production source separately and links all objects; the terminal release
counter now reports actual RELEASE IOCTLs.

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=14 submits=3 releases=1 completions=1 failures=0

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

## DLL fix round 3 (R56-R57, contract-only)

Production and the wrapper remained frozen. The full-mutation loop now executes
both raw-order and duplicate-pipe cases. The duplicate raw mutation changes the
second endpoint descriptor's `bEndpointAddress` byte (54), while changing its
matching packed endpoint record; it leaves the descriptor length intact. These
two executed counterexamples reject publication with one rollback release, so
removing either actual production check makes the focused contract fail.

Pending RELEASE cases now require exactly one `GetOverlappedResult`, bound to
the original device and the same private `OVERLAPPED` recorded for RELEASE,
with the scheduled result/error. Immediate and wait-failed RELEASE paths prove
zero completions.

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=0

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8

sha256sum tests/winusb_user_api_contract.c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-dll-report.md
e529b957ac7038bc3d3d0fed2c9902e123ad427f0a61178211c13751ad45cae2  tests/winusb_user_api_contract.c
```

Only the user host contract and this report changed; no Wine, prefix, device,
build matrix, evidence, or live action was used.

## Combined fix round 1 (R58-R60)

The raw configuration parser now preserves contiguous interface-group order and
rejects only a repeated interface number found in an earlier packed group.
Thus the valid raw descending sequence `[5 alt0, 2 alt0]` is accepted, while a
second group numbered `5` is rejected after the full response and rolled back.
Endpoint-address uniqueness remains scoped to one alternate, so `0x81` reused
by two distinct alternates is accepted.

For a failed private wait, `submit_request` saves the exact `WAIT_FAILED`
error before event cleanup; other unexpected wait outcomes retain the local
generic error. The executable fake now makes `CloseHandle` clobber last error
and sets `WAIT_FAILED` to `ERROR_ACCESS_DENIED`, proving the saved error reaches
the caller.

The fake records the sizing header, the second INITIALIZE output length, and
the snapshot allocation. The success path asserts both latter sizes equal the
first header's advertised `total_size` (211 for MI05, 181 for descending).

RED before the production correction:

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=2
exit=1
```

GREEN after the correction:

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=0

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

R60 mutation proof used the disposable exact path
`/tmp/io24-cp33-r60.HNE64d/dev-source`, changed only the second production
INITIALIZE output argument from `header.total_size` to `header.total_size + 1`,
and then removed that temporary tree. The focused contract produced the
expected feature exit 1 (not harness exit 2):

```
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=7
mutation_exit=1
```

Changed scope versus immutable `task-4-head` is exactly the assigned DLL
production source, user host contract, and this report. Pre-report hashes:

```
6a2ea0ae74185fffbbb81f957bd0af83bda3f044e9212927b8d71920ba700876  dlls/winusb/main.c
6e533ef07acb7dce93014938824f1b89985a460e9b056943a2f0eb1eeeb78859  tests/winusb_user_api_contract.c
```

The report's final SHA-256 is recorded by the completion scope check.

## Combined fix round 2 (R61-R63, contract-only)

All valid initialization fixtures now go through `initialize_handle`, one
shared helper that reads the first sizing header and requires the exact
successful snapshot allocation pointer to be the second INITIALIZE output
pointer. It also requires both the allocation and second output lengths to
equal the advertised total. The executed valid totals are 211 (MI05 and the
cross-alternate endpoint-reuse fixture), 181 (descending `[5,2]`), and 163
(low-speed fixture).

The full-response matrix adds matching raw/packed nonadjacent duplicate
groups `[5,2,5]`; it rejects after the full response with exactly one release.
The fake records the exact `WaitForSingleObject` handle. Two distinct failed
wait results (`ERROR_ACCESS_DENIED` and `ERROR_INVALID_HANDLE`) are checked
through close cleanup, and both INITIALIZE and RELEASE wait paths require the
request's private event identity.

Normal host results:

```
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=0

tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

Four independently copied source roots under the disposable exact parent
`/tmp/io24-cp33-r61-r63.It0f2O` established executable mutation coverage;
the complete parent was then removed. All results are feature failures, never
harness failures:

```
previous-record-only uniqueness: failures=2, exit=1
hardcoded wait error:             failures=4, exit=1
wrong private wait handle:        failures=3, exit=1
non-211 allocation/output +1:     failures=2, exit=1
```

The final mutation changes both allocation and second INITIALIZE output to
`header.total_size + (header.total_size != 211)`, so the 181/163 valid
fixture paths—not the retained 211 path—prove the generalized size checks.
The production DLL remained the frozen SHA-256
`6a2ea0ae74185fffbbb81f957bd0af83bda3f044e9212927b8d71920ba700876`.
The implementer-owned scope relative to `task-4-round-1-head` was exactly this
contract and this report; no wrapper or production file changed. The controller
subsequently regenerated the patch/seal and froze them with the contract in
`task-4-round-2-head`.

Pre-report contract SHA-256:

```
a71eb6e0214656e2863b6555e03580057f834a412f3271e26b70179ecab593f3  tests/winusb_user_api_contract.c
```

## Pre-review helper robustness correction

`initialize_handle` now requires both the sizing and full INITIALIZE events to
exist before it dereferences the full event's output pointer. A missing second
request therefore records a contract feature assertion rather than risking a
test-process fault. The pointer-identity and exact-size assertions run
unchanged once both events are present.

```
CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x84 missing-mask=0 fake-events=13 submits=3 releases=1 completions=0 failures=0
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

Post-correction contract SHA-256:

```
badf5808b4ca99ec0334bb315c8b4165f304c9458ce865bbc10a1a14ff49abdc  tests/winusb_user_api_contract.c
```

## Controller mutation reproduction

The controller independently reproduced all four R61-R63 production-copy
mutations after the robustness correction. Each exited feature status 1 and
each exact temporary tree was removed:

```text
previous-record-only uniqueness: failures=2, exit=1
hardcoded wait error:             failures=2, exit=1
wrong private wait handle:        failures=3, exit=1
conditional non-211 size +1:      failures=2, exit=1
```

A fifth isolated allocation-identity mutation allocated a disposable
advertised-size block, used a distinct `total_size + 1` block as the actual
181-byte full-output buffer, freed the disposable block, and submitted the
correct 181-byte output length. It exited feature status 1 with `failures=1`.
This distinguishes pointer identity from a size-only search that could accept
an unrelated allocation. Its exact temporary tree was also removed.
