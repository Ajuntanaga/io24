# Voice FX activation scope

Target: user-owned Revelator io24 serial `AB7C22200355`, firmware `0128`.

Objective: establish the smallest stock-firmware transaction that makes the
Host Voice FX controls effective. Authorized actions are bounded block-201,
processing-mix, assignment, state-read, and listening/capture operations.

Do not access Wine, flash or emit firmware, reset, enter DFU, install software,
change gains, overwrite preset bodies, or alter preset-slot selection. Stop at
or below 10 percent battery.
