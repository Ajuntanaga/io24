# Task 9 R145 preauthorization verdict

Timestamp: 2026-08-25T23:00:14-07:00

## Verdict

R145 is rejected before independent ordinary preauthorization review,
explicit authorization, or live application. The live tests remain the frozen
rejected R139 head.

## Blocking finding

R145 closes R144's unrestricted endpoint-call exception with exact API counts,
but those counters do not bind the calls to their arguments, returned objects,
descriptor lifetime, or order. A copied production variant substituting
`libusb_get_device(NULL)` for
`libusb_get_device(device->handle)` compiled and passed the full focused
contract at exit 0 with zero failures.

## Successor requirement

R146 may retain R145 only in a disposable tree. It must add ABI-identical
order and pointer-lineage observations, kill the null-handle, wrong-device,
and wrong/reordered-free counterexamples, and freshly replay all sixteen R145
mutants. Its eventual direct patch may request the same two test paths. This
ruling authorizes no live test or production edit.

