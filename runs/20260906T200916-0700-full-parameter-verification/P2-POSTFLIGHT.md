# P2 aborted batch postflight

Status: `ABORTED_BEFORE_AUDIO_READABLE_STATE_RESTORED`

The P2 runner began at 21 percent battery. Its initial readable state differed
from the earlier P0 snapshot before any runner write: Channel 1 was already on
slot 1 rather than slot 0, and headphone volume was already `0.5541094542`
rather than `0.5841094255`. Those external/front-panel changes are not
attributed to the runner and the immediate pre-write state is the restoration
reference.

The runner emitted exactly two successful 40-byte `Pari/7` SetP frames, muting
Channel 1 and Channel 2. The next intended write, Channel-2 gain zero, timed out.
Consequently:

- no block-100 mixer write was attempted;
- no playback or capture endpoint was opened;
- no stimulus was played;
- no preset slot body was written;
- no phantom, firmware, Wine, DFU, reset, or network action occurred.

The generic cleanup reopen also timed out, leaving the readable mute bits at
`0x199` until bounded recovery. The recovery sequence observed Channel 2
already off (`0x189`), sent one exact-length Channel-1 mute-off frame, and its
immediate JaSt reply was short. A separate serial-pinned two-read postflight
then returned identical state twice:

- battery: 19 percent, discharging;
- flags: `0x0181` (both input mutes off, link off, both presets enabled);
- Channel 1 slot: 1;
- Channel 2 slot: 2;
- reply SHA-256:
  `37c250b0f81dd79ea7624aca643b140f1a86900e434aba4d496d555183e42202`.

Thus all readable state changed by this attempt is restored. The P2 calibration
itself remains unrun. `P2-REPORT.json` and `MUTE-RECOVERY.json` retain the raw
failed observations and must not be rewritten into successes.

Per the predeclared campaign gate, no further live write follows this USB
timeout in the same batch. The next live attempt requires a new battery and
ownership preflight plus a transport revision that tolerates fragmented JaSt
replies and spaces or isolates successive SetP writes.

The kernel journal for 20:14-20:22 contains no USB reset, disconnect,
enumeration, ALSA, or xHCI fault for the io24. The timeout was confined to the
userspace endpoint transaction. Review of the runner found a concrete cadence
difference: it slept 250 ms after SetP, whereas the established Host services
EP_IN with a 400 ms read interval after every SetP. The runner now preserves
that service/spacing while still raising on a write error. The recovery reader
now assembles fragmented JaSt frames rather than requiring one 2048-byte read.
Eleven focused hardware-free contracts pass after those changes.
