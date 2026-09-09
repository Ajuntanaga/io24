# CP23 — independent nonpaged-MDL builds reproduce exactly

Reached on 2026-08-22. Battery was 96% and discharging, above the mandatory
10% stop threshold. CP22's 30-entry seal reverified before this work. CP23
remained hardware-free: every build and test namespace had private devices,
empty sysfs, private home/tmp/run, and no network. No Wine service was
launched and no host USB node or protected prefix was exposed.

## Independent source and configuration

Two separate source trees had independently extracted the pinned Wine 11.15
archive and applied, in order, the NTDDI, processor-feature, and nonpaged-MDL
patches with `patch --batch --forward --fuzz=0 -p1`. They were partial CP23
state at resume and were treated as untrusted: all four inputs were rehashed,
both complete trees were compared, and all reject/original files were checked.

Each tree has 12,443 regular files, 1,377 directories, no symlinks, and no
`.orig` or `.rej` file. Their full content and metadata digests match:

    content   86445f46b96e4160d604a5a5ef1d609384c6f100d647f6d489b9d0a8a5a1806b
    metadata  1f2739429822d81a76c2b28d44a446c970c0860c4982f2e755fb2565b54b8127

Both configurations use identical virtual paths, pinned Bison/M4 tools,
`SOURCE_DATE_EPOCH=1787101002`, and the same Wine options. Their Makefiles,
config.status files, and compile databases are byte-identical. Raw config
logs differ only in randomized temporary object names from expected failed
feature probes; normalized logs are identical.

## Sequential contained builds

Build A and build B ran separately with one make job, low CPU/I/O priority, a
2 GiB address-space ceiling, hard timeout, private hardware views, and no
network. Both exited zero. Their three outputs are byte-identical to each
other and to CP22:

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  ntoskrnl.exe.so
    0c2c004c751c98c4ee389df4d9ddb5175cd4275d065da282fc9f7a002871d155  ntoskrnl.exe_test.exe.so

The Unix builtin is 1,572,656 bytes with build ID
`662e3f85c5d166e4e004b59c8e27e48e2e184118`. Direct dynamic-symbol
inspection finds five undefined names; the earlier CP22 prose count of six is
a documentation error because the bytes and build ID are unchanged.

## Independent matching-pair contracts

Each side then ran its test binary with its matching fake PE and Unix builtin
in a fresh isolated prefix. Both executed 26,476 assertions and exited 13:
twelve known environment-sensitive failures in the driver subtest and one in
driver_netio. Neither emitted any failure from the new nonpaged-MDL
assertions. After normalizing only temporary driver names, Wine process
prefixes, and thread IDs, the full outputs are byte-identical with SHA-256
`5f998d45f04a5c623d0696885111f99b21d97fa8dd85d78db15123b3f3f563c3`.

## Stop boundary

Stop at CP23. Nothing is staged and no device action occurred. CP24 may stage
only the exact fake-PE/Unix-builtin pair above after a real-harness selector
RED/GREEN and must preserve the already staged WineUSB multi-interface
candidate plus its OUT/null-buffer guards. A fresh disposable clone and one
USB-hidden driver-load must pass before any device-visible gate. Firmware,
full Universal Control, Voice FX, interface claims/detaches, alternate-setting
changes, and the protected prefix remain out of scope. Pause at 10% battery
or lower.
