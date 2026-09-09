### Task 1: Materialize CP33 roots and capture genuine RED

**Files:**

- Create: `.io24-build/winusb-api-v1/dev-source/`
- Create: `.io24-build/winusb-api-v1/patch-check-source/`
- Create: `re/winusb-api-v1/logs/cp32-seal-verify.log`
- Create: `re/winusb-api-v1/logs/dspusbdevice-winusb-callsite.log`
- Create: `re/winusb-api-v1/logs/cp33-red.log`
- Create: all five CP33 contract families and their complete fakes listed in the file map

- [ ] **Verify the sealed baseline and create fresh durable roots.**

```bash
test ! -e "$IO24_CP33_ROOT"
mkdir -p "$IO24_CP33_ROOT" "$IO24_EVIDENCE/checkpoints" "$IO24_EVIDENCE/logs"
(cd "$IO24_PROJECT/re/winusb-function-binding-v1/checkpoints" && \
    sha256sum --check CP32_SHA256SUMS) \
    | tee "$IO24_EVIDENCE/logs/cp32-seal-verify.log"
cp -a --reflink=auto "$IO24_CP32_SOURCE" "$IO24_DEV_SOURCE"
cp -a --reflink=auto "$IO24_CP32_SOURCE" "$IO24_PATCH_SOURCE"
diff -qr --no-dereference "$IO24_CP32_SOURCE" "$IO24_DEV_SOURCE"
diff -qr --no-dereference "$IO24_CP32_SOURCE" "$IO24_PATCH_SOURCE"
```

Expected: 72 checksum lines end in `OK`; both `diff` commands produce no output and exit zero.

- [ ] **Freeze the vendor evidence in the analyzer and call-site log.** Use this exact import set in `tests/io24_winusb_vendor_profile_contract.py`:

```python
EXPECTED_IMPORTS = (
    "WinUsb_AbortPipe",
    "WinUsb_ControlTransfer",
    "WinUsb_Free",
    "WinUsb_GetAssociatedInterface",
    "WinUsb_GetDescriptor",
    "WinUsb_GetOverlappedResult",
    "WinUsb_GetPipePolicy",
    "WinUsb_Initialize",
    "WinUsb_QueryDeviceInformation",
    "WinUsb_ReadPipe",
    "WinUsb_ResetPipe",
    "WinUsb_SetCurrentAlternateSetting",
    "WinUsb_SetPipePolicy",
    "WinUsb_WritePipe",
)

EXPECTED_POLICY_SEQUENCE = {
    "all": ((3, 0), (9, 0)),
    "out": ((1, 0),),
    "in": ((2, 0), (4, 0), (5, 0), (6, 0), (7, 1)),
    "get": ((8, 4),),
}
```

```bash
{
    sha256sum "$IO24_VENDOR_DLL"
    objdump -p "$IO24_VENDOR_DLL"
    objdump -d -M intel --start-address=0x180084d50 --stop-address=0x180084dc0 "$IO24_VENDOR_DLL"
    objdump -d -M intel --start-address=0x180095e20 --stop-address=0x180095f80 "$IO24_VENDOR_DLL"
} > "$IO24_EVIDENCE/logs/dspusbdevice-winusb-callsite.log"
```

Expected: DLL hash `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`, exactly fourteen expected imports, policy get at `0x180084d50`, and initializer at `0x180095e20`.

- [ ] **Write complete host fakes before any production edit.** The four C contracts share guard and accounting conventions:

```c
#define GUARD_BYTE 0xa5

struct io24_counts
{
    unsigned int allocations;
    unsigned int frees;
    unsigned int submits;
    unsigned int cancels;
    unsigned int releases;
    unsigned int completions;
    unsigned int failures;
};

#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)
```

The function fixture must encode MI05 alternate 0 with zero endpoints and alternate 1 with bulk endpoints `0x81` and `0x01`, each with maximum packet size 512. The fake libusb must expose counters for claim, release, detach, auto-detach, set-configuration, set-alternate, control, bulk, interrupt, cancel, clear-halt, transfer-free, and close.

- [ ] **Make every wrapper self-check its inputs.** Use these stable signatures:

```text
tests/winusb_user_api_contract.sh WINE_SOURCE_ROOT [MODE]
tests/winusb_function_io_contract.sh WINE_SOURCE_ROOT [MODE]
tests/wineusb_winusb_urb_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT LIBUSB_INCLUDE [MODE]
tests/winusb_overlapped_cancel_contract.sh WINE_SOURCE_ROOT WINE_BUILD_ROOT LIBUSB_INCLUDE [MODE]
tests/io24_winusb_vendor_profile_contract.py --wine-source WINE_SOURCE_ROOT --vendor-dll VENDOR_DLL
```

Each shell wrapper compiles actual production translation units with `cc -std=c11 -Wall -Wextra -Werror`, uses a fresh temporary directory, and exits `2` on usage errors. The lower wrappers compile `unixlib.c` against `wineusb_winusb_urb_fake_libusb.c` and use only `WINE_BUILD_ROOT/dlls/ntdll/ntdll.so` from the sealed CP32 build.

- [ ] **Run all five contracts against untouched CP32 and retain intended failures.**

```bash
set +e
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" > "$IO24_EVIDENCE/logs/cp33-red.log" 2>&1
readonly IO24_RED_USER=$?
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" >> "$IO24_EVIDENCE/logs/cp33-red.log" 2>&1
readonly IO24_RED_FUNCTION=$?
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" >> "$IO24_EVIDENCE/logs/cp33-red.log" 2>&1
readonly IO24_RED_LOWER=$?
tests/winusb_overlapped_cancel_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" >> "$IO24_EVIDENCE/logs/cp33-red.log" 2>&1
readonly IO24_RED_CANCEL=$?
python3 tests/io24_winusb_vendor_profile_contract.py \
    --wine-source "$IO24_DEV_SOURCE" --vendor-dll "$IO24_VENDOR_DLL" \
    >> "$IO24_EVIDENCE/logs/cp33-red.log" 2>&1
readonly IO24_RED_VENDOR=$?
set -e
test "$IO24_RED_USER" -eq 1
test "$IO24_RED_FUNCTION" -eq 1
test "$IO24_RED_LOWER" -eq 1
test "$IO24_RED_CANCEL" -eq 1
test "$IO24_RED_VENDOR" -eq 1
```

Expected failures: absent public prototypes/definitions, create and device-control rejected, select-interface/control/cancel missing, all-pipe abort and unconditional reset/removal completion detected, and vendor callable count `0/14`. A segmentation fault, missing test input, or compiler syntax error requires fixing the harness and rerunning RED.

- [ ] **Checkpoint the untouched roots and RED tests.**

```bash
diff -qr --no-dereference "$IO24_CP32_SOURCE" "$IO24_DEV_SOURCE"
sha256sum tests/winusb_*contract.[ch] tests/winusb_*contract.sh \
    tests/wineusb_winusb_urb_contract.[ch] tests/wineusb_winusb_urb_contract.sh \
    tests/wineusb_winusb_urb_fake_libusb.c \
    tests/io24_winusb_vendor_profile_contract.py \
    "$IO24_EVIDENCE/logs/cp33-red.log" \
    > "$IO24_EVIDENCE/logs/task-01-red.sha256"
```

Expected: source still equals CP32; the hash list is nonempty and verifies with `sha256sum --check` from the project root.

