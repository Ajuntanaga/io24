# Full io24 parameter verification plan

Status: atomic plan generated; no parameter result is accepted from USB-write
success alone

## Objective

Verify every control exposed by the Linux Host, every field transmitted by its
DSP/effect builders, every source/bus route, both physical channels, and every
Host persistence/reconnect path. The raw 117-entry vendor descriptor catalog is
also reconciled so duplicate, read-only, host-model, and unreachable entries are
accounted for instead of silently omitted.

The executable plan is
`PARAMETER-VERIFICATION-MATRIX.json`, generated and validated by
`build_parameter_matrix.py`. It currently contains **750 atomic rows**:

- 142 Fat Channel parameter/targeting rows;
- 60 VoiceFX user-parameter rows, once for each possible physical owner;
- 42 generic backend mixer-cell rows (level and assignment), including the
  three `line/ch3` bus cells whose applicability to the two-input io24 must be
  resolved rather than assumed;
- 52 Host-owned multiband rows;
- all 117 retained legacy descriptor records;
- 211 concrete io24 component-model routes; and
- native controls, shared reverb, Host state, telemetry, serializer, factory
  preset, reconnect, and disconnected-persistence rows.

The 117 descriptor rows and 211 component-route rows are reconciliation rows,
not claims that the io24 has 328 additional knobs. Each must point to exactly
one operational row or end with an evidence-backed read-only, duplicate,
derived, host-only, not-on-io24, or unknown classification. A missing mapping is
a failed completeness gate.

## Authority and hard limits

The user granted full live authorization on 2026-09-06 for this exhaustive
verification on the one connected Revelator io24, serial AB7C22200355, firmware
descriptor 0x0128. USB control, bounded ALSA playback/capture, Channel-2 test-slot
save/recall, Host restart/cache operations, and requested physical A/B actions are
in scope. Wine and the protected Wine prefix remain forbidden. Firmware, DFU,
reset, installation, network, and unknown/unmapped writes are not required and
remain out of scope. Stop all forward work at or below 10 percent workstation
battery, on identity drift, on clipping, on a USB/audio timeout, or if the device
enumerates as bootloader 194f:0405.

If bootloader `194f:0405` appears, stop all work. Recovery is a cold power
cycle at the device end, a wait of about 15 seconds, and confirmation that the
kernel recorded a USB disconnect; a powered-hub replug may not reach the
device. Do not attempt DFU: the interface reports `Upload Unsupported`, so it
is not a recovery path. The historical trigger was sustained playback/capture
concurrent with control writes; P0 item 6 structurally forbids that overlap.

Only Channel 2 global slot 3 may be overwritten for the device-resident test.
Channel 1 slot bodies and global slot 0 are never written.

## What counts as verified

Each matrix row receives exactly one terminal status:

- `PASS_READBACK`: min/nominal/max or off/on writes produce the exact readable
  device state twice, preserve the other channel, and restore exactly.
- `PASS_AUDIO`: a write-only DSP/mixer parameter produces the predeclared,
  repeatable signal-domain change in two A/B brackets with no clipping and an
  appropriate same-path positive control, then its inverse is replayed.
- `PASS_FRONT_PANEL`: a display-only/write-only mode agrees with the unit's
  front-panel indication and declared safe readable transitions; it makes no
  audio claim.
- `PASS_HOST`: a Host-only control passes deterministic local behavior plus GTK
  binding/state synchronization and restart/reconnect behavior where applicable.
- `PASS_PERSISTENCE`: content survives the declared close/reconnect or cold-power
  boundary and is recalled without a Host write during the observation window.
- `FAIL`: the observation contradicts the promised behavior under a valid rig.
- `INCONCLUSIVE`: the rig or positive control cannot discriminate the behavior.
- `NOT_APPLICABLE`: the catalog entry is read-only, duplicate, derived, or not a
  parameter on this model; the evidence for that classification is cited.

A row is not complete until the inverse/restoration step has run. For write-only
state, `WRITE_SENT_NOT_READABLE` is recorded in addition to the audio result; it
is never upgraded to device readback.

Continuous parameters are tested at safe low, nominal, and high points plus an
out-of-range clamp test. Time/frequency/threshold parameters additionally need a
monotonic sweep or temporal/spectral measurement. This verifies each parameter,
not every floating-point value in its continuum.

"Without doubt" therefore has an operational meaning here, rather than an
impossible claim about every real number in a continuous range. A supported row
must pass all applicable layers below:

1. **Definition:** exact model, range, units, enum labels, clamp, ownership, and
   applicability are source-bound. A guessed formula or unresolved vendor typo
   cannot pass.
2. **Serialization:** boundary/default/representative inputs produce the exact
   expected wire bytes and ordering twice; malformed and non-finite inputs are
   rejected before transport.
3. **Transport/readback:** the intended block, index, channel, and instance are
   addressed. Readable values return the exact bit/integer or expected float32
   value. Write-only blocks remain labelled `WRITE_SENT_NOT_READABLE`.
4. **Effect:** an objective capture shows the predeclared acoustic result in two
   randomized A/B/A brackets. Host meters or a successful call are not enough.
5. **Isolation:** the non-target channel and non-target buses remain at baseline.
6. **Persistence:** where persistence is promised, the result survives the
   declared Host-close/reconnect/cold-power boundary without a Host write.
7. **Restoration:** readable state returns exactly; write-only state receives its
   predeclared inverse and the audio baseline returns within tolerance.

No ambiguous row is rounded up to a pass. It stays `INCONCLUSIVE`, and the
campaign stays open.

## Fixed objective thresholds

Thresholds are declared before looking at results:

- readable integer/bit controls: exact equality; float controls: expected
  float32 value or documented quantization;
- mixer gain: requested relative change within 0.35 dB, with the other two buses
  below the calibrated leakage floor;
- EQ/HPF: measured response within 0.75 dB of the exact transmitted biquad at
  the discriminating frequencies, with monotonic cutoff movement;
- output/delay effects: spacing within one sample for DSP delay and within the
  known 2 ms quantization for output delay;
- dynamics: threshold within 1 dB and measured attack/release within 10 percent
  or 2 ms, whichever is larger; gain-reduction telemetry must move with the
  independently captured envelope;
- level restoration: within 0.25 dB and 0.995 normalized correlation of the
  original baseline where a linear path is expected;
- all captures: no sample above -6 dBFS, no feedback growth, and two matching
  trials. Any clipped capture is discarded and the batch is stopped.

The mixer off sentinel is `None` (`-145.0` dB on the wire). A finite dB value
is never off: numeric requests clamp into `-144.0..+10.0`, and `-144.0` remains
a signal-passing floor fader. Clamp probes must declare the expected wire bound
and may never be scored as silence or off. The invalid JaSt slot-14 minus
slot-4 ratio metric is retired; only pinned-stimulus absolute level and
correlation measurements are valid here.

VoiceFX has model-specific signatures: Transformer requires its decoded shelf
response plus tail/width behavior; Detuner requires the expected pitch ratio
within 10 cents; Vocoder requires carrier/type-dependent bands; Ring Modulator
requires the predicted sum/difference sidebands; Filters requires the predicted
comb delay, decay, and damping changes; Delay requires its echo spacing and
feedback series. Shared reverb requires predelay, high-pass movement, and a
decaying tail clearly above the bypass floor.

## Execution order

### P0 — freeze the environment and restoration evidence

1. Before a separately authorized measurement session, cold-start the io24 at
   the device end and confirm `194f:0422`, bcdDevice `0x0128`. This is a
   declared future precondition, not authority to perform the action now.
2. Close every existing io24 controller and prove exclusive ownership.
3. Pin battery, USB ID, serial, firmware, ALSA card/rate/channel map, source
   hashes, and process identities.
4. Preserve the stale cache, clear it without a USB write, and start from a
   deliberately constructed state rather than replaying it.
5. Snapshot all readable JaSt state before each batch. For write-only state,
   write the forward and inverse calls into the ledger before the forward call.
6. Run no spectrum process and no continuous control polling during audio
   capture. Control writes settle first; each playback/capture is short and
   bounded; then control resumes.

### P1 — static completeness and GTK binding audit

1. Regenerate the 750-row atomic matrix and fail if any current public setter,
   GTK control binding, FX builder field, mixer source/bus pair, vendor
   descriptor, or exact component-model route is unclassified.
2. Verify units, clamps, serializer bytes, model-before-state ordering, channel
   indexes, and inverse calls in hardware-free tests.
3. Preserve the repaired Host boundaries before a live row can exercise them:
   `phonesSrc` is exposed through the public setter, daemon, scene, GTK, and
   UCNET paths but remains write-only; Host Hot Key is implemented as a
   source-bound Host snapshot override; and Passive/Vintage factory EQ is
   fail-closed for direct-live replay because no exact alternate-model builder
   exists. The Standard high-shelf builder is source-bound and bit-exact to the
   retained UC 4.7.2 selector-9 double designer. The Passive low-frequency list
   contains the literal vendor string `20kHz`, which must not be silently
   reinterpreted.
4. Fix any missing/broken Host binding before its live row can run. An
   unsupported applicable control is a failure, not `NOT_APPLICABLE`.
5. Launch the repaired GTK Host only after the backend batches are complete;
   test every widget against an instrumented fake and then against the same live
   state. Programmatic sync must not emit a write.

### P2 — establish a deterministic safe audio rig

Use the free end of the cable already in Channel 2 as a physical loopback from
Main Left to Channel 2. Phantom power must be off, Channel-2 gain begins at 0 dB,
monitor volume begins low, and Channel 2 is removed from Main throughout the
measurement to prevent feedback. A level-limited 48 kHz stimulus is played on a
USB return to Main; processed Channel 2 is routed only to Mix A, whose expected
USB 3-4 capture pair is confirmed by correlation across all six captured
channels. The physical Input-2 reference channel is recorded separately and is
not misclassified as routed leakage. Other Mix-A contributors are hard-off.
Calibration must show a
clean, non-clipping direct impulse and multitone before DSP rows begin.

The stimulus set is fixed before looking at results:

- impulses for delay, predelay, attack, release, and VoiceFX repeats;
- stepped sines / logarithmic sweep for gain, EQ, HPF, key filters, detune,
  vocoder carriers, ring modulation, and resonator pitch;
- stepped levels and shaped noise for gate, compressor, limiter, and reverb;
- stereo-identifiable tones for link, pair balance, monitor blend, and routing.

### P3 — readable controls and routing foundation

Test readable live controls first: both gains, both phantom states, both input
mutes, headphone/software output mute, headphone and Main volume, monitor blend,
stereo link, processing-channel permutation, both preset enable states, and both
slot selectors. Preset mode and the input high-pass enable are write-only and
receive front-panel/audio evidence instead of a fabricated readback claim.
Firmware 1.28 exchanges the two active `Pari/16` slot-index values after a
`Pari/12` processing-channel change. That declared side effect is not a failure;
restoration must replay the inverse `Pari/12` and confirm both indexes returned.
Slot-selector readback remains a selector claim only, never recall evidence.

Then test the 18 source/bus level cells and 18 assignment states exposed by the
io24 Host, three bus-master folds, six valid stereo-pair balance combinations,
and both mirror-main actions. The generic backend's three `line/ch3` cells and
three assignments remain separate applicability rows: the exact Michael/io24
component model has two analog inputs, so they cannot be counted as working
routes without contrary device evidence. Every operational row checks bus
isolation; Mix A must appear only on USB 3-4 and Mix B only on USB 5-6.
Independent mono input pan is unavailable because the device exposes one scalar
per source/bus; linked pair balance must work at left, center, and right without
the old one-leg attenuation bug.

### P4 — Fat Channel on both physical channels

For Channel 1 and Channel 2 independently, with the other channel as a guard:

1. Low cut: bypass plus low/nominal/high cutoffs and spectral monotonicity.
2. EQ: all four bands; off, peaking, low shelf, high shelf, high-pass, and
   low-pass shapes; frequency, gain, and Q at safe boundary/nominal points.
   Overall enable, individual band enable, and both DSP sub-instances are
   explicit obligations. Standard, Passive, and Vintage factory-model fields
   are separate rows; no alternate model may be flattened into Standard.
3. Gate/expander: on, threshold, range, attack, release, key frequency,
   expander mode, and key listen; reduction telemetry must agree with audio.
4. Compressor: Standard, Tube, and FET mappings; on, threshold/drive, ratio,
   attack, release, makeup/output, knee, auto mode, Tube limit mode, key
   frequency, and key listen. Loud FET cases are level-limited before monitors.
5. Limiter: bypass/on, threshold, release builder behavior, reduction telemetry,
   and no cross-channel change.
6. Compressor/EQ order: a deliberately non-commutative stimulus must distinguish
   both orders; selector-only success is insufficient.

### P5 — shared reverb and every VoiceFX model field

Shared block-202 reverb is the positive control: off/on, size, wet mix, input
high-pass, and predelay; Channel-1 and Channel-2 sends separately and together;
FX return to Main, Mix A, and Mix B with assignment and level behavior. Character
presets and movement are Host mappings and must be separately verified as such.

VoiceFX is tested with ownership assigned first to Channel 1 and then Channel 2.
For all six models, test bypass/on and every transmitted field listed in the
inventory. Each model needs a distinctive objective signature and two A/B
brackets. `VoFx` selection, payload acceptance, or a stored JSON class ID alone
does not pass audibility. Failure of the same-path block-202 positive control
makes the row inconclusive, not negative.

A prior positive-controlled block-201 negative exists from 2026-08-11:
VoiceFX measured `-0.3 dB` while same-path block-202 reverb measured `+6.0 dB`,
two runs agreed, and preset recall did not open the gate. A dry result here is a
second independent audibility negative, not a new finding; byte correctness,
transport acceptance, storage, and recall remain separate questions.

Each VoiceFX model also gets a complete serializer row and a disconnected
Channel-2 slot-3 recall row. This separates five questions that have repeatedly
been conflated: correct model bytes, accepted transport, active owner, audible
processing, and nonvolatile recall.

### P6 — Host state, presets, and reconnect behavior

1. Save/load a Host JSON preset containing every supported category; mutate all
   rows; reload; verify readable state exactly and write-only state by audio.
2. Verify old alias/one-leg-pan migration, unknown-route parking, assign-without-
   level materialization, slot-before-DSP replay ordering, and explicit
   Reapply/Forget behavior in the real GTK Host.
3. Test preset modes 0/1/2, enable/bypass and both selectors on both channels,
   while never writing a Channel-1 slot body.
4. Keep the `MemP` receiver ambiguity explicit. The only 2026-08-10 live
   `MemP`-tagged `SetP` observation reached a cache-invalidation handler with no
   payload; the distinct CP34 `{0,0}/0x420bc/0x531e0` receiver is static and has
   not been confirmed live. A dry result must identify the exercised receiver
   before attributing failure to storage, parsing, activation, or recall.
4. Write one complete tagged record only to Channel-2 global slot 3; recall it
   with physical Channel-2 controls; require the selected VoiceFX and Fat Channel
   signature while the Host is closed.
5. Repeat the slot-3 record/recall boundary for each of the six VoiceFX models
   and shared reverb, always reusing only slot 3 and preserving Channel 1. This
   is intentionally separate from ordinary live parameter testing.
6. Disconnect from the computer and cold-power the device from a non-computer
   source. The project stopping-point success is hearing the saved effect/reverb
   on Channel 2 with no Host attached. If dry under a valid positive-control rig,
   record the exact failing persistence/activation boundary as unresolved rather
   than guessing which internal stage failed.

### P7 — Host-only controls and final restoration

Verify supported sample rates and PipeWire quantum requests, device identity and
channel-name display, meter/GR presentation, page-gated spectrum lifecycle,
offline/reattach behavior, and every multiband crossover/band control on the
Host-created PipeWire sink. These are explicitly separated from device firmware
claims.

Restore all readable controls exactly. Replay every write-only inverse in reverse
order, park capture-only routes, close the Host cleanly, and produce a hashed
matrix whose rows link raw evidence, analyzer output, GTK binding evidence, and
restoration status. Any unclassified or nonterminal row keeps the campaign open.

## Batch discipline

One controller owns the device. Each live batch contains a prestate snapshot,
the finite row IDs being tested, forward and inverse calls, capture hashes,
analysis, a poststate snapshot, and a restoration verdict. A later batch cannot
start if the prior one is not restored.

`deterministic_audio_rig` is a per-batch token, not a campaign-wide fact. Each
audio batch re-verifies its same-path positive control at open and close. If the
closing control does not reproduce the opening control within the level-
restoration tolerance, every row in that batch becomes `INCONCLUSIVE`; a future
retry requires a rebuilt rig and separately authorized cold start.

The run order minimizes repeated setup and risk:

1. hardware-free serializer/catalog/component reconciliation;
2. readable native controls with no audio;
3. calibrated loopback and routing cells;
4. Channel 1 Fat Channel, then exact restoration;
5. Channel 2 Fat Channel, then exact restoration;
6. shared reverb and Channel-1/Channel-2 ownership tests;
7. all VoiceFX fields in randomized model batches;
8. Host JSON, GTK, reconnect, sample-rate/quantum, and multiband rows;
9. Channel-2 slot-3 save/recall and disconnected cold-power acceptance;
10. global reverse-order restoration and a final no-delta audit.

The only required user interventions are the deliberately announced physical
loopback, front-panel preset-button actions, computer disconnect/cold power, and
supplementary listening. Objective capture remains the primary oracle.

## Immediate gate

P0 is partly complete: the stale Host was found, closed, and its final cache was
preserved; the cache is now empty. The Host remains closed. Before P2/P3 audio
rows, the physical Main-Left-to-Channel-2 loopback must be confirmed deliberately
and monitors must be down/off. Channel 2 will be removed from Main throughout the
measurement to prevent feedback. Until that confirmation, only P1 static
completeness and read-only P0 evidence may continue.
