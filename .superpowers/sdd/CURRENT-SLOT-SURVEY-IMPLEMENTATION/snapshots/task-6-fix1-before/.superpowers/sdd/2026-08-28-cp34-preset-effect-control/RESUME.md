# CP34 device preset and Voice FX continuation

Timestamp: 2026-08-29
Status: active; current-slot survey final fix wave offline-sealed, scoped
independent re-review pending before any authorization request

## Outcomes

CP34 has exactly two completion outcomes:

1. Save a custom preset into device-resident storage, assign it to a front-panel
   slot, recall it without an editor driving the state, and prove that it
   survives the declared recall boundary.
2. Select and control Voice FX so the effect is audibly present, then preserve
   and restore that state through the same preset workflow.

Host-only JSON persistence is useful predecessor work, but it does not satisfy
either outcome.

## Lane boundary

CP34 is an isolated continuation for presets, effects, firmware behavior, and
native control evidence. It does not resume the older driver-transport task
tree, inherit its review queue, or use its terminology as the framing for this
work.

The immutable predecessor is:

`.superpowers/sdd/2026-08-28-preset-effect-persistence/`

That predecessor established dependable host JSON round trips and prepared the
native capture tooling. Do not edit or reseal it from CP34.

## Evidence baseline

Confirmed:

- The device exposes four front-panel slot indexes. In dual mode channel 1
  cycles 0/1 and channel 2 cycles 2/3, and those transitions are readable.
- Universal Control scene data contains four complete slot records and twelve
  user-library records. Factory records include Voice FX state.
- The direct driver can select a slot and can serialize Voice FX parameters.
- Reverb is a working positive control.
- The internal preset component and Voice FX processing object have been
  located in firmware-derived analysis.
- Universal Control's `StorePreset` branch serializes a real
  `SetP | Appl | 0 | MemP | PrsM` packet, but the io24 firmware routes that
  exact packet to a root cache-republication handler that does not consume the
  nested preset record. It is not a device-resident save on this firmware.
- The only recovered host `Stat` 0..3 sequence uses an enumeration/read-like
  vtable slot, not the `PrsM` update slot, so it is not evidence of slot
  assignment.
- The driver now refuses `fx_on()` and `fx_off()` because their previous
  reverb-route writes could not activate or deactivate the Voice FX insert.
- `PROTOCOL.md` section 13s is a valid negative for an unidentified numeric
  slot recall followed by a direct block-201 re-arm. It did not verify that the
  selected slot named one of the active factory Voice FX records.
- Factory JSON record 4 is `Slap Echo`, with `voicefx.on=1`, a 150 ms delay,
  feedback 0.25, and mix 0.5.

Not yet proven:

- The native transaction that stores a user-library preset and assigns it to a
  device slot.
- The native state transition that opens the Voice FX processing path.
- Device-resident survival and audible Voice FX under a controlled recall.

No existing capture contains those transactions. Static component data proves
the representation, not the missing control sequence.

Static analysis is now exhausted for both gaps: the decoded external firmware
surface cannot reach the preset component, local Universal Control artifacts
contain no io24-specific slot-assignment action, and no known direct parameter
maps to the Voice FX gate flags. The supported-host differential capture is
not an available gate because this project is Linux-only.

The replacement Linux-native closure is now executable:

- `re/cp34_host_queue_inventory.py` statically analyzes the pinned PE module;
  it never loads or executes vendor code.
- `LINUX-OFFLINE-SHA256SUMS` pins the analyzer, contract, active CP34 records,
  and source vendor module for this continuation stage.
- The DLL has exactly six direct callers of its central queue at
  `0x1800546b0`: the local operation families are `FRst`, `VoFx`, `MemP`,
  `Pari`, `Para`, and the generic `SetP`/`GetP` wrapper.
- It has exactly three RIP-relative calls to the `WinUsb_WritePipe` IAT slot at
  `0x1800e53f0`: `0x1800780db`, `0x18007867d`, and `0x180084ac8`.
- There is no queued `Stat`, slot-assignment, save-point, or Voice-FX-on
  operation. `MemP` remains the cache-refresh envelope already ruled out by
  the firmware handler trace.
- The generic base method at `0x180055570` is not present in the active device
  subobject vtable `0x18043a678`; its runtime slot `+0x10` is the known
  `SetP`/`GetP` builder at `0x180055410`.

Combined with the closed firmware ingress map, the pinned Universal Control
module contains no distinct operation capable of device-resident preset store
or assignment, and no explicit operation that opens the Voice FX gate. This is
a capability-negative for this host-module/firmware pair, not permission to
guess a replacement packet.

The remaining factory-recall question now has an offline-executable gate:

- `LINUX-LIVE-MATRIX.md` requires an already-assigned, device-screen-verified
  `Slap Echo`; it never assigns or stores a preset.
- `re/cp34_live_matrix.py` generates the fixed impulse stimulus, validates a
  target-specific restoration ledger, and analyzes two dry brackets, two
  active captures, and a reverb positive control without opening hardware.
- The deterministic stimulus SHA-256 is
  `318786a6af910736dbe8f96d152753884dac6fe360b8ad1e8a685b3077d68142`.
- The ordinary driver shadow has candidate reverb/FX-mix inverse values, but its
  2026-08-23 state is not current-attested and has no explicit assign/master
  rows. It is not yet restoration authority.

The earlier standalone `analyze-slot` delta was reviewed and bounded. The
following paragraph is historical classifier evidence, not a review of the
current-slot procedure or restoration verifier:

- A repeatable audible 150 ms dry/active delta is
  `SIGNATURE_PRESENT` / `REPEAT_150MS_SIGNATURE`, not a `Slap Echo` title or
  model identification.
- The report fixes model identity to `UNRESOLVED` and title verification, live
  readiness, and restoration verification to false.
- A repeatable late tail is `NON_SPECIFIC_LATE_TAIL` and remains inconclusive;
  its source and loaded model are not inferred.
- The focused hardware-free suite passes 37 tests.
- The combined CP34 hardware-free regression set passes 63 tests and 27
  subtests; both pinned DLL inventories reproduce six queue callers and three
  native-writer consumers, and every offline checksum entry verifies.
- This classifier reads already-acquired WAV files only. The later current-slot
  procedure and executable restoration contract now exist, but their final fix
  wave is awaiting scoped independent re-review. Neither creates authority to
  acquire files or touch hardware.

L01 read-only discovery is now partially complete:

- The user authorized USB identity, interface-5 PRESTATE reads, and ALSA
  identity/mapping only on the single connected io24.
- The named target is `AB7C22200355`, USB `194f:0422`, sysfs `1-2`, bus 001
  device 003, `bcdDevice 1.28`.
- One bounded interface-5/alternate-1 claim produced four consistent 503-slot
  JaSt reads. Channel 1 was slot 0 enabled; channel 2 was slot 2 enabled;
  phantom was off on both inputs.
- ALSA exposed `R24` card 2 device 0 with six-channel S32_LE/24-bit 48 kHz
  capability; no playback/capture stream was opened.
- Durable report:
  `runs/20260829T010329-0700-l01-readonly/L01-REPORT.md`; snapshot SHA-256
  `4f114b8a4e215e2345b196543bfa7ce020b4de9ccba6a21b4365a9432c3182e4`.
- Operator-screen title/preset mode, the physical capture-channel map, and a
  current complete restoration baseline remain unresolved. Numeric slots are
  not title evidence.

## Corrections carried into CP34

- Slot selection is not preset-content storage.
- A successful reply, UI toast, or stored parameter blob is not audible-effect
  evidence.
- Voice FX is a channel processing path. Reverb-style return-bus behavior must
  not be assumed as proof of Voice FX operation.
- Do not send guessed tags or patch firmware to compensate for missing evidence.

## Authority and platform boundary

The user has directed this project to resolve both outcomes and has corrected
the platform assumption: Linux is the only host. Do not block the ordinary
continuation on Windows or macOS.

The recorded 2026-08-29 L01 authorization included only USB identity,
interface-5 PRESTATE reads, and ALSA identity/mapping on the connected io24. It
did not include audio playback/capture, front-panel actions, mapped writes,
preset/effect operations, L02-L07, firmware flashing, reset, DFU, installation,
driver staging, network use, access to `/home/ajuntanaga/.wine-io24`, or replay
of a newly decoded transaction. Wine remains prohibited. Stop at or below 10
percent battery.

The supported-host `CAPTURE-MANIFEST.md` was superseded without execution. The
active procedures are `LINUX-MANIFEST.md` and `LINUX-LIVE-MATRIX.md`.
`PRESTATE.md` now records the bounded L01 identity/state result and the
stale-shadow limitation. `LINUX-LIVE-MATRIX.md` also records the title-free
classifier as offline-only. No authority for L02-L07 or a slot survey is
recorded.

## Exact continuation

1. The current-slot survey implementation, six-row core-stage
   `CURRENT-SLOT-SURVEY-STAGE.sha256`, 94-test plus 31-subtest regression, two
   pinned host inventories, and `LINUX-OFFLINE-SHA256SUMS` have been reproduced
   offline. The broader offline manifest separately pins the unchanged
   live-matrix analyzer seam and tests. The final fix wave additionally binds
   derivatives to raw frozen-channel samples, derives JaSt summaries from
   canonical raw JSON, uses candidate-scoped interim seals, binds the actual run
   path to the plan, and enforces five-arrival/one-lag mapping and audible
   ordering. Obtain a scoped independent offline re-review of this corrected
   stage; no clean final review is claimed yet.
   Passing tools, templates, tests, or manifests does not authorize hardware.

   Revision 1 is rejected/superseded. Revision 2 requires fresh independent
   review of total JaSt numeric validation, candidate seals, and four-file
   post-restoration audible attestation; it grants no live authority.
2. Treat device-resident custom store/assignment as unsupported by this exact
   host-module/firmware pair unless a new source artifact shows another io24
   transport. Do not implement or probe a guessed sender.
3. Keep the host JSON predecessor as the working Linux preset round trip, while
   keeping it explicitly separate from device-resident persistence.
4. L01 identifies target `AB7C22200355`, its current numeric slots, readable
   preset-enable state, and ALSA card. Obtain operator transcription of the
   currently visible title and preset mode without inferring either from the
   numeric slots. The physical channel A/B map and exact restoration values are
   still unknown. A no-write current-slot survey procedure and executable
   restoration contract now exist and are offline-sealed, but remain
   review-only until the independent review in step 1 is clean.
5. The current shadow is stale/unattested. A live run is ineligible unless the
   user can attest its validity since the last power cycle/editor change or
   separately authorizes a new known-baseline and restoration boundary.
6. The L01-only authority has been exercised. Do not execute L02-L07 or the
   current-slot survey on it. After a clean independent review, any live run
   still requires a new, separately exact authorization. For
   the title-verified matrix, separate exact authorization must name serial
   `AB7C22200355` and permit the physical audio path, ALSA playback/capture,
   manual Preset-button actions, exact validated mapped writes, evidence
   directory, and restoration. The no-write current-slot survey likewise
   requires its own exact named-run authorization, including the source,
   stimulus hash, physical path and inverse, capture identity, bounded JaSt
   reads, two long manual toggles per attempted candidate, evidence directory,
   audible replay, battery floor, and stop conditions. Offline `VALID`,
   `MAPPED`, `SIGNATURE_PRESENT`, or `RESTORED` fixture results are not that
   authorization.
7. If an authorized factory recall makes Voice FX audible, preserve that result
   without mislabeling it as custom preset storage. If it does not, retain the
   positive control and record an honest negative.
8. Seal CP34 only if both original observable outcomes pass or the user accepts
   a capability-negative closure for an outcome the firmware/vendor pair does
   not expose.

Do not call either outcome resolved until the observable checks in step 8 pass.
