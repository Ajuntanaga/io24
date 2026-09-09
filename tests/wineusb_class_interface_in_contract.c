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

static const unsigned char expected_setup[LIBUSB_CONTROL_SETUP_SIZE] =
    {0xa1, 0x02, 0x00, 0x01, 0x00, 0x05, 0x00, 0x01};
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

static int require_pending_submit(struct fixture *fixture)
{
    NTSTATUS status = submit_fixture(fixture);

    CHECK(status == STATUS_PENDING, "submit returned %#lx", (long)status);
    CHECK(io24_fake_libusb_submit_count() == 1, "submit count is %u",
            io24_fake_libusb_submit_count());
    CHECK(io24_fake_libusb_has_pending(), "fake libusb has no pending transfer");
    return status == STATUS_PENDING && io24_fake_libusb_has_pending();
}

static void test_exact_setup_and_short_completion(void)
{
    static const unsigned char payload[26] =
        {0x02, 0x00, 0x80, 0xbb, 0x00, 0x00, 0x80, 0xbb, 0x00, 0x00,
         0x00, 0x00, 0x00, 0x00, 0x00, 0x77, 0x01, 0x00, 0x00, 0x77,
         0x01, 0x00, 0x00, 0x00, 0x00, 0x00};
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;
    unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE] = {0};

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    CHECK(sizeof(*request) == 0x88, "class URB ABI size is %#lx", (unsigned long)sizeof(*request));
    if (!require_pending_submit(&fixture)) return;

    CHECK(io24_fake_libusb_get_setup(setup) == 0, "could not read fake setup");
    CHECK(!memcmp(setup, expected_setup, sizeof(setup)), "setup packet differs");
    CHECK(io24_fake_libusb_pending_length() == 264, "transfer length is %d",
            io24_fake_libusb_pending_length());
    CHECK(io24_fake_libusb_pending_flags() ==
            (LIBUSB_TRANSFER_FREE_BUFFER | LIBUSB_TRANSFER_FREE_TRANSFER),
            "libusb flags are %#x", io24_fake_libusb_pending_flags());
    CHECK(fixture.irp.Tail.Overlay.DriverContext[0] != NULL, "cancel handle is absent");

    CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_COMPLETED,
            payload, sizeof(payload), sizeof(payload)) == 0, "completion failed");
    drain_completion(&fixture.irp);
    CHECK(request->Hdr.Status == USBD_STATUS_SUCCESS, "USBD status is %#lx",
            (long)request->Hdr.Status);
    CHECK(request->TransferBufferLength == sizeof(payload), "returned length is %lu",
            (unsigned long)request->TransferBufferLength);
    CHECK(!memcmp(fixture.output.data, payload, sizeof(payload)), "payload was not copied");
    CHECK(!memcmp(fixture.output.guard, guard_pattern, sizeof(guard_pattern)), "guard changed");
    CHECK(io24_fake_libusb_alloc_count() == 1, "alloc count is %u", io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 1, "free count is %u", io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_buffer_free_count() == 1, "buffer free count is %u",
            io24_fake_libusb_buffer_free_count());
}

static void test_cancellation_completion(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;
    struct usb_cancel_transfer_params cancel;
    NTSTATUS status;

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    if (!require_pending_submit(&fixture)) return;
    cancel.transfer = fixture.irp.Tail.Overlay.DriverContext[0];
    status = unix_calls[unix_usb_cancel_transfer](&cancel);
    CHECK(status == STATUS_SUCCESS, "cancel returned %#lx", (long)status);
    CHECK(io24_fake_libusb_cancel_count() == 1, "cancel count is %u",
            io24_fake_libusb_cancel_count());
    CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_CANCELLED, NULL, 0, 0) == 0,
            "cancel completion failed");
    drain_completion(&fixture.irp);
    CHECK(request->Hdr.Status == USBD_STATUS_CANCELED, "cancel USBD status is %#lx",
            (long)request->Hdr.Status);
    CHECK(request->TransferBufferLength == 0, "cancel length is %lu",
            (unsigned long)request->TransferBufferLength);
    CHECK(!memcmp(fixture.output.guard, guard_pattern, sizeof(guard_pattern)), "guard changed");
}

static void test_stall_completion(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;
    unsigned char before[256];

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    memcpy(before, fixture.output.data, sizeof(before));
    if (!require_pending_submit(&fixture)) return;
    CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_STALL, NULL, 0, 0) == 0,
            "STALL completion failed");
    drain_completion(&fixture.irp);
    CHECK(request->Hdr.Status == USBD_STATUS_ENDPOINT_HALTED, "STALL USBD status is %#lx",
            (long)request->Hdr.Status);
    CHECK(request->TransferBufferLength == 0, "STALL length is %lu",
            (unsigned long)request->TransferBufferLength);
    CHECK(!memcmp(fixture.output.data, before, sizeof(before)), "STALL copied data");
    CHECK(!memcmp(fixture.output.guard, guard_pattern, sizeof(guard_pattern)), "guard changed");
}

static void test_overrun_is_not_copied(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;
    unsigned char before[256];

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    memcpy(before, fixture.output.data, sizeof(before));
    if (!require_pending_submit(&fixture)) return;
    CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_COMPLETED, NULL, 0, 257) == 0,
            "overrun completion failed");
    drain_completion(&fixture.irp);
    CHECK(request->Hdr.Status == USBD_STATUS_DATA_OVERRUN, "overrun USBD status is %#lx",
            (long)request->Hdr.Status);
    CHECK(request->TransferBufferLength == 0, "overrun length is %lu",
            (unsigned long)request->TransferBufferLength);
    CHECK(!memcmp(fixture.output.data, before, sizeof(before)), "overrun copied data");
    CHECK(!memcmp(fixture.output.guard, guard_pattern, sizeof(guard_pattern)), "guard changed");
}

static void test_immediate_submit_error_is_clean(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;
    NTSTATUS status;

    reset_fixture(&fixture);
    request = &fixture.urb.UrbControlVendorClassRequest;
    io24_fake_libusb_set_submit_result(LIBUSB_ERROR_BUSY);
    status = submit_fixture(&fixture);
    CHECK(status == STATUS_UNSUCCESSFUL, "submit error returned %#lx", (long)status);
    CHECK(request->Hdr.Status == USBD_STATUS_REQUEST_FAILED, "USBD status is %#lx",
            (long)request->Hdr.Status);
    CHECK(!io24_fake_libusb_has_pending(), "failed submit remained pending");
    CHECK(fixture.irp.Tail.Overlay.DriverContext[0] == NULL, "failed submit retained cancel handle");
    CHECK(io24_fake_libusb_alloc_count() == 1, "alloc count is %u", io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 1, "free count is %u", io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_buffer_free_count() == 1, "buffer free count is %u",
            io24_fake_libusb_buffer_free_count());
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

    test_exact_setup_and_short_completion();
    test_cancellation_completion();
    test_stall_completion();
    test_overrun_is_not_copied();
    test_immediate_submit_error_is_clean();
    test_fail_closed_rejections();

    dlclose(module);
    if (failures)
    {
        fprintf(stderr, "%u WineUSB class-interface-IN contract check(s) failed\n", failures);
        return 1;
    }
    puts("WineUSB class-interface-IN fake-libusb contract: pass");
    return 0;
}
