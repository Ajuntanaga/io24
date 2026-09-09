# Task 1 fix round 4 scoped re-review

Verdict: **FAIL — one narrowly defined finding remains open**.

## Finding verdict

**Caller-visible returned-value propagation — NOT ADDRESSED only for `GetPipePolicy` ValueLength.** Descriptor/speed/transfer/read/write/overlapped outputs and policy value now have independent injection, sentinels, exact caller assertions, and guards. Policy `ValueLength`, however, begins as valid capacity `4` and is expected to return `4`; an implementation that omits writing `*ValueLength` leaves `4` unchanged and passes.

## Preservation and breakage

All previous fixes remain preserved. No new Critical/Important breakage was found.

## Required bounded correction

- Add a valid policy-get caller path whose input buffer capacity differs from the fake's exact returned policy length, for example an oversized valid capacity or a supported one-byte policy. The fake must return the exact actual length through the real response channel, and caller assertion must distinguish a missing `*ValueLength` write.
- Preserve the frozen vendor policy-8 call's exact four-byte input where required; the companion focused policy case may prove the shared wrapper's returned-length propagation.
- Rerun focused policy/vendor/red coverage and the complete Task 1 evidence. Do not alter any production source.

