# R137 second-admission hookless control

This copied offline fixture arms the helper replacement pair only before the
second pending admission. It uses the hookless R135 control lens and must
compile successfully, exit feature 1, and retain exactly 203 baseline failures.
It asserts two helper allocations, two frees, and the unchanged original 4/4
retirement journal. `mutation.diff` records the exact copied-source mutation.

Replay from any directory with `sh replay.sh`. The wrapper delegates to the
sealed package runner and expects zero retained-latch, direct-lens,
helper-accounting, harness, crash, or sanitizer failures.
