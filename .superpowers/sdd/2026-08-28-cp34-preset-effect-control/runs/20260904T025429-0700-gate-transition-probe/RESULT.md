# CP34 linked gate-transition result

Timestamp: 2026-09-04T03:10:45-07:00

Result: `NO_REPEAT_DOWNSTREAM_GATE_OFF`

The one authorized trial completed once against serial `AB7C22200355`. It
captured 14.0 seconds of six-channel S32_LE audio at 48 kHz without playback,
gain, routing, output, or preset-content changes. The raw capture is 16,128,044
bytes with SHA-256
`9f2307056e44b909668deb4226ec2b191d1e23ade12d641996fc9669e4beafda`.

The exact state sequence was Channel 2 slot `3 -> 2`, stereo link on, Channel 2
slot `2 -> 3`, factory gate on, factory gate off, the exact factory gate-on
inverse sent, then stereo link off. The final readable state was flags `0x1a1`,
Channel 1 slot 0 disabled, Channel 2 slot 3 enabled, and Channel 1's readable
guard unchanged. Both independent postflight `JaSt` replies were 2040 bytes and
had identical SHA-256
`408195df650fbe897953f0cf7983e9ee6f20b791e252d9dfaaca3ff2d3dd448f`.
The gate itself is not readable, so its restoration is recorded only as the
exact factory restoration write sent—not as readback proof.

All four captured monitor channels changed by approximately 48.142 dB between
the factory-gate-on and gate-off windows. This proves that the captured taps
were downstream of, and observable to, the gate. During the gate-off window,
each monitor channel tracked Input 2 with direct coefficient approximately
`0.70794561` and model correlation approximately `0.99999542`. The fitted 150
ms coefficient divided by direct was only approximately `0.00001426`, far
below the predeclared `0.05` repeat threshold.

Therefore the linked Channel-2 slot-3 path did not produce the factory Slap
Echo 150 ms repeat even when the same factory record's gate was opened. This is
strong audible-path waveform evidence against active Voice FX in the recalled
linked path. It does not establish whether the record is physically resident,
whether the device parser accepted all record semantics, or whether another
unobserved activation condition exists. Firmware emission, staging, flash,
reset, DFU, install, Wine, network, and any further hardware action remain out
of scope.
