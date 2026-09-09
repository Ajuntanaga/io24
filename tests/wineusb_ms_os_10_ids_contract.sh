#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: tests/wineusb_ms_os_10_ids_contract.sh WINE_SOURCE_ROOT" >&2
    exit 2
fi

readonly io24_wine_source=$1
readonly io24_source_dir="$io24_wine_source/dlls/wineusb.sys"
readonly io24_test_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/wineusb_ms_os_10_ids_contract.c"

for io24_required in \
        "$io24_test_source" \
        "$io24_source_dir/msos_id.h" \
        "$io24_source_dir/msos_id.c"; do
    [[ -f "$io24_required" ]] || {
        echo "FAIL: missing Microsoft OS 1.0 ID contract input: $io24_required" >&2
        exit 1
    }
done

io24_build_dir=$(mktemp -d -p /tmp io24-wineusb-ms-os-10-ids.XXXXXX)
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

cc -std=c11 -Wall -Wextra -Werror -fshort-wchar \
    -I"$io24_wine_source/include" \
    -I"$io24_source_dir" \
    "$io24_test_source" \
    "$io24_source_dir/msos_id.c" \
    -o "$io24_build_dir/wineusb_ms_os_10_ids_contract"

"$io24_build_dir/wineusb_ms_os_10_ids_contract"
