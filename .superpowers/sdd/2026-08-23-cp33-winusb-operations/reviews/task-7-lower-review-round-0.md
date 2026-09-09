# CP33 Task 7 lower review round 0

Result: **FAIL**. Task 7 remains open and the combined review is gated.

Reviewed head hashes:

- `wineusb.c`: `150d049d...`
- `unixlib.c`: `a9ebe86d...`
- `wineusb_winusb_urb_contract.c`: `59f26070...`
- `wineusb_pipe_observe_contract.c`: `78e6b805...`

## Findings

1. **Critical — the live `wineusb.c` translation unit does not compile.**
   `URB_FUNCTION_SELECT_INTERFACE` appears both in the forwarded group near
   line 790 and in the obsolete `STATUS_NOT_IMPLEMENTED` branch near line 897.
   The focused lower wrapper compiled only `unixlib.c` and missed the duplicate
   switch case. Delete the obsolete branch and add an actual-translation-unit
   executable gate.

2. **Important — selection trusts caller pipe metadata rather than the active
   descriptor.** Alternate and configuration selection do not prove that the
   alternate exists or that endpoint, type, count, maximum packet size, and
   returned fields match the active descriptor. Pipe lookup likewise does not
   revalidate endpoint/type against the current descriptor. The focused test
   incorrectly accepts MI05 alternate 2 and never supplies or asserts 512-byte
   endpoint metadata.

3. **Important — alternate selection does not reject outstanding child IRPs.**
   The kernel path forwards SELECT_INTERFACE without inspecting
   `device->irp_list`. Leave one fake child request pending and require a busy
   rejection, zero lower alternate calls, and byte-for-byte preservation.

4. **Important — generation exhaustion wraps and can resurrect stale tokens.**
   Generation zero is converted back to one, and generation advances per pipe
   instead of once per successful selection. Reserve one generation for the
   complete staged map and make exhaustion terminal before any backend call.

5. **Important — configuration capacity/generation failure occurs after claims
   and publication.** A late failure can roll back claims while leaving the
   caller's returned `ConfigurationHandle` pointing at a freed transaction.
   Validate descriptor metadata, capacity, and generation and build the full
   staged table before claims; publish caller fields only after all fallible
   staging succeeds.

6. **Important — the focused tests are false-GREEN-capable.** The fake exposes
   no active descriptor. The matrix omits unknown alternate, descriptor
   endpoint/type/count/512-byte validation, unclaimed scope, pending IRP,
   target-only preservation, a real old-token rejection after generation two,
   wrong generation/slot/record fields, capacity/exhaustion, configuration
   rollback preservation, and child destruction of staged/committed tables.
   Retained tests must obtain actual production-returned tokens, never fabricate
   or decode legacy packed handles.

7. **Minor — variable-size validation accepts a trailing partial byte.** Require
   exact header plus `N * pipe_size` equality before any backend action.

The copied-table approach, target-only retirement, delayed alternate output
writes, transaction-staged configuration publication, rollback freeing, and
child-destruction freeing are directionally sound, but insufficient for PASS.

## Required continuation

Apply R89 with the two added test paths. Preserve all non-owned paths, the
existing bus-interface wrapper, and all retained metadata v1/v2 assertions.
After focused GREEN, regenerate a sixteen-path base-to-head package and obtain
one independent combined Task-7 review.
