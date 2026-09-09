# Task 9 R146 targeted preauthorization review

Timestamp: 2026-08-25

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: one.

Material Minor findings: none.

## Important: descriptor lifetime is not observed

R146 proves the get-device, get-active-config, free-config call multiset,
ordinals, and pointer lineage, but has no observation between descriptor
acquisition and the CPU-side descriptor traversal.

In fresh disposable `/tmp/io24-r146-targeted.vJnD0c`, the reviewer moved the
correct `libusb_free_config_descriptor(config)` from after descriptor
traversal to immediately after successful lookup. The later traversal remained
unchanged and the original late free was removed. This preserves exactly three
correctly ordered calls and the correct handle, device, descriptor, and pointer
lineage.

The R146 fake only journals free and leaves the descriptor readable. The
mutated copied production therefore compiled through fake libusb and passed:

```text
WineUSB pipe-observe fake-libusb behavior: pass
CP33 lower executed mode=--control-descriptor completions=1 failures=0
```

The sealed nineteen-mutant matrix covers a wrong-descriptor free, but not this
correct-pointer premature free and subsequent use-after-free.

## Strengths and checks

- R146 manifest verified 12/12.
- Frozen R139 head verified 2/2; live fake matched `c48fbe4c...52acb`.
- Patch matched `ec62d2a8...c214f`, dry-ran, and touched only the two
  requested paths.
- Disposable candidate hashes matched `68082796...b4fc5` and
  `399b21b5...340fc`.
- Active/copied production matched `ba3172e...d53051`; the pre-edit snapshot
  remained `ff9bea...b760e`.
- Count/record layouts were ABI-identical, used `uintptr_t), and reset fully.
- The compiled fake exported 32 `libusb_*` symbols with the global witness
  first by the reviewer's source lens, and exactly three dedicated increments.
- Focused and retained baselines passed.
- An independent null-handle same-count variant correctly failed at exit 1
  with three feature failures.
- Copied production was restored before review close.

Commands included manifest/hash checks, patch path/numstat/dry-run,
disposable application, strict fake compilation, `nm`, per-symbol source
audit, normalized layout comparison, focused/retained replay, and two
same-count production mutants. The disposable tree was removed after
restoration.

