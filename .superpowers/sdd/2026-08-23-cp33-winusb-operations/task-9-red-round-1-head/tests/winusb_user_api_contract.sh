#!/usr/bin/env bash
set -uo pipefail
if (( $# < 1 || $# > 2 )); then echo 'usage: tests/winusb_user_api_contract.sh WINE_SOURCE_ROOT [MODE]' >&2; exit 2; fi
readonly source_root=$1 mode=${2:---red}
case "$mode" in --red|--surface-only|--initialize|--handles|--alternate|--descriptors|--policy|--transfer|--cancel|--vendor|--control-descriptor) ;; *) echo "usage: unsupported MODE: $mode" >&2; exit 2;; esac
required_tools=(awk cc dirname find grep mktemp rmdir)
for tool in "${required_tools[@]}"; do
    command -v "$tool" >/dev/null 2>&1 || { echo "HARNESS: required tool unavailable: $tool" >&2; exit 2; }
done
readonly test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for input in "$source_root/include/winusb.h" "$source_root/include/Makefile.in" "$source_root/dlls/winusb/main.c" "$source_root/dlls/winusb/winusb.spec" "$test_dir/winusb_user_api_contract.c"; do
    [[ -f "$input" ]] || { echo "HARNESS: missing or non-regular required input: $input" >&2; exit 2; }
    [[ -r "$input" ]] || { echo "HARNESS: unreadable required input: $input" >&2; exit 2; }
done
build_dir=$(mktemp -d -p /tmp io24-winusb-user-api.XXXXXX) || { echo 'HARNESS: mktemp failed' >&2; exit 2; }
trap 'find "$build_dir" -mindepth 1 -delete; rmdir "$build_dir"' EXIT INT TERM

print_log()
{
    local line
    while IFS= read -r line; do printf '%s\n' "$line" >&2; done < "$1"
}

printf '%s\n' 'io24-tool-baseline' > "$build_dir/tool-baseline.txt"
grep -Fqx 'io24-tool-baseline' "$build_dir/tool-baseline.txt" >"$build_dir/grep-baseline.log" 2>&1
tool_status=$?
if (( tool_status != 0 )); then echo "HARNESS: grep baseline failed with status $tool_status" >&2; print_log "$build_dir/grep-baseline.log"; exit 2; fi
grep -Fqx 'io24-tool-absent' "$build_dir/tool-baseline.txt" >"$build_dir/grep-negative.log" 2>&1
tool_status=$?
if (( tool_status != 1 )); then echo "HARNESS: grep negative baseline returned status $tool_status instead of 1" >&2; print_log "$build_dir/grep-negative.log"; exit 2; fi
awk '{ print NR ":" $0 }' "$build_dir/tool-baseline.txt" >"$build_dir/awk-baseline.out" 2>"$build_dir/awk-baseline.log"
tool_status=$?
if (( tool_status != 0 )); then echo "HARNESS: awk baseline failed with status $tool_status" >&2; print_log "$build_dir/awk-baseline.log"; exit 2; fi
mapfile -t awk_baseline < "$build_dir/awk-baseline.out"
if (( ${#awk_baseline[@]} != 1 )) || [[ "${awk_baseline[0]}" != '1:io24-tool-baseline' ]]; then echo 'HARNESS: awk baseline produced incorrect output' >&2; exit 2; fi

require_feature_match()
{
    local description=$1 status
    shift
    grep "$@" >/dev/null 2>"$build_dir/grep.log"
    status=$?
    if (( status == 0 )); then return 0; fi
    if (( status == 1 )); then echo "FEATURE: $description" >&2; feature_fail=1; return 0; fi
    echo "HARNESS: grep failed while checking $description" >&2
    print_log "$build_dir/grep.log"
    exit 2
}

compiler_failure_class()
{
    local label=$1 status=$2 log=$3 grep_status
    if (( status != 1 )); then
        echo "HARNESS: $label compiler exited abnormally with status $status" >&2
        print_log "$log"
        return 2
    fi
    grep -Eiq 'internal compiler error|segmentation fault|cannot execute|exec format error|killed signal|out of memory' "$log"
    grep_status=$?
    if (( grep_status == 0 )); then
        echo "HARNESS: $label compiler reported an internal/tool failure" >&2
        print_log "$log"
        return 2
    elif (( grep_status > 1 )); then
        echo "HARNESS: could not read $label compiler diagnostics" >&2
        return 2
    fi
    grep -Eq '(^|[[:space:]])(error:|fatal error:)|static assertion failed' "$log"
    grep_status=$?
    if (( grep_status == 0 )); then
        print_log "$log"
        return 1
    elif (( grep_status > 1 )); then
        echo "HARNESS: could not read $label compiler diagnostics" >&2
        return 2
    fi
    echo "HARNESS: $label compiler failed without a valid rejection diagnostic" >&2
    print_log "$log"
    return 2
}

printf '%s\n' \
    '#include <dlfcn.h>' \
    '#include <stdint.h>' \
    '#include <stddef.h>' \
    '#include <stdio.h>' \
    '#include <stdlib.h>' \
    '#include <string.h>' \
    '#include "windef.h"' \
    '#include "winbase.h"' \
    '#include "wine/debug.h"' \
    'int io24_compiler_baseline;' > "$build_dir/compiler-baseline.c"
cc -std=c11 -Wall -Wextra -Werror -D__WINESRC__ -I"$source_root/include" -c "$build_dir/compiler-baseline.c" -o "$build_dir/compiler-baseline.o" >"$build_dir/compiler-baseline.log" 2>&1
baseline_status=$?
if (( baseline_status != 0 )); then
    echo "HARNESS: native compiler/standard-header baseline failed with status $baseline_status" >&2
    print_log "$build_dir/compiler-baseline.log"
    exit 2
fi
[[ -s "$build_dir/compiler-baseline.o" ]] || { echo 'HARNESS: native compiler baseline produced no object' >&2; exit 2; }

if [[ "$mode" == --surface-only || "$mode" == --red ]]; then
    feature_fail=0
    for input in "$source_root/include/winusbio.h" "$source_root/include/wine/winusb.h"; do
        if [[ ! -e "$input" ]]; then echo "FEATURE: missing public/private ABI input: $input" >&2; feature_fail=1; continue; fi
        [[ -f "$input" ]] || { echo "HARNESS: non-regular ABI input: $input" >&2; exit 2; }
        [[ -r "$input" ]] || { echo "HARNESS: unreadable ABI input: $input" >&2; exit 2; }
    done
    public_symbols=(WinUsb_AbortPipe WinUsb_ControlTransfer WinUsb_Free WinUsb_GetAssociatedInterface WinUsb_GetDescriptor WinUsb_GetOverlappedResult WinUsb_GetPipePolicy WinUsb_Initialize WinUsb_QueryDeviceInformation WinUsb_ReadPipe WinUsb_ResetPipe WinUsb_SetCurrentAlternateSetting WinUsb_SetPipePolicy WinUsb_WritePipe)
    require_feature_match 'WINUSB_SETUP_PACKET is absent' -q 'WINUSB_SETUP_PACKET' "$source_root/include/winusb.h"
    for symbol in "${public_symbols[@]}"; do
        require_feature_match "public prototype absent: $symbol" -q "${symbol}(" "$source_root/include/winusb.h"
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
        require_feature_match "real export absent: $export" -Fqx "$export" "$source_root/dlls/winusb/winusb.spec"
    done
    for symbol in "${stub_exports[@]}"; do
        require_feature_match "explicit stub absent: $symbol" -Fqx "@ stub $symbol" "$source_root/dlls/winusb/winusb.spec"
    done
    real_count=$(awk '$2 == "stdcall" { count++ } END { print count + 0 }' "$source_root/dlls/winusb/winusb.spec")
    awk_status=$?
    (( awk_status == 0 )) || { echo "HARNESS: awk failed while counting real exports with status $awk_status" >&2; exit 2; }
    stub_count=$(awk '$2 == "stub" { count++ } END { print count + 0 }' "$source_root/dlls/winusb/winusb.spec")
    awk_status=$?
    (( awk_status == 0 )) || { echo "HARNESS: awk failed while counting stub exports with status $awk_status" >&2; exit 2; }
    if [[ "$real_count" != 14 || "$stub_count" != 8 ]]; then echo "FEATURE: export counts real=$real_count stub=$stub_count expected=14/8" >&2; feature_fail=1; fi
    require_feature_match 'winusbio.h is not publicly installed' -Eq '^[[:space:]]*winusbio\.h[[:space:]]*\\' "$source_root/include/Makefile.in"

    if [[ -f "$source_root/include/wine/winusb.h" && -r "$source_root/include/wine/winusb.h" ]]; then
        expected_schema=(
            'struct wine_winusb_request' '{' 'UINT32 size;' 'UINT32 version;' 'UINT64 session;' 'UINT32 interface_index;' 'UINT32 reserved;' '};'
            'struct wine_winusb_snapshot' '{' 'UINT32 size;' 'UINT32 version;' 'UINT64 session;' 'UINT32 speed;' 'UINT32 total_size;' 'UINT32 device_offset;' 'UINT32 device_length;' 'UINT32 configuration_offset;' 'UINT32 configuration_length;' 'UINT32 interfaces_offset;' 'UINT32 interface_count;' 'UINT32 alternates_offset;' 'UINT32 alternate_count;' 'UINT32 endpoints_offset;' 'UINT32 endpoint_count;' 'UINT32 reserved[2];' '};'
            'struct wine_winusb_interface_snapshot' '{' 'UINT32 interface_number;' 'UINT32 first_alternate;' 'UINT32 alternate_count;' 'UINT32 reserved;' '};'
            'struct wine_winusb_alternate_snapshot' '{' 'UINT32 interface_index;' 'UINT32 alternate_setting;' 'UINT32 first_endpoint;' 'UINT32 endpoint_count;' '};'
            'struct wine_winusb_endpoint_snapshot' '{' 'UINT32 alternate_index;' 'UINT32 pipe_id;' 'UINT32 pipe_type;' 'UINT32 maximum_packet_size;' '};'
            'struct wine_winusb_alternate_request' '{' 'struct wine_winusb_request request;' 'UINT32 alternate_setting;' 'UINT32 reserved;' '};'
            'struct wine_winusb_pipe_request' '{' 'struct wine_winusb_request request;' 'UINT32 pipe_id;' 'UINT32 transfer_length;' '};'
            'struct wine_winusb_descriptor_request' '{' 'struct wine_winusb_request request;' 'UINT32 type;' 'UINT32 index;' 'UINT32 language;' 'UINT32 length;' '};'
            'struct wine_winusb_policy_request' '{' 'struct wine_winusb_request request;' 'UINT32 pipe_id;' 'UINT32 policy_id;' 'UINT32 value_length;' 'UINT32 value;' '};'
            'struct wine_winusb_control_request' '{' 'struct wine_winusb_request request;' 'UINT8 setup[8];' 'UINT32 transfer_length;' 'UINT32 reserved;' '};'
        )
        awk '
            function normalize(line) {
                sub(/^[[:space:]]+/, "", line); sub(/[[:space:]]+$/, "", line);
                gsub(/[[:space:]]+/, " ", line); return line;
            }
            /^[[:space:]]*struct wine_winusb_[[:alnum:]_]+[[:space:]]*$/ { active=1; print normalize($0); next }
            active { line=normalize($0); if (line != "") print line; if (line == "};") active=0 }
        ' "$source_root/include/wine/winusb.h" > "$build_dir/private-schema.actual"
        awk_status=$?
        if (( awk_status != 0 )); then echo "HARNESS: awk failed while parsing private ABI schema with status $awk_status" >&2; exit 2; fi
        mapfile -t actual_schema < "$build_dir/private-schema.actual"
        if (( ${#actual_schema[@]} != ${#expected_schema[@]} )); then
            echo "FEATURE: private ABI declaration schema line count=${#actual_schema[@]} expected=${#expected_schema[@]}" >&2
            feature_fail=1
        else
            for ((schema_index=0; schema_index<${#expected_schema[@]}; schema_index++)); do
                if [[ "${actual_schema[schema_index]}" != "${expected_schema[schema_index]}" ]]; then
                    echo "FEATURE: private ABI declaration schema mismatch at line $((schema_index + 1)): actual='${actual_schema[schema_index]}' expected='${expected_schema[schema_index]}'" >&2
                    feature_fail=1
                    break
                fi
            done
        fi
    fi
    (( feature_fail == 0 )) || exit 1
    cc -std=c11 -Wall -Wextra -Werror -D__WINESRC__ -I"$source_root/include" -fsyntax-only "$test_dir/winusb_user_api_contract.c" >"$build_dir/native-candidate.log" 2>&1
    candidate_status=$?
    if (( candidate_status != 0 )); then
        compiler_failure_class 'native candidate' "$candidate_status" "$build_dir/native-candidate.log"
        failure_class=$?
        if (( failure_class == 1 )); then echo 'FEATURE: public/private surface compile-time contract failed' >&2; exit 1; fi
        exit 2
    fi
    cc -m32 -std=c11 -Wall -Wextra -Werror -D__WINESRC__ -I"$source_root/include" -fsyntax-only "$build_dir/compiler-baseline.c" >"$build_dir/m32-baseline.log" 2>&1
    m32_status=$?
    if (( m32_status == 0 )); then
        cc -m32 -std=c11 -Wall -Wextra -Werror -D__WINESRC__ -I"$source_root/include" -fsyntax-only "$test_dir/winusb_user_api_contract.c" >"$build_dir/m32-candidate.log" 2>&1
        candidate_status=$?
        if (( candidate_status != 0 )); then
            compiler_failure_class '-m32 candidate' "$candidate_status" "$build_dir/m32-candidate.log"
            failure_class=$?
            if (( failure_class == 1 )); then echo 'FEATURE: -m32 public/private layout contract failed' >&2; exit 1; fi
            exit 2
        fi
        echo 'CP33 surface-only passed layouts=native,m32 exports=14 stubs=8'
    else
        grep -Eq 'fatal error:.*(bits/|gnu/|sys/|stdint|stddef|stdio|stdlib|string|dlfcn).*No such file or directory|unrecognized command-line option.*-m32|unsupported option.*-m32' "$build_dir/m32-baseline.log"
        m32_probe_class=$?
        if (( m32_probe_class == 0 )); then
            echo 'CP33 surface-only passed layouts=native m32=unavailable exports=14 stubs=8'
        elif (( m32_probe_class > 1 )); then
            echo 'HARNESS: could not read -m32 compiler diagnostics' >&2
            exit 2
        else
            echo "HARNESS: -m32 compiler probe failed abnormally with status $m32_status" >&2
            print_log "$build_dir/m32-baseline.log"
            exit 2
        fi
    fi
    [[ "$mode" != --surface-only ]] || exit 0
fi
sources=("$source_root/dlls/winusb/main.c"); [[ ! -f "$source_root/dlls/winusb/io.c" ]] || sources+=("$source_root/dlls/winusb/io.c")
sanitizer=(); [[ "$mode" != --initialize && "$mode" != --alternate && "$mode" != --policy ]] || sanitizer=(-fsanitize=undefined -fno-sanitize-recover=alignment)
objects=("$build_dir/contract.o")
if ! cc -std=c11 -Wall -Wextra -Werror "${sanitizer[@]}" -I"$source_root/include" -c "$test_dir/winusb_user_api_contract.c" -o "${objects[0]}"; then echo 'HARNESS: compiling public host contract with actual winusb source failed' >&2; exit 2; fi
for ((source_index=0; source_index<${#sources[@]}; source_index++)); do
    object="$build_dir/production-$source_index.o"
    if ! cc -std=c11 -Wall -Wextra -Werror "${sanitizer[@]}" -I"$source_root/include" -c "${sources[source_index]}" -o "$object"; then echo 'HARNESS: compiling public host contract with actual winusb source failed' >&2; exit 2; fi
    objects+=("$object")
done
if ! cc -rdynamic "${sanitizer[@]}" "${objects[@]}" -ldl -o "$build_dir/contract"; then echo 'HARNESS: compiling public host contract with actual winusb source failed' >&2; exit 2; fi
if (( ${#sanitizer[@]} )); then
    UBSAN_OPTIONS="${UBSAN_OPTIONS:+$UBSAN_OPTIONS:}halt_on_error=1" "$build_dir/contract" self "$mode"; code=$?
else
    "$build_dir/contract" self "$mode"; code=$?
fi
(( code == 0 || code == 1 )) || { echo "HARNESS: public contract exited $code" >&2; exit 2; }
exit "$code"
