#!/usr/bin/env bash
set -euo pipefail

if (( $# != 5 )); then
    echo "usage: tests/wineusb_pipe_observe_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT WINEUSB_BUILTIN WINEUSB_UNIXLIB LIBUSB_INCLUDE" >&2
    exit 2
fi

readonly io24_wine_source=$1
readonly io24_wine_build=$2
readonly io24_wineusb_builtin=$3
readonly io24_wineusb_unixlib=$4
readonly io24_libusb_include=$5
readonly io24_test_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly io24_test_source="$io24_test_dir/wineusb_pipe_observe_contract.c"
readonly io24_fake_source="$io24_test_dir/wineusb_pipe_observe_fake_libusb.c"
readonly io24_ntdll_dir="$io24_wine_build/dlls/ntdll"
readonly io24_wineusb_source="$io24_wine_source/dlls/wineusb.sys/wineusb.c"
readonly io24_unixlib_source="$io24_wine_source/dlls/wineusb.sys/unixlib.c"

for io24_required in \
        "$io24_test_source" \
        "$io24_fake_source" \
        "$io24_libusb_include/libusb.h" \
        "$io24_ntdll_dir/ntdll.so" \
        "$io24_wineusb_source" \
        "$io24_unixlib_source" \
        "$io24_wineusb_builtin" \
        "$io24_wineusb_unixlib"; do
    [[ -f "$io24_required" ]] || {
        echo "FAIL: missing pipe-observe contract input: $io24_required" >&2
        exit 1
    }
done

io24_build_dir=$(mktemp -d -p /tmp io24-wineusb-pipe-observe-contract.XXXXXX)
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
    -o "$io24_build_dir/wineusb_pipe_observe_contract"

readonly io24_runtime_log="$io24_build_dir/runtime.log"
if ! LD_LIBRARY_PATH="$io24_build_dir:$io24_ntdll_dir" \
        "$io24_build_dir/wineusb_pipe_observe_contract" "$io24_wineusb_unixlib" \
        >"$io24_runtime_log" 2>&1; then
    cat "$io24_runtime_log" >&2
    exit 1
fi
cat "$io24_runtime_log"

io24_require_marker() {
    local io24_marker=$1
    local io24_file=$2
    grep -Fq -- "$io24_marker" "$io24_file" || {
        echo "FAIL: missing marker '$io24_marker' in $io24_file" >&2
        exit 1
    }
}

for io24_marker in \
        'IO24_PIPE_OBSERVE event=clear_halt' \
        'IO24_PIPE_OBSERVE event=transfer_route' \
        'route=bulk' \
        'route=interrupt' \
        'route=invalid' \
        'IO24_PIPE_OBSERVE event=transfer_submit' \
        'IO24_PIPE_OBSERVE event=select_configuration_backend' \
        'IO24_PIPE_OBSERVE event=pipe_handle'; do
    io24_require_marker "$io24_marker" "$io24_runtime_log"
done

for io24_marker in \
        'IO24_PIPE_OBSERVE event=transfer_map' \
        'IO24_PIPE_OBSERVE event=select_configuration_header' \
        'IO24_PIPE_OBSERVE event=select_interface' \
        'IO24_PIPE_OBSERVE event=select_pipe'; do
    io24_require_marker "$io24_marker" "$io24_wineusb_source"
    [[ "$(strings "$io24_wineusb_builtin" | grep -Fc -- "$io24_marker" || true)" == 1 ]] || {
        echo "FAIL: compiled builtin marker mismatch: $io24_marker" >&2
        exit 1
    }
done

for io24_marker in \
        'IO24_PIPE_OBSERVE event=clear_halt' \
        'IO24_PIPE_OBSERVE event=transfer_route' \
        'IO24_PIPE_OBSERVE event=transfer_submit' \
        'IO24_PIPE_OBSERVE event=select_configuration_backend' \
        'IO24_PIPE_OBSERVE event=pipe_handle'; do
    io24_require_marker "$io24_marker" "$io24_unixlib_source"
    [[ "$(strings "$io24_wineusb_unixlib" | grep -Fc -- "$io24_marker" || true)" == 1 ]] || {
        echo "FAIL: compiled Unix-library marker mismatch: $io24_marker" >&2
        exit 1
    }
done

if grep -En 'libusb_(claim_interface|detach_kernel_driver|set_interface_alt_setting|set_configuration|control_transfer)[[:space:]]*\(' \
        "$io24_wineusb_source" "$io24_unixlib_source" | \
        grep -Ev ':[[:space:]]*(/\*|\*)'; then
    echo 'FAIL: observation candidate contains a newly actionable USB call' >&2
    exit 1
fi

echo 'WineUSB pipe-observe source/binary/runtime contract: pass'
