# Task 9 R142 coherent three-scope RANGE adjudication request

Timestamp: 2026-08-25

## Verdict requested

Authorize one test-only correction in exactly:

- `tests/wineusb_winusb_urb_contract.c`

The complete live-R139-to-proposed delta is
`task-9-r142-proposed-coherent-three-scope.patch`. Its SHA-256 is
`53789e1883e584ca496af5faadc639b8e9e00d2039515402f32f6fd2da9bd3a0`.
No upper test, production, support, wrapper, RANGE implementation, snapshot,
prior manifest, prior review, device, Wine/prefix, build/staging, firmware,
preset/effect, or live-hardware path is requested for reopening.

## Rejected predecessors

R139 was authorized and applied exactly, then rejected after both mandatory
reviewers proved a scope-conditioned false green. R140 and R141 were never
applied. Both were rejected in read-only preauthorization review. The live
tests remain the frozen rejected R139 head.

R141 established the needed exact-positive and seven-negative three-scope
matrix, but its reviewers found three remaining false-green surfaces:

1. exact success did not detect synchronous backend control activity;
2. non-function fixtures retained impossible function metadata;
3. generic negatives did not require the full caller buffer to remain
   unchanged before completion.

## Proposed correction

R142 retains the complete R141 matrix and closes all three findings:

1. `make_nonfunction_device()` clears the function flag, interface count,
   root, and complete membership bitmap together. The fixture keeps only the
   already-selected generic control-transfer state needed to exercise ordinary
   routing.
2. A shared backend snapshot copies the complete fake-libusb count and record
   structures plus allocation count/attempts, submission attempts, reported
   actual length, and pending state. Exact local success and function-scope
   rejection both require this whole state to remain byte-for-byte unchanged.
3. Every generic RANGE miss snapshots the complete guarded caller storage and
   requires it to remain byte-for-byte unchanged while the transfer is pending.
   OUT payload seeding is performed before the snapshot and repeated with the
   same bytes by the existing pending helper.

The exact positive runs as coherent non-function, function/out-of-scope, and
consistent `{0,1,5}` function/in-scope state. Each of the six interface
one-field negatives runs as function/out-of-scope rejection plus coherent
non-function and function/in-scope generic routing. The recipient negative
runs generically in all three scope classes. Structural admission negatives,
null-buffer isolation, endpoint/generic requests, and the `0xab05`/`0xab07`
low-byte witness remain unchanged.

## Isolated proof

Only disposable `/tmp` test and production copies were mutated. The R142
candidate compiled actual live R138 `unixlib.c` through the fake-libusb
boundary and exited 0 with `failures=0`. Its resulting test SHA-256 is
`c4175a58739f09b5d05ccbec6870fbc6cc4dd24ba2ff311272e7e3bff3d53051`.

The candidate then rejected eight bounded bad production variants:

- R139 broad/suppress: exit 1, failures 66;
- membership-conditioned exact suppression/direction widening: exit 1,
  failures 20;
- allocate/free before function-scope rejection: exit 1, failures 18;
- coherent non-function tail corruption: exit 1, failures 1;
- coherent non-function exact suppression: exit 1, failures 10;
- synchronous backend control followed by local exact response: exit 1,
  failures 6;
- targeted 49-byte pre-completion caller-buffer corruption: exit 1,
  failures 1;
- membership-conditioned recipient widening: exit 1, failures 10.

The sealed patch dry-runs against the verified live R139 head and produces a
byte-identical copy of the isolated candidate.

## Next gate

Do not apply without explicit controller authorization. If preauthorization
review is clean and the controller authorizes this exact one-file delta, verify
the R142 manifest, live 2/2 R139 head, and patch dry-run; apply only the sealed
patch; replay focused and retained host gates; replay all eight mutants; freeze
the corrected test; and obtain two clean independent post-application reviews.

Only after the corrected oracle is accepted may R138 sanitizer, full final-head
mutants, production freeze/manifest, independent production review, or Task 9
sealing resume.
