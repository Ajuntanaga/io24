# io24 — user guide

The app used to explain itself in the interface: every group carried a
paragraph, and together they took about a third of the window before you reached
a control. That material is here instead. Nothing was deleted, only moved.

[README.md](README.md) covers installation and the command line.
[PROTOCOL.md](PROTOCOL.md) is the reverse-engineering record.

---

## Mixer

Level and metering per input, plus bus meters and master strips.

The three aligned bus meters identify what the Host can publish. **Mix A** is
USB capture 3–4 and appears as the passive PipeWire source **io24 Host Mix A**.
**Mix B** is USB capture 5–6 and appears as **io24 Host Mix B**. The sources
route nowhere by default; another application must select one explicitly.
They are computer-side, disappear when the Host closes, and do not change the
device's Main or headphone routing. **Main is not exposed by USB capture**
because the device provides no complete Main capture pair. There are no bus-pan
controls. Mix A/B remain fixed-unity stereo sources with no channel crossing.
Older `host_features.pan` snapshot data is ignored and is never re-saved.

The command-line `pan` operation remains a different, older device-send
**stereo-pair balance**. The device has only one level per source/bus, so that
API cannot place an independent mono input in the stereo field.

Against UC 4.7.2, nothing is missing from the ordinary level-routing job:
source faders, Main/Mix A/Mix B sends and assigns, source mute, per-bus solo,
bus mute/master, phones source, blend, stereo link and the FX return all have
Linux controls. The complete send matrix lives on **Routing** instead of UC's
bus-selected Mixer view. The remaining UC fields have no faithful proven io24
representation: mono-source `pan`, `stereopan` width/mono collapse, per-input
`FXA`, `dawpostdsp`, output mono, and a writable physical Main-mute latch.
Channel/mix names are durable Host metadata. **Mirror Main** is a persistent
Host latch: Main edits continue into that aux, and clearing it restores the
aux's retained mix. The physical Main-mute button is mirrored read-only—just as
UC exposes `hardwareMute` display-only—while **Output mute** is the separate
writable software control.

**Blend** sets playback against direct monitoring. Centre is an even mix.

**Auto** (under each input's fader) is automatic preamp gain, as in Universal
Control: switch it on and the Host keeps that input's typical loud level (the
95th percentile of its meter over the last few seconds) near −12 dBFS by
itself, with nothing to confirm. It corrects only when the level drifts more
than 3 dB, at most once a second, rising up to 2 dB and falling up to 4 dB per
step; a reading at clip drops the gain 6 dB at once. It never raises the gain on
silence or a steady noise floor, only on the rise and fall of real playing or
speech. The gain fader is locked while it is on. With stereo link on the two
switches move together and both inputs get the gain the louder one needs. The
firmware has nothing behind UC's own switch, so this runs in the Host: it works
only while the Host is open. The Host remembers which inputs had it on and
switches them back on the next time it opens.

Double-click any fader or knob to return it to its default.

---

## Fat channel

The rack at the top is a navigator. **Click** a unit to open its controls;
**double-click** to switch it in or out. A lit unit is active; the outlined one
is the section you are looking at. Drag the compressor and EQ to swap them —
they are the only two the hardware can reorder, and the rest are drawn with a
lock and refuse the drop rather than pretending.

One module is shown at a time, for one channel. Both racks stay visible so you
can reach either.

**Standard EQ:** **EQ** switches the complete equaliser without erasing its
curve. Each of Low, Low mid, High mid and High has its own independent **band**
switch. Low and High also have the exact UC shelf switch; switching it off uses
parametric mode. The two middle bands are always parametric—there is no hidden
shape menu. All four bands use 36 Hz–18 kHz, ±15 dB and Q 0.1–10 (default 0.6),
matching UC 4.7.2's embedded `Eqxt4` model. Drag a node for frequency/gain and
scroll over it for Q. Global and per-band bypass states survive Host snapshots
and reconnects independently.

**Limiter**: threshold plus **release**, 50 ms to 1.5 s. The device has always
taken a release coefficient and the driver has always computed it exactly; the
page simply never offered the control, so every limiter write before this used
the 0.4 s default. UC keeps no release field in its preset record, so release
is live Host state — it rides a Host snapshot, not a device slot body.

**Passive and Vintage EQ:** choose the model in **EQ model**. Each model has its
own editable UC controls and its own global **EQ** power state. Passive exposes
Low Boost/Atten and their 20/30/60/100 Hz switch, High Boost and bandwidth with
3/4/5/8/10/12/16 kHz selection, and High Atten with 5/10/20 kHz selection.
Vintage exposes Low, Low-Mid, Hi-Mid and High gain; its first three bands have
the exact 35/60/110/220 Hz, 360/700/1600 Hz and 3.2/4.8/7.2 kHz switches. These
models have no per-band power switches in UC's component model.

The response graph and device packets are generated by UC 4.7.2's exact
designers, read from the separately retained, hash-pinned
`dspusbdevice.dll` as data. The Host does not load that DLL or substitute
generic shelves. If the local artifact is absent, enabling or editing one of
these models stops before a device write and explains what is missing. Host
snapshots, reconnect replay and user presets retain the selected model and all
of its semantic controls independently for each input.

**High-pass filters**: the Mixer strip's **HPF** is the unit's
fixed preamp switch. The Fat Channel's digital HPF is separate: choose Off,
40 Hz, 80 Hz, or 160 Hz, or select Advanced and set an exact 24 Hz–1 kHz
cutoff. The rack shows the Host's last intended digital value. That DSP value
is write-only, so the Host cannot claim it is device readback.

**Gate**: the key filter tunes what the gate listens to; key listen monitors that
side-chain so you can hear what is triggering it.

**Compressor**: the shaded area between the unity line and the transfer curve is
the gain change — red where the signal is being reduced, green where makeup is
adding. The dot is the live working point, with its input and output read off
the axes.

Three models, and they do not share a parameter set:

| model | what the controls mean |
|---|---|
| Standard | threshold, ratio and makeup, as labelled |
| Tube | an LA-2A topology. Peak Reduction drives it; Limit mode is a steeper curve than Compress |
| FET | an 1176. There is **no threshold** — Input drives a fixed one and auto-makeup compensates |

> The FET model can get **very loud**. Its auto-makeup is a steep function of
> drive: roughly unity at the default, but up to **+53 dB** with the threshold
> slider at minimum. That is faithful to the model — Universal Control behaves
> the same way — but bring monitors down before exploring it.

**Multiband** is the fourth compressor **Model**, next to Standard, Tube and
FET. The unit's firmware has no multiband, crossover or FFT vocabulary at all,
so this one runs on the computer, and choosing it switches the unit's own
compressor off: Multiband replaces it. It cannot sit inside the unit's chain,
so it comes straight after it. The io24 sends each input to the computer after
the whole Fat Channel, limiter included (its manual: it records "just as you
hear it in your headphones, complete with the Fat Channel preset"), and the
Host takes it there.

With **Multiband** selected and the **Compressor** switched on, the input
passes a phase-compensated 4th-order Linkwitz-Riley four-band split. Each band
has its own **Character** selector and the real UC control surface for that
model: Standard has Threshold, Ratio, Attack, Release, Gain, Soft knee and Auto
mode; Tube has Peak Reduction, Gain and Limit; FET has Input, Output, Attack,
Release and the five ratio-button choices. Key filter and Key listen are common
to all three. The same UC-derived builders used by the device compressor turn
those public controls into the common sidechain/timing/curve tuple consumed by
the Host processor, and the four phase-aligned bands are summed again. Changing
character does not discard the other two models' settings. Then:

- **Recording.** A new input device, **io24 Input 1+2 Multiband**, carries
  Input 1 on the left and Input 2 on the right, each processed when its channel
  has Multiband. It is the default input while Multiband is on; in a recording
  app, pick it instead of the io24's own input.
- **Listening and the stream mixes.** The processed input plays back into the
  io24 on **USB playback 1-2**. The Host takes the input's own feed out of
  Main, Mix A and Mix B wherever it was, and turns USB playback 1-2 on there
  if it was off. The input's fader keeps its position and comes back when
  Multiband is off. USB playback 1-2 also carries the computer's own audio, so
  that one fader sets both.
- **Buffer.** Monitoring now goes to the computer and back, so while Multiband
  runs the Host holds PipeWire's buffer at 128 frames (about 2.7 ms a period
  at 48 kHz) unless it is already smaller, and puts back what it was
  afterwards. Changing **Buffer** yourself keeps your choice.

Each input has its own Multiband settings; linked channels share them. The
status row says **On** only once the processing and its return are both
running. If the io24's audio is not in PipeWire yet, it says so and waits with
the input's own feed in place. If the processing cannot start, the Compressor
switch goes off and the Host says why. The compressor is bundled as source and
built once into the user's cache with the system C compiler; it requires
PipeWire but no `swh-plugins`, system-wide plugin install or sudo. Closing the
Host gives every input its own feed back, and the next launch puts Multiband
back where it was on. A device block cannot hold Multiband: saving one while it
is selected stores the unit's compressor off.

An objective physical Main-L -> Input-1 run now verifies the complete return
path and all three character graphs without requiring listening: against a
bracketed crossover-only baseline, Standard changed the 1 kHz tone by
-0.895 dB, Tube by -4.994 dB and FET by +1.482 dB, with only 0.044 dB baseline
drift. FET getting louder is expected here: the exact hardware-free graph
measures +4.350 dB for the same UC-derived fixed-threshold/auto-makeup state.
This establishes processing and model selection; the subjective feel of the
round-trip latency while playing remains a matter for the musician.

---

## Effects

### Reverb

A shared effect on block 202. It needs a channel that is processing — **Bypass**
off and a **DSP amount** above zero, both on the Device page — and the **FX
return up in a bus**; set both, or nothing is audible. The channel control is
not an isolated reverb send: bypass skips that channel's EQ, compression,
limiting and effects, while 100% is fully processed. Both channels can feed the
shared engine, but their exact amounts are write-only; device readback reports
only bypass versus nonzero.

Turning the shared reverb switch on re-sends Channel 1's processing as set on
the Device page — a bypassed channel stays bypassed — and the Main-return level
displayed beside the switch, and assigns that return to Main. Moving
reverb-character controls updates only the engine. Turning the switch off
disables only the shared engine, preserving the displayed path for the next use.

**Character** presets position the one algorithm the device has. They are not
separate reverb engines, and saying so would be a lie about the hardware:

| | size | input high-pass | pre-delay |
|---|---|---|---|
| Room | 0.28 | 220 Hz | 8 ms |
| Plate | 0.52 | 320 Hz | 14 ms |
| Spring | 0.34 | 480 Hz | 4 ms |
| Hall | 0.72 | 160 Hz | 32 ms |
| Cathedral | 0.94 | 110 Hz | 70 ms |

Moving any slider by hand drops the character back to Custom, so the label never
claims a preset that is no longer loaded.

**Wet mix** is the engine's own dry/wet, and it starts at 100 %. The reverb is a
send effect: the FX return carries what comes back from the engine, so any dry
share doubles the input that is already in the bus. Every character sets it to
100 %, which is where each Universal Control scene recovered from this unit
keeps it. Set how much reverb you hear with the FX return level, not with this.

**Movement** is genuine host-side augmentation rather than a preset: the host
drifts room size on a slow sine (about a 14-second period). The device's tail is
otherwise perfectly static, which is most of what makes a digital reverb sound
synthetic. Switching it off restores the size you set.

**Pre-delay** is the gap between the dry sound and the first reflection — in a
real room, the time sound takes to reach a surface and come back.

### Host spring reverb

This is a second, genuinely different reverb rather than another position on
the device algorithm. A bundled realtime LADSPA processor uses dispersive
all-pass stages and two decorrelated banks of damped resonators: **Dwell** sets
feedback/tail length, **Tone** sets spring loss, **Drip** sets transient splash,
and **Width** blends the two tank paths from mono to stereo. It outputs wet
signal only, so the ordinary direct input remains the dry path.

Inputs 1 and 2 are captured after their Fat Channels. The wet pair travels to
the io24 over **USB playback 5–6**, but that is only an internal return lane:
while Spring tank is on, the Host assigns it to **physical Main 1–2 only** and
temporarily removes it from Mix A and Mix B. Switching the tank off or closing
the Host restores all three prior assignments and fader states. Normal computer
playback on USB 1–2 is untouched. The active PipeWire profile must expose all
six playback channels; the Host reports that requirement instead of silently
remixing or falling back to another sound device.

Disconnect any Main-output-to-input loopback cable left from a test campaign
before enabling the spring. That cable makes the returned wet signal feed its
own input and can create loud feedback.

The spring is Host-only. It is saved in Host snapshots and the last session,
but it cannot be put in a device-resident slot or exported as a UC scene effect.
The bundled processor, impulse tail, stereo width, package contents and route
restore behavior are verified without hardware. A live Main-output acceptance
run is a separate hardware check.

### Voice FX

Block 201 is one Voice FX settings instance configured as a **two-input,
two-output processor**. Firmware maps both physical inputs into its two
processing lanes, and Doubler/Transformer binds its private reverb core to lane
0 and lane 1. The six-unit rack is the model navigator: click a unit to select
its XML component, or double-click it to toggle that component's own **On**
field. The separate **Model** row provides the same selector for keyboard and
screen-reader use. The Host presents one model at a time, and each model
page has its own **On** switch because `On` belongs to that model's component; there
is no master enable above the six models in Universal Control's component
tree. Those are independent stored controls, not six simultaneous processors:
selecting a model still replaces the one shared block-201 state. The Host does not change
`processingChannel`, which swaps physical inputs between DSP chains and is
unrelated routing state. What the hardware cannot hold is two different FX
models or settings: both lanes share one state.

The private core is not the shared Reverb section above and does not use block
202. UC's captured VoiceFX transaction also does not open or change the reverb
return; that routing belongs to the Reverb section alone. The factory preset
named **Reverb** is actually Doubler model 0 with the private-core settings
stored in its `voicefx` JSON object.

UC remembers the selected algorithm as `voicefx.__classid`. On load the Host
resolves that class, selects and fully materializes the model, and only then
applies later control edits directly to that model. It does not resend the
selector for On/Off or an ordinary knob move. Saving either channel carries
the same global FX state. A fresh component uses the XML defaults; loading a
preset replaces them with that preset's values. Detuner therefore starts at
XML index 4 (minus 4 semitones) and 50 percent WetDry.

#### What the Host sends

The selected model's **On** switch is the device command: it is the first word
of that model's state blob. The complete UC 4.7.2 USB capture contains no
separate master enable or hidden activation tag. Selecting Delay sends
`VoFx + vech`; later On/Off sends only `vech`. Selecting Transformer sends
`VoFx + two Bqdf + two MBdf + godv`; later On/Off, Width and WetDry changes send
only `godv`. The Host now follows those rules and adds no artificial delay.

The earlier Linux listening campaign used the superseded transaction: it
reselected on every edit, omitted both Transformer `MBdf` tables, inserted
20 ms gaps and opened the reverb return. Its dry result is real for that older
Host but does not test the corrected one. The corrected protocol is implemented
and hardware-verified for all six models on physical Input 1, with two
independent on/off cycles per model. Delay produced the programmed 250, 500 and
750 ms repeats; Detuner produced the exact -8-semitone targets; Ring Modulator
produced the programmed carrier sidebands; and Transformer, Vocoder and Filters
each produced repeatable spectral changes. The same-path reverb control and all
VoiceFX-off baselines passed. The corresponding Input-2 Delay run was a valid
null, so do not infer simultaneous/two-lane processing from the Input-1 result.
Reverb is a different engine and is independently measured working.

Saving a preset does not substitute for that Host transaction. The record can
contain the VoiceFX fields while standalone recall remains dry; only Fat
Channel processing is established as audible without a host.

#### Deferred post-publication custom firmware

Custom-firmware implementation is deliberately out of the initial Linux-host
release. It resumes only after the first GitHub publication. The general design
for genuinely different effects is a second VoiceFX parent/model instance,
index-aware block-201 dispatch, one instance bound to each input lane, separate
per-channel preset state, and a measured code/RAM/DSP-cycle budget.

The earlier, narrower per-lane wet/bypass proposal remains an offline design
fixture:

The historical custom-firmware branch proposed independent lane controls represented
in the saved `voicefx` object as `wet_ch1`, `wet_ch2`, `bypass_ch1`, and
`bypass_ch2`. Wet values range from `0.0` to `1.0`; omitted fields mean `1.0`
wet and not bypassed, so existing presets retain their stock behavior. The
existing `on`, `lows`, `width`, and `mix` controls remain shared by both lanes;
`mix` remains the effect's existing Wet/Dry parameter. The source-bound model-0
work path already selects a lane, loads `mix`, and calls the private reverb
core; the patch point substitutes `bypass ? 0 : clamp(mix * lane_wet, 0, 1)`.
The core performs its own final dry/wet blend.

A future firmware-capable host could emit the extended object only after an
explicit capability check. The initial-release UI keeps that control disabled
and writes only legacy Voice FX fields; stock acceptance of extra keys is not
established. In the historical shared-instance design, recalling either custom
record would restore both lanes' wet/bypass state rather than create two
separately parameterized effects. Any two records would be written
sequentially, not atomically.

Do not substitute a nearby stock control for these fields: `dspAmount` and
`bypassDSP` have no io24 device binding of their own, and the Host's DSP amount
and Bypass drive the whole-channel processing scalar, which also feeds block
202 but bypasses the whole channel chain at zero; and `processingChannel` changes
input routing rather than an effect gain. None represents a Doubler private
reverb wet control.

This design is deferred and offline only. The Linux host may document and test
its JSON representation, but no custom firmware image is distributed or ready
to write.
No safe existing model-0 storage or reclaimed model code has been proved: the
nearby per-lane coefficient arrays and models 0–5 are live. Do not attempt a
device update from this project. Any eventual hardware test is a separate
authorization and requires the original complete vendor firmware/package to be
available for recovery first.

| model | controls in exact XML order (every row also has On) |
|---|---|
| Transformer | Lows, Width, WetDry |
| Detuner | Detune, WetDry. Nine steps, −8 to 0 semitones: it only pitches **down** |
| Vocoder | Volume, Carrier Type (Noise / Sawtooth / Rect), Carrier Frequency, Voiced (read-only), WetDry |
| Ring Modulator | Frequency, Sub Carrier, Sub Carrier Frequency, Distortion, Volume, WetDry |
| Filters | Pitch, Regeneration, Damping, Distortion, Volume, WetDry |
| Delay | Time, Feedback, WetDry |

UC declares Vocoder's **Voiced** field read-only. Block 201 has no readable
state that could populate it, so the Host preserves it in the recovered schema
but does not display a permanently disabled control.

These names, ranges and defaults are not guesses: they are Universal Control's
own component model, recovered from its binary and retained in the private
research workspace. The vendor-derived XML is deliberately not redistributed;
its decoded contract agrees with this project's implementation on every
parameter.

The implementation follows the same split: [`io24_fx.py`](io24_fx.py) contains
the six exact model packet builders, while `FXVisual` and the per-model control
pages live in [`io24gtk.py`](io24gtk.py). The visual for the selected model is
driven by that model's decoded parameters and visibly marks that model **OFF**
when its own On switch is off. The six-unit rack reuses those signatures as
compact live previews; the XML parameter ID and its exact builder keyword are
the one route behind each editable row.

> **A naming discrepancy worth knowing about.** Universal Control's binary (and
> its UI) calls model 0 **Transformer**; both the io24 and io44 owner's manuals
> call the same processor **Doubler** — the io24 spec sheet lists "Doubler,
> Vocoder, Ring Modulator, Comb Filter, Detuner, Delay, Reverb". PreSonus never
> reconciled the two. This app shows **Doubler / Transformer** so either vendor
> name is recognizable. That same spec sheet's **"Comb Filter"** independently confirms what
> the decode found for Filters: a tuned feedback comb.

---

## Routing

Every source into every bus, with an assign toggle per source. `assign` takes a
source out of a bus while keeping its fader position, so toggling it twice lands
on exactly the level you left. A route for which the Host has never sent a
level is shown parked, not falsely active at 0 dB; unmuting it materializes the
displayed 0 dB send.

**S** solos a source within one bus: the bus's other sources go silent and come
back at exactly their previous levels when the solo is released. Several
sources can be soloed in a bus at once, and each bus has its own solo. The
hardware has no solo, so the Host writes the others off without touching their
faders or assigns. Solo is never saved in a snapshot, and the Host releases any
active solo when it closes. A route the Host had never set is given the 0 dB it
displays the first time its bus is soloed, so releasing has a real level to
return to.

The mute button beside each **Return** and **FX Return** source silences that
source in Main, Mix A, and Mix B while retaining its three faders and assigns.
The mute button beside each **Bus master** silences that whole output while
retaining every source level and assign in it. These are UC scene semantics
implemented by the Host over the device's individual sends; releasing either
mute restores the exact retained mix. Physical input mute remains on the Mixer
page.

**Bus master** offsets every send in a bus at once. The hardware has no such
control — block 100 holds one level per source and nothing above them — so it is
applied by rewriting each send. Measured exact to 0.00 dB, with no crosstalk.

**Mirror Main** latches Mix A or Mix B to Main levels, assignments, and
stereo-pair balance. Its own mix remains stored underneath. Main changes keep
flowing to the latched aux; switch the latch off and its exact retained mix
returns. This is durable Linux Host state, not a claim that firmware maintains
the latch after the Host closes.

Mix A is loopback to USB capture 3–4, Mix B to USB capture 5–6. The GTK Host
publishes them as **io24 Host Mix A** and **io24 Host Mix B**; these passive
sources route nowhere by default. Main is not exposed by USB capture. None of
these facts makes either bus audible at Main or headphones without an explicit
route in another host application.

Both need the card profile to expose those capture channels. The io24's six
channels are only all present in the **Pro Audio** profile (and in the
six-channel surround input profiles); the Analog Surround 2.1 profile carries
three, so Mix A and Mix B are not there at all. The Host reads the profile
rather than assuming, and when a bus is missing it says so instead of
publishing a source fed by channels that do not exist. Change the profile in
your desktop's sound settings, or with `wpctl`/`pactl`, and the sources appear
on the next reconcile. The Multiband compressor type is unaffected: it needs
only Inputs 1 and 2, which every profile with a stereo pair carries.

> The mixer has **no read-back**. The device accepts a level and will not report
> one, so these sliders show what this app last sent, not what the hardware
> holds. The Host deliberately replays that durable shadow on reconnect so its
> last mix, source/output mutes, Fat Channel, Voice FX and reverb return rather
> than disappearing after a USB or power cycle. Device-readable controls are
> adopted from the unit instead, and device block selection is quarantined from
> ordinary replay. Use `io24.py shadow clear` when cached bookkeeping is
> unwanted; clearing it does not alter the device.

---

## Device

**Sample rate** — the device supports 44.1, 48, 88.2 and 96 kHz; PipeWire
decides which is used. The Host starts at 96 kHz and a 512-frame buffer on its
first launch, then remembers and restores the last successful selections. Two
things to know if you check by hand: PipeWire's
`clock.rate` is the *default* and stays at 48000 whatever the graph is doing —
the real rate is in `/proc/asound/card*/pcm0p/sub0/hw_params` — and a forced rate
only takes effect once something is playing, because a suspended device has no
graph to re-rate.

Every coefficient this Host computes is a function of that rate: EQ and HPF
biquads, gate/compressor/limiter time constants, the reverb, and the
rate-dependent Voice FX filters. The device stores the coefficients, not the
Hz and seconds they came from, so when the clock moves the Host recomputes and
re-sends them and says so. Before this, nothing passed a rate at all and every
write was built for 48 kHz — at 96 kHz a 1 kHz EQ band was landing at 2 kHz and
a 240 ms delay was running at 120 ms.

**Buffer** is PipeWire's quantum. Latency is quantum ÷ rate, so smaller is
tighter but works the CPU harder and risks dropouts.

**Output delay** holds one output back so it lines up with a delayed remote
signal — a co-host on a call, or a stream's video path. 0–500 ms in 2 ms steps.
It is one global delay plus a bus selector, not an independent delay per bus.

**Channel Mute Sync** matches UC's mute-behavior setting: when enabled, a
channel Mute follows Main, Mix A, and Mix B. It is write-only, so the switch and
scene loader show what this Host last sent, not device readback. UC names the
enabled value and the owner's manual defines the behavior; the `1 = enabled`
value remains a protocol inference because the io24 exposes no readable slot
for it.

**Channel processing** gives each input Universal Control's **DSP amount** and
**Bypass**. Behind both is the one processing value the device keeps per
channel: Bypass sends zero, which skips that channel's EQ, dynamics and
effects; otherwise the amount is sent. The amount is remembered and greyed out
while bypassed, and it cannot reach zero by itself, so a bypassed channel always
shows as one. The device reports only bypassed versus processing, so the exact
amount is what this Host last sent. The switch also follows the unit's
press-and-hold once the device has reported the new state for half a second (a
short Preset press only blips it, and is ignored); a channel the unit turns
back on shows 100%. A slot recall on a bypassed channel likewise turns
processing back on at 100%, and the controls follow. UC's own
`dspAmount`/`bypassDSP` routes have no recovered device binding; pairing them
onto this one value is the Host's reading of UC's schema, whose amount minimum
sits just above zero.

Use intermediate DSP Amount values only when a parallel whole-chain sound is
actually wanted. A live no-listening meter test with a controlled EQ showed a
linear dry-to-processed blend at 0/25/50/75/100%; it is not a channel level or
send. That makes the control useful for effects such as parallel compression,
but a poor control for corrective processing:

- With EQ or a high-pass filter, the dry path restores frequencies the filter
  was meant to remove and can change the intended phase response.
- With a gate, the dry path leaks the signal around the gate.
- With a limiter, dry peaks bypass the ceiling, so the output is no longer
  reliably limited.

For those modules, leave DSP Amount at **100%** while processing is enabled and
use the module's own parameters or bypass. Treat **Bypass** as the normal
whole-chain on/off control. Voice FX **Wet/Dry** and reverb **Wet mix** remain
separate effect-specific controls; DSP Amount does not replace them. The live
result establishes the functional blend law, not whether the firmware
literally implements two parallel signal paths.

**Host component names** lets you label Inputs 1/2, all three USB playback
pairs, FX return, Mix A/B, and Main. UC keeps these `username` values in its
component model rather than sending a label-write command to the io24, so Linux
stores them with Host snapshots and scenes. The separate **Device-reported
channel names (read-only)** group shows the unit's small `CHNP` table.

The Mixer page's **Physical Main Mute (read-only)** follows the front-panel
MUTE latch. UC also exposes `hardwareMute` only as display state; neither Host
has a writable command for that physical latch. **Output mute (software)** is
the independently writable Main-bus mute.

---

## Presets

The page has a **Load into** row, a search box, a **Preset name** field with
**Save**, and two drop-downs: **User Presets** and **Factory Presets**. The
search filters both by name and description.

### Loading

Click the preset's **Load** button to load it into the channel chosen in
**Load into**. Its Fat Channel goes to that channel; while the channels are
linked, the Fat Channel goes to both. FX has one global state, so the same
action also adopts and sends the preset's recorded FX intent.

A Host-known **Device Presets** record is replayed through the ordinary Fat
Channel and Voice FX setters, matching UC's RestorePreset behavior. It does not
select a front-panel block. Historical front-panel `Stat` receipts are a
separate legacy list: on their own channel the Host selects that block and then
replays its retained record because selection alone did not reapply the
unreadable body in the retained live test. A block the Host did not write can
only be selected, and the UI says that its body is unknown instead of pretending
to load it. If the target channel is bypassed, Load enables processing; a
channel already processing keeps its exact DSP amount.

A loaded preset is shown on the controls, so the pages stop describing the
previous sound. A recalled Passive/Vintage EQ selects its own exact editable
panel and response curve rather than being misrepresented as four Standard
bands.

### User Presets

First come known Device Presets library records, followed by historical
front-panel-block transport receipts. A receipt is not proof that a body was
installed: the io24 can report a selected front-panel block but cannot return
either kind of stored body, and the objective `Stat` inactive-slot tests did
not apply the test EQ/gate state.

Then come the presets you saved on this computer.

### Saving, and sending to Device Presets

Type a name and press **Save**: the **Load into** channel's current sound,
Voice FX included, joins your presets on this computer, in
`~/.config/io24/user-presets.json` (the factory file's format). Saving over an
existing name asks first. FX is one global settings object, so either channel's
preset carries the same current FX state.

Choose one of six **Device Presets destinations** for the selected channel.
Each preset's **⋯** menu offers **Send to Device Presets**. This uses UC's actual
`MemP/PrsM` Store route: indexes 16–21 belong to Input 1 and 22–27 to Input 2.
It is separate from the four front-panel button blocks. The Host validates and
sends a complete record, then retains an identity-bound receipt with status
`WRITE_SENT_UNVERIFIED`. The io24 cannot return that body, so the status is not
called device readback, cold-boot persistence, or standalone VoiceFX proof.

Known Device Presets appear under **User Presets**. **Load** performs UC's
RestorePreset behavior by replaying the retained record through the normal Fat
Channel and VoiceFX setters; it does not move a front-panel selector. Historical
front-panel `Stat` receipts remain visible as legacy Host-assisted records, but
the disproved writer is no longer offered as a normal action. Your own presets
also have **Delete**, which removes them from this computer only.

### Scenes

**Save scene…** writes the readable and Host-known device state atomically with
Universal Control's scene field names. It includes exact semantic Standard,
Passive, and Vintage EQ state from the editor and the selected Voice FX model's
own On value. It also includes every complete front-panel-block and Device
Presets body retained for this exact unit. Unknown bodies, physical slot
selection, and any other unknown value are reported and omitted; they are never
guessed. The saved file is proven to round-trip through this Linux Host, not
through the untested Universal Control import path.

**Load scene…** applies a Universal Control `.scene` from the Presets page. The
Host parses and validates the entire file before the first device
write. It covers the global delay and headphone source, Channel Mute Sync,
preset-button mode, both Fat Channels and DSP amounts, Standard/Passive/Vintage
EQ, the complete Main/Mix A/Mix B matrix, source and output mutes, Host solos,
bus masters, persistent Mirror Main, shared Voice FX and shared reverb. The three
retained UC scenes plan 94–97 real Host operations each. Their device-resident
preset libraries are reported but never overwritten.

The io24 has no faithful mapping for mono-source pan, stereo width, exact `FXA`
reverb sends, `dawpostdsp`, or output mono fold-down. The loader reports those
fields explicitly instead of mapping them to a nearby control. Text names and
Mirror Main round-trip as Host-persisted UC state. Because Voice FX is one shared processor, two
conflicting per-channel Voice FX records make validation fail before transport.
Once a valid plan starts, writes are sequential. A USB/runtime failure stops on
that setting, prevents later writes, and triggers compensation from the exact
pre-load readable state, Host write mirror, and solo state. The UI says rollback
is complete only when every attempted control had known prestate and every
restore write succeeded. A partial result names unknown prior values or restore
errors; the device itself has no transaction primitive.

### Factory presets

The originals from Universal Control, decoded from the installer and applied
through this driver. Standard, Passive and Vintage EQ records all load through
their own exact model routes. Any remaining module the io24 does not implement
is skipped rather than silently dropped; a preset that cannot be applied says
why and is not partially presented as successful.

### The unit's Preset button

**Preset blocks on the unit** (Device page, **Preset button**) sets how many
blocks the unit's Preset button steps through: **One**, **Two** (what the unit
ships with), or **None**. It is write-only; the device never reports it back.

> In **Two**-block mode the Preset button is visible to the app: pressing it
> walks that channel's two blocks and the **· playing** tag follows, and
> press-and-hold bypasses the channel while the Device page's **Bypass**
> follows. In One-block mode a press has nowhere to go, so nothing moves.

The button lands on the pair's first block. On the Mixer, each strip's dot shows
its active block: solid with a breathing brightness (block 1 every 1.8 s, block
2 every 0.9 s), and an outlined dot when bypassed. With reduced motion the dots
stay steady and differ slightly in size.

### Host snapshots

A snapshot also carries the Host-only half of the reverb — the named
**character**, **movement**, and **movement depth**. The device has no
parameter for any of them, so a save that kept only the device values came back
with the character reset to Custom. Saved values that are unreadable, unknown,
or out of range are refused with a completed-load notice rather than quietly
moving a control.

`savepreset` / `loadpreset` keep arbitrarily many settings as JSON. A preset
holds the live values the device *can* report, plus this driver's mirror of the
DSP writes it has made.

Two consequences: loading a preset applies what is in it and does not reset
settings the preset never mentioned; and the mirror is a claim about what was
last sent, not a reading. Device preset mode, slot selection, and enable state
are quarantined by default, so loading a Host snapshot or reapplying cached
controls cannot move or disable either channel's device slot. The lower-level
API has an explicit opt-in for workflows that intentionally include those
selectors.

GTK Host snapshots also save both inputs' Multiband settings under the versioned
`host_features.multiband_insert` object, with the reverb character and which
inputs have Auto gain on. The Host spring's On state, two input sends, Dwell,
Tone, Drip, Width and pre-delay are stored under
`host_features.spring_reverb`. What the Host changed in the unit's mixer for
Multiband, and the buffer it borrowed, belong to the running session and are
left out of snapshot files; the spring's temporary Main-only return ownership
is treated the same way. A snapshot written before 2026-09-11 carries the
retired playback multiband as `host_features.multiband`: its settings are
loaded into both inputs' Multiband, switched off, and a completed-load notice
says so. The passive source lifecycle is reconciled separately. Obsolete `host_features.pan` data is discarded with a completed-load
notice, regardless of its old contents, and is never re-saved. Other invalid
Host-only data is rejected before any device setting is applied. These objects are deliberately absent
from device-slot records, cached-device reapply,
and standalone-device claims. Older snapshots without these objects continue
to load and do not change the current Host-only state.

### Making settings persist

The Host picks up where it left off, as Universal Control did. Everything it
sends to the unit is kept on disk (`~/.cache/io24/shadow.json`), and its own
features (both inputs' Multiband, reverb character and movement, and which
inputs have Auto gain on, plus the Host spring) are saved to
`~/.config/io24/last-session.json` every few seconds and on exit.

Each time the io24 connects, the Host re-sends the settings the unit cannot
keep through a power cycle (EQ, dynamics, mixer, source/output mutes, reverb,
Voice FX, DSP amount and Bypass) and shows them on the controls. What the unit
reports itself (gains, phantom power, input/headphone mute, stereo link,
volumes, the selected block) comes from the unit, so a change made on the
hardware while the Host was closed stands. The selected block is never moved.
Voice FX is restored with its exact model transaction and model-local On state;
the Host does not claim a device block activated it and does not mutate
`processingChannel`. Host-only features come back once per launch, not on every
reconnect.

Two consequences: settings changed from Universal Control on another computer in
between are overwritten on the next connection, and solo starts off each launch,
as it did in Universal Control. Auto gain, which Universal Control also started
off, comes back on for the inputs that had it.

`io24.py startup save` and `systemd/io24-startup.service` remain for applying
settings without the Host window — see
[README.md](README.md#making-settings-stick). For a sound that plays with no
computer at all, the unit's own preset storage is the intended path. Fat
Channel is established standalone; Voice FX is not, so keep the Host available
when that effect is part of the sound.
