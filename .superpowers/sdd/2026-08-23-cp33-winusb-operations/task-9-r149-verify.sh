#!/usr/bin/env bash
set -euo pipefail

readonly workspace=${1:-$PWD}
readonly task_dir="$workspace/.superpowers/sdd/2026-08-23-cp33-winusb-operations"
readonly archive="$task_dir/task-9-r149-isolated-evidence.tar.gz"
readonly proposal="$task_dir/task-9-r149-proposed-lifecycle-oracle.patch"
readonly expected_archive=f9d9879bf0806482d555c7c69fe7e75348e173df0344634b758fb48fffe00527
readonly expected_proposal=69ad5fb4e1f406a947313ba662cfefff73a45e6d1487086994c3ae0f1d18fa95
readonly expected_production=ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1
readonly expected_upper=eb3323df6df6fc40745e992263ada5ab2a83319e40851af55d58d2c46d359380
readonly expected_lower=7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa
readonly expected_fake=c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb
readonly expected_wrapper=4076a1bda411fe2295f8f1afe2c6f54ee0a49bbf93632a95d03c316a2a0b0829

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
check_hash "$expected_proposal" "$proposal"
check_hash "$expected_production" "$workspace/.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c"
check_hash "$expected_upper" "$workspace/tests/winusb_function_io_contract.c"
check_hash "$expected_lower" "$workspace/tests/wineusb_winusb_urb_contract.c"
check_hash "$expected_fake" "$workspace/tests/wineusb_winusb_urb_fake_libusb.c"
check_hash "$expected_wrapper" "$workspace/tests/wineusb_winusb_urb_contract.sh"

verify_dir=$(mktemp -d -p /tmp io24-r149-controller.XXXXXX)
cleanup()
{
    find "$verify_dir" -mindepth 1 -delete 2>/dev/null || true
    rmdir "$verify_dir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

bad_paths=$(tar -tzf "$archive" | awk '
    $0 ~ /^\// || $0 ~ /(^|\/)\.\.($|\/)/ ||
    $0 !~ /^task-9-r149-isolated-evidence(\/|$)/ { ++bad }
    END { print bad + 0 }
')
[[ $bad_paths -eq 0 ]]
tar -xzf "$archive" -C "$verify_dir"
root="$verify_dir/task-9-r149-isolated-evidence"
[[ $(find "$root" -type l | wc -l) -eq 0 ]]

(
    cd "$root"
    sha256sum --check package-manifest.sha256 > "$verify_dir/package-manifest.log"
)
manifest_entries=$(wc -l < "$root/package-manifest.sha256" | tr -d ' ')
manifest_ok=$(rg -c ': OK$' "$verify_dir/package-manifest.log")
[[ $manifest_entries -eq 86 && $manifest_ok -eq 86 ]]

jq -e '
    .status == "PASS" and
    .production_changed == false and
    .live_tests_changed == false and
    .tdd_red.clean_controls == 2 and
    .tdd_red.oracle_misses == 3 and
    .final.clean_before == 2 and
    .final.feature_red_executions == 3 and
    .final.clean_after == 2 and
    .final.harness_exit_2 == 0 and
    .final.timeouts == 0 and
    .source_bound_rows == 2 and
    .zero_fuzz_reconstructable_rows == 2 and
    .direct_patch_paths == 3
' "$root/run-summary.json" >/dev/null

jq -e '
    .patch_sha256 == "69ad5fb4e1f406a947313ba662cfefff73a45e6d1487086994c3ae0f1d18fa95" and
    .candidate.lower_contract == "29082348c3d29d75a99e9290c0c54fe8586a3fc8d4bc248e61f1633a1efe59ac" and
    .candidate.fake_libusb == "1096aa0298a3950103d1ce1a5497b2afb07d43b41a8832fa03954282ef8a9539" and
    .candidate.wrapper == "6c2b64c2e1a7b328af951f6d33df36739b51683eeb8bfbac98ccaa6dbadea7cf" and
    .unchanged.production_unixlib == "ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1" and
    (.paths | length) == 3
' "$root/proposal/proposal.json" >/dev/null

cmp -s "$root/proposal/task-9-r149-proposed-lifecycle-oracle.patch" "$proposal"
actual_paths=$(awk '/^diff -urN / {print $3}' "$proposal")
expected_paths=$'a/tests/wineusb_winusb_urb_contract.c\na/tests/wineusb_winusb_urb_contract.sh\na/tests/wineusb_winusb_urb_fake_libusb.c'
[[ $actual_paths == "$expected_paths" ]]

proposal_recon="$verify_dir/proposal-reconstruction"
mkdir -p "$proposal_recon/tests"
cp "$root/inputs/frozen-live/tests/wineusb_winusb_urb_contract.c" "$proposal_recon/tests/"
cp "$root/inputs/frozen-live/tests/wineusb_winusb_urb_contract.sh" "$proposal_recon/tests/"
cp "$root/inputs/frozen-live/tests/wineusb_winusb_urb_fake_libusb.c" "$proposal_recon/tests/"
patch --silent --batch --fuzz=0 -p1 -d "$proposal_recon" -i "$proposal"
cmp -s "$proposal_recon/tests/wineusb_winusb_urb_contract.c" "$root/candidate/tests/wineusb_winusb_urb_contract.c"
cmp -s "$proposal_recon/tests/wineusb_winusb_urb_contract.sh" "$root/candidate/tests/wineusb_winusb_urb_contract.sh"
cmp -s "$proposal_recon/tests/wineusb_winusb_urb_fake_libusb.c" "$root/candidate/tests/wineusb_winusb_urb_fake_libusb.c"

row_count=0
reconstructed=0
for phase in tdd-red final; do
    for row_dir in "$root/$phase"/rows/[0-9][0-9]-*; do
        ((++row_count))
        (
            cd "$row_dir"
            sha256sum --check row-manifest.sha256 >/dev/null
            sha256sum --check mutated-pre.sha256 >/dev/null
            sha256sum --check mutated-post.sha256 >/dev/null
            sha256sum --check restored.sha256 >/dev/null
            sha256sum --check mutation.sha256 >/dev/null
        )
        cmp -s "$row_dir/restored-unixlib.c" "$root/inputs/frozen-production/unixlib.c"
        recon="$verify_dir/reconstruct-$phase-$(basename "$row_dir")"
        mkdir -p "$recon/dlls/wineusb.sys"
        cp "$root/inputs/frozen-production/unixlib.c" "$recon/dlls/wineusb.sys/unixlib.c"
        patch --silent --batch --fuzz=0 -p1 -d "$recon" -i "$row_dir/mutation.diff"
        cmp -s "$recon/dlls/wineusb.sys/unixlib.c" "$row_dir/mutated-unixlib.c"
        ((++reconstructed))
    done
done
[[ $row_count -eq 4 && $reconstructed -eq 4 ]]

for gate in "$root"/tdd-red/clean/*.exit "$root"/tdd-red/rows/*/*.exit; do
    [[ $(tr -d '\n' < "$gate") -eq 0 ]]
done
for log in "$root"/tdd-red/clean/*.log "$root"/tdd-red/rows/*/*.log; do
    rg -q 'failures=0' "$log"
    ! rg -q 'HARNESS:' "$log"
done

for gate in "$root"/final/clean-before/*.exit "$root"/final/clean-after/*.exit; do
    [[ $(tr -d '\n' < "$gate") -eq 0 ]]
done
for log in "$root"/final/clean-before/*.log "$root"/final/clean-after/*.log; do
    rg -q 'failures=0' "$log"
    ! rg -q 'HARNESS:' "$log"
done

row1="$root/final/rows/01-same-address-table-release"
row2="$root/final/rows/02-cached-nested-config-release"
[[ $(tr -d '\n' < "$row1/focused.exit") -eq 1 ]]
[[ $(tr -d '\n' < "$row2/focused.exit") -eq 1 ]]
[[ $(tr -d '\n' < "$row2/retained.exit") -eq 1 ]]
rg -q 'failures=1$' "$row1/focused.log"
rg -q 'failures=10$' "$row2/focused.log"
rg -q 'failures=5$' "$row2/retained.log"
[[ $(rg -c '^WineUSB pipe-observe fake-libusb behavior: pass$' "$row1/focused.log") -eq 1 ]]
row2_focused_markers=$(grep -c '^WineUSB pipe-observe fake-libusb behavior: pass$' "$row2/focused.log" || true)
row2_retained_markers=$(grep -c '^WineUSB pipe-observe fake-libusb behavior: pass$' "$row2/retained.log" || true)
[[ $row2_focused_markers -eq 0 && $row2_retained_markers -eq 0 ]]
rg -q '^CP33 lower executed mode=--control-descriptor completions=1 failures=10$' "$row2/focused.log"
rg -q '^CP33 lower executed mode=--red completions=3 failures=5$' "$row2/retained.log"
! rg -q 'HARNESS:|Terminated|lower contract exited' "$root"/final/rows/*/*.log

awk -F '\t' 'NR > 1 && $12 == "ORACLE_MISS" { ++n } END { exit n == 3 ? 0 : 1 }' "$root/matrix.tsv"
awk -F '\t' 'NR > 1 && $12 == "FEATURE_RED" && $10 == 1 && $11 > 0 { ++n } END { exit n == 3 ? 0 : 1 }' "$root/matrix.tsv"

check_hash "$expected_production" "$workspace/.io24-build/winusb-api-v1/dev-source/dlls/wineusb.sys/unixlib.c"
check_hash "$expected_upper" "$workspace/tests/winusb_function_io_contract.c"
check_hash "$expected_lower" "$workspace/tests/wineusb_winusb_urb_contract.c"
check_hash "$expected_fake" "$workspace/tests/wineusb_winusb_urb_fake_libusb.c"
check_hash "$expected_wrapper" "$workspace/tests/wineusb_winusb_urb_contract.sh"

printf 'R149_VERIFY PASS archive=%s manifest=%s/%s rows=2 executions=3 tdd_red=3 clean=4 proposal_paths=3 live_surface=5/5\n' \
    "$expected_archive" "$manifest_ok" "$manifest_entries"
