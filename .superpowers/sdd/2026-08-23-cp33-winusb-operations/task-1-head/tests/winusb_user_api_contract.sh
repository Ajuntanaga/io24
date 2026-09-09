#!/usr/bin/env bash
set -euo pipefail
if (( $# < 1 || $# > 2 )); then echo 'usage: tests/winusb_user_api_contract.sh WINE_SOURCE_ROOT [MODE]' >&2; exit 2; fi
readonly source_root=$1 mode=${2:---red}
[[ "$mode" == --red || "$mode" == --api ]] || { echo "usage: unsupported MODE: $mode" >&2; exit 2; }
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for input in "$source_root/include/winusb.h" "$source_root/dlls/winusb/main.c" "$source_root/dlls/winusb/winusb.spec" "$test_dir/winusb_user_api_contract.c"; do
    [[ -f "$input" ]] || { echo "HARNESS: missing input: $input" >&2; exit 2; }
done
build_dir=$(mktemp -d -p /tmp io24-winusb-user-api.XXXXXX)
trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM
cc -std=c11 -Wall -Wextra -Werror -D__WINESRC__ -I"$source_root/include" -c "$source_root/dlls/winusb/main.c" -o "$build_dir/main.o"
cc -std=c11 -Wall -Wextra -Werror "$test_dir/winusb_user_api_contract.c" -o "$build_dir/contract"
"$build_dir/contract" "$source_root"
