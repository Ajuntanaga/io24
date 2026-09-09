# CP6 — implementation and device-free contracts GREEN

Reached at `2026-08-19T20:51:01-07:00`. This is the pause point before clean,
independent builds. No artifact is staged for the harness at CP6.

## Exact implementation boundary

`re/wine-11.15-wineusb-class-interface-in-v1.patch`, SHA-256
`3f63ff71b37a361a0de1605991458d1eb950e632053615e25addb94d0ec24b55`,
layers on Wine 11.15 plus USB-DI v1 and observation v2. It applies to all three
modified files with `--fuzz=0`, and a clean application byte-matches the
development source.

The patch accepts only:

```text
function=0x1b flags=0x3 reserved=0 request=0x02
value=0x0100 index=0x0500 receive_capacity=256
```

The Windows side validates the full URB, maps either the direct transfer buffer
or MDL, and refuses a missing mapping. The Unix side validates the tuple again,
constructs `a1 02 00 01 00 05 00 01`, submits asynchronously with the existing
zero timeout, and retains a cancellation handle. Because the observed flags
include `USBD_SHORT_TRANSFER_OK`, it deliberately does not set libusb's
`SHORT_NOT_OK` flag.

Completion copies only a nonnegative `actual_length` no larger than the
original 256-byte capacity. An overrun copies nothing, returns length zero, and
sets `USBD_STATUS_DATA_OVERRUN`. Cancellation and STALL copy nothing, return
length zero, and map to `USBD_STATUS_CANCELED` and
`USBD_STATUS_ENDPOINT_HALTED`. Immediate submit failure clears the cancellation
handle and frees its setup buffer, transfer, and context.

OUT direction, missing short-transfer permission, unknown flags, altered
request/value/index/length, reserved bits, short headers, and missing buffers
all fail before libusb submission. `URB_FUNCTION_SELECT_INTERFACE` retains the
observation-only common `STATUS_NOT_IMPLEMENTED` path. There is no class-OUT,
claim/detach, alternate-setting, timeout-change, or control-write path.

## Contracts

The final contract inputs are:

```text
c6f872ac7c8257b654e620355b17b92434211f56fc84da20729e5b19bd693a08  tests/wineusb_class_interface_in_contract.c
f70f767da5d1d3475e44694eeec73d6a9290fce72c333f8f856706d2642067bd  tests/wineusb_class_interface_in_fake_libusb.c
f7ee696aae656f413051b6d4f8ac17ab2df9943eee8e2776402e964c5cb19392  tests/wineusb_class_interface_in_contract.sh
```

The fake uses libusb's real ABI and SONAME but exposes no device enumeration.
It drove the real compiled WineUSB Unix call table through:

- exact setup construction and a 26-byte short completion;
- cancellation and STALL completion;
- a synthetic 257-byte overrun with guarded destination memory;
- immediate submit error and exact cleanup; and
- ten malformed, altered, or OUT cases with zero submissions.

The behavioral and source/binary contract passed. Its one error-level Wine log
is intentionally injected by the immediate-submit-error case. The existing
compiled USB-DI v1 contract also passed. Exact outputs are in:

```text
.io24-build/wineusb-class-interface-in-v1/logs/contract-green.log
.io24-build/wineusb-class-interface-in-v1/logs/usbdi-green.log
.io24-build/wineusb-class-interface-in-v1/logs/patch-apply.log
```

## Development build only

The bounded incremental build compiled both changed translation units without
a warning. Its non-staged artifacts are:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  wineusb.sys.so
d5cbdf21f773488523c16bec90af8d83f9c7a9464afc39dceefdea16e399edbc  wineusb.so
```

The builtin and Unix library build IDs are
`e599b02a315eeee14ddf1285d1d995cde15f43c7` and
`e5c7e3e325da2f891f5ffd389d08baa725f91487`. The fake PE is unchanged because
the implementation remains in the paired builtin/Unix library.

## Safety state and next pause

Every build and test ran with USB and `/sys` hidden, external networking
unshared, an empty host home, and no Wine or candidate service. The io24 count
remained zero, no related process survived, and the protected prefix retained
inode 3427833 and timestamp `2026-08-12 00:31:35.825186221 -0700`.

CP7 requires two independent, clean extractions of the pinned signed Wine
archive, zero-fuzz application of USB-DI v1, observation v2, and class-IN v1,
identical virtual build paths and resource limits, all contracts GREEN, and
byte-identical artifacts. Any mismatch is a hard pause before staging.
