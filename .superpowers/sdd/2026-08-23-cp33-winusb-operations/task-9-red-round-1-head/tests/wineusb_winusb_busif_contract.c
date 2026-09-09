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
        return STATUS_PENDING;
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
static void test_control_descriptor_translation(void)
{
    struct usb_device device;
    IRP request;
    IO_STACK_LOCATION stack;
    URB urb;
    unsigned char descriptor[18];
    NTSTATUS status;

    memset(&device, 0, sizeof(device)); memset(&request, 0, sizeof(request));
    memset(&stack, 0, sizeof(stack)); memset(&urb, 0, sizeof(urb));
    InitializeListHead(&device.irp_list);
    request.Tail.Overlay.CurrentStackLocation = &stack;
    stack.Parameters.Others.Argument1 = &urb;
    /* A descriptor already has a lower route.  Keep this separate from the
     * missing generic-control route, so the RED proves the actual dispatcher
     * rather than a synthetic status/count check. */
    memset(&urb, 0, sizeof(urb)); memset(descriptor, 0xa5, sizeof(descriptor));
    stack.Parameters.Others.Argument1 = &urb;
    urb.UrbControlDescriptorRequest.Hdr.Function = URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE;
    urb.UrbControlDescriptorRequest.Hdr.Length = sizeof(urb.UrbControlDescriptorRequest);
    urb.UrbControlDescriptorRequest.TransferBufferLength = sizeof(descriptor);
    urb.UrbControlDescriptorRequest.TransferBuffer = descriptor;
    urb.UrbControlDescriptorRequest.DescriptorType = 1;
    lower_submit_calls = 0; lower_last_irp = NULL; lower_last_buffer = NULL;
    status = usb_submit_urb(&device, &request);
    CHECK(status == STATUS_PENDING, "descriptor returned %#lx", (long)status);
    CHECK(lower_submit_calls == 1 && lower_last_irp == &request && lower_last_buffer == descriptor,
            "descriptor did not preserve original IRP/buffer (%u %p %p)",
            lower_submit_calls, lower_last_irp, lower_last_buffer);

    memset(&urb, 0, sizeof(urb));
    urb.UrbControlTransfer.Hdr.Function = URB_FUNCTION_CONTROL_TRANSFER;
    urb.UrbControlTransfer.Hdr.Length = sizeof(urb.UrbControlTransfer);
    urb.UrbControlTransfer.TransferFlags = USBD_TRANSFER_DIRECTION_IN;
    urb.UrbControlTransfer.TransferBufferLength = 8;
    urb.UrbControlTransfer.SetupPacket[0] = 0x80;
    urb.UrbControlTransfer.SetupPacket[1] = 6;
    lower_submit_calls = 0; lower_last_irp = NULL; lower_last_buffer = NULL;
    status = usb_submit_urb(&device, &request);
    CHECK(status == STATUS_PENDING, "generic control returned %#lx", (long)status);
    CHECK(lower_submit_calls == 1 && lower_last_irp == &request,
            "generic control reached Unix %u times with IRP %p", lower_submit_calls, lower_last_irp);

    /* Malformed generic input must fail before lower dispatch once the route
     * exists; current RED fails this assertion because the route is absent. */
    urb.UrbControlTransfer.Hdr.Length = sizeof(urb.UrbControlTransfer) - 1;
    lower_submit_calls = 0;
    status = usb_submit_urb(&device, &request);
    CHECK(status == STATUS_INVALID_PARAMETER && !lower_submit_calls,
            "short generic header returned %#lx / dispatched %u", (long)status, lower_submit_calls);
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
