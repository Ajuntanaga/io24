#!/usr/bin/env bash
set -euo pipefail

readonly workspace=${1:-$PWD}
readonly task_dir="$workspace/.superpowers/sdd/2026-08-23-cp33-winusb-operations"
readonly archive="$task_dir/task-9-r148-source-bound-evidence.tar.gz"
readonly expected_archive=36f43b038bb0bab62fde7975a7acd0a14de8e6f33946ce077e12e6e4c65b6a06
readonly expected_original_archive=561da904b991e9fcf41c55f1c95230f7a8f90d5e24c228069e9f606b22dea4a1
readonly expected_patch=23333adc2918a72e2f1b32c53713533620f1be782373d1fcd389f4c598f2d08a
readonly expected_base=ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1
readonly expected_upper=eb3323df6df6fc40745e992263ada5ab2a83319e40851af55d58d2c46d359380
readonly expected_lower=7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa
readonly expected_fake=c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb

check_hash()
{
    local expected=$1 path=$2 actual
    actual=$(sha256sum "$path" | awk '{print $1}')
    if [[ $actual != "$expected" ]]; then
        printf 'HASH_MISMATCH expected=%s actual=%s path=%s\n' "$expected" "$actual" "$path" >&2
        return 1
    fi
}

check_hash "$expected_archive" "$archive"
check_hash "$expected_original_archive" "$task_dir/task-9-r148-isolated-evidence.tar.gz"
check_hash "$expected_patch" "$task_dir/task-9-r148-proposed-unified-rejection-state.patch"
check_hash "$expected_upper" "$workspace/tests/winusb_function_io_contract.c"
check_hash "$expected_lower" "$workspace/tests/wineusb_winusb_urb_contract.c"
check_hash "$expected_fake" "$workspace/tests/wineusb_winusb_urb_fake_libusb.c"
check_hash "$expected_base" "$workspace/.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c"

verify_dir=$(mktemp -d -p /tmp io24-r148-source-bound-controller.XXXXXX)
cleanup()
{
    find "$verify_dir" -mindepth 1 -delete 2>/dev/null || true
    rmdir "$verify_dir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

bad_paths=$(tar -tzf "$archive" | awk '
    $0 ~ /^\// || $0 ~ /(^|\/)\.\.($|\/)/ ||
    $0 !~ /^task-9-r148-source-bound-evidence(\/|$)/ { ++bad }
    END { print bad + 0 }
')
[[ $bad_paths -eq 0 ]]
tar -xzf "$archive" -C "$verify_dir"
root="$verify_dir/task-9-r148-source-bound-evidence"
[[ $(find "$root" -type l | wc -l) -eq 0 ]]

(
    cd "$root"
    sha256sum --check package-manifest.sha256 > "$verify_dir/package-manifest.log"
)
manifest_entries=$(wc -l < "$root/package-manifest.sha256" | tr -d ' ')
manifest_ok=$(rg -c ': OK$' "$verify_dir/package-manifest.log")
[[ $manifest_entries -eq 313 && $manifest_ok -eq 313 ]]

row_count=0
for row_dir in "$root"/rows/[0-9][0-9]-*; do
    ((++row_count))
    (
        cd "$row_dir"
        sha256sum --check row-manifest.sha256 >/dev/null
        sha256sum --check mutated.sha256 >/dev/null
        sha256sum --check restored.sha256 >/dev/null
    )
    jq -e '
        .classification == "FEATURE_RED" and
        .harness_exit == 1 and
        .failures == .expected_failures and
        .mutated_sha256 == .pre_run_sha256 and
        .mutated_sha256 == .post_run_sha256 and
        .restored_sha256 == "ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1" and
        .no_harness_diagnostic == true and
        (if .row == 29 then
            .harness_marker_count == 0 and .retained_assertion_witness == true
         else
            .harness_marker_count == 1
         end)
    ' "$row_dir/result.json" >/dev/null
done
[[ $row_count -eq 29 ]]

[[ $(( $(wc -l < "$root/matrix.tsv") - 1 )) -eq 29 ]]
[[ $(tail -n +2 "$root/matrix.tsv" | cut -f4 | sort -u | wc -l) -eq 29 ]]
[[ $(tail -n +2 "$root/matrix.tsv" | awk -F '\t' '$11 == "FEATURE_RED" { ++n } END { print n + 0 }') -eq 29 ]]
[[ $(tail -n +2 "$root/matrix.tsv" | awk -F '\t' '$6 == "ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1" { ++n } END { print n + 0 }') -eq 29 ]]

recon="$verify_dir/reconstruction"
mkdir -p "$recon/dlls/wineusb.sys"
reconstructed=0
for row_dir in "$root"/rows/[0-9][0-9]-*; do
    cp "$root/inputs/base/unixlib.c" "$recon/dlls/wineusb.sys/unixlib.c"
    patch --silent --fuzz=0 -p1 -d "$recon" -i "$row_dir/mutation.diff"
    expected=$(awk '{print $1}' "$row_dir/mutated.sha256")
    check_hash "$expected" "$recon/dlls/wineusb.sys/unixlib.c"
    ((++reconstructed))
done
[[ $reconstructed -eq 29 ]]

for gate in before-focused before-retained after-focused after-retained; do
    [[ $(tr -d '\n' < "$root/baseline/$gate.exit") -eq 0 ]]
    rg -q 'failures=0' "$root/baseline/$gate.log"
    ! rg -q 'HARNESS:' "$root/baseline/$gate.log"
done

[[ $(rg --no-filename '^\+\+\+ b/dlls/wineusb\.sys/unixlib\.c$' "$root"/rows/*/mutation.diff | wc -l) -eq 29 ]]
[[ $(( $( (rg --no-filename '^\+#include' "$root"/rows/*/mutation.diff || true) | wc -l) )) -eq 0 ]]
[[ $(( $( (rg -i --no-filename '^\+.*\b(system|popen|execve?|socket|connect|getaddrinfo|curl|wget)\b|^\+.*https?://' "$root"/rows/*/mutation.diff || true) | wc -l) )) -eq 0 ]]
[[ $(( $( (rg --no-filename '^\+.*(/dev/|/sys/|WINEPREFIX|\.wine-io24)' "$root"/rows/*/mutation.diff || true) | wc -l) )) -eq 0 ]]

cmp -s "$root/inputs/task-9-r148-provenance-replay.py" "$task_dir/task-9-r148-provenance-replay.py"
jq -e '
    .status == "PASS" and
    .all_rows_feature_red == true and
    .live_surface_restored == true and
    .materialized_rows == 29 and
    .rows_with_exit_1 == 29 and
    .rows_with_nonzero_failures == 29
' "$root/run-summary.json" >/dev/null

printf 'R148_SOURCE_BOUND_VERIFY PASS archive=%s manifest=%s/%s rows=%s reconstructed=%s unique_mutants=29 clean_replays=4 live_surface=4/4\n' \
    "$expected_archive" "$manifest_ok" "$manifest_entries" "$row_count" "$reconstructed"
