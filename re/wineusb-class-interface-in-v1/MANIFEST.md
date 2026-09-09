# WineUSB class-interface-IN v1

## Scope and authorization

This overlay is the offline implementation of the one class-interface request
observed twice by WineUSB observation v2. The owned io24 was disconnected for
all design, build, staging, contract, clone, and driver-load work described
here. No live USB run, control write, class OUT, interface claim/detach,
alternate-setting selection, timeout change, full Universal Control, Voice FX,
or protected-prefix access was authorized or performed.

The accepted request is exactly:

```text
URB function       CLASS_INTERFACE (0x1b)
transfer flags     IN | SHORT_TRANSFER_OK (0x3)
reserved bits      0
request            0x02
value              0x0100
index              0x0500
receive capacity   256
setup bytes        a1 02 00 01 00 05 00 01
```

All other fields, lengths, directions, and flag combinations fail before
libusb submission. `URB_FUNCTION_SELECT_INTERFACE` remains on the common
observation-only `STATUS_NOT_IMPLEMENTED` path.

## Patch and contracts

The implementation patch is:

```text
3f63ff71b37a361a0de1605991458d1eb950e632053615e25addb94d0ec24b55  re/wine-11.15-wineusb-class-interface-in-v1.patch
```

It layers on Wine 11.15, USB-DI v1, and observation v2. CP5 records the RED
fake-libusb baseline; CP6 records the narrow implementation and GREEN
development contracts; CP7 records two independent clean builds, byte
reproducibility, and both contract suites against both builds.

The fake-libusb behavioral test covers exact setup construction, a 26-byte
short completion, cancellation, STALL, a guarded synthetic overrun, immediate
submit cleanup, and ten malformed or OUT requests with zero submissions. The
existing USB-DI v1 contract remains GREEN.

## Reproduced and staged artifacts

Only the exact CP7-reproduced triplet is staged here:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  (2,560 bytes)
404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  x86_64-unix/wineusb.sys.so (192,528 bytes)
d5cbdf21f773488523c16bec90af8d83f9c7a9464afc39dceefdea16e399edbc  x86_64-unix/wineusb.so     (92,760 bytes)
```

The Windows builtin build ID is
`e599b02a315eeee14ddf1285d1d995cde15f43c7`; the Unix library build ID is
`e5c7e3e325da2f891f5ffd389d08baa725f91487`. The staged files byte-match both
clean builds and are regular files, not symlinks.

`tests/uc_wine_sandbox.sh` now selects and read-only mounts this class-IN-v1
triplet for `driver-load` and any separately authorized future `live-read`.
It rejects unknown hashes before launching the transient unit. Observation-v2
selector names and mount paths are absent. `bash -n` passed, and the exact
harness SHA-256 is:

```text
4706b84e5ea5daff2b274af28f6faf051fc66797cb5d569ecc9237ea4effaf7c  tests/uc_wine_sandbox.sh
```

The exact staged builtin and Unix library again passed the class-IN
fake-libusb/source/binary contract plus USB-DI v1 in USB-hidden containment.
Unit `io24-wineusb-class-in-cp8-staged-contracts.service`, invocation
`466a69e381c94434afd82a8fcb844397`, completed status 0 in 2.049 seconds with
21.2 MiB peak memory and zero swap.

## Disposable clone and offline driver-load

The observation sandbox was preserved and cloned to:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819
```

The copy ran into a `.partial` destination under idle I/O, 15% CPU, 512 MiB
memory, and zero swap, then was promoted only after verification. Source and
clone both contained 5,097 files and 41 symlinks; file path/size, symlink, and
directory manifests matched. Key files compared byte-for-byte, the inherited
CP4 checkpoint verified, and `system.reg` had an independent inode.

Exactly one class-IN-v1 offline driver-load then ran:

```text
unit=io24-wine-driver-load-822720.service
invocation=0233fe7e28e94120ad439220eaff61fa
exit=0/SUCCESS
runtime=22.922s
cpu=4.692s
memory_peak=57.3M
swap=0B
PaeDSPUSB_start_status=0
PaeDSPUSB_query_status=0
```

The namespace reported no host home, hardware, bus, or network. The exact NT
registry probe passed; the corrected Windows 7 NT DDI and SSE2 paths appeared;
WineUSB loaded as the hash-pinned builtin; PaeDSPUSB reported `RUNNING`; and
cleanup unloaded it. There were zero `IO24_CLASS_IN`, `IO24_CLASS_OUT`, and
`IO24_OBSERVE` records, as expected without USB or a USB PDO. This proves the
offline overlay load path, not a device request or synchronization.

Key run-log hashes are:

```text
0bddb514f49409e2b8b3909849085460178c6e1f075c7c42408969cb193b7634  driver-load.log
4e1d29b318ad1d6b62ba6517daf5967f5a5d628cb7ede515951d6f6535c4d611  driver-query.log
53c7a0aaddf1136110594fdde8007e5c9b1068658ae955abf37f832f89b26617  driver-load-status.txt
89fd48ff31e0f01b337821853eadbcffcd5a79985ef0921f8fbe7469d22fdac1  registry-probe.log
```

Exact evidence verifies from the checkpoint directory:

```text
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819/out/checkpoints/driver-load-class-in-v1-20260819T231029PDT/
```

Its relative `SHA256SUMS` file hashes to
`4e9e14779bf20a8a8f76a00a4ebb261268764624b6f8a135198832275e6270c1`.

## Postflight and next gate

Postflight found zero connected `194f:0422` devices, no Wine/UC/Xvfb process,
and a collected driver-load unit. The protected prefix retained inode 3427833
and timestamp `2026-08-12 00:31:35.825186221 -0700`. The source observation
sandbox retained `system.reg` SHA-256
`adecbb1610a9d6024bae3c8397f783c3e70cd10ec1d7a4212787cc40673720f5`
and active-capture SHA-256
`f7ae3a97696dfd1ceff7b511c307d054422250e481deceb7b180167538762a67`.
The clone's registries changed as expected during its driver run; its inherited
capture and CP4 checkpoint remained unchanged.

Stop at this offline checkpoint. A device is required only for a future
class-IN observation. Reconnection alone is not authorization. Any such run
requires a fresh full preflight, capture preservation, and new explicit
one-run approval. Class OUT, select-interface semantics, claims/detach,
alternate settings, timeout changes, full Universal Control, Voice FX, and the
protected prefix remain out of scope.
