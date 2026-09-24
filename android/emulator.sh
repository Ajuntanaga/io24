#!/bin/sh
set -eu

ANDROID_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SDK="$ANDROID_DIR/.toolchain/android-sdk"
AVD_HOME="$ANDROID_DIR/.toolchain/avd"
ADB="$SDK/platform-tools/adb"
EMULATOR="$SDK/emulator/emulator"
APK="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
AVD_NAME=io24_blu_api35
SERIAL=emulator-5556
COMPONENT=dev.ajuntanaga.io24/.MainActivity
SIMULATED_EXTRA=dev.ajuntanaga.io24.SIMULATED_IO24
FAILURE_EXTRA=dev.ajuntanaga.io24.SIMULATED_READBACK_FAILURE
DELAY_96_EXTRA=dev.ajuntanaga.io24.SIMULATED_DELAY_96

require_file() {
    if [ ! -e "$1" ]; then
        echo "Missing required local file: $1" >&2
        exit 2
    fi
}

start_emulator() {
    require_file "$EMULATOR"
    require_file "$AVD_HOME/$AVD_NAME.ini"

    alias_dir=$(mktemp -d "${TMPDIR:-/tmp}/io24-android-emulator.XXXXXX")
    cleanup() {
        [ ! -L "$alias_dir/sdk" ] || unlink "$alias_dir/sdk"
        [ ! -L "$alias_dir/avd" ] || unlink "$alias_dir/avd"
        rmdir "$alias_dir"
    }
    trap cleanup EXIT HUP INT TERM
    ln -s "$SDK" "$alias_dir/sdk"
    ln -s "$AVD_HOME" "$alias_dir/avd"

    ANDROID_SDK_ROOT="$alias_dir/sdk" \
    ANDROID_HOME="$alias_dir/sdk" \
    ANDROID_AVD_HOME="$alias_dir/avd" \
        "$alias_dir/sdk/emulator/emulator" \
        -avd "$AVD_NAME" \
        -port 5556 \
        -no-window \
        -no-audio \
        -no-boot-anim \
        -no-snapshot \
        -gpu swiftshader_indirect \
        -cores 2
}

wait_for_boot() {
    "$ADB" -s "$SERIAL" wait-for-device
    attempt=0
    while [ "$("$ADB" -s "$SERIAL" shell getprop sys.boot_completed)" != 1 ]; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 60 ]; then
            echo "Emulator did not finish booting within 60 seconds." >&2
            exit 3
        fi
        sleep 1
    done
}

install_apk() {
    require_file "$ADB"
    require_file "$APK"
    wait_for_boot
    "$ADB" -s "$SERIAL" install -r -t "$APK"
}

launch_simulation() {
    require_file "$ADB"
    scenario=${1:-verified}
    case "$scenario" in
        verified)
            "$ADB" -s "$SERIAL" shell am start -S -W \
                -n "$COMPONENT" \
                --ez "$SIMULATED_EXTRA" true
            ;;
        failure)
            "$ADB" -s "$SERIAL" shell am start -S -W \
                -n "$COMPONENT" \
                --ez "$SIMULATED_EXTRA" true \
                --ez "$FAILURE_EXTRA" true
            ;;
        delay96)
            "$ADB" -s "$SERIAL" shell am start -S -W \
                -n "$COMPONENT" \
                --ez "$SIMULATED_EXTRA" true \
                --ez "$DELAY_96_EXTRA" true
            ;;
        *)
            echo "Simulation must be 'verified', 'failure', or 'delay96'." >&2
            exit 4
            ;;
    esac
}

case "${1:-}" in
    start)
        start_emulator
        ;;
    install)
        install_apk
        ;;
    simulate)
        launch_simulation "${2:-verified}"
        ;;
    plain)
        require_file "$ADB"
        "$ADB" -s "$SERIAL" shell am start -S -W -n "$COMPONENT"
        ;;
    status)
        require_file "$ADB"
        "$ADB" -s "$SERIAL" shell getprop sys.boot_completed
        ;;
    stop)
        require_file "$ADB"
        "$ADB" -s "$SERIAL" emu kill
        ;;
    *)
        echo "Usage: $0 {start|install|simulate [verified|failure|delay96]|plain|status|stop}" >&2
        exit 1
        ;;
esac
