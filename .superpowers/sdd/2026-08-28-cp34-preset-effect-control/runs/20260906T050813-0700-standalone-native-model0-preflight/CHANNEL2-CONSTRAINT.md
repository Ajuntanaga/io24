# Channel-2 storage constraint

Timestamp: 2026-09-06T06:20:48-07:00
Status: **NO ELIGIBLE STOCK CHANNEL-2 PRIVATE-REVERB RECORD**

The user prohibited slot 0 and requested a slot on the second channel. No live
write occurred, and the former slot-0 plan is cancelled.

This request cannot be implemented by replacing the slot number alone:

| Native global slots | Front-panel family | Exact native contents | Can store model-0 private reverb? |
|---|---|---|---|
| 0, 1 | Channel 1 | `opt ` channel strip plus component 201 | Yes, but currently prohibited by the user |
| 2, 3 | Channel 2 | `opt ` channel strip only | No; component 201 is absent and rejected by the validated stock layout |

Shared reverb block 202 is absent from all four native slot records. Its live
send/return path can process both inputs, but the known stock slot writer cannot
make that state survive a standalone cold boot.

The remaining honest choices are:

1. If “second channel” means **physical Input 2**, store model 0 in owning slot
   1 and route the singleton Voice FX chain to physical Input 2. The storage and
   hardware preset control remain Channel 1, and survival of the host-selected
   route becomes part of the standalone test.
2. If the effect must be stored in and controlled by an actual **Channel-2
   slot/button**, defer that requirement to the private custom-firmware lane.
   Stock slots 2/3 provide no component-201 storage position to populate.

Sending the slot-0/1 record to slot 2 or 3 would repeat the disproved family
attribution behind the earlier dry Channel-2 trials. It is not an eligible
“try it anyway” substitution.
