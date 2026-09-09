# Universal Control 4.7.2 static host-module comparison

Timestamp: 2026-08-30T17:02:10-07:00

Status: offline static record source-bound, manifest-verified, and independently
reviewed clean; source retention is temporary; both CP34 observable outcomes
remain unresolved

## Scope and authority

This is the bounded, non-executing artifact continuation authorized by the
user's `proceed` after the 2026-08-30 CP34 resume. It records task-local hashes
and static outputs only. No vendor executable or DLL was loaded; no Wine,
network, USB, device, ALSA, firmware, installation, preset/effect, or physical
control action occurred.

The candidate installer and extraction remain under `/tmp`. They were not
copied into the project or treated as durable source retention. The JSON
inventories below preserve the exact analyzer output and bind it to the source
module SHA-256. Re-execution after `/tmp` cleanup requires reacquiring the exact
same source hash.

## Source identity

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `/tmp/PreSonus_Universal_Control_v4_7_2-108537.exe` | 186,792,552 | `1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95` |
| `/tmp/io24-uc472-extract.IHXUdb/Universal Control.exe` | 22,172,120 | `27f9fe550b466c9d783e3432d6663bb02af9aa001b23165985a56c96005e1a96` |
| `/tmp/io24-uc472-extract.IHXUdb/cclgui.dll` | 7,053,272 | `04cd73f8f6e65cd025c61b586b87c32093d75f3289e2d73e9e5ccf9b4506bd16` |
| `/tmp/io24-uc472-extract.IHXUdb/hwaccess/dspusbdevice.dll` | 4,979,672 | `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28` |
| pinned UC 5.0 `dspusbdevice.dll` | 4,984,704 | `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b` |

The PE version resource in `Universal Control.exe` reports both FileVersion and
ProductVersion `4.7.2.108537`. Candidate strings include `Revelator IO 24`,
`Stream Mix A`, `Stream Mix B`, `StorePreset`, `RestorePreset`, `VoiceFxOn`,
`Active Preset Slot`, and `Preset Slot 1` through `Preset Slot 4`. Those strings
establish that this is a feature-bearing Revelator-family artifact; they are
representations, not native transaction evidence.

## Target provenance

The 4.7.2 central queue starts at `0x180053420`. Its instruction prologue and
queue topology match the pinned 5.0 queue at `0x1800546b0`, with version-local
relocation. `objdump -p` names the 4.7.2 `WinUsb_WritePipe` import slot at
`0x1800e43f0`; the pinned 5.0 slot is `0x1800e53f0`.

The checked-in outputs were generated with the existing hardware-free analyzer:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py \
  '/tmp/io24-uc472-extract.IHXUdb/hwaccess/dspusbdevice.dll' \
  --target 0x180053420 --context-before 384

PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_host_queue_inventory.py \
  '/tmp/io24-uc472-extract.IHXUdb/hwaccess/dspusbdevice.dll' \
  --target 0x1800e43f0 --call-kind rip-indirect --context-before 384
```

## Candidate inventory

The candidate has exactly six direct central-queue callers:

| Call site | Bounded nearby ASCII immediates |
| --- | --- |
| `0x18003535d` | `FRst`, `Appl` |
| `0x1800497c1` | `JICC`, `JDvC`, `VoFx` |
| `0x180051065` | `MemP` |
| `0x180052e10` | none |
| `0x180052fca` | `Pari` |
| `0x18005308b` | `Pari`, `Para` |

It has exactly three RIP-relative consumers of the named writer import:
`0x18007700b`, `0x1800775ad`, and `0x180083a98`.

The pinned 5.0 module independently reproduces six direct callers and three
writer consumers. Its bounded queue contexts are `FRst`/`Appl`,
`JICC`/`JDvC`/`VoFx`, `MemP`, `Pari`, `Pari`/`Para`, and
`GetP`/`SetP`. The paired rows are version-local structural correspondences;
the ASCII scanner is context evidence and does not assign function semantics
by itself.

## Path-by-path correspondence

The queue counts are reconciled with the named control paths rather than used
alone:

- The candidate request handler references `RestorePreset` at `0x18003af68`
  and `StorePreset` at `0x18003b3cc`, exactly corresponding to pinned 5.0
  sites `0x18003b6c8` and `0x18003bb2c`. The `presetTarget` references and
  `RenamedPreset` notification remain in the same branches.
- Candidate helper `0x180037250` builds `PrsM` plus `Appl` and invokes owner
  vtable slot `+0x10` at `0x1800372b7`, matching pinned helper
  `0x1800379b0` and its call at `0x180037a17` instruction-for-instruction.
- Candidate owner vtable `0x1804393e0` maps slot `+0x10` to
  `0x180050f10`. That builder writes `MemP`, length `0x7ec`, the same fragment
  fields, and queues through `0x180053420` at `0x180051065`. This is the
  version-local counterpart of pinned builder `0x180052270` and call site
  `0x18005238e`; it is still the already-reconciled `MemP | PrsM` envelope.
- Candidate `Stat` records 0 through 3 are built at `0x18003372e`,
  `0x18003375a`, `0x18003378c`, and `0x1800337be`; each dispatches through
  vtable slot `+0x18`. Candidate dynamic `Stat` builder `0x180042231` also
  retains its virtual target. These correspond to the pinned enumeration-like
  paths, not the `PrsM` update slot, so they do not establish assignment.
- Candidate Voice FX model function `0x180049260` constructs a 16-byte `VoFx`
  payload for block 201 and queues it at `0x1800497c1`. The scene serializer
  still checks byte `+0xe6` and copies `VoiceFxOn` at `0x18003bb6c`; that site
  does not queue an enable operation. Both paths are structurally equivalent
  to the pinned 5.0 paths.

Thus the feature-bearing 4.7.2 build preserves the pinned Store/Restore,
`Stat`, and Voice FX control shapes. It does not expose a version-only native
save, assignment, or explicit Voice FX gate path through those seams.

## Result and boundary

The 4.7.2 candidate retains the same six-caller/three-writer topology as the
pinned 5.0 module. It adds no distinct queue caller whose bounded context names
`Stat`, a slot assignment, a save-point operation, or an explicit Voice FX
enable operation. The existing `MemP` and `VoFx` families remain subject to the
already sealed firmware and host-state reconciliation.

This closes the seam-bounded claim that the recovered 4.7.2 module contains an
obvious additional native sender through the compared seams that is absent from
5.0. It does not prove a product-wide capability negative, rule out behavior
hidden behind an existing generic caller, establish a rendered Universal
Control interface, establish device synchronization, or resolve either CP34
outcome. No packet is inferred or made eligible for replay from this static
result.

The prior disposable runtime experiment is excluded from this seal. Process
`RUNNING`/alive state was not synchronization, and the current instructions
prohibit continuing Wine during io24 work.

## Verification

Fresh verification for this record:

- `PYTHONDONTWRITEBYTECODE=1 python3
  tests/test_cp34_host_queue_inventory.py -v`: 3 tests passed.
- Both analyzer commands above reproduced their checked-in JSON byte-for-byte.
- The complete hardware-free CP34 suite returned 104 passed and 38 subtests in
  181.84 seconds, exit 0.
- `SHA256SUMS`: 10/10 entries verified before the final report-status update;
  the final report hash was then refreshed and the manifest rechecked.
- Passive sysfs reported BAT0 at 94 percent, charging.

The scoped independent review then reproduced all five artifact sizes and
hashes, both candidate analyzer outputs byte-for-byte, the pinned 5.0
six-caller/three-writer baseline, representative `objdump` evidence for the
named paths, the three analyzer contracts, and the complete 104-test/38-subtest
hardware-free suite. The independent broad run completed in 310.87 seconds,
exit 0; all 10/10, 27/27, and 6/6 checksum gates also passed. The review found
no Critical or Important issues. Its sole Minor wording note was corrected in
the seam-bounded result above.

Final post-review controller verification returned 104 passed and 38 subtests
passed in 171.02 seconds, exit 0. Passive sysfs then reported BAT0 at 98
percent, charging.

These are offline evidence checks. They do not substitute for independent
observable proof or grant live authority. The static stage's scoped independent
review is clean.
