# Contributing to io24 Controller for Android

Thanks for helping make the Revelator io24 useful from an Android phone.

Ordinary pull-request checks must stay hardware-free. They must not claim a USB
interface, write device state, change firmware, alter audio routing, or assume
that an io24 is attached. Run the source contracts first:

```sh
./verify.sh --host-only
```

For the complete local check, install the toolchain recorded in
`toolchain.lock.json`, then run:

```sh
./verify.sh
```

Live phone and interface tests belong in a separately authorized campaign.
Record the phone, Android version, app build, route, stimulus, restoration,
and exact result. A successful USB reply proves a write was accepted. It does
not prove audibility, stored-body readback, or cold-boot persistence.

Keep protocol commands typed and allowlisted. Do not add arbitrary parameter
or raw-record entry points to the UI. Do not add Universal Control installers,
vendor DLLs or firmware, device serials, local paths, captures, APKs, signing
keys, SDK archives, emulator images, or private work records. See
[`PUBLICATION.md`](PUBLICATION.md) for the repository boundary.
