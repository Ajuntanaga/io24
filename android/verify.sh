#!/bin/sh
set -eu

ANDROID_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(dirname -- "$ANDROID_DIR")
TOOLCHAIN_DIR="$ANDROID_DIR/.toolchain"

if [ -x "$TOOLCHAIN_DIR/jdk-17/bin/java" ]; then
    JAVA_HOME="$TOOLCHAIN_DIR/jdk-17"
    export JAVA_HOME
fi
if [ -d "$TOOLCHAIN_DIR/android-sdk" ]; then
    ANDROID_HOME="$TOOLCHAIN_DIR/android-sdk"
    ANDROID_SDK_ROOT="$TOOLCHAIN_DIR/android-sdk"
    ANDROID_USER_HOME="$TOOLCHAIN_DIR/android-user"
    export ANDROID_HOME ANDROID_SDK_ROOT ANDROID_USER_HOME
fi
if [ -d "$TOOLCHAIN_DIR/gradle-home" ]; then
    GRADLE_USER_HOME="$TOOLCHAIN_DIR/gradle-home"
    export GRADLE_USER_HOME
fi

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
    -q "$REPO_DIR/tests/test_android_probe_contract.py" \
    -p no:cacheprovider

if [ "${1:-}" = "--host-only" ]; then
    exit 0
fi

if [ -x "$TOOLCHAIN_DIR/gradle-8.11.1/bin/gradle" ]; then
    GRADLE="$TOOLCHAIN_DIR/gradle-8.11.1/bin/gradle"
elif [ -x "$ANDROID_DIR/gradlew" ]; then
    GRADLE="$ANDROID_DIR/gradlew"
elif command -v gradle >/dev/null 2>&1; then
    GRADLE=$(command -v gradle)
else
    echo "Android build unavailable: install the toolchain pinned in toolchain.lock.json." >&2
    echo "The host protocol and safety contracts passed." >&2
    exit 3
fi

cd "$ANDROID_DIR"
"$GRADLE" --offline --max-workers=1 --console=plain \
    clean testDebugUnitTest lintDebug assembleDebug

APK="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
if [ ! -s "$APK" ]; then
    echo "Android build completed without producing $APK" >&2
    exit 4
fi
sha256sum "$APK"
