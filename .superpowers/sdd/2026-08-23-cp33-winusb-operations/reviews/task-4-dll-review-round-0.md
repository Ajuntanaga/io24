# CP33 Task 4 DLL-half independent review — round 0

Verdict: **FAIL**. This is an offline correctness/ABI review, not a
cybersecurity assessment.

## Important

1. `WinUsb_Initialize` overwrites meaningful event, IOCTL, wait, and completion
   errors with `ERROR_BAD_DEVICE`. Preserve the helper's effective failure and
   add event/immediate/pending failure cases with exact `LastError` assertions.
2. The 72-byte noncommitting header validation omits reserved, speed, offset,
   length, and count invariants. Corrupting only that first response currently
   permits a later valid full response to publish.
3. The validator searches raw interface descriptors by value instead of
   checking their actual order, so alt1-before-alt0 can pass. It also permits
   duplicate endpoint addresses within one alternate. Add both counterexamples
   and enforce exact raw/record ordering plus per-alternate pipe uniqueness.
4. The executable contract omits event failure, wait failure, pending full
   success/failure, pending/failed release, NONALERT mode, invalid-handle value,
   failing `IO_STATUS_BLOCK`, and exact RELEASE request/session/device/event
   assertions. The release counter alone is false-green-capable.
5. The R32 wrapper collects optional future production sources but compiles
   only `${sources[0]}`. Compile and link every collected source so Task 7's
   `io.c` cannot be silently omitted.

## Minor

- The terminal `releases=0` field reports an unused counter instead of the
  actual release-IOCTL count.
- Nine coarse mutations do not cover the brief's required header, count,
  overflow, region, default/ordering, and endpoint-index classes.

Both authorized gates passed. Alignment-safe reads, sanitizer linkage, the
bulk/512 retained fixture, the non-MI05 low-speed fixture, caller-handle
ownership, and both allocation boundaries had no material finding.
