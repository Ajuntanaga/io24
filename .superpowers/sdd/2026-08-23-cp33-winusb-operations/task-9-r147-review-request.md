# Task 9 R147 independent preauthorization review request

Review the exact unapplied R147 proposal and return `PASS` or
`REQUEST CHANGES` with file/line evidence.

## Exact review object

- patch: `task-9-r147-proposed-lifetime-and-reject-state-oracle.patch`
- patch SHA-256:
  `8285b45f3c59c0b6442c59df1a943843f8ad45a997fd5e74d2315c20ed753801`
- candidate contract:
  `45c33598b8cf74298248a4e5e0ad3826527259c8dc8474e7e0d8fe1007c4681a`
- candidate fake:
  `bd76d84e99227549eb587317971c33707457b56d93de3a90e1e5672b509bab15`
- evidence archive:
  `71a549fb9314b2ff1bc829d7dc36ca9ffacb71ac2301741d36e0ee9b5a6a814a`

Read the R147 brief, implementer report, adjudication, isolated proof, controller
preflight, proposal patch, and evidence archive.  Verify the patch directly
against frozen R139 rather than trusting prose summaries.

## Questions

1. Can any rejection mutate caller/device/pipe-table state other than the
   required invalid URB status and still pass?
2. Can a production mutation change the device handle and validate calls
   against its own changed state?
3. Does moving the correct descriptor free before traversal fail safely and
   for the intended feature reason?
4. Is the global witness truly first in every exported fake function in source
   and compiled code, with each dedicated increment immediately second?
5. Are all 24 mutant rows fresh, compiled, production-through-fake executions
   with distinct canonical evidence and exact restoration?
6. Does the direct patch touch only the two allowed test paths and reconstruct
   the declared candidate hashes from frozen R139?
7. Did R147 add any dependency or external-operation surface?

Do not edit live tests or production.  Any fresh replay must remain disposable,
offline, and hardware-free.
