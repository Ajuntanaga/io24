#!/usr/bin/env bash
set -euo pipefail

if (( $# != 2 )); then
    echo "usage: tests/wineusb_urb_observe_contract.sh WINE_SOURCE_ROOT WINEUSB_BUILTIN" >&2
    exit 2
fi

io24_wine_source=$1
io24_wineusb_builtin=$2
io24_wineusb_source="$io24_wine_source/dlls/wineusb.sys/wineusb.c"

for io24_required in "$io24_wineusb_source" "$io24_wineusb_builtin"; do
    if [[ ! -f "$io24_required" ]]; then
        echo "FAIL: missing observation artifact: $io24_required" >&2
        exit 1
    fi
done

io24_require_count() {
    local io24_expected=$1
    local io24_pattern=$2
    local io24_file=$3
    local io24_actual

    io24_actual=$(grep -Ec -- "$io24_pattern" "$io24_file" || true)
    if [[ "$io24_actual" != "$io24_expected" ]]; then
        echo "FAIL: expected $io24_expected match(es) for $io24_pattern in $io24_file, got $io24_actual" >&2
        exit 1
    fi
}

io24_require_count 1 'case URB_FUNCTION_CLASS_INTERFACE:' "$io24_wineusb_source"
io24_require_count 1 'case URB_FUNCTION_SELECT_INTERFACE:' "$io24_wineusb_source"
io24_require_count 1 'IO24_OBSERVE class-interface:' "$io24_wineusb_source"
io24_require_count 1 'IO24_OBSERVE select-interface:' "$io24_wineusb_source"

io24_class_block=$(awk '
    /case URB_FUNCTION_CLASS_INTERFACE:/ { emit = 1 }
    /case URB_FUNCTION_SELECT_INTERFACE:/ { if (emit) exit }
    emit { print }
' "$io24_wineusb_source")

io24_select_block=$(awk '
    /case URB_FUNCTION_SELECT_INTERFACE:/ { emit = 1 }
    /^[[:space:]]*default:/ { if (emit) exit }
    emit { print }
' "$io24_wineusb_source")

for io24_name in class select; do
    if [[ "$io24_name" == class ]]; then
        io24_block=$io24_class_block
    else
        io24_block=$io24_select_block
    fi

    grep -q 'returning STATUS_NOT_IMPLEMENTED' <<<"$io24_block" || {
        echo "FAIL: $io24_name observation block does not declare fail-closed status" >&2
        exit 1
    }
    grep -q '^[[:space:]]*break;' <<<"$io24_block" || {
        echo "FAIL: $io24_name observation block does not leave through the common fail-closed return" >&2
        exit 1
    }
    if grep -Eq 'WINE_UNIX_CALL|libusb_|memcpy|MmGetSystemAddress|TransferBufferMDL|return STATUS_SUCCESS' \
            <<<"$io24_block"; then
        echo "FAIL: $io24_name observation block contains submission, buffer-copy, or success semantics" >&2
        exit 1
    fi
done

io24_submit_function=$(awk '
    /static NTSTATUS usb_submit_urb\(/ { emit = 1 }
    /static NTSTATUS WINAPI driver_internal_ioctl\(/ { if (emit) exit }
    emit { print }
' "$io24_wineusb_source")

io24_common_returns=$(grep -c '^[[:space:]]*return STATUS_NOT_IMPLEMENTED;' <<<"$io24_submit_function" || true)
if [[ "$io24_common_returns" != 1 ]]; then
    echo "FAIL: usb_submit_urb must retain exactly one common STATUS_NOT_IMPLEMENTED return" >&2
    exit 1
fi

for io24_marker in \
    'IO24_OBSERVE class-interface:' \
    'IO24_OBSERVE select-interface:'; do
    io24_marker_count=$(strings "$io24_wineusb_builtin" | grep -Fc -- "$io24_marker" || true)
    if [[ "$io24_marker_count" != 1 ]]; then
        echo "FAIL: compiled builtin has $io24_marker_count copies of marker: $io24_marker" >&2
        exit 1
    fi
done

echo "wineusb URB observation contract: pass"
