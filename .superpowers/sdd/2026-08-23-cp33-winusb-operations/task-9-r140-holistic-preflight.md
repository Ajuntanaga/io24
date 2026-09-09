# Task 9 R140 holistic preauthorization review

## Verdict

`REQUEST CHANGES`

Critical findings: none.

Important findings: three.

Material Minor findings: none.

1. The non-function exact positive omits the established tail-guard loop. A bad
   scope-conditioned completion can copy the correct 50 bytes, report length
   50, then corrupt byte 51 and pass.
2. The proposed truth table covers non-function and function/out-of-scope, but
   not function/in-scope low-byte membership. A bad predicate can suppress or
   widen only when `device.function && device_has_interface(...)`; all R140
   cases then pass.
3. The new reject helper omits allocation, free, buffer, and submit-attempt
   counters, allowing forbidden allocate/free activity before the expected
   invalid return.

The reviewer verified the 6/6 manifest, exact patch scope/dry-run, genuine
copied-production isolated proof, and unchanged device, endpoint, structural,
generic, and high-byte witnesses.
