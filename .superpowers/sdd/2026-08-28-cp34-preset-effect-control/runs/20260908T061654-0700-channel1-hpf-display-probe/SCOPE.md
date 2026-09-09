# Channel-1 HPF physical-display correlation probe

Authorized by the user on 2026-09-08 after the exact probe boundary was stated.

Allowed live actions are limited to the exact io24 serial `AB7C22200355`,
firmware `0x0128`, readable pre/post state, and human-paced Channel-1 digital
HPF writes at 40, 80, 160, and 55 Hz, followed by an exact 24 Hz bypass write
in cleanup. Execution must refuse at or below 10% battery, unless MAIN is
enabled on Channel-1 slot 0 at 30 dB with stereo link off, or if identity does
not match. Channel-2 readable state must remain unchanged.

No preset save, slot select, preset enable/disable, preset-mode, preamp HPF,
phantom, gain, routing, audio, firmware, reset, DFU, Wine, Host GUI, install,
network publication, Git, or Obsidian action is authorized by this probe.

The digital HPF has no protocol readback. A cleanup result can prove only that
the exact 24 Hz bypass command was sent; physical display observations come
from the user and must be recorded as such.
