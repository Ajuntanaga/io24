# Offline verification

Timestamp: 2026-09-06T06:20:48-07:00

## User Channel-2 requirement gate

After the user prohibited slot 0 and required actual Channel-2 storage, the
live runner was changed to block both stock component-201-owning slots before
device open. An added contract proves that the current constraint returns
`BLOCKED_USER_REQUIRES_CHANNEL2_STORAGE` without invoking the device factory.

The focused native-format and staging suite now passes **21 tests**, 0 failures,
exit 0, in 0.228 seconds. No device access occurred.

## Focused contracts

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_cp34_native_model0_slot_stage \
  tests.test_io24_native_stat
```

Pre-correction result: **20 tests passed**, 0 failures, exit 0, in 0.155
seconds. The superseding focused result is recorded above.

The contracts cover exact candidate hashes, native slot-family validation,
byte-preserving model-0 construction, no-I/O dry run, battery and overwrite
gates, invalid selector refusal, zero-based readback normalization, active-slot
bypass/dislodging, command order, post-state verification, and the distinction
between staged transport and physical/standalone/audible success.

## Exact dry run

The pinned slot-0/Input-1 invocation returned `OFFLINE_READY`, one 1092-byte
record, one `MemP` payload with SHA-256
`f0d7f0878f8d06cb5c3629ec452e4b688c2bb342a29975d1a26fbdf0d97e6a8c`,
and candidate SHA-256
`da1b3e00463ed6e51139119611ef18ba8b8286d4db41f7d6dac7290e2f041c57`.
It reported no power cycle, audio capture, stereo-link change, device commit,
standalone recall, or audibility.

## Compilation

`python3 -m py_compile` passed for the staging runner, native analyzer/codec,
driver, and focused tests. The recurring sandbox diagnostic
`Failed to create stream fd: Operation not permitted` preceded commands but did
not affect their exit status.

## Complete suite

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tests -p 'test_*.py' -q
```

Immediately before the user-target safety gate, **261 tests passed**, one
expected skip, 0 failures, exit 0, in 160.291 seconds. The only emitted
diagnostic was the pre-existing unclosed-WAV `ResourceWarning` at
`re/cp34_current_slot_survey.py:260`. The post-correction change is limited to
the new fail-before-open gate and its focused contract above.

No USB/device, Wine, ALSA, playback, capture, network, firmware, installation,
or GitHub action occurred during verification.
