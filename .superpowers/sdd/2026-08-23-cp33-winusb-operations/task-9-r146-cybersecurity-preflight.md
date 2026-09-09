# Task 9 R146 cybersecurity preauthorization review

Timestamp: 2026-08-25T23:12:42-07:00

## Verdict

`PASS`

Critical findings: none.

Important findings: none.

Material Minor findings: none.

## Threat boundary

R146 is a test/fake proposal and adds no deployed production surface. The
security boundary under review is production-to-libusb least privilege on
rejection: zero backend calls for pre-backend rejection, and exactly the
retained active-config authority sequence for endpoint rejection.

Local hashes bind accidental workspace drift but are not cryptographic
signatures against a malicious same-user process capable of replacing an
artifact and its manifest together.

## Findings and evidence

R146 preserves the complete backend snapshots on exact success, function-scope
rejection, generic rejection, malformed admission, and the forked null-buffer
path. Its endpoint exception now requires both the exact API multiset and:

1. consecutive global ordinals in get-device, get-active-config, free-config
   order;
2. the expected device handle;
3. device-result to active-config-input identity; and
4. non-null descriptor-result to free-input identity.

The controller reproduced and rejected the three same-count authority attacks
in a separate disposable tree. The null-handle and substituted-device variants
each exited 1 with three failures. Reordered `free(NULL)` with omission of
the acquired descriptor free exited 1 with twelve failures. Each compiled
actual copied production, reached fake libusb, and emitted its pass marker.
Clean focused and retained replays pass, and copied production is restored.

The complete nineteen-mutant package additionally covers extra and omitted
endpoint calls; probes on exact, scope, malformed, null, and oversized reject
paths; success-status omission; caller mutation; synchronous control; resource
activity; membership/direction widening; and RANGE suppression.

## Hardening checks

- ABI-shaped count and record structures are identical between contract and
  fake; pointer observations use `uintptr_t`.
- Whole-record reset clears every journal field.
- All 32 exported `libusb_*` entries retain the first executable global
  witness; exactly three target increments immediately follow it.
- Only the eight individually checked journal observations are copied into the
  expected record before complete-state comparison.
- The patch adds no dependency, secret, credential, network, untrusted shell,
  device, prefix, staging, firmware, preset, or effect surface.
- No protected or live boundary was invoked.

## Maintenance constraint

The oracle intentionally freezes the audited three-call endpoint-validation
sequence. A legitimate future production change to that sequence must update
the count, ordinal, pointer-lineage, and executable-mutant evidence together.

