#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: $0 BASELINE_SANDBOX_ROOT" >&2
    exit 2
fi

readonly baseline_root="$(readlink -f -- "$1")"
readonly script_path="$(readlink -f -- "${BASH_SOURCE[0]}")"
readonly project_dir="$(cd -- "$(dirname -- "$script_path")/.." && pwd -P)"
readonly harness="$project_dir/tests/uc_wine_sandbox.sh"
readonly captured_staged_root=/run/io24-project/re/wine-ntoskrnl-mdl-nonpaged-v1
readonly inner_staged_root=/run/io24-ntoskrnl-mdl-nonpaged-v1
readonly inner_wineusb_root=/run/io24-wineusb-multi-interface-handles-v1

[[ -d "$baseline_root" && ! -L "$baseline_root" ]] || {
    echo "FAIL: baseline sandbox must be a real directory: $baseline_root" >&2
    exit 1
}
[[ -x "$harness" ]] || {
    echo "FAIL: sandbox harness is unavailable: $harness" >&2
    exit 1
}

contract_dir=$(mktemp -d -p /tmp io24-ntoskrnl-mdl-selector-contract.XXXXXX)
fixture_root=$(mktemp -d -p /tmp io24-wine-sandbox.ntoskrnl-mdl-selector.XXXXXX)
trap 'rm -rf -- "$contract_dir" "$fixture_root"' EXIT INT TERM

readonly fixture_tail="${fixture_root##*/}"
readonly capture="$contract_dir/systemd-run-args.nul"
readonly harness_log="$contract_dir/harness.log"
readonly fake_systemd_run="$contract_dir/systemd-run"
readonly fake_winegcc="$contract_dir/winegcc"

install -d -m 700 \
    "$fixture_root/prefix/drive_c/windows/system32/drivers" \
    "$fixture_root/out/wine-ntddi/x86_64-windows" \
    "$fixture_root/out/wine-ntddi/x86_64-unix" \
    "$fixture_root/out/wine-rtl-registry-handle/x86_64-windows" \
    "$fixture_root/home" "$fixture_root/runtime" "$fixture_root/.X11-unix" \
    "$fixture_root/xvfb-root/usr/bin"
printf 'selector contract fixture\n' >"$fixture_root/prefix/system.reg"
install -m 600 \
    /opt/wine-staging/lib/wine/x86_64-windows/ntoskrnl.exe \
    "$fixture_root/prefix/drive_c/windows/system32/ntoskrnl.exe"
install -m 600 \
    /opt/wine-staging/lib/wine/x86_64-windows/ntdll.dll \
    "$fixture_root/prefix/drive_c/windows/system32/ntdll.dll"
install -m 600 \
    /opt/wine-staging/lib/wine/x86_64-windows/wineusb.sys \
    "$fixture_root/prefix/drive_c/windows/system32/drivers/wineusb.sys"
install -m 600 \
    "$baseline_root/out/wine-ntddi/x86_64-windows/ntoskrnl.exe" \
    "$fixture_root/out/wine-ntddi/x86_64-windows/ntoskrnl.exe"
install -m 600 \
    "$baseline_root/out/wine-ntddi/x86_64-unix/ntoskrnl.exe.so" \
    "$fixture_root/out/wine-ntddi/x86_64-unix/ntoskrnl.exe.so"
install -m 600 \
    "$baseline_root/out/wine-rtl-registry-handle/x86_64-windows/ntdll.dll" \
    "$fixture_root/out/wine-rtl-registry-handle/x86_64-windows/ntdll.dll"
install -m 700 /bin/true "$fixture_root/xvfb-root/usr/bin/Xvfb"

cat >"$fake_systemd_run" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${IO24_SYSTEMD_CAPTURE:?}"
printf '%s\0' "$@" >"$IO24_SYSTEMD_CAPTURE"
EOF
chmod 700 "$fake_systemd_run"

cat >"$fake_winegcc" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
output=''
while (( $# )); do
    if [[ "$1" == -o && $# -ge 2 ]]; then
        output=$2
        shift 2
    else
        shift
    fi
done
[[ "$output" == /tmp/io24-wine-sandbox.*/out/io24-registry-probe.exe ]]
install -m 700 /bin/true "$output"
install -m 700 /bin/true "$output.so"
EOF
chmod 700 "$fake_winegcc"

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
    --setenv IO24_SYSTEMD_CAPTURE /run/io24-contract/systemd-run-args.nul
    --ro-bind / /
    --dev /dev
    --proc /proc
    --tmpfs /sys
    --tmpfs /home
    --tmpfs /tmp
    --tmpfs /run
    --dir /tmp/home
    --dir "/tmp/$fixture_tail"
    --bind "$fixture_root" "/tmp/$fixture_tail"
    --dir /run/io24-project
    --ro-bind "$project_dir" /run/io24-project
    --dir /run/io24-contract
    --bind "$contract_dir" /run/io24-contract
    --ro-bind "$fake_systemd_run" /usr/bin/systemd-run
    --ro-bind "$fake_winegcc" /opt/wine-staging/bin/winegcc
    --chdir /run/io24-project
    /bin/bash
    /run/io24-project/tests/uc_wine_sandbox.sh
    driver-load
    "/tmp/$fixture_tail"
)

if ! "${bubblewrap[@]}" >"$harness_log" 2>&1; then
    cat "$harness_log" >&2
    echo "FAIL: driver-load selector preflight did not reach systemd-run" >&2
    exit 1
fi

[[ -s "$capture" ]] || {
    cat "$harness_log" >&2
    echo "FAIL: no systemd-run argument capture was produced" >&2
    exit 1
}

mapfile -d '' -t captured_args <"$capture"

require_arg() {
    local expected=$1
    local actual

    for actual in "${captured_args[@]}"; do
        [[ "$actual" == "$expected" ]] && return 0
    done
    echo "FAIL: missing systemd-run argument: $expected" >&2
    return 1
}

require_pair() {
    local first=$1
    local second=$2
    local i

    for ((i = 0; i + 1 < ${#captured_args[@]}; i++)); do
        if [[ "${captured_args[i]}" == "$first" &&
              "${captured_args[i + 1]}" == "$second" ]]; then
            return 0
        fi
    done
    echo "FAIL: missing adjacent arguments: $first -> $second" >&2
    return 1
}

require_pair WINEDLLPATH "$inner_staged_root/x86_64-unix:$inner_wineusb_root/x86_64-unix"
require_arg "$captured_staged_root"
require_pair "$captured_staged_root" "$inner_staged_root"
require_pair "$captured_staged_root/x86_64-windows/ntoskrnl.exe" \
    /opt/wine-staging/lib/wine/x86_64-windows/ntoskrnl.exe
require_pair "$captured_staged_root/x86_64-windows/ntoskrnl.exe" \
    /tmp/prefix/drive_c/windows/system32/ntoskrnl.exe

for captured_arg in "${captured_args[@]}"; do
    if [[ "$captured_arg" == /tmp/out/wine-ntddi/x86_64-unix* ||
          "$captured_arg" == /tmp/out/wine-ntddi/x86_64-windows* ]]; then
        echo "FAIL: driver-load still selects the pre-MDL kernel: $captured_arg" >&2
        exit 1
    fi
done

echo "io24 Wine sandbox ntoskrnl nonpaged-MDL v1 selector contract: pass"
