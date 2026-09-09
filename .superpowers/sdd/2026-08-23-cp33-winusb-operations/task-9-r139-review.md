# Task 9 R139 review adjudication

Timestamp: 2026-08-25

## Verdict

R139 is rejected. Both independent reviewers returned `REQUEST CHANGES` with
the same Important scope-conditioned RANGE false green. The upper correction
is sound, but the two-file candidate is not an accepted final test oracle and
R138 closure must not resume.

## Controller reproduction

The targeted bad `unixlib.c` mutant was applied only to a temporary source
copy. Against the frozen R139 tests, the real lower focused wrapper compiled
and executed that mutant at exit 0 with `failures=0`. The temporary tree was
then deleted. This converts the review concern into executable false-green
evidence rather than a source-only objection.

## Preserved state

The rejected candidate remains frozen 2/2 in `task-9-r139-test-head/` at
manifest SHA-256
`fd27abae1e92fb4b93f96e4c49f2792f205e6f693331d17b090b6992d8b05e62`.
Both live tests remain byte-identical to that head. The 14/14 controller replay
remains sealed at manifest SHA-256
`0cf8ce97cb349d6a1093d731bf8508d77178674c5a66b12c5737591d9c75b24f`.

No production, wrapper, support, RANGE, prior snapshot, prior manifest, device,
Wine/prefix, build/staging, firmware, preset/effect, or live-hardware path was
changed by review or reproduction.
