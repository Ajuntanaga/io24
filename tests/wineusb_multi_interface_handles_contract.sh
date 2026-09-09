#!/usr/bin/env bash
set -euo pipefail

if (( $# != 4 )); then
    echo "usage: tests/wineusb_multi_interface_handles_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT WINEUSB_UNIXLIB LIBUSB_INCLUDE" >&2
    exit 2
fi

readonly io24_wine_source=$1
readonly io24_wine_build=$2
readonly io24_wineusb_unixlib=$3
readonly io24_libusb_include=$4
readonly io24_test_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly io24_test_source="$io24_test_dir/wineusb_multi_interface_handles_contract.c"
readonly io24_fake_source="$io24_test_dir/wineusb_pipe_observe_fake_libusb.c"
readonly io24_ntdll_dir="$io24_wine_build/dlls/ntdll"

for io24_required in \
        "$io24_test_source" \
        "$io24_fake_source" \
        "$io24_libusb_include/libusb.h" \
        "$io24_ntdll_dir/ntdll.so" \
        "$io24_wineusb_unixlib"; do
    [[ -f "$io24_required" ]] || {
        echo "FAIL: missing multi-interface contract input: $io24_required" >&2
        exit 1
    }
done

io24_build_dir=$(mktemp -d -p /tmp io24-wineusb-multi-interface-contract.XXXXXX)
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

cc -std=c11 -Wall -Wextra -Werror -fPIC -shared \
    -I"$io24_libusb_include" \
    -Wl,-soname,libusb-1.0.so.0 \
    "$io24_fake_source" \
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
    -o "$io24_build_dir/wineusb_multi_interface_handles_contract"

readonly io24_runtime_log="$io24_build_dir/runtime.log"
if ! LD_LIBRARY_PATH="$io24_build_dir:$io24_ntdll_dir" \
        "$io24_build_dir/wineusb_multi_interface_handles_contract" "$io24_wineusb_unixlib" \
        >"$io24_runtime_log" 2>&1; then
    cat "$io24_runtime_log" >&2
    exit 1
fi
cat "$io24_runtime_log"

for io24_marker in \
        'IO24_HANDLE_POPULATION event=validated' \
        'interfaces=3 pipes=3' \
        'IO24_HANDLE_POPULATION event=populated' \
        'IO24_HANDLE_POPULATION event=reject' \
        'reason=truncated_pipe_array interface_index=1' \
        'IO24_PIPE_SAFETY event=transfer_reject reason=null_buffer'; do
    grep -Fq -- "$io24_marker" "$io24_runtime_log" || {
        echo "FAIL: missing runtime marker '$io24_marker'" >&2
        exit 1
    }
done
