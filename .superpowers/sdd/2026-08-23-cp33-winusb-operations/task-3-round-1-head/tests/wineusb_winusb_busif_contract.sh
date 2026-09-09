#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: tests/wineusb_winusb_busif_contract.sh WINE_SOURCE_ROOT" >&2
    exit 2
fi

readonly io24_wine_source=$1
readonly io24_source_dir="$io24_wine_source/dlls/wineusb.sys"
readonly io24_test_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/wineusb_winusb_busif_contract.c"

for io24_required in "$io24_test_source" "$io24_source_dir/winusb_busif.h" "$io24_source_dir/winusb_busif.c" "$io24_source_dir/wineusb.c"; do
    [[ -f "$io24_required" ]] || { echo "HARNESS: missing WineUSB WinUSB metadata bus-interface contract input: $io24_required" >&2; exit 2; }
done

io24_build_dir=$(mktemp -d -p /tmp io24-wineusb-winusb-busif.XXXXXX) || { echo "HARNESS: mktemp failed" >&2; exit 2; }
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

if ! cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-unused-variable \
    -Wno-implicit-function-declaration \
    -ffunction-sections -fdata-sections -fshort-wchar -D__WINESRC__ \
    -I"$io24_wine_source/include" -I"$io24_source_dir" \
    "$io24_test_source" "$io24_source_dir/winusb_busif.c" \
    -Wl,--gc-sections -o "$io24_build_dir/wineusb_winusb_busif_contract"; then
    echo "HARNESS: compiling actual wineusb.c metadata bus-interface contract failed" >&2
    exit 2
fi
set +e
"$io24_build_dir/wineusb_winusb_busif_contract"
io24_code=$?
set -e
(( io24_code == 0 || io24_code == 1 )) || { echo "HARNESS: metadata contract exited $io24_code" >&2; exit 2; }
exit "$io24_code"
