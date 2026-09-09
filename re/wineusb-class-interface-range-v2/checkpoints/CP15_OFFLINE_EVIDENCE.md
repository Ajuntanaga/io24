# CP15 — class-IN evidence resolved offline; pipe path becomes primary

Reached at 2026-08-21T04:57:00-07:00 without a new live run, device request,
interface claim or detach, alternate-setting change, USB write, Universal
Control launch, Voice FX action, or protected-prefix access.

## Restored and refreshed state

The current handoff was recovered at CP14 rather than the older CP8 memory
snapshot. All 16 CP14 project-chain entries and all 47 retained runtime-evidence
entries reverified. A fresh host-side postflight found no candidate Wine,
Universal Control, Xvfb, Bubblewrap, or io24 process, and a direct user-systemd
query returned no matching `io24-wine-*` unit. The protected prefix retained
inode 3427833 and timestamp `2026-08-12 00:31:35.825186221 -0700`.

The same owned io24 serial `AB7C22200355` was present at sysfs `3-1`, now
re-enumerated at `/dev/bus/usb/003/002`. That reconnection is state evidence,
not authorization. Interfaces 0 through 4 remained bound to
`snd-usb-audio`; interfaces 5 and 6 remained unclaimed. Every interface was
passively observed at alternate setting 0.

## Reproducible class-IN evidence

A new test-first offline analyzer pairs usbmon control submissions with their
completions, matches the three exact CP14 tuples, and decodes UAC2 input/output
terminal `bmControls` from the complete configuration descriptor. Its
synthetic contract first failed because the analyzer did not exist, then
passed after the minimal implementation.

Against the sealed reconnect pcap
`194a4b2619e0bddcdeef2108b0969cf13c029b3d2516309123c6567437b2922d`,
the analyzer found:

- 14 status-zero `GET_CUR` responses for clock source 5 sampling frequency;
- 11 responses containing `80 bb 00 00` (48,000 Hz) and three containing
  `00 77 01 00` (96,000 Hz);
- no request or response for terminal 2 or terminal 3 latency `GET_CUR`;
- one complete io24 UAC2 configuration for the target device instance; and
- input/output terminal entities 1 through 4 all advertising
  `bmControls=0x0000`.

Latency is selector 7, so its two-bit control field is bits 12-13. For
terminal entities 2 and 3 that field is `00`: the control is not present.
The two observed clock values also establish that sampling-frequency `CUR`
is live state, not a constant response.

Therefore the evidence does not support synthesizing any of the three CP14
responses. A fixed clock value would falsify device state, and inventing a
latency value would contradict the device's own UAC2 descriptors. The current
fail-closed treatment is conservative for both terminal-latency tuples.

## CP14 runtime-path reclassification

The three class-IN rejects are newly visible operations, but the retained log
shows that PaeDSPUSB continues beyond all three in each device cycle into
registry, pipe, and streaming setup. They are not demonstrated fatal
boundaries.

The four `Failed to clear halt: Entity not found` lines are also not
WineUSB-status failures. In the exact source used for CP14,
`URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL` calls `libusb_clear_halt`, logs
an error if it fails, and then returns `STATUS_SUCCESS` unconditionally.

The stronger unresolved boundary is the pipe/streaming path:

- the live capture contains no bulk or interrupt submission;
- the log contains eight `MmMapLockedPagesSpecifyCache` stub calls and eight
  `KeInsertQueueDpc` stub calls;
- Wine's mapping stub returns `NULL`, while its DPC stub returns `TRUE`
  without invoking the deferred routine;
- WineUSB `SELECT_CONFIGURATION` initializes pipe handles only for the first
  embedded interface record; and
- the io24 descriptor places bulk endpoints `0x81` and `0x01` on interface 5
  alternate setting 1, while current passive sysfs state is interface 5
  alternate setting 0 with no active endpoints.

These facts make pipe topology, MDL mapping, and DPC dispatch higher-value
offline targets than fabricated class-IN replies. The current evidence does
not yet separate their individual causal contributions, and it does not prove
which one is the first fatal condition.

## Gate

CP15 records evidence and analysis only. No WineUSB behavior or staged binary
was changed. Safe next work is an offline, contract-tested observation patch
that records the full `SELECT_CONFIGURATION` interface list, encoded pipe
handles, bulk/interrupt request metadata, and MDL mapping result without
changing USB behavior.

The CP14 one-run authorization remains consumed. Any future device query,
live-read, claim/detach, alternate-setting change, class OUT, USB write, full
Universal Control, Voice FX, or protected-prefix access still requires new
explicit authorization and a fresh complete preflight.

