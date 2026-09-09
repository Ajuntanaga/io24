/* Offline CP32 contract for WineUSB's private WinUSB metadata bus interface. */

#include <stdio.h>
#include <string.h>

#include "winusb_busif.h"
#include "wine/debug.h"

#undef WINE_DEFAULT_DEBUG_CHANNEL
#undef TRACE
#undef WARN
#undef ERR
#undef FIXME
#define WINE_DEFAULT_DEBUG_CHANNEL(name)
#define TRACE(...) ((void)0)
#define WARN(...) ((void)0)
#define ERR(...) ((void)0)
#define FIXME(...) ((void)0)
#undef DEVICE_TYPE
#include "wineusb.c"

static unsigned int failures, references, dereferences;
static void *expected_callback_context = (void *)0x12345678;
static unsigned int lower_submit_calls;
static IRP *lower_last_irp;
static void *lower_last_buffer;
static NTSTATUS lower_submit_status = STATUS_PENDING;
static IO_STACK_LOCATION *lower_last_stack;
static FILE_OBJECT *lower_last_file;
static URB lower_last_urb;

unixlib_handle_t __wine_unixlib_handle;
static NTSTATUS WINAPI lower_dispatch(unixlib_handle_t handle, unsigned int code, void *args)
{
    (void)handle;
    if (code == unix_usb_submit_urb)
    {
        struct usb_submit_urb_params *params = args;
        ++lower_submit_calls;
        lower_last_irp = params->irp;
        lower_last_buffer = params->transfer_buffer;
        lower_last_stack = IoGetCurrentIrpStackLocation(params->irp);
        lower_last_file = params->irp->Tail.Overlay.OriginalFileObject;
        lower_last_urb = *(URB *)lower_last_stack->Parameters.Others.Argument1;
        return lower_submit_status;
    }
    return STATUS_SUCCESS;
}
NTSTATUS (WINAPI *__wine_unix_call_dispatcher)(unixlib_handle_t, unsigned int, void *) = lower_dispatch;

#define CHECK(condition, ...) do { if (!(condition)) { \
    fprintf(stderr, "FAIL %s:%u: ", __func__, __LINE__); \
    fprintf(stderr, __VA_ARGS__); fputc('\n', stderr); ++failures; } } while (0)

static void WINAPI reference(void *context)
{
    CHECK(context == expected_callback_context, "unexpected context %p", context);
    ++references;
}

static void WINAPI dereference(void *context)
{
    CHECK(context == expected_callback_context, "unexpected context %p", context);
    ++dereferences;
}

static const GUID metadata_guid =
    {0xa6523832, 0x2ca5, 0x42ff, {0xaa, 0x70, 0xc7, 0x60, 0xf0, 0x6a, 0x8e, 0x73}};
static const GUID unrelated_guid =
    {0xdeadbeef, 0xcafe, 0x4000, {0x80, 0, 1, 2, 3, 4, 5, 6}};

static const WCHAR valid_guid[] =
    {'{','1','2','3','4','5','6','7','8','-','9','A','b','C','-','d','E','f','0','-',
     '1','2','3','4','-','a','B','c','D','e','F','0','1','2','3','4','5','}',0};
static const GUID expected_guid =
    {0x12345678, 0x9abc, 0xdef0, {0x12, 0x34, 0xab, 0xcd, 0xef, 0x01, 0x23, 0x45}};

/* Native host boundary for winusb_busif.c's documented RtlGUIDFromString use. */
static int hex_value(WCHAR character)
{
    if (character >= '0' && character <= '9') return character - '0';
    if (character >= 'a' && character <= 'f') return character - 'a' + 10;
    if (character >= 'A' && character <= 'F') return character - 'A' + 10;
    return -1;
}

static int parse_hex(const WCHAR *text, unsigned int offset, unsigned int count, ULONG *value)
{
    ULONG result = 0;
    unsigned int i;

    for (i = 0; i < count; ++i)
    {
        int digit = hex_value(text[offset + i]);
        if (digit < 0) return 0;
        result = (result << 4) | digit;
    }
    *value = result;
    return 1;
}

VOID WINAPI RtlInitUnicodeString(PUNICODE_STRING string, PCWSTR source)
{
    unsigned int length = 0;

    if (!source)
    {
        string->Buffer = NULL;
        string->Length = string->MaximumLength = 0;
        return;
    }
    while (source[length]) ++length;
    string->Buffer = (WCHAR *)source;
    string->Length = length * sizeof(WCHAR);
    string->MaximumLength = string->Length + sizeof(WCHAR);
}

NTSTATUS WINAPI RtlGUIDFromString(UNICODE_STRING *string, GUID *guid)
{
    ULONG data1, data2, data3, byte;
    unsigned int i;

    if (!string || !guid || !string->Buffer || string->Length != 38 * sizeof(WCHAR))
        return STATUS_INVALID_PARAMETER;
    if (string->Buffer[0] != '{' || string->Buffer[9] != '-' || string->Buffer[14] != '-' ||
            string->Buffer[19] != '-' || string->Buffer[24] != '-' || string->Buffer[37] != '}')
        return STATUS_INVALID_PARAMETER;
    if (!parse_hex(string->Buffer, 1, 8, &data1) || !parse_hex(string->Buffer, 10, 4, &data2) ||
            !parse_hex(string->Buffer, 15, 4, &data3))
        return STATUS_INVALID_PARAMETER;

    guid->Data1 = data1;
    guid->Data2 = data2;
    guid->Data3 = data3;
    for (i = 0; i < 2; ++i)
    {
        if (!parse_hex(string->Buffer, 20 + i * 2, 2, &byte)) return STATUS_INVALID_PARAMETER;
        guid->Data4[i] = byte;
    }
    for (i = 0; i < 6; ++i)
    {
        if (!parse_hex(string->Buffer, 25 + i * 2, 2, &byte)) return STATUS_INVALID_PARAMETER;
        guid->Data4[2 + i] = byte;
    }
    return STATUS_SUCCESS;
}

static NTSTATUS WINAPI getter(void *context, GUID *guid)
{
    return wineusb_ms_os_10_get_device_interface_guid(context, guid);
}

typedef NTSTATUS (WINAPI *expected_get_device_speed)(void *context, UCHAR *speed);

struct expected_metadata_interface_v2
{
    USHORT Size;
    USHORT Version;
    void *BusContext;
    PINTERFACE_REFERENCE InterfaceReference;
    PINTERFACE_DEREFERENCE InterfaceDereference;
    wineusb_get_device_interface_guid GetDeviceInterfaceGuid;
    expected_get_device_speed GetDeviceSpeed;
};

struct expected_metadata_routines_v2
{
    PINTERFACE_REFERENCE InterfaceReference;
    PINTERFACE_DEREFERENCE InterfaceDereference;
    wineusb_get_device_interface_guid GetDeviceInterfaceGuid;
    expected_get_device_speed GetDeviceSpeed;
};

static const struct wineusb_ms_os_10_metadata_routines routines =
{
    .InterfaceReference = reference,
    .InterfaceDereference = dereference,
    .GetDeviceInterfaceGuid = getter,
};

static const struct expected_metadata_routines_v2 routines_v2 =
{
    reference, dereference, getter, wineusb_metadata_get_speed,
};

struct guarded_interface
{
    struct wineusb_ms_os_10_metadata_interface_v1 interface;
    unsigned char guard[16];
};

static void reset(struct guarded_interface *guarded)
{
    memset(guarded, 0xa5, sizeof(*guarded));
    references = dereferences = 0;
}

static void test_query_rejections(void)
{
    struct wineusb_ms_os_10_metadata_routines incomplete = routines;
    struct guarded_interface guarded, before;
    NTSTATUS status;

    reset(&guarded); before = guarded;
    status = wineusb_query_ms_os_10_metadata_interface(NULL, sizeof(guarded.interface), 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &routines);
    CHECK(status == STATUS_NOT_SUPPORTED, "NULL GUID returned %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "NULL GUID changed output");
    CHECK(references == 0, "NULL GUID acquired a reference");

    reset(&guarded);
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, sizeof(guarded.interface), 1,
            NULL, (void *)0x12345678, &routines);
    CHECK(status == STATUS_NOT_SUPPORTED, "NULL interface returned %#lx", (long)status);
    CHECK(references == 0, "NULL interface acquired a reference");

    reset(&guarded); before = guarded;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, sizeof(guarded.interface), 1,
            (INTERFACE *)&guarded.interface, NULL, &routines);
    CHECK(status == STATUS_NOT_SUPPORTED, "NULL context returned %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "NULL context changed output");

    reset(&guarded); before = guarded;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, sizeof(guarded.interface), 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, NULL);
    CHECK(status == STATUS_NOT_SUPPORTED, "NULL routines returned %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "NULL routines changed output");

    incomplete.GetDeviceInterfaceGuid = NULL;
    reset(&guarded); before = guarded;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, sizeof(guarded.interface), 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &incomplete);
    CHECK(status == STATUS_NOT_SUPPORTED, "incomplete routines returned %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "incomplete routines changed output");
    CHECK(references == 0, "incomplete routines acquired a reference");

    reset(&guarded); before = guarded;
    status = wineusb_query_ms_os_10_metadata_interface(&unrelated_guid, sizeof(guarded.interface), 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &routines);
    CHECK(status == STATUS_NOT_SUPPORTED, "unknown GUID returned %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "unknown GUID changed output");

    reset(&guarded); before = guarded;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, sizeof(guarded.interface), 3,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &routines);
    CHECK(status == STATUS_NOT_SUPPORTED, "unsupported version returned %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "wrong version changed output");

    reset(&guarded); before = guarded;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, sizeof(guarded.interface) - 1, 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &routines);
    CHECK(status == STATUS_NOT_SUPPORTED, "short buffer returned %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "short buffer changed output");
}

static void check_v2_rejection(USHORT size, USHORT version, const char *name)
{
    struct
    {
        struct expected_metadata_interface_v2 interface;
        unsigned char guard[16];
    } guarded, before;
    NTSTATUS status;

    memset(&guarded, 0xa5, sizeof(guarded));
    before = guarded;
    references = dereferences = 0;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, size, version,
            (INTERFACE *)&guarded.interface, (void *)0x12345678,
            (const struct wineusb_ms_os_10_metadata_routines *)&routines_v2);
    CHECK(status == STATUS_NOT_SUPPORTED, "%s returned %#lx", name, (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "%s changed output", name);
    CHECK(!references && !dereferences,
            "%s changed callback balance %u/%u", name, references, dereferences);
}

static void test_v2_query_and_speed_balance(void)
{
    struct
    {
        struct expected_metadata_interface_v2 interface;
        unsigned char guard[16];
    } guarded;
    struct usb_device device;
    unsigned char expected_guard[sizeof(guarded.guard)];
    UCHAR speed = 0xa5;
    NTSTATUS status;

    check_v2_rejection(sizeof(guarded.interface) - 1, 2, "undersized v2");
    check_v2_rejection(sizeof(guarded.interface) + 1, 2, "oversized v2");
    check_v2_rejection(sizeof(struct wineusb_ms_os_10_metadata_interface_v1), 2,
            "v1-size v2");
    check_v2_rejection(sizeof(guarded.interface), 3, "unsupported v2-sized version");

    memset(&device, 0, sizeof(device));
    expected_callback_context = &device.winusb_metadata;
    memset(&guarded, 0xa5, sizeof(guarded));
    memset(expected_guard, 0xa5, sizeof(expected_guard));
    references = dereferences = 0;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid,
            sizeof(guarded.interface), 2, (INTERFACE *)&guarded.interface,
            &device.winusb_metadata,
            (const struct wineusb_ms_os_10_metadata_routines *)&routines_v2);
    CHECK(status == STATUS_SUCCESS, "v2 query returned %#lx", (long)status);
    CHECK(guarded.interface.Size == sizeof(guarded.interface), "v2 wrong size %#x",
            guarded.interface.Size);
    CHECK(guarded.interface.Version == 2, "v2 wrong version %u", guarded.interface.Version);
    CHECK(guarded.interface.BusContext == &device.winusb_metadata, "v2 wrong context");
    CHECK(guarded.interface.InterfaceReference == reference, "v2 wrong reference routine");
    CHECK(guarded.interface.InterfaceDereference == dereference, "v2 wrong dereference routine");
    CHECK(guarded.interface.GetDeviceInterfaceGuid == getter, "v2 wrong GUID getter");
    CHECK(guarded.interface.GetDeviceSpeed == wineusb_metadata_get_speed,
            "v2 did not return actual lower speed getter");
    CHECK(!memcmp(guarded.guard, expected_guard, sizeof(guarded.guard)),
            "v2 success overwrote guard bytes");
    CHECK(references == 1 && !dereferences,
            "v2 query callback balance %u/%u", references, dereferences);
    if (status == STATUS_SUCCESS && guarded.interface.GetDeviceSpeed == wineusb_metadata_get_speed &&
            guarded.interface.InterfaceDereference == dereference)
    {
        device.high_speed = FALSE;
        status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
        CHECK(status == STATUS_SUCCESS && speed == LowSpeed, "v2 low speed returned %#lx/%#x",
                (long)status, speed);
        device.high_speed = TRUE;
        speed = 0xa5;
        status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
        CHECK(status == STATUS_SUCCESS && speed == HighSpeed, "v2 high speed returned %#lx/%#x",
                (long)status, speed);
        device.removed = TRUE;
        speed = 0xa5;
        status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
        CHECK(status == STATUS_DEVICE_NOT_CONNECTED && speed == 0xa5,
                "v2 removed speed returned %#lx/%#x", (long)status, speed);
        device.removed = FALSE;
        device.winusb_metadata.removed = TRUE;
        speed = 0x5a;
        status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
        CHECK(status == STATUS_DEVICE_NOT_CONNECTED && speed == 0x5a,
                "v2 removed metadata returned %#lx/%#x", (long)status, speed);
        CHECK(references == 1 && !dereferences,
                "v2 speed changed reference balance %u/%u", references, dereferences);
        guarded.interface.InterfaceDereference(guarded.interface.BusContext);
        CHECK(references == 1 && dereferences == 1,
                "v2 consumer did not balance reference %u/%u", references, dereferences);
    }
    expected_callback_context = (void *)0x12345678;
}

void WINAPI EnterCriticalSection(CRITICAL_SECTION *critical_section) { (void)critical_section; }
void WINAPI LeaveCriticalSection(CRITICAL_SECTION *critical_section) { (void)critical_section; }
PVOID WINAPI MmMapLockedPagesSpecifyCache(PMDL mdl, KPROCESSOR_MODE mode,
        MEMORY_CACHING_TYPE cache, PVOID base, ULONG bugcheck, MM_PAGE_PRIORITY priority)
{ (void)mdl; (void)mode; (void)cache; (void)base; (void)bugcheck; (void)priority; return NULL; }

/* This calls the actual static wineusb.c dispatcher in this translation unit.
 * A queued child must stop SELECT_INTERFACE before it reaches Unix. */
static void test_select_interface_pending_child(void)
{
    struct usb_device device;
    IRP request, child;
    IO_STACK_LOCATION stack;
    URB urb;
    NTSTATUS status;

    memset(&device, 0, sizeof(device)); memset(&request, 0, sizeof(request));
    memset(&child, 0, sizeof(child)); memset(&stack, 0, sizeof(stack)); memset(&urb, 0, sizeof(urb));
    InitializeListHead(&device.irp_list);
    request.Tail.Overlay.CurrentStackLocation = &stack;
    stack.Parameters.Others.Argument1 = &urb;
    urb.UrbHeader.Function = URB_FUNCTION_SELECT_INTERFACE;
    urb.UrbHeader.Length = sizeof(urb.UrbSelectInterface);
    InsertTailList(&device.irp_list, &child.Tail.Overlay.ListEntry);
    lower_submit_calls = 0;
    status = usb_submit_urb(&device, &request);
    CHECK(status == STATUS_DEVICE_BUSY, "pending SELECT_INTERFACE returned %#lx", (long)status);
    CHECK(urb.UrbHeader.Status == USBD_STATUS_REQUEST_FAILED, "pending request status %#x", urb.UrbHeader.Status);
    CHECK(!lower_submit_calls, "pending SELECT_INTERFACE reached Unix %u times", lower_submit_calls);
    RemoveEntryList(&child.Tail.Overlay.ListEntry);
}

/* The production dispatcher must carry a generic control URB into the Unix
 * boundary.  At the Task-9 RED head this reaches the actual dispatcher and
 * is rejected because that routing case is not implemented yet. */
static void reset_lower_observation(void)
{
    lower_submit_calls = 0;
    lower_last_irp = NULL;
    lower_last_buffer = NULL;
    lower_last_stack = NULL;
    lower_last_file = NULL;
    memset(&lower_last_urb, 0, sizeof(lower_last_urb));
    lower_submit_status = STATUS_PENDING;
}

static void setup_control_request(struct usb_device *device, IRP *request,
        IO_STACK_LOCATION *stack, URB *urb, FILE_OBJECT *file)
{
    memset(device, 0, sizeof(*device));
    memset(request, 0, sizeof(*request));
    memset(stack, 0, sizeof(*stack));
    memset(urb, 0, sizeof(*urb));
    InitializeListHead(&device->irp_list);
    request->Tail.Overlay.CurrentStackLocation = stack;
    request->Tail.Overlay.OriginalFileObject = file;
    stack->Parameters.Others.Argument1 = urb;
    urb->UrbControlTransfer.Hdr.Function = URB_FUNCTION_CONTROL_TRANSFER;
    urb->UrbControlTransfer.Hdr.Length = sizeof(urb->UrbControlTransfer);
}

static void set_mapped_control_buffer(IRP *request, URB *urb, MDL *mdl,
        void *buffer, ULONG length)
{
    memset(mdl, 0, sizeof(*mdl));
    mdl->MdlFlags = MDL_MAPPED_TO_SYSTEM_VA;
    mdl->MappedSystemVa = buffer;
    mdl->ByteCount = length;
    request->MdlAddress = mdl;
    urb->UrbControlTransfer.TransferBuffer = NULL;
    urb->UrbControlTransfer.TransferBufferMDL = mdl;
    urb->UrbControlTransfer.TransferBufferLength = length;
}

static void check_control_routed(const char *name, struct usb_device *device,
        IRP *request, IO_STACK_LOCATION *stack, URB *urb, void *expected_buffer,
        const unsigned char setup[8])
{
    NTSTATUS status = usb_submit_urb(device, request);

    CHECK(status == STATUS_PENDING, "%s returned %#lx", name, (long)status);
    CHECK(lower_submit_calls == 1, "%s Unix dispatches %u", name, lower_submit_calls);
    CHECK(lower_last_irp == request && lower_last_stack == stack,
            "%s did not retain original IRP/stack", name);
    CHECK(lower_last_file == request->Tail.Overlay.OriginalFileObject,
            "%s changed original file association", name);
    CHECK(lower_last_buffer == expected_buffer, "%s mapped buffer %p, expected %p",
            name, lower_last_buffer, expected_buffer);
    CHECK(lower_last_urb.UrbHeader.Function == URB_FUNCTION_CONTROL_TRANSFER &&
            lower_last_urb.UrbHeader.Length == sizeof(lower_last_urb.UrbControlTransfer),
            "%s altered generic control URB header %#x/%#x", name,
            lower_last_urb.UrbHeader.Function, lower_last_urb.UrbHeader.Length);
    CHECK(lower_last_urb.UrbControlTransfer.TransferBufferLength ==
            urb->UrbControlTransfer.TransferBufferLength,
            "%s altered transfer length %u", name,
            lower_last_urb.UrbControlTransfer.TransferBufferLength);
    CHECK(((unsigned int)setup[6] | ((unsigned int)setup[7] << 8)) ==
            urb->UrbControlTransfer.TransferBufferLength,
            "%s setup wLength and transfer length disagree", name);
    if (urb->UrbControlTransfer.TransferBufferLength)
    {
        CHECK(!urb->UrbControlTransfer.TransferBuffer &&
                urb->UrbControlTransfer.TransferBufferMDL == request->MdlAddress,
                "%s did not use the incoming direct-I/O MDL", name);
        CHECK(!lower_last_urb.UrbControlTransfer.TransferBuffer &&
                lower_last_urb.UrbControlTransfer.TransferBufferMDL == request->MdlAddress,
                "%s changed direct-I/O buffer ownership", name);
    }
    CHECK(!memcmp(lower_last_urb.UrbControlTransfer.SetupPacket, setup, 8),
            "%s altered setup packet", name);
    CHECK(!IsListEmpty(&device->irp_list) && request->IoStatus.Status == STATUS_PENDING,
            "%s did not retain pending IRP invariants", name);
    if (status == STATUS_PENDING && !IsListEmpty(&device->irp_list))
        RemoveEntryList(&request->Tail.Overlay.ListEntry);
}

static void check_control_rejected(const char *name, struct usb_device *device,
        IRP *request, URB *urb)
{
    NTSTATUS status = usb_submit_urb(device, request);

    CHECK(status == STATUS_INVALID_PARAMETER, "%s returned %#lx", name, (long)status);
    CHECK(urb->UrbHeader.Status == USBD_STATUS_INVALID_PARAMETER,
            "%s URB status %#x", name, urb->UrbHeader.Status);
    CHECK(!lower_submit_calls && IsListEmpty(&device->irp_list),
            "%s dispatched or queued (%u)", name, lower_submit_calls);
}

/* This intentionally calls the actual included wineusb.c dispatcher.  The
 * frozen Task-9 RED head routes retained descriptors but not generic controls;
 * all generic assertions below therefore fail as feature evidence, never as a
 * synthetic source scan. */
static void test_control_descriptor_translation(void)
{
    struct usb_device device;
    IRP request;
    IO_STACK_LOCATION stack;
    URB urb;
    FILE_OBJECT file;
    MDL mdl;
    unsigned char direct[64], mapped[64], mapped_4096[4096], mapped_4097[4097];
    const unsigned char in_setups[][8] =
    {
        {0x80, 0x06, 0, 1, 0, 0, 8, 0},  /* standard/device IN */
        {0xa1, 0x01, 0, 0, 1, 0, 8, 0},  /* class/interface IN */
        {0xc2, 0x33, 0, 0, 0x81, 0, 8, 0},/* vendor/endpoint IN */
        {0x83, 0x00, 0, 0, 0, 0, 8, 0},  /* standard/other IN */
    };
    const unsigned char out_setup[8] = {0x41, 0x09, 1, 0, 2, 0, 8, 0};
    const unsigned char zero_setup[8] = {0x80, 0x00, 0, 0, 0, 0, 0, 0};
    const unsigned char max_setup[8] = {0x80, 0x06, 0, 1, 0, 0, 0, 0x10};
    const unsigned char oversize_setup[8] = {0x80, 0x06, 0, 1, 0, 0, 1, 0x10};
    unsigned char mismatch_short[8], mismatch_long[8];
    NTSTATUS status;
    unsigned int i;

    memset(&file, 0, sizeof(file));
    memset(direct, 0xa5, sizeof(direct));
    memset(mapped, 0x5a, sizeof(mapped));
    memset(mapped_4096, 0x69, sizeof(mapped_4096));
    memset(mapped_4097, 0x96, sizeof(mapped_4097));

    /* Retained descriptor routing: direct output buffer, selector, length,
     * original IRP/stack/file identity, and asynchronous pending state. */
    setup_control_request(&device, &request, &stack, &urb, &file);
    urb.UrbControlDescriptorRequest.Hdr.Function = URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE;
    urb.UrbControlDescriptorRequest.Hdr.Length = sizeof(urb.UrbControlDescriptorRequest);
    urb.UrbControlDescriptorRequest.TransferBufferLength = 18;
    urb.UrbControlDescriptorRequest.TransferBuffer = direct;
    urb.UrbControlDescriptorRequest.DescriptorType = 1;
    urb.UrbControlDescriptorRequest.Index = 2;
    urb.UrbControlDescriptorRequest.LanguageId = 0x0409;
    reset_lower_observation();
    status = usb_submit_urb(&device, &request);
    CHECK(status == STATUS_PENDING && lower_submit_calls == 1, "descriptor returned %#lx/%u",
            (long)status, lower_submit_calls);
    CHECK(lower_last_irp == &request && lower_last_stack == &stack && lower_last_file == &file,
            "descriptor lost original request identity");
    CHECK(lower_last_buffer == direct && lower_last_urb.UrbHeader.Function ==
            URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE && lower_last_urb.UrbHeader.Length ==
            sizeof(lower_last_urb.UrbControlDescriptorRequest), "descriptor changed route/header");
    CHECK(lower_last_urb.UrbControlDescriptorRequest.TransferBufferLength == 18 &&
            lower_last_urb.UrbControlDescriptorRequest.DescriptorType == 1 &&
            lower_last_urb.UrbControlDescriptorRequest.Index == 2 &&
            lower_last_urb.UrbControlDescriptorRequest.LanguageId == 0x0409,
            "descriptor changed selector/output shape");
    RemoveEntryList(&request.Tail.Overlay.ListEntry);

    /* Generic control accepts standard/class/vendor and all relevant recipient
     * encodings without rewriting setup bytes or direction flags. */
    for (i = 0; i < ARRAY_SIZE(in_setups); ++i)
    {
        setup_control_request(&device, &request, &stack, &urb, &file);
        urb.UrbControlTransfer.TransferFlags = USBD_TRANSFER_DIRECTION_IN;
        set_mapped_control_buffer(&request, &urb, &mdl, mapped, 8);
        memcpy(urb.UrbControlTransfer.SetupPacket, in_setups[i], 8);
        reset_lower_observation();
        check_control_routed("generic IN", &device, &request, &stack, &urb, mapped, in_setups[i]);
    }
    setup_control_request(&device, &request, &stack, &urb, &file);
    urb.UrbControlTransfer.TransferFlags = USBD_TRANSFER_DIRECTION_OUT;
    set_mapped_control_buffer(&request, &urb, &mdl, mapped, 8);
    memcpy(urb.UrbControlTransfer.SetupPacket, out_setup, 8);
    reset_lower_observation();
    check_control_routed("generic OUT", &device, &request, &stack, &urb, mapped, out_setup);

    /* Zero-length controls are legal without either direct buffer or MDL. */
    setup_control_request(&device, &request, &stack, &urb, &file);
    memcpy(urb.UrbControlTransfer.SetupPacket, zero_setup, 8);
    reset_lower_observation();
    check_control_routed("generic zero", &device, &request, &stack, &urb, NULL, zero_setup);

    /* Direct I/O is represented by the incoming MDL; its mapped system VA is
     * the sole buffer passed to Unix, even when TransferBuffer is NULL. */
    setup_control_request(&device, &request, &stack, &urb, &file);
    urb.UrbControlTransfer.TransferFlags = USBD_TRANSFER_DIRECTION_IN;
    set_mapped_control_buffer(&request, &urb, &mdl, mapped_4096, sizeof(mapped_4096));
    memcpy(urb.UrbControlTransfer.SetupPacket, max_setup, 8);
    reset_lower_observation();
    check_control_routed("generic 4096 mapped IN", &device, &request, &stack, &urb,
            mapped_4096, max_setup);

    /* Immediate lower failure is propagated without queuing; pending is the
     * only completion state that enters the in-flight list. */
    setup_control_request(&device, &request, &stack, &urb, &file);
    set_mapped_control_buffer(&request, &urb, &mdl, mapped, 8);
    memcpy(urb.UrbControlTransfer.SetupPacket, out_setup, 8);
    reset_lower_observation(); lower_submit_status = STATUS_UNSUCCESSFUL;
    status = usb_submit_urb(&device, &request);
    CHECK(status == STATUS_UNSUCCESSFUL && lower_submit_calls == 1 && IsListEmpty(&device.irp_list),
            "immediate lower failure returned %#lx/%u", (long)status, lower_submit_calls);

    /* Reject malformed shapes before Unix dispatch or state/list mutation. */
    setup_control_request(&device, &request, &stack, &urb, &file);
    urb.UrbControlTransfer.Hdr.Length--;
    reset_lower_observation(); check_control_rejected("short control header", &device, &request, &urb);
    /* A raw user buffer is never a nonzero generic-control input path. */
    setup_control_request(&device, &request, &stack, &urb, &file);
    urb.UrbControlTransfer.TransferBufferLength = 8;
    urb.UrbControlTransfer.TransferBuffer = direct;
    memcpy(urb.UrbControlTransfer.SetupPacket, in_setups[0], 8);
    reset_lower_observation(); check_control_rejected("raw buffer without MDL", &device, &request, &urb);
    setup_control_request(&device, &request, &stack, &urb, &file);
    urb.UrbControlTransfer.TransferBufferLength = 8;
    memcpy(urb.UrbControlTransfer.SetupPacket, in_setups[0], 8);
    reset_lower_observation(); check_control_rejected("missing nonzero buffer", &device, &request, &urb);
    setup_control_request(&device, &request, &stack, &urb, &file);
    memset(&mdl, 0, sizeof(mdl)); mdl.ByteCount = 8;
    request.MdlAddress = &mdl;
    urb.UrbControlTransfer.TransferBufferLength = 8; urb.UrbControlTransfer.TransferBufferMDL = &mdl;
    memcpy(urb.UrbControlTransfer.SetupPacket, in_setups[0], 8);
    reset_lower_observation(); check_control_rejected("unmappable MDL", &device, &request, &urb);
    setup_control_request(&device, &request, &stack, &urb, &file);
    set_mapped_control_buffer(&request, &urb, &mdl, mapped, 4);
    urb.UrbControlTransfer.TransferBufferLength = 8;
    memcpy(urb.UrbControlTransfer.SetupPacket, in_setups[0], 8);
    reset_lower_observation(); check_control_rejected("undersized MDL", &device, &request, &urb);
    setup_control_request(&device, &request, &stack, &urb, &file);
    set_mapped_control_buffer(&request, &urb, &mdl, mapped, 8);
    urb.UrbControlTransfer.TransferBuffer = direct;
    memcpy(urb.UrbControlTransfer.SetupPacket, in_setups[0], 8);
    reset_lower_observation(); check_control_rejected("inconsistent direct/MDL buffers", &device, &request, &urb);
    setup_control_request(&device, &request, &stack, &urb, &file);
    set_mapped_control_buffer(&request, &urb, &mdl, mapped, 8);
    memcpy(mismatch_short, in_setups[0], sizeof(mismatch_short)); mismatch_short[6] = 4;
    memcpy(urb.UrbControlTransfer.SetupPacket, mismatch_short, 8);
    reset_lower_observation(); check_control_rejected("setup length below transfer", &device, &request, &urb);
    setup_control_request(&device, &request, &stack, &urb, &file);
    set_mapped_control_buffer(&request, &urb, &mdl, mapped, 8);
    memcpy(mismatch_long, in_setups[0], sizeof(mismatch_long)); mismatch_long[6] = 12;
    memcpy(urb.UrbControlTransfer.SetupPacket, mismatch_long, 8);
    reset_lower_observation(); check_control_rejected("setup length above transfer", &device, &request, &urb);
    setup_control_request(&device, &request, &stack, &urb, &file);
    set_mapped_control_buffer(&request, &urb, &mdl, mapped_4097, sizeof(mapped_4097));
    memcpy(urb.UrbControlTransfer.SetupPacket, oversize_setup, 8);
    reset_lower_observation(); check_control_rejected("oversize control", &device, &request, &urb);

    /* Descriptors receive the same basic malformed/header gate. */
    setup_control_request(&device, &request, &stack, &urb, &file);
    urb.UrbControlDescriptorRequest.Hdr.Function = URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE;
    urb.UrbControlDescriptorRequest.Hdr.Length = sizeof(urb.UrbControlDescriptorRequest) - 1;
    urb.UrbControlDescriptorRequest.TransferBufferLength = 18;
    urb.UrbControlDescriptorRequest.TransferBuffer = direct;
    reset_lower_observation(); check_control_rejected("short descriptor header", &device, &request, &urb);
}

static void test_query_success_and_balance(void)
{
    struct guarded_interface guarded;
    unsigned char expected_guard[sizeof(guarded.guard)];
    NTSTATUS status;

    reset(&guarded);
    memset(expected_guard, 0xa5, sizeof(expected_guard));
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, sizeof(guarded.interface), 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &routines);
    CHECK(status == STATUS_SUCCESS, "query returned %#lx", (long)status);
    CHECK(guarded.interface.Size == sizeof(guarded.interface), "wrong size %#x", guarded.interface.Size);
    CHECK(guarded.interface.Version == 1, "wrong version %u", guarded.interface.Version);
    CHECK(guarded.interface.BusContext == (void *)0x12345678, "wrong context");
    CHECK(guarded.interface.InterfaceReference == reference, "wrong reference routine");
    CHECK(guarded.interface.InterfaceDereference == dereference, "wrong dereference routine");
    CHECK(guarded.interface.GetDeviceInterfaceGuid == getter, "wrong getter routine");
    CHECK(!memcmp(guarded.guard, expected_guard, sizeof(guarded.guard)), "success overwrote guard bytes");
    CHECK(references == 1 && dereferences == 0, "unbalanced acquire %u/%u", references, dereferences);
    guarded.interface.InterfaceDereference(guarded.interface.BusContext);
    CHECK(references == 1 && dereferences == 1, "consumer did not balance reference");
}

static void test_actual_lower_speed_callback(void)
{
    struct
    {
        struct wineusb_ms_os_10_metadata_interface_v2 interface;
        UCHAR guard[16];
    } guarded;
    struct usb_device device, before;
    UCHAR speed;
    NTSTATUS status;

    memset(&device, 0, sizeof(device));
    memset(&guarded, 0xa5, sizeof(guarded));
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid,
            sizeof(guarded.interface), WINEUSB_MS_OS_10_METADATA_VERSION_2,
            (INTERFACE *)&guarded.interface, &device.winusb_metadata,
            &winusb_metadata_routines);
    CHECK(status == STATUS_SUCCESS, "actual lower v2 query returned %#lx", (long)status);
    CHECK(guarded.interface.BusContext == &device.winusb_metadata,
            "actual lower v2 changed metadata-source context");
    CHECK(guarded.interface.GetDeviceSpeed == wineusb_metadata_get_speed,
            "actual lower v2 did not expose its real speed callback");
    CHECK(!memcmp(guarded.guard, (UCHAR[16]){[0 ... 15] = 0xa5}, sizeof(guarded.guard)),
            "actual lower v2 query overwrote guard");

    device.high_speed = FALSE; speed = 0xa5;
    status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
    CHECK(status == STATUS_SUCCESS && speed == LowSpeed,
            "actual lower low speed returned %#lx/%#x", (long)status, speed);
    device.high_speed = TRUE; speed = 0xa5;
    status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
    CHECK(status == STATUS_SUCCESS && speed == HighSpeed,
            "actual lower high speed returned %#lx/%#x", (long)status, speed);
    before = device;
    status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, NULL);
    CHECK(status == STATUS_INVALID_PARAMETER,
            "actual lower null output returned %#lx", (long)status);
    CHECK(!memcmp(&device, &before, sizeof(device)),
            "actual lower null output changed device state");
    speed = 0x3c;
    status = guarded.interface.GetDeviceSpeed(NULL, &speed);
    CHECK(status == STATUS_INVALID_PARAMETER && speed == 0x3c,
            "actual lower null context returned %#lx/%#x", (long)status, speed);
    CHECK(!memcmp(&device, &before, sizeof(device)),
            "actual lower null context changed device state");
    CHECK(!memcmp(guarded.guard, (UCHAR[16]){[0 ... 15] = 0xa5}, sizeof(guarded.guard)),
            "actual lower invalid input changed query guard");
    device.removed = TRUE; speed = 0xa5;
    status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
    CHECK(status == STATUS_DEVICE_NOT_CONNECTED && speed == 0xa5,
            "actual lower removed speed returned %#lx/%#x", (long)status, speed);
    device.removed = FALSE; device.winusb_metadata.removed = TRUE; speed = 0x5a;
    status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
    CHECK(status == STATUS_DEVICE_NOT_CONNECTED && speed == 0x5a,
            "actual lower removed metadata returned %#lx/%#x", (long)status, speed);
    guarded.interface.InterfaceDereference(guarded.interface.BusContext);
}

static void check_getter(const struct wineusb_ms_os_10_metadata_source *metadata, int expected_success,
        const char *name)
{
    GUID guid, before = {0xa5a5a5a5, 0xa5a5, 0xa5a5, {0xa5,0xa5,0xa5,0xa5,0xa5,0xa5,0xa5,0xa5}};
    NTSTATUS status;

    guid = before;
    status = wineusb_ms_os_10_get_device_interface_guid(metadata, &guid);
    CHECK((status == STATUS_SUCCESS) == expected_success, "%s returned %#lx", name, (long)status);
    if (expected_success) CHECK(IsEqualGUID(&guid, &expected_guid), "%s produced wrong GUID", name);
    else CHECK(!memcmp(&guid, &before, sizeof(guid)), "%s changed failed output", name);
}

static void test_metadata_validation(void)
{
    struct wineusb_ms_os_10_metadata_source metadata =
        {{'W','I','N','U','S','B',0,0,0}, {0},
         {'{','1','2','3','4','5','6','7','8','-','9','A','b','C','-','d','E','f','0','-',
          '1','2','3','4','-','a','B','c','D','e','F','0','1','2','3','4','5','}',0}, FALSE};

    check_getter(&metadata, 1, "WINUSB metadata");
    memcpy(metadata.sub_compatible_id, "ABC", 4);
    check_getter(&metadata, 1, "WINUSB compatible-only fallback with sub-compatible ID");
    memcpy(metadata.compatible_id, "XUSB10", 7);
    memcpy(metadata.sub_compatible_id, "WINUSB", 7);
    check_getter(&metadata, 0, "unrelated compatible ID with WINUSB sub-compatible ID");
    memcpy(metadata.compatible_id, "winusb", 7);
    memset(metadata.sub_compatible_id, 0, sizeof(metadata.sub_compatible_id));
    check_getter(&metadata, 0, "lowercase compatible ID");
    memcpy(metadata.compatible_id, "WINUSB", 7);
    metadata.compatible_id[3] = 0;
    check_getter(&metadata, 0, "internally terminated compatible ID");
    memcpy(metadata.compatible_id, "WINUSB", 7);
    metadata.device_interface_guid[0] = 0;
    check_getter(&metadata, 0, "empty GUID");
    metadata.device_interface_guid[0] = '{';
    metadata.device_interface_guid[1] = 'x';
    metadata.device_interface_guid[2] = '}';
    metadata.device_interface_guid[3] = 0;
    check_getter(&metadata, 0, "malformed GUID");
    memcpy(metadata.device_interface_guid, valid_guid, sizeof(valid_guid));
    metadata.removed = TRUE;
    check_getter(&metadata, 0, "removed child");
    metadata.removed = FALSE;
    memcpy(metadata.device_interface_guid, valid_guid, sizeof(valid_guid));
    metadata.device_interface_guid[WINEUSB_MS_OS_10_GUID_SIZE - 1] = 'x';
    check_getter(&metadata, 0, "unterminated GUID storage");
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    test_query_rejections();
    test_query_success_and_balance();
    test_v2_query_and_speed_balance();
    test_actual_lower_speed_callback();
    test_select_interface_pending_child();
    test_metadata_validation();
    if (!strcmp(argv[1], "--control-descriptor")) test_control_descriptor_translation();
    if (failures) { fprintf(stderr, "%u WineUSB metadata bus-interface check(s) failed\n", failures); return 1; }
    puts("WineUSB WinUSB metadata bus-interface contract: pass");
    return 0;
}
