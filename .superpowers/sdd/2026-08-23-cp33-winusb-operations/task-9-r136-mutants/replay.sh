#!/bin/sh
set -u

artifact_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$artifact_root/../../../.." && pwd)
replay_temp_root=$(mktemp -d /tmp/io24-r136-mutant-replay.XXXXXX) || exit 2
status=0

cleanup()
{
    find "$replay_temp_root" -mindepth 1 -maxdepth 1 -type f -delete
    rmdir "$replay_temp_root"
}
trap cleanup EXIT HUP INT TERM

replay_case()
{
    case_name=$1
    expected_failures=$2
    expected_retained_failures=$3
    case_root="$artifact_root/$case_name"
    binary="$replay_temp_root/$(printf '%s' "$case_name" | tr / -)"
    compile_log="$replay_temp_root/compile-$(printf '%s' "$case_name" | tr / -).log"
    run_log="$replay_temp_root/run-$(printf '%s' "$case_name" | tr / -).log"

    cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -D__WINESRC__ \
        -I"$case_root/tests" \
        -I"$repo_root/.io24-build/winusb-api-v1/dev-source/include" \
        -I"$case_root/dlls/winusb.sys" \
        -I"$repo_root/.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys" \
        "$case_root/tests/winusb_function_io_contract.c" \
        "$case_root/dlls/winusb.sys/session.c" \
        "$case_root/dlls/winusb.sys/transfer.c" \
        -o "$binary" >"$compile_log" 2>&1
    compile_exit=$?

    if [ "$compile_exit" -eq 0 ]; then
        "$binary" --control-descriptor >"$run_log" 2>&1
        run_exit=$?
    else
        run_exit=125
        : >"$run_log"
    fi

    failures=$(grep -c '^FAIL ' "$run_log" || true)
    retained_failures=$(grep -c '^FAIL control_retained_allocation_end:' "$run_log" || true)
    direct_failures=$(grep -c '^FAIL control_completion_allocation_end:' "$run_log" || true)
    bad_markers=$(grep -Eih 'HARNESS:|Segmentation fault|AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:|LeakSanitizer' \
        "$compile_log" "$run_log" | wc -l | tr -d ' ')
    printf '%s compile=%s run=%s failures=%s retained=%s direct=%s bad-markers=%s\n' \
        "$case_name" "$compile_exit" "$run_exit" "$failures" \
        "$retained_failures" "$direct_failures" "$bad_markers"

    if [ "$compile_exit" -ne 0 ] || [ "$run_exit" -ne 1 ] || \
            [ "$failures" -ne "$expected_failures" ] || \
            [ "$retained_failures" -ne "$expected_retained_failures" ] || \
            [ "$direct_failures" -ne 0 ] || [ "$bad_markers" -ne 0 ]; then
        status=1
    fi
}

cd "$repo_root" || exit 2
replay_case admission/r135 203 0
replay_case admission/r136 204 1
replay_case completion/bypass 203 0
replay_case completion/r136 204 1
replay_case failed/r136 204 1
exit "$status"
