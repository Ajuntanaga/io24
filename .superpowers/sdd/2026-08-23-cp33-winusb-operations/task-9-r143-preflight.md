# Task 9 R143 combined preauthorization verdict

Timestamp: 2026-08-25T21:58:04-07:00

## Verdict

R143 is rejected before authorization or live application. Targeted review
returned `PASS`, but holistic review returned `REQUEST CHANGES` with one
executed Important false green. Live tests remain the frozen rejected R139
head.

## Blocking finding

R143's fake now counts every externally defined libusb entry, but only exact
success and function-scope rejection compare the complete snapshot. The
malformed exact-admission helper, its forked null-buffer variant, and generic
rejection helper do not observe `api_calls`. Holistic review compiled a bad
active-production copy that queried the device descriptor before rejecting a
malformed header; the R143 candidate still exited 0 with zero failures.

## Successor requirement

R144 may retain the complete R143 two-file candidate only in a disposable tree.
It must extend the boundary witness to every helper that claims rejection
before backend activity, including generic control rejection, all malformed
exact-admission cases, and the forked null-buffer case. Preserve all existing
status, length, storage, pending, allocation, submission, record, and
`DriverContext` assertions.

The successor must replay all eleven R143 production mutants and add compiled
counterexamples for:

1. a device/descriptor query before malformed-header rejection;
2. a device/descriptor query before null-buffer rejection; and
3. a device/descriptor query before generic control rejection.

Each must execute copied production through the fake boundary and exit feature
1 with nonzero contract failures. A source scan or harness exit 2 is not
evidence. The eventual direct patch may request the same two live test paths
because the fake instrumentation is still necessary, but no live edit is
authorized by this ruling.
