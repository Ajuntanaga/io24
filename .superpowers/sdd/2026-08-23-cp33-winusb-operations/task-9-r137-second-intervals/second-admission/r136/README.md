# R137 second-admission R136 witness

This copied offline fixture arms the same helper replacement pair only before
the second pending admission while retaining the unchanged R136 allocation
hook. It must compile successfully, exit feature 1, and report exactly 204
failures: the 203 baseline failures plus one
`control_retained_allocation_end` witness. It asserts two helper allocations,
two frees, and the unchanged original 4/4 retirement journal.

Replay from any directory with `sh replay.sh`. `mutation.diff` records the exact
copied-source mutation; the package runner also requires this log to match the
hookless control after line-number normalization and removal of the one intended
retained-latch failure.
