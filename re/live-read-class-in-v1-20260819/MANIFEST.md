# io24 class-interface-IN v1 live-read

## Authorization and boundary

The user explicitly authorized exactly one non-mutating class-interface-IN
live-read on 2026-08-19. The command was launched once:

    ./tests/uc_wine_sandbox.sh live-read \
      /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819

The user then said pause while the command was still in flight. No second
command was launched. The existing command later completed, and this manifest
was recovered from its unchanged output on 2026-08-21. The one-run
authorization is consumed. Nothing here authorizes a retry, a USB write,
interface claim or detach, alternate-setting selection, timeout change, full
Universal Control, Voice FX, or protected-prefix access.

## Inputs and containment

The run used the CP8-staged class-interface-IN overlay. The current staged
triplet still matches CP8:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  x86_64-unix/wineusb.sys.so
    d5cbdf21f773488523c16bec90af8d83f9c7a9464afc39dceefdea16e399edbc  x86_64-unix/wineusb.so

The current harness still matches CP8 at SHA-256
4706b84e5ea5daff2b274af28f6faf051fc66797cb5d569ecc9237ea4effaf7c.
The sealed CP8 SHA256SUMS file still hashes to
4e9e14779bf20a8a8f76a00a4ebb261268764624b6f8a135198832275e6270c1,
and every entry verifies.

The launch console records:

- unit io24-wine-live-read-854561.service;
- invocation cb532c4af3a04271bf4c2c4ce92affb3;
- one exact io24 node and no audio, GPU, host home, session bus, or external
  network exposed inside containment;
- native libusb debug level 4;
- service installer status 124 and loader diagnostic status 255;
- registered PreSonus Hardware Access Service at RUNNING after one readiness
  check;
- no UCNET DA announcement within 8 seconds;
- final status 1 after 38.982 seconds, 7.985 seconds CPU, 105.3 MiB peak
  memory, and zero swap.

RUNNING is service-state evidence only. No synchronize.json exists.

## USB evidence

The unchanged active capture is 149,021 bytes and 1,457 lines:

    c05811fb8f488a3ae28574792e3951f6e4cf91fedc7a88824e4eb9af774978c5  live-service-usb.txt

It contains one contained libusb process and:

- 96 asynchronous control-IN submissions;
- 94 status-zero callbacks;
- two immediate submission errors;
- no control-OUT, bulk, interrupt, or immediate error other than the two
  exact class-interface requests.

Both rejected submissions used the accepted CP8 setup packet:

    a1 02 00 01 00 05 00 01

The correlated evidence appears twice:

    S Ci ... a1020001 00050001
    libusb: error [submit_control_transfer] submiturb failed, errno=16
    E Ci ... -1 0
    wineusb: Failed to submit io24 class-interface IN transfer: Input/Output Error.

errno 16 is EBUSY. Both failures were immediate, before the request could
reach the device, so this run captured no class response and does not validate
CP8 completion semantics against hardware.

The driver later reached the existing select-interface path twice. That path
remained fail-closed with STATUS_NOT_IMPLEMENTED. Two 120-byte error records
follow the class failures, and two 92-byte records follow select-interface,
matching the previously localized Audio Controller initialization and Set
Configuration failure paths.

## Confirmed Linux arbitration blocker

The setup byte a1 marks a class, device-to-host request whose recipient is an
interface. For interface-recipient controls, Linux usbfs masks wIndex to its
low byte. Here wIndex is 0x0500, so the target is interface 0 and the high byte
is entity or clock-source ID 5. It is not a request to interface 5.

Linux usbfs check_ctrlrecip calls checkintf for that low-byte interface. If
usbfs has not claimed it, checkintf attempts an implicit claim. The USB core
returns EBUSY when another driver already owns the interface:

- https://github.com/torvalds/linux/blob/master/drivers/usb/core/devio.c
- https://github.com/torvalds/linux/blob/master/drivers/usb/core/driver.c

At launch and at delayed postflight, interface 0 was owned by snd-usb-audio.
The exact setup packet, two errno-16 results, and current ownership therefore
converge on a usbfs versus snd-usb-audio ownership conflict. The staged
WineUSB implementation itself reached the intended libusb submit call.

ALSA's current cached state lists the io24 rates as 44,100, 48,000, 88,200,
and 96,000 Hz. That is useful corroboration that snd-usb-audio already learned
clock/rate information, but it is not the exact 50-byte-or-other UAC2 RANGE
response. Do not synthesize a Wine response from the rate list alone.

An offline source-and-evidence search completed on 2026-08-21. Linux
snd-usb-audio fetches the UAC2 RANGE payload, parses its subranges into a rate
table, and frees the raw payload
(https://github.com/torvalds/linux/blob/master/sound/usb/format.c). No exact
response was found in the retained project captures or current procfs ALSA
state. The cached rates therefore cannot recover the original byte sequence.

## Delayed postflight

The original turn stopped before immediate postflight. Fresh checks on
2026-08-21 found:

- no Wine, wineserver, Xvfb, PreSonus, or io24 process surviving;
- the transient unit collected and no longer loaded;
- exactly one 194f:0422, serial AB7C22200355, currently re-enumerated at
  sysfs 3-1 and /dev/bus/usb/003/003, configuration 1, 480 Mbit/s;
- interfaces 0 through 4 still owned by snd-usb-audio and interfaces 5 and 6
  still unclaimed;
- protected prefix inode 3427833 and timestamp
  2026-08-12 00:31:35.825186221 -0700, unchanged from every prior checkpoint;
- CP8 hashes and the staged overlay triplet still valid.

Because this verification occurred after a pause and a later resume, it proves
current clean state, not uninterrupted interface ownership during the entire
gap. The completed transient unit, inner cleanup trap, zero surviving
processes, and unchanged protected prefix support safe cleanup.

## Sealed evidence

Exact run and delayed-postflight evidence verifies under:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819/out/checkpoints/live-read-class-in-v1-20260819T233401PDT/

Its relative SHA256SUMS file hashes to
8e7d4ae8dafb22c650abce9abe05a0fdcc18991b6682fcce805087c7f03c0287.

## Next gate

Do not retry the run or remove the active capture. A successful on-device
class-interface read now requires crossing the interface-0 ownership boundary.
Detaching or claiming interface 0 could disrupt the working ALSA device and is
not authorized.

The retained-evidence and current procfs search is exhausted without the exact
UAC2 RANGE response. The safest next candidate is a separately authorized,
passive usbmon capture while a user-controlled device reconnect causes
snd-usb-audio to perform its normal enumeration. Do not reconnect the device,
start a live capture, detach or claim interface 0, or synthesize response bytes
without a new explicit authorization.
