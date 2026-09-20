# Voice FX was armed into a return nothing was listening to

Status: `OFFLINE_COMPLETE; LISTENING_TEST_REQUIRES_AUTHORIZATION`

## Controlling pre-CP34 evidence

`~/.claude/projects/-home-ajuntanaga-Development-Experiments-PreSonus-Revelator---UniCont/memory/io24-native-protocol-CRACKED.md`,
section `REVERB + INSERT-FX DELAY CONFIRMED ON HARDWARE (2026-07-28)`:

> **CORRECTION (2026-07-28): block 201 is NOT a true insert — it needs the SAME
> send/return path as the reverb** (`'Para'` id 4 = channel FX send, mixer
> paramId 5 = FX return). With the send closed and the return muted, the delay
> is SILENT; restoring both brings it back immediately.

Delay (`'vech'`), De-Tuner and Transformer were ear-verified that day; the Delay
gave distinct ping-pong repeats at 0.60 s. `InsertFXSelectorComponent` is a host
class name, and the earlier "insert, no routing needed" reading came from that
name rather than from signal flow.

## What the Host was doing

`_push_reverb(establish_path=True)` opened the feed and the return before arming
block 202 — `set_fx_mix(1, …)`, `set_send_db("fxreturn/ch1", "main", …)`,
`set_send_assigned("fxreturn/ch1", "main", True)`. That is why the shared reverb
is the only effect the user has ever heard.

`_push_fx()` sent `dev.set_fx(model, on=…, **params)` and nothing else. Block 201
was armed correctly into a return that was neither levelled nor assigned, so no
bus carried it. The same gap existed on a record's FX load
(`_load_factory` → `PR.apply_voicefx`).

`Io24.fx_on()`/`fx_off()`, which used to perform that transaction, are CP34
refusals. They are left exactly as they are; this repair reuses the three calls
the reverb path already uses in production.

## Why the CP34 nulls do not contradict this

`re/io24_voicefx_meter_probe.py` and `re/io24_corrected_ringmod_probe.py` measure
JaSt `main`/`mixa`/`mixb` against the Input-1 meter, and neither opens the FX
send nor assigns `fxreturn/ch1` into the bus it measures. They observe the
channel's direct path — the one path the 2026-07-28 result says block 201 does
not reach. `NO_DIRECT_BLOCK201_METER_EFFECT_DETECTED` is the expected reading of
the wrong bus, not evidence that the insert is inert.

One genuine counter-observation stands: `tests/fx_gate_probe.py` (2026-08-11)
did open the send and assign the return into Mix A, with reverb at +6.0 dB as an
in-run positive, and still read the **vocoder** at −0.3 dB. The vocoder is
carrier-driven and close to energy-preserving in a broadband ratio metric, and
it is one of the three models never ear-verified. It is weak evidence against an
ear-verified Delay positive, and the decisive retest is the Delay.

## Change

- `io24gtk.establish_effects_path(dev, channel_mix, return_db, bus="main")` —
  one transaction for both engines; `channel_mix=None` leaves the channel's
  processing scalar alone.
- `io24gtk.effects_path_plan(win)` — the user's existing processing scalar and
  return level, `None` before those controls exist. A bypassed Channel 1 keeps
  its bypass and the Host says why FX stays silent instead of switching
  processing back on behind the user.
- `_push_fx()` establishes the path before arming, and `_push_reverb()` now
  calls the same helper so the two cannot drift.
- `_load_factory()` establishes it before `apply_voicefx` for a record whose FX
  is on. The Host-known slot-recall path already routes through `_push_fx()`.
- FX off changes no routing: the model blob carries `on=False`, and closing the
  send would bypass the channel's whole Fat Channel (wire 4 is one scalar).
- Disclosure, as row subtitles because `Win` carries no group descriptions: the
  returns group is now `Shared effects returns`, each return row says it carries
  both engines, and `FX active` says it is heard through that return and not in
  the channel's direct signal.

## Verification

- `tests/test_io24_global_fx.py`: 14 pass, six of them new — send/return before
  arming in exact order, no bypass lift plus its disclosure, FX-off touching no
  routing, one shared helper across both engines, the record path, and an
  unbuilt Host establishing nothing.
- Affected set `test_io24_global_fx` + `test_io24_host_dsp_amount` +
  `test_io24_host_parameter_repairs` + `test_io24_host_rate_and_effects`:
  103 pass plus 33 subtests.
- Full hardware-free suite: **889 passed, 1 skipped, 265 subtests**, in 236 s.
  The first run had two failures, both resolved: the stale deterministic-matrix
  source hash, and the returns-group name.
- The 709-row matrix was regenerated twice byte-identically at SHA-256
  `58dbe363874d4fac227f30851baa65851bbc7a5fdd36211c5702be11705dd878`; the only delta against the
  checked-in artifact was `io24gtk.py`'s source hash.
- `test_io24_host_state_repair` now expects `Shared effects returns`. The two
  reverbs are still named by the rows above it, which is what that assertion is
  for.
- `git diff --check` clean. SHA-256 after the change:
  `io24gtk.py` `0ce09baf62e0615b7ec63cdcc901258cdb13905bb23751b291ada754eece3523`,
  `tests/test_io24_global_fx.py`
  `4c40d5a5eaed3d82a3b4e566649080db5439a20da8dd67ec3e0ca6e419a7476f`,
  `tests/test_io24_host_state_repair.py`
  `09c6c47d6abea5425944f36505f68addf8e4863bd19f225144779f8ad31aef26`.

## Not done

No USB, device, audio, Host launch, Wine, network, install, or publication.
Audibility is unproven by this change. The decisive test is a listening one and
needs separate authorization: Model `Delay`, Time long, Feedback high, Wet/Dry
100 %, `FX active` on, Channel 1 not bypassed, and the `FX return → Main out`
row above 0 dB — then toggle `FX active`. That is the 2026-07-28 rig, which is
the one configuration the CP34 campaign never re-ran.

## Second pass: one implementation, and the other silent-failure mode

The first pass fixed the GTK Host only. Three gaps remained.

**The transaction now lives in the driver.** `Io24.establish_effects_return(
bus, return_db, channel, channel_mix)` is the single implementation;
`io24gtk.establish_effects_path()` and the preset library both call it, so they
cannot drift. `channel_mix=None` leaves wire 4 alone, because it is one scalar
and writing it would take a bypassed channel out of bypass and change what the
main output carries.

**The preset library armed FX into a closed return.**
`io24_presets.apply_voicefx()` and `apply_preset(with_fx=True)` now open the
shared return by default (`establish_return`, with `return_db`, `bus` and
`channel_mix` passed through) and report which happened. Every non-GTK caller
was previously guaranteed silence.

**The report wording was from the wrong model.** `voicefx=… (n writes;
activation unresolved)` described a belief that block 201 needed an
undiscovered gate. It now says either `through the main effects return at
+0.0 dB` or `the effects return was not opened, so it is inaudible`. The Host's
load message changed with it.

**The second way an armed effect stays silent** is a shared return sitting at
its own −60 dB floor, which is indistinguishable from never opening it. The
Host now says so, as it already did for a bypassed Channel 1.

**PROTOCOL.md's most expensive sentence is corrected.** The passage listing
"the right signal path — Voice FX is a channel INSERT … so the observable is
the channel output `line/ch1 → Mix A`" now carries a correction: that is the
one path block 201 does not reach, the document's own earlier block-201
correction already said so from ear-verified hardware, and every CP34 null was
taken there.

### Verification, second pass

- Full hardware-free suite: **921 passed, 1 skipped, 265 subtests**.
- `test_io24_global_fx.py` is 20 tests, including the driver transaction's own
  contract, the floored-return disclosure, and a check that driver, library and
  Host share one implementation.
- Four stubs borrow the real `establish_effects_return` rather than recording
  it opaquely, so existing assertions still pin the exact wire writes — notably
  that enabling reverb over a bypassed channel still writes wire 4 as zero.
- The 709-row matrix regenerated twice byte-identically at SHA-256
  `6e8f936d5b58001a76873d18ba9d57b423d7a341e28f6f9310d2f1b0e9bb7d75`.
- `git diff --check` clean. SHA-256: `io24.py`
  `30163f278d456d11563db855fd647c166abf300879e1ec31a63c18e766dc0cd7`,
  `io24gtk.py`
  `9ce4b30930e105f49fc9b9a29a83864bb83ccadbee03a22ee4c87d39a2423f02`,
  `io24_presets.py`
  `bd364d95385077f9971aab3bcc8fff1e1cc8443768d51c50e0bb57a50c906d3c`,
  `PROTOCOL.md`
  `29fef9e0261593e4169700868a956767e9835c84231fb867138123fa62cea449`.

Still no device action. Audibility remains unproven until the shared-return
probe runs.
