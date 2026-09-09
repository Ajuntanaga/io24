# CP33 Task 2 implementation report

## Status

DONE. The public WinUSB surface, exact fourteen real exports, eight retained
stubs, and pointer-free private ABI v1 are defined in the five R13 production
paths. The R11 test carry was closed before any production edit, and the R12
surface-only wrapper mode distinguishes feature failure (exit 1) from harness
failure (exit 2).

Commits: n/a (non-Git workspace).

## Implementation summary

- Hardened the fake `DeviceIoControl` boundary to record its
  `lpBytesReturned` pointer. The focused policy test asserts that pointer does
  not alias the public caller's `ValueLength` pointer. The independent 8-byte
  policy probe still observes an 8-to-4 return, while the frozen vendor
  policy-8 input capacity is explicitly fixed at 4 bytes.
- Added compile-time public/private assertions before production changes.
  They validate every required size and offset, every fixed-width leaf type,
  all public constant values, all private caps, all twelve IOCTL
  function/method pairs, and all fourteen exact public prototypes.
- Added `--surface-only` to the public contract wrapper. It source-checks the
  exact 14/8 export split and public installation, then compiles the real
  public/private headers with `-std=c11 -Wall -Wextra -Werror`. Feature
  deficiencies return 1; missing harness inputs, build failures outside this
  surface preflight, and abnormal contract exits return 2.
- Added the policy and speed definitions, exact eight-byte
  `WINUSB_SETUP_PACKET`, and fourteen public prototypes. `winusbio.h` is in
  the public include install list.
- Added private ABI v1 with the exact `0x800` through `0x80b` IOCTL methods,
  R14's three 16-byte snapshot records, the 24-byte common request, 72-byte
  snapshot, two 32-byte requests, and three 40-byte requests. Request payloads
  embed the common header and use fixed-width integer leaves only.
- Converted exactly fourteen spec entries to `stdcall`, including `int64` for
  `WinUsb_ControlTransfer`'s by-value setup packet. The other eight names are
  still explicit stubs.

## TDD evidence

### R11 hardening RED before production

Command:

```bash
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --policy
```

Relevant output on untouched Task 2 production:

```text
CP33 public executed mode=--policy target-mask=0x18c0 present-mask=0x4 missing-mask=0x18c0 fake-events=0 submits=0 releases=0 completions=0 failures=5
```

Exit: 1 (feature RED). This was neither usage/missing-input/harness exit 2 nor
a compiler failure or crash.

### Compile-time surface/ABI RED before production

Command exactly as required:

```bash
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source
```

Relevant output:

```text
FEATURE: missing public/private ABI input: .io24-build/winusb-api-v1/dev-source/include/winusbio.h
FEATURE: missing public/private ABI input: .io24-build/winusb-api-v1/dev-source/include/wine/winusb.h
FEATURE: WINUSB_SETUP_PACKET is absent
FEATURE: public prototype absent: WinUsb_AbortPipe
FEATURE: public prototype absent: WinUsb_WritePipe
FEATURE: real export absent: @ stdcall WinUsb_ControlTransfer(ptr int64 ptr long ptr ptr)
FEATURE: export counts real=1 stub=21 expected=14/8
FEATURE: winusbio.h is not publicly installed
```

Exit: 1 (feature RED). The wrapper exited before compilation because the
production definitions were absent, so the RED cannot be attributed to a
compiler or harness failure.

### Focused GREEN

Command:

```bash
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
```

Output and exit:

```text
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

Exit: 0. Native compilation was clean with `-std=c11 -Wall -Wextra -Werror`.
The wrapper probed `-m32`; this host lacks a usable 32-bit standard-header
compile path, so the optional second compile was reported unavailable without
installing anything.

The owned function contract also compiles cleanly with its required warning
flags. Its `--red` runtime remains intended feature RED for later CP33 driver
tasks (exit 1), not harness exit 2:

```text
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--red dispatches=3 mode-ioctls=2 last-ioctl=0x222022 last-status=0xffffffffc00000bb failures=27
```

## Retained CP32 tests

```bash
tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source
```

```text
WineUSB WinUSB metadata bus-interface contract: pass
```

```bash
tests/winusb_function_binding_contract.sh .io24-build/winusb-api-v1/dev-source
```

```text
CP32 winusb function-binding lifecycle checks passed
```

```bash
python3 tests/winusb_function_binding_inf_contract.py --wine-source .io24-build/winusb-api-v1/dev-source
```

```text
CP32 WinUSB function-binding INF contract: pass
```

All three commands exited 0.

## Files changed

Production (the five R13 paths only):

- `.io24-build/winusb-api-v1/dev-source/include/winusb.h`
- `.io24-build/winusb-api-v1/dev-source/include/winusbio.h` (new)
- `.io24-build/winusb-api-v1/dev-source/include/wine/winusb.h` (new, private)
- `.io24-build/winusb-api-v1/dev-source/include/Makefile.in`
- `.io24-build/winusb-api-v1/dev-source/dlls/winusb/winusb.spec`

Tests and wrapper:

- `tests/winusb_user_api_contract.c`
- `tests/winusb_function_io_contract.c`
- `tests/winusb_user_api_contract.sh`

Evidence and report:

- `re/winusb-api-v1/logs/task-02-abi.patch`
- `re/winusb-api-v1/logs/task-02-abi.sha256`
- `.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-2-report.md`

No other path was edited. In particular,
`dlls/winusb/Makefile.in` remains byte-identical to the immutable CP32-derived
base for Task 4.

## Evidence hashes and verification

The timestamp-free unified patch was generated from the immutable
CP32-derived `patch-check-source` base with explicit labels. Its five deltas
are exactly:

```text
a/include/winusb.h -> b/include/winusb.h
/dev/null -> b/include/winusbio.h
/dev/null -> b/include/wine/winusb.h
a/include/Makefile.in -> b/include/Makefile.in
a/dlls/winusb/winusb.spec -> b/dlls/winusb/winusb.spec
```

Hashes:

```text
049afb59966dd679dab6270b99ee5437b9a04775319a3d86c33d6f71ea14fc82  re/winusb-api-v1/logs/task-02-abi.patch
d15d4508f17437c9793b150b96dd3e662a4b1a3f8780a03100f090ef248606f1  re/winusb-api-v1/logs/task-02-abi.sha256
```

Immediate verification:

```text
re/winusb-api-v1/logs/task-02-abi.patch: OK
tests/winusb_user_api_contract.c: OK
tests/winusb_function_io_contract.c: OK
tests/winusb_user_api_contract.sh: OK
```

`patch --dry-run -p1` against the immutable CP32-derived patch-check tree also
passed without output or mutation.

## Self-review

- Public constants, packet fields, types, offsets, sizes, and fourteen
  prototypes are asserted from the production headers. The control function
  pointer in the executed contract now also passes the setup packet by value.
- The private records match R14 exactly. The required sizes are
  24/72/16/16/16/32/32/40/40/40, and the declared leaves are only `UINT8`,
  `UINT32`, `UINT64`, or an array of `UINT8`/`UINT32`. There are no pointers,
  handles, native-width integers, enums, bitfields, or flexible arrays.
- Each IOCTL function code `0x800` through `0x80b` appears once in the private
  header, with the exact buffered/direct method. `METHOD_NEITHER` is absent.
- The spec audit found exactly fourteen `stdcall` entries and eight explicit
  stubs; the setup packet uses `int64`.
- `include/Makefile.in` installs `winusbio.h` but does not install
  `wine/winusb.h`.
- The metadata bus-interface v1 header and implementation are byte-identical
  to the immutable base. The Task 4 DLL Makefile is also byte-identical.
- The evidence patch contains only the five production paths, uses `/dev/null`
  for both new files, has stable labels without timestamps, verifies by hash,
  and applies in dry-run.
- No Git operation, Wine invocation, prefix access, device/sysfs access,
  driver action, application start, physical USB operation, installation,
  contained full build/matrix, or CP24 retry occurred.

## Concerns

No implementation blocker or known ABI concern. Optional 32-bit layout
compilation could not run because this host's `-m32` standard-header capability
probe failed; native compile-time layout checks passed, and no tools were
installed. Public/function runtime operations remain intentionally
unimplemented for later CP33 tasks; Task 2 proves declarations, layouts,
exports, and retained CP32 compatibility only.

## Fix round 1: review Important findings

Fix base: sealed `task-2-head`. Production was not changed. The two deferred
minor findings were not addressed.

### Finding 1: harness failures could masquerade as feature RED

Changed only `tests/winusb_user_api_contract.sh`:

- Added availability checks for `awk`, `cc`, `dirname`, `find`, `grep`,
  `mktemp`, and `rmdir` before use, plus functional known-good baselines for
  `grep` and `awk`.
- Added `include/Makefile.in` to the regular/readable required-input preflight.
  Existing ABI inputs must also be regular and readable; absent
  not-yet-implemented ABI inputs remain a genuine feature condition.
- Wrapped every `grep` and `awk`: no-match is feature exit 1, while tool/read
  failure is HARNESS exit 2.
- Added a known-good native compiler/standard-header/Wine-header baseline.
  Missing/broken compilers, absent standard headers, and failed baselines are
  HARNESS exit 2.
- Candidate status 1 is feature rejection only with a recognized compiler
  diagnostic. Abnormal status, internal tool failures, unreadable diagnostics,
  and diagnostic-free failure are HARNESS exit 2.
- Applied the same distinction to optional `-m32`: known missing multilib
  headers/options mean unavailable; abnormal probe failure is HARNESS exit 2.

Normal surface command:

```bash
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
```

```text
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
```

Exit: 0.

The historical pre-production RED remains reproducible:

```bash
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/patch-check-source
```

```text
FEATURE: missing public/private ABI input: .io24-build/winusb-api-v1/patch-check-source/include/winusbio.h
FEATURE: missing public/private ABI input: .io24-build/winusb-api-v1/patch-check-source/include/wine/winusb.h
FEATURE: WINUSB_SETUP_PACKET is absent
FEATURE: export counts real=1 stub=21 expected=14/8
FEATURE: winusbio.h is not publicly installed
```

Exit: 1, never HARNESS 2.

Current default public feature behavior is unchanged:

```bash
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source
```

```text
CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8
CP33 public executed mode=--red target-mask=0x3fff present-mask=0x4 missing-mask=0x3ffb fake-events=0 submits=0 releases=0 completions=0 failures=21
```

Exit: 1.

Fresh `/tmp` missing-compiler PATH fixture:

```text
NO_CC_EXIT=2
HARNESS: required tool unavailable: cc
```

Executable but broken baseline `cc` fixture:

```text
BROKEN_CC_EXIT=2
HARNESS: native compiler/standard-header baseline failed with status 1
synthetic compiler failure
```

Broken `grep` and `awk` executable fixtures are also HARNESS 2:

```text
BROKEN_GREP_EXIT=2
HARNESS: grep baseline failed with status 1
BROKEN_AWK_EXIT=2
HARNESS: awk baseline failed with status 1
```

Compiler fixture that delegates the baseline to `/usr/bin/cc`, then exits 3
for the candidate:

```text
ABNORMAL_CANDIDATE_EXIT=2
HARNESS: native candidate compiler exited abnormally with status 3
synthetic abnormal candidate compiler failure
```

Unreadable required-input fixture command and result:

```bash
chmod 000 "$fixture_root/unreadable/include/Makefile.in"
tests/winusb_user_api_contract.sh "$fixture_root/unreadable" --surface-only
```

```text
UNREADABLE_INPUT_EXIT=2
HARNESS: unreadable required input: /tmp/io24-task2-harness.*/unreadable/include/Makefile.in
```

Each fixture used `mktemp -d -p /tmp`, asserted its exact exit class, and was
removed by deleting only its explicit fixture contents and root.

### Finding 2: compatible aliases could evade `_Generic`

Added an independent token-level schema to the wrapper. `awk` extracts every
`struct wine_winusb_*` declaration, normalizes whitespace only, and compares
it line-for-line with the exact R14 schema. It enforces all ten struct names,
member order, exact `UINT8`/`UINT32`/`UINT64` tokens used by this ABI, array
spellings, and only the explicitly embedded
`struct wine_winusb_request request`. Existing C size, offset, `_Generic`,
IOCTL, constant, and prototype assertions were not weakened.

Disposable compatible-alias mutation:

```bash
alias_root=$(mktemp -d -p /tmp io24-task2-alias.XXXXXX)
cp -a --reflink=auto .io24-build/winusb-api-v1/dev-source "$alias_root/source"
sed -i '0,/UINT32 size;/s//ULONG size;/' "$alias_root/source/include/wine/winusb.h"
tests/winusb_user_api_contract.sh "$alias_root/source" --surface-only
```

```text
COMPATIBLE_ALIAS_EXIT=1
FEATURE: private ABI declaration schema mismatch at line 3: actual='ULONG size;' expected='UINT32 size;'
```

Because `ULONG` is compatible with `UINT32` here, this rejection specifically
proves the token schema closes the review gap. The copy was removed afterward.

### Round-1 regression and evidence results

R11 focused policy remains feature RED exit 1:

```text
CP33 public executed mode=--policy target-mask=0x18c0 present-mask=0x4 missing-mask=0x18c0 fake-events=0 submits=0 releases=0 completions=0 failures=5
```

Function mode remains feature RED exit 1, not HARNESS 2:

```text
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--red dispatches=3 mode-ioctls=2 last-ioctl=0x222022 last-status=0xffffffffc00000bb failures=27
```

All retained CP32 checks remain exit 0:

```text
WineUSB WinUSB metadata bus-interface contract: pass
CP32 winusb function-binding lifecycle checks passed
CP32 WinUSB function-binding INF contract: pass
```

The five-production-path patch is byte-identical to `task-2-head`; only the
test seal changed:

```text
049afb59966dd679dab6270b99ee5437b9a04775319a3d86c33d6f71ea14fc82  re/winusb-api-v1/logs/task-02-abi.patch
55c98069a62727d8902af327c9543df486d2dd77ab4c2ccd00e85eef9eab0c99  re/winusb-api-v1/logs/task-02-abi.sha256
```

```text
re/winusb-api-v1/logs/task-02-abi.patch: OK
tests/winusb_user_api_contract.c: OK
tests/winusb_function_io_contract.c: OK
tests/winusb_user_api_contract.sh: OK
```

Round-1 concern: none. Optional `-m32` remains unavailable for the known
multilib-header reason; native baseline and candidate checks pass.
