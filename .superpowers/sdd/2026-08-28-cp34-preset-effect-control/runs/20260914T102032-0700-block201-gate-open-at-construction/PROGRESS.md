# Block 201's gate is satisfied at construction

Status: `GATE_OPEN_AFTER_CONSTRUCTION_SILENCE_UNEXPLAINED`

## Correction this forces

The controlling reading has been that block 201's handler is shut and that only
the native `Stat` structured-state load opens it, so a direct `SetP | 201`
write is discarded. That reading is too strong, and the part of it that
attributes the silence to a closed gate is not supported.

**The block-201 constructor satisfies all three gate conditions itself.**

## What was verified, byte-exact

Firmware `io24_fw.bin`, 1,104,448 bytes, SHA-256
`65ad2b65bcef932b41e748bfab87f62a9e529c17cceaa0a6a7679e387952eb1a`.
Every listing below was disassembled from a known function entry, not swept.

Gate handler `0x50af8`, reproducing 13c exactly:

```
0x50b06  ldrb.w r3, [r4, #0x44]   ; FLAG A
0x50b0a  cbz    r3, 0x50b22
0x50b0c  ldrb.w r3, [r4, #0x39]   ; FLAG B
0x50b10  cbz    r3, 0x50b22
0x50b12  ldr    r3, [r4, #0x40]   ; FLAG C
0x50b14  cbnz   r3, 0x50b22
0x50b16  ldr    r3, [r4]          ; all three -> tail-call vtable +0x34
```

Stat loader `0x5545c`, reproducing the 2026-08-31 note exactly:

```
0x554ba  str  r5, [r6, #0x40]     ; r5 = 0  -> FLAG C
0x554bc  strh r3, [r6, #0x38]     ; r3 = 0x101 -> byte +0x39 = 1 -> FLAG B
0x554c2  bl   0x55388             ; -> FLAG A
```

Model selector `0x55388`:

```
0x5538a  subs r5, r1, #0          ; model
0x5538c  blt  0x553c4             ; model < 0 -> return, no flag set
0x5539a  bne  0x553cc             ; delegate mismatch -> blx r3, then fall through
0x5539e  cmp  r0(6), r5
0x553a0  ble  0x553c4             ; model >= 6 -> return, no flag set
0x553a8  strb.w r3, [r4, #0x44]   ; r3 = 1 -> FLAG A
```

The `bne` path is not an exit: `0x553cc` calls the delegate and branches back to
`0x5539e`, so any model in 0..5 reaches the `+0x44` store.

**Block-201 constructor `0x591bc`:**

```
0x591e6  movs   r5, #0
0x591ec  strh   r0, [r4, #0x38]   ; r0 = 0x101 -> byte +0x39 = 1   FLAG B
0x59202  strb.w r5, [r4, #0x44]   ; +0x44 = 0
0x59214  strd   r5, r5, [r4, #0x3c] ; +0x3c = 0 and +0x40 = 0      FLAG C
0x59240  mov    r1, r5            ; model = 0
0x59244  mov    r0, r4
0x59248  bl     0x55388           ; model 0 is valid -> +0x44 = 1  FLAG A
```

`r5` is callee-saved and survives the intervening `bl 0x10d7e0`, so the model
argument really is 0.

## Consequence

At the end of construction, `+0x44 = 1`, `+0x39 = 1`, `+0x40 = 0`. The gate is
**open from device boot**, before any host action. A shut gate is therefore not
a sufficient explanation for block-201 writes producing no audio, and the
2026-08-31 statement that the native `Stat` load is what supplies the three
conditions should be read as "also supplies", not "uniquely supplies".

## What remains unexplained

Why direct block-201 writes were inaudible in 12S and in the 2026-09-14 live
runs. The candidates are unchanged in kind but the gate is no longer the
leading one: something later clearing a flag, the `[+0x14]` delegate branch, or
13a's separate point that the FX slot is a chain member which must be
*installed* in the signal path.

## Limits, stated plainly

This establishes the construction path only. It does **not** establish that
nothing later changes those fields. A whole-image scan for stores at
displacement `0x44` returns 378 sites, `0x40` returns 259 and `0x38` returns
205, none of which can be attributed to the block-201 object without type
information, and a 2-byte linear Thumb sweep decodes garbage besides. No
exclusivity claim is made here.

## Boundary

Offline only. No device, audio, Wine, network, install or firmware action, and
nothing was written to the unit.
