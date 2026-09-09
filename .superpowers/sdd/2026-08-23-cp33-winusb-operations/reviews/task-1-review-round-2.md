# Task 1 fix round 2 scoped re-review

Verdict: **FAIL — findings remain open**.

## Finding verdicts

1. **Fake observations/assertions could false-GREEN — NOT ADDRESSED.** Function and cancellation baselines are corrected, but public validation searches for integers at arbitrary byte offsets and does not verify descriptor arguments, policy length/value, or returned values. Malformed events can contain the integers in unrelated fields and pass.
2. **Vendor trace was caller-authored — ADDRESSED.** `DeviceIoControl` now emits observed boundary events and validation consumes them; caller code only invokes APIs.
3. **Python reads could escape as exit 1 — ADDRESSED.** Required/optional reads and tools are inside the `OSError`/tool-failure handler; abnormal child statuses are remapped.
4. **Fabricated private handle — ADDRESSED.** Dependent groups use only the interface handle returned by production initialization.
5. **Non-control completion truncation — ADDRESSED.** Setup-size subtraction is control-only, and the lower contract validates the full bulk payload and length.

## Important regression

When `WinUsb_Initialize` is absent, every dependent public group returns at the same prerequisite and executes no fake-boundary event; retained output shows zero events/submissions for every public mode. Function session/alternate/policy/transfer modes likewise collapse on initialization. The focused modes therefore no longer expose distinct missing-feature boundaries on untouched CP32.

## Required bounded correction

- Replace public arbitrary-offset integer searches with typed, field-specific, independently defined expected request/response assertions: exact IOCTL, buffer method/direction, request version/size, descriptor type/index/language, policy ID/value length/value, pipe ID, setup packet bytes, transfer length, caller `OVERLAPPED` identity, returned bytes/value, and free/close order as applicable.
- Keep handle-dependent calls safe: never fabricate a private handle. Resolve each mode's own target exports before initialization and report its specific absent-symbol/operation set. Exercise a safe actual production negative path where available. Once initialization succeeds, continue through that mode's distinct boundary calls and typed assertions.
- Make function modes cross distinct actual IOCTL dispatch boundaries on CP32 without constructing a fake private context or risking a correct implementation. Preserve the full prerequisite sequence for later GREEN, but expose/log the exact mode-specific IOCTL/rejection when a prerequisite is absent.
- Preserve all four addressed round-2 fixes and all earlier real-production and exit-code separation fixes.

