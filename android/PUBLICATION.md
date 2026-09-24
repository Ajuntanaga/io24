# Public release boundary

The public [`Ajuntanaga/io24-android`](https://github.com/Ajuntanaga/io24-android)
repository contains the direct Android controller as an independent project.
It was separated from the companion
[`Ajuntanaga/io24`](https://github.com/Ajuntanaga/io24) Linux Host so each can
be developed and released without coupling their runtimes.

## Published source

The public tree contains the Android app, Java unit tests, protocol and source
contracts, Gradle wrapper, pinned toolchain record, design and test notes,
license, and hardware-free GitHub automation. `PUBLIC_FILES.txt` is the exact
allowlist. `tools/export_public.py` can copy only that list into a clean Git
checkout and can verify that no extra tracked files are present.

## Deliberately excluded

The public tree does not contain private Git history, agent work records, local
handoffs, USB or audio captures, device serials, account details, APKs, signing
keys, SDK or JDK archives, emulator images, caches, Universal Control
installers, vendor DLLs or firmware, decompiler output, named factory presets,
or recovered preset libraries.

The Gradle wrapper JAR is Gradle's standard bootstrap artifact and is pinned by
SHA-256 in `toolchain.lock.json`. The app includes one neutral 1,028-byte
native-slot structural template needed to construct supported device records.
It is not a named factory preset or a preset library.

## Reproducible checks

From a clean checkout:

```sh
python3 -m pip install 'pytest>=7,<10'
python3 -m pytest -q tests
./gradlew --no-daemon testDebugUnitTest lintDebug assembleDebug
python3 tools/export_public.py /path/to/clean/io24-android-checkout --check
git grep -nE 'github_pat_|ghp_|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY'
```

GitHub Actions runs the same source, unit, lint, assembly, and CodeQL checks
without accessing hardware. Live USB, audio, firmware, and device-preset tests
are separate authorized work and are never a CI requirement.
