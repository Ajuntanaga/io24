# CP33 Task 4 kernel-half independent review — fix round 1

Verdict: **PASS**

No Critical, Important, or Minor kernel-half issue remains.

## Prior findings

- **Builder-IRP lifetime — addressed.** `session.c:70-97` uses only the supplied
  `IO_STATUS_BLOCK` after dispatch. The fake frees each IRP before return at
  `tests/winusb_function_io_contract.c:260-267`, with ASan enabled by
  `tests/winusb_function_io_contract.sh:7-18`.
- **USB status channel — addressed.** Production seeds
  `USBD_STATUS_NOT_ACCESSED` and requires success at `session.c:79-96`.
  Missing-write cases execute at `tests/winusb_function_io_contract.c:953-964`.
  The lower backend's validated success path explicitly sets success at
  `unixlib.c:1265-1302`; its baseline diff is exactly that one line.
- **Packed-record alignment — addressed.** Checked offsets and aligned-local
  `memcpy` helpers appear at `session.c:282-335`, and all record construction and
  consumption uses them. Tests decode odd offsets through `memcpy` at
  `tests/winusb_function_io_contract.c:504-514`.
- **Interleaved alternates — addressed.** Reappearing interfaces after another
  group begins are rejected at `session.c:251-260`; the literal counterexample
  executes at `tests/winusb_function_io_contract.c:717-720`.
- **Generic default endpoints — addressed.** Select sizing and pipe population
  include default endpoints at `session.c:483-556`. The independent one-pipe
  fixture executes at `tests/winusb_function_io_contract.c:848-892`.
- **Post-select/precommit claim rollback — correctly carried.** R46 records this
  as Task 6 ownership in `progress.md`. Task 4 adds no persistent
  claim/configuration effect.

## Authorized gates

```text
--initialize: exit 0, failures=0
--lifecycle:  exit 0, failures=0
binding:      exit 0, exact CP32 terminal line preserved
```

## Reviewed hashes

```text
session.c                         ca8dee42917d0ecbed13f0a9018404722137fe92a472ae4491793650bd07a0dc
winusb.sys/main.c                 b8dd5e7d41501dd1df0afb83860bc948baf929c400d2ff4dd1853e8061e9081a
winusb.sys/winusb_private.h       4d86d68fa30895c95214bdf07f7740516dcccd289903e28eda564f4ff3efa272
wineusb.sys/unixlib.c             26aca45291ae882bcd03f3a2882c75271157b7ce91c82a2065bba43a095c0c71
function contract                 e05d51fff2a37bdf92acce9806c5ee0fd758d89621c2431559e6daff3f8f7ce1
function wrapper                  76fecbd9533983d9b764dbda5bf3874ffd9b9e9a89dee6984f3c75e0cb3ae941
kernel report                     0f537d69b6a027f0422389439cae08e7567bdd4fefb9342e376ead1047a57baa
```

R28 and the combined rubric correctly reflect the expanded fourteen-path patch
and fifteen-entry seal. R49-R55 are DLL-specific and were outside this kernel
re-review.
