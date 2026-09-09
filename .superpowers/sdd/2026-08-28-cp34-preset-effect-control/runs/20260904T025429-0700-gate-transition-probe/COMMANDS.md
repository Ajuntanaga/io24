# Executed commands and bounded outcomes

All live operations targeted serial `AB7C22200355`. No Wine path was accessed,
and no network, firmware, install, reset, DFU, or playback command was run.

## Offline eligibility

The implementation was built test-first in three layers: the exact gate action,
the strict offline waveform analyzer, and the execute-gated runner. Their final
focused set passed 18/18. The broader eligibility set, including the factory
Slap action, host Delay action, and read-only preflight, passed 26/26.

The runner was first invoked without `--execute`. It returned `DRY_RUN_ONLY`,
`usb_opened=false`, `capture_opened=false`, and `playback=false`. Process and
ownership checks found no active `arecord`, io24 controller, native host, ALSA
capture owner, or owner of the serial-correlated USB node. At that point battery
was 54 percent. `SCOPE.md` and `GATE-BLOBS.json` both verified against
`SCOPE.sha256`.

The preceding 20-row checkpoint was reconciled. Eighteen rows remained `OK`;
only `io24.py` and `tests/test_io24_linked_recall_action.py` changed, exactly as
required for this successor action and its tests.

## Serial-pinned preflight

```text
python3 re/cp34_readonly_preflight.py --serial AB7C22200355
```

PASS at 53 percent battery. Flags were `0x1a1`: stereo link off, Channel 1 slot
0 disabled, and Channel 2 slot 3 enabled. Both 2040-byte replies had SHA-256
`66c74642eaeaa39360e5bd9b59a1f1d04aaa9cee21504a5de08d2a96347c8689`.

## One live trial

The execute-gated runner was called exactly once with fresh report and capture
paths. It started only this fixed recorder command:

```text
arecord -q -D hw:CARD=R24,DEV=0 -t wav -f S32_LE \
  -r 48000 -c 6 -d 14 gate-transition.wav
```

It then opened `io24.Io24(shadow=False)`, rechecked the USB serial, required
Input-2 level no greater than `0.01`, and ran the byte-pinned action. Confirmed
capture offsets were:

```text
0.501902  baseline: unlinked, Channel 2 slot 3
1.002935  unlinked Channel 2 slot 2
2.504326  stereo link on
3.005401  linked Channel 2 slot 3
3.006414  exact factory gate on sent
4.507135  exact factory gate off sent
7.507942  exact factory gate-on restoration sent
9.009557  stereo link off
```

Execution returned `LINKED_CHANNEL2_GATE_TRANSITION_COMPLETED`; `arecord`
exited 0 with no stderr. The 14.0-second raw WAV is 16,128,044 bytes and has
SHA-256
`9f2307056e44b909668deb4226ec2b191d1e23ade12d641996fc9669e4beafda`.

## Postflight and offline classification

The independent read-only postflight passed at 53 percent battery. It showed
link off, Channel 1 slot 0 disabled, and Channel 2 slot 3 enabled. Its two
2040-byte replies both had SHA-256
`408195df650fbe897953f0cf7983e9ee6f20b791e252d9dfaaca3ff2d3dd448f`.

```text
python3 re/cp34_gate_transition_audio.py LIVE-TRIAL.json \
  gate-transition.wav
```

The analyzer returned `NO_REPEAT_DOWNSTREAM_GATE_OFF`. No further live command
was run. Final-tree hardware-free discovery passed 223 tests with one expected
skip in 176.921 seconds.

A final read-only ownership check found that an unrelated REAPER process had
started after the live work and acquired the io24 ALSA capture and playback
nodes. The run did not start, configure, stop, or otherwise touch that process.
