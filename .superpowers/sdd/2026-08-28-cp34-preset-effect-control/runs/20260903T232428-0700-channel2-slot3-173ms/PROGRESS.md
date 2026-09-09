# Progress

- [x] Authority recorded: full CP34 access; channel-2 preset blocks only.
- [x] Fresh preflight: serial `AB7C22200355`, firmware descriptor 1.28,
  battery 89%, channel 1 slot 0 enabled, channel 2 slot 2 enabled.
- [x] Native USB and ALSA availability confirmed; no preset write or selector
  change had occurred before the trial.
- [x] Channel-2-only runner implemented test-first. Its contracts reject a
  channel-1 target and the active channel-2 target before a `Stat` write.
- [x] Dry-run record validation: 860 bytes,
  `b609139abc514c67171f047252c554529287bd679cb5df416e391397fc49c3ed`.
- [x] One bounded `Stat(3)` write and channel-2 selection: post-state reports
  slot 3, two empty `SetP` acknowledgements, and unchanged guarded channel-1
  state. See `RESULT.json`.
- [x] Complete hardware-free regression suite after the runner repair: 197
  tests passed, one expected skip, in 233.811 seconds. The only diagnostic was
  the pre-existing unclosed-file warning from `cp34_current_slot_survey.py`.
- [x] Final read-only snapshot: 95% battery, channel 2 slot 3 enabled, and
  two identical JaSt replies. Channel 1 remains slot 0 but reports disabled.
- [x] Post-cabling passive capture: fresh preflight passed at 96% battery with
  channel 2 still enabled on slot 3 and channel 1 still left untouched. The
  retained three-second Input-2 capture contains a -24.14 dBFS signal but not
  the five isolated impulses required for a delay measurement; it makes no
  Voice-FX conclusion. See `PASSIVE-AUDIO-BASELINE.json`.
- [x] Operator audible check using a finger-touched free patch-cable end on
  Input 2: direct sound was heard, with **dry only** reported and no separate
  173 ms repeat. Fresh post-observation preflight passed at 98% battery with
  channel 2 still enabled on slot 3 and channel 1 untouched. This is an
  inconclusive negative—not proof that the stored Voice FX is absent—because
  the source was not a calibrated isolated line-level transient. See
  `PHYSICAL-OBSERVATION-RESULT.json`.
- [x] Native-host execution was separated from audibility. The open GTK host's
  `arm-channel2-delay` action was repeated once while its short-lived result was
  read from the host UI: Channel 1's guard was unchanged, Channel 2 remained
  enabled on slot 3, and both exact Delay frames were sent for 173 ms, 25%
  feedback, and 50% wet/dry. The operator's earlier **dry** report therefore
  does not mean the host action failed. One possible delay-like moment shortly
  after restart is retained as an unconfirmed, non-repeatable observation. See
  `HOST-ACTION-RESULT.json`.
- [x] Controlled native-host action repeat: the operator reported **no audible
  difference; dry**. This makes the earlier possible one-off moment
  non-reproducible and confirms that the current exact host sequence does not
  establish audible Voice FX.
- [x] Root-cause comparison found that the host action reselected slot 3 while
  slot 3 was already active; firmware's native `Stat` application is triggered
  by a changed selector. Through the still-open host, Channel 2 alone was moved
  global slot `3 -> 2 -> 3`, with both transitions and the final return to slot
  3 reflected by the host UI after one-second settle intervals. No preset
  content or direct block-201 parameter was written. See
  `RECALL-EDGE-RESULT.json`.
- [x] Physical result after the controlled Channel-2 recall edge: **dry only**.
  Direct audio remained present, so this was not a mute or routing loss; the
  changed selector still did not establish audible Voice FX.
- [x] Byte-exact factory control added test-first to the native host. The action
  rejects every near-match before a device call and accepts only the recovered
  850-byte `Slap Echo` record with wire SHA-256
  `a6c3294b62cfb3a46122a82c93514ea2aeb836280fb5d1e458707a78634f87eb`.
  Its focused persistence/action suite passed 28 tests.
- [x] At 99% battery, the restarted native host sent that exact record only to
  Channel-2 global slot 3 and forced `3 -> 2 -> 3`. The host's final state check
  reported Channel 2 enabled on slot 3 and the Channel-1 guard unchanged. It
  sent one fragment and received no transport reply; this remains a submission,
  not commit or audibility proof. See `FACTORY-SLAP-ECHO-RESULT.json`.
- [x] Exact factory-control observation: the operator reported **"dry all dry
  everytime"**; no distinct 150 ms repeat was heard. This rules out the 173 ms
  customization and record-shape differences as the leading explanation, but
  it still does not distinguish device record uptake from recall dispatch that
  never reaches block 201. See `FACTORY-SLAP-ECHO-RESULT.json`.
- [x] The operator explicitly ruled out the headphone channel as the cause.
  No output-routing or headphone control will be changed; the remaining fault
  boundary is slot-record storage versus structured recall dispatch.
- [ ] Attribute or, only with operator direction, restore the channel-1 preset
  enabled flag. It was true in the pre-trial 89% snapshot and false before the
  final trial's guarded write window; no final-trial frame targets channel 1.
- [ ] Continue offline from the sealed changed-selector dispatcher evidence:
  source-bind whether recall reaches block 201 or the distinct dynamic slot-two
  component. Separately retain full slot-record readback as unavailable until
  an independently decoded record exists.
