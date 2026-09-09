# CP34 structured-state input cursor provenance - progress

Timestamp: 2026-09-05T18:31:26-07:00
Status: locally verified and checkpointed, offline-only static evidence;
independent review remains open.

## TDD recovery

The first new contract invocation errored on the intentionally absent report
key, so it was corrected to assert key presence first. The corrected RED then
failed for the expected missing analyzer boundary in 16.459 seconds. Minimal
source-bound implementation passed the focused contract in 16.871 seconds.

The production change this contract catches is any drift in the fragment-copy,
stack-reader construction, cursor reset, vtable read, or first-read source that
would make `0x531e0` consume bytes from somewhere other than the accumulated
`Stat` buffer at cursor zero.

## Source-bound result

- The live `Stat` branch at `0x42200` reads a caller-supplied copy-extent word
  from input-object offset `+0x19` and a fragment offset from `+0x12`. It
  advances the source to input-object offset `+0x1d` and copies those bytes,
  capped at `0xc1c`, into the device-owned buffer at `device+0x18+offset` via
  the pinned memory-copy target at raw `0x10d930`.
- `0x42222..0x42228` records the completed buffer length at `device+0xc34`.
  Only completion byte zero at input-object offset `+0x16` reaches stream
  construction.
- Constructor `0x2ccf4` creates a non-owning span over `device+0x18`, stores
  its data pointer at stack-stream offset `+0x8`, its data length at `+0xc`,
  its limit at `+0x20`, and initializes cursor `+0x1c` to zero.
- The direct cursor call at `0x42244` receives zero displacement and zero mode,
  taking the `0x2cb6e -> 0x2cb8a` path and retaining cursor zero. No intervening
  write changes that cursor before the stream is passed as `r2` at `0x42266`.
- At `0x531e0`, the first four-byte read forwards through vtable slot raw
  `0x669f4` to reader `0x2cbb4`. That reader loads the data pointer at stream
  offset `+0x8`, adds cursor `+0x1c`, copies four bytes, and advances the
  cursor. If the read succeeds, the tested word therefore comes from the
  caller-supplied `Stat` bytes accumulated at `device+0x18`, offset zero.

Result:
`STAT_STREAM_CURSOR_ZERO_SOURCE_BOUND_FIRST_WORD_FROM_ACCUMULATION_BUFFER`.

## Current Linux frame consequence

The existing pure frame builder maps its nested `MemP` object exactly onto the
firmware offsets: nested `Stat` tag at `+0x8`, fragment offset zero at `+0x12`,
completion zero at `+0x16`, record length 850 at `+0x19`, and record bytes at
`+0x1d`. For retained factory Slap Echo those first record bytes are
`7b690b70`, native word `0x700b697b`. The source-bound cursor trace excludes a
hidden advance or transform on this direct incoming `Stat` path, so the current
Linux-generated frame cannot satisfy the required entry word `2`.

This is a framing incompatibility in the current local generated frame. It does
not prove whether any bytes were physically stored, whether factory recall uses
the same representation, or whether the correct sender form is simply a
four-byte prefix. The exact UC 4.7.2 sender-side representation remains
unresolved and must be recovered before changing or replaying the frame.

## Verification

- Correct contract RED: missing report key, 1 failure in 16.459 seconds.
- Focused GREEN: 1/1 in 16.871 seconds.
- Firmware-static module: 46/46 in 18.210 seconds.
- Existing Linux framing module: 24/24 in 0.182 seconds.
- Complete hardware-free suite: 225 tests passed, one expected historical-
  artifact skip, 159.328 seconds, exit 0.
- The full suite's only diagnostic was the pre-existing unclosed-WAV
  `ResourceWarning` at `re/cp34_current_slot_survey.py:260`.

## Safety and next boundary

No firmware image was built, modified, emitted, staged, signed, uploaded, or
executed. No USB/device, ALSA, preset/effect, Wine, network, reset, DFU,
install, or REAPER action occurred.

The next safe scope is offline source analysis of the retained UC 4.7.2 host
serializer that prepares the `Stat` record bytes. It must recover the exact
sender-side leading representation and its provenance. Do not prepend `2`,
change the local writer, or perform another live write merely because the
callee requires that word.
