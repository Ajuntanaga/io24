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
