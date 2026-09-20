# Candidate: staged-driver, audio-suppressed UC capture

## Done

USB passthrough, WinUSB enumeration, UCNET loopback, capture tooling, and safe
device/VM restoration are proven.

## Verified

The first live attachment installed and started the PreSonus audio drivers and
never opened control endpoint 1. Whether driver staging caused the missed
service hand-off remains a hypothesis. The missing virtual NIC is ruled out.
Windows Audio, not Universal Control, opened endpoint 3 automatically.

## Unverified

UC device discovery after the drivers are already staged, and the actual
VoiceFX activation transaction, remain unobserved.

## Decision

Use one bounded rerun: boot without USB, temporarily stop Windows Audio,
hot-plug only serial `AB7C22200355`, restart only the PreSonus Hardware Access
Service if UC does not enumerate, and abort/detach on any endpoint-3 transfer.

## Evidence

See `PROGRESS.md`, the two hashed USB traces, Device Manager screenshots,
SetupAPI export, and UCNET process screenshot in this directory.

## Next

Obtain exact authorization for the temporary Windows service changes, then
perform the rerun and translate the captured component On/model/parameter wire
sequence into the Linux Host.
