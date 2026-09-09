## Task 8 RED evidence — 2026-08-24

Scope: test-first RED only. Modified only `tests/winusb_function_io_contract.c`
and `tests/winusb_user_api_contract.c`; no production, wrapper, fake,
snapshot, manifest, retained log, or progress-ledger path was edited.

### Focused commands and terminal output

```text
$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --policy
FAIL group_policy:1771: status == STATUS_INVALID_PARAMETER && lower_calls == lower_before
FAIL group_policy:1773: status == STATUS_INVALID_PARAMETER && lower_calls == lower_before
FAIL group_policy:1775: status == STATUS_INVALID_PARAMETER && lower_calls == lower_before
FAIL group_policy:1779: effect.status == STATUS_SUCCESS && effect.lower_after == effect.lower_before + 1
FAIL group_policy:1783: status == STATUS_SUCCESS
FAIL group_policy:1785: status == STATUS_SUCCESS
FAIL group_policy:1787: status == STATUS_SUCCESS
FAIL group_policy:1789: status == STATUS_SUCCESS
FAIL group_policy:1790: status == STATUS_SUCCESS
FAIL group_policy:1791: status == STATUS_SUCCESS
FAIL group_policy:1792: status == STATUS_SUCCESS
FAIL group_policy:1793: status == STATUS_SUCCESS
FAIL group_policy:1795: status == STATUS_INVALID_PARAMETER
FAIL group_policy:1797: status == STATUS_SUCCESS && irp.IoStatus.Information == sizeof(input.request)
FAIL group_policy:1800: status == STATUS_INVALID_PARAMETER
FAIL group_policy:1802: status == STATUS_INVALID_PARAMETER
FAIL group_policy:1804: status == STATUS_INVALID_PARAMETER
FAIL group_policy:1808: status == STATUS_INVALID_PARAMETER
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--policy dispatches=5 mode-ioctls=2 last-ioctl=0x22200c last-status=0xffffffffc000000d failures=18
EXIT=1
```

Classification: accepted feature RED. The retained baseline passed, the real
`winusb.sys/main.c` plus separately compiled `session.c` ran through the fake
WDM boundary, and 18 policy assertions executed. It was neither a compiler nor
link failure and did not return harness exit 2.

```text
$ tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --policy
CP33 public executed mode=--policy target-mask=0x18c0 present-mask=0x99c missing-mask=0x1040 fake-events=20 submits=4 releases=1 completions=0 failures=3
EXIT=1
```

Classification: accepted feature RED. Missing `WinUsb_GetPipePolicy` and
`WinUsb_SetPipePolicy` symbols are the intended absent feature. Before that
symbol assertion, the focused mode invokes the real public initialize and
alternate paths through the existing fake (`fake-events=20`, `submits=4`,
`releases=1`), so the policy mode is not empty execution. It is not a compile,
link, prerequisite, or harness failure.

The first public attempt was rejected as invalid evidence: it dereferenced the
missing policy wrapper and exited 2/139. The test was corrected to assert the
missing feature after real-boundary preflight; only the final exit-1 command
above is accepted RED evidence.

### Changed-file hashes

```text
54d003595e23ec6b8a7eeeb0c524232efd1c7a6f285740b7b43bd3852ed757c9  tests/winusb_function_io_contract.c
8e77966e4d73efb34832f898da9269ecee0252a6dd4f74a7a08af949706c41f6  tests/winusb_user_api_contract.c
```

### Self-review

- Replaced the empty function-driver policy group with actual private
  40-byte policy IOCTLs, including pre-alternate pipe rejection, alternate-1
  admission, exact one/four-byte values, direction, read-only, unknown, and
  unsupported-enabled checks.
- Replaced stale public pipe IDs and one-byte timeout behavior with the R95
  alternate-1 profile and explicit short-capacity/guard preservation checks.
- The public missing-symbol path first executes real production through the
  existing fake boundary; it cannot report a feature RED solely from a text
  scan or unused compilation unit.
- No production behavior is claimed; this report records RED only.

## Task 8 test RED correction — round 1 — 2026-08-25

This section supersedes the round-0 acceptance classifications above.  It does
not rewrite or remove that historical evidence.

### R102 evidence adjudication

Independent read-only adjudication found that literal R101 cannot be completed
while all production remains frozen:

- the actual public translation units do not yet define
  `WinUsb_GetPipePolicy` or `WinUsb_SetPipePolicy`, so no test-only edit can
  execute real public policy behavior without adding a forbidden shim or test
  entry point; and
- the frozen function driver has no policy dispatch/state implementation, so a
  meaningful production policy mutant does not yet exist.

R102 therefore supersedes R101 only for evidence that cannot exist before the
first production edit.  This correction round may accept an actual
function-driver behavioral RED plus a public missing-symbol RED after real
initialize/alternate/free preflight.  The public result is explicitly
**nonbehavioral policy evidence**.  At the first callable implementation head,
the complete public behavior branch and isolated wrapper mutants must run.  At
the first kernel policy head, the complete private matrix and isolated
dispatch/state mutants must run.  Task 8 and Gate 2 remain incomplete until
both focused modes are GREEN, all required final-head mutants exit feature 1,
and the combined implementation passes independent review.

No shim, deliberately defective production skeleton, test-only production
entry point, Wine action, prefix access, build staging, or physical USB action
was added or used.

### Corrected test scope

Only these two contracts differ from `task-8-red-head`:

```text
aaa25f98ee7d5594095abe00f4455d62ceb8bc5676f698ed19bb58d77b128b35  tests/winusb_function_io_contract.c
ad7e03764b4a8e5f4e4f0358d743a8134290fc7f9b0667c99c7fb7392f698117  tests/winusb_user_api_contract.c
```

All four Task-8 production paths compare byte-for-byte equal to
`task-8-red-head`:

```text
FROZEN .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c
FROZEN .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c
FROZEN .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h
FROZEN .io24-build/winusb-api-v1/dev-source/dlls/winusb/io.c
```

Both immutable six-path manifests independently verified 6/6:
`task-8-base.sha256` and `task-8-red-head.sha256`.

### Fresh lead verification

```text
$ tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --policy
[202 policy assertion lines beginning with `FAIL group_policy:`]
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--policy dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=202
EXIT=1
PARSED_FAIL_LINES=202
HARNESS_MARKERS=0
```

Classification: honest function-driver behavioral feature RED.  The retained
CP32 prerequisite passed, the contract invoked the actual frozen
`winusb.sys/main.c` dispatch through the intended fake-WDM boundary, intended
policy assertions executed, the parsed assertion count equals the final
failure counter, and the result is neither harness exit 2 nor a crash.

```text
$ tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --policy
CP33 public executed mode=--policy target-mask=0x18c0 present-mask=0x99c missing-mask=0x1040 fake-events=20 submits=4 releases=1 completions=0 failures=3
EXIT=1
HARNESS_MARKERS=0
```

Classification: honest lifecycle-first missing-symbol feature RED under R102,
not public policy behavior proof.  Missing mask `0x1040` is exactly Get/Set
policy.  The real initialize, alternate, and free prerequisites execute before
the explicit missing-policy assertion; the complete policy branch remains
behind the actual function pointers for the first callable production head.

The function contract also passed a fresh ASan/UBSan harness-integrity check:

```text
CP32 winusb function-binding lifecycle checks passed
CP33 function executed mode=--policy dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=202
asan_exit=1
fail_lines=202
final_failure_count=failures=202
sanitizer_markers=0
```

The host login shell emitted `Failed to create stream fd: Operation not
permitted` before local commands; it did not alter either wrapper's exit,
compile, assertion, harness, or sanitizer result.

Battery at the final lead integrity check was 50%, discharging, above the 10%
hard stop.

### Corrected assertion families

- The private contract uses exact 40-byte GET input/output and 40-byte/zero-
  output SET shapes, validates header/version/session/interface/reserved fields
  independently for GET and SET, and requires rejected request nonmutation,
  zero information, and no lower call.
- Private GET treats `value_length` as caller capacity and rewrites it to the
  exact one- or four-byte result.  Public GET independently binds caller
  capacity, returned length/value, untouched tail bytes and guards, and a
  private byte-count pointer distinct from the caller's `ValueLength` pointer.
- Defaults, direction-neutral and direction-specific applicability, writable
  Boolean/ULONG sizes, read-only maximum, unknown IDs, enabled unsupported
  values, distinguishing readback after rejected writes, and zero/noncurrent
  pipe admission are covered.
- Successful target replacement resets all target defaults; NT failure, lower
  URB failure, and post-select revalidation failure preserve distinguishing
  policy state.  A real two-interface fixture proves target-only reset and
  cross-interface endpoint isolation.
- The public branch binds exact request fields, one submission, 4 MiB output,
  handle/pointer admission, caller preservation, transport errors, associated
  `interface_index == 1`, cross-interface rejection, and balanced frees.  Its
  event trace is bounded at 512 entries and still fails explicitly on overflow,
  large enough for the complete correct schedule.
- Test-local snapshot storage was enlarged only enough for the exact 300-byte
  two-interface fixture.  The legacy function trace is cleared after each
  policy/alternate dispatch because it is not a policy oracle; ASan/UBSan
  verifies that this removes the prior diagnostic-buffer corruption without
  suppressing assertion failures.

The independent review first rejected intermediate hashes for event-capacity,
pointer-alias, header-validation, post-alternate admission, cross-interface,
rollback, writable-size, and failure-nonmutation gaps.  Those findings are
addressed in the hashes above.  Final re-review is still required before any
production path may unlock.

### Final independent re-review

The final live-head review passed Task 8 test-correction round 1 under R102:

- Critical findings: none.
- Important findings: none.
- Material Minor findings: none.
- Fresh focused results matched the lead run: function exit 1 with 202 policy
  assertion failures and `failures=202`; public exit 1 with missing mask
  `0x1040` exactly identifying Get/Set policy; neither run emitted a harness
  marker or crashed.
- Fresh ASan/UBSan execution matched the 202 intentional function failures and
  emitted zero sanitizer markers.
- Test hashes remained
  `aaa25f98ee7d5594095abe00f4455d62ceb8bc5676f698ed19bb58d77b128b35`
  and
  `ad7e03764b4a8e5f4e4f0358d743a8134290fc7f9b0667c99c7fb7392f698117`.
- All four frozen production files remained byte-identical to the RED head,
  and both six-path manifests verified 6/6.

This verdict accepts the corrected preproduction RED tests only.  It does not
complete Task 8 or Gate 2.  The R102 deferrals remain mandatory: execute real
public behavior and isolated wrapper mutants at the first callable wrapper
head; execute complete private behavior and dispatch/state mutants at the
first kernel-policy head; then require both focused modes GREEN, every required
final-head mutant to exit feature 1, and a combined independent review.

The reviewer's final battery boundary check observed 46%, discharging, still
above the 10% hard stop.  No live USB or Wine action was performed.

## Task 8 implementation — R103 ownership correction — 2026-08-25

The first callable public implementation exposed a lifecycle-state requirement
that cannot be implemented correctly in `dlls/winusb/io.c` alone.  Local
pre-submission admission must know each interface's current alternate setting,
but the cached ABI snapshot is immutable and its interface `reserved` field
must remain zero.  Encoding mutable state there would violate the snapshot
contract and would race concurrent alternate and policy operations.

R103 therefore expands the Task 8 production allowlist by exactly these two
adjacent public lifecycle paths:

```text
.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c
.io24-build/winusb-api-v1/dev-source/dlls/winusb/winusb_private.h
```

The permitted delta is limited to root-owned per-interface current-alternate
storage, its allocation/free/error cleanup, and declarations needed by
`io.c`.  Alternate selection and policy admission/submission must be serialized
through the existing root lock, publish the new setting only after transport
success, and preserve it on failure.  No wrapper, fake, test, snapshot,
manifest, brief, progress, Wine, prefix, build, or physical-device scope is
unlocked by this correction.

## Task 8 implementation — R104 callable-head test extension — 2026-08-25

The first callable implementation review identified two final-head deletion
mutants that the accepted preproduction RED contracts cannot distinguish:

- removing endpoint-type admission while retaining direction checks, because
  every accepted fixture exposes only bulk endpoints; and
- removing public GET response-integrity validation, because the accepted fake
  always returns a well-formed 40-byte response.

R104 reopens only the two already-owned Task 8 contracts for bounded executable
coverage of those callable-head boundaries.  The private contract must exercise
a current non-bulk endpoint and require policy GET/SET rejection without lower
submission or mutation.  The public contract must exercise short and long
successful byte counts plus wrong echoed header/session/interface/pipe/policy/
value-length and non-Boolean response values; each must fail with
`ERROR_BAD_DEVICE` after exactly one submission while preserving caller length,
value bytes, and guards.  The corrected production head must remain GREEN and
isolated removal/bypass mutants must exit feature 1.  No other test behavior,
production scope, wrapper, fake file, snapshot, manifest, brief, progress, Wine,
prefix, build, or physical-device action is unlocked.

## Task 8 implementation — R105 public lifecycle witnesses — 2026-08-25

R103 requires root-owned current-alternate state and serialization, but the
accepted public policy schedule is single-threaded and frees associated handles
only at the end.  R105 reopens only `tests/winusb_user_api_contract.c` for three
bounded lifecycle witnesses: the cached snapshot remains byte-identical across
alternate/policy operations; an associated interface retains its selected
alternate after its public handle is freed and recreated while the root remains
live; and a deterministic two-thread schedule holds an alternate submission at
the fake transport boundary while a policy call proves it cannot observe or
submit against half-published state.  The correct head must remain GREEN and
isolated snapshot-mutation, handle-local-state, publish-before-success, and
serialization-removal mutants must exit feature 1 without timeout or crash.

No additional production path or external action is authorized by R105.

## Task 8 implementation — combined final-head candidate — 2026-08-25

This section records the combined implementation evidence before independent
final-head review.  It does not rewrite the historical RED evidence or claim
Gate 2 sealed.

### Exact scoped delta

R95 plus R103 authorize six production paths, and R104/R105 reopen only the
two existing contracts:

    .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c
    .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c
    .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h
    .io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c
    .io24-build/winusb-api-v1/dev-source/dlls/winusb/io.c
    .io24-build/winusb-api-v1/dev-source/dlls/winusb/winusb_private.h
    tests/winusb_function_io_contract.c
    tests/winusb_user_api_contract.c

No wrapper, fake, retained log, snapshot, manifest, brief, or progress-ledger
path was edited.  Both immutable historical manifests still verify 6/6:

    sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-8-base.sha256
    EXIT=0, six OK entries

    sha256sum -c .superpowers/sdd/2026-08-23-cp33-winusb-operations/task-8-red-head.sha256
    EXIT=0, six OK entries

The private implementation admits and dispatches only the exact buffered
40-byte GET/SET requests, validates both independent headers, session,
interface, reserved fields, current nonzero bulk endpoint, direction, policy,
and capacity/length before access or commit, and never forwards a policy
operation to the lower stack.  Pipe maps own the exact documented defaults.
Successful alternate replacement creates a fresh defaulted target map; every
alternate failure preserves prior target state and other interfaces.

The public implementation performs handle, pointer, current-endpoint,
bulk-type, direction, policy, and value-shape admission before submission.
GET uses a private byte-count pointer, preserves caller storage on every
failure, reports a short caller capacity without submitting, and validates the
entire returned 40-byte response before copying one or four bytes.  SET accepts
only an exact zero-byte successful response.  Root-owned current-alternate
state is allocated and freed with the root, survives associated-handle
retirement/recreation, leaves the immutable snapshot unchanged, publishes only
after alternate transport success, and is serialized with policy admission and
submission by the root lock.

Task 8 stores RAW_IO and allow-partial state only.  Per R95, no Task-9 transfer
enforcement is claimed.

### Callable-head correction evidence

The R104 public extension initially produced two focused failures against the
first callable head: a non-Boolean successful GET value was accepted and a
successful SET response with a nonzero private byte count was accepted.  The
minimal response checks made the same contract GREEN.  The retained current
non-bulk private fixture and the bulk-guard deletion mutant below independently
bind endpoint type.  During R105 initialization coverage, UBSan identified an
unaligned direct interface-record read in the public root constructor; copying
each packed record into an aligned local before access removed the diagnostic
while preserving the frozen snapshot bytes.

The final public policy mode additionally executes:

- malformed-success GET cases for short/long byte count, size, version,
  session, interface, reserved, pipe, policy, value length, and Boolean value;
- a nonzero successful SET byte-count case;
- cached snapshot byte identity and zero reserved fields after alternate and
  policy operations;
- associated-handle free/recreate retention of interface 1 alternate 1 and
  pipe 0x83 admission; and
- a bounded two-thread schedule that holds SET_ALTERNATE inside the fake
  transport and proves GET policy neither completes nor submits until the
  alternate call publishes and releases the root lock.

### Fresh focused GREEN

The lead reran every Task-8 brief command against the frozen live head:

    tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --policy
    EXIT=0
    CP33 function executed mode=--policy dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=0

    tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --policy
    EXIT=0
    CP33 public executed mode=--policy target-mask=0x18c0 present-mask=0x19dc missing-mask=0 fake-events=38 submits=8 releases=1 completions=0 failures=0

    tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
    EXIT=0
    CP33 function executed mode=--alternate dispatches=4 mode-ioctls=1 last-ioctl=0x222002 last-status=0 failures=0

    tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
    EXIT=0
    CP33 lower executed mode=--claims completions=0 failures=0

    tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
    EXIT=0
    CP33 lower executed mode=--alternate completions=0 failures=0

The lead also reran the three retained public lifecycle modes:

    tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
    EXIT=0
    CP33 public executed mode=--alternate target-mask=0x88c present-mask=0x19dc missing-mask=0 fake-events=22 submits=4 releases=1 completions=0 failures=0

    tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
    EXIT=0
    CP33 public executed mode=--initialize target-mask=0x80 present-mask=0x19dc missing-mask=0 fake-events=19 submits=3 releases=1 completions=0 failures=0

    tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --handles
    EXIT=0
    CP33 public executed mode=--handles target-mask=0x8c present-mask=0x19dc missing-mask=0 fake-events=20 submits=3 releases=1 completions=0 failures=0

Fresh disposable function-contract instrumentation compiled the retained test
and live session.c with:

    cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
      -fsanitize=address,undefined -fno-sanitize-recover=all \
      -fno-omit-frame-pointer -Itests \
      -I.io24-build/winusb-api-v1/dev-source/include \
      -I.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys \
      -I.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys \
      tests/winusb_function_io_contract.c \
      .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c \
      -o /tmp/io24-lead-final-policy-asan.XXXXXX/contract

The resulting --policy run used ASan with leak detection disabled and UBSan
halt-on-error: compile exit 0, run exit 0, failures=0, zero FAIL lines, and
zero AddressSanitizer, UndefinedBehaviorSanitizer, or runtime-error markers.
All disposable objects and logs were removed.

### Private final-head mutants

Each private mutant copied the live dev-source into a mktemp directory under
/tmp, applied exactly one substitution, and ran:

    tests/winusb_function_io_contract.sh "$mutant_root/dev-source" --policy

The source overlay and log were hashed before removal.  Every result was
feature exit 1 with the normal terminal summary, no HARNESS marker, no
sanitizer marker, and no crash:

1. Remove GET/SET from dispatch admission in winusb.sys/main.c:
   failures=204; mutant
   5ecde66f6d27c020e84d364bc48b9ad2ffc44b9c65e5a5610226c874ba16c866;
   log
   378a959583c8a30782890f96d97d0dd2a2d6f421d65e39955ca798209e9dc6a1.
2. Change the IN allow-partial default from TRUE to FALSE in session.c:
   failures=2; mutant
   25d96b7fe0e6afeee0b402e5f2ade0d63ab195b1b2127cf43d11e536360f801c;
   log
   9637d2381a6005830d88db05e4796e278c538fada52c5af77f338324b154ba0e.
3. Force policy lookup to file->interfaces[0] in session.c:
   failures=5; mutant
   57babb10dc8045a5c632571fbc51253be4da23ec8f272a863ff8efb081adfa19;
   log
   37a212147e443216e78cfe91b33690978596e2a1079566868b70380efa1f5b61.
4. Store and accept enabled SHORT_PACKET_TERMINATE instead of returning
   STATUS_NOT_SUPPORTED: failures=2; mutant
   bfc31bae4572d2c9ddef21af76cd2199a23c2982cab3d17a0593de3e0c991b91;
   log
   af6f6a4f0bbf03edaf6f93cb352d3f37f0cecda971442bc355dc1651ab70690b.
5. Delete the UsbdPipeTypeBulk admission guard: failures=3; mutant
   0b5617265f92f78f791c144286d215ef19d44b1d60f4cffacf667c9f96ee9218;
   log
   e746623b69e99d14c7559560bb05c0d9a3f845a09579e0a4a04b0f7920f9d30a.

### Public final-head mutants

Each public mutant copied only the live dev-source under a mktemp /tmp root,
applied the stated substitution, and ran:

    tests/winusb_user_api_contract.sh "$mutant_source" --policy

The final-free mutant used --handles.  Every result was feature exit 1 with a
normal terminal summary, no HARNESS marker, no sanitizer/runtime-error marker,
and no crash:

1. Disable the non-Boolean GET-response check:
   failures=1; mutated io.c
   136de140e079a212f30a8e3a0511cb3474dda3bf143725293404471c0515a909;
   log
   8bab021ab0c9a57260972e41cadaead19d65f745c912019c34ca8ab72f278d4b.
2. Publish current alternate immediately before its transport call:
   failures=4; mutated io.c
   812446da7440d335bcdb3c337559c182d41e80d25fd1db72852bd1f9a5dde2a8;
   log
   a1400b6edecd2403666a169a2afc095cfbf6472da0c8e68849e7efa9906c279f.
3. Remove the root-lock boundaries around alternate submission/publication:
   failures=2; mutated io.c
   57e66e482d3aafcf8f51feb2c2a89fde5977aa83899a75341603306220d0f3c0;
   log
   5547740815d277321388c3244c23356387555d5ebe9e6136ca3fd8db987d1508.
4. Force acquired.interface_index to zero in public GET:
   failures=5; mutated io.c
   d9fb523245b08cb17a2f1d42368f9419f6b1c89d93a75281ed9d8d22efb2a113;
   log
   20a94258731eb85e5402e02a954a670af1ac8e14e63619a812c63f7e05d0aa1b.
5. Delete the winusb_root_release current_alternates free:
   --handles failures=4; mutated main.c
   9761ea1e79414967d98b6d5fbe24c0bdfd6d910ad7bf0e71965ba93d8ca683a5;
   log
   f9ab79b3acd7a4ed2b74e344b79af13d984957d6537db463ed760a39b4981615.
   The source hash was reconstructed without execution by streaming the exact
   one-line deletion through sha256sum after the original temporary source was
   removed.
6. Mutate snapshot reserved[0] after successful alternate publication:
   failures=1; exact terminal fake-events=38/submits=8/releases=1; mutated io.c
   a049f323d8f83ee69036d6e74b050ed357d7e543b42fe1d51ec1a0a22bcc0fcd;
   log
   8bab021ab0c9a57260972e41cadaead19d65f745c912019c34ca8ab72f278d4b.
7. Reset an associated interface's root current-alternate entry to
   first_alternate whenever its public handle is created/recreated:
   failures=1; exact terminal fake-events=35/submits=7/releases=1; mutated
   main.c
   1c1422d4356686526b40e01a9934fd421d86f11f830d8fa8f8114b03169c5f79;
   log
   f5416ecc9c90b657c1e9b6f7e25e005dbfdcc3de71c8837e9f5a09297b58e53d.

All mutant directories and logs were removed after evidence capture.

### Frozen candidate hashes

    e1823e6797af31a145f65851e342ec46a14d397ffa5c4c4575228cfe4777b8e1  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c
    b915d107361c26a3b012c352307ffa1a07a272e79fd39fc446d9af4cf67afd7  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c
    d2f6bacba34096e55c19a7bd9e18d61777bff6a3098ca85daaae79bf1edb1b6c  .io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h
    e7e25ef680765acb5e28f9beb5cd30b3f6dca8ce4f189cd89d8ba95bbfc6316d  .io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c
    057a862f69b310688f7c2e11f88dbcf2f60aefc5525d0604cbdf727236b563dd  .io24-build/winusb-api-v1/dev-source/dlls/winusb/io.c
    bb15c30e7354ae68b90b6031861e2736f026a8333d06dc1fedb1f9421f130ffe  .io24-build/winusb-api-v1/dev-source/dlls/winusb/winusb_private.h
    976952ade0471a54606298b5a11921b9b2ce38f7f7ea56e75bc7203e1df47267  tests/winusb_function_io_contract.c
    cbe349aedc28b75e59b4d58cf86896385a98a8c3e51b1f0ca9b60e245ead1778  tests/winusb_user_api_contract.c

### Boundary and candidate self-review

- All retained focused modes execute production through their existing fake
  boundaries; no source scan, unused duplicate, or missing-symbol result is
  counted as final behavior evidence.
- GET/SET request shapes, information counts, caller preservation, no-lower
  behavior, defaults, writable/read-only behavior, direction and bulk
  applicability, alternate reset/rollback, cross-interface isolation, public
  response integrity, root lifetime, and serialization each have direct
  positive assertions and a bounded deletion/bypass lens.
- The immutable snapshots remain independently reproducible and live cached
  snapshot bytes are not used as mutable lifecycle storage.
- The host shell's recurring Failed to create stream fd diagnostic did not
  alter command exits or contract/sanitizer counts.
- Battery was 25%, discharging, at the final manifest/boundary checks, above
  the 10% hard stop.
- No Wine process, Wine prefix, contained build, build selection/staging,
  physical USB path, claim/detach, alternate/configuration change, or transfer
  was accessed.  The interface remained unplugged.
- Independent combined final-head review is still required.  The plan's Gate-2
  seal manifest has not been created because the Task-8 brief explicitly
  prohibits manifest edits; the reviewer must adjudicate implementation PASS
  separately from controller-owned Gate-2 sealing.

## Task 8 final independent review and Gate-2 closure — 2026-08-25

### Independent combined verdict

The independent final-head reviewer returned PASS under R103-R105:

- Critical findings: none.
- Important findings: none.
- Material Minor findings: none.
- No material correctness, concurrency, lifetime, recovery, or scope issue.

The reviewer independently inspected all six production paths and both
contracts, reran the five brief gates plus public --alternate, --initialize,
and --handles, and reran function policy with ASan/UBSan.  Every positive gate
exited 0 with failures=0 and the sanitizer run emitted zero sanitizer markers.
The reviewer also independently reproduced two deletion/bypass lenses:

- deleting the private bulk-type guard exited feature 1 with failures=3; and
- mutating cached snapshot reserved[0] during alternate publication exited
  feature 1 with failures=1.

Neither mutant emitted a harness, sanitizer, or crash marker.  Both disposable
roots were removed.  The eight candidate hashes remained exact, and the
immutable Task-8 base and RED manifests again verified 6/6.  Reviewer battery
ended at 20%, discharging.  No Wine, prefix, contained build, staging, network,
USB/device, configuration, claim, alternate, or transfer action occurred.

The lock review found the ordering safe: policy/alternate paths leave the root
lock before releasing their acquired handle, concurrent public free waits and
then retires its reference without an inversion, and the kernel session_mutex
keeps a looked-up pipe-map entry live while serializing policy access with
alternate replacement.

### R106 controller Gate-2 seal adjudication

The independent review ruled that the Task-8 brief's manifest prohibition
constrains implementer ownership but does not cancel the approved controller
checkpoint in the plan.  Task 8 therefore passed before seal creation, and the
controller was authorized to create the nonrecursive Gate-2 seal without a new
user decision.

The controller created eight fresh final-head output logs.  Each records its
exact command, complete terminal output, and EXIT=0:

    96e5631782a65644a3407f1abf1babb3ff090708b425cd06513b407f849e3801  re/winusb-api-v1/logs/gate-2-final-function-alternate.log
    4e6e05e54c30fdb68f731e1a50daa2ab8ac821fbb4fb5d0b842ad37c078cd2bf  re/winusb-api-v1/logs/gate-2-final-function-policy.log
    a643d43cc6a33a7052026b910b5ba73ea1603643d7cb3b0867e2b02ae97f9270  re/winusb-api-v1/logs/gate-2-final-lower-alternate.log
    f7be17fc751ec5af811df00ff8b41781e1ed4067e7c5d2ec43fba4e408202319  re/winusb-api-v1/logs/gate-2-final-lower-claims.log
    30b6207c8f977b8c2ae4c69c64e82275adcf59492209e352853660fa3fc8de7b  re/winusb-api-v1/logs/gate-2-final-public-alternate.log
    d3c920481b4a74339ed8ac52674b1084e0f6c54e7f5619b817ba1bfebdaec503  re/winusb-api-v1/logs/gate-2-final-public-handles.log
    9d87d9422e68a9d24ca31d8de3dcf46e481e646af887d4b4f2aa3906984aa970  re/winusb-api-v1/logs/gate-2-final-public-initialize.log
    63fe7a75e9d28a4d10e557d1e2695d2ffc1a6af1f9f07e8320369b38d3d20ee7  re/winusb-api-v1/logs/gate-2-final-public-policy.log

The controller then created:

    re/winusb-api-v1/logs/gate-2-function-pipe-state.sha256

Its 29 unique paths are the sorted 21-path current union of
task-06-claims.sha256 and task-07-alternate.sha256 plus the eight fresh logs
above.  The seal excludes itself, historical/superseded outputs, reports, and
disposable mutants.  Immediate verification produced 29 OK entries:

    candidate_count=29 source_support_count=21 focused_log_count=8 missing=0
    seal_entries=29 unique_paths=29 self_entries=0 verify_exit=0

The finalized seal file hash is:

    63127db956be81f5c51a396967009276a12cbe4b7f9daebca6f02e5ed8c7cd36  re/winusb-api-v1/logs/gate-2-function-pipe-state.sha256

Battery was 18%, discharging, after seal verification, above the 10% hard
stop.  Task 8 and the offline Gate-2 function/pipe-state checkpoint are now
complete.  This closure remains host-contract evidence only and makes no
contained-build, Wine, prefix, staged-binary, or physical-device claim.  The
interface remained unplugged throughout.
