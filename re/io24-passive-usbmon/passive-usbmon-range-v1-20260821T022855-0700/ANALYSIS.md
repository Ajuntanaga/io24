# Passive usbmon reconnect window v1 — no reconnect observed

## Authorization and scope

The user explicitly authorized the previously proposed passive usbmon capture
during a user-controlled reconnect. The wrapper captured only control URBs on
bus 3 with a 512-byte snap length. It did not open the io24 device node,
detach or claim an interface, write USB or sysfs state, start Universal
Control, or touch the protected Wine prefix.

An initial launch at 02:26 PDT failed before capture readiness because the
local tcpdump AppArmor profile denied pcap creation under hidden `.cache`.
That attempt produced no pcap, restored the usbmon module, and did not ask for
a reconnect. The corrected wrapper moved only the output location to this
non-hidden project evidence directory and passed its offline plan and parser
contract before relaunch.

## Bounded live result

The corrected capture reported ready at 2026-08-21 02:28:55 PDT and stopped at
02:30:55 PDT. No disconnect or reconnect was detected during the 120-second
window. tcpdump captured 18 control-URB events, received 18 through the
filter, and reported zero kernel drops.

The exact io24 UAC2 RANGE extractor found:

    target_request_count=0
    full_response_count=0

Therefore this capture contains no Clock Source Sampling Frequency RANGE
request or response. It is evidence that the passive pipeline reached
readiness and stopped cleanly, not evidence about the device's RANGE bytes.

## Postflight

- The target remained at sysfs `3-1`, bus 3 device 3, serial
  `AB7C22200355`.
- Interfaces 0 through 4 remained bound to `snd-usb-audio`; interfaces 5 and
  6 remained unclaimed.
- The usbmon module was absent again after the wrapper restored its prior
  state.
- No tcpdump, udev monitor, Wine, UC, Xvfb, or io24 process remained.
- The protected prefix retained inode 3427833 and timestamp
  `2026-08-12 00:31:35.825186221 -0700`.

The pcap SHA-256 is
`70f9b4db815d48a344d2da943a0049485b779a8333232a6426c31b31fd2c17d4`.
The wrapper-generated `SHA256SUMS` hashes to
`0ab3f30471ac8a94ae46c22247705e3dfb1c76fde8dc849b00bfc5bebdc03f5e`.

## Gate

Do not infer a RANGE response or retry automatically. A new bounded capture
window requires the user to be physically ready and explicitly say to launch
it. The same passive-only boundaries remain in force.
