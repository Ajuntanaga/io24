#!/bin/bash
# Capture what Universal Control sends to the io24 — on Linux, no Windows, no root.
#
# WHY THIS IS RETAINED. UC's hardware-access module imports exactly fourteen
# WinUsb_* functions (PROTOCOL §13v). CP30 corrected the original assumption
# that Wine implements those calls over its wineusb bus driver: all fourteen
# required calls are currently semantic stubs, and MI05/MI06 have no generic
# WinUSB function binding. This script remains a capture harness for after that
# three-layer compatibility boundary is implemented; it is not evidence that
# Universal Control can currently drive the device under Wine.
#
# Wine's wineusb bus library links libusb normally (DT_NEEDED + PLT), so an
# LD_PRELOAD interposer records transfers that actually reach that library
# without usbmon or root. Verification with a normally-linked C caller proved
# the tap, not the missing WinUSB discovery, function-driver, or API layers.
#
# This is the one route to the Voice FX gate that requires no guessing: every
# static attempt failed (§13m, §13t, §13u), but the FX were audible under UC on
# this unit, so a working sequence exists on the wire.
#
#     tests/uc_wine_capture.sh baseline   # this project's driver (no wine needed)
#     tests/uc_wine_capture.sh uc         # CP30-blocked until full WinUSB GREEN
#     tests/uc_wine_capture.sh diff       # what UC sends that we never do
#
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
UC_DIR="${UC_DIR:-$HOME/Documents/Universal Control}"
OUT="${OUT:-$HOME/.cache/io24/capture}"
TAP="$OUT/usbtap.so"
MODE="${1:-uc}"
WINEPREFIX="${WINEPREFIX:-$HOME/.wine-io24}"
WINE_BIN="${WINE_BIN:-$(command -v wine 2>/dev/null || true)}"
[ -n "$WINE_BIN" ] || WINE_BIN=/opt/wine-staging/bin/wine
if [ "$MODE" = uc ]; then
    echo "Refusing Universal Control capture: CP30 proves the required Wine"
    echo "WinUSB discovery, function binding, and API layers are incomplete."
    echo "Remove this guard only with a future hash-pinned behavioral selector."
    exit 1
fi
if [ "$MODE" = uc ] && [ "${IO24_WINE_SANDBOX_ACTIVE:-0}" != 1 ]; then
    echo "Refusing an uncontained Universal Control launch."
    echo "Pass this script only through the audited io24 Wine sandbox."
    exit 1
fi
mkdir -p "$OUT"

build_tap() {
    [ -f "$TAP" ] && [ "$TAP" -nt "$HERE/tests/usbtap.c" ] && return 0
    gcc -shared -fPIC -O2 -o "$TAP" "$HERE/tests/usbtap.c" -ldl || return 1
    echo "built $TAP"
}

case "$MODE" in
  baseline)
    # pyusb loads libusb via ctypes, which LD_PRELOAD cannot reach, so the
    # baseline is taken with the Python-level tap instead. Same output format.
    python3 "$HERE/tests/usbtap_py.py" "$OUT/baseline.txt" || exit 1
    python3 "$HERE/tests/usbmon_decode.py" "$OUT/baseline.txt"
    ;;

  uc)
    [ -x "$WINE_BIN" ] || {
        echo "wine is not installed (looked for PATH wine and $WINE_BIN)"; exit 1; }
    # A running io24 app may hold the vendor interface.  Never stop another
    # process implicitly: a capture must fail closed and let the operator
    # decide when it is safe to release the device.
    if pgrep -f '([i]o24gtk\.py|[i]o24d\.py|[u]cnet_shim\.py)' >/dev/null; then
        echo "An io24 process is already running and may hold the USB interface."
        echo "Stop it yourself when safe, then retry; nothing was terminated."
        exit 1
    fi
    build_tap || exit 1
    [ -d "$UC_DIR" ] || { echo "no UC install at $UC_DIR"; exit 1; }
    [ ! -s "$OUT/uc.txt" ] || {
        echo "$OUT/uc.txt already contains a capture; refusing to overwrite it."
        echo "Move it aside or set OUT to a new directory, then retry."
        exit 1
    }
    echo "Launching Universal Control under Wine."
    echo
    echo "  In UC:  select the io24 -> Voice FX -> pick a model -> switch it ON"
    echo "          and CONFIRM YOU CAN HEAR IT. That is the whole point:"
    echo "          a capture where the FX never worked proves nothing."
    echo "  Then quit UC to end the capture."
    echo
    rm -f "$OUT/uc.txt"               # remove only a stale empty placeholder
    ( cd "$UC_DIR" && WINEPREFIX="$WINEPREFIX" \
        IO24_USBLOG="$OUT/uc.txt" LD_PRELOAD="$TAP" \
        "$WINE_BIN" "Universal Control.exe" ) 2>&1 | tail -25
    echo
    if [ -s "$OUT/uc.txt" ]; then
        echo "captured $(wc -l < "$OUT/uc.txt") transfers -> $OUT/uc.txt"
        python3 "$HERE/tests/usbmon_decode.py" "$OUT/uc.txt" | tail -25
    else
        echo "Nothing captured. Current CP30 evidence says Wine's WinUSB"
        echo "discovery/function/API stack is incomplete; do not treat this"
        echo "as an interface-claim result."
    fi
    ;;

  diff)
    for f in baseline uc; do
        [ -s "$OUT/$f.txt" ] || { echo "missing $OUT/$f.txt — run '$0 $f' first"; exit 1; }
    done
    python3 - "$OUT/baseline.txt" "$OUT/uc.txt" <<'PY'
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())
from importlib.machinery import SourceFileLoader
here = os.path.dirname(os.path.abspath(sys.argv[0]))
dec = SourceFileLoader("dec", os.path.join(os.getcwd(), "tests", "usbmon_decode.py")).load_module()
def vocab(p):
    v=set()
    for u in dec.parse(p):
        for cmd,blk,idx,btag,blen,n in dec.decode_msg(u["data"]):
            v.add((cmd,blk,btag))
    return v
b,u = vocab(sys.argv[1]), vocab(sys.argv[2])
only = sorted(x for x in u-b if x[0])
print("baseline messages: %d kinds | UC: %d kinds" % (len(b),len(u)))
print("\nWHAT UC SENDS THAT WE NEVER DO:")
if only:
    for cmd,blk,btag in only:
        print("   cmd %-5s block %-8s blob %s" % (cmd,blk,btag or "-"))
else:
    print("   nothing — UC's vocabulary is a subset of ours.")
    print("   If the FX worked in that session, the gate is not a message.")
PY
    ;;

  *) echo "usage: $0 [baseline|uc|diff]"; exit 2;;
esac
