# MAIN power-cycle survival

Status: `SELECTION_AND_ENABLE_SURVIVED_BODY_UNVERIFIED`

## What was done

The user physically unplugged and reconnected the io24. There is no software
path to this test on this workstation: the unit sits on a root-hub port
(`/sys/bus/usb/devices/1-2`) with no per-port power switching, so every
available action — `authorized` 0/1, `port/disable`, `USBDEVFS_RESET`,
unbind/bind — is a bus reset that leaves VBUS applied and would have returned a
guaranteed false positive. Resets are also a separately gated action on this
unit, which has twice been driven into its bootloader by transport-level pokes.

The Host was closed for the whole window so no cached shadow state could be
re-pushed on reattachment and contaminate the reading. Re-enumeration is
confirmed: `devnum` moved 5 -> 6, so the device genuinely left the bus.

## Result

Every readable preset-relevant field is byte-identical across the cycle:

| field | before | after |
|---|---|---|
| serial / `bcdDevice` | `AB7C22200355` / `0128` | same |
| `input1SlotIndex` | 0 | 0 |
| Channel 1 preset enabled | true | true |
| `input1Gain` | 30.0 | 30.0 |
| `input2SlotIndex` | 2 | 2 |
| Channel 2 preset enabled | true | true |
| `input2Gain` | 24.287769317626953 | same |
| stereo link | false | false |
| processing channels | (0, 1) | (0, 1) |

One field moved: `flags` 897 -> 385, i.e. bit 9 cleared. Bit 9 is not in the
recovered slot-42 table (which documents 1-6, 12 and 13). 385 is exactly the
value the slot-0 stage recorded immediately after its write, so bit 9 tracks
session or stream state rather than preset state — it was set while the Host
and audio had been running and is clear on a fresh power-on.

## Boundary

This establishes that the device-slot **selection** and the **preset enable**
survive a real power cycle. It does **not** establish that the stored body is
MAIN. Slot bodies have no readback on firmware 0128, so no software check can
confirm the contents.

Listening is now the only remaining test of the body, and it is meaningful:
the live Fat Channel values the stage applied directly were wiped by the power
loss, so whatever the channel produces now came from the device's own storage.
MAIN is Standard compressor 2:1 soft knee, the four-band Strandberg Boden 8
curve, limiter at -0.6 dBFS, HPF bypassed, gate off, no Voice FX.

## Correction (same day): the restored record is not the user's MAIN

The user reported the MAIN description as inaccurate. It is, and the cause is
the source record, not the wording.

`build_main_record()` in `re/cp34_channel1_main_slot_stage.py` is not derived
from any retained user data. Compare it with the user's own scene exports in
`~/.cache/io24/re/scenes/`:

| | `build_main_record()` | `Main.scene` ch1 | `B A S E.scene` ch1 |
|---|---|---|---|
| embedded `preset_name` | `MAIN` | `Broadcast` | `Main` |
| EQ model | Standard | Vintage | Vintage |
| gate | **off** | on, -48.72, 325 Hz key | on, -48.72, 325 Hz key |
| comp | 2:1 soft knee, manual, +2 dB | 4.01:1 hard knee, auto, +9.8 dB | 4.01:1 hard knee, auto, +9.8 dB |
| limiter | -0.600 dBFS | -0.800 dBFS | -0.800 dBFS |
| voicefx delay time | 0.19 | 0.0351 | 0.0226 |
| `icon_id` | `electricguitar` | — | — |

`B A S E.scene` ch1 matches registry slot 1 exactly, field for field, so that
restoration genuinely used the user's export. Nothing in either scene matches
`build_main_record()`. Both real records are broadcast-style vocal chains; the
fabricated one is a guitar preset.

The slot-0 write therefore restored a fabrication. It did not destroy pristine
data: slot 0's body had already been overwritten by the `voicefx-arm:MAIN`
Detuner write before this session touched it, and both scene files are intact
on disk.

The power-cycle result stands as a *mechanism* result — device-slot selection
and preset enable survive power loss. The claim "MAIN survived" does not: what
survived is a selection pointing at a fabricated body.

The scene filenames and their embedded channel preset names are crossed
(`B A S E.scene` holds a channel preset named `Main`; `Main.scene` holds one
named `Broadcast`), so which record is the user's MAIN is a question only the
user can answer. Awaiting that before rewriting slot 0.
