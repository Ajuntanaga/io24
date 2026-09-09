# Offline verification record

Timestamp: 2026-08-28T17:52:38-07:00

## Outcome

The host preset/effect persistence phase is GREEN offline, independently
reviewed, and sealed by `SHA256SUMS`. The device-resident custom-slot and audible
Voice FX transaction remains evidence-pending and was not exercised.

## Fresh executable checks

Command:

```bash
PYTHONWARNINGS=error python3 -m unittest discover -s tests -p 'test_*io24*.py' -v
```

Result after the review corrections: exit 0; 10 tests passed in 0.091 seconds.
Coverage includes:

- real hardware-free effect save-load-save replay;
- failed-overwrite preservation and temporary-file cleanup;
- file and containing-directory sync;
- file-only `presetinfo` with no device construction;
- FX-return fader presence, assignment, master, and effective/off/unknown state;
- structurally complete paesdk request/response decoding;
- strict malformed/truncated JSONL rejection; and
- deterministic bus/device/interface/endpoint normalization; and
- preservation plus visible reporting of a coherent novel command.

Command:

```bash
python3 -m py_compile io24.py tests/io24_capture_format.py tests/usbmon_decode.py tests/normalize_io24_capture.py tests/test_io24_preset_persistence.py tests/test_io24_capture_decode.py tests/test_normalize_io24_capture.py
```

Result: exit 0, no output.

Commands:

```bash
python3 io24.py --help
python3 tests/normalize_io24_capture.py --help
```

Result: both exited 0. `presetinfo` is listed as device-free inspection;
startup wording distinguishes host persistence from the unresolved custom-slot
writer; and the normalizer documents its exact six-column, target-device-scoped
TSV contract.

## Independent review

The first read-only re-review identified inner-frame, target-device scoping,
missing-fader, live-setter, matrix-restoration, recovery-state, and service-text
gaps. A second re-review then caught over-strict novel-command rejection and an
unbounded restart description. Both received corrections: a coherent 20-byte
novel command has an end-to-end normalization/decoder regression, shorter
admitted-but-invisible envelopes are rejected, and the unit declares an explicit
three-start/15-second limit. The final independent adjudication found no material
issue and explicitly supported sealing.

`systemd-analyze verify systemd/io24-startup.service` could not complete in this
restricted environment: the tool exited 1 after only SO_PASSRIGHTS/SO_PASSCRED
permission diagnostics and emitted no unit-file diagnostic. This is an
environment-invalid check, not evidence against or for the unit.

## Seal verification

Command:

```bash
sha256sum --check .superpowers/sdd/2026-08-28-preset-effect-persistence/SHA256SUMS
```

Result: exit 0; every listed file reported `OK`.

## Safety and scope evidence

- Battery was 100 percent and `Full` at final verification.
- No Wine process or protected prefix was started or accessed.
- No USB/device node was opened, claimed, detached, read, or written.
- No transfer, preset/effect device operation, firmware action, driver staging,
  install, or network request was performed.
- The frozen CP33 proposals and production surfaces were not changed.
