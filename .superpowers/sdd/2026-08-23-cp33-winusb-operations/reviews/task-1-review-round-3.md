# Task 1 fix round 3 scoped re-review

Verdict: **FAIL — one finding remains open**.

## Finding verdicts

1. **Public fake-boundary validation remains false-GREEN-capable for returned values — NOT ADDRESSED.** Typed request fields are checked, but the vendor caller checks only API success. It never verifies caller-observed descriptor length/data or `GetPipePolicy` value/value-length. A wrapper can submit the correct IOCTL and discard returned data while passing.
2. **Focused modes collapsed behind initialization prerequisites — ADDRESSED.** Public modes report distinct target/missing masks before initialization; function modes issue their own safe negative IOCTL after failed initialization.

## Preservation and breakage

All earlier fixes were preserved: real production compilation/execution, boundary-authored observation, Python harness remapping, initialization-returned handles, control-only setup subtraction, pre/post deltas, distinct lower/cancel modes, and exit-code separation. No new Critical/Important breakage was found.

## Required bounded correction

- Make the fake Win32 boundary return independently defined descriptor bytes/length and pipe-policy value/value-length through the actual output buffers and returned-byte channels for the exact typed IOCTL.
- Assert the public caller observes those exact bytes and lengths after actual `WinUsb_GetDescriptor` and `WinUsb_GetPipePolicy` return. Boundary request correctness and caller-visible response propagation are separate required assertions.
- Cover other returned transfer/result lengths touched by the vendor sequence if the same omission exists, without widening beyond Task 1.
- Preserve every addressed finding and rerun the public/vendor focused evidence plus the complete Task 1 matrix/checkpoint/clone diffs.

