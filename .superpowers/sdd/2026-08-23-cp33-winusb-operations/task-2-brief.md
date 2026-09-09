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

