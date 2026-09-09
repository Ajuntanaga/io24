#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: tests/wineusb_usbdi_contract.sh WINE_SOURCE_ROOT" >&2
    exit 2
fi

io24_wine_source=$1
io24_usbdi_dir="$io24_wine_source/dlls/wineusb.sys"
io24_test_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/wineusb_usbdi_contract.c"

for io24_required in \
    "$io24_usbdi_dir/usbdi.h" \
    "$io24_usbdi_dir/usbdi.c"; do
    if [[ ! -f "$io24_required" ]]; then
        echo "FAIL: missing Wine USBDI implementation artifact: $io24_required" >&2
        exit 1
    fi
done

io24_build_dir=$(mktemp -d -p /tmp io24-wineusb-usbdi-test.XXXXXX)
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter \
    -I"$io24_wine_source/include" \
    -I"$io24_usbdi_dir" \
    "$io24_test_source" \
    "$io24_usbdi_dir/usbdi.c" \
    -o "$io24_build_dir/wineusb_usbdi_contract"

"$io24_build_dir/wineusb_usbdi_contract"
