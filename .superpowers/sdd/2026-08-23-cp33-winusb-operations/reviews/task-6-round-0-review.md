# CP33 Task 6 independent review — round 0

Result: FAIL. Task 6 remains open; Task 7 is gated.

## Critical

`.io24-build/winusb-api-v1/dev-source/dlls/winusb.sys/session.c:796`
publishes `snapshot`, `interfaces`, `session`, and
`WINUSB_FILE_INITIALIZED` before lower COMMIT at line 819. Actual dispatch
admits concurrent same-file requests at `dlls/winusb.sys/main.c:388-399`; a
concurrent RELEASE with the predictable next cookie can free those objects at
`session.c:877-903`, after which the initializer reads freed `snapshot` at line
847. This violates atomic claim finalization/session publication. Serialize
RELEASE against an outstanding initializer or otherwise make publication and
finalization indivisible, and add a deterministic reentrant ASan case.

## High

1. `session.c:821-843` attempts ROLLBACK after failed COMMIT but ignores the
   rollback result, clears the local token, frees/restores upper state, and
   returns. If both submissions fail, the lower pending journal survives.
   Retain ownership/token until rollback succeeds or synchronous child teardown
   proves release. Add distinct COMMIT-failure and ROLLBACK-failure schedules.
2. `session.c:781-785` rejects successful SELECT with a null transaction, while
   `wineusb.sys/unixlib.c:1314-1352` creates tokens only for function children.
   Existing single-interface enumeration publishes WinUSB metadata on a
   non-function parent at `unixlib.c:631-647`. Preserve that legacy path by
   conditioning finalization on a nonnull token or using an explicit safe
   discriminator, with an executable non-function SELECT regression.

## Medium

The real finalize-ROLLBACK route at
`tests/wineusb_winusb_urb_contract.c:209-213` carries an empty idempotent
transaction. The nonempty reverse-order witness reaches the shared helper only
through destruction. Add a nonempty finalize-ROLLBACK witness that proves
reverse release and unchanged committed claims. Then commit one interface,
fail a later multi-interface extension, and prove only that transaction's new
journal is released while the earlier committed set remains.

## Confirmed non-findings and environment caveat

- The real `unixlib.c` and `session.c` translations execute through their fake
  boundaries.
- R77 remains unsupported-only; metadata v1/v2 remain unchanged with no v3;
  `unixlib.h` remains at `23079216...`; no detach, auto-detach, or
  set-configuration path was added.
- LeakSanitizer's ptrace refusal is a nonblocking environment caveat. The
  leak-disabled assertion run retains ASan, UBSan, and alignment
  instrumentation, and explicit allocation balances cover Task 6 upper
  allocations. It does not cover the missing schedules above.
