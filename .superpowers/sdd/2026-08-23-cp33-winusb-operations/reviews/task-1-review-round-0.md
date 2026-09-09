# Task 1 review — initial verdict

Verdict: **FAIL**.

## Blocking findings

1. The four C families compile production objects but do not link/load/invoke them. The public and function contracts source-scan while discarding `main.o`; the lower contract builds an unused shared object; the cancellation wrapper never compiles `wineusb.c` and source-scans it instead.
2. The required fake Win32 and WDM/lower-stack boundaries are absent. Fake libusb state is not loaded or asserted and lacks the scripted arguments/failures/completion races needed for later behavioral modes. Guard arrays never cross a production boundary.
3. The vendor contract has valid frozen static PE evidence but no synthetic fourteen-operation call sequence through the public boundary.
4. Focused modes are parsed but ignored. Later Tasks 2–13 do not have a usable focused RED/GREEN surface.
5. Raw compile/link commands under `set -e` and uncaught Python `check=True` failures can return `1`, making a harness/tool failure indistinguishable from feature RED. Harness/tool failures must diagnose and return `2` (or another non-`1` value).

## Accepted evidence

- Fresh CP32 seal: 72/72 `OK`.
- Both CP33 clones equal CP32.
- Task checkpoint and review manifests verify.
- Static vendor hash, fourteen imports, and both address windows are valid.
- MI05 bytes encode alt 0 and alt 1 with `0x81`/`0x01`, 512-byte packets.
- Usage checks return `2`; temporary directories are fresh.
- No production, plan, spec, ledger, handoff, or retained-test edit was found.

## Required bounded correction

Keep both CP33 production clones untouched. Replace source-only assertions with host execution of the actual relevant production translation units against complete controllable fakes. Source checks may remain supplemental. Make every focused mode behaviorally distinct and make `--red` aggregate them. Convert every compile/link/static-tool failure into an explicit harness diagnostic and non-`1` exit. Run all five genuine REDs again, regenerate `cp33-red.log` and `task-01-red.sha256`, update the report, and re-prove source equality.
