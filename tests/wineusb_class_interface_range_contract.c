/*
 * Device-free behavioral contract for the exact io24 UAC2 class-interface IN
 * request observed at CP4.  The test loads the built WineUSB Unix library
 * against the fake libusb SONAME and calls its real unix_usb_submit_urb entry.
 */

#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libusb.h>

#include "ntstatus.h"
#include "windef.h"
#include "winternl.h"
#include "ddk/wdm.h"
#include "ddk/usb.h"
#include "wine/list.h"
#include "unixlib.h"

void io24_fake_libusb_reset(void);
void io24_fake_libusb_set_submit_result(int result);
unsigned int io24_fake_libusb_alloc_count(void);
unsigned int io24_fake_libusb_free_count(void);
unsigned int io24_fake_libusb_buffer_free_count(void);
unsigned int io24_fake_libusb_submit_count(void);
unsigned int io24_fake_libusb_cancel_count(void);
int io24_fake_libusb_has_pending(void);
int io24_fake_libusb_pending_flags(void);
int io24_fake_libusb_pending_length(void);
int io24_fake_libusb_get_setup(unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE]);
int io24_fake_libusb_complete(enum libusb_transfer_status status,
        const unsigned char *data, size_t data_length, int actual_length);

static unsigned int failures;

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

struct io24_unix_device
{
    struct list entry;
    libusb_device_handle *handle;
    void *parent;
    unsigned int refcount;
};

struct guarded_output
{
    unsigned char data[256];
    unsigned char guard[32];
};

struct fixture
{
    struct io24_unix_device device;
    IRP irp;
    IO_STACK_LOCATION stack;
    URB urb;
    struct guarded_output output;
    struct usb_submit_urb_params params;
};

static const unsigned char guard_pattern[32] =
    {0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
     0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
     0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
     0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5};

static const unixlib_entry_t *unix_calls;

static void reset_fixture(struct fixture *fixture)
{
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;

    memset(fixture, 0, sizeof(*fixture));
    memset(fixture->output.data, 0xcc, sizeof(fixture->output.data));
    memcpy(fixture->output.guard, guard_pattern, sizeof(guard_pattern));
    fixture->device.handle = (libusb_device_handle *)(uintptr_t)0x12340000;
    fixture->device.refcount = 1;
    fixture->irp.Tail.Overlay.CurrentStackLocation = &fixture->stack;
    fixture->stack.Parameters.Others.Argument1 = &fixture->urb;

    request = &fixture->urb.UrbControlVendorClassRequest;
    request->Hdr.Length = sizeof(*request);
    request->Hdr.Function = URB_FUNCTION_CLASS_INTERFACE;
    request->Hdr.Status = (USBD_STATUS)0xffffffff;
    request->TransferFlags = USBD_TRANSFER_DIRECTION_IN | USBD_SHORT_TRANSFER_OK;
    request->TransferBufferLength = sizeof(fixture->output.data);
    request->TransferBuffer = fixture->output.data;
    request->RequestTypeReservedBits = 0;
    request->Request = 0x02;
    request->Value = 0x0100;
    request->Index = 0x0500;

    fixture->params.device = (struct unix_device *)&fixture->device;
    fixture->params.irp = &fixture->irp;
    fixture->params.transfer_buffer = fixture->output.data;
    io24_fake_libusb_reset();
}

static NTSTATUS submit_fixture(struct fixture *fixture)
{
    return unix_calls[unix_usb_submit_urb](&fixture->params);
}

static void drain_completion(IRP *expected_irp)
{
    struct usb_event event;
    struct usb_main_loop_params params = {.event = &event};
    NTSTATUS status = unix_calls[unix_usb_main_loop](&params);

    CHECK(status == STATUS_PENDING, "main loop returned %#lx", (long)status);
    if (status == STATUS_PENDING)
    {
        CHECK(event.type == USB_EVENT_TRANSFER_COMPLETE, "event type is %u", event.type);
        CHECK(event.u.completed_irp == expected_irp, "completed IRP is %p", event.u.completed_irp);
    }
}

static void test_exact_tuple_returns_captured_range_without_libusb(void)
{
    static const unsigned char expected_range[50] =
        {0x04, 0x00,
         0x44, 0xac, 0x00, 0x00, 0x44, 0xac, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
         0x80, 0xbb, 0x00, 0x00, 0x80, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
         0x88, 0x58, 0x01, 0x00, 0x88, 0x58, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
         0x00, 0x77, 0x01, 0x00, 0x00, 0x77, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00};
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;
    unsigned char before[sizeof(fixture.output.data)];
    NTSTATUS status;

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    memcpy(before, fixture.output.data, sizeof(before));
    CHECK(sizeof(*request) == 0x88, "class URB ABI size is %#lx", (unsigned long)sizeof(*request));
    status = submit_fixture(&fixture);

    CHECK(status == STATUS_SUCCESS, "submit returned %#lx", (long)status);
    CHECK(request->Hdr.Status == USBD_STATUS_SUCCESS, "USBD status is %#lx",
            (long)request->Hdr.Status);
    CHECK(request->TransferBufferLength == sizeof(expected_range), "returned length is %lu",
            (unsigned long)request->TransferBufferLength);
    CHECK(!memcmp(fixture.output.data, expected_range, sizeof(expected_range)),
            "captured RANGE payload differs");
    CHECK(!memcmp(fixture.output.data + sizeof(expected_range), before + sizeof(expected_range),
            sizeof(fixture.output.data) - sizeof(expected_range)), "response wrote past 50 bytes");
    CHECK(!memcmp(fixture.output.guard, guard_pattern, sizeof(guard_pattern)), "guard changed");
    CHECK(io24_fake_libusb_alloc_count() == 0, "alloc count is %u", io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 0, "free count is %u", io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_buffer_free_count() == 0, "buffer free count is %u",
            io24_fake_libusb_buffer_free_count());
    CHECK(io24_fake_libusb_submit_count() == 0, "submit count is %u",
            io24_fake_libusb_submit_count());
    CHECK(io24_fake_libusb_cancel_count() == 0, "cancel count is %u",
            io24_fake_libusb_cancel_count());
    CHECK(!io24_fake_libusb_has_pending(), "fake libusb has a pending transfer");
    CHECK(fixture.irp.Tail.Overlay.DriverContext[0] == NULL, "cancel handle is present");

    if (io24_fake_libusb_has_pending())
    {
        CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_CANCELLED, NULL, 0, 0) == 0,
                "RED cleanup completion failed");
        drain_completion(&fixture.irp);
    }
}

static void expect_rejected(struct fixture *fixture, NTSTATUS expected,
        USBD_STATUS expected_usbd, const char *name)
{
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request =
            &fixture->urb.UrbControlVendorClassRequest;
    NTSTATUS status = submit_fixture(fixture);

    CHECK(status == expected, "%s returned %#lx", name, (long)status);
    CHECK(request->Hdr.Status == expected_usbd, "%s USBD status is %#lx",
            name, (long)request->Hdr.Status);
    CHECK(io24_fake_libusb_submit_count() == 0, "%s submitted %u transfer(s)",
            name, io24_fake_libusb_submit_count());
    CHECK(!io24_fake_libusb_has_pending(), "%s left a pending transfer", name);
    CHECK(!memcmp(fixture->output.guard, guard_pattern, sizeof(guard_pattern)),
            "%s changed guard", name);
}

static void test_fail_closed_rejections(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->TransferFlags = USBD_SHORT_TRANSFER_OK;
    expect_rejected(&fixture, STATUS_NOT_SUPPORTED, USBD_STATUS_NOT_SUPPORTED, "OUT request");

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->TransferFlags |= 0x4;
    expect_rejected(&fixture, STATUS_NOT_SUPPORTED, USBD_STATUS_NOT_SUPPORTED, "unknown flags");

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->TransferFlags = USBD_TRANSFER_DIRECTION_IN;
    expect_rejected(&fixture, STATUS_NOT_SUPPORTED, USBD_STATUS_NOT_SUPPORTED, "short-not-ok variant");

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->Request = 0x01;
    expect_rejected(&fixture, STATUS_NOT_SUPPORTED, USBD_STATUS_NOT_SUPPORTED, "unknown request");

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->Value = 0x0200;
    expect_rejected(&fixture, STATUS_NOT_SUPPORTED, USBD_STATUS_NOT_SUPPORTED, "unknown value");

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->Index = 0x0600;
    expect_rejected(&fixture, STATUS_NOT_SUPPORTED, USBD_STATUS_NOT_SUPPORTED, "unknown index");

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->TransferBufferLength = 255;
    expect_rejected(&fixture, STATUS_NOT_SUPPORTED, USBD_STATUS_NOT_SUPPORTED, "unknown length");

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->RequestTypeReservedBits = 1;
    expect_rejected(&fixture, STATUS_NOT_SUPPORTED, USBD_STATUS_NOT_SUPPORTED, "reserved bits");

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->Hdr.Length = sizeof(*request) - 1;
    expect_rejected(&fixture, STATUS_INVALID_PARAMETER, USBD_STATUS_INVALID_PARAMETER, "short header");

    reset_fixture(&fixture);
    fixture.params.transfer_buffer = NULL;
    expect_rejected(&fixture, STATUS_INVALID_PARAMETER, USBD_STATUS_INVALID_PARAMETER, "missing buffer");
}

int main(int argc, char **argv)
{
    void *module;

    if (argc != 2)
    {
        fprintf(stderr, "usage: %s WINEUSB_UNIXLIB\n", argv[0]);
        return 2;
    }

    module = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
    if (!module)
    {
        fprintf(stderr, "FAIL: dlopen: %s\n", dlerror());
        return 1;
    }
    unix_calls = dlsym(module, "__wine_unix_call_funcs");
    if (!unix_calls)
    {
        fprintf(stderr, "FAIL: dlsym: %s\n", dlerror());
        return 1;
    }

    test_exact_tuple_returns_captured_range_without_libusb();
    test_fail_closed_rejections();

    dlclose(module);
    if (failures)
    {
        fprintf(stderr, "%u WineUSB captured-RANGE contract check(s) failed\n", failures);
        return 1;
    }
    puts("WineUSB captured-RANGE fake-libusb contract: pass");
    return 0;
}
