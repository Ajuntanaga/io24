# Android Read-Only Probe Build

Built and verified offline on 2026-09-22.

## Result

- Artifact: `app/build/outputs/apk/debug/app-debug.apk`
- SHA-256: `f415bc4af06e18eda3691ba4a0a21cbebb9e56c840d1291f403166062336ef17`
- Package: `dev.ajuntanaga.io24`
- Version: `0.1.0` (`versionCode` 1)
- Android range: API 23 minimum, API 35 target
- Signing: Android debug certificate, APK signature schemes v1 and v2 verified

## Verification

- Host protocol and safety contracts: 7 passed
- Java unit tests: passed
- Android lint: no issues found
- Debug APK assembly: passed
- Manifest permission audit: no requested permissions; USB host feature only
- Source and APK entry privacy scan: no workstation paths found

The build used the versions and checksums pinned in `toolchain.lock.json`.
`./verify.sh` ran Gradle in offline mode.

No APK installation, USB access, phone operation, or io24 operation occurred
during this offline build. A later, separately authorized hardware test is
recorded in `LIVE_TEST_REPORT.md`.
