# Task 9 R138 production correction implementer report

## Authority and scope

R138 accepts the unchanged R136 head plus the additive R137 evidence and
unlocks only the nine production paths listed in `RESUME.md`. Every test,
support, wrapper, RANGE, snapshot, manifest, review, and prior evidence path
remains frozen. This report is append-only implementation evidence; Task 9 is
not complete.

## Pre-edit recovery base

Before any production edit, the exact live nine-file head was copied to
`task-9-r138-production-base/`. The corresponding
`task-9-r138-production-base.sha256` manifest verifies 9/9 and has SHA-256
`5a04d77c31be46567355d540893b3e089aa3f5aea6392e9da455b48b011bd1b7`.
Every live production path compared byte-for-byte with its snapshot.

BAT0 was 41 percent and charging. The work remained offline and hardware-free.

## Fresh focused RED

All four frozen focused contracts compiled and executed their actual production
boundaries:

| Boundary | Exit | Failures | Classification |
| --- | ---: | ---: | --- |
| function driver | 1 | 203 | genuine feature RED |
| actual `wineusb.c` | 1 | 12 | genuine feature RED |
| actual `unixlib.c` | 1 | 17 | genuine feature RED |
| public DLL | 1 | 2 | genuine feature RED |

The function summary was
`CP33 function executed mode=--control-descriptor ... failures=203`.
The actual-lower failures are the three cross-interface permitted SELECT
schedules, with four executable failures each. The Unix-lower summary was
`CP33 lower executed mode=--control-descriptor completions=1 failures=17`.
The public summary was
`CP33 public executed mode=--control-descriptor ... failures=2`.

No usage, missing-input, compiler, linker, crash, or harness exit 2 was counted
as RED.

## Implementation order

1. Upper session mutex, per-interface accounting, endpoint lookup, and
   completion retirement.
2. Actual-lower locked complete-list interface classification.
3. Unix lower admission-before-RANGE, canonical predicate reuse, function
   scope, and actual-length reporting.
4. Public descriptor admission and handle seed restoration.
5. Focused, retained, sanitizer, mutant, freeze, manifest, and independent
   production-review gates.

## R138 production implementation

The approved production correction is implemented in six paths:

- `winusb.sys/transfer.c`, `session.c`, and `winusb_private.h`: session-mutex
  admission, actual interface selection, real per-interface transfer counts,
  explicit zero-initialization, target-only alternate blocking, and retirement
  in unlink/count, URB free, record free, object dereference, file-I/O-reference
  order;
- `wineusb.sys/wineusb.c`: a complete locked queued-IRP scan that classifies
  only structurally valid descriptor and generic-control traffic, preserves
  canonical low-byte interface identity, and treats unknown scopes
  conservatively;
- `wineusb.sys/unixlib.c`: structural admission before RANGE synthesis, an
  adapter that calls the existing canonical legacy predicate, a shared response
  helper, low-byte function-scope validation, and bounded lower-reported OUT
  completion length; and
- `winusb/main.c`: descriptor type/empty-fallback validation and restoration of
  `next_handle_token` to seed `1`.

`winusb.sys/Makefile.in`, `winusb.sys/main.c`, and `winusb/io.c` remain unchanged
from the R138 base.

Live verification currently records:

| Boundary | Result |
| --- | --- |
| actual `wineusb.c` focused | exit 0 |
| actual `wineusb.c` retained `--red` | exit 0 |
| public focused | exit 0, failures 0 |
| upper retained lifecycle | exit 0, failures 0 |
| frozen upper focused | one stale-oracle failure |
| frozen Unix focused | 42 predicate-fixture scope failures |

Two isolated test-only corrections in `/tmp` make both remaining focused modes
exit 0 with zero failures. The frozen live tests remain unchanged. Exact
evidence and the proposed minimal patch are in
`task-9-r139-test-oracle-adjudication.md` and
`task-9-r139-proposed-test-oracle.patch`.

BAT0 was 47 percent and charging. All work remained offline and hardware-free.
