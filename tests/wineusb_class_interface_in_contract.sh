#!/usr/bin/env bash
set -euo pipefail

if (( $# != 5 )); then
    echo "usage: tests/wineusb_class_interface_in_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT WINEUSB_BUILTIN WINEUSB_UNIXLIB LIBUSB_INCLUDE" >&2
    exit 2
fi

readonly io24_wine_source=$1
readonly io24_wine_build=$2
readonly io24_wineusb_builtin=$3
readonly io24_wineusb_unixlib=$4
readonly io24_libusb_include=$5
readonly io24_source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly io24_test_source="$io24_source_dir/wineusb_class_interface_in_contract.c"
readonly io24_fake_source="$io24_source_dir/wineusb_class_interface_in_fake_libusb.c"
readonly io24_ntdll_dir="$io24_wine_build/dlls/ntdll"
readonly io24_wineusb_source="$io24_wine_source/dlls/wineusb.sys/wineusb.c"
readonly io24_unixlib_source="$io24_wine_source/dlls/wineusb.sys/unixlib.c"
readonly io24_unixlib_header="$io24_wine_source/dlls/wineusb.sys/unixlib.h"

for io24_required in \
        "$io24_test_source" \
        "$io24_fake_source" \
        "$io24_libusb_include/libusb.h" \
        "$io24_ntdll_dir/ntdll.so" \
        "$io24_wineusb_source" \
        "$io24_unixlib_source" \
        "$io24_unixlib_header" \
        "$io24_wineusb_builtin" \
        "$io24_wineusb_unixlib"; do
    [[ -f "$io24_required" ]] || {
        echo "FAIL: missing contract input: $io24_required" >&2
        exit 1
    }
done

io24_build_dir=$(mktemp -d -p /tmp io24-wineusb-class-in-contract.XXXXXX)
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
    -o "$io24_build_dir/wineusb_class_interface_in_contract"

LD_LIBRARY_PATH="$io24_build_dir:$io24_ntdll_dir" \
    "$io24_build_dir/wineusb_class_interface_in_contract" "$io24_wineusb_unixlib"

io24_require_count() {
    local io24_expected=$1
    local io24_pattern=$2
    local io24_file=$3
    local io24_actual

    io24_actual=$(grep -Ec -- "$io24_pattern" "$io24_file" || true)
    [[ "$io24_actual" == "$io24_expected" ]] || {
        echo "FAIL: expected $io24_expected match(es) for $io24_pattern in $io24_file, got $io24_actual" >&2
        exit 1
    }
}

io24_require_count 1 'wineusb_io24_class_interface_in_supported' "$io24_unixlib_header"
io24_require_count 2 'case URB_FUNCTION_CLASS_INTERFACE:' "$io24_wineusb_source"
io24_require_count 2 'case URB_FUNCTION_CLASS_INTERFACE:' "$io24_unixlib_source"
io24_require_count 1 'LIBUSB_REQUEST_TYPE_CLASS.*LIBUSB_RECIPIENT_INTERFACE.*LIBUSB_ENDPOINT_IN' "$io24_unixlib_source"
io24_require_count 1 'USBD_STATUS_DATA_OVERRUN' "$io24_unixlib_source"
io24_require_count 1 'IO24_CLASS_IN submit' "$io24_unixlib_source"
io24_require_count 1 'IO24_CLASS_IN reject' "$io24_wineusb_source"

io24_select_block=$(awk '
    /case URB_FUNCTION_SELECT_INTERFACE:/ { emit = 1 }
    /^[[:space:]]*default:/ { if (emit) exit }
    emit { print }
' "$io24_wineusb_source")
grep -q 'returning STATUS_NOT_IMPLEMENTED' <<<"$io24_select_block" || {
    echo 'FAIL: select-interface no longer declares fail-closed status' >&2
    exit 1
}
grep -q '^[[:space:]]*break;' <<<"$io24_select_block" || {
    echo 'FAIL: select-interface no longer leaves through the common fail-closed return' >&2
    exit 1
}
if grep -Eq 'WINE_UNIX_CALL|libusb_|return STATUS_SUCCESS' <<<"$io24_select_block"; then
    echo 'FAIL: select-interface gained submission or success semantics' >&2
    exit 1
fi

for io24_marker in 'IO24_CLASS_IN reject'; do
    [[ "$(strings "$io24_wineusb_builtin" | grep -Fc -- "$io24_marker" || true)" == 1 ]] || {
        echo "FAIL: builtin marker mismatch: $io24_marker" >&2
        exit 1
    }
done
for io24_marker in 'IO24_CLASS_IN submit'; do
    [[ "$(strings "$io24_wineusb_unixlib" | grep -Fc -- "$io24_marker" || true)" == 1 ]] || {
        echo "FAIL: Unix library marker mismatch: $io24_marker" >&2
        exit 1
    }
done

if strings "$io24_wineusb_unixlib" | grep -Fq 'IO24_CLASS_OUT'; then
    echo 'FAIL: Unix library contains a class-OUT implementation marker' >&2
    exit 1
fi

echo 'WineUSB class-interface-IN source/binary contract: pass'
