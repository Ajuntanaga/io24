# CP33 Task 5 contract-only round 2 re-review package

- Current rubric: `../task-5-review-rubric.md` (R64-R74), SHA-256
  `2590b23b4727bdbb602b15ab1acfad46165a33aad26b003ae61dd4f1952bef16`.
- Round-1 package: `task-5-round-1-package.md`, SHA-256
  `67ddb9c609855fefe3bd77d50254584e2d8387873ef1faf24af68a2509d9037d`.
- Frozen round-1 head: `../task-5-round-1-head`, manifest
  `task-5-round-1-head.sha256`.
- Contract-only round-2 head: `../task-5-round-2-head`, manifest
  `task-5-round-2-head.sha256`.
- One-file/one-hunk proof diff: `task-5-round-2.diff` (11 lines), SHA-256
  `7e930347d2d3f3b808d82c03f71aa9f940ed7423edfdcd8d61142f880d4d0ce2`.

## Supplemental proof gap and correction

The R73 production correction remained clean, but resetting the token counter
after final root teardown passed the first 32-cycle contract. That contract
proved uniqueness only while one root remained live.

R74 preserves the retired root token and all 32 issued associated tokens,
creates a fresh root after final teardown, requires its token differ from every
prior token, and rechecks stale Free/Associated/Descriptor/Speed admission
while the fresh root remains live. Production and private-header hashes remain
byte-frozen:

```text
8f4144b2f540f05c16a53bf4f49f1ea29455e30effb2589818ea13a3cc64d753  dlls/winusb/main.c
4be97b07b4f091619a9c5c86b42a33af31976ffbaf61c7576d42c0a15626a1c0  dlls/winusb/winusb_private.h
7547c6f2292c3a8650bb18b0610959eee30927418e1d6b279a5bf6f6e8751fca  tests/winusb_user_api_contract.c
```

Against frozen pre-fix production, final `--handles` remains a genuine feature
RED with 33 failures and exit 1. Authoritative log
`task-05-handles-red-fix-round-1-cross-root.log` has SHA-256
`ae29510b7da2ddc8988d120a3df04c6b98df016bc1053c8df379f49f243e0e7b`.

## Final gates and mutations

All eight `gate-1-final-*.log` contract gates exit zero. Their summaries remain:

```text
handles/descriptors/user initialize: failures=0, submits=3, releases=1
surface: native, m32 unavailable, exports=14, stubs=8
function lifecycle: dispatches=12, failures=0
function initialize: dispatches=4, mode-ioctls=1, last=0x222002/status=0, failures=0
metadata bus and binding: pass
```

All nine final-head mutations exit feature 1. The new
`token-reset-after-root` lens reports five failures; the other eight retain
their expected failure classifications. Exact diffs and logs verify 18/18 via
`task-5-round-2-mutations.sha256`, SHA-256
`5ecdd93bbf63a895f6fc84a0acf85ad4e33f768d3835d2b6e593c8cb6c0b648b`.

## Integrity and review request

```text
round-1 head manifest: badd96e9cdc05ab96fba67b2a91d753d41bbc6abd99ff43c2ae0474b7279ec4a
round-2 head manifest: 30dd58c4130af55dd0c3b2843b15809f5d0dfbd5352ee029f98c3fdf8dc2805f
entries:               3/3 in each
round-2 diff headers:  exactly 1
production delta:      none
```

Judge the round-0 Important lifetime issue and the cross-root proof gap
ADDRESSED or NOT ADDRESSED; then report any new Critical, Important, or Minor
finding. Review is read-only. Do not use Git, run Wine or a contained/full
build, touch a prefix or device/live USB path, install anything, or perform
physical actions.

## Final disposition

Independent review round 2 returned PASS with no Critical, Important, or Minor
finding. Gate 1 was then sealed at exactly 35 unique inputs; 35/35 verify and
the seal SHA-256 is
`e1d164ec9197be4385cc4d0a8279cf7e906d1972379390a6ca8fb3567f670122`.
