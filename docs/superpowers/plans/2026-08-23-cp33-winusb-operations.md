# CP33 Exact WinUSB Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and seal the exact fourteen `WinUsb_*` operations imported by the pinned vendor DLL, including function-scoped initialization, descriptor and pipe state, synchronous and overlapped transfers, cancellation, and deterministic offline reproduction.

**Architecture:** `winusb.dll` owns validated opaque public handles and immutable descriptor caches. A pointer-free version-1 IOCTL ABI carries requests to per-file state in `winusb.sys`; transfer IOCTLs translate into standard URBs and forward the original IRP to the function-scoped `wineusb.sys` PDO. The lower driver and Unix backend own interface claims, generation-checked pipes, libusb transfer lifetime, cancellation, and one physical completion.

**Tech Stack:** Wine 11.15 C, Win32/NT user APIs, WDM and USB URBs, Wine Unix-call ABI, libusb, native C/Python/Bash contracts, GNU `patch`/`diff`, bubblewrap, and SHA-256 seals.

**Spec:** `docs/superpowers/specs/2026-08-23-cp33-winusb-operations-design.md`

## Global Constraints

- CP32 is immutable. Start from `.io24-build/winusb-function-binding-v1/patch-check-source`, whose production patch hash is `7df4011ea20fa36bf80f4bc0ba409c9dca812b7d76b00f19f1709774eebf75bb`.
- All implementation and verification is offline. Do not run Wine, create or access a Wine prefix, stage or select a build, load a driver, start Universal Control or Voice FX, open a USB node, inspect a sysfs USB path, claim or detach a physical interface, change a physical alternate/configuration, or issue a physical transfer.
- CP24 authorization is consumed. A connected io24 is state evidence only and is not authorization.
- Check `/sys/class/power_supply/BAT0/capacity` before each contained build or full matrix. Stop when capacity is `10` or lower.
- Use `apply_patch` for every manual source, test, or documentation edit. Never overwrite an existing CP33 tree; stop and audit it if a target path already exists.
- Add a focused contract first, run it, and record the intended RED before changing the corresponding production path. A missing fake, malformed harness, unrelated compile failure, or retained-test failure is not an acceptable feature RED.
- Preserve metadata bus-interface version 1 byte-for-byte. Version 2 is additive.
- Keep the eight unimported legacy exports as explicit stubs. The completion claim is exactly 14/14 imported operations, not full WinUSB.
- Use the original user IRP, original file handle, caller `OVERLAPPED`, and caller MDL for transfer completion. Do not introduce nested asynchronous IRPs, helper threads, shadow events, raw user pointers in the ABI, or `METHOD_NEITHER`.
- Do not use `IoCsq*`; the pinned `ntoskrnl` implementations are stubs. Use explicit cancel-spin-lock and queue ownership.
- No automatic detach, `libusb_detach_kernel_driver`, libusb auto-detach, `libusb_set_configuration`, selector, firmware, or live candidate is permitted.
- This workspace has an empty `.git` directory and is not a Git repository. Replace each requested commit with the task-local patch/hash checkpoint specified below; do not initialize Git.

## Working Paths

Run implementation commands from the project root in one shell:

```bash
readonly IO24_PROJECT='/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont'
readonly IO24_CP32_SOURCE="$IO24_PROJECT/.io24-build/winusb-function-binding-v1/patch-check-source"
readonly IO24_CP33_ROOT="$IO24_PROJECT/.io24-build/winusb-api-v1"
readonly IO24_DEV_SOURCE="$IO24_CP33_ROOT/dev-source"
readonly IO24_PATCH_SOURCE="$IO24_CP33_ROOT/patch-check-source"
readonly IO24_BUILD_A="$IO24_CP33_ROOT/build-a"
readonly IO24_BUILD_B="$IO24_CP33_ROOT/build-b"
readonly IO24_CP32_BUILD="$IO24_PROJECT/.io24-build/winusb-function-binding-v1/build-a"
readonly IO24_TOOLS="$IO24_PROJECT/.io24-build/wineusb-observe-v2/tools"
readonly IO24_LIBUSB_INCLUDE="$IO24_TOOLS/usr/include/libusb-1.0"
readonly IO24_EVIDENCE="$IO24_PROJECT/re/winusb-api-v1"
readonly IO24_VENDOR_DLL='/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll'
```

Every focused contract wrapper accepts absolute paths and uses a fresh `mktemp -d` directory. It must not read a prefix, device, or host USB topology.

## File Map

### Public and private ABI

- Modify `include/winusb.h`: public setup packet and fourteen prototypes.
- Create `include/winusbio.h`: policy IDs, `DEVICE_SPEED`, and documented speed values.
- Create `include/wine/winusb.h`: private IOCTL codes and fixed-width version-1 structures.
- Modify `include/Makefile.in`: install `winusbio.h`; the private header remains internal under `include/wine/`.

### User-mode DLL

- Modify `dlls/winusb/Makefile.in`: add `kernelbase`/`ntdll` imports and `io.c`.
- Modify `dlls/winusb/winusb.spec`: convert exactly fourteen stubs to real `stdcall` exports.
- Modify `dlls/winusb/main.c`: registry-backed handle/root ownership, initialization, release, associated interfaces, cached descriptors, and speed.
- Create `dlls/winusb/io.c`: common synchronous/overlapped IOCTL submission and transfer/policy API wrappers.
- Create `dlls/winusb/winusb_private.h`: root, handle, snapshot, and helper declarations shared by the two DLL sources.

### Generic function driver

- Modify `dlls/winusb.sys/Makefile.in`: compile `session.c` and `transfer.c`.
- Modify `dlls/winusb.sys/main.c`: PnP-compatible device state, create/cleanup/close, device-control dispatch, and removal drain.
- Create `dlls/winusb.sys/winusb_private.h`: per-device, per-file, interface, pipe, policy, and upper-transfer structures.
- Create `dlls/winusb.sys/session.c`: ABI validation, descriptor snapshot/parser, session commit/release, alternate selection, and policy state.
- Create `dlls/winusb.sys/transfer.c`: direct-MDL validation, URB construction, same-IRP forwarding/completion, byte counts, and status mapping.

### Lower WineUSB and Unix backend

- Modify `dlls/wineusb.sys/winusb_busif.h` and `winusb_busif.c`: additive metadata interface v2 and speed getter.
- Modify `dlls/wineusb.sys/wineusb.c`: cancel-safe pending contexts, pipe-specific abort, select-interface forwarding, status propagation, and removal drain.
- Modify `dlls/wineusb.sys/unixlib.h`: explicit opaque transfer return/cancel/release calls and completion-event identity.
- Modify `dlls/wineusb.sys/unixlib.c`: transactional claims, alternate selection, generation-checked pipe records, generic control transfers, retained transfer objects, reset errors, and claim release.

### Contracts and evidence

- Create `tests/winusb_user_api_contract.c` and `.sh`.
- Create `tests/winusb_function_io_contract.c` and `.sh`.
- Create `tests/wineusb_winusb_urb_contract.c`, `.sh`, and `wineusb_winusb_urb_fake_libusb.c`.
- Create `tests/winusb_overlapped_cancel_contract.c` and `.sh`.
- Create `tests/io24_winusb_vendor_profile_contract.py`.
- Create `tests/cp33_contract_matrix.sh` to make the two clean matrices identical and auditable.
- Modify retained contracts only when an intentional CP33 semantic extension invalidates a CP32 prohibition; preserve every unrelated assertion.
- Create `re/winusb-api-v1/MANIFEST.md`, checkpoint/report/seal files, focused logs, two clean matrix logs, patch replay logs, build logs, and comparisons.
- Create `re/wine-11.15-winusb-api-v1.patch`.
- Modify `re/IO24_HANDOFF.md` only after the final seal verifies.

---

## Gate 1 — Handle and Metadata

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

### Task 2: Define the public surface and pointer-free private ABI

**Files:**

- Modify: `$IO24_DEV_SOURCE/include/winusb.h`
- Create: `$IO24_DEV_SOURCE/include/winusbio.h`
- Create: `$IO24_DEV_SOURCE/include/wine/winusb.h`
- Modify: `$IO24_DEV_SOURCE/include/Makefile.in`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/winusb.spec`
- Modify: `tests/winusb_user_api_contract.c`
- Modify: `tests/winusb_function_io_contract.c`

- [ ] **Add compile-time surface and ABI assertions first.** Require `sizeof(WINUSB_SETUP_PACKET) == 8`, `sizeof(struct wine_winusb_request) == 24`, `sizeof(struct wine_winusb_snapshot) == 72`, and identical private structure sizes under normal and `-m32` preprocessing when a 32-bit compiler is available. Assert that every private structure contains only `UINT8`, `UINT16`, `UINT32`, `UINT64`, or arrays of those types.

- [ ] **Run the focused surface contract and confirm RED.**

```bash
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE"
```

Expected: exit 1 identifying the absent setup packet/prototypes, missing private header, and fourteen stub exports.

- [ ] **Add the exact public definitions.** `include/winusbio.h` contains policy IDs `0x01` through `0x09`, `DEVICE_SPEED 0x01`, `LowSpeed 0x01`, `FullSpeed 0x02`, `HighSpeed 0x03`, and `SuperSpeed 0x04`. `include/winusb.h` contains:

```c
#define SHORT_PACKET_TERMINATE 0x01
#define AUTO_CLEAR_STALL 0x02
#define PIPE_TRANSFER_TIMEOUT 0x03
#define IGNORE_SHORT_PACKETS 0x04
#define ALLOW_PARTIAL_READS 0x05
#define AUTO_FLUSH 0x06
#define RAW_IO 0x07
#define MAXIMUM_TRANSFER_SIZE 0x08
#define RESET_PIPE_ON_RESUME 0x09

#define DEVICE_SPEED 0x01
#define LowSpeed 0x01
#define FullSpeed 0x02
#define HighSpeed 0x03
#define SuperSpeed 0x04

typedef struct _WINUSB_SETUP_PACKET
{
    UCHAR RequestType;
    UCHAR Request;
    USHORT Value;
    USHORT Index;
    USHORT Length;
} WINUSB_SETUP_PACKET, *PWINUSB_SETUP_PACKET;

BOOL WINAPI WinUsb_AbortPipe(WINUSB_INTERFACE_HANDLE, UCHAR);
BOOL WINAPI WinUsb_ControlTransfer(WINUSB_INTERFACE_HANDLE, WINUSB_SETUP_PACKET,
        PUCHAR, ULONG, PULONG, LPOVERLAPPED);
BOOL WINAPI WinUsb_Free(WINUSB_INTERFACE_HANDLE);
BOOL WINAPI WinUsb_GetAssociatedInterface(WINUSB_INTERFACE_HANDLE, UCHAR,
        PWINUSB_INTERFACE_HANDLE);
BOOL WINAPI WinUsb_GetDescriptor(WINUSB_INTERFACE_HANDLE, UCHAR, UCHAR, USHORT,
        PUCHAR, ULONG, PULONG);
BOOL WINAPI WinUsb_GetOverlappedResult(WINUSB_INTERFACE_HANDLE, LPOVERLAPPED,
        LPDWORD, BOOL);
BOOL WINAPI WinUsb_GetPipePolicy(WINUSB_INTERFACE_HANDLE, UCHAR, ULONG, PULONG, PVOID);
BOOL WINAPI WinUsb_Initialize(HANDLE, PWINUSB_INTERFACE_HANDLE);
BOOL WINAPI WinUsb_QueryDeviceInformation(WINUSB_INTERFACE_HANDLE, ULONG, PULONG, PVOID);
BOOL WINAPI WinUsb_ReadPipe(WINUSB_INTERFACE_HANDLE, UCHAR, PUCHAR, ULONG, PULONG,
        LPOVERLAPPED);
BOOL WINAPI WinUsb_ResetPipe(WINUSB_INTERFACE_HANDLE, UCHAR);
BOOL WINAPI WinUsb_SetCurrentAlternateSetting(WINUSB_INTERFACE_HANDLE, UCHAR);
BOOL WINAPI WinUsb_SetPipePolicy(WINUSB_INTERFACE_HANDLE, UCHAR, ULONG, ULONG, PVOID);
BOOL WINAPI WinUsb_WritePipe(WINUSB_INTERFACE_HANDLE, UCHAR, PUCHAR, ULONG, PULONG,
        LPOVERLAPPED);
```

- [ ] **Add the version-1 private ABI.** Use function codes `0x800` through `0x80b` exactly once and the methods specified below:

```c
#define WINE_WINUSB_ABI_VERSION 1
#define WINE_WINUSB_MAX_CONTROL_TRANSFER 4096u
#define WINE_WINUSB_MAXIMUM_TRANSFER_SIZE (4u * 1024u * 1024u)

#define IOCTL_WINE_WINUSB_INITIALIZE CTL_CODE(FILE_DEVICE_UNKNOWN, 0x800, METHOD_OUT_DIRECT, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_RELEASE CTL_CODE(FILE_DEVICE_UNKNOWN, 0x801, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_GET_DESCRIPTOR CTL_CODE(FILE_DEVICE_UNKNOWN, 0x802, METHOD_OUT_DIRECT, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_SET_ALTERNATE CTL_CODE(FILE_DEVICE_UNKNOWN, 0x803, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_GET_PIPE_POLICY CTL_CODE(FILE_DEVICE_UNKNOWN, 0x804, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_SET_PIPE_POLICY CTL_CODE(FILE_DEVICE_UNKNOWN, 0x805, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_CONTROL_IN CTL_CODE(FILE_DEVICE_UNKNOWN, 0x806, METHOD_OUT_DIRECT, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_CONTROL_OUT CTL_CODE(FILE_DEVICE_UNKNOWN, 0x807, METHOD_IN_DIRECT, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_READ_PIPE CTL_CODE(FILE_DEVICE_UNKNOWN, 0x808, METHOD_OUT_DIRECT, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_WRITE_PIPE CTL_CODE(FILE_DEVICE_UNKNOWN, 0x809, METHOD_IN_DIRECT, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_ABORT_PIPE CTL_CODE(FILE_DEVICE_UNKNOWN, 0x80a, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_WINE_WINUSB_RESET_PIPE CTL_CODE(FILE_DEVICE_UNKNOWN, 0x80b, METHOD_BUFFERED, FILE_ANY_ACCESS)

struct wine_winusb_request
{
    UINT32 size;
    UINT32 version;
    UINT64 session;
    UINT32 interface_index;
    UINT32 reserved;
};

struct wine_winusb_snapshot
{
    UINT32 size;
    UINT32 version;
    UINT64 session;
    UINT32 speed;
    UINT32 total_size;
    UINT32 device_offset;
    UINT32 device_length;
    UINT32 configuration_offset;
    UINT32 configuration_length;
    UINT32 interfaces_offset;
    UINT32 interface_count;
    UINT32 alternates_offset;
    UINT32 alternate_count;
    UINT32 endpoints_offset;
    UINT32 endpoint_count;
    UINT32 reserved[2];
};
```

Define 16-byte fixed-width interface, alternate, and endpoint snapshot records; 32-byte alternate and pipe requests; 40-byte descriptor, policy, and control requests. Every request embeds `wine_winusb_request`, has explicit transfer length where relevant, and has reserved fields that must be zero.

- [ ] **Convert exactly fourteen spec entries.** Use `int64` for the eight-byte setup packet in `WinUsb_ControlTransfer`; leave `FlushPipe`, current-alternate query, power policy, descriptor parsing, interface query, and pipe query as stubs.

- [ ] **Run surface/ABI GREEN and the retained CP32 binding tests.**

```bash
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --surface-only
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_binding_contract.sh "$IO24_DEV_SOURCE"
python3 tests/winusb_function_binding_inf_contract.py --wine-source "$IO24_DEV_SOURCE"
```

Expected: the surface-only line passes; all three retained CP32 lines pass.

- [ ] **Checkpoint Task 2.** Generate `re/winusb-api-v1/logs/task-02-abi.patch` with a unified diff of only the six touched production files and seal it plus the two focused contracts in `task-02-abi.sha256`.

### Task 3: Add metadata-interface v2 and per-file lifecycle

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/winusb_busif.h`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/winusb_busif.c`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/wineusb.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/main.c`
- Create: `$IO24_DEV_SOURCE/dlls/winusb.sys/winusb_private.h`
- Modify: `tests/wineusb_winusb_busif_contract.c`
- Modify: `tests/winusb_function_io_contract.c`

- [ ] **Extend the tests first.** Cover exact v1 query success and layout, v2 undersize/version rejection without output mutation, v2 speed callback reference balance, create-before-start failure, create-after-start success, distinct `FsContext` objects, cleanup admission closure, idempotent close, and create rejection after surprise removal.

- [ ] **Run focused RED.**

```bash
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --lifecycle
```

Expected: v1 remains green; v2 and lifecycle scenarios fail because v2 and file contexts are absent.

- [ ] **Append metadata v2 without changing v1.**

```c
#define WINEUSB_MS_OS_10_METADATA_VERSION_2 2

typedef NTSTATUS (WINAPI *wineusb_get_device_speed)(void *context, UCHAR *speed);

struct wineusb_ms_os_10_metadata_interface_v2
{
    USHORT Size;
    USHORT Version;
    void *BusContext;
    PINTERFACE_REFERENCE InterfaceReference;
    PINTERFACE_DEREFERENCE InterfaceDereference;
    wineusb_get_device_interface_guid GetDeviceInterfaceGuid;
    wineusb_get_device_speed GetDeviceSpeed;
};
```

`wineusb_metadata_get_speed()` returns `HighSpeed` when `device->high_speed` is true and `LowSpeed` otherwise. It returns `STATUS_DEVICE_NOT_CONNECTED` after removal and never reads a descriptor to infer speed.

- [ ] **Introduce explicit device/file state.** The private driver header defines:

```c
enum winusb_file_state
{
    WINUSB_FILE_UNINITIALIZED,
    WINUSB_FILE_INITIALIZING,
    WINUSB_FILE_INITIALIZED,
    WINUSB_FILE_RELEASING,
    WINUSB_FILE_CLOSING,
    WINUSB_FILE_REMOVED,
};

struct winusb_file
{
    LIST_ENTRY device_entry;
    FILE_OBJECT *file_object;
    KSPIN_LOCK lock;
    enum winusb_file_state state;
    UINT64 session;
    LONG references;
    LONG outstanding;
    KEVENT zero_outstanding;
    LIST_ENTRY transfers;
    void *snapshot;
    ULONG snapshot_size;
    struct winusb_interface_state *interfaces;
    ULONG interface_count;
};
```

Extend `struct winusb_device` with a spin lock, file list/count, removal event, metadata-interface version, and cached speed. `IRP_MJ_CREATE` allocates one file context only in `WINUSB_DEVICE_STARTED`; cleanup marks it closing and starts drain; close unlinks and frees only when the outstanding count is zero. Set `FsContext` only after allocation and list insertion succeed.

- [ ] **Run lifecycle GREEN and retained PnP regression.**

```bash
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --lifecycle
tests/winusb_function_binding_contract.sh "$IO24_DEV_SOURCE"
```

Expected: all pass; the retained CP32 lifecycle line is unchanged.

- [ ] **Checkpoint Task 3.** Hash the five production paths and two contract sources into `re/winusb-api-v1/logs/task-03-lifecycle.sha256`, then verify the file from the project root.

### Task 4: Implement atomic initialization and bounded snapshot parsing

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/Makefile.in`
- Create: `$IO24_DEV_SOURCE/dlls/winusb.sys/session.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/winusb_private.h`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/main.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/Makefile.in`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/main.c`
- Create: `$IO24_DEV_SOURCE/dlls/winusb/winusb_private.h`
- Modify: `tests/winusb_function_io_contract.c`
- Modify: `tests/winusb_user_api_contract.c`

- [ ] **Add descriptor and rollback cases first.** Cover two-stage device/config reads; `bLength < 2`; truncated descriptor; checked-add overflow; mismatched `wTotalLength`; no interface; no default alternate; duplicate alternate; endpoint before interface; output header too short; exact required-size query; allocation failure; select-configuration failure; and DLL-side offset/overlap rejection followed by exactly one release.

- [ ] **Run initialization RED.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --initialize
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --initialize
```

Expected: both exit 1 at the absent initialize IOCTL and stub `WinUsb_Initialize`.

- [ ] **Build snapshots in temporary kernel memory.** Use checked addition everywhere:

```c
static BOOL add_size(SIZE_T left, SIZE_T right, SIZE_T *result)
{
    if (right > ~(SIZE_T)0 - left) return FALSE;
    *result = left + right;
    return TRUE;
}
```

Retrieve the device descriptor, the nine-byte projected configuration header, then exactly validated `wTotalLength`. Parse into temporary interface/alternate/endpoint arrays. Build `URB_FUNCTION_SELECT_CONFIGURATION` for each projected default alternate. Commit snapshot, pipe state, default policies, speed, and a nonzero monotonic session cookie only after the lower request succeeds.

- [ ] **Make short output a noncommitting size query.** Return a validated 72-byte `wine_winusb_snapshot` header with `total_size` and `STATUS_BUFFER_TOO_SMALL`; keep the file uninitialized and claims unchanged. On sufficient output, copy the entire snapshot to the mapped MDL only after all offsets and lengths are final.

- [ ] **Validate overlapped mode in the DLL.** Query `FileModeInformation` with `NtQueryInformationFile`; reject null, invalid, unqueryable, `FILE_SYNCHRONOUS_IO_ALERT`, or `FILE_SYNCHRONOUS_IO_NONALERT` handles with `ERROR_INVALID_HANDLE`. Set `*InterfaceHandle = NULL` before validation. Issue one size query, allocate the exact bounded snapshot, issue initialization again, validate it independently, and publish a handle only after validation.

- [ ] **Run initialization GREEN.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --initialize
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --initialize
```

Expected: MI05 initializes at alternate 0 with zero pipes, speed is `0x03` for the high-speed fixture, all malformed cases leave no session, and every post-commit DLL rejection releases once.

- [ ] **Checkpoint Task 4.** Record a focused unified diff and hashes as `task-04-initialize.patch` and `task-04-initialize.sha256`.

### Task 5: Complete public handle ownership, descriptors, speed, and free

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/winusb/main.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/winusb_private.h`
- Modify: `tests/winusb_user_api_contract.c`

- [ ] **Add ownership tests first.** Cover null/arbitrary/stale handles, associated index mapping, associated lookup on a nondefault handle, out-of-range, duplicate retrieval, allocation failure, all valid free orders, concurrent acquire/free, cached device/config descriptors, descriptor index/language matching, short buffers, default-handle-only speed query, and input/output length mutation rules.

- [ ] **Run ownership RED.**

```bash
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --handles
```

Expected: exit 1 because associated handles, cache queries, and balanced retirement are absent.

- [ ] **Use registry-backed handle validation.** Define a process-global locked list. API entry scans by pointer without dereferencing untrusted memory, increments the handle reference while locked, then acquires the root. `WinUsb_Free` removes one live handle atomically; the memory is freed only after in-flight API references leave. The final root release sends one synchronous `IOCTL_WINE_WINUSB_RELEASE`, frees the snapshot/cache, deletes its critical section, and never closes the caller's device handle.

```c
struct winusb_handle
{
    struct list entry;
    LONG references;
    BOOL live;
    struct winusb_root *root;
    UINT32 interface_index;
};

struct winusb_root
{
    LONG references;
    HANDLE device;
    UINT64 session;
    CRITICAL_SECTION lock;
    BYTE *snapshot;
    UINT32 snapshot_size;
    struct winusb_handle **interface_handles;
    UINT32 interface_count;
};
```

- [ ] **Implement cached operations exactly.** Device and projected configuration descriptors come from validated cache; string and other descriptors use the kernel fallback later in Task 9. `WinUsb_QueryDeviceInformation` accepts `DEVICE_SPEED` only on interface index zero, requires a one-byte output, returns `0x03` for high-or-higher and `0x01` for full-or-lower, and reports one byte copied.

- [ ] **Run handle/cache GREEN and all Gate 1 tests.**

```bash
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --handles
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --surface-only
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --lifecycle
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --initialize
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_binding_contract.sh "$IO24_DEV_SOURCE"
```

Expected: every command exits zero with its named pass line.

- [ ] **Seal Gate 1 checkpoint evidence.** Create `re/winusb-api-v1/logs/gate-1-handle-metadata.sha256` over all Gate 1 production files, tests, RED log, and focused logs; verify it immediately.

---

## Gate 2 — Function and Pipe State

### Task 6: Claim only the function-scoped interfaces transactionally

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/unixlib.h`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/unixlib.c`
- Modify: `tests/wineusb_winusb_urb_contract.c`
- Modify: `tests/wineusb_winusb_urb_fake_libusb.c`

- [ ] **Add claim tests first.** Cover MI05-only claim, a multi-interface function bitset, idempotent repeated selection, second-claim failure rollback, busy ownership error, release on child destruction, sibling-function isolation, parent-handle lifetime, and counters proving zero detach, zero auto-detach, and zero set-configuration calls.

- [ ] **Run claim RED.**

```bash
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --claims
```

Expected: exit 1 with zero claim calls and no rollback/release state.

- [ ] **Add claim state to each function child.** Store a 256-bit claimed set beside the existing function bitset. During `URB_FUNCTION_SELECT_CONFIGURATION`, collect only newly needed interfaces, call `libusb_claim_interface` in ascending interface-number order, and on failure release only the interfaces acquired by that transaction in reverse order. Do not mutate the committed set until all claims succeed.

```c
struct claim_transaction
{
    UINT8 interfaces[256];
    UINT16 count;
};
```

On `usb_destroy_device`, release every committed claim before decrementing the parent/shared physical handle. Map `LIBUSB_ERROR_BUSY` to a failed USBD request and `STATUS_DEVICE_BUSY`; never detach the owner.

- [ ] **Run claim GREEN and retained function-scope regression.**

```bash
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --claims
tests/wineusb_function_scope_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" \
    "$IO24_CP32_BUILD/dlls/wineusb.sys/wineusb.so" "$IO24_LIBUSB_INCLUDE"
```

Expected: claim scenarios pass; retained projected-function behavior still passes.

- [ ] **Checkpoint Task 6.** Hash both production files and both test files as `task-06-claims.sha256`.

### Task 7: Select alternates and issue generation-checked pipe tokens

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/session.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/winusb_private.h`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/wineusb.c`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/unixlib.c`
- Modify: `tests/winusb_function_io_contract.c`
- Modify: `tests/wineusb_winusb_urb_contract.c`

- [ ] **Add alternate and stale-token tests first.** Cover unknown interface/alternate, interface outstanding count nonzero, MI05 alternate 1 success, exact `0x81`/`0x01`/512 metadata, backend failure rollback, out-of-function interface, unclaimed interface, wrong endpoint/type/interface/alternate/generation, successful second generation, and rejection of the previous token.

- [ ] **Run alternate RED.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --alternate
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --alternate
```

Expected: function driver has no alternate IOCTL and lower PDO returns `STATUS_NOT_IMPLEMENTED` for `URB_FUNCTION_SELECT_INTERFACE`.

- [ ] **Make lower pipe tokens portable and generation checked.** Use a bounded per-child token table. The `HANDLE` value encodes a nonzero slot and generation; the slot record contains endpoint, pipe type, actual interface, alternate, and full generation. Validation compares every field against current child state before any backend call.

```c
struct wineusb_pipe_token
{
    UINT32 generation;
    UINT8 endpoint;
    UINT8 type;
    UINT8 interface_number;
    UINT8 alternate;
    BOOL current;
};
```

Successful configuration/alternate selection increments generation, fills new records, then retires the old map. Failed selection does not change generation or current tokens.

- [ ] **Implement transactional `URB_FUNCTION_SELECT_INTERFACE`.** Validate the sized URB, function membership, committed claim, descriptor endpoints, and zero outstanding interface I/O. Call `libusb_set_interface_alt_setting` once, populate returned `USBD_PIPE_INFORMATION`, and commit only on backend success.

- [ ] **Implement public alternate selection.** Resolve the public handle to the exact actual interface, send a synchronous `IOCTL_WINE_WINUSB_SET_ALTERNATE`, and commit upper endpoint/policy state only after lower success.

- [ ] **Run alternate GREEN.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --alternate
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --alternate
```

Expected: alternate 0 has zero pipes; alternate 1 has only bulk IN `0x81` and bulk OUT `0x01`, both 512 bytes; every rollback/stale case passes.

- [ ] **Checkpoint Task 7.** Save and verify `task-07-alternate.sha256` over four production files and both contracts.

### Task 8: Implement the exact vendor pipe-policy profile

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/session.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/winusb_private.h`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/io.c`
- Modify: `tests/winusb_function_io_contract.c`
- Modify: `tests/winusb_user_api_contract.c`

- [ ] **Add a direction/value/default matrix first.** Assert defaults and vendor changes for policies 1 through 9, four-byte maximum `4 * 1024 * 1024`, one-byte boolean lengths, four-byte timeout/maximum lengths, read-only maximum, wrong direction, unknown pipe/policy, enabled unsupported behaviors, and RAW_IO nonzero/multiple/maximum rules.

- [ ] **Run policy RED.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --policy
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --policy
```

Expected: exit 1 because policy dispatch and public wrappers are absent.

- [ ] **Store only authoritative supported state.** Each current pipe starts with timeout `0`, reset-on-resume false, and direction-appropriate documented defaults. Support OUT short-packet-terminate false; IN auto-clear false, ignore-short false, allow-partial true or false, auto-flush false, and RAW_IO false or true. Reject unsupported enabled values with `STATUS_NOT_SUPPORTED`; do not store them.

```c
struct winusb_pipe_policy
{
    ULONG timeout;
    ULONG maximum_transfer_size;
    BOOL short_packet_terminate;
    BOOL auto_clear_stall;
    BOOL ignore_short_packets;
    BOOL allow_partial_reads;
    BOOL auto_flush;
    BOOL raw_io;
    BOOL reset_pipe_on_resume;
};
```

- [ ] **Implement public get/set wrappers.** Validate handle, `PipeID`, value pointer, exact input length, and exact returned length. Pass the authoritative interface index and session; copy a value only on success and preserve guard bytes on failure.

- [ ] **Run policy GREEN and the complete Gate 2 matrix.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --policy
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --policy
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --alternate
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --claims
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --alternate
```

Expected: all pass and the fake records no detach, auto-detach, or set-configuration call.

- [ ] **Seal Gate 2 checkpoint evidence.** Create and verify `gate-2-function-pipe-state.sha256` over all Gate 2 production files, contracts, and focused outputs.

---

## Gate 3 — Synchronous Transfers

### Task 9: Translate generic control and fallback descriptor requests

**Files:**

- Create: `$IO24_DEV_SOURCE/dlls/winusb.sys/transfer.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/Makefile.in`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/main.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/winusb_private.h`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/wineusb.c`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/unixlib.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/main.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/io.c`
- Modify: `tests/winusb_function_io_contract.c`
- Modify: `tests/wineusb_winusb_urb_contract.c`
- Modify: `tests/winusb_user_api_contract.c`

- [ ] **Add control/descriptor test matrices first.** Cover zero through 4096 bytes, 4097 rejection, setup-length mismatch, IN/OUT direct-method selection, null data with nonzero length, standard/class/vendor types, device/interface/endpoint/other recipients, default-handle-only device recipient, interface-index low-byte canonicalization, endpoint membership/direction, reserved request-type bits, five-second timeout, returned-length bounding, cached device/config paths, string fallback, lower failure mapping, and the retained exact class-IN RANGE fixture.

- [ ] **Run control/descriptor RED.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --control-descriptor
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --control-descriptor
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --control-descriptor
```

Expected: all three exit 1 at absent direct-IOCTL translation or absent generic lower control support.

- [ ] **Validate direct buffers before building a URB.** The device-control dispatch checks exact structure size/version/session/interface/reserved fields, `MdlAddress`, mapped length, and integer bounds. The upper transfer context owns the allocated URB and records the final length field to read in its completion routine.

```c
struct winusb_upper_transfer
{
    LIST_ENTRY file_entry;
    struct winusb_file *file;
    IRP *irp;
    URB *urb;
    UINT32 pipe_index;
    UINT32 interface_index;
    BOOL admitted;
};
```

For `URB_FUNCTION_CONTROL_TRANSFER`, set `TransferBuffer = NULL`, reuse the incoming `MdlAddress`, copy the eight setup bytes exactly after recipient validation, and set `USBD_TRANSFER_DIRECTION_IN` only from setup bit 7.

- [ ] **Implement lower generic control routing.** Validate function scope for all four recipients. Build one libusb control setup, copy OUT payload after the eight-byte setup, use timeout `5000`, and copy only bounded `actual_length` for IN. Preserve the retained RANGE response only for its exact predicate; every other class request follows generic control behavior.

- [ ] **Implement descriptor fallback and cache routing.** Cached device/config descriptor calls never issue an IOCTL. All other types issue `IOCTL_WINE_WINUSB_GET_DESCRIPTOR`, become `URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE`, and reuse the direct output MDL. Return no bytes beyond request length, MDL byte count, or lower actual length.

- [ ] **Map final status and byte count in one upper completion routine.** Translate cancellation, timeout, removal, invalid parameter/pipe, no memory, and request failure to the approved NT statuses. Set `IoStatus.Information` to actual bytes only on successful data completion; otherwise set it to zero. Free the URB and upper context exactly once.

```c
static NTSTATUS winusb_status_from_urb(USBD_STATUS status)
{
    if (status == USBD_STATUS_SUCCESS) return STATUS_SUCCESS;
    if (status == USBD_STATUS_CANCELED || status == USBD_STATUS_CANCELING)
        return STATUS_CANCELLED;
    if (status == USBD_STATUS_TIMEOUT || status == USBD_STATUS_DEV_NOT_RESPONDING)
        return STATUS_IO_TIMEOUT;
    if (status == USBD_STATUS_DEVICE_GONE) return STATUS_DEVICE_NOT_CONNECTED;
    if (status == USBD_STATUS_INVALID_PARAMETER) return STATUS_INVALID_PARAMETER;
    if (status == USBD_STATUS_INVALID_PIPE_HANDLE) return STATUS_NOT_FOUND;
    if (status == USBD_STATUS_ERROR_BUSY) return STATUS_DEVICE_BUSY;
    if (status == USBD_STATUS_NO_MEMORY) return STATUS_NO_MEMORY;
    return STATUS_UNSUCCESSFUL;
}
```

- [ ] **Run control/descriptor GREEN and retained class/descriptor regressions.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --control-descriptor
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --control-descriptor
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --control-descriptor
tests/wineusb_class_interface_range_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" \
    "$IO24_CP32_BUILD/dlls/wineusb.sys/x86_64-windows/wineusb.sys" \
    "$IO24_CP32_BUILD/dlls/wineusb.sys/wineusb.so" "$IO24_LIBUSB_INCLUDE"
```

Expected: CP33 control/descriptor lines pass; the captured RANGE contract remains green without widening its predicate.

- [ ] **Checkpoint Task 9.** Save and verify `task-09-control-descriptor.sha256` over the eight production paths and three contract sources.

### Task 10: Implement synchronous read, write, pipe abort, and reset

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/transfer.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/session.c`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/wineusb.c`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/unixlib.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/io.c`
- Modify: `tests/winusb_function_io_contract.c`
- Modify: `tests/wineusb_winusb_urb_contract.c`
- Modify: `tests/winusb_user_api_contract.c`

- [ ] **Add synchronous pipe tests first.** Cover IN-only reads, OUT-only writes, bulk and interrupt routes, unknown endpoint, stale generation, null/non-null transferred-length rules, zero-length read under both partial-read states, forwarded zero-length write, maximum-size rejection, RAW_IO packet-multiple rejection, immediate backend success/failure, short success, stall, timeout, cancel status, abort matching only one pipe, abort not touching control/descriptor/other-file transfers, reset busy, reset success, and clear-halt failure propagation.

- [ ] **Run pipe RED.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --sync-pipes
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --sync-pipes
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --sync-pipes
```

Expected: current lower abort cancels unrelated requests, reset hides failure, and public/upper operations are absent.

- [ ] **Translate read/write to a same-IRP bulk/interrupt URB.** Resolve `PipeID` through the current upper pipe map, take an outstanding reference before state unlock, set `TransferBuffer = NULL`, reuse `MdlAddress`, and pass the current lower token in `PipeHandle`. Do not segment transfers above 4 MiB.

- [ ] **Make abort pipe-specific.** Lower pending contexts store the exact encoded pipe token and URB function. `URB_FUNCTION_ABORT_PIPE` scans only bulk/interrupt contexts on the same PDO whose token equals the requested token, marks cancellation requested, and returns without waiting for callbacks. It never cancels control, descriptor, another pipe, or another PDO.

- [ ] **Make reset truthful.** The function driver rejects reset while the selected pipe's outstanding count is nonzero. Lower validation checks the current token and maps `libusb_clear_halt` failure to a failed USBD status and non-success NT status.

- [ ] **Implement the DLL's synchronous path once.** For public calls without a caller `OVERLAPPED`, create a private manual-reset event and zeroed local `OVERLAPPED`, call `DeviceIoControl`, wait with `GetOverlappedResult(root->device, &local_overlapped, &bytes, TRUE)` only after `ERROR_IO_PENDING`, close the event, write the actual byte count only on success, and restore the meaningful final error after cleanup.

- [ ] **Run synchronous GREEN and immediate-submit regression.**

```bash
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --sync-pipes
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --sync-pipes
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --sync-pipes
tests/wineusb_immediate_submit_cleanup_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" \
    "$IO24_CP32_BUILD/dlls/wineusb.sys/wineusb.so" "$IO24_LIBUSB_INCLUDE"
```

Expected: exact-pipe abort and reset failure tests pass; every immediate failure balances transfer/context allocation and clears `DriverContext`.

- [ ] **Seal Gate 3 checkpoint evidence.** Create and verify `gate-3-synchronous-transfers.sha256` over all Gate 3 production paths, contracts, and focused outputs.

---

## Gate 4 — Overlapped Lifetime

### Task 11: Retain lower transfer identity through one kernel release

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/unixlib.h`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/unixlib.c`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/wineusb.c`
- Modify: `tests/winusb_overlapped_cancel_contract.c`
- Modify: `tests/wineusb_winusb_urb_contract.c`
- Modify: `tests/wineusb_winusb_urb_fake_libusb.c`

- [ ] **Add deterministic lower-race schedules first.** Exercise immediate submit failure; callback before submit returns; natural completion; cancel before backend transfer publication; cancel during publication; cancel after publication; callback racing cancel; cancel after callback event; and duplicate cancel. For each schedule assert one backend submit at most, one cancel at most, one event, one Unix release, one kernel queue removal, one IRP completion, and no post-free access.

- [ ] **Run lifetime RED.**

```bash
tests/winusb_overlapped_cancel_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --lower
```

Expected: exit 1 because callback auto-frees the libusb transfer/context and the kernel keeps a stale raw transfer pointer.

- [ ] **Replace raw IRP queue entries with owned kernel contexts.**

```c
enum wineusb_transfer_state
{
    WINEUSB_TRANSFER_SUBMITTING,
    WINEUSB_TRANSFER_PENDING,
    WINEUSB_TRANSFER_COMPLETION_QUEUED,
    WINEUSB_TRANSFER_COMPLETING,
    WINEUSB_TRANSFER_DONE,
};

struct wineusb_transfer
{
    LIST_ENTRY device_entry;
    IRP *irp;
    struct usb_device *device;
    void *unix_transfer;
    HANDLE pipe_handle;
    USHORT urb_function;
    LONG references;
    enum wineusb_transfer_state state;
    BOOL cancel_requested;
    BOOL cancel_sent;
};
```

Use `DriverContext[0]` only for the kernel context pointer. Protect state, cancel visibility, and the pending list with a kernel spin lock; do not acquire `wineusb_cs` from a cancel routine.

- [ ] **Change the Unix-call contract.** `usb_submit_urb_params` returns an opaque `transfer`; the completion event contains both that opaque identity and the IRP. Add `unix_usb_release_transfer`. Remove `LIBUSB_TRANSFER_FREE_TRANSFER`; the callback records status/length, queues one event, and retains both its `transfer_ctx` and `libusb_transfer` until release. Cancel accepts only the opaque identity and is idempotent after the first libusb cancel request.

- [ ] **Release in strict order.** The event-thread completion path clears cancel visibility, removes queue membership, transitions to completing, calls `unix_usb_release_transfer`, clears `DriverContext[0]`, writes mapped status/length, and completes the IRP. Every immediate submit failure follows the same allocation-unwind order without entering the pending queue.

- [ ] **Run lower lifetime GREEN and immediate-cleanup regression.**

```bash
tests/winusb_overlapped_cancel_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --lower
tests/wineusb_winusb_urb_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --transfer-lifetime
tests/wineusb_immediate_submit_cleanup_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" \
    "$IO24_CP32_BUILD/dlls/wineusb.sys/wineusb.so" "$IO24_LIBUSB_INCLUDE"
```

Expected: all race counters are exactly one where applicable; AddressSanitizer mode reports no leak, double free, or use-after-free.

- [ ] **Checkpoint Task 11.** Save and verify `task-11-lower-lifetime.sha256` over three production and three test paths.

### Task 12: Preserve original-IRP overlapped completion and cancellation identity

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/transfer.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/winusb_private.h`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/io.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/main.c`
- Modify: `tests/winusb_overlapped_cancel_contract.c`
- Modify: `tests/winusb_user_api_contract.c`
- Modify: `tests/winusb_function_io_contract.c`

- [ ] **Add public/upper overlap tests first.** Assert exact caller `OVERLAPPED` pointer passed to `DeviceIoControl`, no private event for caller-overlapped calls, immediate success, `ERROR_IO_PENDING`, failed pending completion, null transferred pointer accepted only for overlapped calls, delegated file handle/wait flag in `WinUsb_GetOverlappedResult`, `CancelIo` and `CancelIoEx` reaching the same IRP, completion-port-compatible byte count, and one upper context release.

- [ ] **Run overlap RED.**

```bash
tests/winusb_overlapped_cancel_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --upper
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --overlapped
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --same-irp
```

Expected: exit 1 if any nested IRP, substituted `OVERLAPPED`, shadow event, or missing cancel routine remains.

- [ ] **Forward the original device-control IRP.** Rewrite the next stack location to `IRP_MJ_INTERNAL_DEVICE_CONTROL` and `IOCTL_INTERNAL_USB_SUBMIT_URB`, place the owned URB in `Argument1`, install the upper completion routine, mark pending when needed, and call the lower device with the incoming IRP. Do not allocate with `IoBuildDeviceIoControlRequest` or `IoAllocateIrp`.

- [ ] **Install lower cancellation before external pending visibility.** Under the cancel spin lock, publish the kernel transfer context and `IoSetCancelRoutine`. If `irp->Cancel` is already set, remove the routine and mark `cancel_requested`; after Unix submission publishes the opaque transfer, issue at most one Unix cancel. The cancel routine releases `irp->CancelIrql`, takes a temporary context reference, marks cancellation, sends cancel only when a backend transfer exists, and never calls `IoCompleteRequest`.

- [ ] **Make caller-overlapped APIs pass through unchanged.** `io.c` sends the caller's pointer directly and returns false with `ERROR_IO_PENDING` on a pending request. `WinUsb_GetOverlappedResult` validates/acquires the interface handle and calls `GetOverlappedResult(root->device, caller_overlapped, transferred, wait)` without modifying the structure.

- [ ] **Run overlap GREEN.**

```bash
tests/winusb_overlapped_cancel_contract.sh "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --upper
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --overlapped
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --same-irp
```

Expected: every path observes the same IRP, file handle, MDL, and caller `OVERLAPPED`; cancellation maps to `STATUS_CANCELLED` and `ERROR_OPERATION_ABORTED` with zero transferred bytes.

- [ ] **Checkpoint Task 12.** Save and verify `task-12-original-irp.sha256` over four production paths and three contracts.

### Task 13: Drain cleanup, surprise removal, and remove without double completion

**Files:**

- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/main.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/session.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb.sys/transfer.c`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/wineusb.c`
- Modify: `$IO24_DEV_SOURCE/dlls/wineusb.sys/unixlib.c`
- Modify: `tests/winusb_overlapped_cancel_contract.c`
- Modify: `tests/winusb_function_io_contract.c`

- [ ] **Add teardown schedules first.** Cover release with no transfer, release with pending transfer, file cleanup with multiple pipes/control, close after cleanup, surprise removal before/during/after callback, lower remove with pending transfer, backend cancellation failure followed by natural callback, repeated cleanup, and two independent file contexts. Assert admission closes immediately and object destruction waits for zero ownership.

- [ ] **Run teardown RED under AddressSanitizer.**

```bash
IO24_CONTRACT_SANITIZE=1 tests/winusb_overlapped_cancel_contract.sh \
    "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE" --teardown
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --teardown
```

Expected: current direct queue completion/removal semantics fail ownership assertions; no unrelated harness sanitizer error is accepted.

- [ ] **Use one drain protocol at every layer.** File cleanup/session release atomically closes admission, requests cancellation of its admitted transfers, and signals `zero_outstanding` only when completion paths decrement the count to zero. Surprise removal marks device and file contexts removed, disables the interface, requests cancellation, and retains objects until both upper and lower counts reach zero.

- [ ] **Remove direct completion from teardown.** Replace `remove_pending_irps()` with cancel requests plus a bounded drain wait. Unix device destruction occurs only after all completion events have been consumed and all opaque transfers released. Release claimed interfaces before decrementing/closing the shared libusb handle.

- [ ] **Prove lock order.** Contract instrumentation enforces: cancel spin lock before transfer state only; never wait while holding a spin lock; device/file state lock before no blocking lower call; Unix `device_mutex` never nests inside a kernel lock. Add a source comment documenting this order beside each state structure.

- [ ] **Run teardown GREEN and all Gate 4 tests.**

```bash
IO24_CONTRACT_SANITIZE=1 tests/winusb_overlapped_cancel_contract.sh \
    "$IO24_DEV_SOURCE" "$IO24_CP32_BUILD" "$IO24_LIBUSB_INCLUDE"
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE" --teardown
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE" --overlapped
```

Expected: every race schedule passes, sanitizer is clean, and one completion/release is observed per accepted request.

- [ ] **Seal Gate 4 checkpoint evidence.** Create and verify `gate-4-overlapped-lifetime.sha256` over all Gate 4 production paths, contracts, and sanitizer logs.

---

## Gate 5 — Exact Profile and Reproducible Closure

### Task 14: Drive the exact 14/14 vendor profile synthetically

**Files:**

- Modify: `tests/io24_winusb_vendor_profile_contract.py`
- Modify: `tests/winusb_user_api_contract.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/winusb.spec`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/main.c`
- Modify: `$IO24_DEV_SOURCE/dlls/winusb/io.c`
- Create: `re/winusb-api-v1/logs/vendor-profile.log`

- [ ] **Freeze four distinct readiness levels in the analyzer.** Report `imported`, `publicly defined`, `synthetically callable`, and `physical compatibility` separately. The offline success condition is exactly `14/14 imported`, `14/14 defined`, `14/14 callable`, and `physical compatibility: not tested`.

- [ ] **Add the exact synthetic sequence before final fixes.** The host boundary records and asserts: initialize; speed query; device/config/string descriptors; maximum-transfer query; OUT policies `(3,0),(9,0),(1,0)`; IN policies `(3,0),(9,0),(2,0),(4,0),(5,0),(6,0),(7,1)`; alternate 1; synchronous and overlapped control/read/write; overlapped result; cancel; one-pipe abort; reset; and all valid associated/default free orders.

- [ ] **Run the full-profile RED.**

```bash
python3 tests/io24_winusb_vendor_profile_contract.py \
    --wine-source "$IO24_DEV_SOURCE" --vendor-dll "$IO24_VENDOR_DLL" \
    --user-contract tests/winusb_user_api_contract.sh
```

Expected: any missing exact behavior is named by operation and scenario; a structural-only pass remains a failure.

- [ ] **Close only observed gaps.** Keep the eight unimported entries as `stub`. Ensure all fourteen expected exports have a public prototype and one non-stub `BOOL WINAPI` definition. Do not broaden enabled policy behavior or report live/device success.

- [ ] **Run vendor-profile GREEN and retain evidence.**

```bash
python3 tests/io24_winusb_vendor_profile_contract.py \
    --wine-source "$IO24_DEV_SOURCE" --vendor-dll "$IO24_VENDOR_DLL" \
    --user-contract tests/winusb_user_api_contract.sh \
    | tee "$IO24_EVIDENCE/logs/vendor-profile.log"
```

Expected terminal line: `io24 exact WinUSB vendor profile: pass (14/14 imported, 14/14 callable, hardware-free)` followed by `physical compatibility: not tested`.

- [ ] **Checkpoint Task 14.** Create and verify `task-14-vendor-profile.sha256` over analyzer, user contract, three DLL production files, call-site log, and vendor-profile log.

### Task 15: Create one exact matrix, run source checks, and replay the patch

**Files:**

- Create: `tests/cp33_contract_matrix.sh`
- Create: `re/wine-11.15-winusb-api-v1.patch`
- Create: `re/winusb-api-v1/logs/source-matrix.log`
- Create: `re/winusb-api-v1/logs/patch-check.log`
- Modify retained contracts only for explicitly documented CP33 extensions

- [ ] **Write the matrix wrapper with a fixed interface.**

```text
tests/cp33_contract_matrix.sh PROJECT_ROOT WINE_SOURCE_ROOT WINE_BUILD_ROOT LIBUSB_INCLUDE VENDOR_DLL
```

It derives the fake WineUSB PE as `WINE_BUILD_ROOT/dlls/wineusb.sys/x86_64-windows/wineusb.sys` and Unix library as `WINE_BUILD_ROOT/dlls/wineusb.sys/wineusb.so`. Run in this order: all eleven OS 1.0 scenarios, PnP IDs, function scope, immediate cleanup, multi-interface handles, pipe observe, captured RANGE, USBDI, class-IN evidence, topology, frozen historical readiness self-contract, metadata bus interface, function binding, INF, all five CP33 families, and the exact vendor profile.

- [ ] **Update only obsolete CP32 prohibitions.** The retained pipe-observe contract must now require claim/control/alternate calls only in its CP33 fixture while continuing to forbid detach, auto-detach, and set-configuration. Preserve CP32 projected descriptor, handle population, RANGE, PnP, and INF assertions unchanged.

- [ ] **Run source-only and host-compilable checks before patch creation.**

```bash
tests/wineusb_ms_os_10_ids_contract.sh "$IO24_DEV_SOURCE"
tests/wineusb_usbdi_contract.sh "$IO24_DEV_SOURCE"
tests/wineusb_winusb_busif_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_binding_contract.sh "$IO24_DEV_SOURCE"
python3 tests/winusb_function_binding_inf_contract.py --wine-source "$IO24_DEV_SOURCE"
tests/winusb_user_api_contract.sh "$IO24_DEV_SOURCE"
tests/winusb_function_io_contract.sh "$IO24_DEV_SOURCE"
```

Expected: all pass and are captured in `source-matrix.log`.

- [ ] **Generate one GNU unified production patch.** The patch must include production Wine paths only, not root-level tests or evidence.

```bash
readonly IO24_DIFF_ROOT=$(mktemp -d -p /tmp io24-cp33-diff.XXXXXX)
trap 'rm -rf -- "$IO24_DIFF_ROOT"' EXIT INT TERM
mkdir "$IO24_DIFF_ROOT/a" "$IO24_DIFF_ROOT/b"
cp -al "$IO24_CP32_SOURCE/." "$IO24_DIFF_ROOT/a/"
cp -al "$IO24_DEV_SOURCE/." "$IO24_DIFF_ROOT/b/"
set +e
(cd "$IO24_DIFF_ROOT" && diff -urN a b) \
    > "$IO24_PROJECT/re/wine-11.15-winusb-api-v1.patch"
readonly IO24_DIFF_STATUS=$?
set -e
test "$IO24_DIFF_STATUS" -eq 1
test -s "$IO24_PROJECT/re/wine-11.15-winusb-api-v1.patch"
```

- [ ] **Prove fuzz-zero forward and reverse applicability.**

```bash
patch -d "$IO24_PATCH_SOURCE" -p1 --fuzz=0 --dry-run \
    < "$IO24_PROJECT/re/wine-11.15-winusb-api-v1.patch"
patch -d "$IO24_PATCH_SOURCE" -p1 --fuzz=0 \
    < "$IO24_PROJECT/re/wine-11.15-winusb-api-v1.patch"
patch -d "$IO24_DEV_SOURCE" -p1 -R --fuzz=0 --dry-run \
    < "$IO24_PROJECT/re/wine-11.15-winusb-api-v1.patch"
diff -qr --no-dereference "$IO24_DEV_SOURCE" "$IO24_PATCH_SOURCE"
test -z "$(find "$IO24_PATCH_SOURCE" -type f \( -name '*.orig' -o -name '*.rej' \) -print -quit)"
test "$(find "$IO24_DEV_SOURCE" -type l | wc -l)" -eq "$(find "$IO24_PATCH_SOURCE" -type l | wc -l)"
```

Expected: both dry runs and apply succeed with no fuzz; trees are identical; no rejected/original leftovers or symlink mismatch exists.

- [ ] **Checkpoint Task 15.** Hash the production patch, matrix wrapper, source matrix, and patch-check log in `task-15-patch-replay.sha256` and verify it.

### Task 16: Produce two contained clean builds and byte comparisons

**Files:**

- Create: `.io24-build/winusb-api-v1/build-a/`
- Create: `.io24-build/winusb-api-v1/build-b/`
- Create: `re/winusb-api-v1/logs/build-a.log`
- Create: `re/winusb-api-v1/logs/build-b.log`
- Create: `re/winusb-api-v1/logs/contracts-build-a.log`
- Create: `re/winusb-api-v1/logs/contracts-build-b.log`
- Create: `re/winusb-api-v1/logs/artifact-comparison.log`
- Create: `re/winusb-api-v1/logs/boundary-audit.log`

- [ ] **Check battery and create two empty roots without replacing prior data.**

```bash
readonly IO24_BATTERY_CAPACITY=$(< /sys/class/power_supply/BAT0/capacity)
test "$IO24_BATTERY_CAPACITY" -gt 10
test ! -e "$IO24_BUILD_A"
test ! -e "$IO24_BUILD_B"
mkdir "$IO24_BUILD_A" "$IO24_BUILD_B"
```

- [ ] **Run the identical contained recipe once per source/build pair.** Define this shell function once, then call it for development/A and patch-check/B:

```bash
io24_contained_build()
{
    local IO24_SELECTED_SOURCE=$1
    local IO24_SELECTED_BUILD=$2

    /usr/bin/bwrap --unshare-all --unshare-net --die-with-parent \
        --ro-bind /usr /usr --ro-bind /etc /etc \
        --symlink usr/bin /bin --symlink usr/sbin /sbin \
        --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
        --proc /proc --dev /dev --dir /sys --tmpfs /tmp \
        --dir /home --dir /home/io24 --dir /run \
        --ro-bind "$IO24_SELECTED_SOURCE" /run/io24-source \
        --ro-bind "$IO24_TOOLS" /run/io24-tools \
        --bind "$IO24_SELECTED_BUILD" /run/io24-build \
        --chdir /run/io24-build \
        /usr/bin/env -i \
            PATH=/run/io24-tools/usr/bin:/usr/bin:/bin \
            BISON=/run/io24-tools/usr/bin/bison \
            BISON_PKGDATADIR=/run/io24-tools/usr/share/bison \
            FLEX=/run/io24-tools/usr/bin/flex \
            M4=/run/io24-tools/usr/bin/m4 \
            LC_ALL=C TZ=UTC \
            SOURCE_DATE_EPOCH=1787101002 \
            /usr/bin/timeout 300 /usr/bin/nice -n 10 /usr/bin/ionice -c 3 \
            /bin/bash -c '
                ulimit -v 2097152
                /run/io24-source/configure --quiet --enable-win64 --without-mingw \
                    --without-x --without-freetype --with-usb \
                    USB_CFLAGS=-I/run/io24-tools/usr/include/libusb-1.0 \
                    USB_LIBS=/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0.5.0
                make -s -j1
                make -s -j1 dlls/winusb/all dlls/winusb.sys/all dlls/wineusb.sys/all
            '
}

io24_contained_build "$IO24_DEV_SOURCE" "$IO24_BUILD_A" \
    > "$IO24_EVIDENCE/logs/build-a.log" 2>&1
io24_contained_build "$IO24_PATCH_SOURCE" "$IO24_BUILD_B" \
    > "$IO24_EVIDENCE/logs/build-b.log" 2>&1
```

Expected: configure and both make invocations exit zero; no warning or error originates from `winusb`, `winusb.sys`, or `wineusb.sys` translation units.

- [ ] **Run the same full matrix in two networkless containers.** Recheck that battery capacity is greater than 10, define this function, and invoke it for A and B:

```bash
test "$(< /sys/class/power_supply/BAT0/capacity)" -gt 10

io24_contained_matrix()
{
    local IO24_SELECTED_SOURCE=$1
    local IO24_SELECTED_BUILD=$2

    /usr/bin/bwrap --unshare-all --unshare-net --die-with-parent \
        --ro-bind /usr /usr --ro-bind /etc /etc \
        --symlink usr/bin /bin --symlink usr/sbin /sbin \
        --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
        --proc /proc --dev /dev --dir /sys --tmpfs /tmp \
        --dir /run --dir /home --dir /home/ajuntanaga \
        --dir /home/ajuntanaga/Documents \
        --dir '/home/ajuntanaga/Documents/Universal Control' \
        --dir '/home/ajuntanaga/Documents/Universal Control/hwaccess' \
        --ro-bind "$IO24_PROJECT" /run/io24-project \
        --ro-bind "$IO24_SELECTED_SOURCE" /run/io24-source \
        --ro-bind "$IO24_SELECTED_BUILD" /run/io24-build \
        --ro-bind "$IO24_TOOLS" /run/io24-tools \
        --ro-bind "$IO24_VENDOR_DLL" \
            '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll' \
        --chdir /run/io24-project \
        /usr/bin/env -i PATH=/run/io24-tools/usr/bin:/usr/bin:/bin LC_ALL=C TZ=UTC \
            /run/io24-project/tests/cp33_contract_matrix.sh \
                /run/io24-project /run/io24-source /run/io24-build \
                /run/io24-tools/usr/include/libusb-1.0 \
                '/home/ajuntanaga/Documents/Universal Control/hwaccess/dspusbdevice.dll'
}

io24_contained_matrix "$IO24_DEV_SOURCE" "$IO24_BUILD_A" \
    > "$IO24_EVIDENCE/logs/contracts-build-a.log" 2>&1
io24_contained_matrix "$IO24_PATCH_SOURCE" "$IO24_BUILD_B" \
    > "$IO24_EVIDENCE/logs/contracts-build-b.log" 2>&1
```

Expected: both logs end in the five CP33 pass lines and the retained CP32 INF pass line.

- [ ] **Compare all selected deliverables byte-for-byte.**

```bash
for IO24_RELATIVE in \
    dlls/winusb/x86_64-windows/winusb.dll \
    dlls/winusb/winusb.dll.so \
    dlls/winusb.sys/x86_64-windows/winusb.sys \
    dlls/winusb.sys/winusb.sys.so \
    dlls/winusb.sys/winusb.res \
    dlls/wineusb.sys/x86_64-windows/wineusb.sys \
    dlls/wineusb.sys/wineusb.sys.so \
    dlls/wineusb.sys/wineusb.so \
    dlls/wineusb.sys/wineusb.res; do
    cmp "$IO24_BUILD_A/$IO24_RELATIVE" "$IO24_BUILD_B/$IO24_RELATIVE"
    sha256sum "$IO24_BUILD_A/$IO24_RELATIVE" "$IO24_BUILD_B/$IO24_RELATIVE"
done | tee "$IO24_EVIDENCE/logs/artifact-comparison.log"
```

Expected: every `cmp` exits zero and each A/B pair has the same hash and size. Compare top-level `Makefile`, `config.status`, `include/config.h`, configure output, build output, and normalized `config.log` as in CP32.

- [ ] **Audit the compiled boundary.** Use `objdump -p`/`nm`/`strings` to prove fourteen real DLL exports, eight remaining stubs, required Unix-call additions, private ABI constants, and no `libusb_detach_kernel_driver`, auto-detach, `libusb_set_configuration`, firmware, or selector symbol/string. Confirm the lower Unix module contains claim/release/control/alternate/cancel/clear-halt calls and that no other production module imports libusb.

- [ ] **Seal Task 16 build evidence.** Create and verify `task-16-clean-builds.sha256` over both build/matrix logs, comparisons, boundary audit, and every selected deliverable from A and B.

### Task 17: Write the checkpoint, verify the final seal, and update handoff

**Files:**

- Create: `re/winusb-api-v1/MANIFEST.md`
- Create: `re/winusb-api-v1/checkpoints/CP33_WINUSB_API.md`
- Create: `re/winusb-api-v1/checkpoints/CP33_SHA256SUMS`
- Create: `re/winusb-api-v1/checkpoints/CP33_FINAL_VERIFICATION_SHA256`
- Modify: `docs/superpowers/specs/2026-08-23-cp33-winusb-operations-design.md`
- Modify: `re/IO24_HANDOFF.md`

- [ ] **Write the report from retained evidence.** Separate observations, commands, hashes, interpretations, and non-claims. State exact 14/14 offline coverage, same-IRP cancellation evidence, MI05 fixture result, reproducibility result, physical compatibility not tested, and every safety exclusion.

- [ ] **Write the manifest.** Enumerate report, spec, plan, handoff, production patch, all CP33 tests, logs, build configurations, selected deliverables, CP32 predecessor seal, and checksum chain. Record the exact artifact-root working directory for seal verification.

- [ ] **Update the spec status only after all gates pass.** Change status to `Implemented and sealed offline at CP33`; leave scope, non-goals, and live boundary intact.

- [ ] **Create the final checksum file last.** From `re/winusb-api-v1/checkpoints`, hash every manifest-listed retained file with relative paths, excluding `CP33_SHA256SUMS` itself. Include the CP32 checksum file hash and the CP33 production patch hash.

- [ ] **Verify the entire seal from its artifact root.**

```bash
(cd "$IO24_EVIDENCE/checkpoints" && sha256sum --check CP33_SHA256SUMS)
```

Expected: every entry ends in `OK`; any missing or changed item blocks completion and handoff update.

- [ ] **Update `re/IO24_HANDOFF.md` only after seal verification.** Record CP33 as sealed, exact report/patch/seal paths and hashes, the no-live-test interpretation, and the next boundary: selector/staging design requires a separate approved specification and fresh live/prefix authorization.

- [ ] **Recreate and reverify the seal after the handoff change.** Because the handoff is sealed, regenerate `CP33_SHA256SUMS` once with its final hash and rerun `sha256sum --check`, piping the output to `re/winusb-api-v1/logs/final-seal-verify.log`. Do not modify any main-seal input afterward. Create `CP33_FINAL_VERIFICATION_SHA256` as an outer, non-recursive checksum containing only the finalized `CP33_SHA256SUMS` and `final-seal-verify.log`, then verify that outer checksum once.

## Final Acceptance Checklist

- [ ] CP32 seal reverified before production changes.
- [ ] Genuine five-family RED retained against untouched CP32.
- [ ] Exactly fourteen imported public functions have prototypes, exports, and behavior definitions; exactly eight legacy names remain stubs.
- [ ] Private ABI layouts are fixed-width, pointer-free, versioned, size checked, reserved-zero checked, and never `METHOD_NEITHER`.
- [ ] Initialization uses an overlapped file handle, bounded validated descriptors, atomic session commit, scoped claims, and alternate 0.
- [ ] Associated handles, free order, cached descriptors, and speed values pass ownership tests.
- [ ] MI05 alternate 1 yields only bulk `0x81` and `0x01`, both maximum packet size 512, with generation validation.
- [ ] Exact vendor policy sequence succeeds; unsupported enabled behavior fails honestly; RAW_IO constraints hold.
- [ ] Control, descriptor, read, and write reuse the original IRP and MDL and report mapped final status/length.
- [ ] Cancel, exact-pipe abort, reset, cleanup, surprise removal, and remove prove one completion and one backend release with no use-after-free.
- [ ] No detach, auto-detach, set-configuration, selector, staging, prefix, Wine, device, UC/Voice, firmware, or live transfer action occurred.
- [ ] Development and fuzz-zero patch-check sources are identical; no `.orig`/`.rej` or symlink mismatch remains.
- [ ] Both full clean matrices pass and all nine selected deliverables reproduce byte-for-byte.
- [ ] `CP33_SHA256SUMS` verifies from `re/winusb-api-v1/checkpoints` after the final handoff update.

## Execution Handoff

When implementation starts, execute one checkbox at a time and stop at the first unexpected RED, regression, build divergence, sanitizer finding, battery threshold, or safety-boundary ambiguity. Do not reinterpret a partial gate as CP33 completion. The final response must identify which checks were local host contracts, which were contained clean-build checks, and that no live device or prefix validation occurred.
