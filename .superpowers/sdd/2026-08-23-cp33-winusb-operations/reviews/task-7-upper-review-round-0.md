# CP33 Task 7 upper review round 0

Result: **FAIL**. The focused alternate path executes, but Task 7 remains open.

Reviewed hashes:

- `winusb.sys/main.c`: `0c602bd8...`
- `winusb.sys/session.c`: `38fac173...`
- `winusb.sys/winusb_private.h`: `771063a4...`
- `winusb_function_io_contract.c`: `939c2848...`

## Findings

1. **High — target-interface outstanding rejection is an unconnected
   placeholder.** `winusb_interface_state.outstanding` is declared and read,
   but no production path increments or decrements it. The test directly sets
   the field. The existing file-wide `outstanding != 1` guard is conservative
   and executable; the lower R89 gate separately rejects any pending child IRP.
   R91 removes the false target-specific claim and defers precise accounting to
   the tasks that create actual transfer records.

2. **Medium — SET_ALTERNATE accepts a nonzero output contract.** Dispatch routes
   it without rejecting nonzero output length or `MdlAddress`. Require both to
   be absent before calling the session handler, with guarded executable cases.

3. **Medium — the R86 behavioral matrix is under-covered.** Add short and
   oversized input; bad request size/version/nested reserved/session;
   nonzero-output/MDL; temporary-map and URB allocation failure; distinct lower
   NT and URB status failures; multi-interface target-only preservation;
   revalidation around lower completion; default SELECT nonzero-handle
   retention/cleanup; and stale prior lower-handle observations.

## Sound portions retained

Production already checks exact input size and header/session/interface state,
builds and zeroes the variable SELECT_INTERFACE URB, holds the device
finalization and file session mutexes in the observed order, replaces only the
target interface on success, centralizes cleanup, and adds no Task-8 behavior.

Focused offline results:

- upper `--alternate`: exit 0
- upper `--lifecycle`: exit 0
- upper `--session`: exit 0
- retained function binding: exit 0
- raw upper `--initialize`: exit 1, LeakSanitizer ptrace refusal only
- `LSAN_OPTIONS=detect_leaks=0` upper `--initialize`: exit 0 with ASan/UBSan,
  alignment instrumentation, and explicit allocation balance retained

No Wine runtime, prefix, USB/sysfs/device, staging, selection, or live action
was used.
