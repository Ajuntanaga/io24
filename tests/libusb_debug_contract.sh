#!/usr/bin/env bash
set -euo pipefail

io24_project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
io24_harness="$io24_project_dir/tests/uc_wine_sandbox.sh"
io24_build_dir="$(mktemp -d -p /tmp io24-libusb-debug.XXXXXX)"
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

io24_debug_count=$(grep -Fc -- '--setenv LIBUSB_DEBUG 4' "$io24_harness" || true)
if (( io24_debug_count != 1 )); then
    printf 'FAIL: expected one live-read LIBUSB_DEBUG setting, found %d\n' \
        "$io24_debug_count" >&2
    exit 1
fi

if ! grep -Fq '[[ "${LIBUSB_DEBUG:-}" == 4 ]]' "$io24_harness"; then
    printf 'FAIL: inner live-read does not fail closed on debug level\n' >&2
    exit 1
fi

if ! awk '
    /^if \[\[ "\$mode" == live-read \]\]; then$/ { live_read = 1; next }
    live_read && /^fi$/ { live_read = 0 }
    live_read && /--setenv LIBUSB_DEBUG 4/ { found++ }
    END { exit found == 1 ? 0 : 1 }
' "$io24_harness"; then
    printf 'FAIL: LIBUSB_DEBUG is not scoped to the live-read block\n' >&2
    exit 1
fi

cc -std=c11 -Wall -Wextra -Werror \
    "$io24_project_dir/tests/libusb_debug_contract.c" -ldl \
    -o "$io24_build_dir/libusb_debug_contract"

if [[ -n "${IO24_USBTAP_ARTIFACT:-}" ]]; then
    [[ -f "$IO24_USBTAP_ARTIFACT" && ! -L "$IO24_USBTAP_ARTIFACT" ]] || {
        printf 'FAIL: IO24_USBTAP_ARTIFACT is not a regular file\n' >&2
        exit 1
    }
    cp -- "$IO24_USBTAP_ARTIFACT" "$io24_build_dir/usbtap.so"
    cmp -s -- "$IO24_USBTAP_ARTIFACT" "$io24_build_dir/usbtap.so" || {
        printf 'FAIL: staged artifact copy differs from its source\n' >&2
        exit 1
    }
else
    cc -std=c11 -Wall -Wextra -Werror -shared -fPIC -O2 \
        "$io24_project_dir/tests/usbtap.c" -ldl \
        -o "$io24_build_dir/usbtap.so"
fi

timeout --signal=TERM --kill-after=2s 10s \
    bwrap \
    --die-with-parent \
    --unshare-net \
    --unshare-pid \
    --unshare-ipc \
    --unshare-uts \
    --ro-bind /usr /usr \
    --symlink usr/bin /bin \
    --symlink usr/lib /lib \
    --symlink usr/lib64 /lib64 \
    --proc /proc \
    --dev /dev \
    --tmpfs /sys \
    --tmpfs /run \
    --tmpfs /home \
    --tmpfs /tmp \
    --bind "$io24_build_dir" /run/io24-libusb-debug \
    --setenv HOME /home/io24-isolated \
    --setenv LANG C \
    --setenv LIBUSB_DEBUG 4 \
    --setenv IO24_USBLOG /run/io24-libusb-debug/durable.log \
    --setenv LD_PRELOAD /run/io24-libusb-debug/usbtap.so \
    /run/io24-libusb-debug/libusb_debug_contract \
    >"$io24_build_dir/stdout.log" \
    2>"$io24_build_dir/libusb-debug.log"

grep -Fq 'isolated libusb debug lifecycle: pass' "$io24_build_dir/stdout.log" || {
    printf 'FAIL: isolated libusb lifecycle did not pass\n' >&2
    cat "$io24_build_dir/stdout.log" >&2
    cat "$io24_build_dir/libusb-debug.log" >&2
    exit 1
}

grep -Eq '^# usbtap pid=[0-9]+ tid=[0-9]+ event=R-init object=/.*/libusb-1\.0\.so\.0(\.[0-9]+)* symbol=libusb_init$' \
    "$io24_build_dir/durable.log" || {
    printf 'FAIL: real libusb initializer routing was not recorded\n' >&2
    cat "$io24_build_dir/durable.log" >&2
    exit 1
}

grep -Eq '^# usbtap pid=[0-9]+ tid=[0-9]+ event=L-global-installed$' \
    "$io24_build_dir/durable.log" || {
    printf 'FAIL: global libusb callback was not installed before init\n' >&2
    cat "$io24_build_dir/durable.log" >&2
    exit 1
}

grep -Fq 'libusb_init_context' "$io24_build_dir/durable.log" || {
    printf 'FAIL: dedicated callback did not capture libusb initialization\n' >&2
    cat "$io24_build_dir/durable.log" >&2
    exit 1
}

grep -Fq 'libusb_exit' "$io24_build_dir/durable.log" || {
    printf 'FAIL: dedicated callback did not capture libusb shutdown\n' >&2
    cat "$io24_build_dir/durable.log" >&2
    exit 1
}

if grep -Fq 'libusb:' "$io24_build_dir/libusb-debug.log"; then
    printf 'FAIL: native libusb logs escaped the dedicated callback sink\n' >&2
    cat "$io24_build_dir/libusb-debug.log" >&2
    exit 1
fi

printf 'libusb durable-log empty-device contract: pass\n'
