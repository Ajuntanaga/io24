# Task 9 R141 combined preauthorization verdict

Timestamp: 2026-08-25

## Verdict

R141 is rejected before authorization. Both required reviewers returned
`REQUEST CHANGES`. R141 was never applied, and the live R139 test head remains
frozen.

## Blocking findings

1. The exact-success helper does not detect synchronous libusb control activity
   followed by the correct local synthetic answer.
2. The non-function fixtures retain function-only count, root, and membership
   metadata, leaving coherent non-function behavior untested.
3. Generic negatives only require inequality with the complete captured answer;
   a targeted 49-byte pre-completion caller-buffer corruption passes R141.

The targeted reviewer converted finding 3 into an executable false green
against the actual production boundary in a disposable copy. The holistic
review independently identified findings 1 and 2 from the sealed proposal and
harness boundary.

## Successor requirement

Any successor must retain R141's three-scope exact/negative matrix while adding
a coherent non-function constructor, a complete fake-backend before/after
snapshot for exact and reject paths, and full caller-storage preservation for
every generic miss. It must execute cleanly against live R138 production and
kill bounded mutants for all three findings before another preauthorization
review.

## Boundary

No R141 byte was applied. Live production and the rejected R139 tests remain
frozen. R138 final closure stays blocked.
