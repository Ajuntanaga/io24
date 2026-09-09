# Fast closure decision

Update: the proposed slot-0 trial is cancelled by the user. An actual Channel-2
slot cannot be substituted on stock firmware because slots 2/3 do not own
component 201. No live action is eligible until the user chooses between the
two routes in `CHANNEL2-CONSTRAINT.md`.

The Linux host has enough information to construct and transport the stock
firmware's native model-0 slot state. It does not yet have a verified custom
firmware deployment and recovery path.

Custom firmware is therefore not on the critical path. The first live action
must test the stock model-0 private reverb on physical Input 1 with the corrected
native record. Simultaneous two-input behavior is not required for closure. A
standalone audible pass removes custom firmware from the host release scope. A
failure is recorded as a stock-firmware save/recall or routing limitation; any
routing patch, image emission, Linux updater, and recovery validation then
continue only in the later private firmware lane.
