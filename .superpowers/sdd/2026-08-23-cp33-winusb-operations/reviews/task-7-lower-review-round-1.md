# CP33 Task 7 lower review round 1

Result: **FAIL**. Task 7 lower and combined review remain open.

Reviewed hashes:

- `wineusb.c`: `87ffe326022144f45313bb734b487633bd7c0766f4c74eb7c60a56f4f04c2e5c`
- `unixlib.c`: `0c20cfbf8eaba9fbc48fb78f6c68a026d95ca132862ee704c085fccf2b9e2a9e`
- lower contract: `4858a78e353e66f8d085b04c7f4e7f61588ff9377629048afc56e95fec1af24b`
- lower fake: `6b599c66a5742b61d5dcae751c2dacfcc784722e4396aafb6a773aaec335741e`
- bus-interface contract: `1ab7456c87ca7f835120059bd780afbb2f3caca017491b1c92a7d36963f9f847`
- retained pipe contract: `0c0fd7950e5b20dfab383d6d7f39fe6399af92daccfa4f4f096c731500ef6c1d`
- retained pipe fake: `f98c28fee7fb27fdce380069770607f2568810ca51456c4a5694215a9a767b86`

## Findings

1. **Important — root configuration retains a caller-metadata fallback.**
   Active-descriptor validation is conditional on `device->function`; root
   SELECT_CONFIGURATION can mint tokens with descriptors disabled. The retained
   contract explicitly expects that success. Its positive interrupt input also
   omits the descriptor's 64-byte maximum and interval 1; function validation
   compares no interval and selection publishes only handles. Require descriptor
   authority for root and function children and exact descriptor-faithful pipe
   metadata before issuing any token.

2. **Important — the R84/R85/R89 matrix remains false-GREEN-capable.** There is
   no executable real stale token after generation two, field-specific wrong
   slot/generation/endpoint/type/interface/alternate, target-only preservation,
   shared generation for both pipes, configuration generation exhaustion,
   committed old-table usability after rollback, or staged/committed table
   reclamation. Zero-pipe claim tests cannot prove pipe-map atomicity. Add direct
   behavioral cases and mutations for target-global retirement, generation and
   record checks, per-pipe generation, pre-COMMIT publication, rollback loss,
   and table leaks.

3. **Medium — SELECT_INTERFACE accepts a trailing partial pipe byte.** It derives
   pipe count by integer division without exact inner-length equality. The
   existing test only shortens the outer URB length. Add a genuine inner and
   outer `+1` case and require exact rejection before the backend.

Verified fixed: duplicate switch removal and actual translation-unit build,
kernel pending-child rejection, reverse partial-claim rollback, claim release
before parent ownership, strict lookup descriptor absence, bounded table shape,
and the four then-frozen R94 hashes. Fresh alternate, claims, sync-pipes,
transfer-lifetime, and bus-interface gates each exited zero, but those greens do
not override the findings. R96 evidence was not counted as GREEN.
