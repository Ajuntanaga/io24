# io24 firmware: REA decompile and post-analysis audit

Date: 2026-10-13

## Scope and safety

This pass is static and offline. REA 6.4.0 invoked Ghidra 12.1.4 as its decompiler provider with Eclipse Temurin JDK 21.0.12.1. No USB device was opened, no DFU transaction was attempted, no firmware was executed, and no device or system firmware was written.

The immutable source remains `originals/io24-uc472-vendor-package.bin`:

- size: 1,222,292 bytes (`0x12a694`)
- SHA-256: `790f668608448b7c9f244c360ad72e3c51f71b4e8a3d828eab0e08cd03b35de1`

Because REA rejects a headerless ARM image as an application, `tools/wrap-arm-elf.mjs` creates a byte-preserving ELF envelope for provider loading. The mapped payload hash remains the source hash above. The final envelope is `analysis/io24-package-arm-reset.elf`, SHA-256 `9603830a27f480011a29924d4cfef552185024a9b1f9b7dc39e82a6462320e14`.

## Architecture, mapping, and entry

REA observed a Cortex-M vector table at `0x60020000`:

- initial stack pointer: `0x20000600`
- reset vector: `0x60020335` (Thumb bit set)
- executable entry: `0x60020334`
- mapped image: `0x60020000` through `0x6014a693`
- language: `ARM:LE:32:Cortex`

The final REA overview reports 1,311 recovered procedures and 253 defined strings. Evidence:

- overview: `ev_b3cb54aee84ed5b3a5c122f71d1ba80872f2bdb05b698d52b4055a5a6cac9421`
- vector bytes: `ev_585cad1f3c8b526d44528997c5c2741e0583007bda6c078dcf46a9b94ebe35e2`
- measured load mapping: `ev_92a005dbc8103cbebbeba6739265cf70e0446c36fe3d3facb13a38479779ed6b`

REA's load-image command measured the complete mapped payload at the original package hash. Its format-specific independent verifier currently supports DOS only, so the ELF result is a measured mapping observation rather than REA's format-specific verification status.

## Reset and application startup

REA decompiled the reset handler at `0x60020334`. It disables interrupts, installs the `0x20000600` stack, initializes low-level control registers, copies initialized data, clears zero-initialized regions, restores interrupts, and hands off through `FUN_60084160`. Evidence: `ev_ff27bc7eb69b11bc95e8d9c586a63911da2de035b7b562dbfd2bbd9245e040e3`.

The handoff function at `0x60084160` performs runtime initialization and calls application setup functions. REA flags bad/unreachable instruction data in this mixed startup area, so its high-level pseudocode is incomplete there; the instruction listing and direct call edges remain usable. Evidence: `ev_ab19edb4906687633450d10d26f60c9d7b7078cd46aa7baeafcff528002fbb00`.

## DFU findings in the device image

REA's defined-string inventory contains the exact product identity `Revelator IO 24 DFU` at `0x60087a84`. The broader DFU/boot/flash/erase/download/reboot/update search found no other defined DFU or firmware-programming strings. Evidence: `ev_0cbaf3667eb51573f867eaccae550c78b1c331e4d35d3490cd3e0a1ae277484e`.

The application image therefore contains a DFU USB identity, but this pass did not recover a self-contained erase/program/download state machine from the application firmware. A later REA pass located and decompiled the host-side programmer in Universal Control's `dspusbdevice.dll`; see `REA_DSP_PROGRAMMER_ANALYSIS.md`. The device-image result remains:

1. The application can request a controlled system reset.
2. A mode value can influence that reset path.
3. The host-side transfer/programming controller is in `dspusbdevice.dll`; the device-side DFU recipient still appears to live in a bootloader, ROM, or another separately delivered region, while this image supplies or shares the DFU identity.

Item 3 is an inference, not proof. Packed code, indirect dispatch, or a non-string-based implementation could evade this defined-string and call-graph pass.

## Controlled reset path

REA found five references to the Cortex-M AIRCR address `0xe000ed0c`; only one recovered function writes it. Evidence: `ev_d7dca6b9befea621824577042f012d07d90821f7008cc38fc9056274c1b2215b`.

The reset function is `FUN_600646f8`, body `0x600646f8` through `0x6006472b`. Its behavior is:

- clear `0x400f8030`;
- if argument bit 0 is set, write `0x174f35ab` to `0x400f8030`;
- run two shutdown/pre-reset helpers;
- disable interrupts and issue data barriers;
- preserve AIRCR priority-group bits (`0x700`);
- write `0x05fa0004 | preserved_bits` to AIRCR at `0xe000ed0c`;
- loop indefinitely while reset takes effect.

`0x05fa0004` is the Cortex-M AIRCR key plus `SYSRESETREQ`. REA decompile evidence: `ev_d2ce60157cbec6e5ae915f3e823b729ed71df3e7bea5f7a1bb851005ea9bbbf0`.

Two callers were recovered:

- `FUN_60041490` quiesces an object, toggles a status output for a bounded period, then calls the reset function with constant `1`. It is reached by the firmware's fatal/error path. Evidence: `ev_f8db3d3895c85aeae1f2874a066b145bd1c2a3a9f6bb4bfac1bda2f4a1695e80`.
- `FUN_600584b4` notifies registered clients, waits, loads a mode value from object offset `0x164`, and passes that value to the reset function. Evidence: `ev_6cf2624dc23da30c7c8e70bd85e50bc8ba88abc8b97b2529551a5eaab4adc905`.

The mode-controlled caller is the best application-side candidate for a normal-versus-boot-mode transition. Static evidence does not yet assign a semantic name to object field `+0x164`, so it should not be called a DFU flag without live or bootloader evidence.

## Post-analysis audit

One direct audit was completed after analysis:

- REA read every instruction in `FUN_600646f8`; all 21 instructions cover the complete 52-byte function and agree with the decompiler's control flow. Evidence: `ev_3cb9c8f666e4d0da0a18af9db42ac41eb641d2b6fe47910b76a15c0d97432373`.
- REA read the complete 16-byte literal pool at `0x6006472c`: `00800f40 ab354f17 00ed00e0 0400fa05`, decoding little-endian to `0x400f8000`, `0x174f35ab`, `0xe000ed00`, and `0x05fa0004`. Evidence: `ev_b956b50190d1a6e59734b061bc7214700d3dc292e036dcae4a1141b9e8dad1f5`.
- The mapped payload digest in the provider equals the immutable source-package digest.

Verdict: the architecture, entry point, reset routine, reset constants, callers, and DFU identity are internally consistent. This report's original device-image boundary still holds, but the host-side programmer and the on-device DSP engine have since been located and decompiled with REA. Those superseding findings and their remaining limits are in `REA_DSP_PROGRAMMER_ANALYSIS.md`.

## Reproduction

Use the existing local Ghidra/JDK installation and run REA with:

```bash
export JAVA_HOME=/home/ajuntanaga/Development/Experiments/tools/jdk-21.0.12.1+1
export GHIDRA_INSTALL_DIR=/home/ajuntanaga/Development/Experiments/tools/ghidra_12.1.4_PUBLIC
export REA_GHIDRA_LANGUAGE_ID=ARM:LE:32:Cortex
export PATH="$JAVA_HOME/bin:$PATH"
```

Create the byte-preserving envelope:

```bash
node re/rea-io24-firmware-v1/tools/wrap-arm-elf.mjs \
  re/rea-io24-firmware-v1/originals/io24-uc472-vendor-package.bin \
  re/rea-io24-firmware-v1/analysis/io24-package-arm-reset.elf \
  0x60020000 0x60020335
```

The complete REA evidence cache is `analysis/io24-package-arm-reset.snapshot.json`.
