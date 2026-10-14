# io24 DSP and firmware-programmer analysis

Date: 2026-10-13

## Result

REA establishes two distinct but connected architectures:

1. The io24 application image is a Cortex-M firmware containing the device's audio processing graph, parameter dispatch, sample-rate configuration, channel-buffer routing, USB-audio and I2C/peripheral setup, and the application-side reset transition.
2. Universal Control's native `dspusbdevice.dll` contains the host-side Thesycon DFU image parser, compatibility checks, transfer state machine, progress orchestration, and error handling. The corresponding device-side flash recipient is not present as a separately recoverable image in the analyzed application package.

This materially supersedes the earlier inference that the programmer was simply absent: it is absent from the Cortex-M application image, but its host half is present in the shipped Universal Control DLL.

All binary analysis in this pass was performed through REA 6.4.0 with its Ghidra 12.1.4 provider. The plugged-in io24 was not opened because the shipped artifacts answered the architecture questions. No USB request, DFU operation, reset, firmware execution, or write occurred.

## Analyzed artifacts

- Device package: `originals/io24-uc472-vendor-package.bin`, 1,222,292 bytes, SHA-256 `790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`.
- Byte-preserving ARM envelope: `analysis/io24-package-arm-reset.elf`, SHA-256 `9603830a27f480011a29924d4cfef552185024a9b1f9b7dc39e82a6462320e14`, mapped at `0x60020000`, reset entry `0x60020334`.
- Universal Control host module: `dspusbdevice.dll`, 4,984,704 bytes, SHA-256 `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`, native x86-64 PE.

REA observed 1,311 procedures and 253 defined strings in the ARM application, and 3,009 procedures and 9,772 defined strings in the host DLL. The DLL's PE resources contain version and manifest resources only; the firmware payload is not embedded as an ordinary PE resource. Overview evidence: `ev_08caa4ac9a9b39ca5677a304e850afde76af5469078552a5c04a3734a342d2fc`.

## Host-side firmware programmer

REA's shipped-artifact string and reference analysis recovered a complete Thesycon DFU stack alongside PreSonus's update orchestrator. Identified components include `paesdk::DeviceFirmwareUpdate::DoUpgrade`, `thesycon::DfuDevice::DoDownload`, `DfuImageTlBinary::VerifyImage`, compatibility checking, target selection/unlock, and the `TLDFU_StartUpgrade`, status, and finish APIs. Evidence: `ev_85484271dc10818d0c0c407f6e7e5637bfbe2975f85b4cc8448d0bcb297ebf7a`.

### Upgrade orchestration

`FUN_1800815a0`, reached from `DeviceFirmwareUpdate::DoUpgrade`, does the following:

- enumerates DFU-mode devices and requires exactly one match;
- starts the upgrade with the loaded image handle, target, and option state;
- polls upgrade status at approximately 50 ms intervals;
- updates shared progress under a critical section;
- calls the finish path when the operation reports completion;
- returns explicit failure states rather than silently continuing.

REA trace target: `FUN_1800815a0`.

### Image validation

`FUN_1800a8ec0` requires a loaded image, locates its metadata block, and invokes the validator. `FUN_1800a76c0` scans aligned image data for a metadata structure of at least 60 bytes and checks its marker, declared size, and bounds. `FUN_1800a7a40` reads the metadata and computes a table-driven CRC-32 from `0xffffffff`; validation succeeds only when the complemented result equals the stored CRC. REA recovered a distinct CRC mismatch result (`0xee000069`) and an oversized-image failure path.

REA decompile targets: `FUN_1800a8ec0`, `FUN_1800a76c0`, and `FUN_1800a7a40`.

### Device compatibility

`FUN_1800a0b40` sends a four-byte control-IN compatibility request using the selected image target/index and requires a four-byte response. A nonzero device result is mapped into the host error namespace as `0xee000000 | (value & 0x3fff)`.

### Block transfer and DFU state machine

`FUN_18009df00` is the central download routine. Its decompile shows that it:

- caps the transfer block at `0x1000` bytes;
- allocates an aligned working buffer;
- reads consecutive image chunks and submits sequential DFU download blocks;
- polls `GETSTATUS` across download-sync/busy/idle states and honors the returned poll timeout;
- updates the transferred byte count and block number;
- uses `ABORT` on its cancellation/error route;
- submits a zero-length final download block;
- polls the manifestation states through completion, reset, or a typed error.

REA decompile target: `FUN_18009df00`.

## On-device audio DSP architecture

### One firmware image, not a second DSP blob

The application strings and graph objects include `input1HighPassFilter`, `input2HighPassFilter`, `outputDelayBus`, `outputDelay`, multiple key-filter parameters, `UsbdAudio`, `I2cMst`, and `Processing Mutex`. No defined strings identify a SHARC, SigmaDSP, XMOS, ADAU, or similar separately programmed DSP image.

REA decompiled a large processing-engine constructor, `FUN_6007d990`, which creates the processing mutex, routing and per-channel objects, filter/dynamics state, coefficient defaults, and multiple DSP virtual interfaces. The constructor is wrapped by `FUN_6007e014`, which installs its interface tables and routing-mode fields, and is instantiated once by `FUN_6005d4f0` into the global service object at `0x20216660`. Wrapper evidence: `ev_3e4e5ececaf102eb87d80825d52364ff38ad4ff3937c84e1f46e42bb65ada0e1`; global-instantiation evidence: `ev_4a75cb8f252c63fe9e87dd3fb02195b60e6b7ac4d1a7f5841302740a56a5e4c9`.

This supports a single-controller architecture: audio DSP code and state are compiled into the same Cortex-M application rather than loaded as a second firmware image.

### Parameters and graph configuration

`FUN_600629b0` registers the input processing parameters and maps `input1HighPassFilter` to the processing-state object at offset `+0x300`. `FUN_6005c190` routes input 1/input 2 high-pass state, phantom power, and gain through the parameter dispatch layer.

`FUN_600619a0` is the graph's command dispatcher. It recognizes the FourCC messages `SetP` and `GetP`, emits `Rply`, and dispatches reads/writes to parameter objects under the processing mutex.

`FUN_6005ef50` performs major DSP reconfiguration. REA recovered:

- aligned per-channel/sample-buffer allocation;
- separate 48 kHz and 96 kHz configuration paths;
- Voice FX enable/disable state (`VFxO` in the recovered FourCC ordering);
- filter, dynamics, routing, and limiter-state setup;
- coefficient/smoothing calculations using a form equivalent to `exp(-2*pi/(sample_rate*100))`;
- sample-count timing derived from the selected rate.

REA decompile target: `FUN_6005ef50`.

### Buffer processing and transport

`FUN_6005f788` is a recovered real-time buffer-routing routine. It accepts the processing object plus a buffer descriptor, selects routing behavior from object field `+0x5e54`, iterates the available input/output channel arrays for modes 2 and 3, wraps unequal channel counts with integer remainder arithmetic, and invokes the underlying sample/block primitive for each mapped channel. Its complete 256-byte body contains 99 decoded Thumb instructions. Evidence: decompile `ev_b91af9104805b55b7c80e8346d96dde903a81409d3f5fd4bcb6654446cc793b4`.

The hardware initializer `FUN_6006c2dc` configures memory-mapped audio peripherals, constructs the I2C master, sets up 64-byte `MFin` and `MFout` buffers, creates DMA/interrupt-facing components, and starts I2C at either 100 kHz or 400 kHz according to the hardware configuration. `FUN_600414d4` creates the named global, endpoint, USB-audio, and I2C synchronization objects; `FUN_60052608` creates the I2C mutex/event pair.

Together these findings establish the control/data split: USB-audio and peripheral/DMA infrastructure feed channel buffers; the Cortex-M processing service owns the parameterized filter/dynamics/routing graph and applies it to those buffers.

## Corrected false lead

The large objects named `Nimbus16` and `Nimbus24` are not DSP firmware. REA initially exposed the names adjacent to large data objects, but `FUN_60042c54` validates `BM` bitmap headers and pixel depths, while `FUN_60043454` composes named bitmap/font assets. Nimbus is UI font/bitmap data.

## Post-analysis audit

One direct audit pass checked the two load-bearing implementations at the instruction layer:

- REA read all 459 instructions in host routine `FUN_18009df00`, covering the single contiguous 1,996-byte body `0x18009df00` through `0x18009e6cb`. The instruction stream independently confirms the `0x1000` cap, repeated block/status loops, state comparisons, terminal-block path, cancellation/abort path, typed errors, and cleanup. Evidence: `ev_65103c183879b38924f5d80ff813bf28f68974056a83ef8063e842a98554ef6d`.
- REA read all 99 instructions in device routine `FUN_6005f788`, covering the single contiguous 256-byte body `0x6005f788` through `0x6005f887`. The instruction stream independently confirms the routing-mode comparisons, channel-array loops, modulo-style index wrapping, and repeated calls to the buffer primitive. Evidence: `ev_2922749d2cac4d1af6872190deb2d93735715278caa732cd6306fe98f8971714`.

Audit verdict: the decompiled firmware-programming and DSP-buffer claims agree with their complete instruction bodies. No contradictory static evidence was found.

## What is and is not fully understood

The architecture is now understood well enough to locate the responsibilities, follow the update flow, reproduce the major state machines, and connect named controls to the on-device DSP service. It is not a source-level reconstruction of every algorithm:

The reverb network, all six Voice FX algorithm families, and the five-stage
Fat Channel base structure have since been decoded in
`REA_REVERB_EFFECTS_FAT_CHANNEL.md`. That report supersedes the broader
algorithm-level limits below where it has exact evidence, while retaining the
source-reconstruction and live-audibility boundaries.

The firmware-native `MemP/Stat` write, stored-record read, conditional recall,
and Voice FX state-application path is documented separately in
`REA_PRESET_EFFECT_PERSISTENCE.md`. It also records the persistence boundary
between Transformer's private reverb core and independent shared reverb block
202.

- the device-side DFU bootloader/ROM implementation has not been acquired;
- several optimized or indirect DSP primitives retain generated names, and the exact source classes/types are unavailable;
- every EQ, compressor, reverb, and limiter coefficient routine has not been semantically renamed or converted into maintainable source;
- static decompiler pseudocode is evidence about shipped machine code, not the original source and not proof of live audible behavior.

Those limits do not change the main architecture verdict, and none requires reading the connected device for this static deliverable.
