# Task 1 fix round 1 scoped re-review

Verdict: **FAIL — findings remain open**.

## Finding verdicts

1. **Production behavior was not executed — ADDRESSED.** Public loads/calls the built module; function includes actual `main.c`; lower loads/calls actual `unixlib.c`; cancellation includes actual `wineusb.c` and dispatches to the loaded lower call table.
2. **Complete, controllable, observable fakes/assertions were missing or inert — NOT ADDRESSED.** Function setup pre-increments `lower_calls`, so a no-op read can satisfy forwarding; session/alternate checks only inspect prefilled bytes; cancellation counts before real lower behavior; public fake IOCTL records are not substantively asserted.
3. **Vendor profile lacked a synthetic fourteen-operation sequence through the public fake boundary — NOT ADDRESSED.** The caller writes the alleged trace after attempted calls. The fake boundary records only generic IOCTL arrays, and validation reduces these to aggregate counts, so incorrect API-to-IOCTL translation can pass.
4. **Focused modes were accepted but ignored — ADDRESSED.** Each family dispatches distinct executed behavior groups.
5. **Harness/tool failures could collide with feature exit 1 — NOT ADDRESSED.** Python source reads are outside the exception handler; an `OSError` can escape and produce exit 1 without `HARNESS:`.

## Important new breakage in the fix diff

1. Public focused modes pass fabricated handle `0x2200` directly to production APIs, including `WinUsb_Free`. A correct implementation using an allocated private handle can crash rather than reach GREEN.
2. Fake libusb subtracts `LIBUSB_CONTROL_SETUP_SIZE` from payload capacity for every transfer type, truncating bulk/interrupt completion data and permitting inconsistent `actual_length`.

## Required bounded correction

- Make forwarding/session/alternate/cancellation assertions observe post-call production effects, with baselines captured before the call and exact deltas/arguments checked.
- Move the vendor semantic trace into the fake boundary and validate exact API-to-IOCTL/setup/pipe/policy/length/overlapped/result/free-order behavior; caller-authored operation labels are not evidence.
- Catch all source-read and optional-file `OSError` paths as `HARNESS:` exit 2.
- Obtain public API handles through successful production initialization before any handle-dependent focused call; absent/failed initialization is the feature RED. Never hand a fabricated private pointer to production.
- Apply control setup-length adjustment only to control transfers; enforce consistent copied length and `actual_length` for bulk/interrupt completion.

