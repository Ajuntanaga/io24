# Remaining VoiceFX model result

Status: `VOICEFX_REMAINING_MODELS_PROCESSING_DETECTED`

The authorized Main-L -> Input-1 waveform run is valid and complete. The
Linux Host fully materialized Transformer, Detuner, Vocoder, Ring Modulator,
and Filters while off, then operated each model's own `On` field through two
independent on/off cycles. All five produced repeatable processing. Together
with the preceding Delay run, every VoiceFX model is now hardware-verified on
this Host path.

## Rig validity

- physical Input-1 burst level: -22.353 dBFS;
- gated-source contrast: 19.525 dB;
- maximum source drift across VoiceFX-off stages: 0.0065 dB;
- maximum off-state return burst drift: 0.0065 dB;
- same-return reverb positive control: +11.708 dB gap rise;
- `run_valid: true`.

## Model results

- Transformer: gain-normalized spectral change 7.201 and 7.448 dB;
- Detuner: both programmed -8-semitone partners appeared twice. The 800 Hz
  tone moved to 503.97 Hz with +41.135/+40.304 dB target rise, and the 1234 Hz
  tone moved to 777.37 Hz with +34.941/+33.872 dB rise;
- Vocoder: gain-normalized spectral change 11.521 and 11.821 dB;
- Ring Modulator: the programmed 313.7 Hz sidebands appeared twice, with
  maximum rises of +33.090 and +34.409 dB while guard bands did not rise;
- Filters: gain-normalized spectral change 4.218 and 3.856 dB.

The immutable live report initially returned `VOICEFX_MODELS_PARTIAL` because
the inherited generic Detuner test required a distant guard band to remain
within 3 dB. A pitch shifter redistributes broadband energy, so that condition
was over-strict. Both exact target frequencies were already present strongly
in both immutable captures. The corrected regression requires both predicted
tones to rise by at least 12 dB and stand at least 10 dB above local guards.
Reanalysis returns all five models detected; the raw report was not rewritten.

## Restoration

The exact io24 PipeWire sink returned to muted, Input 1 returned from the
guarded 60 dB to its exact 11 dB prestate, every protected readable device
field matched, and the Host-known Delay-on, reverb-off, and five changed
write-only routes were resent. Battery was 26% before and 23% after. No slot,
DSP Amount, `processingChannel`, phantom, link, firmware, reset, or DFU action
occurred.

## Evidence

- `attempt-1/live-report.json` (immutable raw live report), SHA-256
  `153a8c340f9ba8cacca8e4871b7e4d65a0302f8cb0f1821a9278b51d8e4abd22`;
- `attempt-1/corrected-verdict.json`, SHA-256
  `72454aa7b329dd69dcb2db70e41af6dbac572da74fc66a52c3c350f67dd8d7ee`;
- 28 immutable capture WAV files plus the exact stimulus;
- `re/io24_voicefx_model_waveform_probe.py` and its hardware-free regression
  tests.

No packet-builder correction was justified by this run: the common UC 4.7.2
selection/materialization and state-only edit repair already made the five
remaining models work. The only new defect found was in the first Detuner
analysis rule, and that classifier is corrected and regression-covered.
