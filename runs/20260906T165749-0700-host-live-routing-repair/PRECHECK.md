# Authorized live Host routing repair

Timestamp: 2026-09-06T16:57:49-07:00

- Scope: preserve and forget stale Host cache; launch repaired Linux Host; establish Channel 2 to Main at unity; enable a deliberately high shared reverb with an audible Main FX return; target Voice FX to Channel 2; human listening only.
- Excluded: device-resident slot record write, firmware, DFU/reset, Wine, network, and audio capture.
- Battery: 81 percent, discharging; above the mandatory 10 percent stop floor.
- USB identity: 194f:0422, serial AB7C22200355, bcdDevice 1.28 (0x0128).
- Existing Host process: none.
- Original cache: 63 entries; SHA-256 f25be20f2b56a41bab5bfacec62cb3a231f0437eb07942a0707b088c35106cff.
- The cache is preserved in SHADOW-BEFORE.json and must not be reapplied because it explicitly unassigns Channel 2 from Main and mutes/unassigns the Main FX return.

## Settled cache

The first cache read was transient because an older Host process was still alive outside the terminal sandbox. It is retained as historical evidence, not claimed byte-identical to the final state. PID 909292 was identity-checked as the project io24gtk.py and terminated gracefully. Its final flushed cache is preserved semantically in SHADOW-FINAL-FLUSH.json; the source raw SHA-256 after exit was ba0dca7302597a87b059bb846c512443aec1bbe5e04ca00b3c9649498605f7d1.
