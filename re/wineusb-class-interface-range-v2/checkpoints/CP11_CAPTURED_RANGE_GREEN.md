# CP11 — exact captured RANGE contract GREEN offline

Reached at `2026-08-21T02:56:27-07:00`.

The captured 50-byte UAC2 Clock Source RANGE response is now implemented for
only the exact PaeDSPUSB class-interface-IN tuple. The backend returns it
synchronously with success and performs zero libusb or device operations.
Every altered tuple remains fail-closed, and select-interface is unchanged and
unimplemented.

Strict RED/GREEN evidence is preserved under `../logs/`. The v2 test failed in
eight expected ways against the preserved v1 build, then passed against the
minimal v2 development build. USB-DI v1 also passed. Both GREEN suites were
rerun with hardware, host home, `/sys`, and networking hidden.

The v2 patch SHA-256 is:

    461f68de736ddba876cfaa4d0e385c8eaa0002bd22df05932987ad3f4fe7fe8f

It applies with fuzz zero to the pre-class-IN Wine 11.15 + USB-DI v1 +
observation-v2 baseline and reproduces all changed source files byte-for-byte.
No v2 binary is staged, the harness still selects the sealed v1 triplet, and
the v1 development workspace was restored after patch extraction.

Next: independent clean A/B builds and contract comparison, offline only.
This checkpoint grants no live-run or hardware authorization.
