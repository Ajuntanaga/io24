#!/usr/bin/env bash
set -euo pipefail

io24_project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
io24_harness="$io24_project_dir/tests/uc_wine_sandbox.sh"
io24_build_dir="$(mktemp -d -p /tmp io24-usbtap-log-contract.XXXXXX)"
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

cc -std=c11 -Wall -Wextra -Werror -shared -fPIC \
    -DIO24_FAKE_LIBUSB_LOG \
    "$io24_project_dir/tests/usbtap_log_contract.c" \
    -o "$io24_build_dir/libio24_fakeusb_log.so"

cc -std=c11 -Wall -Wextra -Werror \
    "$io24_project_dir/tests/usbtap_log_contract.c" \
    -L"$io24_build_dir" -Wl,-rpath,'$ORIGIN' -lio24_fakeusb_log \
    -o "$io24_build_dir/usbtap_log_contract"

if [[ -n "${IO24_USBTAP_ARTIFACT:-}" ]]; then
    [[ -f "$IO24_USBTAP_ARTIFACT" && ! -L "$IO24_USBTAP_ARTIFACT" ]] || {
        printf 'FAIL: IO24_USBTAP_ARTIFACT is not a regular file\n' >&2
        exit 1
    }
    io24_tap="$io24_build_dir/usbtap-artifact.so"
    cp -- "$IO24_USBTAP_ARTIFACT" "$io24_tap"
    cmp -s -- "$IO24_USBTAP_ARTIFACT" "$io24_tap" || {
        printf 'FAIL: staged artifact copy differs from its source\n' >&2
        exit 1
    }
else
    io24_tap="$io24_build_dir/usbtap.so"
    cc -std=c11 -Wall -Wextra -Werror -shared -fPIC -O2 \
        "$io24_project_dir/tests/usbtap.c" -ldl \
        -o "$io24_tap"
fi

read -r io24_tap_hash _ < <(sha256sum -- "$io24_tap")
mapfile -t io24_pinned_hashes < <(
    sed -n 's/^readonly USBTAP_RESOLVER_V6_SHA256=//p' "$io24_harness"
)
if (( ${#io24_pinned_hashes[@]} != 1 )) ||
   [[ "${io24_pinned_hashes[0]:-}" != "$io24_tap_hash" ]]; then
    printf 'FAIL: resolver-v6 artifact and live harness hash pin differ\n' >&2
    exit 1
fi

io24_log="$io24_build_dir/durable.log"
io24_stdout="$io24_build_dir/stdout.log"
io24_stderr="$io24_build_dir/stderr.log"
IO24_USBLOG="$io24_log" LD_PRELOAD="$io24_tap" \
    "$io24_build_dir/usbtap_log_contract" \
    >"$io24_stdout" 2>"$io24_stderr"

rg -Fq 'durable libusb log probe: pass' "$io24_stdout" || {
    printf 'FAIL: durable log probe did not complete\n' >&2
    sed -n '1,120p' "$io24_stdout" >&2
    sed -n '1,120p' "$io24_stderr" >&2
    exit 1
}

if ! rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=L-global-installed$' \
        "$io24_log"; then
    printf 'FAIL: libusb global callback was not installed before init\n' >&2
    sed -n '1,160p' "$io24_log" >&2
    exit 1
fi

for io24_message in \
        '[fake] libusb init' \
        '[fake] libusb submit' \
        '[fake] libusb events'; do
    if ! rg -Fq "level=4 $io24_message" "$io24_log"; then
        printf 'FAIL: dedicated log is missing: %s\n' "$io24_message" >&2
        sed -n '1,160p' "$io24_log" >&2
        exit 1
    fi
done

if ! rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=R-submit object=.*libio24_fakeusb_log\.so symbol=libusb_submit_transfer$' \
        "$io24_log"; then
    printf 'FAIL: real submit symbol routing was not recorded\n' >&2
    sed -n '1,160p' "$io24_log" >&2
    exit 1
fi

if rg -Fq '[fake] libusb' "$io24_stderr"; then
    printf 'FAIL: native logs escaped the dedicated callback sink\n' >&2
    sed -n '1,160p' "$io24_stderr" >&2
    exit 1
fi

if ! rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=H-enter$' "$io24_log" ||
   ! rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=H-return status=0$' "$io24_log" ||
   ! rg -q '^ffff8800[0-9a-f]{8} [0-9]+ S Ci:1:004:00 -115 8 = 80060001 00000400$' "$io24_log" ||
   ! rg -q '^ffff8800[0-9a-f]{8} [0-9]+ C Ci:1:004:00 0 4 = 12010003$' "$io24_log"; then
    printf 'FAIL: durable logging changed the existing transfer/event contract\n' >&2
    sed -n '1,160p' "$io24_log" >&2
    exit 1
fi

printf 'usbtap durable libusb log contract: pass\n'
