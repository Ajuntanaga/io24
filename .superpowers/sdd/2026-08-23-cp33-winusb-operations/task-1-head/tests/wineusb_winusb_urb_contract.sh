#!/usr/bin/env bash
set -euo pipefail
if (( $# < 3 || $# > 4 )); then echo 'usage: tests/wineusb_winusb_urb_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT LIBUSB_INCLUDE [MODE]' >&2; exit 2; fi
readonly source_root=$1 build_root=$2 libusb_include=$3 mode=${4:---red}
case "$mode" in --red|--claims|--alternate|--control-descriptor|--sync-pipes|--transfer-lifetime) ;; *) echo "usage: unsupported MODE: $mode" >&2; exit 2;; esac
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) ntdll="$build_root/dlls/ntdll/ntdll.so"
for input in "$source_root/dlls/wineusb.sys/unixlib.c" "$source_root/dlls/wineusb.sys/unixlib.h" "$libusb_include/libusb.h" "$ntdll" "$test_dir/wineusb_winusb_urb_contract.c" "$test_dir/wineusb_winusb_urb_fake_libusb.c"; do [[ -f "$input" ]] || { echo "HARNESS: missing input: $input" >&2; exit 2; }; done
build_dir=$(mktemp -d -p /tmp io24-wineusb-winusb-urb.XXXXXX); trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM
cc -std=c11 -Wall -Wextra -Werror -fPIC -shared -I"$libusb_include" -Wl,-soname,libusb-1.0.so.0 "$test_dir/wineusb_winusb_urb_fake_libusb.c" -o "$build_dir/libusb-1.0.so.0"
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-sign-compare -Wno-implicit-fallthrough -DWINE_UNIX_LIB -D__WINESRC__ -I"$build_root/include" -I"$libusb_include" -I"$source_root/include" -I"$source_root/dlls/wineusb.sys" -fPIC -c "$source_root/dlls/wineusb.sys/unixlib.c" -o "$build_dir/unixlib.o"
cc -shared -Wl,-Bsymbolic -Wl,-z,defs "$build_dir/unixlib.o" "$ntdll" -L"$build_dir" -Wl,-l:libusb-1.0.so.0 -lpthread -o "$build_dir/wineusb-contract.so"
cc -std=c11 -Wall -Wextra -Werror "$test_dir/wineusb_winusb_urb_contract.c" -o "$build_dir/contract"
"$build_dir/contract" "$source_root" "$mode"
