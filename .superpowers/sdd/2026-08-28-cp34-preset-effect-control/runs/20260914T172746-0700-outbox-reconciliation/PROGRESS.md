# Claude OUTBOX reconciliation and probe timing provenance

Status: `OFFLINE_COMPLETE; COLD_BOOT_STORED_FX_REQUIRES_AUTHORIZATION`

Commit `f39f1a8` is present and the pre-continuation working tree was clean. It
contains the joint block-201 lifecycle/audio/Host sequencing work and Claude's
five authorized live runs.

## Controlling result

- Host v2 selector replay: gate `-19.551 dB`; Ring Mod `-0.167 dB` against
  `1.722 dB`.
- Genuine streaming at observed 48 kHz / period 512: gate `-19.580 dB`; Ring
  Mod `+0.005 dB` against `2.038 dB`.
- Channel-2 discriminator: Ring Mod `+0.035 dB` against `2.054 dB`.
- Correct three-word `VFxO`: gate `-19.647 dB`; Ring Mod `-0.132 dB` against
  `2.724 dB`.
- The complete `Para`/`Pari` space, both primary block tags, gate fields,
  delegate, scheduler, Host v1/v2, idle/streaming, and channel ownership are
  closed by source or controlled live measurement.

## Offline correction after f39f1a8

`re/io24_corrected_fx_rebuild_probe.py` and
`re/io24_corrected_ringmod_probe.py` no longer report hardcoded 96 kHz/512
constants as measured Host configuration. Schema v2 records an unobserved ALSA
timing object with null rate and quantum because these meter-only probes open no
stream. Retained schema-v1 reports were not modified. The regression was first
reproduced by two failing tests, then fixed; focused result is 14/14. The full
hardware-free suite passes 873 tests with one expected historical-fixture skip;
the two pre-existing unclosed-file ResourceWarnings remain visible.

## Next boundary

Prepare and, only after fresh exact authorization, execute one device-resident
test: write a known Voice-FX-on slot body, choose it as the boot slot,
power-cycle, and have the user listen with no Host attached. Audible means
capture UC next. Inaudible means document firmware `0128` as insert-inert and
publish. Target slot/body/restoration must be chosen before requesting the live
authorization.

No USB, device, audio, Wine, network, power-cycle, commit, or push occurred in
this reconciliation.
