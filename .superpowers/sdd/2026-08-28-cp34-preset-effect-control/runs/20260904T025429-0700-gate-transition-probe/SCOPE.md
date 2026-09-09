# CP34 autonomous linked gate-transition probe

Timestamp: 2026-09-04T02:54:29-07:00

## Authority interpretation

The operator directed: **“mmake extended plan, then proceed -authorized.”**
This run treats that instruction as authority for exactly one execution of the
serial-pinned plan in
`docs/superpowers/plans/2026-09-04-cp34-autonomous-voicefx-gate-transition.md`.
It is not general device or audio authority.

Target: PreSonus Revelator io24 serial `AB7C22200355`, descriptor 1.28.

## Required prestate

- Host battery strictly above 10 percent.
- No existing native host or capture process owns the target surfaces.
- Exact serial match before mutation.
- Flags `0x1a1`: stereo link off, Channel 1 disabled on slot 0, Channel 2
  enabled on slot 3.
- Input-2 instantaneous meter no greater than `0.01` linear (-40 dBFS) before
  the temporary gate-off write.

## Permitted live operation set

1. Bounded `JaSt` pre/post reads and the action's state-confirmation reads.
2. One passive 14-second, six-channel S32_LE/48 kHz ALSA capture at
   `hw:CARD=R24,DEV=0`; no playback.
3. `set_preset_slot(2, 2)` while unlinked.
4. `set_channel_link(True)`.
5. `set_preset_slot(2, 3)` once while linked.
6. `set_gate(2, on=True, ...)` for both gate instances using the exact factory
   Slap Echo fields, to establish the known gate-on bracket.
7. `set_gate(2, on=False, ...)` for the same two instances with only the `on`
   bit changed, to expose the existing low-level Input-2 noise.
8. Re-emit the exact two factory gate-on blobs before leaving linked state.
9. `set_channel_link(False)` in outer cleanup and one final state read.

The factory fields are threshold -47.5 dBFS, range -60 dB, attack 25 ms,
release 700 ms, key filter 730.000244 Hz, expander on, key listen off, at
48 kHz. Gate state is not readable; restoration is an exact write assertion,
not a readback claim.

## Prohibited actions

No gain, phantom, mute, high-pass, processing-channel, mixer, routing, send,
return, main/headphone, output-delay, preset-record, direct Voice-FX parameter,
playback, firmware, reset, DFU, install, Wine, network, interface detach, or
automatic retry. Do not access `/home/ajuntanaga/.wine-io24`.

## Stop rules

Stop before the next mutation on identity, battery, process ownership, capture,
prestate, meter, or state-confirmation mismatch. If a live write raises, attempt
the exact gate-on restoration and link-off cleanup but do not repeat the trial.
If cleanup or postflight cannot be confirmed, report it directly and perform no
additional repair write without new authority.
