# Task 9 R140 preauthorization adjudication

R140 is rejected before authorization or live application. Both independent
preflight reviewers returned `REQUEST CHANGES`. They agreed that the reject
helper fails to observe libusb allocation/submission activity. Holistic review
also found missing function/in-scope membership and a missing non-function
tail-guard lens.

No R140 patch was applied. The live workspace remains byte-identical to the
rejected 2/2 R139 head. The sealed R140 package remains preserved as rejected
proposal evidence at manifest SHA-256
`1c75fcd2f42a9066a3b0efb69042b1c245e769f68e897aacdfee13b0ce009354`.

A successor must cover the exact positive and all seven one-field negatives
under a consistent three-scope matrix: non-function, function/out-of-scope,
and function/in-scope. Exact positives must share full status/length/payload,
tail-guard, no-allocation, and no-submission assertions. Out-of-scope rejects
must additionally prove zero allocation attempts/counts/frees, buffer activity,
and submit attempts while preserving the entire caller buffer.
