# CP33 Task 5 fix round 1 re-review package

- Current rubric: `../task-5-review-rubric.md` (R64-R73), SHA-256
  `938fb49f6472402981d82f788b6cdaa0f313a3def3b482a294a72b7bd1d778ac`.
- Round-0 verdict: `task-5-review-round-0.md` (FAIL), SHA-256
  `c751d55e8b0dcaf391be5e3c2d95c7517d6398d0df7c66905bd20d8d58505630`.
- Frozen failed head: `../task-5-head`, manifest `task-5-head.sha256`.
- Fix head: `../task-5-round-1-head`, manifest
  `task-5-round-1-head.sha256`.
- Three-file fix diff: `task-5-round-1.diff` (202 lines), SHA-256
  `8ad1186804bc91c999ed2b8536e0ac2cac590a98800cb27ed559b629d762432b`.
- Plan/spec SHA-256 remain `013feee53959cd8efdf5a13e6a83ffacf2a6517f43def0566ed95f534b0fe981`
  and `8d04b44c89860b34afe0560caa9fa83c12aa80ca1e49f93734ce899dd56294a7`.

## Round-0 finding and correction

Round 0 found that nonfinal Free retained every associated record until final
root destruction, causing linear memory growth under a long-lived default
handle. Fix round 1 separates public identity from record storage:

- a process-global registry-locked odd token is returned instead of the heap
  record address;
- the counter never returns zero or `INVALID_HANDLE_VALUE`, never wraps, and
  returns `ERROR_NOT_ENOUGH_MEMORY` with balanced rollback on exhaustion;
- lookup compares only the opaque token before any caller-value dereference;
- Free immediately reclaims a zero-API-reference record, while the last
  admitted release reclaims a deferred record before dropping the root
  reference that may wake the finalizer;
- the one final synchronous RELEASE, root drain, snapshot/slot cleanup, lock
  order, and caller-device nonownership remain unchanged.

Final bounded hashes:

```text
8f4144b2f540f05c16a53bf4f49f1ea29455e30effb2589818ea13a3cc64d753  dlls/winusb/main.c
4be97b07b4f091619a9c5c86b42a33af31976ffbaf61c7576d42c0a15626a1c0  dlls/winusb/winusb_private.h
2588b4bfcce2bf465c8a80b9f7dd50bc2e77c4e3db0d699c426ecf8a154cf6fd  tests/winusb_user_api_contract.c
f601c75e890afb48771f77e976041139ee33e3ce4331cb380c1e601af9bf4ebc  tests/winusb_user_api_contract.sh
```

## Test-first evidence

The final contract adds a 32-cycle associated issue/free stress case while the
default root stays live. Every cycle must restore the post-initialize
outstanding-allocation baseline; all returned tokens must be pairwise distinct,
nonzero, and not `INVALID_HANDLE_VALUE`; final default Free must issue one
RELEASE and balance all storage.

Against immutable pre-fix production (`79d52561...` / `d3dee379...`):

```text
CP33 public executed mode=--handles target-mask=0x8c present-mask=0x19c missing-mask=0 fake-events=18 submits=3 releases=1 completions=0 failures=32
exit_code 1
```

Authoritative log: `re/winusb-api-v1/logs/task-05-handles-red-fix-round-1-final.log`,
SHA-256 `66d47d72796190f93de5be1f0c766499822d6a3c88112e78eabf30602c0f6fbb`.

## Fresh controller GREEN

All eight offline gates exited zero:

```text
handles:             failures=0, submits=3, releases=1
descriptors:         failures=0, submits=3, releases=1
user initialize:     failures=0, submits=3, releases=1
surface:             native, m32 unavailable, exports=14, stubs=8
function lifecycle:  dispatches=12, failures=0
function initialize: dispatches=4, mode-ioctls=1, last=0x222002/status=0, failures=0
metadata bus:        pass
binding:             pass
```

The eight `gate-1-round-1-*.log` hashes are bound in the eventual Gate-1 seal.

## Executable mutation lenses

Every final-head mutation compiles and exits as a genuine feature failure:

```text
pre-registry dereference:    exit 1, failures=3
missing final wait:          exit 1, failures=1
associated without +1:       exit 1, failures=572
partial short copy:          exit 1, failures=1
speed length/tail overrun:   exit 1, failures=2
missing retired reclaim:     exit 1, failures=34
token reuse:                 exit 1, failures=530
invalid token plus wrap:     exit 1, failures=1
```

One-hunk/two-hunk mutation diffs are in `task-5-round-1-mutations/`; matching
execution logs are `re/winusb-api-v1/logs/gate-1-round-1-mutation-*.log`.
The exact 16-file diff/log set verifies through
`task-5-round-1-mutations.sha256`, SHA-256
`fdeed9e14d645dd2079f19e287a07fe4a17b3dd5a2a63106e319c180d7765d2f`.

## Integrity and review request

```text
failed-head manifest: 6b4cef6742a4d47850b96943dee7c42c59e9ec994b3ece3fc5425194dcb1942a
fix-head manifest:    badd96e9cdc05ab96fba67b2a91d753d41bbc6abd99ff43c2ae0474b7279ec4a
entries:              3/3 in each, all verified
workspace vs fix head: 3/3 byte-identical
fix diff headers:     exactly 3
```

Judge the round-0 Important finding ADDRESSED or NOT ADDRESSED, then report any
new Critical, Important, or Minor correctness or executable-proof finding.
Review is read-only. Do not use Git, run Wine or a contained/full build, touch a
prefix or device/live USB path, install anything, or perform physical actions.
