#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
    echo "usage: $0 SANDBOX_FIXTURE_ROOT" >&2
    exit 2
fi

readonly sandbox_root="$(readlink -f -- "$1")"
readonly sandbox_tail="${sandbox_root##*/}"
readonly script_path="$(readlink -f -- "${BASH_SOURCE[0]}")"
readonly project_dir="$(cd -- "$(dirname -- "$script_path")/.." && pwd -P)"
readonly harness="$project_dir/tests/uc_wine_sandbox.sh"
readonly captured_staged_root=/run/io24-project/re/wineusb-class-interface-range-v2
readonly inner_staged_root=/run/io24-wineusb-range-v2

[[ -d "$sandbox_root" && ! -L "$sandbox_root" ]] || {
    echo "FAIL: sandbox fixture must be a real directory: $sandbox_root" >&2
    exit 1
}
[[ "$sandbox_tail" == io24-wine-sandbox.* ]] || {
    echo "FAIL: sandbox fixture name is outside the harness contract" >&2
    exit 1
}
[[ -x "$harness" ]] || {
    echo "FAIL: sandbox harness is unavailable: $harness" >&2
    exit 1
}

contract_dir=$(mktemp -d -p /tmp io24-range-v2-selector-contract.XXXXXX)
trap 'rm -rf -- "$contract_dir"' EXIT INT TERM

readonly capture="$contract_dir/systemd-run-args.nul"
readonly harness_log="$contract_dir/harness.log"
readonly fake_systemd_run="$contract_dir/systemd-run"

cat >"$fake_systemd_run" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${IO24_SYSTEMD_CAPTURE:?}"
printf '%s\0' "$@" >"$IO24_SYSTEMD_CAPTURE"
EOF
chmod 700 "$fake_systemd_run"

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
    --dir "/tmp/$sandbox_tail"
    --bind "$sandbox_root" "/tmp/$sandbox_tail"
    --dir /run/io24-project
    --ro-bind "$project_dir" /run/io24-project
    --dir /run/io24-contract
    --bind "$contract_dir" /run/io24-contract
    --ro-bind "$fake_systemd_run" /usr/bin/systemd-run
    --chdir /run/io24-project
    /bin/bash
    /run/io24-project/tests/uc_wine_sandbox.sh
    driver-load
    "/tmp/$sandbox_tail"
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

require_pair WINEDLLPATH "/tmp/out/wine-ntddi/x86_64-unix:$inner_staged_root/x86_64-unix"
require_arg "$captured_staged_root"
require_pair "$captured_staged_root" "$inner_staged_root"
require_pair "$captured_staged_root/x86_64-windows/wineusb.sys" /opt/wine-staging/lib/wine/x86_64-windows/wineusb.sys
require_pair "$captured_staged_root/x86_64-windows/wineusb.sys" /tmp/prefix/drive_c/windows/system32/drivers/wineusb.sys
require_pair "$captured_staged_root/x86_64-unix/wineusb.so" /opt/wine-staging/lib/wine/x86_64-unix/wineusb.so

for captured_arg in "${captured_args[@]}"; do
    if [[ "$captured_arg" == *wineusb-class-interface-in-v1* ||
          "$captured_arg" == *io24-wineusb-class-in-v1* ]]; then
        echo "FAIL: driver-load still selects the class-IN-v1 overlay: $captured_arg" >&2
        exit 1
    fi
done

echo "io24 Wine sandbox RANGE-v2 selector contract: pass"
