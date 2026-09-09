/*
 * Offline contract test for the Wine wineusb USBDI query-interface helper.
 *
 * This test intentionally uses literal, independently checked ABI values from
 * the Windows USBDI V1 contract.  It links the real helper from the patched
 * Wine source tree; no USB device or Wine process is involved.
 */

#include <stdio.h>
#include <string.h>

#include "usbdi.h"

static unsigned int failures;
static unsigned int reference_count;
static unsigned int dereference_count;

#define CHECK(condition, ...) \
    do \
    { \
        if (!(condition)) \
        { \
            fprintf(stderr, "FAIL %s:%u: ", __func__, __LINE__); \
            fprintf(stderr, __VA_ARGS__); \
            fputc('\n', stderr); \
            ++failures; \
        } \
    } while (0)

static void WINAPI test_reference(void *context)
{
    CHECK(context == (void *)0x12345678, "unexpected context %p", context);
    ++reference_count;
}

static void WINAPI test_dereference(void *context)
{
    CHECK(context == (void *)0x12345678, "unexpected context %p", context);
    ++dereference_count;
}

static void WINAPI test_get_usbdi_version(void *context,
        USBD_VERSION_INFORMATION *version, ULONG *capabilities)
{
    (void)context;
    (void)version;
    (void)capabilities;
}

static NTSTATUS WINAPI test_query_bus_time(void *context, ULONG *frame)
{
    (void)context;
    (void)frame;
    return STATUS_NOT_SUPPORTED;
}

static NTSTATUS WINAPI test_submit_iso_out_urb(void *context, URB *urb)
{
    (void)context;
    (void)urb;
    return STATUS_NOT_SUPPORTED;
}

static NTSTATUS WINAPI test_query_bus_information(void *context, ULONG level,
        void *buffer, ULONG *buffer_length, ULONG *actual_length)
{
    (void)context;
    (void)level;
    (void)buffer;
    (void)buffer_length;
    (void)actual_length;
    return STATUS_NOT_SUPPORTED;
}

static BOOLEAN WINAPI test_is_device_high_speed(void *context)
{
    (void)context;
    return TRUE;
}

static const struct wineusb_usbdi_routines test_routines =
{
    test_reference,
    test_dereference,
    test_get_usbdi_version,
    test_query_bus_time,
    test_submit_iso_out_urb,
    test_query_bus_information,
    test_is_device_high_speed,
};

static const GUID usbdi_guid =
    {0xb1a96a13, 0x3de0, 0x4574, {0x9b, 0x01, 0xc0, 0x8f, 0xea, 0xb3, 0x18, 0xd6}};
static const GUID unrelated_guid =
    {0xdeadbeef, 0xcafe, 0x4000, {0x80, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06}};

struct guarded_interface
{
    struct wineusb_usb_bus_interface_usbdi_v1 interface;
    unsigned char guard[16];
};

static void reset_guarded(struct guarded_interface *guarded)
{
    memset(guarded, 0xa5, sizeof(*guarded));
    reference_count = 0;
    dereference_count = 0;
}

static void test_rejects_unknown_guid_without_mutation(void)
{
    struct guarded_interface guarded, before;
    NTSTATUS status;

    reset_guarded(&guarded);
    before = guarded;
    status = wineusb_query_usbdi_interface(&unrelated_guid, 0x48, 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &test_routines);

    CHECK(status == STATUS_NOT_SUPPORTED, "got status %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "output buffer changed");
    CHECK(reference_count == 0, "reference count is %u", reference_count);
}

static void test_rejects_unsupported_versions_without_mutation(void)
{
    static const struct { USHORT size, version; } cases[] = {{0x50, 2}, {0x60, 3}};
    struct guarded_interface guarded, before;
    unsigned int i;

    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
    {
        NTSTATUS status;

        reset_guarded(&guarded);
        before = guarded;
        status = wineusb_query_usbdi_interface(&usbdi_guid, cases[i].size,
                cases[i].version, (INTERFACE *)&guarded.interface,
                (void *)0x12345678, &test_routines);

        CHECK(status == STATUS_NOT_SUPPORTED, "version %u got status %#lx",
                cases[i].version, (long)status);
        CHECK(!memcmp(&guarded, &before, sizeof(guarded)),
                "version %u changed output buffer", cases[i].version);
        CHECK(reference_count == 0, "version %u reference count is %u",
                cases[i].version, reference_count);
    }
}

static void test_rejects_undersized_v1_without_mutation(void)
{
    struct guarded_interface guarded, before;
    NTSTATUS status;

    reset_guarded(&guarded);
    before = guarded;
    status = wineusb_query_usbdi_interface(&usbdi_guid, 0x47, 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &test_routines);

    CHECK(status == STATUS_NOT_SUPPORTED, "got status %#lx", (long)status);
    CHECK(!memcmp(&guarded, &before, sizeof(guarded)), "output buffer changed");
    CHECK(reference_count == 0, "reference count is %u", reference_count);
}

static void test_exports_exact_v1_contract_and_takes_reference(void)
{
    static const unsigned char guard_bytes[16] =
        {0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
         0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5};
    struct guarded_interface guarded;
    NTSTATUS status;

    reset_guarded(&guarded);
    status = wineusb_query_usbdi_interface(&usbdi_guid, 0x48, 1,
            (INTERFACE *)&guarded.interface, (void *)0x12345678, &test_routines);

    CHECK(sizeof(guarded.interface) == 0x48, "V1 ABI size is %#lx",
            (unsigned long)sizeof(guarded.interface));
    CHECK(status == STATUS_SUCCESS, "got status %#lx", (long)status);
    CHECK(guarded.interface.Size == 0x48, "got size %#x", guarded.interface.Size);
    CHECK(guarded.interface.Version == 1, "got version %u", guarded.interface.Version);
    CHECK(guarded.interface.BusContext == (void *)0x12345678, "got context %p",
            guarded.interface.BusContext);
    CHECK(guarded.interface.InterfaceReference == test_reference,
            "wrong InterfaceReference");
    CHECK(guarded.interface.InterfaceDereference == test_dereference,
            "wrong InterfaceDereference");
    CHECK(guarded.interface.GetUSBDIVersion == test_get_usbdi_version,
            "wrong GetUSBDIVersion");
    CHECK(guarded.interface.QueryBusTime == test_query_bus_time,
            "wrong QueryBusTime");
    CHECK(guarded.interface.SubmitIsoOutUrb == test_submit_iso_out_urb,
            "wrong SubmitIsoOutUrb");
    CHECK(guarded.interface.QueryBusInformation == test_query_bus_information,
            "wrong QueryBusInformation");
    CHECK(guarded.interface.IsDeviceHighSpeed == test_is_device_high_speed,
            "wrong IsDeviceHighSpeed");
    CHECK(reference_count == 1, "reference count is %u", reference_count);
    CHECK(dereference_count == 0, "dereference count is %u", dereference_count);
    CHECK(!memcmp(guarded.guard, guard_bytes, sizeof(guarded.guard)),
            "write escaped the 0x48-byte V1 buffer");
}

int main(void)
{
    test_rejects_unknown_guid_without_mutation();
    test_rejects_unsupported_versions_without_mutation();
    test_rejects_undersized_v1_without_mutation();
    test_exports_exact_v1_contract_and_takes_reference();

    if (failures)
    {
        fprintf(stderr, "%u wineusb USBDI contract check(s) failed\n", failures);
        return 1;
    }

    puts("wineusb USBDI V1 contract checks passed");
    return 0;
}
