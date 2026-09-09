# Task 9 R148 independent preauthorization review request

## Proposed scope

Review, but do not apply, the direct two-file proposal:

- `tests/wineusb_winusb_urb_contract.c`
- `tests/wineusb_winusb_urb_fake_libusb.c`

Patch: `task-9-r148-proposed-unified-rejection-state.patch`

Patch SHA-256:
`23333adc2918a72e2f1b32c53713533620f1be782373d1fcd389f4c598f2d08a`

Candidate hashes:

- lower contract:
  `56a7aace5141dff885e4859659cc1e729031deeba76e371cbbcc1b64ebdf7cf5`;
- fake:
  `bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15`.

Evidence archive:
`task-9-r148-isolated-evidence.tar.gz`, SHA-256
`561da904b991e9fcf41c55f1c95230f7a8f90d5e24c228069e9f606b22dea4a1`.

## Targeted lens

1. Does complete immutable rejection state now cover generic, endpoint,
   function-scope, malformed/mismatched/undersized admission, and forked
   null-buffer rejection?
2. Does pipe-table comparison check pointer identity before any dereference,
   safely reject a changed/null pointer, and still detect same-pointer deep
   mutation?
3. Do endpoint journal assertions retain captured pre-call handle authority?
4. Does a retained product assertion failure remain feature exit 1 and continue
   into the requested lower group, while actual harness failures stay exit 2?
5. Are rows 25-29 real copied-production executions with the required marker,
   failure, and no-crash classification?

## Holistic lens

1. Does the direct patch apply from frozen R139, touch exactly two allowed
   paths, and reconstruct both declared candidates byte-for-byte?
2. Are focused and retained baseline/final results clean, and are all 29
   canonical mutations meaningful feature REDs rather than compiler, loader,
   or harness substitutes?
3. Are the fake ABI layouts, resets, global witness ordering, dedicated journal
   ordering, and mutable configuration view still correct?
4. Does the R147-to-R148 delta close the rejected defects without weakening
   existing state, backend, storage, length, status, guard, or context checks?
5. Is there any remaining material false green, unsafe comparison, unintended
   scope, or regression?

Return PASS only with no Critical, Important, or material Minor finding. This
review does not authorize application, production work, or Task 9 closure.
