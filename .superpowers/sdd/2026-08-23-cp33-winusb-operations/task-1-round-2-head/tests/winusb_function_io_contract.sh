#!/usr/bin/env bash
set -uo pipefail
if (( $# < 1 || $# > 2 )); then echo 'usage: tests/winusb_function_io_contract.sh WINE_SOURCE_ROOT [MODE]' >&2; exit 2; fi
readonly source_root=$1 mode=${2:---red}
case "$mode" in --red|--lifecycle|--session|--alternate|--policy|--transfer) ;; *) echo "usage: unsupported MODE: $mode" >&2; exit 2;; esac
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for input in "$source_root/dlls/winusb.sys/main.c" "$source_root/dlls/wineusb.sys/winusb_busif.h" "$test_dir/winusb_function_io_contract.c" "$test_dir/winusb_function_binding_contract.c"; do [[ -f "$input" ]] || { echo "HARNESS: missing input: $input" >&2; exit 2; }; done
build_dir=$(mktemp -d -p /tmp io24-winusb-function-io.XXXXXX) || { echo 'HARNESS: mktemp failed' >&2; exit 2; }
trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM
if ! cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ -I"$test_dir" -I"$source_root/include" -I"$source_root/dlls/winusb.sys" -I"$source_root/dlls/wineusb.sys" "$test_dir/winusb_function_io_contract.c" -o "$build_dir/contract"; then echo 'HARNESS: compiling actual winusb.sys fake-WDM contract failed' >&2; exit 2; fi
"$build_dir/contract" "$mode"; code=$?
(( code == 0 || code == 1 )) || { echo "HARNESS: function contract exited $code" >&2; exit 2; }
exit "$code"
