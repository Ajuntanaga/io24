/*
 * Device-free behavioral contract for observation-only WineUSB pipe telemetry.
 * It calls the real Unix call table against a fake libusb SONAME and preserves
 * the pre-observation return values and pipe-handle routing semantics.
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
void io24_fake_libusb_set_clear_halt_result(int result);
unsigned int io24_fake_libusb_alloc_count(void);
unsigned int io24_fake_libusb_free_count(void);
unsigned int io24_fake_libusb_submit_count(void);
unsigned int io24_fake_libusb_clear_halt_count(void);
unsigned char io24_fake_libusb_clear_halt_endpoint(void);
int io24_fake_libusb_has_pending(void);
int io24_fake_libusb_pending_type(void);
int io24_fake_libusb_pending_endpoint(void);
int io24_fake_libusb_pending_length(void);
int io24_fake_libusb_discard_pending(void);

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

static struct io24_pipe decode_pipe_handle(HANDLE handle)
{
    union
    {
        struct io24_pipe pipe;
        HANDLE handle;
    } value = {0};

    value.handle = handle;
    return value.pipe;
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
}

static NTSTATUS submit_fixture(struct fixture *fixture)
{
    return unix_calls[unix_usb_submit_urb](&fixture->params);
}

static void test_clear_halt_return_is_unchanged(void)
{
    struct fixture fixture;
    struct _URB_PIPE_REQUEST *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL);
    request = &fixture.urb.UrbPipeRequest;
    request->PipeHandle = make_pipe_handle(0x81, UsbdPipeTypeBulk);
    io24_fake_libusb_set_clear_halt_result(LIBUSB_ERROR_NOT_FOUND);
    status = submit_fixture(&fixture);

    CHECK(status == STATUS_SUCCESS, "clear-halt returned %#lx", (long)status);
    CHECK(io24_fake_libusb_clear_halt_count() == 1, "clear-halt count is %u",
            io24_fake_libusb_clear_halt_count());
    CHECK(io24_fake_libusb_clear_halt_endpoint() == 0x81, "endpoint is %#x",
            io24_fake_libusb_clear_halt_endpoint());
    CHECK(io24_fake_libusb_alloc_count() == 0, "clear-halt allocated a transfer");
    CHECK(io24_fake_libusb_submit_count() == 0, "clear-halt submitted a transfer");
}

static void test_transfer_route(USBD_PIPE_TYPE pipe_type, unsigned char endpoint,
        unsigned char expected_libusb_type)
{
    struct fixture fixture;
    struct _URB_BULK_OR_INTERRUPT_TRANSFER *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER);
    request = &fixture.urb.UrbBulkOrInterruptTransfer;
    request->PipeHandle = make_pipe_handle(endpoint, pipe_type);
    request->TransferBufferLength = 32;
    request->TransferBuffer = fixture.buffer;
    status = submit_fixture(&fixture);

    CHECK(status == STATUS_PENDING, "transfer returned %#lx", (long)status);
    CHECK(io24_fake_libusb_submit_count() == 1, "submit count is %u",
            io24_fake_libusb_submit_count());
    CHECK(io24_fake_libusb_has_pending(), "transfer is not pending");
    CHECK(io24_fake_libusb_pending_type() == expected_libusb_type,
            "libusb type is %#x", io24_fake_libusb_pending_type());
    CHECK(io24_fake_libusb_pending_endpoint() == endpoint, "endpoint is %#x",
            io24_fake_libusb_pending_endpoint());
    CHECK(io24_fake_libusb_pending_length() == 32, "length is %d",
            io24_fake_libusb_pending_length());

    if (io24_fake_libusb_has_pending())
    {
        CHECK(io24_fake_libusb_discard_pending() == 0, "discard failed");
    }
    CHECK(io24_fake_libusb_free_count() == 1, "free count is %u",
            io24_fake_libusb_free_count());
}

static void test_invalid_pipe_is_unchanged(void)
{
    struct fixture fixture;
    struct _URB_BULK_OR_INTERRUPT_TRANSFER *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER);
    request = &fixture.urb.UrbBulkOrInterruptTransfer;
    request->PipeHandle = make_pipe_handle(0x82, UsbdPipeTypeIsochronous);
    request->TransferBufferLength = 16;
    status = submit_fixture(&fixture);

    CHECK(status == USBD_STATUS_INVALID_PIPE_HANDLE, "invalid pipe returned %#lx", (long)status);
    CHECK(io24_fake_libusb_alloc_count() == 1, "allocation count is %u",
            io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 1, "free count is %u",
            io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_submit_count() == 0, "invalid pipe submitted a transfer");
    CHECK(!io24_fake_libusb_has_pending(), "invalid pipe remained pending");
}

static void test_select_configuration_scope_is_unchanged(void)
{
    struct fixture fixture;
    struct _URB_SELECT_CONFIGURATION *request;
    struct io24_pipe pipe;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_SELECT_CONFIGURATION);
    request = &fixture.urb.UrbSelectConfiguration;
    request->Hdr.Length = sizeof(*request);
    request->Interface.Length = sizeof(request->Interface);
    request->Interface.InterfaceNumber = 5;
    request->Interface.AlternateSetting = 1;
    request->Interface.NumberOfPipes = 1;
    request->Interface.Pipes[0].EndpointAddress = 0x81;
    request->Interface.Pipes[0].PipeType = UsbdPipeTypeBulk;
    status = submit_fixture(&fixture);
    pipe = decode_pipe_handle(request->Interface.Pipes[0].PipeHandle);

    CHECK(status == STATUS_SUCCESS, "select-configuration returned %#lx", (long)status);
    CHECK(pipe.endpoint == 0x81, "decoded endpoint is %#x", pipe.endpoint);
    CHECK(pipe.type == UsbdPipeTypeBulk, "decoded type is %#x", pipe.type);
    CHECK(io24_fake_libusb_alloc_count() == 0, "select-configuration allocated a transfer");
    CHECK(io24_fake_libusb_submit_count() == 0, "select-configuration submitted a transfer");
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

    test_clear_halt_return_is_unchanged();
    test_transfer_route(UsbdPipeTypeBulk, 0x81, LIBUSB_TRANSFER_TYPE_BULK);
    test_transfer_route(UsbdPipeTypeInterrupt, 0x83, LIBUSB_TRANSFER_TYPE_INTERRUPT);
    test_invalid_pipe_is_unchanged();
    test_select_configuration_scope_is_unchanged();

    dlclose(module);
    if (failures)
    {
        fprintf(stderr, "%u WineUSB pipe-observe contract check(s) failed\n", failures);
        return 1;
    }
    puts("WineUSB pipe-observe fake-libusb behavior: pass");
    return 0;
}
