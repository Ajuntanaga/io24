# Host bus source and balance scope

Date: 2026-09-09
Status: offline implementation in progress

Implement the approved Host-only bus-source design:

- expose passive, independently routable `io24 Host Mix A` and
  `io24 Host Mix B` PipeWire sources from exact USB capture pairs 3-4 and 5-6;
- keep the aligned Main balance control disabled because a complete Main bus is
  not exposed by USB capture;
- replace the physical-input pan monitor, activation control, and automatic
  capture-to-playback route;
- migrate Host snapshot `pan` version 1 to neutral version 2 bus balances; and
- keep all implementation and validation hardware-free.

Claude independently agreed with the architecture against the exact 53-file
snapshot created `2026-09-09T10:33:34-07:00`. It required carrying
`stream.dont-remix` on both PipeWire sides and using two independent chain
owners. No further design review is required unless implementation exposes a
concrete contradiction.

This scope does not authorize a Host or PipeWire launch, USB/device/audio
access, Wine, firmware, installation, publication, Obsidian mutation, or an
expanded external disclosure. Live endpoint visibility, routing, sound,
latency, and visual acceptance remain separate gates.
