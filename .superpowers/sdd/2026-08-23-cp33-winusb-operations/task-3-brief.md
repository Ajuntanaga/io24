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

