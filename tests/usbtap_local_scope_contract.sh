#!/usr/bin/env bash
set -euo pipefail

io24_project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
io24_build_dir="$(mktemp -d -p /tmp io24-usbtap-local-scope.XXXXXX)"
trap 'rm -rf -- "$io24_build_dir"' EXIT INT TERM

cc -std=c11 -Wall -Wextra -Werror -shared -fPIC \
    -DIO24_FAKE_LIBUSB_LOG \
    "$io24_project_dir/tests/usbtap_log_contract.c" \
    -Wl,-soname,libusb-1.0.so.0 \
    -o "$io24_build_dir/libusb-1.0.so.0"

cc -std=c11 -Wall -Wextra -Werror -shared -fPIC \
    -DIO24_LOCAL_SCOPE_CLIENT \
    "$io24_project_dir/tests/usbtap_local_scope_contract.c" \
    -L"$io24_build_dir" -Wl,--no-as-needed -l:libusb-1.0.so.0 \
    -Wl,-rpath,'$ORIGIN' \
    -o "$io24_build_dir/libio24_local_scope_client.so"

cc -std=c11 -Wall -Wextra -Werror \
    "$io24_project_dir/tests/usbtap_local_scope_contract.c" -ldl \
    -o "$io24_build_dir/usbtap_local_scope_contract"

if [[ -n "${IO24_USBTAP_ARTIFACT:-}" ]]; then
    [[ -f "$IO24_USBTAP_ARTIFACT" && ! -L "$IO24_USBTAP_ARTIFACT" ]] || {
        printf 'FAIL: IO24_USBTAP_ARTIFACT is not a regular file\n' >&2
        exit 1
    }
    cp -- "$IO24_USBTAP_ARTIFACT" "$io24_build_dir/usbtap.so"
    cmp -s -- "$IO24_USBTAP_ARTIFACT" "$io24_build_dir/usbtap.so" || {
        printf 'FAIL: staged artifact copy differs from its source\n' >&2
        exit 1
    }
else
    cc -std=c11 -Wall -Wextra -Werror -shared -fPIC -O2 \
        "$io24_project_dir/tests/usbtap.c" -ldl \
        -o "$io24_build_dir/usbtap.so"
fi

io24_log="$io24_build_dir/durable.log"
io24_stdout="$io24_build_dir/stdout.log"
io24_stderr="$io24_build_dir/stderr.log"
set +e
IO24_USBLOG="$io24_log" LD_PRELOAD="$io24_build_dir/usbtap.so" \
    "$io24_build_dir/usbtap_local_scope_contract" \
    "$io24_build_dir/libio24_local_scope_client.so" \
    >"$io24_stdout" 2>"$io24_stderr"
io24_status=$?
set -e

if (( io24_status != 0 )); then
    sed -n '1,120p' "$io24_stdout" >&2
    sed -n '1,120p' "$io24_stderr" >&2
    sed -n '1,120p' "$io24_log" >&2
    exit "$io24_status"
fi

rg -Fq 'usbtap local-scope resolution contract: pass' "$io24_stdout" || {
    printf 'FAIL: local-scope probe did not complete\n' >&2
    exit 1
}
rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=R-init object=.*libusb-1\.0\.so\.0 symbol=libusb_init$' \
    "$io24_log" || {
    printf 'FAIL: local-scope real initializer routing was not recorded\n' >&2
    sed -n '1,160p' "$io24_log" >&2
    exit 1
}
rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=R-submit object=.*libusb-1\.0\.so\.0 symbol=libusb_submit_transfer$' \
    "$io24_log" || {
    printf 'FAIL: local-scope real submit routing was not recorded\n' >&2
    sed -n '1,160p' "$io24_log" >&2
    exit 1
}
rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=L-global-installed$' \
    "$io24_log" || {
    printf 'FAIL: local-scope global callback was not installed\n' >&2
    sed -n '1,160p' "$io24_log" >&2
    exit 1
}
for io24_message in \
        '[fake] libusb init' \
        '[fake] libusb submit' \
        '[fake] libusb events'; do
    rg -Fq "level=4 $io24_message" "$io24_log" || {
        printf 'FAIL: local-scope native log was not captured: %s\n' \
            "$io24_message" >&2
        sed -n '1,160p' "$io24_log" >&2
        exit 1
    }
done
if ! rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=H-enter$' "$io24_log" ||
   ! rg -q '^# usbtap pid=[0-9]+ tid=[0-9]+ event=H-return status=0$' "$io24_log"; then
    printf 'FAIL: local-scope event lifecycle was not captured\n' >&2
    sed -n '1,160p' "$io24_log" >&2
    exit 1
fi
if rg -Fq 'event=L-global-unavailable' "$io24_log"; then
    printf 'FAIL: local-scope real initializer remained unavailable\n' >&2
    sed -n '1,160p' "$io24_log" >&2
    exit 1
fi

printf 'usbtap local-scope contract: pass\n'
