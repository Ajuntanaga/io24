# CP34 UC 5.0 structured-state serializer comparison

Timestamp: 2026-09-05T20:00:05-07:00
Status: offline static comparison; not UC 4.7.2 closure

## Objective

Trace the installed UC 5.0 host module far enough to determine the exact
leading representation produced by its structured-state serializer before a
host `MemP/Stat` save message is fragmented. Use this only to form a
version-local comparison and a precise future UC 4.7.2 tracing target.

## Source identity

- `/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll`
- expected size: 4,984,704 bytes
- expected SHA-256:
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`

## Allowed

- Read-only PE parsing and x86-64 disassembly of the pinned installed module.
- Read-only comparison with the durable UC 4.7.2 report and inventories.
- Hardware-free analyzer/test implementation and task-local documentation.
- In-memory access to the already pinned firmware only if needed to compare
  interfaces; do not emit an image.

## Forbidden

- Treating UC 5.0 behavior as proof of UC 4.7.2 behavior.
- Network access or reacquisition of the missing UC 4.7.2 artifact.
- Loading or executing any vendor binary.
- Wine or access to `/home/ajuntanaga/.wine-io24`.
- USB/device access, interface claim/detach, transfer, ALSA, capture,
  preset/effect mutation, reset, DFU, install, staging, flash, or firmware
  emission.
- Changing or replaying the Linux `MemP/Stat` writer.

## Stop condition

Stop after either source-binding UC 5.0's leading serializer bytes with exact
addresses and executable regression evidence, or recording that the bounded
static route remains unresolved. Preserve the UC 4.7.2 result as unresolved in
either case.
