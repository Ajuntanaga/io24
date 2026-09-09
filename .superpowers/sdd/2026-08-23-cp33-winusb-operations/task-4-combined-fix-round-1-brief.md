# CP33 Task 4 combined fix round 1 brief

The authoritative Task-4 plan/spec, combined review round 0, and controller
rulings R58-R60 apply. The failed reviewed base is immutable `task-4-head`.

## Ownership

Only these paths may change:

```text
.io24-build/winusb-api-v1/dev-source/dlls/winusb/main.c
tests/winusb_user_api_contract.c
.superpowers/sdd/2026-08-23-cp33-winusb-operations/task-4-dll-report.md
```

Base hashes:

```text
b4f1ead66779024c7c0125e90b2ab8a5ac1c3fcc2b4a970d9dd9f7b63d475fb6  dlls/winusb/main.c
e529b957ac7038bc3d3d0fed2c9902e123ad427f0a61178211c13751ad45cae2  tests/winusb_user_api_contract.c
1b57098fde77c57510a666ac34798b9baa0f755bfe3fe9a37be9d3146bba4081  task-4-dll-report.md
```

The user wrapper, DLL private header/Makefile, complete kernel half, all other
contracts, failed head, controller patch/checksum, ledger, rubric, packages,
and reviews are frozen.

## Required TDD correction

1. Add RED cases first for:
   - a valid descriptor/snapshot with two interface groups in descending numeric
     order, `[5 alt0, 2 alt0]`;
   - a duplicate interface number rejected postcommit;
   - endpoint address reuse across distinct alternates accepted;
   - `WAIT_FAILED` setting a distinct error that must survive clobbering event
     cleanup;
   - the second INITIALIZE output length and snapshot allocation each equaling
     the sizing header's advertised `total_size`.
2. Replace DLL numeric interface sorting with explicit equality rejection
   against every prior interface record, preserving actual raw group order and
   contiguous packed ranges.
3. In `submit_request`, preserve `GetLastError()` only for `WAIT_FAILED` before
   closing the event; map other unexpected wait results to the local generic
   error.
4. Record the full request and allocation sizes generically in the fake and
   assert exact sizing-header equality. Use a temporary source copy to prove a
   `header.total_size + 1` production mutation exits feature 1, never harness 2;
   remove the temporary copy afterward.

Do not hardcode success to one fixture, weaken existing rejection matrices, add
a production seam, source-scan instead of executing production, or expand into
Task 5 ownership.

## Authorized commands

```text
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --initialize
tests/winusb_user_api_contract.sh .io24-build/winusb-api-v1/dev-source --surface-only
```

Append exact RED/GREEN, mutation, scope, and hash evidence to the DLL report.
Do not regenerate controller evidence. No Wine, prefix, device/sysfs USB,
contained/full build, driver action, application, install, Git, physical action,
or CP24 retry is authorized.
