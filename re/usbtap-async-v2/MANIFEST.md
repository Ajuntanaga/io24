# io24 async libusb control completion interposer v2

Built and validated offline on 2026-08-19 PDT. No USB node, Wine process,
Universal Control process, or real Wine prefix was opened during this work.

## Purpose

The submit-only interposer used by the 2026-08-18 patched live-read recorded
three endpoint-zero buffers as `Bo` submissions. Their USB setup packet proved
they were device-to-host `GET_DESCRIPTOR` requests, but the tap could not show
whether libusb rejected, stalled, completed, or lost them.

Version 2 identifies async control direction from `bmRequestType`, reserves one
record ID for the transfer, and wraps the real libusb callback. It restores the
caller's callback and `user_data` before invoking that callback.

Record semantics:

- `S Ci` / `S Co`: async control submission, status `-115` (pending);
- `C Ci` / `C Co`: callback, with numeric `libusb_transfer_status` and
  `actual_length`;
- `E Ci` / `E Co`: immediate negative `libusb_submit_transfer` return, meaning
  no callback was scheduled;
- an IN submission records only its eight-byte setup packet, never stale or
  preallocated receive-buffer bytes;
- an IN callback with a nonzero `actual_length` records only returned data
  bytes after the setup packet, alongside its success or error status;
- submit and completion/error records use the same ID.

Relevant callback status values are 0 `COMPLETED`, 1 `ERROR`, 2 `TIMED_OUT`,
3 `CANCELLED`, 4 `STALL`, 5 `NO_DEVICE`, and 6 `OVERFLOW`. Immediate `E`
statuses are negative libusb error codes instead.

Record IDs use a relaxed C11 atomic counter and each complete text record is
stream-locked, preventing concurrent callbacks from colliding or interleaving
their evidence lines.

## RED-GREEN contract

The contract links a real caller to a deterministic fake libusb shared library
and loads the production interposer through `LD_PRELOAD`. It never links to or
opens the host libusb device path.

Before implementation, the contract failed for the intended reason:

```text
FAIL: expected one submit and one completion record, found 1
ffff880000000000 ... S Bo:1:004:00 -115 12 = 80060001 00000400 deadbeef
```

That RED result caught both defects: endpoint-zero was misclassified as bulk
OUT, and the stale IN buffer was logged without a completion record.

After implementation, both a fresh build and the exact staged artifact pass:

```text
callback contract (completed): pass
callback contract (stall): pass
callback contract (submit-error): pass
usbtap async control contract: pass
```

The three cases distinguish successful callback status 0, asynchronous STALL
status 4, and immediate submit error `-6`. Every case verifies that the caller's
callback pointer and `user_data` are restored; immediate rejection verifies
that the callback is not fabricated.

Sources and SHA-256:

- `../../tests/usbtap.c`:
  `2b640ede1936027a03c49c82cef3cb180fd62b097c9e2c359557330b70def4a4`;
- `../../tests/usbtap_async_contract.c`:
  `bd5aee72244987b29cfe27e76b27fbc45d7ec48bf999df92eceadd9ea346806a`;
- `../../tests/usbtap_async_contract.sh`:
  `e4244e3f1abdb51e9072325841a0f2eb788c7ee711c0e4627e20aaadb6b5f71d`.

## Artifact and reversible staging

Build command:

```bash
cc -std=c11 -Wall -Wextra -Werror -shared -fPIC -O2 \
  tests/usbtap.c -ldl \
  -o re/usbtap-async-v2/x86_64-unix/usbtap.so
```

- compiler: `cc (Ubuntu 15.2.0-16ubuntu1) 15.2.0`;
- artifact SHA-256:
  `fdd1a418be106ec91bafefbad8680eaec7ea8404148a18998178de630cfad916`;
- ELF build ID: `2e03dc877f7b4d9006c52c58faf656ec6b75bf7d`.

Because `LD_PRELOAD` treats spaces as separators, the artifact cannot be loaded
directly from this project's space-containing path. The exact bytes were
copied to the no-space disposable sandbox:

- active `out/usbtap.so` and versioned `out/usbtap-async-v2.so`:
  `fdd1a418be106ec91bafefbad8680eaec7ea8404148a18998178de630cfad916`;
- preserved former `out/usbtap-submit-only-64ddfe1412ea.so`:
  `64ddfe1412ea2bf823374db17a726fd8cf74920456b1d396d9e5e114e37c166a`.

Staging changed only these disposable `out/` files. The disposable prefix
mtime remained `2026-08-18 23:46:00.509397893 -0700`, and no Wine/UC process
was present before or after staging.

## Retained Wine-source correlation

The exact patched Wine 11.15 source remains under the contained io24 build
cache. Its `unixlib.c` constructs the standard IN `GET_DESCRIPTOR` control
transfer and emits `Failed to submit GET_DESCRIPTOR transfer` only when
`libusb_submit_transfer` returns a negative immediate error. That message is
absent from the preserved live log, so immediate rejection is not supported by
current evidence.

On callback, Wine maps `transfer->status` into `UrbHeader.Status`; only
`LIBUSB_TRANSFER_COMPLETED` copies descriptor bytes and updates the returned
length. The new `C` record captures exactly that previously missing status and
length. It does not guess a Wine fix before the status is observed.

## Gate

This is an offline instrumentation result, not a second live-device result.
The existing capture remains in place, so the harness also continues to refuse
an overwrite. Do not move it, rerun `live-read`, broaden to full Universal
Control, or touch Voice FX without a new explicit authorization.
