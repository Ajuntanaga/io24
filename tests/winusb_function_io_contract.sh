#!/usr/bin/env bash
set -uo pipefail
if (( $# < 1 || $# > 2 )); then echo 'usage: tests/winusb_function_io_contract.sh WINE_SOURCE_ROOT [MODE]' >&2; exit 2; fi
readonly source_root=$1 mode=${2:---red}
case "$mode" in --red|--lifecycle|--initialize|--session|--alternate|--policy|--transfer|--control-descriptor|--sync-pipes) ;; *) echo "usage: unsupported MODE: $mode" >&2; exit 2;; esac
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sanitize_flags=()
if [[ "$mode" == --initialize ]]; then
    sanitize_flags=(-fsanitize=address,undefined,alignment -fno-sanitize-recover=all -fno-omit-frame-pointer)
fi
for input in "$source_root/dlls/winusb.sys/main.c" "$source_root/dlls/winusb.sys/session.c" "$source_root/dlls/winusb.sys/winusb_private.h" "$source_root/dlls/wineusb.sys/winusb_busif.h" "$test_dir/winusb_function_io_contract.c" "$test_dir/winusb_function_binding_contract.c"; do [[ -f "$input" ]] || { echo "HARNESS: missing input: $input" >&2; exit 2; }; done
transfer_sources=()
# Task 9 introduces transfer.c.  Its absence is the intentional feature RED;
# once present it must be part of the executable boundary, never merely scanned.
if [[ -f "$source_root/dlls/winusb.sys/transfer.c" ]]; then transfer_sources=("$source_root/dlls/winusb.sys/transfer.c"); fi
build_dir=$(mktemp -d -p /tmp io24-winusb-function-io.XXXXXX) || { echo 'HARNESS: mktemp failed' >&2; exit 2; }
trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM
if ! cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ "${sanitize_flags[@]}" -I"$test_dir" -I"$source_root/include" -I"$source_root/dlls/winusb.sys" -I"$source_root/dlls/wineusb.sys" "$test_dir/winusb_function_io_contract.c" "$source_root/dlls/winusb.sys/session.c" "${transfer_sources[@]}" -o "$build_dir/contract"; then echo 'HARNESS: compiling actual winusb.sys main/session/transfer fake-WDM contract failed' >&2; exit 2; fi
if [[ "$mode" == --initialize ]]; then
    ASAN_OPTIONS=halt_on_error=1:abort_on_error=0:exitcode=1:detect_leaks=1 \
        UBSAN_OPTIONS=halt_on_error=1:exitcode=1 \
        "$build_dir/contract" "$mode"; code=$?
else
    "$build_dir/contract" "$mode"; code=$?
fi
(( code == 0 || code == 1 )) || { echo "HARNESS: function contract exited $code" >&2; exit 2; }
exit "$code"
