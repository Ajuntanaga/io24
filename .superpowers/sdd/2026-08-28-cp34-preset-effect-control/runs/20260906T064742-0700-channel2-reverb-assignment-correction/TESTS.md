# Verification

Timestamp: 2026-09-06T06:47:42-07:00

Status correction: these historical tests modeled an invalid assumption that
VoiceFX assignment renumbered physical preset controls. The successor runner
now enforces channel 2 for every preset call. The historical pass counts below
do not validate the attempted Channel-2 recall.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_cp34_channel2_reverb_slot_stage.py \
  tests/test_io24_preset_persistence.py \
  tests/test_io24_native_stat.py \
  tests/test_io24_factory_slap_action.py \
  tests/test_cp34_dual_private_reverb_slots.py \
  -p no:cacheprovider
```

Result: **61 passed, 12 subtests passed in 1.14s**.

Hardware-free plan command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_channel2_reverb_slot_stage.py
```

Result: exit 0, `OFFLINE_READY`, Channel 2, global slot 3,
`slot_zero_targeted=false`.

Complete hardware-free command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
```

Result: **272 passed, 1 skipped, 47 subtests passed in 713.06s**, exit 0.

## Post-attempt slot-swap correction

The first live attempt exposed the missing firmware behavior before any record
write. The corrected runner test models the exact `Pari/12` side effect and
covers both a default assignment and an already-Ch2-assigned baseline.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_cp34_channel2_reverb_slot_stage.py \
  tests/test_cp34_doubler_reverb_static.py
```

Result: **21 passed in 0.46s**.

The pinned firmware analyzer also passed against the exact 1,104,448-byte
firmware 1.28 image, including the new `0x2e77a`, 66-byte slot-swap slice SHA-256
`4fed3b4674f89b8a94498cf064f9e38fc8f5336da454bff5aeb399b9c4ae1093`
and four instruction anchors showing wire id 16 replayed for target indexes 0
and 1. Python compilation and the corrected dry run both exit 0.

## Corrected live stage

The separately authorized corrected command exited 0 with
`STAGED_FOR_STANDALONE_LISTENING`. Battery was 100 percent; identity, assignment,
slot-family, bypass, target slot 3, enable, link, and other-chain preservation
checks passed. Transport reported one fragment sent to slot 3 and zero replies,
as expected for the fire-and-forget write. Exact output is retained in
`LIVE-ATTEMPT-2.json`; disconnected persistence and audibility are pending.
