#!/usr/bin/env bash
# Run Wine/Universal Control probes without exposing the Linux desktop or hardware.
#
# The outer process creates a transient systemd service with hard resource limits.
# Bubblewrap then supplies a disposable home/prefix, a private /run and /sys,
# a minimal /dev, and loopback-only networking.  The live-USB modes expose only
# the selected io24 node after the offline gates have passed.
set -euo pipefail

readonly SCRIPT_PATH="$(readlink -f -- "${BASH_SOURCE[0]}")"
readonly PROJECT_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")/.." && pwd -P)"
readonly UC_DIR="${UC_DIR:-/home/ajuntanaga/Documents/Universal Control}"
readonly WINE=/opt/wine-staging/bin/wine
readonly WINEBOOT=/opt/wine-staging/bin/wineboot
readonly WINEGCC=/opt/wine-staging/bin/winegcc
readonly WINESERVER=/opt/wine-staging/bin/wineserver
readonly WINE_NTOSKRNL=/opt/wine-staging/lib/wine/x86_64-windows/ntoskrnl.exe
readonly WINE_NTDLL=/opt/wine-staging/lib/wine/x86_64-windows/ntdll.dll
readonly WINE_WINEUSB=/opt/wine-staging/lib/wine/x86_64-windows/wineusb.sys
readonly WINE_WINEUSB_SO=/opt/wine-staging/lib/wine/x86_64-unix/wineusb.so
# This exact Wine 11.15 build returns false for every NT DDI version query.
readonly WINE_NTDDI_FALSE_STUB_SHA256=8826a8bb2335df7f5dcea9494582031cb539358c1ba0af32d60915d6b59c06e9
readonly CORRECTED_NTOSKRNL_SHA256=259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e
readonly CORRECTED_NTOSKRNL_SO_SHA256=3c1556529d6b44bf0826eca3498b47d53cf46b0150a51e595a14e73607e2b8a6
readonly WINE_NTDLL_ORIGINAL_SHA256=d18d18318a70e3d833598a0b9e62c950a8d878b1d530d8cf88a108e5fddd8a7c
readonly PATCHED_NTDLL_SHA256=35729f3c03ed11c4a6ad33605d00b7280bc83f1d93044dd169132e0c673740de
readonly WINE_WINEUSB_ORIGINAL_SHA256=7a974393bffa48ad60f3217a8d3e8d9ed065aad8667b3d8638a497308c734285
readonly WINE_WINEUSB_SO_ORIGINAL_SHA256=8979d5e5c7d1667e2ea1864054f07a87719ea76fe8fc806bcd6b71a042495baf
readonly WINEUSB_RANGE_V2_FAKE_PE_SHA256=b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e
readonly WINEUSB_RANGE_V2_BUILTIN_SHA256=404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa
readonly WINEUSB_RANGE_V2_UNIXLIB_SHA256=9518320f495ace5cabc27ef4e740f182b3840700fba3e9371b36b7e12538dea2
readonly USBTAP_RESOLVER_V6_SHA256=dbce256b328b53866dd13dbe382c28b216a1baf64bdb47fc746b722375e86977
readonly REG=/tmp/prefix/drive_c/windows/system32/reg.exe
readonly SC=/tmp/prefix/drive_c/windows/system32/sc.exe
readonly XVFB=/tmp/xvfb-root/usr/bin/Xvfb
readonly DISPLAY_NUMBER=:98
readonly X_SOCKET=/tmp/.X11-unix/X98
readonly OUT=/tmp/out
readonly CORRECTED_NTOSKRNL_ROOT="$OUT/wine-ntddi"
readonly CORRECTED_NTOSKRNL="$CORRECTED_NTOSKRNL_ROOT/x86_64-windows/ntoskrnl.exe"
readonly CORRECTED_NTOSKRNL_SO="$CORRECTED_NTOSKRNL_ROOT/x86_64-unix/ntoskrnl.exe.so"
readonly PATCHED_NTDLL_ROOT="$OUT/wine-rtl-registry-handle"
readonly PATCHED_NTDLL="$PATCHED_NTDLL_ROOT/x86_64-windows/ntdll.dll"
readonly WINEUSB_RANGE_V2_ROOT="$PROJECT_DIR/re/wineusb-class-interface-range-v2"
readonly WINEUSB_RANGE_V2_FAKE_PE="$WINEUSB_RANGE_V2_ROOT/x86_64-windows/wineusb.sys"
readonly WINEUSB_RANGE_V2_BUILTIN="$WINEUSB_RANGE_V2_ROOT/x86_64-unix/wineusb.sys.so"
readonly WINEUSB_RANGE_V2_UNIXLIB="$WINEUSB_RANGE_V2_ROOT/x86_64-unix/wineusb.so"
readonly PREFIX_NTOSKRNL=/tmp/prefix/drive_c/windows/system32/ntoskrnl.exe
readonly PREFIX_NTDLL=/tmp/prefix/drive_c/windows/system32/ntdll.dll
readonly PREFIX_WINEUSB=/tmp/prefix/drive_c/windows/system32/drivers/wineusb.sys
readonly DRIVER_REGISTRY_TRACE="${IO24_DRIVER_REGISTRY_TRACE:-0}"

xvfb_pid=''
service_name=''

die() {
    printf 'io24 Wine sandbox: %s\n' "$*" >&2
    exit 1
}

case "$DRIVER_REGISTRY_TRACE" in
    0|1) ;;
    *) die 'IO24_DRIVER_REGISTRY_TRACE must be 0 or 1' ;;
esac

assert_inner_driver_overlays() {
    local binary hash

    [[ -s "$CORRECTED_NTOSKRNL_SO" ]] || \
        die 'corrected Wine kernel builtin is unavailable'
    read -r hash _ < <(sha256sum -- "$CORRECTED_NTOSKRNL_SO")
    [[ "$hash" == "$CORRECTED_NTOSKRNL_SO_SHA256" ]] || \
        die 'unexpected corrected Wine kernel builtin'

    for binary in "$CORRECTED_NTOSKRNL" "$WINE_NTOSKRNL" "$PREFIX_NTOSKRNL"; do
        [[ -s "$binary" ]] || die "corrected Wine kernel is unavailable: $binary"
        read -r hash _ < <(sha256sum -- "$binary")
        [[ "$hash" == "$CORRECTED_NTOSKRNL_SHA256" ]] || \
            die "unexpected corrected Wine kernel at $binary"
    done
    for binary in "$PATCHED_NTDLL" "$WINE_NTDLL" "$PREFIX_NTDLL"; do
        [[ -s "$binary" ]] || die "patched Wine ntdll is unavailable: $binary"
        read -r hash _ < <(sha256sum -- "$binary")
        [[ "$hash" == "$PATCHED_NTDLL_SHA256" ]] || \
            die "unexpected Wine registry-handle ntdll at $binary"
    done
    for binary in "$WINEUSB_RANGE_V2_FAKE_PE" "$WINE_WINEUSB" "$PREFIX_WINEUSB"; do
        [[ -s "$binary" ]] || die "RANGE-v2 wineusb fake PE is unavailable: $binary"
        read -r hash _ < <(sha256sum -- "$binary")
        [[ "$hash" == "$WINEUSB_RANGE_V2_FAKE_PE_SHA256" ]] || \
            die "unexpected RANGE-v2 wineusb fake PE at $binary"
    done
    [[ -s "$WINEUSB_RANGE_V2_BUILTIN" ]] || \
        die 'RANGE-v2 wineusb builtin is unavailable'
    read -r hash _ < <(sha256sum -- "$WINEUSB_RANGE_V2_BUILTIN")
    [[ "$hash" == "$WINEUSB_RANGE_V2_BUILTIN_SHA256" ]] || \
        die 'unexpected RANGE-v2 wineusb builtin'
    for binary in "$WINEUSB_RANGE_V2_UNIXLIB" "$WINE_WINEUSB_SO"; do
        [[ -s "$binary" ]] || \
            die "RANGE-v2 wineusb Unix library is unavailable: $binary"
        read -r hash _ < <(sha256sum -- "$binary")
        [[ "$hash" == "$WINEUSB_RANGE_V2_UNIXLIB_SHA256" ]] || \
            die "unexpected RANGE-v2 wineusb Unix library at $binary"
    done
}

usage() {
    cat >&2 <<'EOF'
usage: tests/uc_wine_sandbox.sh MODE SANDBOX_ROOT

MODE is one of:
  audit    verify namespace, device, home, display, and network isolation
  init     initialize a new disposable Wine prefix (hard-capped at 1 GiB)
  update   finish/update an existing disposable Wine prefix
  drivers  register Wine's own winebus/wineusb INFs with USB hidden
  presonus-driver  stage official io24 driver payloads with USB hidden
  smoke    run an 8-second `wine cmd /c exit 0` prefix smoke test
  driver-load  load the staged PreSonus driver with the RANGE-v2 overlay
  service  install/start the UC service with USB still hidden
  live-audit  bind the io24 node and verify isolation without opening it
  live-read  expose only the io24 and run non-mutating Subscribe/Synchronize

SANDBOX_ROOT must be a private /tmp/io24-wine-sandbox.XXXXXX directory or
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.XXXXXX on-disk clone.
It must contain an extracted Xvfb at xvfb-root/usr/bin/Xvfb.
driver-load always runs the exact one-handle NT registry probe before loading
the driver. Set IO24_DRIVER_REGISTRY_TRACE=1 to also write a separate +reg
driver trace.
EOF
    exit 2
}

cleanup_inner() {
    local status=$?
    trap - EXIT INT TERM
    set +e
    if [[ -n "$service_name" ]]; then
        timeout --signal=TERM --kill-after=2s 5s \
            "$WINE" "$SC" stop "$service_name" >"$OUT/service-stop.log" 2>&1
    fi
    timeout --signal=TERM --kill-after=2s 5s "$WINESERVER" -k \
        >/dev/null 2>&1
    timeout --signal=TERM --kill-after=2s 5s "$WINESERVER" -w \
        >/dev/null 2>&1
    if [[ -n "$xvfb_pid" ]]; then
        kill -TERM "$xvfb_pid" >/dev/null 2>&1
        wait "$xvfb_pid" >/dev/null 2>&1
    fi
    exit "$status"
}

assert_inner_isolation() {
    local forbidden
    for forbidden in \
        /dev/dri \
        /dev/snd \
        /run/udev/control \
        /run/user/1000/bus \
        /home/ajuntanaga/.wine-io24; do
        [[ ! -e "$forbidden" ]] || \
            die "isolation failure: $forbidden is visible"
    done

    if [[ "${IO24_SANDBOX_LIVE_USB:-0}" == 1 ]]; then
        local usb_node="/dev/bus/usb/${IO24_USB_BUS:?}/${IO24_USB_DEV:?}"
        local sys_device="/sys/bus/usb/devices/${IO24_USB_SYS_NAME:?}"
        local device_count
        local -a usb_nodes
        [[ -c "$usb_node" && -r "$usb_node" && -w "$usb_node" ]] || \
            die 'live gate does not expose the expected io24 node'
        shopt -s nullglob
        usb_nodes=(/dev/bus/usb/*/*)
        shopt -u nullglob
        device_count=${#usb_nodes[@]}
        [[ "$device_count" == 1 && "${usb_nodes[0]-}" == "$usb_node" ]] || \
            die "live gate exposes $device_count USB device nodes instead of one"
        [[ "$(sed -n '1p' "$sys_device/idVendor")" == 194f ]] || \
            die 'live gate vendor check failed'
        [[ "$(sed -n '1p' "$sys_device/idProduct")" == 0422 ]] || \
            die 'live gate product check failed'
        [[ "$(sed -n '1p' "$sys_device/serial")" == "$IO24_USB_SERIAL" ]] || \
            die 'live gate serial check failed'
        findmnt -n -o VFS-OPTIONS /sys | grep -Eq '(^|,)ro(,|$)' || \
            die 'live gate sysfs is not read-only'
    else
        [[ ! -e /dev/bus/usb ]] || \
            die 'isolation failure: USB device nodes are visible'
        if find /sys -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
            die 'isolation failure: host sysfs is visible'
        fi
    fi
    if ip -o link show | grep -Ev '^[0-9]+: lo:' | grep -q .; then
        die 'isolation failure: a non-loopback network interface is visible'
    fi
    if ! ip -o link show dev lo | grep -q '<LOOPBACK,UP'; then
        die 'isolation failure: private loopback is not usable'
    fi
    if ip -o route show | grep -q .; then
        die 'isolation failure: a network route is visible'
    fi
    if [[ "${IO24_SANDBOX_LIVE_USB:-0}" == 1 ]]; then
        printf 'live isolation verified: one io24 node; no audio, GPU, home, bus, or external network\n'
    else
        printf 'offline isolation verified: no host home, hardware, bus, or network\n'
    fi
}

prepare_inner_dirs() {
    mkdir -p \
        /tmp/.X11-unix \
        /tmp/home \
        /tmp/runtime \
        "$OUT/cache" \
        "$OUT/config" \
        "$OUT/data"
    chmod 1777 /tmp/.X11-unix
    chmod 700 /tmp/home /tmp/runtime "$OUT" "$OUT/cache" "$OUT/config" "$OUT/data"
}

start_xvfb() {
    [[ -x "$XVFB" ]] || die "missing isolated Xvfb: $XVFB"
    if [[ -S "$X_SOCKET" ]]; then
        rm -f -- "$X_SOCKET"
    elif [[ -e "$X_SOCKET" ]]; then
        die "refusing to replace non-socket path: $X_SOCKET"
    fi

    "$XVFB" "$DISPLAY_NUMBER" \
        -screen 0 1024x768x24 \
        -nolisten tcp \
        -noreset \
        -ac \
        -extension GLX \
        >"$OUT/xvfb.log" 2>&1 &
    xvfb_pid=$!

    local attempt
    for attempt in {1..50}; do
        [[ -S "$X_SOCKET" ]] && break
        kill -0 "$xvfb_pid"
        sleep 0.05
    done
    [[ -S "$X_SOCKET" ]] || die 'isolated Xvfb did not create its socket'
    DISPLAY="$DISPLAY_NUMBER" xdpyinfo >"$OUT/xdpyinfo.log" 2>&1
    grep -q 'dimensions:.*1024x768 pixels' "$OUT/xdpyinfo.log" || \
        die 'isolated Xvfb geometry check failed'
}

inner_init() {
    [[ ! -e /tmp/prefix/system.reg ]] || \
        die 'init requires a new disposable prefix'
    prepare_inner_dirs
    assert_inner_isolation
    start_xvfb
    timeout --signal=TERM --kill-after=3s 180s \
        "$WINEBOOT" --init >"$OUT/wineboot.log" 2>&1
    [[ -s /tmp/prefix/system.reg ]] || die 'wineboot did not create system.reg'
    [[ -d /tmp/prefix/drive_c/windows/system32 ]] || \
        die 'wineboot did not populate system32'
    printf 'disposable prefix initialization completed\n'
}

inner_update() {
    [[ -s /tmp/prefix/system.reg ]] || die 'disposable prefix has no system.reg'
    prepare_inner_dirs
    assert_inner_isolation
    start_xvfb
    if find_service; then
        timeout --signal=TERM --kill-after=2s 6s "$WINE" "$REG" add \
            'HKLM\System\CurrentControlSet\Services\PreSonus Hardware Access Service' \
            /v Start /t REG_DWORD /d 3 /f \
            >"$OUT/update-service-config.log" 2>&1
        timeout --signal=TERM --kill-after=2s 6s \
            "$WINE" "$SC" stop "$service_name" \
            >"$OUT/update-service-stop.log" 2>&1 || true
        timeout --signal=TERM --kill-after=2s 6s "$WINESERVER" -k \
            >/dev/null 2>&1
        timeout --signal=TERM --kill-after=2s 6s "$WINESERVER" -w \
            >/dev/null 2>&1
    fi
    timeout --signal=TERM --kill-after=3s 120s \
        "$WINEBOOT" --update >"$OUT/wineboot-update.log" 2>&1
    [[ -s /tmp/prefix/drive_c/windows/system32/winmm.dll ]] || \
        die 'wineboot update did not populate winmm.dll'
    [[ -s /tmp/prefix/drive_c/windows/system32/ws2_32.dll ]] || \
        die 'wineboot update did not populate ws2_32.dll'
    printf 'disposable prefix update completed\n'
}

inner_drivers() {
    local inf
    local registry_pattern='System\\\\ControlSet001\\\\Services\\\\wineusb'
    [[ -s /tmp/prefix/system.reg ]] || die 'disposable prefix has no system.reg'
    for inf in winebus.inf wineusb.inf; do
        [[ -s "/tmp/prefix/drive_c/windows/inf/$inf" ]] || \
            die "disposable prefix is missing $inf"
    done
    prepare_inner_dirs
    assert_inner_isolation
    start_xvfb

    for inf in winebus.inf wineusb.inf; do
        timeout --signal=TERM --kill-after=2s 8s \
            "$WINE" /tmp/prefix/drive_c/windows/system32/rundll32.exe \
            setupapi.dll,InstallHinfSection \
            DefaultInstall 128 "C:\\windows\\inf\\$inf" \
            >"$OUT/${inf%.inf}-default-install.log" 2>&1 || true
    done
    timeout --signal=TERM --kill-after=2s 6s "$WINESERVER" -k >/dev/null 2>&1
    timeout --signal=TERM --kill-after=2s 6s "$WINESERVER" -w >/dev/null 2>&1

    if ! grep -Eqi "$registry_pattern" /tmp/prefix/system.reg; then
        for inf in winebus.inf wineusb.inf; do
            timeout --signal=TERM --kill-after=2s 8s \
                "$WINE" /tmp/prefix/drive_c/windows/system32/rundll32.exe \
                setupapi.dll,InstallHinfSection \
                device_section 128 "C:\\windows\\inf\\$inf" \
                >"$OUT/${inf%.inf}-device-install.log" 2>&1 || true
        done
        timeout --signal=TERM --kill-after=2s 6s "$WINESERVER" -k >/dev/null 2>&1
        timeout --signal=TERM --kill-after=2s 6s "$WINESERVER" -w >/dev/null 2>&1
    fi

    grep -Eqi 'System\\\\ControlSet001\\\\Services\\\\winebus' \
        /tmp/prefix/system.reg || die 'winebus service registration is missing'
    grep -Eqi "$registry_pattern" /tmp/prefix/system.reg || \
        die 'wineusb service registration is missing'
    printf 'Wine bus and USB drivers registered in the disposable prefix\n'
}

inner_presonus_driver() {
    readonly driver_root=/run/io24-uc/Drivers/DSPUSBSeries/x64
    readonly driver_inf="$driver_root/paedspusb.inf"
    readonly driver_catalog="$driver_root/paedspusb.cat"
    readonly driver_binary="$driver_root/paedspusb.sys"
    readonly stage_helper="$OUT/io24-stage-driver.exe"
    local decoded_inf="$OUT/paedspusb.inf.txt"
    local compatibility_text="$OUT/paedspusb-wine.inf.txt"
    local compatibility_inf="$OUT/paedspusb-wine.inf"
    local matched_inf=0
    local matched_catalog=0
    local matched_binary=0
    local candidate
    local -a driver_store_files windows_inf_files

    [[ -s /tmp/prefix/system.reg ]] || die 'disposable prefix has no system.reg'
    [[ -s "$driver_inf" && -s "$driver_catalog" && -s "$driver_binary" ]] || \
        die 'official PreSonus base driver package is incomplete'
    [[ -x "$stage_helper" && -x "$stage_helper.so" ]] || \
        die 'PreSonus driver staging helper is unavailable'

    prepare_inner_dirs
    assert_inner_isolation
    start_xvfb

    iconv -f UTF-16LE -t UTF-8 "$driver_inf" >"$decoded_inf"
    grep -Fq 'USB\VID_194F&PID_0422&MI_00' "$decoded_inf" || \
        die 'official INF does not match the Revelator io24 base interface'
    grep -Fqi '{30A505D7-159E-4585-B453-768409AA2D22}' "$decoded_inf" || \
        die 'official INF does not declare the UC device interface GUID'
    [[ "$(tr -d '\r' <"$decoded_inf" | \
        grep -Fxc '%S_Mfg% = _Models,ntamd64.10.0...17134')" == 1 ]] || \
        die 'official INF manufacturer decoration changed unexpectedly'
    [[ "$(tr -d '\r' <"$decoded_inf" | \
        grep -Fxc '[_Models.ntamd64.10.0...17134]')" == 1 ]] || \
        die 'official INF model decoration changed unexpectedly'

    # Wine 11.15 does not resolve build-decorated model sections. Create a
    # disposable derivative and relax only its two section decorations.
    tr -d '\r' <"$decoded_inf" | sed \
        -e 's/^%S_Mfg% = _Models,ntamd64\.10\.0\.\.\.17134$/%S_Mfg% = _Models,ntamd64/' \
        -e 's/^\[_Models\.ntamd64\.10\.0\.\.\.17134\]$/[_Models.ntamd64]/' \
        >"$compatibility_text"
    [[ "$(grep -Fxc '%S_Mfg% = _Models,ntamd64' \
        "$compatibility_text")" == 1 ]] || \
        die 'Wine compatibility INF manufacturer rewrite failed'
    [[ "$(grep -Fxc '[_Models.ntamd64]' "$compatibility_text")" == 1 ]] || \
        die 'Wine compatibility INF model rewrite failed'
    iconv -f UTF-8 -t UTF-16LE "$compatibility_text" >"$compatibility_inf"
    cp -- "$driver_catalog" "$OUT/PaeDSPUSB.cat"
    cp -- "$driver_binary" "$OUT/PaeDSPUSB.sys"

    timeout --signal=TERM --kill-after=3s 30s \
        "$stage_helper" \
        'Z:\tmp\out\paedspusb-wine.inf' \
        >"$OUT/presonus-driver-stage.log" 2>&1
    timeout --signal=TERM --kill-after=2s 6s "$WINESERVER" -k >/dev/null 2>&1
    timeout --signal=TERM --kill-after=2s 6s "$WINESERVER" -w >/dev/null 2>&1

    mapfile -d '' driver_store_files < <(
        find /tmp/prefix/drive_c/windows/system32 -maxdepth 4 -type f \
            -ipath '*/paedspusb-wine.inf_*/*' \
            \( -iname paedspusb-wine.inf -o -iname paedspusb.cat -o \
               -iname paedspusb.sys \) -print0
    )
    for candidate in "${driver_store_files[@]}"; do
        case "${candidate,,}" in
            */paedspusb-wine.inf)
                cmp -s "$compatibility_inf" "$candidate" && matched_inf=1
                ;;
            */paedspusb.cat)
                cmp -s "$driver_catalog" "$candidate" && matched_catalog=1
                ;;
            */paedspusb.sys)
                cmp -s "$driver_binary" "$candidate" && matched_binary=1
                ;;
        esac
    done
    (( matched_inf == 1 && matched_catalog == 1 && matched_binary == 1 )) || \
        die 'Wine driver store does not contain the compatibility package and official payloads'

    mapfile -d '' windows_inf_files < <(
        find /tmp/prefix/drive_c/windows/inf -maxdepth 1 -type f \
            \( -iname paedspusb-wine.inf -o -iname 'oem*.inf' \) -print0
    )
    for candidate in "${windows_inf_files[@]}"; do
        if cmp -s "$compatibility_inf" "$candidate"; then
            matched_inf=2
            break
        fi
    done
    (( matched_inf == 2 )) || \
        die 'Wine-compatible PreSonus INF was not published to the Wine INF directory'
    printf 'Wine-compatible PreSonus io24 base driver staged with USB hidden\n'
}

inner_smoke() {
    [[ -s /tmp/prefix/system.reg ]] || die 'disposable prefix has no system.reg'
    prepare_inner_dirs
    assert_inner_isolation
    start_xvfb
    timeout --signal=TERM --kill-after=2s 8s \
        "$WINE" cmd /d /c exit 0 >"$OUT/wine-cmd.log" 2>&1
    printf 'wine-cmd-ok\n'
}

inner_driver_load() {
    local start_status query_status probe_status
    local driver_log="$OUT/driver-load.log"
    local query_log="$OUT/driver-query.log"
    local status_log="$OUT/driver-load-status.txt"
    local registry_probe="$OUT/io24-registry-probe.exe"
    local wine_debug=+ntoskrnl,+plugplay,+setupapi,+module

    if [[ "$DRIVER_REGISTRY_TRACE" == 1 ]]; then
        driver_log="$OUT/driver-load-registry.log"
        query_log="$OUT/driver-query-registry.log"
        status_log="$OUT/driver-load-registry-status.txt"
        wine_debug+=,+reg
    fi

    [[ -s /tmp/prefix/system.reg ]] || die 'disposable prefix has no system.reg'
    [[ -s /tmp/prefix/drive_c/windows/system32/unknown/PaeDSPUSB.sys ]] || \
        die 'staged PreSonus base driver is unavailable'
    grep -Eqi '^\[System\\\\ControlSet001\\\\Services\\\\PaeDSPUSB\]' \
        /tmp/prefix/system.reg || die 'PaeDSPUSB service registration is missing'
    assert_inner_driver_overlays

    prepare_inner_dirs
    assert_inner_isolation
    start_xvfb
    service_name=PaeDSPUSB

    [[ -x "$registry_probe" && -x "$registry_probe.so" ]] || \
        die 'exact NT registry probe is unavailable'
    set +e
    WINEDEBUG=-all \
        timeout --signal=TERM --kill-after=2s 12s \
        "$registry_probe" >"$OUT/registry-probe.log" 2>&1
    probe_status=$?
    set -e
    printf 'exact NT registry probe status: %d\n' "$probe_status"
    (( probe_status == 0 )) || \
        die "exact NT registry probe failed with status $probe_status"
    grep -Fq \
        'NtQueryValueKey name=tag class=partial buffer=47 status=0x00000000' \
        "$OUT/registry-probe.log" || die 'driver-sized tag query did not pass'
    grep -Fq \
        'RtlQueryRegistryValues callback name=format status=0x00000000 callback_status=0x00000000 value=0x00000006 expected=0x00000006' \
        "$OUT/registry-probe.log" || die 'format query did not pass'
    grep -Fq \
        'RtlQueryRegistryValues callback name=options status=0x00000000 callback_status=0x00000000 value=0x0000010c expected=0x0000010c' \
        "$OUT/registry-probe.log" || die 'same-handle options query did not pass'
    grep -Fq \
        'RtlQueryRegistryValues callback name=customer status=0x00000000 callback_status=0x00000000 value=0x00000361 expected=0x00000361' \
        "$OUT/registry-probe.log" || die 'same-handle customer query did not pass'
    grep -Fq \
        'NtClose caller-owned License status=0x00000000' \
        "$OUT/registry-probe.log" || die 'caller-owned license handle was not valid at close'

    # The probe starts services.exe with WINEDEBUG disabled. Restart the
    # disposable Wine server so the driver inherits the focused trace channels.
    timeout --signal=TERM --kill-after=2s 5s "$WINESERVER" -k \
        >"$OUT/registry-probe-wineserver-stop.log" 2>&1
    timeout --signal=TERM --kill-after=2s 5s "$WINESERVER" -w \
        >>"$OUT/registry-probe-wineserver-stop.log" 2>&1

    set +e
    WINEDEBUG="$wine_debug" \
        timeout --signal=TERM --kill-after=3s 20s \
        "$WINE" "$SC" start "$service_name" >"$driver_log" 2>&1
    start_status=$?
    timeout --signal=TERM --kill-after=2s 6s \
        "$WINE" "$SC" query "$service_name" \
        >"$query_log" 2>&1
    query_status=$?
    set -e

    {
        printf 'start_status=%d\n' "$start_status"
        printf 'query_status=%d\n' "$query_status"
    } >"$status_log"
    printf 'PaeDSPUSB start status: %d; query status: %d\n' \
        "$start_status" "$query_status"

    if grep -Fq 'RtlIsNtDdiVersionAvailable stub:' "$driver_log"; then
        die 'the Wine NT DDI false stub was still executed'
    fi
    grep -Eq \
        'trace:ntoskrnl:RtlIsNtDdiVersionAvailable 0x0*6010000\.' \
        "$driver_log" || die 'the corrected Windows 7 NT DDI path was not observed'
    if grep -Fq \
        'unimplemented function ntoskrnl.exe.ExIsProcessorFeaturePresent' \
        "$driver_log"; then
        die 'the Wine processor-feature export is still an unimplemented stub'
    fi
    grep -Eq \
        'trace:ntoskrnl:ExIsProcessorFeaturePresent 10\.' \
        "$driver_log" || die 'the corrected SSE2 feature-query path was not observed'

    printf 'registry-handle, Windows 7 NT DDI, and SSE2 gates executed with USB hidden\n'
}

find_service() {
    local candidate
    for candidate in \
        HardwareAccessDaemon \
        PreSonusHardwareAccessService \
        'PreSonus Hardware Access Service'; do
        if timeout --signal=TERM --kill-after=2s 6s \
                "$WINE" "$SC" query "$candidate" \
                >"$OUT/service-query-candidate.log" 2>&1; then
            service_name=$candidate
            return 0
        fi
    done
    return 1
}

inner_service() {
    readonly service_exe=/run/io24-uc/PreSonusHardwareAccessService.exe
    readonly probe=/run/io24-project/tests/ucnet_service_probe.py
    local live_usb="${IO24_SANDBOX_LIVE_USB:-0}"
    local startup_winedebug=-all
    local -a staged_driver_binaries
    [[ -s /tmp/prefix/system.reg ]] || die 'disposable prefix has no system.reg'
    [[ -x "$service_exe" ]] || die 'UC service executable is unavailable'
    [[ -f "$probe" ]] || die 'read-only UCNET probe is unavailable'

    prepare_inner_dirs
    assert_inner_isolation
    start_xvfb
    cd /run/io24-uc

    if [[ "$live_usb" == 1 ]]; then
        [[ "${LIBUSB_DEBUG:-}" == 4 ]] || \
            die 'live read requires libusb debug level 4'
        printf 'libusb debug level: %s\n' "$LIBUSB_DEBUG"
        assert_inner_driver_overlays
        [[ -s /tmp/prefix/drive_c/windows/inf/paedspusb-wine.inf ]] || \
            die 'live read requires the staged Wine-compatible PreSonus INF'
        mapfile -d '' staged_driver_binaries < <(
            find /tmp/prefix/drive_c/windows/system32 -maxdepth 4 -type f \
                -ipath '*/paedspusb-wine.inf_*/*' \
                -iname paedspusb.sys -print0
        )
        (( ${#staged_driver_binaries[@]} == 1 )) || \
            die 'live read requires one staged PreSonus base driver binary'
        startup_winedebug=+plugplay,+setupapi,+ntoskrnl
    fi

    set +e
    WINEDEBUG="$startup_winedebug" timeout --signal=TERM --kill-after=3s 15s \
        "$WINE" "$service_exe" -install >"$OUT/service-install.log" 2>&1
    local install_status=$?
    set -e
    printf 'service installer status: %d\n' "$install_status"
    if (( install_status != 0 )); then
        set +e
        WINEDEBUG=+loaddll,+module \
            timeout --signal=TERM --kill-after=2s 8s \
            "$WINE" "$service_exe" -install \
            >"$OUT/service-loader.log" 2>&1
        local loader_status=$?
        set -e
        printf 'loader diagnostic status: %d\n' "$loader_status"
    fi

    if ! find_service; then
        grep -Eni 'HardwareAccess|PreSonusHardware' /tmp/prefix/system.reg \
            >"$OUT/service-registry-hits.log" 2>&1 || true
        die 'service registration was not found'
    fi
    printf '%s\n' "$service_name" >"$OUT/service-name.txt"
    printf 'registered service: %s\n' "$service_name"
    timeout --signal=TERM --kill-after=2s 6s "$WINE" "$REG" add \
        'HKLM\System\CurrentControlSet\Services\PreSonus Hardware Access Service' \
        /v Start /t REG_DWORD /d 3 /f \
        >"$OUT/service-config.log" 2>&1

    if ! grep -q RUNNING "$OUT/service-query-candidate.log"; then
        timeout --signal=TERM --kill-after=3s 10s \
            "$WINE" "$SC" start "$service_name" >"$OUT/service-start.log" 2>&1
    fi
    local service_deadline=$((SECONDS + 15))
    local service_attempt=0
    local service_running=0
    while (( SECONDS < service_deadline )); do
        service_attempt=$((service_attempt + 1))
        if timeout --signal=TERM --kill-after=1s 2s \
            "$WINE" "$SC" query "$service_name" \
            >"$OUT/service-query-running.log" 2>&1 &&
            grep -Eq 'STATE[[:space:]]*:[[:space:]]*4[[:space:]]+RUNNING' \
                "$OUT/service-query-running.log"; then
            service_running=1
            break
        fi
        sleep 0.5
    done
    printf 'service readiness checks: %d\n' "$service_attempt"
    (( service_running == 1 )) || \
        die 'service did not reach RUNNING within 15 seconds'
    if [[ "$live_usb" == 1 ]]; then
        printf 'service reports RUNNING with only the io24 exposed\n'
    else
        printf 'service reports RUNNING with USB hidden\n'
    fi

    set +e
    timeout --signal=TERM --kill-after=2s 14s \
        python3 "$probe" --timeout 8 --output "$OUT/synchronize.json" \
        >"$OUT/probe.log" 2>&1
    local probe_status=$?
    set -e
    if [[ "$live_usb" == 1 && $probe_status -eq 0 ]]; then
        grep -Eq '^ffff8800[0-9a-f]{8} [0-9]+ [SCE] ' \
            "${IO24_USBLOG:?}" || \
            die 'non-mutating synchronization succeeded but no USB traffic was captured'
        printf 'live non-mutating Subscribe/Synchronize and USB capture completed\n'
    elif [[ "$live_usb" == 1 ]]; then
        die "live non-mutating service probe failed with status $probe_status"
    elif (( probe_status == 0 )); then
        printf 'read-only Subscribe/Synchronize completed with USB hidden\n'
    elif grep -q 'no UCNET DA announcement' "$OUT/probe.log"; then
        printf 'service is healthy; no device announcement was expected with USB hidden\n'
    else
        die "read-only service probe failed with status $probe_status"
    fi
}

inner_main() {
    trap cleanup_inner EXIT INT TERM
    case "${IO24_SANDBOX_MODE:-}" in
        audit)
            prepare_inner_dirs
            assert_inner_isolation
            ;;
        init)
            inner_init
            ;;
        update)
            inner_update
            ;;
        drivers)
            inner_drivers
            ;;
        presonus-driver)
            inner_presonus_driver
            ;;
        smoke)
            inner_smoke
            ;;
        driver-load)
            inner_driver_load
            ;;
        service)
            inner_service
            ;;
        live-audit)
            prepare_inner_dirs
            assert_inner_isolation
            ;;
        live-read)
            inner_service
            ;;
        *)
            die 'invalid inner mode'
            ;;
    esac
}

if [[ "${IO24_SANDBOX_INNER:-0}" == 1 ]]; then
    inner_main
    exit
fi

(( $# == 2 )) || usage
readonly mode=$1
readonly requested_root=$2
case "$mode" in
    audit|init|update|drivers|presonus-driver|smoke|driver-load|service|live-audit|live-read) ;;
    *) usage ;;
esac

[[ -d "$requested_root" ]] || die "sandbox root is not a directory: $requested_root"
[[ ! -L "$requested_root" ]] || die 'sandbox root must not be a symlink'
readonly sandbox_root="$(readlink -f -- "$requested_root")"
case "$sandbox_root" in
    /tmp/io24-wine-sandbox.*)
        sandbox_tail=${sandbox_root#/tmp/io24-wine-sandbox.}
        ;;
    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.*)
        sandbox_tail=${sandbox_root#/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.}
        ;;
    *)
        die 'sandbox root is outside the approved private locations'
        ;;
esac
readonly sandbox_tail
[[ -n "$sandbox_tail" && "$sandbox_tail" != */* ]] || \
    die 'sandbox root name must end in one nonempty component'
[[ "$(stat -c %u -- "$sandbox_root")" == "$(id -u)" ]] || \
    die 'sandbox root must be owned by the current user'
chmod 700 -- "$sandbox_root"

for path in prefix out home runtime .X11-unix; do
    [[ ! -L "$sandbox_root/$path" ]] || die "sandbox path is a symlink: $path"
    mkdir -p -- "$sandbox_root/$path"
done
[[ -x "$sandbox_root/xvfb-root/usr/bin/Xvfb" ]] || \
    die 'extract the Ubuntu xvfb package to SANDBOX_ROOT/xvfb-root first'
[[ -x "$WINE" && -x "$WINEBOOT" && -x "$WINESERVER" ]] || \
    die 'Wine staging 11.15 is unavailable'
command -v bwrap >/dev/null || die 'bubblewrap is unavailable'
command -v systemd-run >/dev/null || die 'systemd-run is unavailable'

if [[ "$mode" == init && -e "$sandbox_root/prefix/system.reg" ]]; then
    die 'init refuses to overwrite an existing disposable prefix'
fi
if [[ "$mode" == update || "$mode" == drivers || \
      "$mode" == presonus-driver || "$mode" == smoke || \
      "$mode" == driver-load || "$mode" == service || \
      "$mode" == live-read ]]; then
    [[ -s "$sandbox_root/prefix/system.reg" ]] || \
        die 'this mode requires an initialized disposable prefix'
fi
if [[ "$mode" == service || "$mode" == live-read ]]; then
    [[ -x "$UC_DIR/PreSonusHardwareAccessService.exe" ]] || \
        die "UC service executable is unavailable under $UC_DIR"
fi
if [[ "$mode" == driver-load || "$mode" == live-read ]]; then
    readonly corrected_ntoskrnl_root="$sandbox_root/out/wine-ntddi"
    readonly corrected_ntoskrnl="$corrected_ntoskrnl_root/x86_64-windows/ntoskrnl.exe"
    readonly corrected_ntoskrnl_so="$corrected_ntoskrnl_root/x86_64-unix/ntoskrnl.exe.so"
    [[ ! -L "$corrected_ntoskrnl" && -s "$corrected_ntoskrnl" ]] || \
        die 'driver-load requires the corrected Wine kernel fake PE'
    [[ ! -L "$corrected_ntoskrnl_so" && -s "$corrected_ntoskrnl_so" ]] || \
        die 'driver-load requires the corrected Wine kernel builtin'
    read -r corrected_ntoskrnl_hash _ < <(sha256sum -- "$corrected_ntoskrnl")
    [[ "$corrected_ntoskrnl_hash" == "$CORRECTED_NTOSKRNL_SHA256" ]] || \
        die "$mode refuses an unknown corrected Wine kernel fake PE"
    read -r corrected_ntoskrnl_so_hash _ < <(sha256sum -- "$corrected_ntoskrnl_so")
    [[ "$corrected_ntoskrnl_so_hash" == "$CORRECTED_NTOSKRNL_SO_SHA256" ]] || \
        die "$mode refuses an unknown corrected Wine kernel builtin"
    readonly patched_ntdll_root="$sandbox_root/out/wine-rtl-registry-handle"
    readonly patched_ntdll="$patched_ntdll_root/x86_64-windows/ntdll.dll"
    [[ ! -L "$patched_ntdll" && -s "$patched_ntdll" ]] || \
        die 'driver-load requires the patched registry-handle ntdll'
    read -r patched_ntdll_hash _ < <(sha256sum -- "$patched_ntdll")
    [[ "$patched_ntdll_hash" == "$PATCHED_NTDLL_SHA256" ]] || \
        die "$mode refuses an unknown registry-handle ntdll"
    for original_ntoskrnl in \
            "$WINE_NTOSKRNL" \
            "$sandbox_root/prefix/drive_c/windows/system32/ntoskrnl.exe"; do
        read -r original_ntoskrnl_hash _ < <(sha256sum -- "$original_ntoskrnl")
        [[ "$original_ntoskrnl_hash" == "$WINE_NTDDI_FALSE_STUB_SHA256" ]] || \
            die "$mode found an unexpected original Wine kernel"
    done
    for original_ntdll in \
            "$WINE_NTDLL" \
            "$sandbox_root/prefix/drive_c/windows/system32/ntdll.dll"; do
        read -r original_ntdll_hash _ < <(sha256sum -- "$original_ntdll")
        [[ "$original_ntdll_hash" == "$WINE_NTDLL_ORIGINAL_SHA256" ]] || \
            die "$mode found an unexpected original Wine ntdll"
    done
    readonly wineusb_range_v2_root="$PROJECT_DIR/re/wineusb-class-interface-range-v2"
    readonly wineusb_range_v2_fake_pe="$wineusb_range_v2_root/x86_64-windows/wineusb.sys"
    readonly wineusb_range_v2_builtin="$wineusb_range_v2_root/x86_64-unix/wineusb.sys.so"
    readonly wineusb_range_v2_unixlib="$wineusb_range_v2_root/x86_64-unix/wineusb.so"
    for artifact in \
            "$wineusb_range_v2_fake_pe" \
            "$wineusb_range_v2_builtin" \
            "$wineusb_range_v2_unixlib"; do
        [[ ! -L "$artifact" && -s "$artifact" ]] || \
            die "$mode requires a regular staged RANGE-v2 wineusb artifact: $artifact"
    done
    read -r wineusb_range_v2_hash _ < <(sha256sum -- "$wineusb_range_v2_fake_pe")
    [[ "$wineusb_range_v2_hash" == "$WINEUSB_RANGE_V2_FAKE_PE_SHA256" ]] || \
        die "$mode refuses an unknown RANGE-v2 wineusb fake PE"
    read -r wineusb_range_v2_hash _ < <(sha256sum -- "$wineusb_range_v2_builtin")
    [[ "$wineusb_range_v2_hash" == "$WINEUSB_RANGE_V2_BUILTIN_SHA256" ]] || \
        die "$mode refuses an unknown RANGE-v2 wineusb builtin"
    read -r wineusb_range_v2_hash _ < <(sha256sum -- "$wineusb_range_v2_unixlib")
    [[ "$wineusb_range_v2_hash" == "$WINEUSB_RANGE_V2_UNIXLIB_SHA256" ]] || \
        die "$mode refuses an unknown RANGE-v2 wineusb Unix library"
    for original_wineusb in \
            "$WINE_WINEUSB" \
            "$sandbox_root/prefix/drive_c/windows/system32/drivers/wineusb.sys"; do
        read -r original_wineusb_hash _ < <(sha256sum -- "$original_wineusb")
        [[ "$original_wineusb_hash" == "$WINE_WINEUSB_ORIGINAL_SHA256" ]] || \
            die "$mode found an unexpected original Wine wineusb driver"
    done
    read -r original_wineusb_so_hash _ < <(sha256sum -- "$WINE_WINEUSB_SO")
    [[ "$original_wineusb_so_hash" == "$WINE_WINEUSB_SO_ORIGINAL_SHA256" ]] || \
        die "$mode found an unexpected original Wine wineusb Unix library"
fi
if [[ "$mode" == driver-load ]]; then

    readonly registry_probe_source="$PROJECT_DIR/tests/io24_registry_probe.c"
    readonly registry_probe_exe="$sandbox_root/out/io24-registry-probe.exe"
    [[ -s "$registry_probe_source" ]] || \
        die 'exact NT registry probe source is missing'
    [[ -x "$WINEGCC" ]] || die 'Wine C compiler is unavailable'
    (
        cd -- "$sandbox_root/out"
        "$WINEGCC" -m64 -Wall -Wextra -Werror \
            -o "$registry_probe_exe" "$registry_probe_source" -lntdll
    )
    [[ -x "$registry_probe_exe" && -x "$registry_probe_exe.so" ]] || \
        die 'failed to compile the exact NT registry probe'
fi
if [[ "$mode" == presonus-driver ]]; then
    readonly helper_source="$PROJECT_DIR/tests/io24_stage_driver.c"
    readonly helper_exe="$sandbox_root/out/io24-stage-driver.exe"
    [[ -s "$helper_source" ]] || die 'PreSonus driver staging helper source is missing'
    [[ -x "$WINEGCC" ]] || die 'Wine C compiler is unavailable'
    for driver_file in paedspusb.inf paedspusb.cat paedspusb.sys; do
        [[ -s "$UC_DIR/Drivers/DSPUSBSeries/x64/$driver_file" ]] || \
            die "official PreSonus driver file is unavailable: $driver_file"
    done
    "$WINEGCC" -m64 -Wall -Wextra -Werror \
        -o "$helper_exe" "$helper_source" -lsetupapi
    [[ -x "$helper_exe" && -x "$helper_exe.so" ]] || \
        die 'failed to compile the PreSonus driver staging helper'
fi

usb_sys_name=''
usb_bus=''
usb_dev=''
usb_serial=''
usb_node=''
if [[ "$mode" == live-audit || "$mode" == live-read ]]; then
    mapfile -t io24_devices < <(
        for vendor_file in /sys/bus/usb/devices/*/idVendor; do
            read -r vendor < "$vendor_file" || continue
            [[ "$vendor" == 194f ]] || continue
            device_dir=${vendor_file%/idVendor}
            read -r product < "$device_dir/idProduct" || continue
            [[ "$product" == 0422 ]] || continue
            printf '%s\n' "$device_dir"
        done
    )
    (( ${#io24_devices[@]} == 1 )) || \
        die "expected exactly one connected io24, found ${#io24_devices[@]}"
    usb_sys_name=${io24_devices[0]##*/}
    read -r raw_bus < "${io24_devices[0]}/busnum"
    read -r raw_dev < "${io24_devices[0]}/devnum"
    read -r usb_serial < "${io24_devices[0]}/serial"
    printf -v usb_bus '%03d' "$raw_bus"
    printf -v usb_dev '%03d' "$raw_dev"
    usb_node="/dev/bus/usb/$usb_bus/$usb_dev"
    [[ -c "$usb_node" && -r "$usb_node" && -w "$usb_node" ]] || \
        die "io24 USB node is not accessible: $usb_node"
    [[ ! -L "/sys/bus/usb/devices/${usb_sys_name}:1.5/driver" ]] || \
        die 'io24 control interface 5 is already claimed by a kernel driver'
    if [[ "$mode" == live-read ]]; then
        staged_driver_match=0
        mapfile -d '' staged_driver_binaries < <(
            find "$sandbox_root/prefix/drive_c/windows/system32" \
                -maxdepth 4 -type f \
                -ipath '*/paedspusb-wine.inf_*/*' \
                -iname paedspusb.sys -print0
        )
        if ps -eo args= | grep -Eq \
                '([i]o24gtk\.py|[i]o24d\.py|[u]cnet_shim\.py|[U]niversal Control\.exe)'; then
            die 'an io24/UC process is already running; nothing was stopped'
        fi
        [[ -s "$sandbox_root/prefix/drive_c/windows/inf/paedspusb-wine.inf" ]] || \
            die 'live-read requires the staged Wine-compatible PreSonus INF'
        for candidate in "${staged_driver_binaries[@]}"; do
            if cmp -s "$UC_DIR/Drivers/DSPUSBSeries/x64/paedspusb.sys" \
                    "$candidate"; then
                staged_driver_match=1
                break
            fi
        done
        (( staged_driver_match == 1 )) || \
            die 'live-read requires the verified official PreSonus driver binary'
        [[ -s "$sandbox_root/out/usbtap.so" ]] || \
            die 'live-read requires SANDBOX_ROOT/out/usbtap.so'
        read -r usbtap_hash _ < <(sha256sum -- "$sandbox_root/out/usbtap.so")
        [[ "$usbtap_hash" == "$USBTAP_RESOLVER_V6_SHA256" ]] || \
            die 'live-read requires the hash-pinned local-resolver v6 usbtap'
        [[ ! -e "$sandbox_root/out/live-service-usb.txt" ]] || \
            die 'refusing to overwrite an existing live USB capture'
    fi
fi

readonly unit="io24-wine-${mode}-$$.service"
declare -a limits=(
    --user
    --wait
    --collect
    --pipe
    --service-type=exec
    "--unit=$unit"
    --property=MemoryAccounting=yes
    --property=TasksAccounting=yes
    --property=MemorySwapMax=0
    --property=CPUQuota=25%
    --property=CPUWeight=10
    --property=TasksMax=64
    --property=Nice=10
    --property=IOSchedulingClass=idle
    --property=IOWeight=1
    --property=RuntimeMaxSec=210
    --property=TimeoutStopSec=3
    --property=KillMode=control-group
    --property=OOMPolicy=kill
    --property=NoNewPrivileges=yes
    --property=RestrictRealtime=yes
    --property=RestrictSUIDSGID=yes
    --property=LimitCORE=0
    --property=UMask=0077
)

case "$mode" in
    audit|live-audit)
        limits+=(--property=MemoryHigh=128M --property=MemoryMax=256M)
        limits+=(--property=RuntimeMaxSec=15 --property=TasksMax=16)
        ;;
    init)
        limits+=(--property=MemoryHigh=896M --property=MemoryMax=1G)
        ;;
    update)
        limits+=(--property=MemoryHigh=1280M --property=MemoryMax=1536M)
        limits+=(--property=RuntimeMaxSec=150)
        ;;
    drivers|presonus-driver)
        limits+=(--property=MemoryHigh=512M --property=MemoryMax=768M)
        limits+=(--property=RuntimeMaxSec=30 --property=TasksMax=48)
        ;;
    driver-load)
        limits+=(--property=MemoryHigh=512M --property=MemoryMax=768M)
        limits+=(--property=RuntimeMaxSec=45 --property=TasksMax=48)
        ;;
    smoke)
        limits+=(--property=MemoryHigh=512M --property=MemoryMax=768M)
        limits+=(--property=RuntimeMaxSec=20 --property=TasksMax=48)
        ;;
    service|live-read)
        limits+=(--property=MemoryHigh=1G --property=MemoryMax=1536M)
        limits+=(--property=RuntimeMaxSec=75 --property=TasksMax=96)
        ;;
esac

declare -a bubblewrap=(
    /usr/bin/bwrap
    --die-with-parent
    --new-session
    --unshare-user
    --unshare-pid
    --unshare-net
    --unshare-ipc
    --unshare-uts
    --unshare-cgroup-try
    --cap-drop ALL
    --clearenv
    --setenv HOME /tmp/home
    --setenv USER ajuntanaga
    --setenv LOGNAME ajuntanaga
    --setenv PATH /opt/wine-staging/bin:/usr/local/bin:/usr/bin:/bin
    --setenv LANG C.UTF-8
    --setenv TMPDIR /tmp
    --setenv WINEPREFIX /tmp/prefix
    --setenv WINEARCH win64
    --setenv WINEDEBUG -all
    --setenv WINEDLLOVERRIDES winemenubuilder.exe=d
    --setenv WINEESYNC 0
    --setenv WINEFSYNC 0
    --setenv DISPLAY :98
    --setenv LIBGL_ALWAYS_SOFTWARE 1
    --setenv LIBGL_DRI3_DISABLE 1
    --setenv XDG_RUNTIME_DIR /tmp/runtime
    --setenv XDG_CACHE_HOME /tmp/out/cache
    --setenv XDG_CONFIG_HOME /tmp/out/config
    --setenv XDG_DATA_HOME /tmp/out/data
    --setenv DBUS_SESSION_BUS_ADDRESS unix:path=/tmp/no-session-bus
    --setenv PULSE_SERVER unix:/tmp/no-pulse
    --setenv IO24_SANDBOX_INNER 1
    --setenv IO24_SANDBOX_MODE "$mode"
    --setenv IO24_DRIVER_REGISTRY_TRACE "$DRIVER_REGISTRY_TRACE"
    --ro-bind / /
    --dev /dev
    --proc /proc
    --bind "$sandbox_root" /tmp
    --tmpfs /run
    --tmpfs /home
    --dir /run/io24-project
    --ro-bind "$PROJECT_DIR" /run/io24-project
)
if [[ "$mode" == live-audit || "$mode" == live-read ]]; then
    bubblewrap+=(
        --setenv IO24_SANDBOX_LIVE_USB 1
        --setenv IO24_USB_SYS_NAME "$usb_sys_name"
        --setenv IO24_USB_BUS "$usb_bus"
        --setenv IO24_USB_DEV "$usb_dev"
        --setenv IO24_USB_SERIAL "$usb_serial"
        --ro-bind /sys /sys
        --dir /dev/bus
        --dir /dev/bus/usb
        --dir "/dev/bus/usb/$usb_bus"
        --dev-bind "$usb_node" "$usb_node"
    )
else
    bubblewrap+=(--tmpfs /sys)
fi
if [[ "$mode" == driver-load || "$mode" == live-read ]]; then
    bubblewrap+=(
        --setenv WINEDLLPATH "$CORRECTED_NTOSKRNL_ROOT/x86_64-unix:/run/io24-wineusb-range-v2/x86_64-unix"
        --setenv WINEDLLOVERRIDES 'ntoskrnl.exe=b;wineusb.sys=b;winemenubuilder.exe=d'
        --dir /run/io24-wineusb-range-v2
        --ro-bind "$wineusb_range_v2_root" /run/io24-wineusb-range-v2
        --ro-bind "$patched_ntdll" "$WINE_NTDLL"
        --ro-bind "$patched_ntdll" "$PREFIX_NTDLL"
        --ro-bind "$corrected_ntoskrnl" "$WINE_NTOSKRNL"
        --ro-bind "$corrected_ntoskrnl" "$PREFIX_NTOSKRNL"
        --ro-bind "$wineusb_range_v2_fake_pe" "$WINE_WINEUSB"
        --ro-bind "$wineusb_range_v2_fake_pe" "$PREFIX_WINEUSB"
        --ro-bind "$wineusb_range_v2_unixlib" "$WINE_WINEUSB_SO"
    )
fi
if [[ "$mode" == live-read ]]; then
    bubblewrap+=(
        --setenv LIBUSB_DEBUG 4
        --setenv IO24_USBLOG /tmp/out/live-service-usb.txt
        --setenv LD_PRELOAD /tmp/out/usbtap.so
    )
fi
if [[ "$mode" == presonus-driver || "$mode" == service || \
      "$mode" == live-read ]]; then
    bubblewrap+=(--dir /run/io24-uc --ro-bind "$UC_DIR" /run/io24-uc)
fi
bubblewrap+=(--chdir /tmp /bin/bash /run/io24-project/tests/uc_wine_sandbox.sh)

printf 'starting %s in %s (unit %s)\n' "$mode" "$sandbox_root" "$unit"
exec /usr/bin/systemd-run "${limits[@]}" "${bubblewrap[@]}"
