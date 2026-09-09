# Task 9 R143 holistic preauthorization review

Timestamp: 2026-08-25T21:58:04-07:00

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one.

Material Minor findings: none.

## Important: malformed-admission rejection does not observe the new witness

The contract explicitly requires malformed exact RANGE requests to be rejected
before the backend observes them, but `expect_exact_range_admission_reject()`
checks only legacy control, allocation, submission, pending, storage, status,
length, and `DriverContext` state. The forked null-buffer case has the same
partial observation. Generic rejection still checks only control count and
pending state. None observes R143's new `api_calls` witness.

The reviewer added this ordinary production-callable behavior immediately
before the structural admission check corresponding to active
`unixlib.c:1539`, only in a disposable production copy:

```c
if (req->Hdr.Length != sizeof(*req))
{
    struct libusb_device_descriptor probe;

    libusb_get_device_descriptor(libusb_get_device(handle), &probe);
}
```

Both fake entry points incremented `api_calls`, but neither changed any legacy
value checked by the malformed-admission helper. The R143 candidate compiled
the copied actual production through the fake boundary and still returned:

```text
WineUSB pipe-observe fake-libusb behavior: pass
CP33 lower executed mode=--control-descriptor completions=1 failures=0
contract_exit=0
```

This is a concrete false green: production reaches the backend before rejecting
a malformed RANGE request while the sealed contract passes.

## Strengths and checks

The reviewer independently verified the 9/9 manifest, exact patch hash,
two-path scope, dry-run/application, candidate hashes, live R139 identity,
active/pre-edit R138 lineage, ABI-identical count layout, reset behavior, and
all 32 first-operation fake-entry witnesses. Focused and retained `--red`
replays were clean. Independent omitted-status and exact/scope descriptor-probe
mutants all exited feature 1 with the expected 3/3/6 failures. The three-scope
matrix, preservation guards, generic routing, device/endpoint cases, and
retained high-byte witness otherwise remained intact.

All execution occurred in `/tmp/io24-r143-holistic.VzEpNt`. Copied production
was restored to `ba3172e...d53051`; no workspace file was edited.
