# io24 — a Linux driver for the PreSonus Revelator io24

PreSonus ships Universal Control for Windows and macOS only. On Linux the io24
works as a class-compliant audio interface — you get audio in and out — but
everything that lives in the device's DSP is unreachable: preamp gain, the
mixer, EQ, compressor, gate, limiter, reverb and the FX models.

This is a userspace driver that reaches nearly all of it, by speaking the
device's own native control protocol over its vendor-specific USB interface.
Preamp, mixer, EQ, dynamics, reverb, routing, output delay and sample rate all
work. The device-slot format is decoded too: firmware 1.28 stores and recalls a
native version-2 chunk record through `MemP/Stat`. UC 4.7.2 also emits a tagged
scene archive from its 500 ms settled-state synchronizer, but its explicit
Store action uses the separate `PrsM` library route, and an objective live test
showed that the tagged body does not apply as an io24 slot. Firmware configures
block 201 as one shared
settings object over two structural input/output lanes. The GTK Host therefore
configures it once for both inputs and never mutates the separate
`processingChannel` permutation as an FX owner control. Its UC 4.7.2 lifecycle
is now captured and implemented: select/materialize once, then state-only edits
with no reverb-return mutation. All six Host VoiceFX models are objectively
waveform-verified through physical Input 1; simultaneous two-lane processing
remains unproved. See
[Current hardware and validation limits](#current-hardware-and-validation-limits).

The control implementation is not based on unpublished PreSonus source code.
The project began with
[oddbear/Revelator.io24.Api](https://github.com/oddbear/Revelator.io24.Api),
whose public UCNET work documents the host-to-service layer and supplied the
original route/client reference. The device does not speak UCNET over USB, so
this project continues below that layer. The native protocol and exact Host
algorithms were recovered from shipped Universal
Control binaries and the device's own firmware, with public manuals used for
names and intended behavior and live claims kept separate. The write-up is in
[PROTOCOL.md](PROTOCOL.md) — it is the real documentation, and if you want to
write your own client for this device or a sibling model, start there.

Day-to-day use — what each control does, and the caveats that matter — is in
[GUIDE.md](GUIDE.md). It used to live inside the app as paragraphs above every
group, which cost about a third of the window.

The source-publication boundary and release checks are in
[PUBLICATION.md](PUBLICATION.md).

## What works

Hardware-verified unless the row says otherwise. The two front ends and the
shim are software over the same verified driver calls, so they are marked
separately rather than implied to be independently measured.

| | |
|---|---|
| Preamp gain, phantom power, mute, fixed 80 Hz preamp HPF, stereo link (mono → stereo) | gain law and levels measured; the app's link switch drives the device and follows it back |
| Fat Channel digital HPF | Off/40/80/160 basic choices plus exact 24 Hz–1 kHz Advanced cutoff; independent of the fixed preamp HPF |
| Headphone / main volume, monitor blend, channel processing/effects mix | live 0/25/50/75/100 meter test confirms one linear dry-to-full-chain blend; exact positive value remains write-only |
| Input, bus and gain-reduction metering | |
| Mixer: per-source level into main / Mix A / Mix B | gain law exact to **0.03 dB over a 106 dB range** on all three buses |
| Aux sends: assign, source/output mute, bus master, persistent Mirror Main | mute retains faders/assigns; master exact to **0.00 dB**, no crosstalk between buses; Mirror Main retains the hidden aux mix and restores it when released |
| GTK Mix A/B capture | independent Host-only PipeWire sources for USB capture 3–4 and USB capture 5–6; both published successfully in the live 96 kHz / 512 smoke |
| CLI pan / balance for a stereo pair | send-level balance using Universal Control's recovered law; centre −3.00 dB, measured within ±1 dB on hardware |
| Standard 4-band EQ | exact UC 4.7.2 controls: independent global and four band-power switches, parametric middle bands, outer shelf/parametric selectors, 36 Hz–18 kHz; frequency accuracy and band indexing measured |
| Passive Program / Vintage 1970s EQ | exact editable UC 4.7.2 controls, designers and `Lfdf[0]` + `Bqdf[1..3]` live routes; source- and packet-verified offline, with a dedicated audible A/B still pending |
| Gate, compressor (3 models), limiter | |
| Reverb | measured processing; **both channels can feed it at once** |
| Host spring reverb | a separate wet-only dispersive/resonator tank for physical Inputs 1/2, returned on USB playback 5–6 and assigned to **physical Main 1–2 only** while enabled. Settings and route restoration are hardware-free tested; a live Main-output acceptance run has not yet been performed. |
| Output delay, 0–500 ms | one global delay plus a bus selector — not an independent delay per bus. 50 ms asked, 49.50 ms measured |
| Sample rate 44.1 / 48 / 88.2 / 96 kHz | device clocks at 96 kHz on demand |
| Processing-channel select | which input feeds a channel's DSP chain |
| Channel-name read-back (`names`) | the device's own `'CHNP'` table |
| UC component names | writable Host metadata for inputs, returns, FX return, Mix A/B and Main; saved in Host presets/scenes because the io24 has no label-write command |
| Presets (host-side JSON) | full round-trip, 13 setting categories |
| UC Device Presets store | exact `MemP/PrsM` Store route, indexes 16–21 for Input 1 and 22–27 for Input 2, with six visible destinations per channel and an identity-bound `WRITE_SENT_UNVERIFIED` receipt. **Load** replays the retained complete record, matching UC's RestorePreset behavior. |
| Front-panel preset buttons | the four `MemP/Stat` records are firmware/front-panel selection state, not UC's explicit Store destination. The earlier writer is retained only as a low-level research primitive and is no longer exposed as a normal GTK action. |
| Voice FX control model and UC transaction | exact XML-ordered controls and builders for all six models, a six-unit visual rack, one global settings object over two structural lanes, and a separate **On** state per model component. A UC 4.7.2 USB capture controls model selection, state-only edits, Transformer `MBdf` tables and pacing. All six models are objectively verified through physical Input 1 in two on/off cycles each: exact Delay timing, Detuner pitch targets, Ring Modulator sidebands, and repeatable Transformer/Vocoder/Filters spectral changes, with same-path reverb controls and stable off states. |
| **Universal Control scene save/load** (`io24_scene.py`) | prevalidates and applies all supported sections of a real UC `.scene`, and atomically saves readable plus Host-known state with UC field names. Every complete front-panel-block and Device-Presets body known to this exact unit is included; load reports those libraries but never overwrites them. A failed load compensates from its pre-load checkpoint and reports whether rollback was complete or partial. |
| GTK4 mixer app (`io24gtk.py`) | both channels side by side — meters, strips, draggable EQ nodes + spectrum, dynamics, clickable rack, routing, device page |
| Browser UI (`io24web.py`) | a subset — meters, both channels, monitor and presets. Binds to localhost by default; pass `--bind` to reach it from a phone |
| UCNET shim | lets UCNET-speaking clients talk to the device |

## Current hardware and validation limits

Firmware 1.28 contains four native version-2 startup/default records and sixteen
tagged factory/library presets. Its `MemP/Stat` ingress and recall path preserve
the stored body byte-for-byte, and the io24 structured-state consumer requires
the leading native word `2`. UC's separate settled-state sender starts its
tagged record with byte `0x7b`; that generic host-side path is not a usable io24
firmware slot representation.

UC's `processingChannel == 0` conditional arbitrates which channel object owns
the shared model in its host tree. The firmware evidence is more direct: block
201 is one settings object configured two-in/two-out, while
`processingChannel` swaps physical inputs between two DSP chains and can also
exchange exposed slot indicators. The Linux Host no longer uses that routing
mutation for ordinary FX control. It selects one global model and applies
that mutable component's own `voicefx.on` and fields once. The GTK page mirrors
the vendor model: its rack selects among the six mutable components, each page
has its own **On** switch, and the remaining controls follow XML order, names,
ranges, defaults, lists, and skew curves. Only the selected model exists in the
one shared block-201 settings instance.

| | |
|---|---|
| Physical acceptance of UC Device Presets store | The correct UC `PrsM` Store transaction is implemented and locally receipted, but the device exposes no body readback. A USB reply is therefore still `WRITE_SENT_UNVERIFIED`, not proof of cold-boot persistence or standalone VoiceFX audibility. The negative +15 dB shelf/gate experiment targeted the different `Stat` front-panel record route. |
| Corrected Host VoiceFX audibility | All six models process audio on physical Input 1 in two repeatable on/off cycles each. Delay timing, Detuner pitch targets, and Ring Modulator sidebands are frequency/time-specific; Transformer, Vocoder, and Filters have repeatable gain-normalized spectral signatures. The prior dry listening campaign used the superseded transaction. A separate valid Input-2 run detected no Delay, so simultaneous/two-lane operation is not implied. Saved VoiceFX data still does not establish standalone audibility. |
| Private reverb on both inputs at once | Structurally supported, not audibly proved: block 201/model 0 has one settings instance and its private core binds lanes 0 and 1. The Host configures that state globally; simultaneous routing/gating still needs the live experiment. |
| Independent private-reverb settings per channel | Not possible without custom firmware: both lanes share one `on/lows/width/mix` setting set. |
| Front-panel recall capacity | Two button-selectable `Stat` blocks per input. UC's separate Device Presets library has six entries per input, but storing a library record does not assign another front-panel button. |
| Reading firmware back | The DFU interface reports `Upload Unsupported`. |
| Multiband dynamics | No firmware support. The Linux Host provides a four-band Linkwitz-Riley insert with per-band Standard, Tube or FET controls compiled through the recovered UC model mappings into its bundled processor. All three characters are objectively verified through the physical Main-L -> Input-1 loop; the exact offline graph and live path agree on each model's direction, including FET's expected auto-makeup increase. |

For Doubler/Transformer specifically, do not involve shared reverb block 202.
The factory preset named `Reverb` is a complete tagged library template for
Voice FX model 0 and supplies `on`, `lows`, `width` and `mix`. It can drive the
live setters, but it cannot be installed directly as a firmware slot body. The
private core uses the same
algorithm implementation as block 202 but is a different state object and
signal path.

### Custom firmware — deferred until after initial publication

No custom-firmware implementation is part of the initial GitHub release. A
future independent-channel design would require a second VoiceFX parent/model
instance, index-aware dispatch, one instance per input lane, separate stored
state, and proven code/RAM/DSP-cycle headroom. That work resumes privately only
after the Linux host is published.

The narrower historical per-lane-control proposal remains an offline design
fixture:

The firmware has two Doubler-private-core lanes but stock firmware exposes one
shared Voice FX state. The experimental branch is designed to add a wet gain
and bypass for each lane without changing the existing model-0 controls. Its
proposed `voicefx` extension is:

```json
"wet_ch1": 1.0,
"wet_ch2": 1.0,
"bypass_ch1": false,
"bypass_ch2": false
```

`wet_ch1` and `wet_ch2` are limited to `0.0` through `1.0`. When any of these
fields is absent, the firmware must retain stock behavior: wet `1.0` and not
bypassed. `on`, `lows`, `width`, and `mix` remain the shared Voice FX fields;
in particular, `mix` remains the private algorithm's existing Wet/Dry control,
not a replacement for either lane gain. The source-bound hook selects the
active lane at model `+0x338`, replaces the scalar loaded from model `+0x358`
before the private-core call, and lets the core's existing final dry/wet blend
do the work: `effective_mix = bypass ? 0 : clamp(mix * lane_wet, 0, 1)`.

Because block 201 is one two-lane singleton, a future custom-firmware design
would store both lane controls alongside the shared model state. The extension
would still not create independent model-0 parameter sets, and it would also
need to address the stock one-input-at-a-time routing/gate. No stock save is
known to accept these extra fields, and no such extension is implemented.

This is an offline implementation design, not a shipped firmware feature. No
custom image is included in this repository, no image is ready to flash, and no
hardware behavior has been claimed for it. The remaining firmware blockers are
newly owned runtime storage with parser/reset lifecycle handling and a safe,
reviewed executable placement; the nearby per-lane 0.5 coefficient arrays and
all model code are already live and must not be reused. A future, separately
authorized live test must begin with the original complete vendor image/package
available for recovery and must validate updater compatibility, restore,
audible operation, slot recall, and power-cycle survival. The offline package
tool accepts only the pinned UC 4.7.2 io24 package (target, vector, length and
SHA-256) and has no device/defaults/detach command. Do not use the device's DFU
interface or attempt a firmware write on the basis of this documentation.

## Install

**System packages first.** `pyusb` is a ctypes binding, not a driver: without
the libusb shared library it imports cleanly and then fails at the first device
call with `No backend available`, which looks like broken hardware rather than a
missing package.

```bash
sudo apt install libusb-1.0-0 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

(Fedora: `dnf install libusb1 python3-gobject gtk4 libadwaita`.) The GTK
packages are only needed for `io24gtk.py` — the CLI, the web UI and the library
need just libusb. Having GNOME installed is **not** sufficient on its own: the
desktop ships the C libraries, but the *Python* bindings and typelibs above are a
separate package on most distributions.

Install the checkout into the active Python environment. This installs PyUSB,
the Capstone decoder used by the exact Passive/Vintage EQ paths, and every
command-line entry point, including `io24-scene`:

```bash
python3 -m pip install .
```

To run directly from a checkout without installing the project, install its two
Python dependencies explicitly:

```bash
python3 -m pip install 'pyusb>=1.2' 'capstone>=5,<6'
```

System GTK packages are still required for `io24-mixer`.

Then the udev rule, so nothing here needs root:

```bash
sudo cp 70-presonus-io24.rules /etc/udev/rules.d/ && sudo udevadm control --reload
```

Replug the device afterwards. The rule tags the device `uaccess`, which makes
logind grant an ACL to whoever is **logged in at the local seat** — so it works
for a normal desktop login and does *not* help over SSH, in a container, or for a
second user. If you need access without a local session, add a `GROUP=` of your
own to the rule; it deliberately sets no group.

### Putting it in the applications menu

```bash
./install-desktop.sh
```

Installs a launcher, a `.desktop` entry and the icon under `~/.local`, then
refreshes the desktop and icon caches. After that the app is in the overview —
press the super key and type *Revelator*. `./install-desktop.sh --remove` undoes
all of it.

The app opens with or without the interface. Unplugged, it shows an offline
banner — host-side features like the multiband compressor still work — and the
moment the io24 is plugged in, the controls attach and go live. Unplugging
mid-session parks the controls and they re-attach on return.

### Checking it worked

```bash
python3 io24.py status
```

If that prints the device's parameters you are done. `No backend available` means
libusb is missing; `not found — plugged in?` with the device connected usually
means the udev rule has not been applied or the device was not replugged.

## Use

### The mixer app

```bash
python3 io24gtk.py
```

A native GTK4 / libadwaita application — the Linux replacement for Universal
Control's window. Live meters for both inputs and all three buses, gain reduction
for the gate, compressor and limiter, channel strips, monitoring, a four-band EQ
with UC's independent global/band switches, exact outer shelf controls, a
256-bin overlapping live spectrum and response curve, dynamics, and
preset save/load. The Mixer fits all four strips in the default desktop window;
the Presets page holds your presets and the factory presets in two drop-downs,
loads one with the row's **Load** button, sends a complete selected-channel
record to any of UC's six **Device Presets** destinations per input, and loads
complete UC `.scene` files. The older front-panel `Stat` writer is a low-level
research primitive, not a normal Host action.

It needs the GTK4 and libadwaita Python bindings from the Install section — the
desktop having GTK is not the same as the bindings being present. Device work is
queued onto a worker thread, so dragging a slider enqueues writes rather than
blocking the UI on them. (Strictly there are two threads that touch USB: the
worker, and the one-shot probe at start-up that finds the device. They do not
overlap.)

### The browser mixer

```bash
python3 io24web.py
```

A subset of the app's controls at <http://127.0.0.1:8424/> — meters, both
channels, monitoring and presets, not the full mixer. **It does not use the
internet**: one self-contained 14 KB page, no CDN, no external requests, no build
step.

It defaults to loopback, so a phone cannot reach it as shipped. To use it from a
phone or tablet over USB tethering or a local hotspot you must bind wider:

```bash
python3 io24web.py --bind 0.0.0.0
```

Do that only on a network you trust — there is no authentication whatsoever, and
anyone who can reach the port can change your monitoring.

Only one process can hold the control interface at a time, so run the app *or*
the web UI *or* `io24d` *or* `ucnet_shim` — not several at once.

`io24d` serves newline-delimited JSON over a Unix socket, but **no front end in
this repo speaks that socket yet** — the app and the web UI each open the device
directly. So running the daemon does not let them share the device, it locks them
out of it. It is useful if you are writing your own client (`io24d.py --client`
is one), not as a general way to run everything at once.

### From the command line

```bash
python3 io24.py status
```

```bash
python3 io24.py gain 1 35
```

```bash
python3 io24.py meters 10
```

`io24.py --help` lists every command. A few worth knowing:

```bash
python3 io24.py eq 1 lowmid peaking 800 -6 1.4
```

```bash
python3 io24.py savepreset vocal.json
```

Mix A and Mix B are the loopback buses that feed the computer's record channels,
and they are what Universal Control calls **aux1** and **aux2** — either name
works. Mix A is USB capture 3–4 and Mix B is capture 5–6; neither is a local
monitor path to Main or headphones. Each source has a send level, an assign,
and a per-bus master:

While the GTK Host is running, it publishes those exact pairs as passive
PipeWire sources named **io24 Host Mix A** (USB capture 3–4) and
**io24 Host Mix B** (USB capture 5–6). They route nowhere by default: recording
or monitoring software must choose and route a source explicitly.
Main is not exposed by USB capture. The device provides no complete Main
capture pair. These computer-side sources disappear when the Host closes.

```bash
python3 io24.py send line/ch1 aux1 -6
```

```bash
python3 io24.py bus aux1
```

`assign` takes a source out of a bus while keeping its fader position, so
toggling it twice lands on exactly the level you left. `busmaster` trims a whole
bus, and `mirror <bus>` copies the main mix's levels into an aux bus in one go.
An assigned route with no prior fader value now materializes at 0 dB instead of
being accepted by the UI while producing no device write.

The command-line **pan** operation is a stereo-pair balance, exactly as
Universal Control did it — UC folds
`volume + aux + blend + pan` into the single number the mixer accepts, and its
pan law was recovered from the host binary (−3.00 dB at centre):

```bash
python3 io24.py pan line/ch1 main left
```

The device gives one level per (source, bus) and ignores the mixer blob's index
field, so there is no way to place a *mono* source in the stereo field. What this
does is a **balance across a stereo pair** — `line/ch1`+`line/ch2` or
`return/ch1`+`return/ch2` — which is what pan means on a two-input interface, and
matches UC's own two-mode law. Panning a source with no partner raises rather than
silently attenuating it.

The GTK Mixer shows only meters for Main, Mix A, and Mix B; it has no bus-pan
controls. Mix A/B are published as fixed-unity stereo sources with their left
and right capture channels kept on their original sides. Host snapshots no
longer save bus pan. An obsolete `host_features.pan` object in an older file is
ignored and reported after a completed load. This is separate from the CLI
pair-balance command above.

Compared with UC 4.7.2, the Linux Host already covers the functional mixer
matrix — fader/send level, assign, source mute, per-bus solo, bus mute/master,
Main/Mix A/Mix B, phones source/blend, stereo link and FX return — but places
the complete matrix on **Routing** instead of swapping one selected bus through
the Mixer view. What remains unavailable is not hidden UI: the io24 has no
faithful proven wire representation for UC's mono-source `pan`, `stereopan`
width/mono collapse, exact per-input `FXA` reverb send, `dawpostdsp`, output
mono, or a writable physical Main-mute latch. Writable UC component names are
retained as Host metadata. Mirror Main is a persistent Host latch that follows
subsequent Main edits and restores the retained aux mix when cleared; it does
not claim a device-side latch that survives without the Host. UC also presents
physical `hardwareMute` as display-only, while Linux's Output mute is the
separate writable software-bus control.

The device's own channel-name table reads back with:

```bash
python3 io24.py names
```





### Every command

Sources are `line/ch1..3`, `return/ch1..3`, `fxreturn/ch1`; buses are
`main`, `mixa` (alias `aux1`) and `mixb` (alias `aux2`).

| | |
|---|---|
| `status` | show all named parameters |
| `meters [secs]` | live levels + gain reduction |
| `gain &lt;ch&gt; &lt;dB&gt;` | preamp gain, 0..60 |
| `hpvol &lt;0..1&gt;` | headphone volume |
| `mainvol &lt;0..1&gt;` | main output volume |
| `blend &lt;-1..1&gt;` | monitor blend |
| `phantom &lt;ch&gt; &lt;on\|off&gt;` | 48 V phantom power |
| `mute &lt;ch&gt; &lt;on\|off&gt;` | input mute |
| `hpmute &lt;on\|off&gt;` | headphone mute |
| `link &lt;on\|off&gt;` | stereo link the inputs |
| `hpf &lt;ch&gt; &lt;on\|off&gt;` | `'Appl'` high-pass enable |
| `hpfreq &lt;ch&gt; &lt;Hz&gt;` | `'filt'` high-pass cutoff, 24..1000 (24 = bypass) |
| `limiter &lt;ch&gt; &lt;on\|off&gt; [dBFS]` | limiter, default −28 dBFS |
| `order &lt;ch&gt; &lt;comp\|eq&gt;` | which of compressor / EQ runs first |
| `eq &lt;ch&gt; &lt;band&gt; &lt;shape&gt; &lt;Hz&gt; [dB] [Q]` | band `low\|lowmid\|himid\|high` or 0..3; shape `peaking\|lowshelf\|highshelf\|hp\|lp\|off` |
| `eqflat &lt;ch&gt;` | flatten all four EQ bands |
| `send &lt;source&gt; &lt;bus&gt; &lt;dB\|off&gt;` | a source's send level in a bus |
| `assign &lt;source&gt; &lt;bus&gt; &lt;on\|off&gt;` | take a source in/out of a bus, keeping its level |
| `busmaster &lt;bus&gt; &lt;dB&gt;` | trim every send in a bus at once |
| `pan &lt;source&gt; &lt;bus&gt; &lt;pos&gt;` | balance a stereo pair — `0..1`, or `left\|centre\|right`, or `off` |
| `mirror &lt;bus&gt;` | copy the main mix's levels into an aux bus |
| `procchan [&lt;ch&gt; &lt;input&gt;]` | which input feeds a channel's DSP chain (setting one swaps both) |
| `delay &lt;ms&gt; [bus]` | output delay 0..500 ms; bus `mixa\|mixb\|off` |
| `delay off` | clear the output delay |
| `bus &lt;bus&gt;` | what this driver believes is in a bus |
| `savepreset &lt;file.json&gt;` | save a Host snapshot; device slot/mode/enable state is excluded by default |
| `loadpreset &lt;file.json&gt;` | apply a Host snapshot without moving or disabling device slots |
| `saveprivatereverb ...` | retired safety stub: rejects the obsolete paired tagged-record operation before a slot write |
| `names` | the device's channel-name table (`'CHNP'`) |
| `shadow [clear]` | show (or reset) the write mirror |

Five more are investigation helpers, listed in the driver's module docstring
rather than its command help:

| | |
|---|---|
| `dump` | one JaSt state read, hex + float view |
| `stable [n]` | n reads; classify offsets as stable vs volatile (meters) |
| `snap <file>` | save a state snapshot — every read kept, not averaged |
| `diff <a> <b>` | diff two snapshots, ignoring volatile offsets |
| `watch [secs]` | report stable-slot changes live, for mapping controls |

### Effects

> **The FET compressor can get very loud.** It models an 1176: there is no
> threshold, the *input* drives a fixed one, and auto-makeup compensates. That
> makeup is a steep function of the drive — around unity at the default, but up to
> **+53 dB** with the threshold slider at its minimum. That is faithful to the
> model rather than a bug, and Universal Control behaves the same way, but bring
> monitors down before exploring it. Standard and Tube are bounded by their 0–28 dB
> makeup control and carry no such surprise.

There are two different things here, and they behave differently.

The **block-202 reverb** is a shared effect, so **both channels can use it
simultaneously**. Its input amount is not an isolated reverb send: wire
parameter 4 is each channel's entire **processing / effects mix**. Zero bypasses
EQ, compression, limiting and effects; a positive value enables the chain, and
100% is fully processed. Bring the FX return up in a bus as well:

```bash
python3 io24.py fxmix 1 0.4
```

JaSt reports only zero versus nonzero for this scalar. The exact positive value
is Host-written and cannot be recovered from device readback. Older Host builds
incorrectly exposed the same state twice as a reverb-send slider and a preset-
enable switch; those controls could overwrite one another and bypass a saved
compressor. Current snapshots canonicalize them to one scalar.

The **Doubler/Transformer private reverb** is a third, distinct path. It lives
inside Voice FX model 0; it is neither block 202 nor either channel's block-202
send. Firmware maps both physical input selectors into two processing objects,
sets singleton block 201 up with two inputs and two outputs, and binds private
core lanes 0 and 1. This makes simultaneous use a concrete live hypothesis; it
is why the Linux Host now keeps one global FX state for both lanes. Audible
simultaneous processing remains unproved.

There is still only one model-0 settings instance, so the two inputs share
`on/lows/width/mix`; different private-reverb values per channel cannot coexist.
The differing four embedded firmware defaults do **not** establish a legal
slot-content ceiling. UC's scene schema carries `voicefx` in all four slot
objects. The tagged mapping emitted by UC's settled-state synchronizer does not
pass the firmware's native version gate. Recalling a Host-known historical
receipt is followed by one explicit global FX-state send;
the recall itself is not treated as activation.

The historical stock acceptance runner derives its target from the factory Reverb
record but raises the private Wet/Dry value from 29.5% to 100% so success is
unmistakable. It requires and reasserts the Input-2 assignment, keeps preset
operations on physical Channel 2, and materializes the saved model before
saving. The runner and fixture remain in the private research workspace:

```text
Private campaign runner and factory-derived fixture are not redistributed.
```

The retained private runner is hardware-free and pins Channel 2, global slot 3, the
exact factory-derived maximum-wet record, its four model-before-state messages,
the exact slot frame, and `Assign Voice FX = Ch2`. Its historical live run was
confounded by inconsistent Host routing. A later clean listening campaign
opened the same send/return path, proved that path with audible block-202
reverb, then found Delay and an all-six fully wet block-201 sweep dry. That
Host transaction is superseded: the current UC-derived transaction is now
waveform-verified for all six models on Input 1. Cold boot with a stored
Voice-FX-on slot and no Host attached remains a separate standalone-preset
question. The old paired builder remains only for offline custom-firmware
comparison; current GTK control does not use its owner assignment.

The Fat Channel (EQ, gate, compressor, limiter) is separately per-channel — the
firmware has two instances of each block. And `procchan` chooses which physical
input feeds a chain, though setting one swaps both:

```bash
python3 io24.py procchan 1 2
```

### Sample rate

The device runs at 44.1, 48, 88.2 and 96 kHz. PipeWire ships allowing 48 kHz
only, so widen it once:

```bash
mkdir -p ~/.config/pipewire/pipewire.conf.d
printf 'context.properties = {\n    default.clock.allowed-rates = [ 44100 48000 88200 96000 ]\n}\n' > ~/.config/pipewire/pipewire.conf.d/10-io24-rates.conf && systemctl --user restart pipewire pipewire-pulse wireplumber
```

After that the mixer app's Device page can switch rate and buffer size. On a
first launch the Host selects 96 kHz and a 512-frame quantum; after that it
remembers and restores the last successful choices. Two things to know if you
check the rate by hand: PipeWire's `clock.rate` is the
*default* and stays at 48000 whatever the graph is doing — the real rate is in
`/proc/asound/card*/pcm0p/sub0/hw_params` — and a forced rate only takes effect
once something is actually playing, because a suspended device has no graph to
re-rate.

### Output delay

The device can hold one output back by up to 500 ms, in 2 ms steps, so a local
signal lines up with a delayed remote one — a co-host on a call, or a stream's
video path. Universal Control puts this beside the sample rate, and so does the
mixer app's **Device** page. From the command line:

```bash
python3 io24.py delay 40 mixa
```

```bash
python3 io24.py delay off
```

Unlike the rate and buffer rows, this one writes the hardware rather than asking
PipeWire for anything. Measured on the device: asking for 50 ms produced 49.50 ms
on Mix A and 49.25 ms on Mix B. `off` and the unselected settings measured 0.00 ms
on both loopback buses — the analog outputs cannot be observed without a loopback
cable, so those are unproven rather than known-inert. There is no read-back, so
the control shows what was last sent.

```bash
python3 calibrate.py level
```

The device's USB playback return doubles as a calibrated signal generator — a
tone played into it arrives inside the mixer at exactly unity gain, so you can
measure the mixer and buses with no cable and no microphone:

```bash
python3 calibrate.py usbtone 20 1000 -26
```

### As a library

```python
from io24 import Io24

d = Io24()
d.set_gain(1, 35.0)
d.set_compressor(1, on=True, threshold_db=-24.0, ratio=3.0,
                 attack_s=0.01, release_s=0.15, gain_db=2.0)
d.set_eq_band(1, "lowmid", shape="peaking", freq_hz=800, gain_db=-6, q=1.4)
d.set_mix_db("line/ch1", -6.0, bus="mixa")
d.close()
```

Only one process can hold the control interface at a time. `io24d.py` exists for
that reason: it keeps the device open and serves JSON lines over a Unix socket,
so several clients can share it.

## The pieces

| file | what it is |
|---|---|
| `io24.py` | transport, named parameters, DSP chain, presets, CLI |
| `io24_dsp.py` | recovered coefficient maths — gate, compressor, limiter, biquads |
| `io24_mixer.py` | fader taper and pan law, mixer blob builders |
| `io24_fx.py` | exact packet builders plus the retained-XML schema and XML-field → builder-keyword routes for all six Voice FX models |
| `io24_meters.py` | meter datagram decoding, reverb |
| `io24d.py` | daemon: holds the device, multiplexes clients |
| `io24gtk.py` | the GTK4 mixer app — including the six-unit Voice FX rack, parameter-driven selected-model visual, and exact XML controls |
| `io24web.py` | the same, in a browser, for phones and tablets |
| `ucnet_shim.py` | speaks UCNET, so existing clients can drive the device |
| `io24_scene.py` | applies a Universal Control `.scene` file to the device |
| `calibrate.py` | measurements that need a known input signal |
| `probes/` | three original first-read/write probes kept as executable evidence |
| private research workspace | extracted tables, captures, and recovered UC data that are not redistributed |

## Presets and standalone use

### Loading a Universal Control scene

Universal Control saves the whole device state as JSON under
`Documents/PreSonus/Revelator IO/Scene/*.scene`. Those files can be applied
directly from the Linux Host's Presets page or the command line. Scene load
never overwrites device-resident blocks:

```bash
python3 io24_scene.py --dry-run "B A S E.scene"
```

```bash
python3 io24_scene.py "B A S E.scene"
```

The Presets page also has **Save scene…**. It writes readable input state and
the exact write-only state retained by this Host using UC's `global`, `line`,
`return`, `fxreturn`, `aux`, `main`, and `fx` field vocabulary. The command-line
equivalent is:

```bash
python3 io24_scene.py --export io24-host.scene
```

The file is replaced atomically only after it validates through the same scene
planner used for load. It round-trips through this Linux Host. Values the Host
cannot know are listed and omitted rather than invented: an unknown device-slot
body, an enabled-but-unshadowed DSP Amount scalar, physical preset selection,
monitor knob values that have no supported scene field, and Host-only features
such as Multiband. Complete front-panel-block and Device Presets bodies retained
in the current unit's identity-scoped registries are exported under `presets`;
scene load reports them but never writes them. This is not a claim that
Universal Control itself accepts the Host-known export; that application round
trip has not been tested.

The dry run validates the complete scene before the first device write and lists
every planned operation and every typed omission. It restores global delay,
headphones source, Channel Mute Sync, preset-button mode, both Fat Channels,
DSP amount, the full Main/Mix A/Mix B matrix, source and output mutes, Host solo,
bus masters, persistent Mirror Main, shared VoiceFX, and shared reverb. Standard,
Passive, and Vintage EQ each use their exact model route. The three retained UC
scenes produce 94–97 operations apiece.

Load is compensating-transactional. Before the first write the Host captures
readable device state, its exact write mirror, and Host solo state. If any
setter fails, later scene settings are not sent and the checkpoint is replayed
without moving a physical preset slot. The result says **rollback complete**
only when every attempted control had exact prestate and every restore write
succeeded. Otherwise it names a partial rollback; the protocol has no native
device transaction and unknown write-only prestate cannot be reconstructed.

Genuinely unrepresentable fields remain explicit: block 100 has no independent
mono-source pan or stereo-width control; exact `FXA`, `dawpostdsp`, and output
mono fold-down have no proven io24 mapping. Component names and Mirror Main are
exact Host-persisted UC state; neither is misrepresented as a firmware command.
The Host never substitutes its stereo-pair balance for a scene's mono pan.

A channel saved with UC's **Passive Program** or **Vintage 1970s** EQ now loads
directly into the Linux Host. The model selector, power switch, amount controls,
frequency switches, defaults, coefficient designers, packet tags, widths and
live indexes all come from UC 4.7.2. The Host emits the same complete route UC
does: `Lfdf` index 0 followed by `Bqdf` indexes 1, 2 and 3. It never flattens an
alternate model into four Standard biquads.

The exact designers read the separately retained, hash-pinned UC 4.7.2
`dspusbdevice.dll` as data; the DLL is not loaded or executed. Set
`IO24_UC472_DSPUSBDEVICE` to a lawful local copy when it is not at the retained
project path. An enabled alternate EQ fails before transport if that artifact
or the Capstone decoder is unavailable. A bypassed model can still emit four
exact identity sections without the artifact. The factory **Big Vocal** record
supplies an authentic Passive state, and validated native records can also
receive exact Passive or Vintage replacements without changing other
components.

Three things the importer gets right that are easy to get wrong. The two channels
can be running **different compressor models** — UC tags each block with a class
GUID, and Standard (`threshold`/`ratio`/`gain`) and FET (`input`/`output` plus a
ratio *index*) do not share a parameter set, so the GUID is honoured rather than
assumed. And a channel's EQ may be stored in either the full parametric form
(real Hz and Q, the same representation the firmware's factory presets use) or
UC's alternate index form; both are applied faithfully through their own model.
And VoiceFX is one shared processor: one saved component is applied once, while
conflicting per-channel VoiceFX records are refused before transport instead of
silently making the later channel win.


Firmware contains **sixteen tagged factory/library presets**, in two banks of
eight (Broadcast, Vocal, Acoustic, Electric, Slap Echo, Detuned Vocal, Robot,
Bass Guitar, Stereo Acoustic/Piano/DJ …). Four version-2 startup/default records
also exist. Those native records are the only representation source-bound
through firmware `Stat` storage and recall into the structured-state loader.
The tagged library schema does not constrain future native saved fields, but it
cannot be substituted for the native record on the wire.

PreSonus's own documentation (the io44 manual's "Presets and Scenes" section)
describes the design: each channel reaches **2 presets from the hardware
buttons**, there are **6 more factory presets**, and **6 user slots per
channel**. The 2 + 6 factory count matches the 16 tagged records found in
firmware. The retained UC 4.7.2 Store path writes the six Device Presets slots;
no command that assigns one of those library entries to a front-panel button was
captured or recovered.

The GTK preset menu can send a complete selected-channel record through UC's
actual `MemP/PrsM` Store route to one of six Device Presets destinations per
input. It records serial, VID/PID, firmware, canonical body hash and transport
counts in `$XDG_STATE_HOME/io24/device-presets.json` (default
`~/.local/state/io24/device-presets.json`) with status
`WRITE_SENT_UNVERIFIED`. That is deliberately not called device readback or a
durable commit: the io24 cannot return the stored body.

**Load** performs UC's RestorePreset behavior by replaying a Host-retained
Device Presets record through the normal Fat Channel and VoiceFX setters; it
does not select a front-panel block. Historical `Stat` receipts remain available
as clearly labelled legacy records. Fat Channel is established as audible
without the Host after the device applies it; VoiceFX remains Host-assisted
rather than standalone.

## Making settings stick

Host-side startup persistence remains useful for arbitrary current driver state:

```bash
python3 io24.py startup save
```

That stores everything the driver knows about — low cut and its cutoff, EQ,
dynamics, processing mix, routing, output delay, armed FX — as an on-connect preset. Then
install the unit so it is re-applied whenever the interface appears:

```bash
cp systemd/io24-startup.service ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user enable io24-startup
```

`io24.py startup` shows what is saved, `startup clear` removes it. To have it fire
on plug-in as well as at boot, add to the udev rule:

```
TAG+="systemd", ENV{SYSTEMD_USER_WANTS}+="io24-startup.service"
```

This startup path is the *host* restoring the device, so it only runs on a
machine with this driver installed. Device-resident `MemP/Stat` saves are the
standalone path, but do not treat them as accepted for production use until the
pending physical recall and power-cycle checks have passed.

## A note on measurement

Some results in PROTOCOL.md were obtained with a "ratio metric" — the difference
between the post-DSP bus meter and the pre-DSP input meter — on the assumption
that it cancelled the source. **It does not** (§13): the two meters have
different dB slopes, so the difference moves by 20 dB across a gain sweep and
*amplifies* source changes rather than removing them. Sections that relied on it
are marked. Results that used a calibrated tone against absolute levels — the
mixer gain law, the bus master, the output delay, the loopback lag — are
unaffected.

## Things to know when using it

**The DSP blocks are write-only.** Every block accepts settings and none reports
them back — the only readable state is the small `'Appl'` parameter set (gain,
volumes, phantom, blend) plus the meters. So the driver keeps a mirror of what it
has written, in `~/.cache/io24/shadow.json`, and that mirror is what presets are
built from. It is a claim about what was last sent, not a reading: after a power
cycle, or after Universal Control has touched the device from another host, the
cache is not proof of current hardware state. Since 2026-09-11 the GTK Host
re-sends that cache on every connection so it resumes where it left off (see
GUIDE.md, *Making settings persist*), leaving out what the unit reports itself:
mute, headphone mute and stereo link.
Device preset mode, slot selection, and enable calls are
quarantined from ordinary snapshot and cached-state replay, so those actions
cannot move or disable a selected device slot. Run `io24.py shadow clear` when
that cached state should instead be discarded.
Forgetting changes Host bookkeeping only; it emits no device command.

GTK Host snapshot files store both inputs' current Multiband state in
`host_features.multiband_insert`. Older `host_features.multiband` and version-1
generic compressor controls are accepted, migrated to the Standard/Tube/FET
schema and never written back in the old form.
The Host spring is stored independently as `host_features.spring_reverb` with
its On state and complete tank controls. Its temporary ownership of USB
playback 5–6 routing belongs only to the running session, so a named snapshot
does not overwrite another session's prior Main/Mix A/Mix B assignments.
Obsolete `host_features.pan` data from an older Host is ignored and is never
re-saved. Host-only objects are never
encoded into a device slot; the GTK Host restores them once per launch from
`~/.config/io24/last-session.json`, not on a USB reconnect. If a required computer-side chain fails, the Host
reports the failure instead of claiming success.

**Settings survive the host closing, but not a power cycle.** They live in the
device's RAM. Verified: gains, EQ and a running reverb were all still there after
the USB interface was fully released and reopened. A cold boot resets them to
firmware defaults.

**Loud-EQ warning.** An EQ **shelf with Q above ~1 is a resonant shelf** and
overshoots the gain you asked for — at the maximum Q of 10 a +15 dB shelf peaks
at +33 dB. Every setting in range is numerically stable, but stable is not the
same as quiet. Q ≤ 0.7 on shelves and filters gives exactly the gain you asked
for. And the four bands cascade, so four at +15 dB is +60 dB, not +15.

**Remaining limits.** Standard peaking, low-shelf, and high-shelf coefficient
routes are source-bound to UC 4.7.2's selector-6, selector-8, and selector-9
double-precision designers, including binary32 input narrowing, operation
order, and output-field order. Their current regression vectors use Python's
math library and are not independent UC output captures. A complete Standard
EQ can be encoded at all four device clocks into a validated native record.
Passive and Vintage are exact, editable Host models when the pinned local UC
4.7.2 DLL is available. Their UC live call sites and packet order are
source-bound, and hardware-free packet regressions pass; their audible device
response has not yet received a dedicated live A/B run. The compressor's knee
semantics remain inferred rather than proved.

**The device can drop into its bootloader under sustained load** — see Safety
below. It has always recovered from a power cycle.

## Safety

The driver never sends `'FRst'`, and the FourCC is deliberately not even defined
in the source.

**The device can drop into its bootloader under sustained load.** It has
happened twice, both times during runs that drove `aplay`/`arecord` hard while
also sending a stream of control writes. The signature is always the same and
the *audio* interface fails first:

```
usb 3-1: clock source 5 is not valid, cannot use
usb 3-1: 1:1: cannot get freq (v2/v3): err -110
usb 3-1: USB disconnect
usb 3-1: Product: Revelator IO 24 BOOTLOADER      (194f:0405)
```

**Recovery is a cold power cycle**: unplug at the device end, wait ~15 s, replug.
It has recovered completely every time and the flash was never damaged. Through a
powered hub the disconnect may not actually reach the device, so watch for a
`USB disconnect` line in the kernel log.

Do not flash it. The DFU interface reports `Upload Unsupported`, so the device
will accept a firmware write and will never hand its existing flash back — there
is no way to take a recovery image from the device first. The experimental
custom-firmware branch therefore requires an original complete vendor package
to be retained as the only prospective recovery source; it remains offline and
is not authorization to write DFU.

An earlier version of this section blamed writes to unmapped wire parameter ids.
That was wrong, and the firmware disassembly disproves it: the `'Para'`
dispatcher bounds-checks to 1..14 and routes ids 5-9 and 11-13 to a shared
`pop {pc}` — those writes do nothing at all. `set_param()` still asks for
`unsafe=True` on ids it has no mapping for, but as a speed bump against writing
values with unknown ranges, not as protection against bricking.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).

Chosen because this is a hardware driver: copyleft means anyone who ships a
modified version has to publish their changes, so the reverse-engineering effort
stays available to the next person who needs their io24 to work on Linux. The
license applies to this project's original work; it does not relicense third-
party material retained in the private research tree.

### What is PreSonus's, and what is in this tree

The driver, the GTK app and the protocol documentation are original work,
produced for interoperability: making hardware its owner already possesses
function on Linux. The GPL above covers that work and only that work.

The private research workspace retains material **derived from PreSonus's
software**. It is not part of this public source tree or the Python wheel, and
its redistribution status is not asserted by this project's GPL:

| path | what it is |
|---|---|
| `re/param_consumers.txt` | ~3,100 lines of Ghidra decompiler output for 20 functions of `dspusbdevice.dll`, kept because the parameter tables and route strings are only legible alongside the code that consumes them |
| `re/uc_factory_presets.json` | 41 factory Fat Channel preset records, extracted verbatim from the Universal Control installer payload — names, class GUIDs and coefficients |
| `re/uc_component_model/dsp_fx_params.xml` | component-model XML extracted from `studiolivepanel.dll` |
| `re/uc_component_model/dspusb_component_model.xml` | io24 component-model XML extracted from `studiolivepanel.dll` |
| `re/uc_component_model/fatchannelxt_eq_contract.xml` | a bounded transcription of the embedded Standard-EQ component contract |
| `re/uc_component_model/fatchannelxt_alternate_eq_contract.xml` | a bounded transcription of the embedded Passive/Vintage component contract |

These files are retained privately as research evidence. Without
`uc_factory_presets.json` the Host remains usable but shows the factory-preset
browser as unavailable. A user may recover optional data from a lawfully
obtained Universal Control installer for personal interoperability work.

Also not included: `dspusbdevice.dll` itself and the io24 firmware image.
[PUBLICATION.md](PUBLICATION.md) records the clean-source boundary, vendor-
material policy, and reproducible release checks.
