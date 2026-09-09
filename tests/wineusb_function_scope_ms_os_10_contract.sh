#!/usr/bin/env bash
set -euo pipefail

if (( $# != 4 )); then
    echo "usage: tests/wineusb_function_scope_ms_os_10_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT WINEUSB_UNIXLIB LIBUSB_INCLUDE" >&2
    exit 2
fi

readonly io24_wine_source=$1
readonly io24_wine_build=$2
readonly io24_wineusb_unixlib=$3
readonly io24_libusb_include=$4
readonly io24_test_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly io24_test_source="$io24_test_dir/wineusb_function_scope_contract.c"
readonly io24_fake_source="$io24_test_dir/wineusb_function_scope_fake_libusb.c"
readonly io24_ms_os_stub="$io24_test_dir/wineusb_ms_os_10_no_support_stub.c"
readonly io24_ntdll_dir="$io24_wine_build/dlls/ntdll"

for io24_required in \
        "$io24_test_source" \
        "$io24_fake_source" \
        "$io24_ms_os_stub" \
        "$io24_libusb_include/libusb.h" \
        "$io24_ntdll_dir/ntdll.so" \
        "$io24_wineusb_unixlib"; do
    [[ -f "$io24_required" ]] || {
        echo "FAIL: missing function-scope contract input: $io24_required" >&2
        exit 1
    }
done

io24_build_dir=$(mktemp -d -p /tmp io24-wineusb-function-scope-contract.XXXXXX)
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

cc -std=c11 -Wall -Wextra -Werror -fPIC -shared \
    -I"$io24_libusb_include" \
    -Wl,-soname,libusb-1.0.so.0 \
    "$io24_fake_source" \
    "$io24_ms_os_stub" \
    -o "$io24_build_dir/libusb-1.0.so.0"

cc -std=c11 -Wall -Wextra -Werror \
    -DWINE_UNIX_LIB -D__WINESRC__ \
    -I"$io24_libusb_include" \
    -I"$io24_wine_source/include" \
    -I"$io24_wine_source/dlls/wineusb.sys" \
    "$io24_test_source" \
    -L"$io24_build_dir" -Wl,--no-as-needed -Wl,-rpath,"$io24_build_dir" \
    -Wl,-rpath,"$io24_ntdll_dir" -Wl,-z,defs \
    -Wl,-l:libusb-1.0.so.0 -ldl \
    -o "$io24_build_dir/wineusb_function_scope_contract"

LD_LIBRARY_PATH="$io24_build_dir:$io24_ntdll_dir" \
    "$io24_build_dir/wineusb_function_scope_contract" "$io24_wineusb_unixlib"
