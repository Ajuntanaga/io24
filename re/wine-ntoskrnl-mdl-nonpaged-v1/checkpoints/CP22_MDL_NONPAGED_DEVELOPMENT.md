# CP22 — Wine nonpaged-pool MDL compatibility, offline

Reached on 2026-08-22. Battery was full at 100%. CP21's project and runtime
seals had reverified before this work. The connected io24 remained outside all
CP22 namespaces; no service was launched and no USB node or sysfs tree was
visible to the build or contract runs.

## Root cause

CP21 records 24 successive 512-byte `IoAllocateMdl` calls immediately followed
by 24 `MmBuildMdlForNonPagedPool stub` events. The eight later bulk-IN URBs
then call the independent `MmMapLockedPagesSpecifyCache` stub, receive null,
and are rejected by the existing WineUSB safety guard before allocation or
submission.

Wine's inline `MmGetSystemAddressForMdlSafe` already returns
`MappedSystemVa` when `MDL_SOURCE_IS_NONPAGED_POOL` is set. Microsoft likewise
documents that an MDL built for nonpaged pool already has a system mapping and
that the safe mapper reuses it. The lifecycle defect is therefore upstream of
WineUSB: Wine's builder never described the allocated buffer.

References:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-mmbuildmdlfornonpagedpool
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-mmgetsystemaddressformdlsafe

## Test-first result

The new driver test allocates the exact 512-byte nonpaged buffer seen at CP21,
creates its MDL, and checks the source flag, unlocked-page semantics, first PFN,
safe mapped address, and source aliasing.

Against the corrected pre-MDL kernel, the final isolated run reports 16 total
failures: the 13 known environment-sensitive baseline failures plus exactly
three new RED failures for the absent flag, zero first PFN, and null mapped
address. Against the candidate, all three disappear; the run reports only the
same 13 baseline failures. The successful mapping executes one additional
alias assertion. The final build is warning-free in the changed test unit.

An earlier candidate comparison retained in `logs/contract-green.txt` loaded
only the candidate Unix builtin beside the packaged PE and stayed RED. Binding
the matching candidate fake PE as well made the new contract GREEN. That
selector mistake is retained because it proves the paired-artifact requirement
for CP23 and staging.

Both final runs used fresh ephemeral prefixes inside networkless Bubblewrap
namespaces with minimal `/dev` and empty `/sys`; neither could access hardware.
The concise final evidence is `logs/final-contract-summary.txt`.

## Implementation

The isolated patch is:

    ccbf6d0cff8b9f59cecfb6f18497705ff81599b3796d1b5f6185a6bba43c309b  wine-11.15-ntoskrnl-mdl-nonpaged-v1.patch

It applies to the pinned Wine 11.15 tree with fuzz zero and changes only the
builder plus its test. The implementation clears `Process`, records the
existing system virtual address, fills every PFN slot using Wine's current
virtual-as-physical model, and sets `MDL_SOURCE_IS_NONPAGED_POOL`. It does not
lock, allocate, remap, or free pages and introduces no USB behavior.

The contained development outputs are:

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  ntoskrnl.exe.so
    0c2c004c751c98c4ee389df4d9ddb5175cd4275d065da282fc9f7a002871d155  ntoskrnl.exe_test.exe.so

The fake PE is unchanged because the export specification did not change. The
new Unix builtin is 1,572,656 bytes, has build ID
`662e3f85c5d166e4e004b59c8e27e48e2e184118`, and preserves the predecessor's
six undefined dynamic symbols.

## Boundary

CP22 is development evidence, not a staged artifact. CP23 must build the exact
archive and three-patch kernel chain independently twice, run the contract on
both outputs with matching fake-PE/builtin pairs, and byte-compare them before
the authorized CP24 diagnostic. The protected prefix, firmware, OUT transfers,
claims/detach, alternate settings, and full Universal Control remain untouched.
