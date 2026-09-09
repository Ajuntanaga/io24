# WineUSB pipe-observe v3 manifest

## Current state

CP17 is complete. The observation-only patch has a contained test-first
development build plus two independent byte-identical clean builds. No
candidate binary is staged yet.

## Pinned base and patch order

Apply these inputs in order to the Wine 11.15 archive:

    5046f36dae210b198ea69792774d4401feed975d465eca6c251c9394400ec272  /home/ajuntanaga/.cache/io24/builds/wine-11.15-usbdi/downloads/wine-11.15.tar.xz
    9e1c3b88a428e3bdd245ee5cdda9dfa423e77ad4abe08c7423bf14dceb073e91  re/wine-11.15-wineusb-usbdi-v1.patch
    ad260f9ab4a1bc138d8ee3fdd7ec3157e0caf8d6a67b490be4bd815092fa5e64  re/wine-11.15-wineusb-urb-observe-v2.patch
    461f68de736ddba876cfaa4d0e385c8eaa0002bd22df05932987ad3f4fe7fe8f  re/wine-11.15-wineusb-class-interface-range-v2.patch
    ce4507d1b789e87195965b71e88c76d02a7de5ab504b52d41e1c431c560d949d  re/wine-11.15-wineusb-pipe-observe-v3.patch

All patches require `patch --batch --forward --fuzz=0 -p1`.

## CP16 source and contract

Changed source hashes:

    ab94b70ceae65eee5019e053c9bf7ec3ce01f20af2a3e824282fbbc3d786785c  dlls/wineusb.sys/wineusb.c
    a54e499c8119282448b8854ed729ec6703b67d30342ad74cd79fc43130e22f44  dlls/wineusb.sys/unixlib.c

Contract hashes:

    e67031f0ccf9198e1ceb13d485f6bba0ee7a883ebd4fed6aefefd4b19ab2352d  tests/wineusb_pipe_observe_contract.c
    315982cd76594ac91840434171ed529f8ed6f3293892f0efd0315c27cab96e3a  tests/wineusb_pipe_observe_contract.sh
    ae19b4281d45925bce9a782b0565f8a9277c29b8a38a309dbd5a474e1746d714  tests/wineusb_pipe_observe_fake_libusb.c

The valid RED and final GREEN outputs, regression results, patch application,
and bounded development build evidence are under `logs/` and sealed by
`checkpoints/CP16_SHA256SUMS`.

## Development outputs only

These files remain under `.io24-build/wineusb-pipe-observe-v3/dev-build/` and
are not staged:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    90d060571d9f8a56aea8d91485802fe500920f741fb5787543a8c141ae104eb9  wineusb.so

## CP17 reproducible clean outputs

Build A and B independently produced the same triplet:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys  (2,560 bytes)
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so                  (202,392 bytes)
    90d060571d9f8a56aea8d91485802fe500920f741fb5787543a8c141ae104eb9  wineusb.so                      (92,328 bytes)

The full source trees, configure/build output, generated Makefile, compile
database, and candidate artifacts compare identical. Both sides pass the new
pipe-observe contract and every retained contract. Exact evidence is in
`checkpoints/CP17_REPRODUCIBLE_BUILDS.md`,
`logs/cp17-artifact-comparison.txt`, and the raw logs under
`.io24-build/wineusb-pipe-observe-v3/logs/`.

## Gate

Next: stage only the exact CP17 triplet, update and test the hash-pinned harness
selector, clone a fresh disposable sandbox, pass a USB-hidden driver-load, and
then use the user's authorization for one bounded live diagnostic. Never touch
the protected `.wine-io24` prefix, and pause safely at 10% battery or lower.
