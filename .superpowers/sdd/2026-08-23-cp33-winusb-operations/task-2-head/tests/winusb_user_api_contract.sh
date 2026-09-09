#!/usr/bin/env bash
set -uo pipefail
if (( $# < 1 || $# > 2 )); then echo 'usage: tests/winusb_user_api_contract.sh WINE_SOURCE_ROOT [MODE]' >&2; exit 2; fi
readonly source_root=$1 mode=${2:---red}
case "$mode" in --red|--surface-only|--initialize|--handles|--descriptors|--policy|--transfer|--cancel|--vendor) ;; *) echo "usage: unsupported MODE: $mode" >&2; exit 2;; esac
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for input in "$source_root/include/winusb.h" "$source_root/dlls/winusb/main.c" "$source_root/dlls/winusb/winusb.spec" "$test_dir/winusb_user_api_contract.c"; do [[ -f "$input" ]] || { echo "HARNESS: missing input: $input" >&2; exit 2; }; done
build_dir=$(mktemp -d -p /tmp io24-winusb-user-api.XXXXXX) || { echo 'HARNESS: mktemp failed' >&2; exit 2; }
trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM
if [[ "$mode" == --surface-only || "$mode" == --red ]]; then
    feature_fail=0
    for input in "$source_root/include/winusbio.h" "$source_root/include/wine/winusb.h"; do
        if [[ ! -f "$input" ]]; then echo "FEATURE: missing public/private ABI input: $input" >&2; feature_fail=1; fi
    done
    public_symbols=(WinUsb_AbortPipe WinUsb_ControlTransfer WinUsb_Free WinUsb_GetAssociatedInterface WinUsb_GetDescriptor WinUsb_GetOverlappedResult WinUsb_GetPipePolicy WinUsb_Initialize WinUsb_QueryDeviceInformation WinUsb_ReadPipe WinUsb_ResetPipe WinUsb_SetCurrentAlternateSetting WinUsb_SetPipePolicy WinUsb_WritePipe)
    if ! grep -q 'WINUSB_SETUP_PACKET' "$source_root/include/winusb.h"; then echo 'FEATURE: WINUSB_SETUP_PACKET is absent' >&2; feature_fail=1; fi
    for symbol in "${public_symbols[@]}"; do
        if ! grep -q "${symbol}(" "$source_root/include/winusb.h"; then echo "FEATURE: public prototype absent: $symbol" >&2; feature_fail=1; fi
    done
    real_exports=(
        '@ stdcall WinUsb_AbortPipe(ptr long)'
        '@ stdcall WinUsb_ControlTransfer(ptr int64 ptr long ptr ptr)'
        '@ stdcall WinUsb_Free(ptr)'
        '@ stdcall WinUsb_GetAssociatedInterface(ptr long ptr)'
        '@ stdcall WinUsb_GetDescriptor(ptr long long long ptr long ptr)'
        '@ stdcall WinUsb_GetOverlappedResult(ptr ptr ptr long)'
        '@ stdcall WinUsb_GetPipePolicy(ptr long long ptr ptr)'
        '@ stdcall WinUsb_Initialize(ptr ptr)'
        '@ stdcall WinUsb_QueryDeviceInformation(ptr long ptr ptr)'
        '@ stdcall WinUsb_ReadPipe(ptr long ptr long ptr ptr)'
        '@ stdcall WinUsb_ResetPipe(ptr long)'
        '@ stdcall WinUsb_SetCurrentAlternateSetting(ptr long)'
        '@ stdcall WinUsb_SetPipePolicy(ptr long long long ptr)'
        '@ stdcall WinUsb_WritePipe(ptr long ptr long ptr ptr)'
    )
    stub_exports=(WinUsb_FlushPipe WinUsb_GetCurrentAlternateSetting WinUsb_GetPowerPolicy WinUsb_ParseConfigurationDescriptor WinUsb_ParseDescriptors WinUsb_QueryInterfaceSettings WinUsb_QueryPipe WinUsb_SetPowerPolicy)
    for export in "${real_exports[@]}"; do
        if ! grep -Fqx "$export" "$source_root/dlls/winusb/winusb.spec"; then echo "FEATURE: real export absent: $export" >&2; feature_fail=1; fi
    done
    for symbol in "${stub_exports[@]}"; do
        if ! grep -Fqx "@ stub $symbol" "$source_root/dlls/winusb/winusb.spec"; then echo "FEATURE: explicit stub absent: $symbol" >&2; feature_fail=1; fi
    done
    real_count=$(awk '$2 == "stdcall" { count++ } END { print count + 0 }' "$source_root/dlls/winusb/winusb.spec")
    stub_count=$(awk '$2 == "stub" { count++ } END { print count + 0 }' "$source_root/dlls/winusb/winusb.spec")
    if [[ "$real_count" != 14 || "$stub_count" != 8 ]]; then echo "FEATURE: export counts real=$real_count stub=$stub_count expected=14/8" >&2; feature_fail=1; fi
    if ! grep -Eq '^[[:space:]]*winusbio\.h[[:space:]]*\\' "$source_root/include/Makefile.in"; then echo 'FEATURE: winusbio.h is not publicly installed' >&2; feature_fail=1; fi
    (( feature_fail == 0 )) || exit 1
    if ! cc -std=c11 -Wall -Wextra -Werror -D__WINESRC__ -I"$source_root/include" -fsyntax-only "$test_dir/winusb_user_api_contract.c"; then echo 'FEATURE: public/private surface compile-time contract failed' >&2; exit 1; fi
    if printf '#include <stdint.h>\nint probe;\n' | cc -m32 -std=c11 -Wall -Wextra -Werror -x c -fsyntax-only - >/dev/null 2>&1; then
        if ! cc -m32 -std=c11 -Wall -Wextra -Werror -D__WINESRC__ -I"$source_root/include" -fsyntax-only "$test_dir/winusb_user_api_contract.c"; then echo 'FEATURE: -m32 public/private layout contract failed' >&2; exit 1; fi
        echo 'CP33 surface-only passed layouts=native,m32 exports=14 stubs=8'
    else
        echo 'CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8'
    fi
    [[ "$mode" != --surface-only ]] || exit 0
fi
sources=("$source_root/dlls/winusb/main.c"); [[ ! -f "$source_root/dlls/winusb/io.c" ]] || sources+=("$source_root/dlls/winusb/io.c")
if ! cc -std=c11 -Wall -Wextra -Werror -fPIC -shared -D__WINESRC__ -I"$source_root/include" "${sources[@]}" -o "$build_dir/winusb-production.so"; then echo 'HARNESS: compiling/linking actual winusb production module failed' >&2; exit 2; fi
if ! cc -std=c11 -Wall -Wextra -Werror -rdynamic -D__WINESRC__ -I"$source_root/include" "$test_dir/winusb_user_api_contract.c" -ldl -o "$build_dir/contract"; then echo 'HARNESS: compiling public host contract failed' >&2; exit 2; fi
"$build_dir/contract" "$build_dir/winusb-production.so" "$mode"; code=$?
(( code == 0 || code == 1 )) || { echo "HARNESS: public contract exited $code" >&2; exit 2; }
exit "$code"
