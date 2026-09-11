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
only while the Host is open, and it starts off each time the Host opens.

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

**Limiter**: threshold plus **release**, 50 ms to 1.5 s. The device has always
taken a release coefficient and the driver has always computed it exactly; the
page simply never offered the control, so every limiter write before this used
the 0.4 s default. UC keeps no release field in its preset record, so release
is live Host state — it rides a Host snapshot, not a device slot body.

**Passive and Vintage EQ.** A device preset stored with the Passive Program or
Vintage 1970s EQ can be recalled, but the Host can neither draw nor edit those
models: the Vintage switch frequencies were never recovered, and Passive has
never appeared in a real preset. After such a recall the rest of the chain is
shown as usual, and the Equaliser lists the stored EQ read-only, each switch as
a position with the Neve 1073 frequency beside it marked unverified. The
Standard band controls are paused on that channel, and saving the channel to a
slot keeps the stored EQ exactly. **Edit with Standard EQ instead** lifts the
pause; nothing is sent until you move a band, and from then on the Standard
bands are written over it.

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

**Multiband compressor** (bottom of the page) is host-side, and says so: the
firmware capability sweep is a clean negative — no multiband, crossover or FFT
vocabulary exists in the device — so this one runs as a PipeWire filter-chain
on the computer instead. Enabling it creates an **"io24 Multiband"** output
device; route an application (or the system output) through it and the audio
passes a 4th-order Linkwitz-Riley four-band split with an `sc3` compressor per
band on its way to the interface. The compression stage needs
`sudo apt install swh-plugins`; without it the Host refuses to show the
multiband switch as enabled and tells you what is missing. The processing runs
inside PipeWire's own
realtime graph — not in this app — so it adds no load to the mixer and cannot
touch the device's latency.

The switch reports **On** only after the public **io24 Multiband** node appears.
Starting a child process is not treated as success; an early exit or missing
node turns the switch back off and reports the failure.

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

**Movement** is genuine host-side augmentation rather than a preset: the host
drifts room size on a slow sine (about a 14-second period). The device's tail is
otherwise perfectly static, which is most of what makes a digital reverb sound
synthetic. Switching it off restores the size you set.

**Pre-delay** is the gap between the dry sound and the first reflection — in a
real room, the time sound takes to reach a surface and come back.

### Voice FX

Block 201 is one Voice FX settings instance configured as a **two-input,
two-output processor**. Firmware maps both physical inputs into its two
processing lanes, and Doubler/Transformer binds its private reverb core to lane
0 and lane 1. That establishes the capacity for the same private-reverb state
on both lanes, not that stock routing enables both concurrently. Universal
Control traditionally selects one physical input for Voice FX at a time. What
the hardware cannot hold is two different Doubler settings: both lanes share
`on`, `lows`, `width` and `mix`.

The private core is not the shared Reverb section above. It does not use block
202 or the FX return. The factory preset named
**Reverb** is actually Doubler model 0 with the private-core settings stored in
its `voicefx` JSON object.

UC remembers the selected algorithm as `voicefx.__classid`. On load it resolves
that class, selects the model, and only then applies the model fields. The
Linux host exposes the exact
route through `with_fx=True`, CLI `--voicefx`, and the GTK **Load + Voice FX**
button. The opted-in load first assigns the singleton VoiceFX layer to the
requested physical channel, then selects the model, then applies `voicefx.on`
and its model fields. A direct model edit sends the owner once, then the selected
model and state; the Device page's DSP amount and Bypass are the shared reverb
path and are not part of Voice FX activation. Detuner starts at the factory
Detuned Vocal values (minus 7 semitones, 80 percent wet) instead of the neutral
zero-semitone position.

#### The device's Voice FX gate

Configuring a model is not switching it on. Block 201's own USB handler checks
three flags on the FX object before it dispatches anything, and returns having
done nothing when any of them fails — no error, no reply difference, no audio.
Only the native `Stat` structured-state load sets all three, and **recalling a
device slot is the decoded way to run that load**. So a model armed by direct
writes alone is accepted, stored and silently discarded; that is why a fully wet
Delay could be sent successfully and still be inaudible, while the shared reverb
on block 202 — which has no such gate — worked in the same session.

The **Device activation** row at the bottom of the Voice FX section says which
of the two is happening:

| Row says | Meaning |
|---|---|
| **Not this session** | No recall this session. The device cannot report its own gate, so this is the Host's knowledge, not a reading |
| **Opened** | A record whose `voicefx.on` is set was recalled on this channel |
| **Closed** | A record was recalled, but its stored Voice FX is off |
| **Unknown** | A slot the Host never wrote was recalled; slot bodies have no readback |

To open it, recall a preset whose Voice FX is on — from the **Host presets**
list on the Presets page, from that channel's slot blocks, or from the unit's
own Preset button. After that, model and parameter edits reach the engine.

Changing the Voice FX target can exchange the two slot indicators exposed by
the device. The Host therefore sends the owner assignment only for the first
send on a connection or when the chosen target actually changes; moving a
model slider does not keep touching the slot-sensitive assignment route.

The four version-2 defaults embedded in firmware have asymmetric contents, but
that is not a slot-ownership rule. UC's own scene schema gives all four slot
objects a `voicefx` member, and its exact active-slot writer sends the complete
tagged scene-shaped record. The earlier Channel-2 dry trial omitted the separate
`Assign Voice FX` control, which is the meaningful missing condition.

Two prior acceptance attempts set `Assign Voice FX = Ch2` and wrote the complete
factory **Reverb** record to global slot 3, but their runners then used preset
control channel 1. Assignment does not renumber those APIs, so readback proves
they selected/enabled physical Channel 1 while Channel 2 stayed elsewhere. The
closed-host listening is therefore not a valid Channel-2 recall result. Channel
1's selector has since been restored without writing either of its preset
bodies.

The final stock discriminator now keeps the layers separate: VoiceFX ownership
is assigned to Input 2, while bypass, slot selection, and enable all address
physical Channel 2. It also performs model-before-state and raises the factory
Reverb Wet/Dry value from 29.5% to 100% for an unmistakable test. Its default
command remains hardware-free:

```bash
python3 re/cp34_channel2_voicefx_materialization_stage.py
```

The separately authorized corrected live run sent this maximum-wet sequence
and left physical Channel 2 enabled on global slot 3. After unplugging and
reconnecting the interface, the user noticed no audible change. Later routing
checks exposed a stale/malformed Linux Host shadow, a missing Main FX-return
level, wrong Channel-2 factory targeting, and one-leg balance attenuation.
Consequently that listening result is retained as evidence but is no longer a
terminal stock-firmware verdict. A clean Host-controlled Channel-2 round trip
is required before distinguishing record commit, persistence, parsing, model
activation, the processing gate, or recall. Do not repeat live mode without new
exact authorization.

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

| model | controls (PreSonus's own names) |
|---|---|
| Transformer | Lows, Width, Wet/Dry — richness and depth with a hint of reverb |
| Detuner | Detune, Wet/Dry. Nine steps, −8 to 0 semitones: it only pitches **down** |
| Vocoder | Carrier Type (Noise / Sawtooth / Rect), Carrier Frequency, Volume, Wet/Dry |
| Ring Modulator | Frequency, Sub Carrier, Sub Carrier Frequency, Distortion, Volume, Wet/Dry |
| Filters | Pitch, Regeneration, Damping, Distortion, Volume, Wet/Dry |
| Delay | Time, Feedback, Wet/Dry |

These names, ranges and defaults are not guesses: they are Universal Control's
own component model, recovered from its binary and kept in
[re/uc_component_model/](re/uc_component_model/). It agrees with this project's
decode on every parameter.

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

**Bus master** offsets every send in a bus at once. The hardware has no such
control — block 100 holds one level per source and nothing above them — so it is
applied by rewriting each send. Measured exact to 0.00 dB, with no crosstalk.

**Mirror main** copies the main mix's levels into an aux bus. A one-shot copy;
the bus does not keep following main afterwards.

Mix A is loopback to USB capture 3–4, Mix B to USB capture 5–6. The GTK Host
publishes them as **io24 Host Mix A** and **io24 Host Mix B**; these passive
sources route nowhere by default. Main is not exposed by USB capture. None of
these facts makes either bus audible at Main or headphones without an explicit
route in another host application.

> The mixer has **no read-back**. The device accepts a level and will not report
> one, so these sliders show what this app last sent, not what the hardware
> holds. USB reconnect never silently replays the cache, and the GTK header no
> longer presents a standing cache-reapply question. Explicit Host snapshot
> save/load is the normal recovery path. Use `io24.py shadow clear` when cached
> bookkeeping is unwanted; clearing it does not alter the device.

---

## Device

**Sample rate** — the device supports 44.1, 48, 88.2 and 96 kHz; PipeWire
decides which is used. Two things to know if you check by hand: PipeWire's
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

**Channel names** are read from the device's own table.

---

## Presets

The page has a **Load into** row, a search box, a **Preset name** field with
**Save**, and two drop-downs: **User Presets** and **Factory Presets**. The
search filters both by name and description.

### Loading

Double-click a preset to load it, Fat Channel and Voice FX together, into the
channel chosen in **Load into**. While the channels are linked it loads into
both, and the chosen channel owns Voice FX.

A preset that lives on the unit loads from the unit itself when it belongs to
that channel: the device runs its own `Stat` load for that block, which is also
what opens the Voice FX gate. Loaded into the other channel, the Host applies
the same record instead. Because a bypassed channel never reaches the device's
load, the Host turns processing on when, and only when, the device reports the
channel bypassed; a channel that is already processing keeps its exact amount.

A loaded preset is shown on the controls, so the pages stop describing the
previous sound. A recalled Passive/Vintage EQ has no Standard-band form, so the
Fat Channel shows it read-only rather than as four derived bands.

### User Presets

First come the presets this Host has put on the unit, tagged **On the unit ·
Channel N, block M**, with **· playing** on the block each channel currently
has selected. Those entries are the Host's own record of what it wrote: the
io24 reports which block is selected but cannot return a block's contents, so
a block the Host never wrote is not listed.

Then come the presets you saved on this computer.

### Saving, and putting a preset on the unit

Type a name and press **Save**: the **Load into** channel's current sound,
Voice FX included, joins your presets on this computer, in
`~/.config/io24/user-presets.json` (the factory file's format). Saving over an
existing name asks first. Voice FX belongs to one input at a time, so saving
the channel that does not own it stores its Voice FX switched off.

Each preset's **⋯** menu has **Put on the unit's button, block 1** and
**block 2**. That writes the complete preset into that block of the **Load
into** channel and then loads it, after one confirmation that names what it
replaces. The block the channel is playing is refused; choose the other one.
Channel 2 blocks do not load Voice FX, so their confirmation warns that an
included effect will not play from that block.
Your own presets also have **Delete**, which removes them from this computer
only.

A unit write is a complete-record `MemP/Stat` operation: global slots 0/1 are
channel 1's two blocks and 2/3 are channel 2's. Each write leaves a
device-identity-bound receipt in `~/.local/state/io24/device-slots.json` (or
`$XDG_STATE_HOME`) marked `WRITE_SENT_UNVERIFIED`, because the device cannot
return the stored body for comparison.

### Factory presets

The originals from Universal Control, decoded from the installer and applied
through this driver. Any module a preset needs that the io24 does not implement
is skipped rather than silently dropped. A preset the Host cannot apply
directly (Passive/Vintage EQ) says why and cannot be loaded.

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

GTK Host snapshots also save the complete multiband panel under the versioned
`host_features.multiband` object. The passive source lifecycle is reconciled
separately. Obsolete `host_features.pan` data is discarded with a completed-load
notice, regardless of its old contents, and is never re-saved. Other invalid
Host-only data is rejected before any device setting is applied. These objects are deliberately absent
from device-slot records, cached-device reapply,
and standalone-device claims. Older snapshots without these objects continue
to load and do not change the current Host-only state.

### Making settings persist

The Host picks up where it left off, as Universal Control did. Everything it
sends to the unit is kept on disk (`~/.cache/io24/shadow.json`), and its own
features (the multiband panel, reverb character and movement, and which inputs
have Auto gain on) are saved to
`~/.config/io24/last-session.json` every few seconds and on exit.

Each time the io24 connects, the Host re-sends the settings the unit cannot
keep through a power cycle (EQ, dynamics, mixer, reverb, Voice FX, DSP amount
and Bypass) and shows them on the controls. What the unit reports itself (gains,
phantom power, mute, headphone mute, stereo link, volumes, the selected block)
comes from the unit, so a change made on the hardware while the Host was closed
stands. The selected block is never moved. If the last session had Voice FX on,
the owning channel's selected block is loaded first, because the unit plays
Voice FX only after loading a block, and that channel's saved DSP amount is
then sent again. Host-only features come back once per launch, not on every
reconnect.

Two consequences: settings changed from Universal Control on another computer in
between are overwritten on the next connection, and solo starts off each launch,
as it did in Universal Control. Auto gain, which Universal Control also started
off, comes back on for the inputs that had it.

`io24.py startup save` and `systemd/io24-startup.service` remain for applying
settings without the Host window — see
[README.md](README.md#making-settings-stick). For a sound that plays with no
computer at all, put a preset on the unit's button.

