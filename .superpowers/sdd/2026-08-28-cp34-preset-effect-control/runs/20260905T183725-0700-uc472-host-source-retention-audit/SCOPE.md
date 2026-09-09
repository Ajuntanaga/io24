# CP34 UC 4.7.2 host-source retention audit

Timestamp: 2026-09-05T18:37:25-07:00
Status: offline, read-only source-availability audit

## Objective

Determine whether the exact UC 4.7.2 host artifacts needed to source-bind the
leading bytes of a valid live `Stat` record are still available locally after
the predecessor cursor-provenance checkpoint.

## Allowed

- Read the task-local CP34 handoff, reports, inventories, and manifests.
- Check the exact historical `/tmp` paths.
- Search bounded, named local roots by the exact recorded names and sizes.
- Hash the installed Universal Control comparison artifacts.
- Update task-local Markdown and checksum records.

## Forbidden

- Network access or artifact download.
- Wine or any access to `/home/ajuntanaga/.wine-io24`.
- Loading or executing vendor binaries.
- USB/device, ALSA, preset/effect, reset, DFU, install, staging, flash, or
  firmware-image action.
- Treating the installed UC 5.0 module as the missing UC 4.7.2 source.
- Modifying or replaying the Linux `MemP/Stat` writer.

## Stop condition

Stop once the exact UC 4.7.2 artifacts are either found and hash-validated or
shown unavailable within the bounded approved roots. If unavailable, preserve
the exact hashes and state that reacquisition requires separate network
authority; do not infer the missing four-byte representation.
