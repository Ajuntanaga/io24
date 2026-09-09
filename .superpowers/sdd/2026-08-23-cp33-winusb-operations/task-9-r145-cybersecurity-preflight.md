# Task 9 R145 cybersecurity preauthorization review

Timestamp: 2026-08-25T23:00:14-07:00

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one.

Material Minor findings: none.

## Threat boundary

R145 changes only the contract and fake-libusb test boundary. It does not alter
deployed production or authorize Wine, a protected prefix, USB, a device,
driver staging, firmware, presets, effects, or live hardware. The relevant
security property is least-privilege fidelity at the compiled
production-to-libusb boundary: an endpoint-rejection path may perform only the
retained active-configuration lookup, with the correct authority objects and
lifetime.

The local SHA-256 seals detect accidental or concurrent drift. They are not
signatures and do not defend against a malicious same-user process that can
replace both an artifact and its manifest.

## Positive evidence

The sealed direct R139-to-R145 patch is
`task-9-r145-proposed-endpoint-call-allowlist.patch`, SHA-256
`4e136fc344a00de8e7f5b1ee33921bb7754de528e0e536879b040c2242addcd9`.
It touches exactly:

- `tests/wineusb_winusb_urb_contract.c`;
- `tests/wineusb_winusb_urb_fake_libusb.c`.

It dry-runs from the verified live R139 head. Disposable application produced
candidate hashes `54ef231b...10f64f` and `855268ed...b16bc`
byte-for-byte. Fresh implementer and controller focused/retained replays
compiled active R138 production through the fake boundary and exited 0 with
`failures=0`. All sixteen R145 mutants compiled, reached that boundary,
emitted the fake pass marker, exited 1 with nonzero feature failures, and were
followed by restoration to production SHA-256 `ba3172e...d53051`.

The fake audit found 32 exported `libusb_*` entries, 32 first-operation global
witnesses, and the three required dedicated counters immediately after their
global witness.

## Important: call counts do not prove authority arguments

R145 observes exactly one call each to `libusb_get_device()`,
`libusb_get_active_config_descriptor()`, and
`libusb_free_config_descriptor()`, plus exactly three global calls. It does
not record their arguments, returned objects, descriptor lifetime, or call
order. A production variant can therefore use the same call multiset against
the wrong authority object and still satisfy the complete snapshot.

In disposable `/tmp/io24-r145-security.B12DKv`, the controller changed only
the active endpoint validator from:

```c
libusb_get_device(device->handle)
```

to:

```c
libusb_get_device(NULL)
```

The R145 candidate compiled that actual copied production through fake libusb
and returned:

```text
WineUSB pipe-observe fake-libusb behavior: pass
CP33 lower executed mode=--control-descriptor completions=1 failures=0
```

The process exited 0. This is an executable false green: the API names and
counts are unchanged, but the required device-handle authority is substituted.
The same design also cannot distinguish freeing the acquired configuration
from an earlier `free(NULL)` followed by omission of the real free.

## Required correction

R146 must retain the R145 global and dedicated counters, then add an
ABI-identical order-and-argument journal to the contract and fake record. It
must prove:

1. the three target calls occupy consecutive global API ordinals in the order
   get-device, get-active-configuration, free-configuration;
2. get-device receives `f->device.handle`;
3. get-active-configuration receives the device returned by get-device;
4. free-configuration receives the non-null descriptor returned by
   get-active-configuration; and
5. the complete backend state changes only by those allowlisted observations.

Fresh executable mutants must cover the passing null-handle substitution,
active-configuration device substitution, and reordered/wrong-descriptor free,
in addition to all sixteen R145 mutants. No live edit is authorized.

## Other security checks

- No secret, credential, payload, network endpoint, untrusted shell input, or
  dependency was added.
- Candidate work used quoted, `mktemp`-created disposable paths.
- No Wine/prefix, USB/device/sysfs, build/staging, firmware, preset/effect,
  UC/Voice FX, or live-hardware boundary was opened.

