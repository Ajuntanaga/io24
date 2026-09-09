/* Offline CP32 contract for WineUSB's private WinUSB metadata bus interface. */

#include <stdio.h>
#include <string.h>

#include "winusb_busif.h"

static unsigned int failures, references, dereferences, speed_calls;

#define CHECK(condition, ...) do { if (!(condition)) { \
    fprintf(stderr, "FAIL %s:%u: ", __func__, __LINE__); \
    fprintf(stderr, __VA_ARGS__); fputc('\n', stderr); ++failures; } } while (0)

static void WINAPI reference(void *context)
{
    CHECK(context == (void *)0x12345678, "unexpected context %p", context);
    ++references;
}

static void WINAPI dereference(void *context)
{
    CHECK(context == (void *)0x12345678, "unexpected context %p", context);
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

static NTSTATUS WINAPI get_speed(void *context, UCHAR *speed)
{
    CHECK(context == (void *)0x12345678, "unexpected speed context %p", context);
    ++speed_calls;
    if (!speed) return STATUS_INVALID_PARAMETER;
    *speed = 0x03;
    return STATUS_SUCCESS;
}

static const struct wineusb_ms_os_10_metadata_routines routines =
{
    .InterfaceReference = reference,
    .InterfaceDereference = dereference,
    .GetDeviceInterfaceGuid = getter,
};

static const struct expected_metadata_routines_v2 routines_v2 =
{
    reference, dereference, getter, get_speed,
};

struct guarded_interface
{
    struct wineusb_ms_os_10_metadata_interface_v1 interface;
    unsigned char guard[16];
};

static void reset(struct guarded_interface *guarded)
{
    memset(guarded, 0xa5, sizeof(*guarded));
    references = dereferences = speed_calls = 0;
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
    references = dereferences = speed_calls = 0;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid, size, version,
            (INTERFACE *)&guarded.interface, (void *)0x12345678,
            (const struct wineusb_ms_os_10_metadata_routines *)&routines_v2);
    CHECK(status == STATUS_NOT_SUPPORTED, "%s returned %#lx", name, (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "%s changed output", name);
    CHECK(!references && !dereferences && !speed_calls,
            "%s changed callback balance %u/%u/%u", name, references, dereferences, speed_calls);
}

static void test_v2_query_and_speed_balance(void)
{
    struct
    {
        struct expected_metadata_interface_v2 interface;
        unsigned char guard[16];
    } guarded;
    unsigned char expected_guard[sizeof(guarded.guard)];
    UCHAR speed = 0xa5;
    NTSTATUS status;

    check_v2_rejection(sizeof(guarded.interface) - 1, 2, "undersized v2");
    check_v2_rejection(sizeof(guarded.interface) + 1, 2, "oversized v2");
    check_v2_rejection(sizeof(struct wineusb_ms_os_10_metadata_interface_v1), 2,
            "v1-size v2");
    check_v2_rejection(sizeof(guarded.interface), 3, "unsupported v2-sized version");

    memset(&guarded, 0xa5, sizeof(guarded));
    memset(expected_guard, 0xa5, sizeof(expected_guard));
    references = dereferences = speed_calls = 0;
    status = wineusb_query_ms_os_10_metadata_interface(&metadata_guid,
            sizeof(guarded.interface), 2, (INTERFACE *)&guarded.interface,
            (void *)0x12345678,
            (const struct wineusb_ms_os_10_metadata_routines *)&routines_v2);
    CHECK(status == STATUS_SUCCESS, "v2 query returned %#lx", (long)status);
    CHECK(guarded.interface.Size == sizeof(guarded.interface), "v2 wrong size %#x",
            guarded.interface.Size);
    CHECK(guarded.interface.Version == 2, "v2 wrong version %u", guarded.interface.Version);
    CHECK(guarded.interface.BusContext == (void *)0x12345678, "v2 wrong context");
    CHECK(guarded.interface.InterfaceReference == reference, "v2 wrong reference routine");
    CHECK(guarded.interface.InterfaceDereference == dereference, "v2 wrong dereference routine");
    CHECK(guarded.interface.GetDeviceInterfaceGuid == getter, "v2 wrong GUID getter");
    CHECK(guarded.interface.GetDeviceSpeed == get_speed, "v2 wrong speed getter");
    CHECK(!memcmp(guarded.guard, expected_guard, sizeof(guarded.guard)),
            "v2 success overwrote guard bytes");
    CHECK(references == 1 && !dereferences && !speed_calls,
            "v2 query callback balance %u/%u/%u", references, dereferences, speed_calls);
    if (status == STATUS_SUCCESS && guarded.interface.GetDeviceSpeed == get_speed &&
            guarded.interface.InterfaceDereference == dereference)
    {
        status = guarded.interface.GetDeviceSpeed(guarded.interface.BusContext, &speed);
        CHECK(status == STATUS_SUCCESS && speed == 0x03, "v2 speed returned %#lx/%#x",
                (long)status, speed);
        CHECK(references == 1 && !dereferences && speed_calls == 1,
                "v2 speed changed reference balance %u/%u/%u", references, dereferences, speed_calls);
        guarded.interface.InterfaceDereference(guarded.interface.BusContext);
        CHECK(references == 1 && dereferences == 1 && speed_calls == 1,
                "v2 consumer did not balance reference %u/%u/%u", references, dereferences, speed_calls);
    }
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

int main(void)
{
    test_query_rejections();
    test_query_success_and_balance();
    test_v2_query_and_speed_balance();
    test_metadata_validation();
    if (failures) { fprintf(stderr, "%u WineUSB metadata bus-interface check(s) failed\n", failures); return 1; }
    puts("WineUSB WinUSB metadata bus-interface contract: pass");
    return 0;
}
