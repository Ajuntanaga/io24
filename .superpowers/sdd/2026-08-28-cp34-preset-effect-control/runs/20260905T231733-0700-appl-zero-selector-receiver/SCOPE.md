# CP34 zero-selector final receiver construction

Timestamp: 2026-09-05T23:17:33-07:00
Status: bounded offline static correction; no live authority

## Scope correction and objective

The opening premise treated the outer host `{Appl,0}` envelope as though it
were the literal query consumed by firmware selector `0x3cf20/0x3ce98`. The
stored-record wrapper is already source-bound to packet layout
`SetP | 0 | 0 | nested Stat`; the selector query on that route is `{0,0}`.

Source-bind the final constructed state of the device global returned by that
zero selector. Recover the order of its lazy initializer, base constructor,
derived constructor, and registered teardown callback; then bind final primary
vtable slot zero and slot `+0x38`. Correct every active report that used a
transient base vtable as final live state.

## Allowed

- Read-only static analysis of the exact hash-pinned firmware application,
  recovered from the installed package in memory only.
- Hardware-free analyzer/tests and task-local documentation.
- Narrow corrections to active reports if exact object provenance requires
  them.

## Forbidden

- Inferring object identity from matching method values or raw adjacent table
  slots without construction/selection provenance.
- Treating a temporary base-constructor or teardown vtable write as the state
  left by the final derived constructor.
- Treating absence of a literal final-vtable pointer as absence of a binding
  when exact code forms that pointer arithmetically from a source-bound header.
- Emitting, staging, patching, flashing, or executing firmware.
- USB/device, interface claim/detach, transfer, ALSA, preset/effect, Wine or
  protected-prefix, network, install, reset, DFU, or REAPER action.

## Stop condition

Stop with a hash-pinned lazy-initializer-to-final-constructor-to-object-to-
vtable-to-slot `+0x38` route, an explicit disposition of the intermediate
no-op checkpoint, corrected executable contracts, and a sealed task-local
handoff. Do not infer runtime completion, physical device state, or authority
for live work.
