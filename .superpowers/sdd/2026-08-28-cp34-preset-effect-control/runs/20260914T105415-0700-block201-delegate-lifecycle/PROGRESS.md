# Block-201 delegate lifecycle correction

Status: `SUPERSEDED_BY_SELECTOR_REPLAY_TRACE`

## Later correction

Primary handler `0x553d4` proves that ordinary model-state messages tail-call
generic delegate handler `0x5079c` and do not revisit selector `0x55388`.
Therefore this checkpoint's state-trigger/state-replay sequence did not invoke
deferred model replacement. The current source-bound sequence is selector ->
60 ms -> selector replay -> model state. See
`../20260914T152132-0700-corrected-ringmod-live/PROGRESS.md` and analyzer schema
`cp34-block201-delegate-lifecycle-v4`.

Offline-only continuation from Claude's cold-boot result and final session-limit
observation. No device, USB, audio, Wine, network, firmware, or system-state
operation occurred.

## Starting point

Claude's last completed peer-outbox entry is the cold-boot result under
`runs/20260914T102740-0700-cold-boot-block201/`: block 201 was inert across
three fully-wet models with an open Channel-1 path and a same-session direct-gate
positive control. His subsequent, not-yet-ledgered observation was that the
block constructor initially stores zero at `block+0x14`, and both the parameter
handler and model selector inspect that field.

That zero is real, but it is only an intermediate constructor state.

## Source-bound result

Pinned firmware: 1,104,448 bytes, SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.

The complete constructor path is:

```text
0x591bc constructor
  block+0x10 = block+0x50 manager/storage object
  block+0x14 = 0
  -> 0x59248 calls selector 0x55388 with model 0
     0x553a8 sets block+0x44 = 1
     0x553ac sees block+0x14 == 0
     -> primary vtable +0x34 = 0x5f1f4
        -> 0x5f1fa calls lazy installer 0x5f130
           model 0 -> constructor 0x5e270 at block+0x60
           0x5f170 stores block+0x60 at block+0x14
           0x5f184 clears block+0x44 = 0
```

So block 201 ends normal construction with a concrete model-0 delegate. A null
delegate cannot explain the cold-boot live null.

The first continuation of this trace called `block+0x44` only a rebuild/dirty
flag. That was too narrow. The block's audio routine proves that `+0x44` is the
target bypass state: zero processes and one bypasses. `+0x39` is the latched
bypass state and `+0x40` is the transition countdown. Model selection sets
`+0x44=1` so the old model can crossfade to bypass before replacement; the
installer clears it to request processing by the new model. Handler `0x50af8`
forwards a block message to delegate `vtable+0x10`, then invokes rebuild work
only after the bypass transition is complete. The three-field test is therefore
a safe-rebuild condition, not proof that the fields are unrelated to audio.

One apparent setter was rejected as code/data confusion. Work function
`0x5f1f4` returns at `0x5f248`, followed by an alignment NOP at `0x5f24a`.
Offsets `0x5f24c` and `0x5f250` are its PC-relative literal pool
(`0x49466163`, `0x4d525370`), loaded at `0x5f214` and `0x5f218`. Linear Thumb
decoding of `0x5f24c` as `str r3,[r4,#0x14]` is false.

## Second correction: 0x3e608 is not a chain installer

The three-pointer call at `0x3f13a` does include `device+0x43a0`, block 201 at
`device+0x11e0`, and reverb at `device+0x3a70`. But callee `0x3e608` does not
retain or link those pointers. It loops over the temporary array, calls each
member's `vtable+0x18`, takes the maximum returned workspace requirement, and
allocates/resizes the buffer rooted at `device+0x11d0`.

Therefore §13a's name “chain installer” and the inference that this call proves
block-201 signal-path membership are withdrawn. The function is a workspace
sizer/allocator.

## Audio scheduler and buffer handoff are source-bound

The next trace resolved the actual audio edge. Block 201's primary vtable
`+0x0c` contains runtime Thumb entry `0x19869`, mapping through the reset-copy
delta to raw process routine `0x1a580`. At `0x1a59e..0x1a5b6`, that routine
loads the installed delegate from `block+0x14` and invokes the delegate's own
`vtable+0x0c`. Model 0's primary vtable `+0x0c` is runtime `0x1d491`, mapping
to the already-proved DSP routine at raw `0x1e1a8`.

The device audio root is equally direct. Raw `0x20546..0x2054e` loads the
device, constructs the buffer descriptor at `stack+0x40`, forms
`device+0x11e0`, and calls block-201 process runtime `0x19868`. The call is
gated by two source-bound conditions:

- `device+0x5e71` is nonzero; setup writes this byte from
  `device+0x5dc0 <= 96000.0`;
- stereo-link bit 12 at `device+0x5e58` is clear.

Claude's cold-boot test was declared at 96 kHz with link off, so it lies on the
static call branch. The source no longer supports describing block 201 as
uninstalled, unscheduled, or lacking buffer handoff in that state.

## The missing transition is in Host pacing

Block setup computes `block+0x3c`, the bypass crossfade countdown, as:

```text
round(sample_rate * 40 / quantum / 1000) audio blocks
```

At the declared 96 kHz / 512 quantum this is eight blocks, or 42.667 ms. Model
selection sets target bypass and defers replacement until the fade completes.
This checkpoint incorrectly treated auxiliary handler `0x50af8` as the primary
message route. The later trace at the top proves model state bypasses it.

The former Host sequence slept only 20 ms between frames. Delay, Filters, and
Ring Mod each contain exactly two frames: selector then one state frame. Their
only state frame therefore arrived before the 42.667 ms transition, and no
later selector existed to rebuild and then program the new model. The number of
later state frames cannot fix that omission.

The superseded Host v1 sequence was:

1. send selector;
2. wait 60 ms;
3. send the first model-state frame, mistakenly assumed to trigger rebuild;
4. wait 60 ms;
5. replay that state frame to the new model, then send remaining frames at the
   ordinary 20 ms interval.

Current Host v2 instead replays the selector after step 2, then sends each
model-state frame once.

## Live result: superseded v1 sequence executed, scalar Delay result inconclusive

The authorized v1 Delay run is retained at
`../20260914T113431-0700-corrected-fx-rebuild-live/`. Delay moved only
`-0.148 dB` against a `1.990 dB` threshold, while the same-process Channel-1
gate control moved `-18.313 dB` against a `12.014 dB` threshold. Restoration
was exact. Feedback 1.0 maps to coefficient 0.5, whose stationary-noise gain is
only `1.249 dB`, below the Delay threshold. The sequence repair is
live-executed; its audibility effect remains unresolved.

## What remains

The important live contrast remains:

- in the earlier already-armed device state, Transformer moved the normalized
  bus level by -4.024 dB;
- after a genuine cold boot, three fully-wet models moved it by at most 0.13 dB
  with a same-session -19.475 dB direct-gate positive control.

The static source and old Host implementation identify a genuine deferred
replacement requirement without attributing it to Universal Control. The live
result does not settle whether that requirement is sufficient for audibility.
The model-5 process/state and input/output lane trace is now complete and rules
out missing Delay construction, state application, process dispatch, and lane
binding. The next objective discriminator is corrected fully-wet Ring Mod with
the same direct-gate control and exact restoration. A further device write
needs fresh exact authorization.

## Executable evidence

- `re/cp34_block201_delegate_static.py`
- `tests/test_cp34_block201_delegate_static.py`

The model-5 extension additionally source-binds constructor `0x56f34`, `vech`
handler `0x57240`, process `0x4ebd4`, its four parameter fields, and the
one-input/two-output in-place descriptor. Its recurrence predicts only
`+1.249387 dB` on the live stationary-noise stimulus, below that run's
`1.989850 dB` threshold.

Focused analyzer, Host-sequencing, and live-probe result: `22 passed`. Direct
analyzer execution on the pinned firmware exited 0 and emitted schema
`cp34-block201-delegate-lifecycle-v3`. The Host contract is
`tests/test_io24_fx_model_transition.py`. The preceding complete hardware-free
discovery pass finished cleanly before this focused extension: 845 passed,
1 skipped, 265 subtests, with only the pre-existing PyGI deprecation warning.
The later broad pass ran 862 tests: 860 passed, one skipped, and the only
failure was the expected deterministic parameter-matrix drift caused by the
new `send_fx` signature. Regenerating that checked-in matrix and rerunning the
failed check with the focused set passed 23/23.
