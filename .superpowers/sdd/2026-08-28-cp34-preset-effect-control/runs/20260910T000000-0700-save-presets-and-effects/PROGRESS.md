# Preset saving and effect correctness

Status: `SAVE_AND_EFFECT_REPAIRS_OFFLINE_LISTENING_PENDING`

## Correction: what MAIN contains

The previous checkpoint claimed device slot 0 `MAIN` held a Detuner body with
`on=1`, and used that as evidence. That was wrong and is withdrawn.

The authorized `MAIN` profile pinned in `re/cp34_channel1_main_slot_stage.py`
is **Delay, `on=0`** (feedback 0.2, mix 0.5, time 0.19) with Standard EQ. The
Detuner body is a *registry entry* written at `2026-09-09T22:47:32Z` under
source `voicefx-arm:MAIN`. A registry receipt was read as if it were the user's
original preset.

Two consequences. First, the user's `MAIN` body was very likely overwritten on
the device by that `voicefx-arm` write; it is `WRITE_SENT_UNVERIFIED` and slots
have no readback, so this cannot be confirmed either way. It is recoverable:
`build_main_record()` still holds the exact authorized profile. Slot 1
`B A S E` is untouched, source `restored-user:B A S E`.

Second, "recall MAIN and listen" is no longer a valid acceptance test — the
authorized MAIN has `voicefx.on=0` and would produce a false negative. The
acceptance test is now Save and activate, which authors a body of known
contents into the channel's inactive block and recalls it.

The block-201 gate finding is unaffected. It rests on the firmware
disassembly and the 2026-08-31 report, not on any slot's contents.

## Saving a preset

Naming: the record builder has always taken a name; the Host never asked, and
hardcoded `Current Channel N` into every body. There is now a **Preset name**
row, refused when empty or over the record's 127-byte short text form.

Activation: **Save and activate** writes the chosen block and then recalls it;
**Save only** writes and leaves selection alone. The write and the recall stay
separate device operations, and a failed recall is reported as a failed recall,
never as a failed save.

Listing: the Host preset list was built once at window construction, so a
preset the user had just saved did not appear until restart. It is now rebuilt
from the registry after every write.

Display: a recalled body is adopted onto the controls, so the pages stop
describing the previous sound. A Passive/Vintage body has no Standard-band
form — `to_bands` raises on the real `B A S E` record — so it is not shown at
all and the product reason is given.

## Effects

Sample rate: no device write passed a rate. Every biquad, time constant,
reverb and rate-dependent Voice FX payload was computed for 48 kHz whatever the
interface was clocking at — at 96 kHz a 1 kHz EQ band landed at 2 kHz. The Host
now tracks the real rate using the authority order already established for the
Device page, passes it to every write, and recomputes and re-sends EQ, HPF,
dynamics, reverb and Voice FX when it changes. The first sighting is adopted
silently, because nothing has been pushed at that point.

Limiter release: the backend has always taken `release_s` and computed the
coefficient exactly — 0.4 s at 48 kHz reproduces the hardware-verified
`0x3f7fea8f`. The page never offered it, so every write used the default. It is
now a control. It is deliberately *not* added to the slot record: UC's own
`limit` section holds only `limiteron` and `threshold`, and inventing a field
UC never writes would violate the completeness rule. It rides the snapshot
shadow instead, which records `set_limiter` with `apply_defaults()`.

Reverb character: the named character, movement and movement depth are Host-only
— the device has no parameter for them — and no save carried them, so a load
reset the character to Custom. They now travel in `host_features`, with
unreadable, unknown or out-of-range values refused with a completed-load notice.

## Evidence

Offline only. 14 new contracts in `tests/test_io24_host_rate_and_effects.py`
and 12 more in `tests/test_io24_device_slot_recall.py` (43 in the two files)
cover the clock adoption and resend, the rate on every write, limiter release
and rate, reverb character round trip and all four refusals, preset naming,
save-only versus save-and-activate, a failed recall, live listing, and the
unsupported-body display refusal. The 748-row matrix regenerates deterministically.

## Boundary

No device write, recall, audio, Host launch, USB, Wine, install, network or
firmware action occurred. `recall_device_slot` still has never run against
hardware. Restoring the authorized `MAIN` body to slot 0 is a separate,
explicitly authorized device write and was not performed.
