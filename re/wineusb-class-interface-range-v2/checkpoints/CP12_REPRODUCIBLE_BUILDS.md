# CP12 — independent clean builds are reproducible

Reached at 2026-08-21T03:14:22-07:00. This is the hard pause after clean-build
reproducibility and before any v2 artifact staging, harness selector change,
sandbox clone, driver load, or live device run.

## Outcome

PASS, offline only. Two fresh source trees were independently extracted from
the retained Wine 11.15 archive. USB-DI v1, observation v2, and exact captured
RANGE v2 were applied in order with fuzz zero. The complete 12,445-file source
trees compare identical and contain no symbolic links or patch leftovers.

Both sources were configured and built independently under the same virtual
paths and reproducible environment. Each used a fresh build directory,
SOURCE_DATE_EPOCH=1787101002, pinned Bison/M4/libusb inputs, and make -j1.
Bubblewrap hid hardware and networking; resource ceilings and idle scheduling
kept the operation bounded.

## Byte-identical outputs

All candidate outputs compare byte-for-byte between build A and build B:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  (2,560 bytes)
    404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  wineusb.sys.so                  (192,528 bytes)
    9518320f495ace5cabc27ef4e740f182b3840700fba3e9371b36b7e12538dea2  wineusb.so                      (89,680 bytes)

The shared builtin build ID is
e599b02a315eeee14ddf1285d1d995cde15f43c7. The shared Unix-library build ID
is 8bf9a581c36824d5df469ab6ccc9a38974aab73a. Generated Makefiles and
compile_commands.json also compare byte-for-byte.

## Independent contract results

Build A and B were each tested in a separate hardware-hidden, networkless
Bubblewrap namespace. Both passed:

- the compiled fake-libusb exact-RANGE behavioral contract;
- the exact-RANGE source/binary fail-closed contract; and
- the retained WineUSB USB-DI V1 contract.

Each contract invocation exited zero in 0.29 seconds, peaked below 38 MiB RSS,
and used zero swap.

## Evidence

Detailed source/build, contract, and artifact-comparison summaries are:

    ../logs/cp12-source-build.txt
    ../logs/cp12-contracts.txt
    ../logs/cp12-artifact-comparison.txt

Raw configure, build, resource, and contract logs plus both independent trees
remain under:

    .io24-build/wineusb-class-interface-range-v2/

CP11 was frozen before advancing the active manifest. Its original manifest
is preserved byte-for-byte as ../CP11_MANIFEST_SNAPSHOT.md and CP11 verifies
against that snapshot.

The 48-entry checkpoint seal is CP12_SHA256SUMS in this directory.

## Safety state and next gate

No v2 binary is staged. The harness remains byte-identical and continues to
pin class-IN v1. The protected .wine-io24 prefix retained inode 3427833 and
timestamp 2026-08-12 00:31:35.825186221 -0700.

The next candidate is an explicit offline staging gate: copy only this exact
reproduced triplet into a versioned v2 directory, update and hash-pin the
sandbox selector, clone a fresh disposable sandbox, and perform a USB-hidden
driver-load validation. That work has not been performed here.

This checkpoint authorizes no live Wine run, device-node access, interface
claim or detach, alternate setting, class OUT, USB write, full Universal
Control, Voice FX, or protected-prefix access. The earlier one-run live-read
authorization remains consumed.
