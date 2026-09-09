# Task 9 R142 combined preauthorization verdict

Timestamp: 2026-08-25

## Verdict

R142 is rejected before authorization or live application. Both mandatory
reviewers returned `REQUEST CHANGES`, each with one independent Important false
green. Live tests remain the frozen rejected R139 head.

## Blocking findings

1. A side-effect-free synchronous libusb device/descriptor query mutates none
   of R142's snapshotted fake state. Targeted review executed that bad behavior
   through the actual fake boundary at exit 0 with `failures=0`.
2. Exact positives begin with zero URB status, which is already
   `USBD_STATUS_SUCCESS`. Omitting the production success-status write therefore
   passes every exact positive.

## Successor requirement

Any successor must retain every sound R142 matrix and preservation assertion,
add a fake-boundary-wide libusb call witness observed by exact/reject snapshots,
and seed a non-success exact-status sentinel before production. It must add
executable mutants for descriptor probes in both exact and reject paths and for
the omitted status write, then replay the retained R142 mutant matrix.

Because a boundary-wide witness must be incremented by the fake libusb entry
points themselves, a successor proposal must explicitly request reopening both
`tests/wineusb_winusb_urb_contract.c` and
`tests/wineusb_winusb_urb_fake_libusb.c`. No live edit is authorized by this
ruling.
