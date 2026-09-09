# CP34 authorized read-only device preflight - progress

Status: locally verified; authorized live invocation completed and stopped.

## Implementation boundary

- Added `re/cp34_readonly_preflight.py` rather than using the broader `Io24`
  client. The dedicated client does not clear endpoint halts, make vendor
  control queries, call `SetP`, open audio, or persist a driver shadow.
- It reads the host battery before USB enumeration, checks the exact serial
  before claiming interface 5, selects alternate setting 1, sends exactly two
  `GetP | Appl(0) | JaSt` frames, validates `Rply`, and releases the interface.
- It reports only readable slot indices and preset-enable bits plus reply
  hashes. It does not claim stored-slot content, physical commit, recall, or
  audibility.

## TDD evidence

- The new test first failed because the restricted client did not exist.
- After implementation and a fixture correction, the focused hardware-free run
  passed 32 tests across the new preflight contract, preset persistence, and
  static recall modules.
- The complete hardware-free suite then passed 193 tests with one expected
  local-artifact skip in 151.298 seconds. Its only warning was the pre-existing
  temporary-WAV `ResourceWarning` in `re/cp34_current_slot_survey.py:260`.

## 2026-09-03T23:04:39-07:00 - read-only preflight result

- Host battery was 84%, above the mandatory 10-percent stop floor.
- The found device matched serial `AB7C22200355` and reported descriptor
  version `1.28` before the authorized interface claim.
- Interface 5 / alternate setting 1 returned two valid 2040-byte JaSt replies
  with the identical SHA-256
  `d3862c071142d1ff2c02931917779817b553977fc65ff97e896576d130b62039`.
- Readable state was channel 1 slot 0 enabled and channel 2 slot 2 enabled.
- The client then ended. It did not send `SetP`, open audio, change a
  preset/effect, access Wine, touch firmware, detach USB, or use the network.

This is a current identity/readable-state PRESTATE fragment only. The JaSt
response does not expose preset title or stored `Stat` record content, so it
cannot establish a device-resident match, restoration baseline, physical
commit, front-panel recall, or audibility.

## 2026-09-03T23:10:32-07:00 - operator-supplied display observation

- The device shows preset-block icons, not preset names.
- The operator reports compression on every currently onboard preset.

This removes display-title transcription as a route to slot identification.
Common compression is not a record fingerprint, so neither observation turns
the readable slot indices into stored-record content or a host/device match.
No device operation accompanied the report.

## Next action

Wait for separately scoped authority before any further live action. The next
safe non-device work is to determine whether a source-bound native readback can
produce a decoded `Stat` record for the comparison gate.
