#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
    printf 'usage: %s TAP_LOG MONITOR_SOCKET ABORT_RECORD\n' "$0" >&2
    exit 2
fi

tap_log=$1
monitor_socket=$2
abort_record=$3

while [[ ! -S "$monitor_socket" ]]; do
    sleep 0.1
done

while [[ ! -e "$tap_log" ]]; do
    sleep 0.1
done

tail -n +1 -F -- "$tap_log" | while IFS= read -r line; do
    if [[ "$line" =~ \ [SC]\ [A-Z][io]:[0-9]+:[0-9]+:(03|83)\  ]]; then
        {
            date --iso-8601=seconds
            printf 'FORBIDDEN_ENDPOINT3=%s\n' "$line"
            printf 'device_del io24\n' | timeout 2s nc -U "$monitor_socket"
        } >"$abort_record" 2>&1
        exit 99
    fi
done
