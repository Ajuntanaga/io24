# Executed commands and bounded outcomes

All commands ran against serial `AB7C22200355`. Hardware commands were
executed outside the ordinary filesystem sandbox only after the operator's
full-access authorization and channel-2-only limitation.

## Read-only baseline

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_readonly_preflight.py \
  --serial AB7C22200355
```

Result: PASS at 89% battery; channel 1 slot 0 enabled and channel 2 slot 2
enabled. ALSA exposed `hw:CARD=R24,DEV=0` with six S32_LE playback/capture
channels at 44.1/48/88.2/96 kHz.

## Test validation

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

Result after the runner acknowledgement repair: 197 tests passed, one expected
skip, 233.811 seconds. The only diagnostic was the existing unclosed-file
warning in `re/cp34_current_slot_survey.py`.

## Initial trial and recovery boundary

The first bounded slot-3 submission returned an eight-byte SetP transport
acknowledgement that the original runner incorrectly rejected as a short reply.
It stopped before selector submission. A subsequent read-only preflight passed,
the device was still enumerated, and channel 2 was still selected on slot 2.

A no-op, source-bound selector control was then sent with its existing value:

```text
io24.set_preset_slot(channel=2, slot=2)
```

Before and after state was channel 1 slot 0 and channel 2 slot 2. This validated
the native control transport without overwriting a preset.

## Final bounded trial

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_channel2_slot_trial.py \
  --serial AB7C22200355 --slot 3 \
  --record channel2-slot3-173ms.json --execute
```

Result: `WRITE_SENT_AND_SELECTED` at 94% battery. One 860-byte Stat fragment
was submitted to slot 3, two empty SetP acknowledgements were drained, and the
post-state reported channel 2 slot 3. The channel-1 guard remained unchanged.
No audio capture, firmware, reset, DFU, Wine, network, or channel-1 write was
performed.

## Final read-only snapshot

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_readonly_preflight.py \
  --serial AB7C22200355
```

Result: PASS at 95% battery. Channel 2 remained enabled on slot 3. Channel 1
remained on slot 0 but reported disabled. This flag was true in the original
89% pre-trial snapshot and false before the final trial's guarded frame window;
the available evidence cannot attribute that change, so no channel-1 restore
write was sent.

## Post-cabling read-only and passive-audio baseline

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_readonly_preflight.py \
  --serial AB7C22200355
arecord -D hw:CARD=R24,DEV=0 -f S32_LE -r 48000 -c 6 -d 3 \
  input2-passive-baseline.wav
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_current_slot_survey.py \
  map-channel input2-passive-baseline.wav --input-channel 2
```

Result: the read-only preflight passed at 96% battery. It again reported
channel 1 slot 0 disabled and channel 2 slot 3 enabled; both JaSt reads hashed
to `0166a241a601e3971d4cbccde2402d0e2e1b08b89be8fb69ac60dfa94308bc9d`.
The three-second six-channel capture was read-only and used no playback. Its
SHA-256 is `9849926ca9c4b324f361fb33fa831a45f4b5c01012f2fa0eb113a1d90ab3600c`;
Input 2 peaked at -24.14 dBFS, but the arbitrary captured source did not
contain the five isolated impulses necessary for a map or echo measurement.
No effect conclusion follows.

## Operator audible observation and post-check

The operator touched the free end of the patch cable feeding Input 2 and
reported **dry only**: direct tap/hum was audible in the headphones, with no
separate repeat about 173 ms later. No host playback was opened or emitted.

The following fresh read-only preflight then passed:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_readonly_preflight.py \
  --serial AB7C22200355
```

It reported 98% battery, channel 1 slot 0 disabled, and channel 2 slot 3
enabled. Both JaSt payloads hashed to
`e16d8477deac023b424816ed0e69cf4c124726bac4c0f73f431ec7bed4b36cd7`.
The observation is a retained inconclusive negative: it does not prove an
effect is absent because the source was an uncontrolled finger/cable transient.

## Native-host action confirmation

The GTK host was restarted once and left open as the sole interface owner. Its
new bounded action was invoked through the host's D-Bus action surface; no
second USB client was opened:

```text
gdbus call --session --dest org.io24.Mixer \
  --object-path /org/io24/Mixer/window/1 \
  --method org.gtk.Actions.Activate arm-channel2-delay '[]' '{}'
```

The action was repeated once while its transient UI result was read through the
desktop accessibility surface. D-Bus returned `()`, and the host reported:

```text
Shared 173 ms Delay armed; Channel 2 remains slot 3
(2 parameter writes; audibility still unproved)
```

That result is produced only after the host's post-write state read confirms
Channel 2 enabled on slot 3 and the Channel-1 guard unchanged. The durable
write mirror subsequently contained the exact Delay request (`on=true`,
`time_s=0.173`, `feedback=0.25`, `mix=0.5`). This confirms host execution and
parameter submission, not an audible processing gate. See
`HOST-ACTION-RESULT.json`.

The operator's time-correlated report for that repeat was **no audible
difference; dry**. The earlier possible one-off delay-like moment therefore did
not reproduce and is not treated as Voice FX activation evidence.

## Native Channel-2 recall edge

The open GTK host's Channel-2 block controls were used to move global slot
`3 -> 2 -> 3`, with one-second settle intervals. The host UI reflected the
intermediate and final selections. No preset content or direct block-201
parameter was written during this step. The operator reported **dry only**
after the final return to slot 3; direct sound remained present, so the result
is not a mute or routing loss. See `RECALL-EDGE-RESULT.json`.

## Byte-exact factory Slap Echo control

The exact action was first pinned by
`tests/test_io24_factory_slap_action.py`. It requires the recovered 850-byte
factory record hash, refuses an altered 173 ms near-match before a device call,
guards Channel 1, and requires a real Channel-2 `3 -> 2 -> 3` edge. The focused
suite passed 28 tests and both host modules passed `py_compile`.

The previous GTK process exited cleanly and the native host was restarted as
PID 565306. Sysfs identified serial `AB7C22200355`; host battery was 99%. The
new window action was invoked on the sole host owner:

```text
gdbus call --session --dest org.io24.Mixer \
  --object-path /org/io24/Mixer/window/1 \
  --method org.gtk.Actions.Activate \
  load-channel2-factory-slap-echo '[]' '{}'
```

D-Bus accepted the action with `()`. The native host reported:

```text
Factory Slap Echo sent and recalled on Channel 2
(1 fragment, 0 transport replies; audibility still needs listening)
```

The action accepts only wire SHA-256
`a6c3294b62cfb3a46122a82c93514ea2aeb836280fb5d1e458707a78634f87eb`,
writes only global slot 3, waits, selects global slot 2, and returns Channel 2
to global slot 3. Its final live-state guard passed. No output control, audio
stream, Channel-1 setter, Wine, firmware, reset, DFU, install, or network action
was used. The time-correlated operator report was **"dry all dry everytime"**;
no separate 150 ms repeat was heard. This is retained in
`FACTORY-SLAP-ECHO-RESULT.json`.

The operator subsequently stated that the headphone channel is not the issue.
This is retained as an operator exclusion at `2026-09-04T00:45:50-07:00`.
No headphone or output-routing action followed. Diagnosis moved upstream to
slot-record storage and changed-selector dispatch into block 201.
