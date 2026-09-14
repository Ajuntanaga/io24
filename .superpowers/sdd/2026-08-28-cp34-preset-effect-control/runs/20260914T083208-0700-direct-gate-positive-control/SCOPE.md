# Positive control for the native active-slot gate null — scope

Target: user-owned Revelator io24 serial `AB7C22200355`, firmware `0128`.

Objective: determine whether the Main/Input-2 metric used by the 2026-09-14
active-slot probe can observe a Channel-2 gate change at all. Without that, the
native null cannot distinguish a failed write from a blind meter.

Method: hold device, channel, meter, window size and gate parameters constant;
change only the write route, from a native `MemP/Stat` record to the already
hardware-verified direct `SetP`/`gate` setter.

Authorized writes: `set_main_volume`, `set_gain`, `set_gate`, `gate_off`. No
native record, no `PrsM`, no slot write, no routing change, no firmware action.
