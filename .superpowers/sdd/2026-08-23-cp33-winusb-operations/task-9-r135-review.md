# Task 9 R135 mandatory review

## Candidate and integrity

The reviewed successor is the immutable 2/2 `task-9-r135-head.sha256`
snapshot at manifest SHA-256
`fe3bd2130c4af10935088c22cf9541182d78816b2b1bb50213613073da1815ae`.
Its exact R134-to-R135 delta is 34 lines at SHA-256
`386d67d278c61c1e530cefedab58c3fd662f218bdc586519fdc6b4584db93936`.
Both reviewers verified R132-R135 lineage, the fourteen frozen paths, all twelve
controller artifacts, exact diff, implementer-report identity, and live
candidate equality.  Stored execution remains function feature RED at 203,
actual-lower feature RED at twelve, both retained modes GREEN, and sanitizer
marker-clean.

## Mandatory verdicts

Both reviewers returned REQUEST CHANGES.

### Important — retained allocations during admission remain invisible

Actual `winusb.sys/main.c` is textually compiled under the retained allocator
rename, while the four-object admission journal sees only the separate direct
allocator used by `transfer.c`.  R135 snapshots the shared counter only around
later completion calls.  A bad implementation can allocate replacement
transfer/URB pairs through new `main.c` helpers during each admission, preserve
the distinct original stack pairs and outcomes, then use the preallocated
replacements during completion while retiring the four journaled originals in
the exact required order.  Completion performs only copy/free work, so both
R135 completion observers stay quiet and final global balance can pass.

### Important — mandatory mutant evidence is not replayable

The implementer removed all disposable mutant sources and logs.  The sealed
controller manifest contains only baseline focused/retained/sanitizer
artifacts, so reviewers cannot inspect the actual helper route, exact arm, or
203-to-204 delta.  Future required mutants must preserve exact source/diffs,
logs, exit files, and a hash manifest.

### Material Minor — unsigned shared-count equality can wrap

The shared `pool_allocations` counter is `unsigned int`; equality before/after
an interval is not a literal nonwrapping attempt observer.  The replacement
must use an attempt latch or another overflow-safe signal, not arithmetic
equality as its sole proof.

All other R132-R135 evidence reviewed cleanly, including distinct identity and
outcomes, pairwise retirement, endpoint-map mutex behavior, locked-list
invalidation, production insertion observation, order mirrors, terminal join,
frozen paths, and Tasks 11-13 exclusions.

## R136 decision

Production cannot reopen.  Preserve `task-9-r135-head` as rejected evidence.
Reopen exactly:

- `tests/winusb_function_io_contract.c`
- `tests/winusb_function_binding_contract.c`

Binding support may add only a default-no-op allocator-attempt hook invoked at
the retained `ExAllocatePool` entry before its failure branch.  The function
contract may enable that hook and use a nonwrapping Boolean attempt latch.  Arm
the retained latch around each of the two pending admissions and each of their
completions; retain the direct admission journal and a nonwrapping direct
completion-attempt lens.  Alternate-selection work remains outside every
completion interval.  R135's shared arithmetic equality must be removed or
left only as non-authoritative diagnostic evidence.

Preserve exact replayable artifacts for an admission-time `main.c` helper
replacement mutant and the completion-time helper mutant, including sources or
exact diffs, pre/post logs, exits, and a hash manifest.  Include a retained
failed-attempt probe.  The actual-lower contract remains frozen at SHA-256
`9ca49316ceedcbef9fc8e6633fb5b34607cb376a07aad1f593b1a4c063932348`.
All production, wrappers, RANGE, other tests/support, snapshots, and prior
evidence remain frozen.  Fresh function focused/lifecycle, standalone binding,
ASan/UBSan, exact-snapshot, frozen-path, and two-clean-review gates remain
mandatory before production can reopen.
