#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: $0 SANDBOX_ROOT" >&2
    exit 64
fi

target=$1
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
project_root=$(cd -- "$script_dir/.." && pwd -P)
service_log=$target/out/service-install.log
capture=$target/out/live-service-usb.txt
probe=$target/out/probe.log
status=$project_root/re/wine-ntoskrnl-mdl-nonpaged-v1/logs/cp24-live-read.status

for required in "$service_log" "$capture" "$probe" "$status"; do
    if [[ ! -f $required || -L $required ]]; then
        echo "missing or non-regular evidence: $required" >&2
        exit 1
    fi
done

failures=0

expect_equal()
{
    local label=$1 actual=$2 expected=$3
    if [[ $actual != "$expected" ]]; then
        printf 'FAIL %s: got %s, expected %s\n' "$label" "$actual" "$expected" >&2
        failures=$((failures + 1))
    fi
}

fixed_count()
{
    local pattern=$1 file=$2
    awk -v pattern="$pattern" 'index($0, pattern) { count++ } END { print count + 0 }' "$file"
}

regex_count()
{
    local pattern=$1 file=$2
    awk -v pattern="$pattern" '$0 ~ pattern { count++ } END { print count + 0 }' "$file"
}

expect_equal capture_sha256 "$(sha256sum "$capture" | cut -d ' ' -f 1)" \
    ab998beda7e6544cf56d574b66212ee3129d17e4f7b97cf3378582d5ef105da8
expect_equal inherited_capture_sha256 \
    "$(sha256sum "$target/out/inherited-live-service-usb-observe-v2-20260819T194220PDT.txt" | cut -d ' ' -f 1)" \
    f7ae3a97696dfd1ceff7b511c307d054422250e481deceb7b180167538762a67

expect_equal validated "$(fixed_count 'IO24_HANDLE_POPULATION event=validated' "$service_log")" 2
expect_equal populated "$(fixed_count 'IO24_HANDLE_POPULATION event=populated' "$service_log")" 2
expect_equal rejected "$(fixed_count 'IO24_HANDLE_POPULATION event=reject' "$service_log")" 0
expect_equal pipe_handles "$(fixed_count 'IO24_PIPE_OBSERVE event=pipe_handle' "$service_log")" 4
expect_equal pipe_0x02 "$(regex_count 'event=pipe_handle.*endpoint=0x2 ' "$service_log")" 2
expect_equal pipe_0x82 "$(regex_count 'event=pipe_handle.*endpoint=0x82 ' "$service_log")" 2
expect_equal mdl_nonpaged "$(fixed_count 'MmBuildMdlForNonPagedPool' "$service_log")" 24
expect_equal transfer_map "$(fixed_count 'IO24_PIPE_OBSERVE event=transfer_map' "$service_log")" 8
expect_equal mapped_ok "$(regex_count 'event=transfer_map.*mapped_ok=1' "$service_log")" 8
expect_equal mapped_null "$(regex_count 'event=transfer_map.*mapped_ok=0' "$service_log")" 0
expect_equal transfer_route "$(fixed_count 'IO24_PIPE_OBSERVE event=transfer_route' "$service_log")" 8
expect_equal transfer_submit "$(fixed_count 'IO24_PIPE_OBSERVE event=transfer_submit' "$service_log")" 8
expect_equal submit_endpoint "$(regex_count 'event=transfer_submit.*endpoint=0x82.*route=bulk.*libusb_status=-1.*returned_status=0x103' "$service_log")" 8
expect_equal null_reject "$(fixed_count 'IO24_PIPE_SAFETY event=transfer_reject' "$service_log")" 0
expect_equal map_stub "$(fixed_count 'MmMapLockedPagesSpecifyCache' "$service_log")" 0
expect_equal dpc_insert "$(fixed_count 'KeInsertQueueDpc' "$service_log")" 0
expect_equal clear_halt_markers "$(fixed_count 'IO24_PIPE_OBSERVE event=clear_halt' "$service_log")" 4

expect_equal libusb_submits "$(fixed_count '[libusb_submit_transfer]' "$capture")" 117
expect_equal control_in_submit "$(fixed_count ' S Ci:' "$capture")" 109
expect_equal control_in_complete "$(fixed_count ' C Ci:' "$capture")" 109
expect_equal control_in_success "$(regex_count ' C Ci:[^ ]+ 0 ' "$capture")" 109
expect_equal non_control_in_bus "$(regex_count ' [SC] (Bi|Bo|Ii|Io|Co):' "$capture")" 0
expect_equal bulk_submit_detail "$(fixed_count '[submit_bulk_transfer]' "$capture")" 24
expect_equal bulk_submit_failed "$(fixed_count 'submiturb failed, errno=16' "$capture")" 8
expect_equal clear_halt_calls "$(fixed_count '[libusb_clear_halt]' "$capture")" 4
expect_equal clear_halt_ebusy "$(fixed_count 'clear halt failed, errno=16' "$capture")" 4
expect_equal sync_bulk "$(fixed_count '[libusb_bulk_transfer]' "$capture")" 0
expect_equal sync_interrupt "$(fixed_count '[libusb_interrupt_transfer]' "$capture")" 0
expect_equal sync_control "$(fixed_count '[libusb_control_transfer]' "$capture")" 0
expect_equal claim "$(fixed_count '[libusb_claim_interface]' "$capture")" 0
expect_equal release "$(fixed_count '[libusb_release_interface]' "$capture")" 0
expect_equal detach "$(fixed_count '[libusb_detach_kernel_driver]' "$capture")" 0
expect_equal auto_detach "$(fixed_count '[libusb_set_auto_detach_kernel_driver]' "$capture")" 0
expect_equal set_alt "$(fixed_count '[libusb_set_interface_alt_setting]' "$capture")" 0
expect_equal set_config "$(fixed_count '[libusb_set_configuration]' "$capture")" 0

expect_equal probe "$(<"$probe")" 'ucnet probe: no UCNET DA announcement within 8.0 seconds'
expect_equal live_status "$(<"$status")" 1
if [[ -e $target/out/synchronize.json ]]; then
    echo 'FAIL synchronize.json exists' >&2
    failures=$((failures + 1))
fi

if (( failures != 0 )); then
    printf 'CP24 live analysis contract: %d failure(s)\n' "$failures" >&2
    exit 1
fi

echo 'CP24 live analysis contract: pass'
