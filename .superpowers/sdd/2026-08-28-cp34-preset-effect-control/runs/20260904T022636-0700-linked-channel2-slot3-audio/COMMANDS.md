# Executed commands and bounded outcomes

All live operations targeted serial `AB7C22200355`.  No Wine path was accessed.

## Preflight

```text
python3 re/cp34_readonly_preflight.py --serial AB7C22200355
```

PASS at 98 percent battery.  Flags were `0x1a1`: stereo link off, Channel 1
slot 0 disabled, Channel 2 slot 3 enabled.  Both 2040-byte replies had SHA-256
`15a0937b3fa2a2dcdd3bae8f8868960ed0702947c8ea3bb60f91708f1ee5347a`.

## Test-first linked action

The initial three contracts failed because
`recall_channel2_slot3_while_linked` did not exist.  After implementation, the
focused action set passed 7/7 and syntax compilation succeeded.  The action
requires the exact prestate, uses only Channel-2 slot selection and the stereo
link setter, and clears link in `finally`.

## Live trial and capture

One bounded Python invocation opened:

```text
arecord -q -D hw:CARD=R24,DEV=0 -t wav -f S32_LE \
  -r 48000 -c 6 -d 14 linked-recall-passive.wav
```

It then opened `io24.Io24(shadow=False)`, rechecked the exact USB serial, and
called the test-covered linked action.  Its confirmed capture offsets were:

```text
0.522732  baseline: unlinked, Channel 2 slot 3
1.024134  unlinked Channel 2 slot 2
4.525615  stereo link on
5.026665  linked Channel 2 slot 3
10.528339 stereo link off
```

Execution returned `LINKED_CHANNEL2_SLOT3_RECALL_COMPLETED`; `arecord` exited
0 with no stderr.  The raw WAV is 16,128,044 bytes and has SHA-256
`e587d9a7cbf78312eabcb4b2b4ee5e2f806d88335d3c812dd4d7372b1120aa14`.

## Offline waveform analysis

Python's standard `wave` module plus NumPy measured the clean unlinked-slot-2,
linked-slot-3, and restored windows.  A least-squares model fit each captured
monitor channel against current, 150 ms delayed, and 300 ms delayed Input 2.
The linked monitor channels were identical for the reported metrics: direct
coefficient `0.70797731`, 150 ms coefficient `0.00000642`, and residual
-51.67 dB relative.  Input 2 was only -97.15 dBFS RMS / -83.66 dBFS peak.

The host lacks SoX and FFmpeg.  Two clearly labeled normalized derivatives were
therefore generated offline with `wave`/NumPy for a secondary listening check,
but this runtime reported that audio input is unsupported.  They are not the
basis for an audible claim.  The raw waveform metrics and factory -47.5 dBFS
gate establish only that no 150 ms repeat exists in below-gate noise.

## Poststate and regression

```text
python3 re/cp34_readonly_preflight.py --serial AB7C22200355
python3 -m unittest discover -s tests
```

The independent read passed at 93 percent battery with link off, Channel 1
slot 0 disabled, Channel 2 slot 3 enabled, and two matching reply hashes.  The
complete hardware-free suite passed 208 tests with one expected skip in
196.907 seconds.
