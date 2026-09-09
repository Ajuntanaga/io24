# Task 9 R140 isolated scope-pairing proof

All mutations were made in disposable `/tmp` copies. The live R139 tests and
R138 production remained unchanged.

## Baseline

The proposed one-file test candidate executed live `unixlib.c` through
`tests/wineusb_winusb_urb_contract.sh ... --control-descriptor` at exit 0 with
`failures=0`.

## R139 passing bad mutant

Against the frozen R139 head, this scope-conditioned predicate passed at exit 0
with `failures=0`:

```c
range_supported = wineusb_io24_control_range_supported(req);
if (params->device->function &&
        request_type == (LIBUSB_REQUEST_TYPE_CLASS |
        LIBUSB_RECIPIENT_INTERFACE | LIBUSB_ENDPOINT_IN) &&
        req->TransferBufferLength >= 255)
    range_supported = true;
if (!params->device->function)
    range_supported = false;
```

It wrongly synthesizes multiple function-scoped RANGE misses and proves R139
is false green.

## Proposed-candidate mutant results

The same broad/suppress mutant against the proposed R140 test exited 1 with
`failures=16`.

A non-function-only exact-RANGE suppression:

```c
range_supported = wineusb_io24_control_range_supported(req);
if (!params->device->function)
    range_supported = false;
```

exited 1 with `failures=4`, caught by the paired non-function exact positive.

A function-only direction-widening mutant:

```c
range_supported = wineusb_io24_control_range_supported(req);
if (params->device->function &&
        (request_type & ~LIBUSB_ENDPOINT_IN) ==
        (LIBUSB_REQUEST_TYPE_CLASS | LIBUSB_RECIPIENT_INTERFACE) &&
        req->SetupPacket[1] == 2 && req->SetupPacket[2] == 0 &&
        req->SetupPacket[3] == 1 && req->SetupPacket[4] == 0 &&
        req->SetupPacket[5] == 5 && length == 256)
    range_supported = true;
```

exited 1 with `failures=3`, caught by the function-scoped direction-negative
mirror.

Every execution compiled actual copied `unixlib.c` at the fake-libusb boundary.
No source scan was counted as feature evidence. The disposable trees were
deleted after comparison and packaging.
