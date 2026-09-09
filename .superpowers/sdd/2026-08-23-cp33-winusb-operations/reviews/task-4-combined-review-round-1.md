# CP33 Task 4 combined independent review — fix round 1

Verdict: **FAIL**

R58 and R59 are addressed. R60 remains **not addressed** because executable
size enforcement is fixture-specific.

## Important finding

`initialize_handle()` records the sizing header and checks the second output
length plus an allocation against `sizing.total_size`
(`tests/winusb_user_api_contract.c:456-463`), but only retained/default MI05
paths use it. Descending total 181, low-speed total 163, and cross-alternate
success fixtures call `f->initialize` directly at lines 506-513. The fake
accepts any initialize output length at least 72 and returns the advertised
fixture bytes.

Consequently a production mutation that allocates/submits
`header.total_size + (header.total_size != 211)` remains green. Route every
successful fixture through the size-binding helper or an equivalent, run that
conditional mutation, and update the report after 181/163 checks execute.

## Dispositions

- **R58 — addressed.** Production preserves raw group order and compares each
  interface number against all prior records. Descending `[5,2]`, duplicate 5,
  and cross-alternate endpoint reuse fixtures execute.
- **R59 — addressed.** `WAIT_FAILED` captures its error before close and restores
  it after clobbering cleanup; the scheduled `ERROR_ACCESS_DENIED` executes.
- **R60 — not addressed overall.** The unconditional `+1` mutation is useful and
  current production expressions are correct, but non-211 enforcement is absent.

All six gates passed. Failed head 16/16, current seal 15/15, round-1 head 16/16,
exact four-file fix scope, 14 full-patch headers, and four fix-diff headers all
verified. R46 remains an explicit Task-6 carry.

```text
rubric             2aed11d6d95c3fbb4876cc6128b2efd36649d38583f52dd2428cc14ace48d999 (`task-4-round-1-rubric.md`)
round-1 package    05be88f96204aceb06f7a1ed5039181cd0cf4dea2a221801f7d8219fc877e783
production DLL     6a2ea0ae74185fffbbb81f957bd0af83bda3f044e9212927b8d71920ba700876
user contract      6e533ef07acb7dce93014938824f1b89985a460e9b056943a2f0eb1eeeb78859
fix diff           3140710a3e03b9fbc3d04b9d8f498c39b7d18fa6de359b75c51995af4db5a48b
full patch         a0c6c29b0c96fbdbc2b29fbbfbc814a6bb890d54f6e208498029b58a05449af9
task seal          aced54e746436694e0e2b919e935164e027e50a94936ca6783c77b0e0da0a470
round-1 manifest   eaaee204760fdbd7c63dc5f333d70282ce9df1e2aed55e9e567be9a01167f39d
```
