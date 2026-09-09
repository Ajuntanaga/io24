# CP23 nonpaged-MDL reproducibility manifest

## Current state

CP23 is complete offline. Two independently prepared, configured, built, and
tested trees reproduce the CP22 nonpaged-MDL candidate exactly. No candidate
kernel is selected by the io24 harness or staged in a disposable sandbox yet.
The CP22 `MANIFEST.md` remains frozen by the CP22 seal; this snapshot is the
authoritative CP23 continuation.

## Pinned input order

    5046f36dae210b198ea69792774d4401feed975d465eca6c251c9394400ec272  wine-11.15.tar.xz
    567cc43f6ba58b01938d78e5e5f4929a9d508077d905142ce69eed1d3a04badb  wine-11.15-ntddi.patch
    c31efc412240b5047578f1dbb41e9443fa972444202c2bf75294bb31c5454ccd  wine-11.15-exprocessorfeature.patch
    ccbf6d0cff8b9f59cecfb6f18497705ff81599b3796d1b5f6185a6bba43c309b  wine-11.15-ntoskrnl-mdl-nonpaged-v1.patch

Every patch uses `patch --batch --forward --fuzz=0 -p1`.

## Reproduced outputs

Both clean sides and CP22 development output contain:

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  ntoskrnl.exe.so
    0c2c004c751c98c4ee389df4d9ddb5175cd4275d065da282fc9f7a002871d155  ntoskrnl.exe_test.exe.so

The full source trees, Makefiles, config.status files, compile databases,
artifacts, and build IDs compare identical. Config logs compare identical
after normalizing compiler-generated temporary object names.

## Contract result

Each candidate matching pair independently executes 26,476 assertions with
the same 13 established baseline failures and zero new MDL assertion failures.
The normalized outputs compare byte-identical at SHA-256
`5f998d45f04a5c623d0696885111f99b21d97fa8dd85d78db15123b3f3f563c3`.

## CP24 gate

Freeze this manifest and the current harness before changing selection.
CP24 must first record a failing real-harness selector contract, then make the
minimal hash-pinned change that mounts the matching fake PE and Unix builtin.
After contained contracts, use a freshly verified disposable clone and one
USB-hidden driver-load. Any later live diagnostic must still be bounded,
read-only, collision-free, and separately supported by the existing user
authorization and a fresh preflight; reconnection alone is not authorization.
Keep the WineUSB OUT guard, firmware, Voice FX, claims/detach, alternate
settings, and the protected prefix out of scope, and stop at 10% battery.
