# Task 9 R143 targeted preauthorization review

Timestamp: 2026-08-25T21:58:04-07:00

## Verdict

`PASS`

Critical findings: none.

Important findings: none.

Material Minor findings: none.

## Evidence

The reviewer independently verified the 9/9 R143 manifest, live 2/2 R139
head, exact patch hash, two-path scope, dry-run, disposable application, and
both candidate hashes. Active production matched `ba3172e...d53051`; the
archived `ff9bea...b760e` file independently matched the pre-edit R138 base,
confirming distinct lineage stages rather than competing heads.

The review confirmed that the non-success sentinel is written immediately
before production and that the success postcondition remains required. It also
confirmed identical contract/fake `io24_fake_counts` tail layout, inclusion of
`api_calls` in the complete snapshot, sound reset ordering, and 32 exported
`libusb_*` fake symbols with 32 first-operation witness increments.

A clean disposable candidate replay compiled copied active production and
exited 0 with `failures=0`. Three independently recreated successor mutants
all reached the fake boundary and exited feature 1:

- omitted success-status write: failures 3;
- exact-path device/descriptor probe: failures 3;
- scope-rejection device/descriptor probe: failures 6.

Copied production was restored to `ba3172e...d53051`. The reviewer used a
disposable `/tmp/io24-r143-targeted.Sj0zUX` tree and removed it after review.
No holistic R143 output was consulted and no workspace file was edited.

## Commands inspected

The review used `sha256sum --check`, `cmp -s`, patch path/numstat/dry-run and
disposable application checks, strict fake compilation, `nm -D
--defined-only`, per-symbol source audit, baseline replay, and three executable
mutant replays.
