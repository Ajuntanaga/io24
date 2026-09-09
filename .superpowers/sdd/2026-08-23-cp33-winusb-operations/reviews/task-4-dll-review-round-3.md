# CP33 Task 4 DLL-half independent review — fix round 3

Verdict: **PASS**

No Critical, Important, or material Minor issue remains in the round-3 DLL
scope.

## Prior findings

- **R56 — addressed.** Both mutations are enumerated at
  `tests/winusb_user_api_contract.c:232-234` and executed by the inclusive loop
  at line 482. The duplicate case changes raw byte 54, the second endpoint's
  `bEndpointAddress`, and updates the corresponding packed endpoint record at
  offset 123 without changing `bLength` (lines 269-270). Rejection asserts
  `ERROR_BAD_DEVICE`, one rollback RELEASE, and balanced resources (lines
  444-454).
- **Supplemental mutation evidence.** Controller-owned temporary source copies
  independently removed the raw alternate-setting match and the
  per-alternate endpoint-uniqueness loop. Each made `--initialize` exit 1 with
  `failures=3`. The temporary copies were removed and workspace production
  hashes remained unchanged.
- **R57 — addressed.** The fake records completion result, error, device, and
  `OVERLAPPED` (lines 379-380). Pending RELEASE requires exactly one completion
  on the original device and identical private `OVERLAPPED`, with the scheduled
  result/error; immediate RELEASE requires zero completions (lines 453-456).
  All immediate/pending success/failure variants execute at line 490, while
  event-allocation and wait-failed paths assert zero completions and exact
  RELEASE identity at lines 491-492.

## Scope hashes

```text
1cb862f861d59a4ffc57fe42833ccd85459239bed137da62e543bf45bd59c02e  dlls/winusb/Makefile.in (frozen)
b4f1ead66779024c7c0125e90b2ab8a5ac1c3fcc2b4a970d9dd9f7b63d475fb6  dlls/winusb/main.c (frozen)
2aad333179951f9b806e3e85678b978138ccd1c217a4253934d54335e34d83d8  dlls/winusb/winusb_private.h (frozen)
e529b957ac7038bc3d3d0fed2c9902e123ad427f0a61178211c13751ad45cae2  tests/winusb_user_api_contract.c
f601c75e890afb48771f77e976041139ee33e3ce4331cb380c1e601af9bf4ebc  tests/winusb_user_api_contract.sh (frozen)
1b57098fde77c57510a666ac34798b9baa0f755bfe3fe9a37be9d3146bba4081  task-4-dll-report.md
```

## Authorized gates

Both exited zero:

```text
--initialize: failures=0, submits=3, releases=1, completions=0
--surface-only: passed, native layout, exports=14, stubs=8
```

The report labels older blockers superseded and gives an unambiguous R56-R57
account. No production/wrapper regression or unauthorized action was observed.
