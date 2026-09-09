#!/usr/bin/env bash
set -uo pipefail
if (( $# < 1 || $# > 2 )); then echo 'usage: tests/winusb_user_api_contract.sh WINE_SOURCE_ROOT [MODE]' >&2; exit 2; fi
readonly source_root=$1 mode=${2:---red}
case "$mode" in --red|--initialize|--handles|--descriptors|--policy|--transfer|--cancel|--vendor) ;; *) echo "usage: unsupported MODE: $mode" >&2; exit 2;; esac
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for input in "$source_root/include/winusb.h" "$source_root/dlls/winusb/main.c" "$source_root/dlls/winusb/winusb.spec" "$test_dir/winusb_user_api_contract.c"; do [[ -f "$input" ]] || { echo "HARNESS: missing input: $input" >&2; exit 2; }; done
build_dir=$(mktemp -d -p /tmp io24-winusb-user-api.XXXXXX) || { echo 'HARNESS: mktemp failed' >&2; exit 2; }
trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM
sources=("$source_root/dlls/winusb/main.c"); [[ ! -f "$source_root/dlls/winusb/io.c" ]] || sources+=("$source_root/dlls/winusb/io.c")
if ! cc -std=c11 -Wall -Wextra -Werror -fPIC -shared -D__WINESRC__ -I"$source_root/include" "${sources[@]}" -o "$build_dir/winusb-production.so"; then echo 'HARNESS: compiling/linking actual winusb production module failed' >&2; exit 2; fi
if ! cc -std=c11 -Wall -Wextra -Werror -rdynamic -D__WINESRC__ -I"$source_root/include" "$test_dir/winusb_user_api_contract.c" -ldl -o "$build_dir/contract"; then echo 'HARNESS: compiling public host contract failed' >&2; exit 2; fi
"$build_dir/contract" "$build_dir/winusb-production.so" "$mode"; code=$?
(( code == 0 || code == 1 )) || { echo "HARNESS: public contract exited $code" >&2; exit 2; }
exit "$code"
