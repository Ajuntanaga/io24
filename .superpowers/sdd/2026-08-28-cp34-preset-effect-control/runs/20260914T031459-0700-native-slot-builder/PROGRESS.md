# Native slot builder continuation

## Continuation result: exact Passive Program EQ seam

The final coefficient-model gap is closed offline. The retained UC factory
collection contains a real Passive **Big Vocal** record; it provides all eight
semantic controls and the class GUID rather than a guessed parameter set.
`re/uc472_passive_eq.py` interprets UC 4.7.2's combined high designer at
`0x18001a610` and combined low designer at `0x18001adb0` directly from the
pinned DLL.

The high routine writes seven floats and is emitted by UC as `Lfdf` index 0;
the low routine writes five floats and is emitted as `Bqdf` index 1, while
indexes 2/3 are identity. Firmware native slot 2 independently has exactly
that layout shape. The builder emits all four stored clock sections and its
record wrapper changes only the native `eq  ` coefficient ranges. At 48 kHz,
the Big Vocal low and high vectors are pinned as exact regression values in
`tests/test_uc472_passive_eq.py`.

The actual selector orders are 20/30/60/100 Hz, 3/4/5/8/10/12/16 kHz, and
5/10/20 kHz. UC's first low label literally reuses `20kHz`; the low circuit
branch and EQP-1A control identify the intended value as 20 Hz. The Host's
read-only alternate-EQ page now presents those decoded positions and friendly
Passive control names.

This is still an offline executable seam because it depends on the retained
vendor DLL. It does not reopen the live writer route closed by the two device
nulls, and no device operation was used here. The decoded UI constants changed
`io24_scene.py`, so the deterministic 709-row parameter matrix was regenerated;
its SHA-256 is
`9f79e1b91385013f338c903c4759aae72e23fc1452ac38b30f76170ee6d600c7`.

## Continuation opened

The user directed the work to proceed after the Vintage/native-payload
integration. The next bounded offline item is the remaining `filt` arithmetic:
turn the observed one-ULP differences into a failing golden test, recover the
exact UC 4.7.2 operation and rounding path, and use firmware slot 0 plus the
retained Piano scene as the oracle. Standard EQ selector coverage follows only
after that smaller gap closes. The peer inbox carries the same handoff. No live
or device action is part of this continuation.

## Continuation result: complete Standard native EQ leaf writer

The final Standard selector route is now source-bound. An enabled first band
selects table index 1 / designer 8; `re/uc472_standard_lowshelf.py` binds the full branch at
`0x18001028a`, and `io24.biquad_lowshelf()` transcribes its binary32 inputs,
binary64 operation order, and five independently narrowed binary32 outputs.
The Broadcast band-1 48 kHz transcription vector is
`f8e57f3f3cf0fe3f70f0febfede47dbf8dfe7d3f`. A discriminating
18 kHz/+15 dB/Q10 vector proves the former generic shelf route is not a safe
substitute.

The three source-bound Standard designer transcriptions are composed into a
complete native EQ leaf. `design_standard_eq()` validates a Standard tagged scene and emits all
four sample-rate sections. Native `low-mid`, `hi-mid`, and `high` carry scene
bands 2, 3, and 4; native `wide` carries scene band 1 plus two zero third-order
coefficients. Disabled bands are identities. The record-level
`build_native_standard_eq_stat_record()` changes only the `eq  ` leaf in a
validated native base, retaining every other Fat Channel and Voice FX byte.

Low-shelf TDD was RED with five failures before implementation and GREEN with
seven focused tests. The record composer was RED with two missing-function
failures and GREEN in the native/Standard focused set. This closed the complete
Standard-EQ portion of the offline native writer. At that checkpoint Passive
EQ remained unmapped, and Vintage remained an offline pinned-DLL builder rather
than a running-Host dependency. No live or device operation occurred.

Proof limit: the regression vectors are computed by the recovered instruction
order with Python `math`; they are not independently captured UC coefficient
output. A native UC `Bqdf`/`Stat` capture or explicit UCRT/vendor-trig
equivalence remains necessary before claiming bit identity.

Independent review found one implementation defect: tagged-scene toggles were
initially interpreted with permissive Python truthiness. The shared Standard EQ
validator now accepts only booleans or numeric 0/1, and validates all frequency,
gain, and Q fields as finite/in-range even while EQ is disabled. Tests also now
exercise enabled band-4 high shelf and outer-band peaking through the native
composer. Final affected verification passes 151 tests and 130 subtests. The
broad run passed 768 tests plus one expected skip before finding only a stale
generated-matrix artifact; after regeneration, the 709-row determinism and
affected suites pass. Matrix SHA-256 is
`39522b66f95905b4b7ef8b8186a43c2e0bd4e0e5fb257b9b87ad054e6a38786b`.

## Continuation result: exact Standard peaking and native HPF edit seam

The retained passive pcaps are enumeration/control-URB captures and contain no
interface-5 bulk `SetP` traffic, so they cannot provide an independent `Bqdf`
golden. The exact UC 4.7.2 `FilterComponent` route is nevertheless settled:
the constructor selects designer 3, the Standard double designer computes the
bilinear high-pass, and the common output path narrows five doubles to floats.
Transcribing the available Windows UCRT small-angle `tan` polynomial produces
the same binary64 values as Python/glibc at all four tested clocks.

This disproves the earlier UCRT explanation for the firmware-default ULP
differences. The embedded slot-0 vectors are not one canonical UC recompute:
17 of 20 coefficient words follow an all-binary32 calculation, while its 96
kHz set follows the binary64 UC route. The firmware record remains valuable as
a layout/round-trip fixture, but it is not an oracle to which the source-bound
UC semantic builder should be distorted.

The next Standard path is now executable. Standard middle bands retain table
index 3, designer selector 6. `re/uc472_standard_peaking.py` binds that route
and the branch at `0x18000fe4c`; `io24.biquad_peaking()` transcribes its exact
input narrowing, operation order, and output rounding. `set_eq_band()` and the
GTK response graph now use the same helper instead of the older approximate
`sin(w)/(2Q)` route. The Bright Vocal band-2 48 kHz vector is
`6ca37d3f6908f53f6908f5bf1d976abfb2f36c3f`.

The native `filt` component also now has atomic four-clock coefficient access.
`set_filter_coefficients()` requires all 44.1/48/88.2/96 kHz biquads, narrows
them to finite binary32 values before mutation, and replaces coefficient bytes
only; structural words, flags, rate labels, and trailing bytes remain from the
validated base.

TDD peaking: RED 6 failures, GREEN 6 passes. TDD filter seam: RED 2 failures,
GREEN within a 58-test focused native/Standard/Vintage set with 82 subtests.
No live or device operation occurred. The selector-8 low-shelf gap recorded at
this intermediate checkpoint is closed by the continuation result above.

## Result

Claude's final UC 4.7.2 finding is now executable through the native record
codec rather than left as isolated reverse-engineering evidence.

- `eq  ` is fully accounted for: 22 coefficient floats at each of 44.1, 48,
  88.2, and 96 kHz, ordered `low-mid`, `hi-mid`, `high`, and seven-float
  `wide`. The two formerly labelled padding floats are real coefficients.
- `re/uc472_vintage_eq.py` runs the pinned vendor designers for a complete
  Vintage EQ, produces all four clocks, replaces only coefficient bytes in a
  complete native EQ leaf, and returns a validated complete native `Stat`
  record while preserving every other component.
- Native `gate` and `comp` states now expose exact live-blob seams. Firmware
  slot 0 matches `Piano Accomany.scene` Channel 2 gate state 0 and FET
  compressor state 0 byte-for-byte at 44.1 kHz; all four stored compressor
  side-chain biquads match the live builder. Either of the two stored states
  can be replaced without touching the other.
- The Vintage switch labels in the Host are now decoded values rather than
  guesses. Direct live Vintage editing remains paused because the executable
  analysis depends on the separately retained UC DLL.

## Writer boundary

The Standard EQ leaf is now a complete semantic `.scene` writer: its peaking,
low-shelf, and high-shelf selector routes are source-bound and all four sample
rates are emitted into a validated native record. The HPF's UC selector-3 route
is also source-bound; mixed historical firmware-default rounding is no longer
treated as the UC arithmetic oracle.

This was not yet a one-call arbitrary Fat Channel scene composer. Gate, FET
compressor, limiter, native component framing, Standard EQ, and Vintage EQ were
closed as offline component seams. At that checkpoint Passive EQ was unmapped,
and the Vintage path still required the separately retained pinned DLL. No USB,
device, audio, Wine, firmware, or network operation was performed.

## Verification

- TDD EQ seam: RED 5 failed / 17 passed; GREEN 22 passed / 58 subtests.
- TDD gate/comp correction: RED 3 failed / 9 passed; GREEN 12 passed / 28
  subtests.
- Final focused set: 115 passed / 103 subtests.
- Parameter matrix: 709 rows; generated twice byte-identically; SHA-256
  `dc92887d81594b29a800461c5174b1419260d0599f8475c29c84733f0fd17e1f`.
- Broad hardware-free suite: 754 passed, 1 expected skip, 224 subtests in
  179.96 seconds. The only warning is PyGObject's external
  `GLib.unix_signal_add_full` deprecation.

## Exact next item

The Standard coefficient family is closed. The next bounded coefficient-model
gap is Passive EQ; independently, the exact Vintage executor would need an
explicitly packaged runtime dependency before the ordinary Host could use it.
Do not attempt a live native write merely because the offline record validates;
the unreadable-slot overwrite and pinned restore remain a separate
authorization gate.
