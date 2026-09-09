# Wine ntoskrnl nonpaged-MDL v1 manifest

## Current state

CP22 is complete offline. The patch replaces Wine 11.15's
`MmBuildMdlForNonPagedPool` stub and adds an upstream-style kernel test. It is
not staged in the io24 sandbox and has not touched the connected device.

## Pinned inputs and order

Apply these inputs in order:

    5046f36dae210b198ea69792774d4401feed975d465eca6c251c9394400ec272  wine-11.15.tar.xz
    567cc43f6ba58b01938d78e5e5f4929a9d508077d905142ce69eed1d3a04badb  wine-11.15-ntddi.patch
    c31efc412240b5047578f1dbb41e9443fa972444202c2bf75294bb31c5454ccd  wine-11.15-exprocessorfeature.patch
    ccbf6d0cff8b9f59cecfb6f18497705ff81599b3796d1b5f6185a6bba43c309b  wine-11.15-ntoskrnl-mdl-nonpaged-v1.patch

Every patch requires `patch --batch --forward --fuzz=0 -p1`. The first two
kernel-compatibility patches are unchanged prerequisites already selected by
the CP21 sandbox. The CP22 patch changes only:

- `dlls/ntoskrnl.exe/ntoskrnl.c`
- `dlls/ntoskrnl.exe/tests/driver.c`

## Contract

For a 512-byte `NonPagedPool` buffer—the exact CP21 allocation size—the test
requires the routine to:

- mark the MDL `MDL_SOURCE_IS_NONPAGED_POOL` without falsely locking pages;
- record the first page-frame entry;
- make `MmGetSystemAddressForMdlSafe` return the original buffer; and
- preserve read/write aliasing across the mapped address.

The corrected pre-MDL kernel fails exactly three new assertions. The candidate
passes all new assertions while retaining the same 13 unrelated Wine baseline
failures. Both comparisons ran with networking disabled, private minimal
devices, empty sysfs, and ephemeral Wine prefixes.

## Development output

The contained incremental build produced:

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  ntoskrnl.exe.so
    0c2c004c751c98c4ee389df4d9ddb5175cd4275d065da282fc9f7a002871d155  ntoskrnl.exe_test.exe.so

The PE remains byte-identical to the pre-MDL corrected PE. The candidate Unix
builtin is 1,572,656 bytes with build ID
`662e3f85c5d166e4e004b59c8e27e48e2e184118` and the same six-name undefined
symbol set as the predecessor.

## Gate

CP23 must independently extract, patch, build, run the candidate/baseline
contract, and byte-compare two clean trees before staging. CP22 grants no live
claim by itself. A later live run must retain the WineUSB null/OUT guards and
must not use the protected `.wine-io24` prefix.
