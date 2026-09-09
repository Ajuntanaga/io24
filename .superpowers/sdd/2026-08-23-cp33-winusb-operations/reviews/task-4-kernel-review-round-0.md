# CP33 Task 4 kernel-half independent review — round 0

Verdict: **FAIL**. This is an offline correctness/lifetime/ABI review, not a
cybersecurity assessment.

## Critical

1. `session.c` reads `irp->IoStatus.Status` after a synchronous
   `IoCallDriver` return. Wine's `IoCompleteRequest` has already copied the
   result to the supplied `UserIosb` and freed a builder-created IRP, so the
   read at `session.c:94` is a reachable use-after-free. The static fake IRP
   masks it. Consume the local `IO_STATUS_BLOCK` for immediate and pending
   completion, and make the fake free an immediate builder IRP under ASan.

## Important

2. Zero-initialized URBs begin with `USBD_STATUS_SUCCESS`, so the upper check
   cannot prove the lower layer wrote success. Initialize a failure sentinel,
   remove the fake's helpful default, and require an observable success write.
   The real lower select backend must also set `Hdr.Status` on success.
3. Production and the contract dereference 32-bit snapshot records at packed
   offsets 131, 147, and 179. Replace typed packed access with aligned locals
   plus `memcpy`, and execute initialize with an alignment sanitizer.
4. The parser accepts interleaved alternates such as MI05 alt0, MI06 alt0,
   MI05 alt1, while the snapshot encodes contiguous per-interface ranges.
   Reject interleaving or group the output explicitly; add the two-interface
   counterexample.
5. Cleanup/removal can change upper state after successful lower select and
   before commit. Task 4 currently has no persistent lower claim state, so
   the immediate leak is absent; the controller must explicitly carry the
   transactional rollback requirement into Task 6 rather than silently
   treating this as future-safe.

## Minor

6. Select-URB construction always emits zero pipes. That is correct for the
   retained MI05 default alternate but inconsistent with generic valid default
   alternates that contain endpoints. Size and populate default pipes from the
   validated snapshot.

All three authorized gates passed, but the current fakes do not detect these
findings. R41/R42 changes were narrow and preserved the exact CP32 terminal
line. No claim, detach, set-configuration, or unrelated kernel change was
found.
