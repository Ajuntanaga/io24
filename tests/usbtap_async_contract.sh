#!/usr/bin/env bash
set -euo pipefail

io24_project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
io24_build_dir="$(mktemp -d -p /tmp io24-usbtap-contract.XXXXXX)"
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

cc -std=c11 -Wall -Wextra -Werror -shared -fPIC \
    -DIO24_FAKE_LIBUSB \
    "$io24_project_dir/tests/usbtap_async_contract.c" \
    -o "$io24_build_dir/libio24_fakeusb.so"

cc -std=c11 -Wall -Wextra -Werror \
    "$io24_project_dir/tests/usbtap_async_contract.c" \
    -L"$io24_build_dir" -Wl,-rpath,'$ORIGIN' -lio24_fakeusb \
    -o "$io24_build_dir/usbtap_async_contract"

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

io24_log="$io24_build_dir/completed.txt"
IO24_FAKE_LIBUSB_MODE=completed IO24_USBLOG="$io24_log" \
    LD_PRELOAD="$io24_tap" \
    "$io24_build_dir/usbtap_async_contract" completed

mapfile -t io24_lines < <(grep -v '^#' "$io24_log")
if (( ${#io24_lines[@]} != 2 )); then
    printf 'FAIL: expected one submit and one completion record, found %d\n' \
        "${#io24_lines[@]}" >&2
    printf '%s\n' "${io24_lines[@]}" >&2
    exit 1
fi

read -r io24_submit_id _ io24_submit_event io24_submit_pipe \
    io24_submit_status io24_submit_length io24_submit_marker \
    io24_submit_hex1 io24_submit_hex2 io24_submit_extra \
    <<< "${io24_lines[0]}"
read -r io24_complete_id _ io24_complete_event io24_complete_pipe \
    io24_complete_status io24_complete_length io24_complete_marker \
    io24_complete_hex io24_complete_extra \
    <<< "${io24_lines[1]}"

if [[ "$io24_submit_event" != S || "$io24_submit_pipe" != Ci:1:004:00 ||
      "$io24_submit_status" != -115 || "$io24_submit_length" != 8 ||
      "$io24_submit_marker" != = ||
      "$io24_submit_hex1$io24_submit_hex2" != 8006000100000400 ||
      -n "${io24_submit_extra:-}" ]]; then
    printf 'FAIL: malformed async control submit record: %s\n' \
        "${io24_lines[0]}" >&2
    exit 1
fi

if [[ "$io24_complete_id" != "$io24_submit_id" ||
      "$io24_complete_event" != C || "$io24_complete_pipe" != Ci:1:004:00 ||
      "$io24_complete_status" != 0 || "$io24_complete_length" != 4 ||
      "$io24_complete_marker" != = || "$io24_complete_hex" != 12010003 ||
      -n "${io24_complete_extra:-}" ]]; then
    printf 'FAIL: malformed async control completion record: %s\n' \
        "${io24_lines[1]}" >&2
    exit 1
fi

if ! grep -Eq '^# usbtap pid=[0-9]+ tid=[0-9]+ transfer=ffff8800[0-9a-f]{8} event=S$' \
        "$io24_log" ||
   ! grep -Eq '^# usbtap pid=[0-9]+ tid=[0-9]+ transfer=ffff8800[0-9a-f]{8} event=C$' \
        "$io24_log" ||
   ! grep -Eq '^# usbtap pid=[0-9]+ tid=[0-9]+ event=H-enter$' \
        "$io24_log" ||
   ! grep -Eq '^# usbtap pid=[0-9]+ tid=[0-9]+ event=H-return status=0$' \
        "$io24_log"; then
    printf 'FAIL: PID/TID or event-loop lifecycle evidence is missing\n' >&2
    cat "$io24_log" >&2
    exit 1
fi

io24_log="$io24_build_dir/stall.txt"
IO24_FAKE_LIBUSB_MODE=stall IO24_USBLOG="$io24_log" \
    LD_PRELOAD="$io24_tap" \
    "$io24_build_dir/usbtap_async_contract" stall
mapfile -t io24_lines < <(grep -v '^#' "$io24_log")
if (( ${#io24_lines[@]} != 2 )) ||
   [[ "${io24_lines[0]}" != *" S Ci:1:004:00 -115 8 = 80060001 00000400" ||
      "${io24_lines[1]}" != *" C Ci:1:004:00 4 0" ]]; then
    printf 'FAIL: async STALL was not preserved as a callback status\n' >&2
    printf '%s\n' "${io24_lines[@]}" >&2
    exit 1
fi

io24_log="$io24_build_dir/submit-error.txt"
IO24_FAKE_LIBUSB_MODE=submit-error IO24_USBLOG="$io24_log" \
    LD_PRELOAD="$io24_tap" \
    "$io24_build_dir/usbtap_async_contract" submit-error
mapfile -t io24_lines < <(grep -v '^#' "$io24_log")
if (( ${#io24_lines[@]} != 2 )) ||
   [[ "${io24_lines[0]}" != *" S Ci:1:004:00 -115 8 = 80060001 00000400" ||
      "${io24_lines[1]}" != *" E Ci:1:004:00 -6 0" ]]; then
    printf 'FAIL: immediate submit error was not recorded separately\n' >&2
    printf '%s\n' "${io24_lines[@]}" >&2
    exit 1
fi

io24_log="$io24_build_dir/event-block.txt"
set +e
IO24_FAKE_LIBUSB_MODE=event-block IO24_USBLOG="$io24_log" \
    LD_PRELOAD="$io24_tap" \
    timeout --signal=TERM --kill-after=1s 1s \
    "$io24_build_dir/usbtap_async_contract" event-block
io24_block_status=$?
set -e
if (( io24_block_status != 124 )); then
    printf 'FAIL: blocking event handler returned status %d, expected 124\n' \
        "$io24_block_status" >&2
    exit 1
fi
if ! grep -Eq '^# usbtap pid=[0-9]+ tid=[0-9]+ event=H-enter$' \
        "$io24_log" ||
   grep -Eq '^# usbtap .* event=H-return' "$io24_log"; then
    printf 'FAIL: blocked event pump was not represented by a lone H-enter\n' >&2
    cat "$io24_log" >&2
    exit 1
fi

printf 'usbtap async control contract: pass\n'
