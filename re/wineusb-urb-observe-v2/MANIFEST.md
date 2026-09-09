# WineUSB URB observation patch v2

Observation-only instrumentation built, independently reproduced, hash-pinned,
and staged offline on 2026-08-19 PDT after the authorized v6 capture proved
descriptor completion and exposed unsupported WineUSB URB functions `0x1b`
and `0x01`.

## Scope

`../wine-11.15-wineusb-urb-observe-v2.patch` adds diagnostic cases for:

- `URB_FUNCTION_CLASS_INTERFACE`: header length/status, transfer flags and
  length, request-type reserved bits, request, value, and index;
- `URB_FUNCTION_SELECT_INTERFACE`: header length/status, configuration handle,
  interface structure length, interface number, alternate setting, class,
  subclass, protocol, and pipe count.

Each case deliberately falls through to the existing final
`STATUS_NOT_IMPLEMENTED` return. It does not call the Unix libusb layer, copy
or print a transfer buffer, claim/detach an interface, select an alternate
setting, or change completion semantics. Its purpose is to identify the exact
next runtime request without guessing from static driver call sites.

## Source provenance

- retained base: Wine 11.15 with the already tested USB-DI-v1 patch;
- base `dlls/wineusb.sys/wineusb.c` SHA-256:
  `dda5adb9b35a9128b74ae4d1dff7da078d55ce61d8b0abe5e75f80d7aab0427b`;
- base `dlls/wineusb.sys/unixlib.c` SHA-256:
  `639d1708593aceb60a7c74c39521fb3b2ecc6f88ee0eb205be2a70014e40add5`;
- patch SHA-256:
  `ad260f9ab4a1bc138d8ee3fdd7ec3157e0caf8d6a67b490be4bd815092fa5e64`.

The patch passed this exact applicability check without offset or fuzz in two
independent clean source extractions:

```bash
patch --dry-run --fuzz=0 -p1 \
  < re/wine-11.15-wineusb-urb-observe-v2.patch
```

The exact signed Wine 11.15 source archive and locally extracted m4, flex,
bison, and libusb development packages are recorded in
`checkpoints/CP0_INPUTS.md`. No package was installed on the host. Both builds
used an empty `/sys`, no USB nodes or udev, no external network, no host home,
and bounded single-job compilation. Full containment and configure evidence is
in `checkpoints/CP1_BUILD.md`.

## Reproducible artifacts

Two independent source extractions, patch applications, configurations, and
builds produced byte-identical logs and artifacts:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
e5d4d22ec48ac4321627b30fb014133193d7d77bff3f296e867c1cafe7e07520  x86_64-unix/wineusb.sys.so
03a4c63ec669bf4f05789dfffd42c55e10d9e0ef990a1cc0622c1a0ab7812826  x86_64-unix/wineusb.so
```

The builtin and Unix library have ELF build IDs
`ec6ff07331507ab0cdb34f2134cc8e25f9e529d1` and
`72fc32d7eff9270708f09965cd07d0498018d77d`. The fake PE remains identical to
USB-DI v1 because the observation logic resides in the paired builtin.

The original and independently reconstructed pairs passed both the compiled
USB-DI contract and the observation source/binary contract in USB-hidden
namespaces. The latter rejects libusb submission, buffer copying, success
semantics, or any departure from the common `STATUS_NOT_IMPLEMENTED` return.
Details and evidence hashes are in
`checkpoints/CP2_REPRO_AND_CONTRACTS.md`.

## Offline staging and driver-load gate

The three exact artifacts above are staged in this versioned directory. The
disposable harness pins all three hashes and binds them read-only only for
`driver-load` or a separately authorized `live-read`. The harness SHA-256 is
`d0efc42a017bde60763976d5fa0985253b4acb19c6b8fe963244ea14caaf20d0`.

To protect the sealed v6 sandbox and capture, offline driver validation ran in
the separate clone:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.observe-v2-20260819
```

Transient unit `io24-wine-driver-load-599712.service`, invocation
`03b94be02d374ab0b7b7bc08bcd6d385`, completed with status 0 in 17.594
seconds, 3.326 seconds CPU, 114.9 MiB peak memory, and zero swap. Its namespace
reported no host home, hardware, bus, or network. The exact NT registry probe,
corrected Windows 7 NT DDI path, and SSE2 path passed; PaeDSPUSB start and query
both returned 0, and the query reported `RUNNING` before cleanup unloaded it.

WineUSB loaded as the pinned builtin. No `IO24_OBSERVE` marker occurred, as
expected with USB and sysfs absent; this validates the overlay load path, not a
device request. The transient unit was collected, no Wine/Xvfb/PreSonus process
survived, the io24 remained disconnected, and the protected Wine prefix was
unchanged. The sealed v6 sandbox's capture and `system.reg` also retained their
prior hashes and timestamps.

Exact driver-load logs, harness, contracts, and overlay bytes verify under:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.observe-v2-20260819/out/checkpoints/driver-load-observe-v2-20260819T192259PDT/
```

Its `SHA256SUMS` file has SHA-256
`4fbaa428e453c34757ce40c129b5e38103ad9f96799ad16c9fe40e3d0544aaad`.

## Prior live gate (consumed)

The offline work is complete and stopped at the live boundary. The device is
needed only for a future one-run trace, not for the completed build, contracts,
staging, or driver-load validation. Connecting it does not authorize a run.

A future trace requires a fresh full preflight and explicit one-run
authorization. Semantic support for either URB, any device write,
alternate-setting operation, interface claim/detach, full Universal Control,
Voice FX, and the protected Wine prefix remain out of scope.

## Authorized one-run observation

The user subsequently authorized one bounded live-read and reported the io24
connected. Fresh preflight found exactly one `194f:0422`, serial
`AB7C22200355`, at sysfs `1-2` and `/dev/bus/usb/001/005`, configuration 1,
480 Mbit/s. Interfaces 0-4 remained with `snd-usb-audio`; 5-6 remained
unclaimed. Exact artifacts, the inherited capture, sealed v6 sandbox,
protected prefix, process state, capacity, and a separate non-opening isolation
audit all passed before launch.

The observation overlay ran exactly once as
`io24-wine-live-read-625692.service`, invocation
`2c5ad2102bd24c11bc1e76ed60b844f6`, and was not retried. The registered
service reached `RUNNING`, but no UCNET `DA` arrived, so the bounded harness
exited status 1 after 30.151 seconds.

The overlay twice observed the same fail-closed class-interface tuple:

```text
flags=0x3 length=256 reserved=0 request=0x02 value=0x0100 index=0x0500
```

It returned `STATUS_NOT_IMPLEMENTED`; the class request was not submitted.
The tuple, the io24's returned UAC2 AudioControl descriptor, and upstream UAC2
definitions identify a high-confidence Clock Source Sampling Frequency `RANGE`
read: `bmRequestType=0xa1`, `bRequest=0x02`, `wValue=0x0100`,
`wIndex=0x0500`, `wLength=0x0100`. The overlay also twice observed a
select-interface request with null/zero fields and rejected it without state
change; its semantics remain unresolved.

The new 179,452-byte capture contains 106 accepted control-IN descriptor
submissions and 106 status-zero callbacks, with no OUT, bulk, interrupt, or
immediate-submit-error record. Its SHA-256 is
`f7ae3a97696dfd1ceff7b511c307d054422250e481deceb7b180167538762a67`.

Postflight found the same device/configuration and interface ownership, no
surviving process, and unchanged protected prefix and original sealed v6
evidence. Full authorization, run facts, raw observations, interpretation, and
hashes are in `../live-read-observe-v2-20260819/MANIFEST.md` and
`checkpoints/CP4_LIVE_OBSERVATION.md`.

Exact evidence verifies under
`out/checkpoints/live-read-observe-v2-20260819T194220PDT/` in the disposable
clone. Its `SHA256SUMS` file hashes to
`45f75278cca8a31fbb70e659efc47849d43f4160ddf0272d99efc6b779f41634`.

The one-run authorization is consumed. Do not retry or replace the active
capture. The next safe work is offline class-interface-IN design and
fake-libusb validation. Semantic URB support, select-interface/alternate-setting
behavior, writes, claims/detach, full UC, Voice FX, and the protected prefix
remain out of scope without separate authorization.
