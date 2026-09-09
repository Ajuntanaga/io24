# Checkpoint 3 — staged and validated offline

Reached at `2026-08-19T19:25:23-07:00`. This is the final offline checkpoint
and the required pause before any device-connected trace.

## Exact staged overlay

Only the independently reproduced WineUSB triplet was copied into the
versioned observation-v2 directory:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
e5d4d22ec48ac4321627b30fb014133193d7d77bff3f296e867c1cafe7e07520  x86_64-unix/wineusb.sys.so
03a4c63ec669bf4f05789dfffd42c55e10d9e0ef990a1cc0622c1a0ab7812826  x86_64-unix/wineusb.so
```

The earlier `re/wineusb-usbdi-v1` artifacts remain in place. The harness now
selects observation v2 for `driver-load` and `live-read`, hash-pins all three
files, and mounts them read-only. `bash -n tests/uc_wine_sandbox.sh` passed;
the resulting harness SHA-256 is:

```text
d0efc42a017bde60763976d5fa0985253b4acb19c6b8fe963244ea14caaf20d0  tests/uc_wine_sandbox.sh
```

The staged bytes again passed the USB-DI and observation contracts inside a
USB-hidden namespace. The staged-contract log SHA-256 is
`44d6ab4d2bb184a30e26c0fdd22c07dc064758342e23263c1a95b506073f157d`.

## Disposable driver-load result

The sealed v6 sandbox was cloned before testing. The only sandbox used for
this gate was:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.observe-v2-20260819
```

The resource-bounded, USB-hidden run completed successfully:

```text
unit=io24-wine-driver-load-599712.service
invocation=03b94be02d374ab0b7b7bc08bcd6d385
exit=0/SUCCESS
runtime=17.594s
cpu=3.326s
memory_peak=114.9M
swap=0B
PaeDSPUSB_start_status=0
PaeDSPUSB_query_status=0
```

The namespace reported no host home, hardware, bus, or network. The exact NT
registry probe passed, the corrected Windows 7 and SSE2 paths were observed,
WineUSB loaded as a builtin, and PaeDSPUSB reported `RUNNING` during the test.
Cleanup then unloaded the driver. There were zero `IO24_OBSERVE` records,
which is expected with no device or USB PDO and is not device-behavior
evidence.

The transient unit is now `LoadState=not-found`, `ActiveState=inactive`, and
`SubState=dead`. No Wine, wineserver, Xvfb, or PreSonus process survived.

## Sealed evidence and postflight

The exact run checkpoint verifies at:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.observe-v2-20260819/out/checkpoints/driver-load-observe-v2-20260819T192259PDT/
```

Its `SHA256SUMS` hash is
`4fbaa428e453c34757ce40c129b5e38103ad9f96799ad16c9fe40e3d0544aaad`.
Key run-log hashes are:

```text
d127aae4422b9602587ac556fe765daf70dd0b3337747f672231be04c19cae60  driver-load-console.log
af58df5b3af1f7680b357d97d028f5f9ac8ebbd75e4fbb8b7ee57de79d9ac3c1  driver-load.log
4e1d29b318ad1d6b62ba6517daf5967f5a5d628cb7ede515951d6f6535c4d611  driver-query.log
53c7a0aaddf1136110594fdde8007e5c9b1068658ae955abf37f832f89b26617  driver-load-status.txt
89fd48ff31e0f01b337821853eadbcffcd5a79985ef0921f8fbe7469d22fdac1  registry-probe.log
```

Postflight found zero `194f:0422` devices. The protected prefix
`/home/ajuntanaga/.wine-io24` retained inode 3427833 and mtime
`2026-08-12 00:31:35.825186221 -0700`. The original sealed v6 sandbox was not
run or modified: its `system.reg` remains
`9d51781ebdea23718153c94a8e39c2c659a9c5582c9915ce664b780fec8be0f4`
and its 224,247-byte capture remains
`f7bb87af84915b94a201d7762af0f2f27c017762981c8387175bf2face56c576`.
The cloned disposable prefix changed during its driver run, as expected; the
original did not.

## Required pause

Stop here. The device is not needed for any completed work. It is required
only if the user later authorizes one new live observation trace. Before that
run, reconnecting the device must be followed by a fresh preflight; connection
alone is not authorization. Do not implement either URB, submit a device
request, expose buffers, claim/detach an interface, select an alternate
setting, run full Universal Control or Voice FX, or touch the protected prefix.
