#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: tests/winusb_function_binding_contract.sh WINE_SOURCE_ROOT" >&2
    exit 2
fi

readonly io24_source=$1
readonly io24_test_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly io24_driver_dir="$io24_source/dlls/winusb.sys"
readonly io24_bus_dir="$io24_source/dlls/wineusb.sys"
readonly io24_build_dir="$(mktemp -d -p /tmp io24-winusb-function-binding.XXXXXX)"
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

io24_transfer_sources=()
if [[ -f "$io24_driver_dir/transfer.c" ]]; then
    io24_transfer_sources=("$io24_driver_dir/transfer.c")
fi

for io24_input in "$io24_driver_dir/main.c" "$io24_driver_dir/session.c"; do
    if [[ ! -r "$io24_input" ]]; then
        echo "HARNESS: missing or unreadable input: $io24_input" >&2
        exit 2
    fi
done

# Deliberately compile the actual driver.  Against CP31 this RED is expected:
# main.c and winusb_busif.h do not exist, proving the missing CP32 surface.
if ! cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
    -DWINUSB_FUNCTION_BINDING_STANDALONE \
    -I"$io24_source/include" -I"$io24_driver_dir" -I"$io24_bus_dir" \
    "$io24_test_dir/winusb_function_binding_contract.c" \
    "$io24_driver_dir/session.c" \
    "${io24_transfer_sources[@]}" \
    -o "$io24_build_dir/winusb_function_binding_contract"; then
    echo "HARNESS: compiling actual winusb.sys main/session fake-WDM contract failed" >&2
    exit 2
fi

io24_code=0
"$io24_build_dir/winusb_function_binding_contract" || io24_code=$?
if (( io24_code != 0 && io24_code != 1 )); then
    echo "HARNESS: retained binding contract exited $io24_code" >&2
    exit 2
fi
exit "$io24_code"
