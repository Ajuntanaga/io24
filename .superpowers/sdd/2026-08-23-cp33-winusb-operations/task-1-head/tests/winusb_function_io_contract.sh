#!/usr/bin/env bash
set -euo pipefail
if (( $# < 1 || $# > 2 )); then echo 'usage: tests/winusb_function_io_contract.sh WINE_SOURCE_ROOT [MODE]' >&2; exit 2; fi
readonly source_root=$1 mode=${2:---red}
[[ "$mode" == --red || "$mode" == --session || "$mode" == --io ]] || { echo "usage: unsupported MODE: $mode" >&2; exit 2; }
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for input in "$source_root/dlls/winusb.sys/main.c" "$source_root/dlls/wineusb.sys/winusb_busif.h" "$test_dir/winusb_function_io_contract.c"; do
    [[ -f "$input" ]] || { echo "HARNESS: missing input: $input" >&2; exit 2; }
done
build_dir=$(mktemp -d -p /tmp io24-winusb-function-io.XXXXXX)
trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ -I"$source_root/include" -I"$source_root/dlls/winusb.sys" -I"$source_root/dlls/wineusb.sys" -c "$source_root/dlls/winusb.sys/main.c" -o "$build_dir/main.o"
cc -std=c11 -Wall -Wextra -Werror "$test_dir/winusb_function_io_contract.c" -o "$build_dir/contract"
"$build_dir/contract" "$source_root"
