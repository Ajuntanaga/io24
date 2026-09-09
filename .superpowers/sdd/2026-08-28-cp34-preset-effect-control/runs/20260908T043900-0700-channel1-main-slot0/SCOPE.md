# Channel 1 MAIN slot-0 scope

The user explicitly authorized replacing the first Channel-1 device slot with
the new preset `MAIN`, selecting and enabling it, turning on a touch-sensitive
compressor and a -0.6 dBFS limiter, applying a Strandberg Boden 8 EQ starting
curve, and bypassing the HPF.

This stage may write only physical Channel 1 and global device slot 0. It must
preserve exposed Channel-2 gain, selector, enable state, and processing
assignment; preserve both input gains and stereo-link-off; avoid the global
preset-mode setter; and avoid changing Voice FX assignment. No audio capture,
Wine, firmware, reset, DFU, install, publication, network, or Obsidian write is
included.

The device-slot transport has no decoded stored-body readback. A successful
write report therefore remains `physical_commit=UNPROVED`; durability and
audibility require separate observation.
