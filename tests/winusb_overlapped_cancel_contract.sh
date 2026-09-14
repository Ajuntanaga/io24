#!/usr/bin/env bash
set -uo pipefail
if (( $# < 3 || $# > 4 )); then echo 'usage: tests/winusb_overlapped_cancel_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT LIBUSB_INCLUDE [MODE]' >&2; exit 2; fi
readonly source_root=$1 build_root=$2 libusb_include=$3 mode=${4:---red};case "$mode" in --red|--lower|--upper|--teardown) ;;*)echo "usage: unsupported MODE: $mode" >&2;exit 2;;esac
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")"&&pwd) ntdll="$build_root/dlls/ntdll/ntdll.so";for i in "$source_root/dlls/wineusb.sys/unixlib.c" "$source_root/dlls/wineusb.sys/wineusb.c" "$libusb_include/libusb.h" "$ntdll" "$test_dir/winusb_overlapped_cancel_contract.c" "$test_dir/wineusb_winusb_urb_fake_libusb.c";do [[ -f "$i" ]]||{ echo "HARNESS: missing input: $i" >&2;exit 2;};done
build_dir=$(mktemp -d -p /tmp io24-winusb-overlapped-cancel.XXXXXX)||{ echo 'HARNESS: mktemp failed' >&2;exit 2;};trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM
sanitize_flags=()
if [[ ${IO24_CONTRACT_SANITIZE:-0} == 1 ]]; then
    sanitize_flags=(-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
elif [[ ${IO24_CONTRACT_SANITIZE:-0} != 0 ]]; then
    echo 'HARNESS: IO24_CONTRACT_SANITIZE must be 0 or 1' >&2
    exit 2
fi
if ! cc -std=c11 -Wall -Wextra -Werror "${sanitize_flags[@]}" -fPIC -shared -I"$libusb_include" -Wl,-soname,libusb-1.0.so.0 "$test_dir/wineusb_winusb_urb_fake_libusb.c" -o "$build_dir/libusb-1.0.so.0";then echo 'HARNESS: compiling cancel fake libusb failed' >&2;exit 2;fi
if ! cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-sign-compare -Wno-implicit-fallthrough "${sanitize_flags[@]}" -DWINE_UNIX_LIB -D__WINESRC__ -I"$build_root/include" -I"$libusb_include" -I"$source_root/include" -I"$source_root/dlls/wineusb.sys" -fPIC -c "$source_root/dlls/wineusb.sys/unixlib.c" -o "$build_dir/unixlib.o";then echo 'HARNESS: compiling actual cancel unixlib failed' >&2;exit 2;fi
if ! cc -shared "${sanitize_flags[@]}" -Wl,-Bsymbolic -Wl,-z,defs "$build_dir/unixlib.o" "$ntdll" -L"$build_dir" -Wl,-l:libusb-1.0.so.0 -lpthread -o "$build_dir/wineusb-contract.so";then echo 'HARNESS: linking actual cancel unixlib failed' >&2;exit 2;fi
if ! cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-unused-variable -Wno-format -Wno-incompatible-pointer-types -Wno-implicit-function-declaration "${sanitize_flags[@]}" -fshort-wchar -D__WINESRC__ -I"$build_root/include" -I"$test_dir" -I"$source_root/include" -I"$source_root/dlls/wineusb.sys" "$test_dir/winusb_overlapped_cancel_contract.c" -L"$build_dir" -Wl,--no-as-needed -Wl,-rpath,"$build_dir" -Wl,-l:libusb-1.0.so.0 -ldl -o "$build_dir/contract";then echo 'HARNESS: compiling actual wineusb.c cancellation harness failed' >&2;exit 2;fi
if [[ ${IO24_CONTRACT_SANITIZE:-0} == 1 ]]; then
    command -v ldd >/dev/null || { echo 'HARNESS: ldd unavailable for sanitizer proof' >&2; exit 2; }
    ldd "$build_dir/contract" | rg -q 'libasan\.so' || { echo 'HARNESS: contract lacks AddressSanitizer runtime linkage' >&2; exit 2; }
    ldd "$build_dir/wineusb-contract.so" | rg -q 'libasan\.so' || { echo 'HARNESS: unixlib lacks AddressSanitizer runtime linkage' >&2; exit 2; }
fi
ASAN_OPTIONS="${ASAN_OPTIONS:-detect_leaks=1:halt_on_error=1}" UBSAN_OPTIONS="${UBSAN_OPTIONS:-halt_on_error=1}" LD_LIBRARY_PATH="$build_dir:$(dirname -- "$ntdll")" "$build_dir/contract" "$build_dir/wineusb-contract.so" "$mode";code=$?;((code==0||code==1))||{ echo "HARNESS: cancel contract exited $code" >&2;exit 2;};exit "$code"
