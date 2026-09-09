# CP33 Task 8 brief — exact vendor pipe-policy profile

## Authority

- Approved plan: `docs/superpowers/plans/2026-08-23-cp33-winusb-operations.md`, Task 8.
- Approved design: `docs/superpowers/specs/2026-08-23-cp33-winusb-operations-design.md`, exact pipe-policy contract.
- Controller rulings: R18 and R95 in `progress.md`.
- Reviewed input checkpoint: `task-7-round-2-head`; `re/winusb-api-v1/logs/task-07-alternate.sha256` verifies 17/17.
- Exact pre-edit snapshot: `task-8-base` and `task-8-base.sha256` over six paths.

## Ownership

Modify only:

1. `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/main.c`
2. `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c`
3. `.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/winusb_private.h`
4. `.io24-build/winusb-api-v1/dev-source/dlls/winusb/io.c`
5. `tests/winusb_function_io_contract.c`
6. `tests/winusb_user_api_contract.c`

Append evidence only to `task-8-report.md`. Do not edit wrappers, fakes,
retained logs, snapshots, manifests, this brief, or `progress.md`.

## Required test-first correction

The current function `group_policy()` is an empty placeholder and the public
policy fixtures use stale pre-alternate pipe IDs and one-byte lengths for every
policy. Replace these cases before production edits and run both focused modes
against `task-8-base`. An accepted RED is feature exit 1 with the intended
policy assertions executed; exit 2, a compile/link failure, empty execution,
or an unrelated prerequisite failure is not RED.

## Required behavior

- `PipeID` zero is never a wildcard. Before selecting alternate 1, policy
  requests for `0`, `0x01`, and `0x81` fail without submission or state change.
- After successful alternate 1, only current OUT `0x01` and IN `0x81` are
  accepted for the root MI05 handle. Associated handles resolve only their own
  current endpoints.
- Each current pipe receives defaults on initialization/creation: timeout 0,
  reset-on-resume false, maximum transfer 4 MiB, OUT short-packet-terminate
  false, and IN auto-clear false, ignore-short false, allow-partial true,
  auto-flush false, RAW_IO false.
- Policy IDs 1 through 9 use exact applicability and lengths: timeout and
  maximum are four-byte ULONG values; all booleans are one byte.
- `MAXIMUM_TRANSFER_SIZE` is read-only. Setting it, unknown policies, wrong
  endpoint direction, wrong sizes, or invalid admission fail without mutation.
- Enabling timeout, short-packet termination, auto-clear, ignore-short,
  auto-flush, or reset-on-resume returns `STATUS_NOT_SUPPORTED` / public
  `ERROR_NOT_SUPPORTED` and is not stored. Supported false values commit.
- IN allow-partial accepts true/false. IN RAW_IO accepts true/false. Do not
  enable RAW_IO on OUT. Task 8 stores authoritative state only; Task 9 owns
  transfer enforcement.
- Public Get with a valid policy but short capacity returns
  `ERROR_INSUFFICIENT_BUFFER`, writes required length 1 or 4, and preserves all
  value bytes and guards. Invalid admission or transport failure preserves the
  caller's original length and value/guards.
- Successful alternate selection resets defaults only for the replaced target
  interface's new pipes. A failed alternate preserves the complete prior
  policy map. Other interfaces' current policy state remains unchanged.
- Validate exact 40-byte private request, header/version/session/interface,
  reserved fields, pipe, policy, and value length before commit/submission.

## Gates and evidence

Required focused GREEN:

```text
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --policy
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --policy
tests/winusb_function_io_contract.sh .io24-build/winusb-api-v1/dev-source --alternate
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source .io24-build/winusb-function-binding-v1/build-a .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --alternate
```

Add bounded negative source variants for plausible policy bypasses so the new
contract cannot pass on constants, text scanning, unused code, or permissive
fakes. Record exact commands, terminal outputs, exit classifications, changed
paths, hashes, and self-review in `task-8-report.md`.

## Boundary

Offline local source and focused host contracts only. Do not run Wine, inspect
or touch a Wine prefix, stage/select a build, load anything, access a physical
USB path, claim/detach an interface, change physical configuration/alternate,
or issue a physical transfer. Check battery during the task and stop cleanly at
10% or lower. Do not run a broad suite or contained build in Task 8.
