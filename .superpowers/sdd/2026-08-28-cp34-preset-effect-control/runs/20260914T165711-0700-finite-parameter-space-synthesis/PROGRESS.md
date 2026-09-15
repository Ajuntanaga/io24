# The host wire-parameter space is finite, closed, and does not contain Voice FX

Status: `PARAMETER_SPACE_EXHAUSTED_CAPABILITY_LIKELY_UNEXPOSED`

Prompted by the observation that the device, the Host and UC each have only so
many parameters, so the answer must be somewhere in them. Enumerated rather
than hypothesised. It is somewhere — but probably not in that space.

## The whole host-reachable parameter space

From the firmware's own two dispatchers (12I), not inferred:

`'Para'` (float), FW VA `0x6004e36e`, `subs r1,#1 ; cmp r1,#13` -> wire **1..14**

| wire | parameter |
|---|---|
| 1 | `hpVolume` |
| 2 | `mainVolume` |
| 3 | `input1/2Gain` |
| 4 | `input1/2FxMix` |
| 10 | `monitorMix` |
| 14 | `outputDelay` |
| **5-9, 11-13** | **firmware no-op** (`add sp,#0x34 ; pop`) |

`'Pari'` (int), FW VA `0x6004e484`, `subs r1,#4 ; cmp r1,#15` -> wire **4..19**

| wire | parameter |
|---|---|
| 4 | processing/effects mix, boolean preset enable |
| 5 | `input1/2HighPassFilter` |
| 6 | `hpOutputMute` |
| 7 | `input1/2Mute` |
| 9 | stereo link |
| 11 | phones source |
| 12 | processing channel |
| 13 | `outputDelayBus` |
| 15 | sets `JaSt` slot 42 bit 13; purpose still unknown |
| 16 | preset slot |
| 17 | preset mode |
| **10, 14, 19** | **firmware no-op** |

That is the entire space: thirty ids, of which nine do nothing at all.

## The unclaimed ids were already swept

12U swept every unclaimed `'Pari'` id -- 8, 10, 11, 14, 15, 18, 19 -- watching
`JaSt` slot 42. Only wire 15 responded, setting bit 13, which remains
unexplained. Wire 8 decodes to `muteMode` in the dispatcher and produced no
observable change.

**There is no unexercised host parameter left.** There is also no parameter
anywhere in the space that selects or activates a Voice FX model: that lives
entirely in the block-message space (`SetP` block 201), not the parameter space.

## The conclusion the project already reached

12U, on `mainOutputMute`, which the firmware carries and no wire id reaches:

> "This is the same shape as block 201: the firmware carries the parameter, and
> the host protocol simply has no id that reaches it. Two independent instances
> of it now, which suggests the wire id space was defined for a family of
> devices and the io24 has capabilities its transport does not expose."

That was written on 2026-08-02 and never carried forward into the Voice FX
work. It is the most economical explanation for everything measured since:
block 201 exists, is addressable, accepts writes, answers normally, has its
delegate installed, sits in a live chain, and does nothing -- on either channel,
streaming or idle, with every host-side sequence we can construct.

## What this does not close

The *parameter* space is closed; the *block-message* space is not. Block 201
accepts `VoFx` plus six model tags, and its work function queries the installed
model for an `IFac`/`MRSp` interface. A block-level message we have not sent
remains possible.

One correction that saves a future live run: 12X shortlisted writing an
`'IFac'` tag to block 201. That is misconceived. `IFac` and `MRSp` are not wire
tags -- the work function at `0x5f1f4` builds a stack descriptor
`{'IFac', 0x10, 'MRSp', &out}` and passes it to the delegate's `vtable+0x04` as
an interface query. They are internal interface identifiers, not things to
send.

## Also corrected here

UC's `<uc:ParamList id="InsertFXSelector" starttag="450">` is host-side object
numbering. The device's firmware table runs ids 1..144 and contains nothing at
450, so `voicefxopt/fxmodel` is not a sendable device parameter.

Compressor and EQ "models" are a purely host-side choice -- one device
compressor, different maths into the same `cpxt` blob -- so they never exercise
the selector mechanism. Voice FX is the only true model-instantiation path on
this device, which is why no working feature can be copied from.

## Boundary

Offline synthesis of existing firmware evidence plus this session's live
eliminations. No device operation was performed for this note.
