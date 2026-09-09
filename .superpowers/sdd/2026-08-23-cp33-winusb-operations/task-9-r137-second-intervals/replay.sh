#!/bin/sh
set -u

artifact_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$artifact_root/../../../.." && pwd)
replay_temp_root=$(mktemp -d /tmp/io24-r137-second-interval-replay.XXXXXX) || exit 2
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
    case_key=$(printf '%s' "$case_name" | tr / -)
    binary="$replay_temp_root/$case_key"
    compile_log="$replay_temp_root/compile-$case_key.log"
    run_log="$replay_temp_root/run-$case_key.log"

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
    helper_failures=$(grep -Ec '^FAIL .*r136_mutant_helper_(calls|frees)' "$run_log" || true)
    summary_count=$(grep -Ec "^CP33 function executed .* failures=$expected_failures$" "$run_log" || true)
    bad_markers=$(grep -Eih 'HARNESS:|Segmentation fault|AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:|LeakSanitizer' \
        "$compile_log" "$run_log" | wc -l | tr -d ' ')
    printf '%s compile=%s run=%s failures=%s retained=%s direct=%s helper=%s summary=%s bad-markers=%s\n' \
        "$case_name" "$compile_exit" "$run_exit" "$failures" \
        "$retained_failures" "$direct_failures" "$helper_failures" \
        "$summary_count" "$bad_markers"

    if [ "$compile_exit" -ne 0 ] || [ "$run_exit" -ne 1 ] || \
            [ "$failures" -ne "$expected_failures" ] || \
            [ "$retained_failures" -ne "$expected_retained_failures" ] || \
            [ "$direct_failures" -ne 0 ] || [ "$helper_failures" -ne 0 ] || \
            [ "$summary_count" -ne 1 ] || [ "$bad_markers" -ne 0 ]; then
        status=1
    fi
}

compare_pair()
{
    pair_name=$1
    control_case=$2
    corrected_case=$3
    control_key=$(printf '%s' "$control_case" | tr / -)
    corrected_key=$(printf '%s' "$corrected_case" | tr / -)
    control_normalized="$replay_temp_root/normalized-$control_key.log"
    corrected_normalized="$replay_temp_root/normalized-$corrected_key.log"

    sed -E -e 's/:[0-9]+:/:LINE:/g' \
        -e '/^FAIL control_retained_allocation_end:/d' \
        -e 's/failures=[0-9]+$/failures=N/' \
        "$replay_temp_root/run-$control_key.log" >"$control_normalized"
    sed -E -e 's/:[0-9]+:/:LINE:/g' \
        -e '/^FAIL control_retained_allocation_end:/d' \
        -e 's/failures=[0-9]+$/failures=N/' \
        "$replay_temp_root/run-$corrected_key.log" >"$corrected_normalized"

    if cmp -s "$control_normalized" "$corrected_normalized"; then
        printf '%s normalized-delta=exact\n' "$pair_name"
    else
        printf '%s normalized-delta=mismatch\n' "$pair_name"
        status=1
    fi
}

run_named_case()
{
    case "$1" in
        second-admission/r135-control) replay_case "$1" 203 0 ;;
        second-admission/r136) replay_case "$1" 204 1 ;;
        second-completion/hook-bypass) replay_case "$1" 203 0 ;;
        second-completion/r136) replay_case "$1" 204 1 ;;
        *) printf 'unknown case: %s\n' "$1" >&2; exit 2 ;;
    esac
}

cd "$repo_root" || exit 2
if [ "$#" -eq 0 ]; then
    run_named_case second-admission/r135-control
    run_named_case second-admission/r136
    run_named_case second-completion/hook-bypass
    run_named_case second-completion/r136
    compare_pair second-admission second-admission/r135-control second-admission/r136
    compare_pair second-completion second-completion/hook-bypass second-completion/r136
elif [ "$#" -eq 2 ] && [ "$1" = --case ]; then
    run_named_case "$2"
else
    printf 'usage: %s [--case CASE]\n' "$0" >&2
    exit 2
fi
exit "$status"
