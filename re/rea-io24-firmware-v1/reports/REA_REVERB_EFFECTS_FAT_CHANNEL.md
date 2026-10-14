# io24 reverb, Voice FX, and Fat Channel base architecture

Date: 2026-10-13

## Scope and safety

This is a static, offline continuation of the firmware analysis. All binary
inspection and decompilation was performed through REA 6.4.0 with its Ghidra
12.1.4 provider. The connected io24 was not opened. No USB transfer, reset,
DFU transition, firmware execution, or device write occurred.

The analyzed Cortex-M image is
`analysis/io24-package-arm-reset.elf`, SHA-256
`9603830a27f480011a29924d4cfef552185024a9b1f9b7dc39e82a6462320e14`.
It is the byte-preserving ELF envelope around the immutable vendor package
payload documented in `REA_DECOMPILE_ANALYSIS.md`.

## Result

The base DSP architecture is now understood at the algorithm-family and state
layout level:

- shared reverb block 202 is one stereo, delay-network reverb with independent
  wet mix, pre-delay, size/feedback, and input high-pass state;
- Voice FX block 201 selects one of six concrete processors: Transformer,
  Detuner, Vocoder, Ring Modulator, Filters, or Delay;
- Transformer owns a private instance of the same reverb core used by the
  shared reverb, rather than borrowing the shared send/return;
- each input owns a distinct Fat Channel container whose five audio stages are
  filter, gate, compressor, EQ, and limiter; `opt` controls chain metadata and
  the compressor/EQ order;
- Voice FX and shared reverb are not hidden Fat Channel stages.

This is substantially more specific than the earlier graph-level result, but
it is not original source recovery. Several real-time inner loops remain
compiler-shaped and unnamed.

## Shared reverb algorithm

This is an algorithmic reverb, not the separate Voice FX Delay presented under
model 5. Algorithmic reverbs create a dense, decaying room response by feeding
audio through several differently sized delays and diffusion stages. Here the
five feedback delays create the decay tail, the four short diffusion delays
increase echo density, and the two offset lanes create stereo decorrelation.
No single audible repeat time is exposed as the reverb algorithm's identity.

### Wire state and control mapping

`FUN_60076e70` accepts the `vrvb` state, copies exactly eleven payload words
into the block state, and calls `FUN_60076da8` to apply them. The payload is:

| Word | Meaning |
|---|---|
| 0 | enable |
| 1 | wet mix |
| 2 | pre-delay enable |
| 3 | pre-delay in seconds |
| 4 | size |
| 5 | high-pass frequency metadata |
| 6..10 | five high-pass biquad coefficients |

Evidence: handler `ev_331b5f9b75295a7d3fd21f8f024b9e46d228688ed991e094f7e3480c7839cd6f`;
state application `ev_546ad300bbcb18ebb2beb82543f067327680376a0596332ff55e036711b17a81`.

The same eleven-word body also has a firmware-native structured-state pair.
Vtable method `0x6006faa0` writes a `0x2c` length and then exports `0x2c` bytes
from block offset `0x370`; `FUN_60076edc` requires that exact length, restores
the body, and calls `FUN_60076da8`. This establishes a complete block-local
save/load interface. The decoded DSP/audio reconfiguration lifecycle instead
calls `FUN_60076e70` with `Setu`, restoring the block defaults, and the recovered
root-settings writer does not include block 202. No device-resident global
container or cold-boot invocation was recovered. The full persistence boundary
and REA evidence IDs are recorded in `REA_PRESET_EFFECT_PERSISTENCE.md`.

The constructor defaults are wet mix 0.25, pre-delay 0.25 seconds, size 0.2,
identity high-pass coefficients, and a 44.1 kHz reference clock. Evidence:
`ev_7569ea411c2bbcfcb23eebca88248407a669eb3e79277adb6167535630672570`.

### Delay network

`FUN_6007af14` constructs two mirrored lanes. Each lane contains five long
feedback-delay records, four short diffusion-delay records, a dedicated
pre-delay/history object, and aligned scratch/output buffers. Evidence:
`ev_250e1e1d042baa6a2b20e86a94edda08a1aef021319c189f76eb59f3c8339d73`.

`FUN_6007a6a8` sizes the network from a 44.1 kHz reference. The base delays are:

| Bank | Lane 0 lengths at 44.1 kHz | Lane 1 |
|---|---|---|
| long feedback bank | 1116, 1188, 1356, 1491, 1617 samples | each length +23 samples |
| short diffusion bank | 556, 441, 341, 225 samples | each length +23 samples |

Every length is rounded from `base_length * sample_rate / 44100`. Allocations
receive 32 samples of guard space and are aligned to 128 bytes. The exact table
bytes are recorded by
`ev_a56159d1ca10691e4a75138fc10734399338919a5ac55fb30406ccc891670bf5`;
the configurator is
`ev_1cc20045082cfe8ae6764aa25711ff240940ed0858ed546741e83d47c8062d4f`.

The second-lane +23 offset is explicit stereo decorrelation. Five parallel
feedback delays followed by four short diffusion stages form an algorithmic
reverberator and are consistent with a Schroeder/Freeverb-family topology; that
family name is an inference from the observed topology, not a recovered class
name. Voice FX Delay is a different processor with two time-controlled private
histories and discrete repeats.

### What the controls really do

The firmware maps size to the long-delay feedback coefficient as:

```text
feedback = 0.70 + 0.28 * size
```

It sets the four diffusion coefficients to 0.5 and installs fixed 0.4/0.6
internal damping weights. Pre-delay is converted independently to samples as
`pre_delay_seconds * sample_rate` and controls its own history length. The five
high-pass coefficients are installed in both lanes.

Consequently, the exposed Size control does not resize the base delay geometry;
it changes feedback/decay. Pre-delay is an independent parameter and should not
automatically drift with Size movement if the goal is to reproduce the native
algorithm faithfully.

The complete configurator body spans 1,772 bytes in two ranges and was read at
the instruction layer after decompilation. Evidence:
`ev_9fac76397aee876bee3cda288c5d65f585e76a2d6769687a14970512d304ed61`.

## Voice FX algorithms

Block 201 is a selectable insert. The six models share the block but not one
algorithm. Their recovered base implementations are:

| Model | Processor | Base implementation |
|---:|---|---|
| 0 | Transformer / Doubler | two tone-filter slots plus a private instance of the reverb core; width derives an internal coefficient `0.2 + 0.2 * width` |
| 1 | Detuner | pitch shifter whose signed semitone state becomes the ratio `2^(semitones/12)`; owns a resizable history and a tone biquad |
| 2 | Vocoder | 22-biquad analysis/synthesis bank; two oscillator lanes with 256-sample carrier tables; the official carrier modes are Noise, Sawtooth, and Rect |
| 3 | Ring Modulator | two 257-point sine-table oscillators with independent phase increments, optional sub-carrier, nonlinear drive `1 + 100*d`, and makeup `1/(1 + 20*d)` |
| 4 | Filters | tuned feedback comb/resonator; pitch is a delay length in samples, regeneration is feedback, damping stores complementary weights, and distortion uses the same drive/makeup form as Ring Modulator |
| 5 | Delay | two private histories sized approximately `time * fs + 2` and `1.4 * time * fs + 2`, providing the decorrelated/tapped delay core |

### Model-specific REA evidence

- Transformer state/filter dispatcher:
  `ev_3fd3f9e1427b09dc27bfc8bd8b64fa019f259301920be4022b1317dbb7bdf014`.
  It accepts `godv`, two `Bqdf` slots, and sample-rate-indexed `MBdf` tables.
- Detuner coefficient application:
  `ev_ec96511d792b3dfa51301d3c6b6684943bbdf3821169abee2b831fe38dd7c231`.
- Vocoder carrier construction and mix state:
  `ev_184d99b305fa9369279ad28099205632bb8734cef463e99e3bce8d63e2d269a7`.
- Ring Modulator oscillator and drive setup:
  `ev_867f575c77909e66b345b5bf997a6c7a28e7571d6d88f7a7365f47d9363b0419`.
- Filters resonator, damping, and drive setup:
  `ev_9335b60baaccd41c070aa13ffc7e0b551dafb7b2ef4a2b180eafcb894d017afe`.
- Delay history sizing:
  `ev_4771893ef4801715e033d9c15d4fa9cf75b4d2b6cc26b4b0f7624d8bb72f6373`.

The recovered vocoder state prepares type-dependent carrier lookup storage
twice, once per lane, and converts both tables to signed 16-bit form. The ring
modulator likewise builds two independent sine lookup tables and phase
accumulators. These are true two-lane implementations, not a single mono effect
with a post-effect stereo control.

The Delay allocation result also explains its high-rate risk: both histories
grow linearly with sample rate, with one 40% longer than the requested delay.
This supports the existing 48 kHz native ceiling but does not by itself prove
the exact cause of the observed 96 kHz reset.

## Fat Channel base structure

There are two channel-strip owners, one per physical input, at device offsets
`+0x43a0` and `+0x508c`; their stride is `0xcec`. Each owner resolves these
sub-blocks:

```text
input
  -> filt (high-pass)
  -> gate
  -> comp <-> eq   (`swapcompeq` selects their order)
  -> lim
  -> channel processing mix / bypass outside the five-stage owner
```

The owner metadata object keeps five processor pointers from `+0x40` through
`+0x50`. `FUN_6006ef44` iterates those five children, asks each for `Redu`,
concatenates their reduction values into one bounded aggregate reply, and
returns the owner's latency for `Ltcy`. This independently confirms that the
base Fat Channel has five audio processors rather than Voice FX or reverb being
embedded in the chain. Decompile evidence:
`ev_ac40b183ffcff8f4e2c927b17aef70dd981d7540b1636fdf716227e085bf98ab`.

The complete 150-byte aggregate handler was checked at the instruction layer;
its pointer walk is exactly `owner+0x40` up to, but not including,
`owner+0x54`, in four-byte steps. Evidence:
`ev_7e7577340ba413d83ea87a536caeadf1fc0f0944c7dce70d5b13564c4f3c5e17`.

The five stages accept DSP-ready state rather than human-unit parameters:

- `filt` and `eq` consume normalized biquad coefficients;
- `gate` consumes a key-filter biquad plus threshold/range/timing coefficients;
- `comp` consumes a key-filter biquad plus dynamics state and derives its
  attack, release, and knee helpers on device;
- `lim` consumes enable, inverse threshold, and release coefficient.

The compressor derivation uses:

```text
attack_step = 1 / (attack_seconds * sample_rate)
release     = exp(-2*pi / (release_seconds * sample_rate))
knee_a      = 0.5 / sqrt(knee)
knee_b      = 0.5 * sqrt(knee)
```

REA evidence:
`ev_34ce1cd38011219e758ed12305b19435fa5b0c4f07bdf565112b94b52f63725f`.

The host therefore remains responsible for converting UI units into each
block's exact coefficient blob. The firmware owns the real-time state machines,
history, metering, and stage ordering.

## Corrected and remaining boundaries

- The device-side persistence consequences are traced in
  `REA_PRESET_EFFECT_PERSISTENCE.md`: a channel `Stat` record can restore a
  compatible Voice FX model, including Transformer's private reverb core, but
  does not contain shared reverb block 202. Block 202 instead exposes its own
  `0x2c`-byte structured writer/loader pair. The recovered root writer does not
  invoke it, and DSP/audio reconfiguration actively reapplies default `Setu`
  state, so Host/phone scene state must save and replay shared reverb.

- A historical host note named `dspusbdevice.dll` address `0x1800207f0` as the
  reverb push routine. In the exact current DLL build that address is not an
  instruction boundary and has no REA xrefs. The nearby recovered function at
  `0x180020730` is a small parameter-update helper, not the full blob builder.
  The device-side `vrvb` handler and state layout above are the current
  authoritative binary evidence.
- The reverb algorithm family, buffer topology, control mapping, coefficient
  relationships, and sample-rate scaling are established. The complete
  sample-by-sample inner loop has not been lifted into clean source.
- The six Voice FX algorithm families and their configuration math are
  established. Not every optimized sample loop has been semantically renamed.
- The Fat Channel ownership, five stages, aggregate metering, coefficient
  boundary, and compressor/EQ ordering control are established. This report
  does not claim live audible acceptance from static decompilation.

## Audit verdict

The post-analysis audit found no contradiction between the reverb
configurator's complete instruction body, its decompiled allocation/control
logic, the exact delay table, and the block-202 wire handler. The Fat Channel
aggregate handler's complete instruction body agrees with its five-child
decompile. These checks are sufficient for the base-architecture claims above;
no device access is needed for this static deliverable.
