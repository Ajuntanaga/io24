# Task 9 R144 cybersecurity preauthorization review

Timestamp: 2026-08-25

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one.

Material Minor findings: none.

## Threat boundary

R144 changes test/fake code only, invokes no device or protected runtime, and
does not expand deployed production attack surface. The relevant security
boundary is the compiled production-to-libusb call boundary: a rejection path
must perform only the backend reads required by its contract. An unexpected
libusb call is not harmless merely because the fake makes it side-effect-free;
on a real backend it is additional device interaction and a least-privilege
violation.

The task-local hashes protect against accidental or concurrent drift. They are
not signatures and do not protect against a malicious same-user process that
can replace both an artifact and its manifest. No stronger adversary model is
claimed by this local offline workflow.

## Important: endpoint-rejection exception has no allowed-call oracle

R144 correctly distinguishes generic pre-backend rejection from three
endpoint-recipient cases whose retained active-endpoint validation legitimately
calls:

1. `libusb_get_device()`;
2. `libusb_get_active_config_descriptor()`; and
3. `libusb_free_config_descriptor()`.

However, `expect_control_endpoint_reject()` retains only the old `control==0`
and no-pending assertions. It does not constrain the number or kind of libusb
calls. The new global `api_calls` witness is therefore ignored precisely where
an allowed backend sequence needs an allowlist.

In disposable `/tmp/io24-r144-security.8VLRBi`, the reviewer inserted this
ordinary production-callable behavior only for the known endpoint `0x01` plus
IN-direction mismatch exercised by the endpoint-rejection helper:

```c
if (recipient == LIBUSB_RECIPIENT_ENDPOINT &&
        req->SetupPacket[4] == 0x01 &&
        (request_type & LIBUSB_ENDPOINT_IN))
{
    struct libusb_device_descriptor probe;

    libusb_get_device_descriptor(libusb_get_device(handle), &probe);
}
```

The R144 candidate compiled actual copied production through the fake boundary
and returned:

```text
WineUSB pipe-observe fake-libusb behavior: pass
CP33 lower executed mode=--control-descriptor completions=1 failures=0
```

The extra device and descriptor calls are visible in `api_calls`, but the
endpoint helper never compares it. This is a concrete security-relevant false
green, not a source-only concern.

## Required correction

Keep endpoint-recipient validation distinct from zero-backend rejection, but
make its allowed backend schedule observable. Extend the ABI-identical fake
count structures with dedicated counters for `libusb_get_device()`,
`libusb_get_active_config_descriptor()`, and
`libusb_free_config_descriptor()`. Increment each after the existing
first-operation global witness. For each retained endpoint-rejection case,
capture the complete backend snapshot, change the expected copy by exactly one
for each dedicated counter and exactly three total `api_calls`, then require
the complete expected state. This permits the required active-config lookup
and rejects omitted, substituted, or additional backend calls.

Add executable mutants for the passing extra device/descriptor query and for a
direction-mismatch rejection that skips active-endpoint validation. Replay the
complete R144 14-mutant matrix. No live edit is authorized.

## Other security checks

- The proposal contains no secrets, credentials, network endpoints, shell
  interpolation from untrusted input, or new dependencies.
- Candidate setup uses `mktemp`-created disposable directories and quoted
  paths; no protected prefix, Wine, USB/sysfs, staging, firmware, or live
  device boundary was opened.
- Bounds, caller-buffer guards, exact lengths, status sentinels, and the full
  no-backend snapshot are preserved and materially reduce tampering and unsafe
  backend-routing false greens.
