# CP7 — independent clean builds are reproducible

Reached at `2026-08-19T22:48:01-07:00`. This is the hard pause point after
clean-build reproducibility and before any artifact staging or harness change.

## Pinned inputs and independent sources

Both source trees were freshly extracted from the same retained Wine 11.15
archive, then patched in order with USB-DI v1, observation v2, and the narrow
class-interface-IN v1 implementation. The exact inputs are:

```text
5046f36dae210b198ea69792774d4401feed975d465eca6c251c9394400ec272  wine-11.15.tar.xz
9e1c3b88a428e3bdd245ee5cdda9dfa423e77ad4abe08c7423bf14dceb073e91  wine-11.15-wineusb-usbdi-v1.patch
ad260f9ab4a1bc138d8ee3fdd7ec3157e0caf8d6a67b490be4bd815092fa5e64  wine-11.15-wineusb-urb-observe-v2.patch
3f63ff71b37a361a0de1605991458d1eb950e632053615e25addb94d0ec24b55  wine-11.15-wineusb-class-interface-in-v1.patch
```

Zero-fuzz application produced the same changed-source hashes in independent
`source-a` and `source-b` trees:

```text
603998bae9b4c40877bc5d3b2678d9b87682b7137cb2e10da5b2ee548ef27a4f  unixlib.h
1d05ac120e747808ee5af56b532bc3e14558babf607bdc53f9fc751c2a575003  wineusb.c
aaafbb888a3391a385f6012880b8d9dd863c7e79a2e7017017ee954cc281b70d  unixlib.c
4296c33f7aa300a042b8198b6715e8d1e108c3907a58a7ed3d8e96c250890886  usbdi.h
93422cbd9975088b217ef4730620ef1512e70e3879750e8dc4860f0db75ae33b  usbdi.c
```

The initial A configure probes are preserved separately in
`build-a-preflight-attempts`. They stopped before Makefile generation because
the extracted Bison data directory and its extracted M4 executable were not
explicit. No candidate artifact was produced. A direct USB-hidden probe then
proved the fix: set `BISON_PKGDATADIR=/run/io24-tools/usr/share/bison` and
`M4=/run/io24-tools/usr/bin/m4`. Final A and B started in fresh empty build
directories with those exact pinned paths.

## Identical build conditions

Both builds used identical virtual paths (`/run/io24-source` and
`/run/io24-build`), `SOURCE_DATE_EPOCH=1787101002`, the retained libusb header
and runtime, and `make -j1`. Each transient user unit enforced:

```text
MemoryMax=2G MemoryHigh=1536M MemorySwapMax=0
CPUQuota=25% TasksMax=64 RuntimeMaxSec=900
Nice=15 IOSchedulingClass=idle
```

Bubblewrap unshared user, PID, network, IPC, UTS, and cgroup namespaces,
dropped every capability, supplied a private `/dev`, and hid `/sys`, udev,
host home, and the protected prefix. Source and pinned tools were read-only;
only the corresponding project-local build directory was writable.

Build A passed in 9m49.915s with 281.9 MiB peak memory and zero swap. Build B
passed in 9m45.171s with 287.1 MiB peak memory and zero swap. Both emitted only
the same optional-component warnings and Wine's pre-existing WRC parser
conflicts; the modified WineUSB units emitted no warning. Their generated
Makefiles are byte-identical. Raw `config.log` files differ only in GCC's
random temporary object basenames; normalizing those basenames makes the logs
identical.

## Byte reproducibility

All three candidate outputs compare byte-for-byte between A and B:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  (2,560 bytes)
404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  wineusb.sys.so                  (192,528 bytes)
d5cbdf21f773488523c16bec90af8d83f9c7a9464afc39dceefdea16e399edbc  wineusb.so                      (92,760 bytes)
```

The Windows builtin build ID is
`e599b02a315eeee14ddf1285d1d995cde15f43c7`; the Unix library build ID is
`e5c7e3e325da2f891f5ffd389d08baa725f91487` in both builds. The unchanged fake
PE hash also matches the prior USB-DI and CP6 development builds, as expected.

## Independent contract results

Build A and build B were each tested in a separate USB-hidden, networkless
Bubblewrap namespace. Both passed:

- the fake-libusb behavioral contract, including exact setup construction,
  short completion, cancellation, STALL, overrun, cleanup, and ten fail-closed
  rejection cases;
- the class-interface-IN source/binary contract; and
- the existing USB-DI v1 contract.

The one error-level line in each run is the contract's deliberate immediate
submit-error injection, not a test failure. Exact summarized outputs are:

```text
3fdc493f07c2698fc40ee4b8c5dc61d4fdda0e4ca7f9f82b054f6bc88e05e483  logs/cp7-build-a.log
8f34ee8c4b12649648f50c03b1577dfbecb466b2cba76e6ac9d5836b88043ded  logs/cp7-build-b.log
8513c0bf8e9cd9445519ad60faf2d714cbeb9033ec5f5ce191850f7fd3b5c141  logs/cp7-contract-a.log
005a0e1a16df489ef6ad62b64d72ca36a01fb5b353334c2a7ada02f30b34ffd5  logs/cp7-contract-b.log
88635edfebc9cafa3f8a2b70dd2d964c707b1690770bddfe54863d396f1a70eb  logs/cp7-seal.log
```

A final combined seal reran both complete contract suites against both clean
builds in one fresh USB-hidden namespace. It passed in 4.002 seconds with
21.6 MiB peak memory and zero swap.

## Safety state and next pause

Postflight found zero connected `194f:0422` devices and no Wine, Wine server,
Xvfb, or candidate UC process. The only matching running user unit was the
pre-existing `io24-crashwatch.service`; no build or contract unit survived.
The protected prefix retained inode 3427833 and timestamp
`2026-08-12 00:31:35.825186221 -0700`. The active observation capture remained
SHA-256 `f7ae3a97696dfd1ceff7b511c307d054422250e481deceb7b180167538762a67`.

No candidate artifact has been copied into the versioned staging directory,
no sandbox has been cloned or changed, and the harness still pins observation
v2. CP8 may begin only by copying this exact reproduced triplet, updating the
offline hash contracts, cloning rather than reusing prior evidence, and
running one USB-hidden `driver-load`. A device is unnecessary. Live USB,
class OUT, select-interface semantics, claims/detach, alternate settings,
timeout changes, full Universal Control, Voice FX, and the protected prefix
remain outside the authorization.
