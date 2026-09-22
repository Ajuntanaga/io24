# Android Bounded Controller Build

Built and verified offline on 2026-09-22.

## Result

- Artifact: `app/build/outputs/apk/debug/app-debug.apk`
- SHA-256: `164b4c48b23f8df03e9b96023dff822415b19d1112f836dbf5371e229d28f3cf`
- Package: `dev.ajuntanaga.io24`
- Version: `0.2.0` (`versionCode` 2)
- Android range: API 23 minimum, API 35 target
- Signing: Android debug certificate, APK signature schemes v1 and v2 verified

## Verification

- Host protocol and safety contracts: 9 passed
- Java unit tests: passed
- Android lint: no issues found
- Debug APK assembly: passed
- Manifest permission audit: no requested permissions; USB host feature only
- Source and APK entry privacy scan: no workstation paths found

The build used the versions and checksums pinned in `toolchain.lock.json`.
`./verify.sh` ran Gradle in offline mode.

Version 0.2.0 adds only the fixed Input 2 mute record and mandatory fresh-state
readback. No APK installation, USB access, phone operation, or io24 operation
occurred during this offline build. `LIVE_TEST_REPORT.md` records the earlier
authorized read-only 0.1.0 hardware test; it does not validate this write path.
