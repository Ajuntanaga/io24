# Progress

## Recovery identity

The eight-entry pre-edit manifest records the current Host source, focused
regression, documentation, approved design, and implementation plan before any
production edit. This project has no usable Git metadata; SHA-256 manifests are
the recovery boundary.

## Peer agreement

Claude reviewed the approved architecture against the exact 53-file snapshot
created `2026-09-09T10:33:34-07:00`, returned with nonzero token usage and zero
permission denials, and found no substantive contradiction. Its two concrete
requirements are part of the plan: retain `stream.dont-remix` on both sides of
each source and use independent chain owners.

## Status

Task 1 complete. The initial schema tests failed because the Host still emitted
version 1 and had no migration API. The Host-file tests then failed because
`io24.py` rejected version 1 before migration. After implementation, 7 focused
tests plus 4 validation subtests pass. Version 1 is strictly validated, maps to
neutral version 2 Mix A/B balances, and records an explicit migration message;
malformed Host features still fail before the first device setter. The
three-entry `TASK1.sha256` verifies.

Task 2 complete. The initial focused run failed 9 tests because the new balance,
graph, configuration, chain, and manager APIs did not exist. After
implementation, 10 focused tests plus 6 validation subtests pass. Each bus has
its own process owner, exact capture pair, passive non-remixing source, and
readiness lifecycle; failure and updates remain isolated. The two-entry
`TASK2.sha256` verifies.

Task 3 complete. Six initial GTK regressions failed against the retired
per-input monitor implementation. After replacement and two added lifecycle
guards, the entire focused module passes: 65 tests plus 35 subtests. Main is
visibly unavailable; Mix A/B readiness, failure, balance writes, snapshot
adoption, migration disclosure, and shutdown cleanup follow the approved
independent-source lifecycle. The two-entry `TASK3.sha256` verifies.

Task 4 complete. Source/persistence gates pass 123 tests plus 46 subtests; the
complete affected suite passes 183 tests plus 81 subtests with ResourceWarning
elevated to error; release-package verification passes 1/1 without installation.
Two independent 748-row matrix builds and the regenerated checked-in artifact
match at `e3b4b378dd3cd0701415e4af9499dad29c60b6299f9c65d80aa8a7a1f8cae037`.
The initial comparison differed only in source-provenance hashes, including two
pre-task source changes; no device row changed.

Task 5 complete. The separately authorized peer turn refreshed the same exact
53-path boundary at `2026-09-09T11:14:02-07:00`; its manifest verifies 53/53.
Dedicated Claude UUID `15978222-d591-4549-9876-21c04f741e14` returned success
with nonzero token use and zero permission denials. Claude reviewed the final
source, lifecycle, state migration, GTK behavior, documentation, and regression
coverage, found no substantive defect, agreed the implementation is sound, and
explicitly requested no further review turn.

Offline closure stands. No Host, PipeWire, device, audio, Wine, install,
firmware, publication, Obsidian, or other live mutation occurred. Live
PipeWire publication, visual layout/control feel, exact channel selection in
practice, routing, balance behavior, and audibility remain separately gated.
