#!/usr/bin/env bash
# Capture only USB control URBs while the user physically reconnects the io24.
#
# plan is read-only and unprivileged. capture must be invoked explicitly as
# root; it loads usbmon only when absent, restores that prior module state,
# never opens the io24 device node, and never writes USB or sysfs state.
set -euo pipefail
shopt -s nullglob

readonly SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
readonly PROJECT_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"
readonly CAPTURE_OWNER=ajuntanaga
readonly CAPTURE_ROOT="$PROJECT_DIR/re/io24-passive-usbmon"
readonly TARGET_VENDOR=194f
readonly TARGET_PRODUCT=0422
readonly TARGET_SERIAL=AB7C22200355
readonly TARGET_BUS=3
readonly CAPTURE_FILTER='link[9] == 2'
readonly CAPTURE_SNAPLEN=512
readonly CAPTURE_BUFFER_KIB=1024
readonly CAPTURE_MAX_PACKETS=20000
readonly CAPTURE_MAX_SECONDS=120
readonly POST_RECONNECT_SECONDS=12
readonly CAPTURE_MAX_FILE_BLOCKS=8192
readonly TCPDUMP=/usr/bin/tcpdump
readonly MODPROBE=/usr/sbin/modprobe
readonly UDEVADM=/usr/bin/udevadm

capture_pid=''
monitor_pid=''
capture_dir=''
capture_status=0
module_loaded_by_script=0

die() {
    printf 'io24 passive usbmon: %s\n' "$*" >&2
    exit 1
}

find_target_paths() {
    local device_path device_product device_serial device_vendor

    for device_path in /sys/bus/usb/devices/*; do
        [[ -r "$device_path/idVendor" && -r "$device_path/idProduct" ]] || continue
        read -r device_vendor < "$device_path/idVendor"
        read -r device_product < "$device_path/idProduct"
        [[ "$device_vendor:$device_product" == "$TARGET_VENDOR:$TARGET_PRODUCT" ]] || continue
        [[ -r "$device_path/serial" ]] || continue
        read -r device_serial < "$device_path/serial"
        [[ "$device_serial" == "$TARGET_SERIAL" ]] || continue
        printf '%s\n' "$device_path"
    done
}

require_one_target() {
    local -a target_paths

    mapfile -t target_paths < <(find_target_paths)
    (( ${#target_paths[@]} == 1 )) || \
        die "expected one $TARGET_VENDOR:$TARGET_PRODUCT serial $TARGET_SERIAL, found ${#target_paths[@]}"
    printf '%s\n' "${target_paths[0]}"
}

device_bus() {
    local device_path=$1 bus

    read -r bus < "$device_path/busnum"
    printf '%s\n' "$bus"
}

snapshot_device() {
    local device_path=$1 bus device_number interface_path driver

    read -r bus < "$device_path/busnum"
    read -r device_number < "$device_path/devnum"
    printf 'device=%s bus=%s dev=%s serial=%s vidpid=%s:%s\n' \
        "$(basename -- "$device_path")" "$bus" "$device_number" \
        "$TARGET_SERIAL" "$TARGET_VENDOR" "$TARGET_PRODUCT"
    for interface_path in "$device_path":*; do
        [[ -e "$interface_path" ]] || continue
        if [[ -L "$interface_path/driver" ]]; then
            driver=$(basename -- "$(readlink -- "$interface_path/driver")")
        else
            driver=unclaimed
        fi
        printf 'interface=%s driver=%s\n' "${interface_path##*:}" "$driver"
    done
}

snapshot_bus() {
    local device_path bus vendor product serial

    for device_path in /sys/bus/usb/devices/*; do
        [[ -r "$device_path/busnum" && -r "$device_path/idVendor" && \
           -r "$device_path/idProduct" ]] || continue
        read -r bus < "$device_path/busnum"
        [[ "$bus" == "$TARGET_BUS" ]] || continue
        read -r vendor < "$device_path/idVendor"
        read -r product < "$device_path/idProduct"
        serial='-'
        [[ ! -r "$device_path/serial" ]] || read -r serial < "$device_path/serial"
        printf 'bus_device=%s vidpid=%s:%s serial=%s\n' \
            "$(basename -- "$device_path")" "$vendor" "$product" "$serial"
    done
}

stop_capture() {
    capture_status=0
    if [[ -n "$capture_pid" ]] && kill -0 "$capture_pid" 2>/dev/null; then
        kill -INT "$capture_pid" 2>/dev/null || true
    fi
    if [[ -n "$capture_pid" ]]; then
        set +e
        wait "$capture_pid"
        capture_status=$?
        set -e
        capture_pid=''
    fi
}

stop_monitor() {
    if [[ -n "$monitor_pid" ]] && kill -0 "$monitor_pid" 2>/dev/null; then
        kill -TERM "$monitor_pid" 2>/dev/null || true
    fi
    if [[ -n "$monitor_pid" ]]; then
        wait "$monitor_pid" 2>/dev/null || true
        monitor_pid=''
    fi
}

restore_module() {
    if (( module_loaded_by_script )) && [[ -d /sys/module/usbmon ]]; then
        if "$MODPROBE" -r usbmon; then
            printf 'usbmon_restored=unloaded\n'
            module_loaded_by_script=0
        else
            printf 'usbmon_restored=FAILED\n' >&2
            return 1
        fi
    else
        printf 'usbmon_restored=preexisting_or_absent\n'
    fi
}

emergency_cleanup() {
    local status=$?

    trap - EXIT INT TERM
    set +e
    stop_capture >/dev/null
    stop_monitor
    restore_module
    if [[ -n "$capture_dir" && -d "$capture_dir" ]]; then
        printf 'aborted_status=%s\n' "$status" >> "$capture_dir/state.log"
        chown -R "$CAPTURE_OWNER:$CAPTURE_OWNER" "$capture_dir"
    fi
    exit "$status"
}

plan_capture() {
    local target_path bus module_state

    [[ -x "$TCPDUMP" ]] || die "missing $TCPDUMP"
    [[ -x "$MODPROBE" ]] || die "missing $MODPROBE"
    [[ -x "$UDEVADM" ]] || die "missing $UDEVADM"
    [[ -d "$CAPTURE_ROOT" ]] || die "missing durable output root: $CAPTURE_ROOT"
    target_path=$(require_one_target)
    bus=$(device_bus "$target_path")
    [[ "$bus" == "$TARGET_BUS" ]] || \
        die "target moved from expected bus $TARGET_BUS to bus $bus"
    "$TCPDUMP" -y USB_LINUX_MMAPPED -ddd "$CAPTURE_FILTER" >/dev/null
    module_state=absent
    [[ ! -d /sys/module/usbmon ]] || module_state=loaded

    printf 'mode=plan-only\n'
    snapshot_device "$target_path"
    snapshot_bus
    printf 'usbmon_module=%s\n' "$module_state"
    printf 'capture_interface=usbmon%s\n' "$TARGET_BUS"
    printf 'capture_filter=%s\n' "$CAPTURE_FILTER"
    printf 'capture_scope=control-urbs-only\n'
    printf 'snaplen=%s\n' "$CAPTURE_SNAPLEN"
    printf 'max_packets=%s\n' "$CAPTURE_MAX_PACKETS"
    printf 'max_seconds=%s\n' "$CAPTURE_MAX_SECONDS"
    printf 'post_reconnect_seconds=%s\n' "$POST_RECONNECT_SECONDS"
    printf 'module_policy=load-if-absent-and-restore-prior-state\n'
    printf 'device_actions=none\n'
    printf 'capture_requires_explicit_root_invocation=yes\n'
}

capture_reconnect() {
    local target_path initial_target run_id capture_file capture_status
    local capture_stdout capture_stderr udev_log preflight_log postflight_log
    local deadline unplug_seen=0 reconnect_seen=0 reconnected_target=''
    local -a current_targets

    (( EUID == 0 )) || die 'capture must be explicitly invoked as root'
    [[ -x "$TCPDUMP" && -x "$MODPROBE" && -x "$UDEVADM" ]] || \
        die 'required capture tools are unavailable'
    [[ -d "$CAPTURE_ROOT" ]] || die "missing durable output root: $CAPTURE_ROOT"
    getent passwd "$CAPTURE_OWNER" >/dev/null || die "unknown capture owner: $CAPTURE_OWNER"

    initial_target=$(require_one_target)
    [[ "$(device_bus "$initial_target")" == "$TARGET_BUS" ]] || \
        die "target is not on expected bus $TARGET_BUS"
    run_id=$(date +%Y%m%dT%H%M%S%z)
    capture_dir="$CAPTURE_ROOT/passive-usbmon-range-v1-$run_id"
    [[ ! -e "$capture_dir" ]] || die "capture output collision: $capture_dir"
    install -d -m 0700 -o "$CAPTURE_OWNER" -g "$CAPTURE_OWNER" "$capture_dir"
    capture_file="$capture_dir/control-urbs.pcap"
    capture_stdout="$capture_dir/tcpdump.stdout"
    capture_stderr="$capture_dir/tcpdump.stderr"
    udev_log="$capture_dir/udev-kernel-usb.log"
    preflight_log="$capture_dir/preflight.txt"
    postflight_log="$capture_dir/postflight.txt"
    trap emergency_cleanup EXIT INT TERM

    {
        printf 'started=%s\n' "$(date --iso-8601=ns)"
        printf 'authorization=explicit-user-proceed-passive-usbmon\n'
        printf 'script_sha256='
        sha256sum "$SCRIPT_PATH" | awk '{print $1}'
        printf 'capture_filter=%s\n' "$CAPTURE_FILTER"
        printf 'capture_scope=control-urbs-only\n'
        printf 'snaplen=%s\n' "$CAPTURE_SNAPLEN"
        printf 'max_packets=%s\n' "$CAPTURE_MAX_PACKETS"
        printf 'max_seconds=%s\n' "$CAPTURE_MAX_SECONDS"
        snapshot_device "$initial_target"
        snapshot_bus
    } > "$preflight_log"

    if [[ ! -d /sys/module/usbmon ]]; then
        "$MODPROBE" usbmon
        module_loaded_by_script=1
        printf 'usbmon_module=loaded-by-script\n' >> "$preflight_log"
    else
        printf 'usbmon_module=preexisting\n' >> "$preflight_log"
    fi

    for _ in {1..20}; do
        [[ -e "/dev/usbmon$TARGET_BUS" ]] && break
        sleep 0.1
    done
    [[ -e "/dev/usbmon$TARGET_BUS" ]] || \
        die "usbmon character device did not appear: /dev/usbmon$TARGET_BUS"
    "$TCPDUMP" -i "usbmon$TARGET_BUS" -y USB_LINUX_MMAPPED -L \
        > "$capture_dir/linktypes.txt" 2>&1
    "$TCPDUMP" -y USB_LINUX_MMAPPED -ddd "$CAPTURE_FILTER" \
        > "$capture_dir/capture-filter.bpf"

    "$UDEVADM" monitor --kernel --property --subsystem-match=usb \
        > "$udev_log" 2>&1 &
    monitor_pid=$!

    (
        ulimit -f "$CAPTURE_MAX_FILE_BLOCKS"
        exec "$TCPDUMP" --immediate-mode -i "usbmon$TARGET_BUS" \
            -y USB_LINUX_MMAPPED -n -s "$CAPTURE_SNAPLEN" \
            -B "$CAPTURE_BUFFER_KIB" -c "$CAPTURE_MAX_PACKETS" -U \
            -Z "$CAPTURE_OWNER" -w "$capture_file" "$CAPTURE_FILTER"
    ) > "$capture_stdout" 2> "$capture_stderr" &
    capture_pid=$!
    sleep 0.5
    kill -0 "$capture_pid" 2>/dev/null || {
        wait "$capture_pid" || true
        capture_pid=''
        die 'tcpdump exited before capture readiness'
    }

    printf 'capture_ready=%s\n' "$(date --iso-8601=ns)" >> "$capture_dir/state.log"
    printf 'IO24_USBMON_READY capture=%s\n' "$capture_dir"
    printf 'Physically unplug the io24, wait two seconds, and reconnect it to the same port.\n'

    deadline=$((SECONDS + CAPTURE_MAX_SECONDS))
    while (( SECONDS < deadline )); do
        kill -0 "$capture_pid" 2>/dev/null || die 'tcpdump exited during reconnect window'
        mapfile -t current_targets < <(find_target_paths)
        (( ${#current_targets[@]} <= 1 )) || die 'more than one matching io24 appeared'
        if (( ${#current_targets[@]} == 0 )); then
            if (( ! unplug_seen )); then
                unplug_seen=1
                printf 'disconnect_seen=%s\n' "$(date --iso-8601=ns)" \
                    >> "$capture_dir/state.log"
                printf 'IO24_DISCONNECT_SEEN\n'
            fi
        elif (( unplug_seen )); then
            reconnected_target=${current_targets[0]}
            [[ "$(device_bus "$reconnected_target")" == "$TARGET_BUS" ]] || \
                die "reconnected target moved off bus $TARGET_BUS"
            reconnect_seen=1
            printf 'reconnect_seen=%s path=%s\n' \
                "$(date --iso-8601=ns)" "$(basename -- "$reconnected_target")" \
                >> "$capture_dir/state.log"
            printf 'IO24_RECONNECT_SEEN path=%s\n' "$(basename -- "$reconnected_target")"
            break
        fi
        sleep 0.2
    done

    if (( reconnect_seen )); then
        for _ in $(seq 1 $((POST_RECONNECT_SECONDS * 2))); do
            kill -0 "$capture_pid" 2>/dev/null || break
            sleep 0.5
        done
    fi

    stop_capture
    stop_monitor
    {
        printf 'finished=%s\n' "$(date --iso-8601=ns)"
        printf 'disconnect_seen=%s\n' "$unplug_seen"
        printf 'reconnect_seen=%s\n' "$reconnect_seen"
        printf 'tcpdump_status=%s\n' "$capture_status"
        mapfile -t current_targets < <(find_target_paths)
        printf 'matching_devices=%s\n' "${#current_targets[@]}"
        if (( ${#current_targets[@]} == 1 )); then
            snapshot_device "${current_targets[0]}"
        fi
    } > "$postflight_log"
    restore_module >> "$postflight_log"

    [[ -s "$capture_file" ]] || die 'capture file is empty'
    (
        cd -- "$capture_dir"
        sha256sum capture-filter.bpf control-urbs.pcap linktypes.txt \
            postflight.txt preflight.txt state.log tcpdump.stderr \
            tcpdump.stdout udev-kernel-usb.log > SHA256SUMS
    )
    chown -R "$CAPTURE_OWNER:$CAPTURE_OWNER" "$capture_dir"
    trap - EXIT INT TERM

    printf 'IO24_USBMON_COMPLETE capture=%s\n' "$capture_dir"
    (( unplug_seen && reconnect_seen )) || return 3
    (( capture_status == 0 )) || return "$capture_status"
}

case "${1:-}" in
    plan)
        (( $# == 1 )) || die 'usage: io24_usbmon_passive_reconnect.sh plan'
        plan_capture
        ;;
    capture)
        (( $# == 1 )) || die 'usage: io24_usbmon_passive_reconnect.sh capture'
        capture_reconnect
        ;;
    *)
        die 'usage: io24_usbmon_passive_reconnect.sh {plan|capture}'
        ;;
esac
