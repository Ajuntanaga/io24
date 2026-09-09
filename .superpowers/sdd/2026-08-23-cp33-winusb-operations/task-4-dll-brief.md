# CP33 Task 4 DLL-half implementation brief

This is the user-mode half of approved Task 4. The authoritative plan/spec and
controller rulings R26–R63 apply. The frozen base is `task-4-base`; do not edit
the kernel half, controller evidence, ledger, snapshots, plan, or
specification.

## Owned paths

- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/Makefile.in`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c`
- new `.io24-build/winusb-api-v1/dev-source/dlls/winusb/winusb_private.h`
- `tests/winusb_user_api_contract.c`
- narrowly expanded `tests/winusb_user_api_contract.sh`
- report only: `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-dll-report.md`

## Test-first boundary

Expand `--initialize` before production edits and retain genuine feature RED
against the compiled actual `winusb.dll` source. The fake Win32/NT boundary
must drive the real exported `WinUsb_Initialize`; caller-authored traces or
source-text assertions do not count.

R32 authorizes the wrapper only to link the actual production source together
with (or otherwise resolve it against) the existing fake boundary so hidden
Wine Win32/NT imports execute through those fakes. Preserve every mode and
feature-1/harness-2 rule. Do not add a production test seam, omit `main.c`,
accept unresolved load failures, or turn behavior into source scanning.

Cover at minimum:

- null output pointer; null, invalid, unqueryable, and both synchronous-mode
  input handles; output-null publication on every failure and exact last error;
- successful `NtQueryInformationFile(FileModeInformation)` only for a valid
  overlapped handle; no duplicate/close of the caller handle;
- private synchronous event/OVERLAPPED behavior for immediate success,
  `ERROR_IO_PENDING` plus completion, event/allocation failure, IOCTL failure,
  and failed completion;
- first initialize request: exact 24-byte zero-session input and exactly
  72-byte output; false API result with the exact insufficient-buffer mapping,
  completion bytes 72, and a validated `STATUS_BUFFER_TOO_SMALL` header with
  session zero and retained-fixture `total_size=211`; allocate exactly 211;
  second exact request and full response;
- independent rejection of bad version/size/total/returned byte count,
  offset add/multiply overflow, any range outside 211, overlap or disorder,
  wrong device/config lengths/types/`wTotalLength`, missing interface/default
  alternate, duplicate/unordered alternates, and invalid endpoint indices;
- zero release for every precommit failure; exactly one release carrying the
  returned nonzero session for every postcommit parse/allocation/publication
  rejection; no partially published handle and no caller-handle close;
- exact successful MI05 header and record layout from R27, cached speed 0x03,
  and a fully owned default root/interface object published only after
  validation.

## Production invariants

- Set `*InterfaceHandle = NULL` before input-handle validation. A null output
  pointer uses `ERROR_INVALID_PARAMETER`; invalid/unqueryable/synchronous
  handles use `ERROR_INVALID_HANDLE`.
- Query `FileModeInformation` using `NtQueryInformationFile`; reject
  `FILE_SYNCHRONOUS_IO_ALERT` and `FILE_SYNCHRONOUS_IO_NONALERT`.
- Use the original caller handle for both IOCTLs and release. A private event
  and local `OVERLAPPED` are permitted only for the synchronous public call;
  never duplicate or close the caller handle.
- Use the exact Task 2 ABI and checked arithmetic. Validate the returned
  snapshot independently and generically before constructing or publishing
  objects. Production must not hardcode R27's MI05 size, speed, offsets,
  interface number, or endpoint set; those are fixture assertions in tests.
- Snapshot arrays may be unaligned (R27 offsets 131/147/179). Copy records to
  aligned locals with `memcpy` or decode bytes; never dereference a cast record
  pointer. Add an executable alignment-sanitizer witness or equivalent trap.
- Submit rollback and successful RELEASE through the same private-event/local
  `OVERLAPPED` synchronous helper as initialization, never a NULL-overlapped
  call on the caller's overlapped handle.
- Task 4 may provide the minimum valid-default-handle `WinUsb_Free` cleanup
  needed to release a successfully initialized root exactly once. Task 5 owns
  registry-backed arbitrary/stale/associated/concurrent handle safety and the
  completion claim; do not weaken or pre-claim that work.
- The DLL Makefile records the imports needed by the implemented NT/Win32
  calls. Do not create `io.c`; Task 7 owns it.

## Gates and handoff

Run at minimum:

```bash
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
```

Do not create Task 4 patch/hash evidence. Append exact RED/GREEN commands,
outputs, changed paths, release accounting, and concerns to the DLL report.
