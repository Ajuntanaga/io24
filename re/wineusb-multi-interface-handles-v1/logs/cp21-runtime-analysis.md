# CP21 multi-interface-handles v1 live analysis

## Result

The candidate clears CP18's missing-handle boundary and then stops at the
separate MDL-mapping guard. It does not synchronize the device.

Two valid 256-byte `SELECT_CONFIGURATION` requests each contained seven
interfaces and two pipes. Both passed whole-request validation and population,
with no rejection. Interface 4, alternate 0, class 1/subclass 3 received the
stable bulk handles:

    endpoint 0x02 -> handle 0x202
    endpoint 0x82 -> handle 0x282

The PreSonus driver then issued four 512-byte bulk-IN URBs per device cycle.
All eight carried handle `0x282`, decoded to endpoint `0x82`, and reached
WineUSB with a non-null MDL. Each immediately preceded an
`MmMapLockedPagesSpecifyCache` stub, mapped to null, and produced
`IO24_PIPE_SAFETY event=transfer_reject reason=null_buffer`. There were eight
map events, eight rejections, zero libusb allocations, and zero WineUSB
transfer submissions. Each rejection was followed by a non-dispatching
`KeInsertQueueDpc` stub, also eight total.

## Direct USB evidence

`live-service-usb.txt` is 2,283 lines and 237,649 bytes, SHA-256:

    db25dc188d5cd568fc2082eb8cf34912b12eb3b8b7aabb10cad53a494817e6f9

It contains 146 accepted submissions and 146 status-zero completions. Every
USBmon submit is control-IN. There is no bulk, interrupt, or control-OUT bus
transaction, and no libusb claim, detach, alternate-setting change, or
configuration change.

Libusb recorded six attempts to clear halt on endpoints `0x82` and `0x02`.
All six failed with errno 16 (`EBUSY`). The six-line kernel window independently
records that the Wine processes did not claim interface 4 before those uses;
it contains no reset, disconnect, reconnect, or binding event. These are
failed ioctl attempts, not successful bus transactions.

## Service and postflight

The registered PreSonus Hardware Access Service reached state 4 `RUNNING`, but
the bounded UCNET probe received no `DA` announcement within eight seconds.
No `synchronize.json` exists. `RUNNING` is therefore process-state evidence
only, not communication or synchronization evidence.

The single live unit exited 1 after 25.639 seconds, used 4.492 CPU seconds,
peaked at 103.8 MiB, and used zero swap. Immediate postflight found no live
test unit or candidate process. The device retained serial `AB7C22200355`,
sysfs path `3-1`, node `/dev/bus/usb/003/004`, configuration 1, alternate 0
on all interfaces, `snd-usb-audio` on interfaces 0 through 4, and unclaimed
interfaces 5 and 6. The protected prefix retained its preflight inode and
timestamp; the source clone retained its three pinned hashes.

## Interpretation and next boundary

The handle-population change is directly validated live. The next demonstrated
pre-submission blocker is Wine's null MDL mapping; DPC dispatch remains a
separate compatibility boundary. Interface routing also remains unresolved:
the selected pipes belong to host interface 4, which is still bound to
`snd-usb-audio`, while prior descriptor evidence placed the io24 vendor bulk
pair on interface 5 alternate 1. Do not infer that implementing MDL mapping
alone will synchronize the device.

Any next live run must be a new checkpoint with a fresh preflight and a new
single-run gate. Safe immediate work is offline, test-first analysis of MDL
mapping, DPC semantics, and the interface/alternate selection path.
