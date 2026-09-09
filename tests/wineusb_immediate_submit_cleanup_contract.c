/*
 * Device-free behavioral contract for WineUSB immediate-submit failures.
 *
 * It calls the real WineUSB Unix call table against the existing fake libusb
 * SONAME.  A libusb rejection must be reported synchronously and leave no
 * cancellation handle, pending transfer, transfer context, or control buffer.
 */

#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <unistd.h>

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
int io24_fake_libusb_has_pending(void);

static unsigned int failures;
static const unixlib_entry_t *unix_calls;

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

struct io24_pipe
{
    unsigned char endpoint;
    unsigned char type;
};

struct fixture
{
    struct io24_unix_device device;
    IRP irp;
    IO_STACK_LOCATION stack;
    URB urb;
    unsigned char buffer[64];
    struct usb_submit_urb_params params;
};

static HANDLE make_pipe_handle(unsigned char endpoint, USBD_PIPE_TYPE type)
{
    union
    {
        struct io24_pipe pipe;
        HANDLE handle;
    } value = {0};

    value.pipe.endpoint = endpoint;
    value.pipe.type = type;
    return value.handle;
}

static void reset_fixture(struct fixture *fixture, USHORT function)
{
    memset(fixture, 0, sizeof(*fixture));
    fixture->device.handle = (libusb_device_handle *)(uintptr_t)0x12340000;
    fixture->device.refcount = 1;
    fixture->irp.Tail.Overlay.CurrentStackLocation = &fixture->stack;
    fixture->stack.Parameters.Others.Argument1 = &fixture->urb;
    fixture->urb.UrbHeader.Function = function;
    fixture->params.device = (struct unix_device *)&fixture->device;
    fixture->params.irp = &fixture->irp;
    fixture->params.transfer_buffer = fixture->buffer;
    io24_fake_libusb_reset();
    io24_fake_libusb_set_submit_result(LIBUSB_ERROR_BUSY);
}

static NTSTATUS submit_fixture(struct fixture *fixture)
{
    return unix_calls[unix_usb_submit_urb](&fixture->params);
}

static void check_rejected_submit(struct fixture *fixture, NTSTATUS status,
        unsigned int expected_buffer_frees, const char *name)
{
    CHECK(status == STATUS_UNSUCCESSFUL, "%s returned %#lx", name, (long)status);
    CHECK(fixture->urb.UrbHeader.Status == USBD_STATUS_REQUEST_FAILED,
            "%s USBD status is %#lx", name, (long)fixture->urb.UrbHeader.Status);
    CHECK(fixture->irp.Tail.Overlay.DriverContext[0] == NULL,
            "%s retained cancel handle %p", name,
            fixture->irp.Tail.Overlay.DriverContext[0]);
    CHECK(!io24_fake_libusb_has_pending(), "%s remained pending", name);
    CHECK(io24_fake_libusb_alloc_count() == 1, "%s allocation count is %u",
            name, io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 1, "%s transfer free count is %u",
            name, io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_buffer_free_count() == expected_buffer_frees,
            "%s buffer free count is %u", name,
            io24_fake_libusb_buffer_free_count());
    CHECK(io24_fake_libusb_submit_count() == 1, "%s submit count is %u",
            name, io24_fake_libusb_submit_count());
}

static void test_bulk_immediate_submit_error_is_clean(void)
{
    struct fixture fixture;
    struct _URB_BULK_OR_INTERRUPT_TRANSFER *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER);
    request = &fixture.urb.UrbBulkOrInterruptTransfer;
    request->PipeHandle = make_pipe_handle(0x82, UsbdPipeTypeBulk);
    request->TransferBufferLength = 32;
    request->TransferBuffer = fixture.buffer;

    status = submit_fixture(&fixture);

    check_rejected_submit(&fixture, status, 0, "bulk");
}

static void test_invalid_pipe_does_not_retain_freed_cancel_handle(void)
{
    struct fixture fixture;
    struct _URB_BULK_OR_INTERRUPT_TRANSFER *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER);
    request = &fixture.urb.UrbBulkOrInterruptTransfer;
    request->PipeHandle = make_pipe_handle(0x82, UsbdPipeTypeIsochronous);
    request->TransferBufferLength = 32;
    request->TransferBuffer = fixture.buffer;

    status = submit_fixture(&fixture);

    CHECK(status == USBD_STATUS_INVALID_PIPE_HANDLE,
            "invalid pipe returned %#lx", (long)status);
    CHECK(fixture.irp.Tail.Overlay.DriverContext[0] == NULL,
            "invalid pipe retained freed cancel handle %p",
            fixture.irp.Tail.Overlay.DriverContext[0]);
    CHECK(!io24_fake_libusb_has_pending(), "invalid pipe remained pending");
    CHECK(io24_fake_libusb_alloc_count() == 1, "invalid pipe allocation count is %u",
            io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 1, "invalid pipe transfer free count is %u",
            io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_submit_count() == 0, "invalid pipe submit count is %u",
            io24_fake_libusb_submit_count());
}

static void test_descriptor_immediate_submit_error_is_clean(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_DESCRIPTOR_REQUEST *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE);
    request = &fixture.urb.UrbControlDescriptorRequest;
    request->DescriptorType = LIBUSB_DT_DEVICE;
    request->TransferBufferLength = 18;

    status = submit_fixture(&fixture);

    check_rejected_submit(&fixture, status, 1, "descriptor");
}

static void test_vendor_immediate_submit_error_is_clean(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_VENDOR_INTERFACE);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->TransferFlags = USBD_TRANSFER_DIRECTION_IN;
    request->Request = 0x01;
    request->Value = 0x0200;
    request->Index = 0x0004;
    request->TransferBufferLength = 16;

    status = submit_fixture(&fixture);

    check_rejected_submit(&fixture, status, 1, "vendor-interface");
}

static bool constrain_address_space_for_control_buffer_failure(void)
{
    const rlim_t headroom = 8 * 1024 * 1024;
    struct rlimit limit;
    unsigned long virtual_pages;
    long page_size;
    FILE *statm;
    rlim_t current_size, target;

    if (!(statm = fopen("/proc/self/statm", "r"))) return false;
    if (fscanf(statm, "%lu", &virtual_pages) != 1)
    {
        fclose(statm);
        return false;
    }
    fclose(statm);

    if ((page_size = sysconf(_SC_PAGESIZE)) <= 0) return false;
    current_size = (rlim_t)virtual_pages * (rlim_t)page_size;
    if (current_size > RLIM_INFINITY - headroom) return false;
    target = current_size + headroom;

    if (getrlimit(RLIMIT_AS, &limit) < 0) return false;
    if (limit.rlim_max != RLIM_INFINITY && target > limit.rlim_max) return false;
    limit.rlim_cur = target;
    return setrlimit(RLIMIT_AS, &limit) == 0;
}

static void test_descriptor_buffer_allocation_failure_has_no_cancel_handle(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_DESCRIPTOR_REQUEST *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE);
    request = &fixture.urb.UrbControlDescriptorRequest;
    request->DescriptorType = LIBUSB_DT_DEVICE;
    request->TransferBufferLength = 64 * 1024 * 1024;

    status = submit_fixture(&fixture);

    CHECK(status == STATUS_NO_MEMORY, "descriptor allocation failure returned %#lx",
            (long)status);
    CHECK(fixture.irp.Tail.Overlay.DriverContext[0] == NULL,
            "descriptor allocation failure retained freed cancel handle %p",
            fixture.irp.Tail.Overlay.DriverContext[0]);
    CHECK(!io24_fake_libusb_has_pending(), "descriptor allocation failure remained pending");
    CHECK(io24_fake_libusb_alloc_count() == 1,
            "descriptor allocation failure transfer count is %u",
            io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 1,
            "descriptor allocation failure free count is %u",
            io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_submit_count() == 0,
            "descriptor allocation failure submit count is %u",
            io24_fake_libusb_submit_count());
}

static void test_vendor_buffer_allocation_failure_has_no_cancel_handle(void)
{
    struct fixture fixture;
    struct _URB_CONTROL_VENDOR_OR_CLASS_REQUEST *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_VENDOR_INTERFACE);
    request = &fixture.urb.UrbControlVendorClassRequest;
    request->TransferFlags = USBD_TRANSFER_DIRECTION_IN;
    request->Request = 0x01;
    request->Value = 0x0200;
    request->Index = 0x0004;
    request->TransferBufferLength = 64 * 1024 * 1024;

    status = submit_fixture(&fixture);

    CHECK(status == STATUS_NO_MEMORY, "vendor allocation failure returned %#lx",
            (long)status);
    CHECK(fixture.irp.Tail.Overlay.DriverContext[0] == NULL,
            "vendor allocation failure retained freed cancel handle %p",
            fixture.irp.Tail.Overlay.DriverContext[0]);
    CHECK(!io24_fake_libusb_has_pending(), "vendor allocation failure remained pending");
    CHECK(io24_fake_libusb_alloc_count() == 1,
            "vendor allocation failure transfer count is %u",
            io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 1,
            "vendor allocation failure free count is %u",
            io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_submit_count() == 0,
            "vendor allocation failure submit count is %u",
            io24_fake_libusb_submit_count());
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

    test_bulk_immediate_submit_error_is_clean();
    test_invalid_pipe_does_not_retain_freed_cancel_handle();
    test_descriptor_immediate_submit_error_is_clean();
    test_vendor_immediate_submit_error_is_clean();
    if (constrain_address_space_for_control_buffer_failure())
    {
        test_descriptor_buffer_allocation_failure_has_no_cancel_handle();
        test_vendor_buffer_allocation_failure_has_no_cancel_handle();
    }
    else
    {
        CHECK(false, "could not constrain address space for allocation-failure tests");
    }

    dlclose(module);
    if (failures)
    {
        fprintf(stderr, "%u WineUSB immediate-submit cleanup check(s) failed\n",
                failures);
        return 1;
    }
    puts("WineUSB immediate-submit cleanup contract: pass");
    return 0;
}
