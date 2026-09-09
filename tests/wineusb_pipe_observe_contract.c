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
void io24_fake_libusb_enable_mi05_active_descriptor(int enable);
void io24_fake_libusb_enable_interrupt_active_descriptor(int enable);
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
    bool function;
    uint8_t function_interface_count;
    uint16_t configuration_length;
    uint8_t function_root;
    unsigned char function_interfaces[32];
    unsigned char claimed_interfaces[32];
    void *pipe_table;
    void *pending_claim_transaction;
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

static HANDLE select_pipe(struct fixture *fixture, unsigned char endpoint,
        USBD_PIPE_TYPE type)
{
    struct _URB_SELECT_CONFIGURATION *select = &fixture->urb.UrbSelectConfiguration;
    unsigned int pipes = endpoint == 0x83 ? 1 : 2;

    /* A usable production token requires an active descriptor; reset remains
     * intentionally descriptor-disabled for negative schedules. */
    io24_fake_libusb_enable_mi05_active_descriptor(1);
    io24_fake_libusb_enable_interrupt_active_descriptor(endpoint == 0x83);
    memset(&fixture->urb, 0, sizeof(fixture->urb));
    select->Hdr.Function = URB_FUNCTION_SELECT_CONFIGURATION;
    select->Hdr.Length = offsetof(struct _URB_SELECT_CONFIGURATION, Interface) +
            offsetof(USBD_INTERFACE_INFORMATION, Pipes) + pipes * sizeof(USBD_PIPE_INFORMATION);
    select->Interface.Length = offsetof(USBD_INTERFACE_INFORMATION, Pipes) +
            pipes * sizeof(USBD_PIPE_INFORMATION);
    select->Interface.InterfaceNumber = 5;
    select->Interface.AlternateSetting = 1;
    select->Interface.Class = 0xff;
    select->Interface.Protocol = 6;
    select->Interface.NumberOfPipes = pipes;
    select->Interface.Pipes[0].EndpointAddress = endpoint;
    select->Interface.Pipes[0].PipeType = type;
    select->Interface.Pipes[0].MaximumPacketSize = endpoint == 0x83 ? 64 : 512;
    select->Interface.Pipes[0].Interval = endpoint == 0x83 ? 1 : 0;
    if (pipes == 2)
    {
        select->Interface.Pipes[1].EndpointAddress = 0x01;
        select->Interface.Pipes[1].PipeType = UsbdPipeTypeBulk;
        select->Interface.Pipes[1].MaximumPacketSize = 512;
    }
    CHECK(submit_fixture(fixture) == STATUS_SUCCESS, "select-configuration failed");
    CHECK(select->Interface.Pipes[0].MaximumPacketSize == (endpoint == 0x83 ? 64 : 512),
            "descriptor maximum packet size changed");
    CHECK(select->Interface.Pipes[0].Interval == (endpoint == 0x83 ? 1 : 0),
            "descriptor interval changed");
    return select->Interface.Pipes[0].PipeHandle;
}

static void test_clear_halt_return_is_unchanged(void)
{
    struct fixture fixture;
    struct _URB_PIPE_REQUEST *request;
    HANDLE pipe;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL);
    pipe = select_pipe(&fixture, 0x81, UsbdPipeTypeBulk);
    fixture.urb.UrbHeader.Function = URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL;
    request = &fixture.urb.UrbPipeRequest;
    request->PipeHandle = pipe;
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
    HANDLE pipe;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER);
    pipe = select_pipe(&fixture, endpoint, pipe_type);
    fixture.urb.UrbHeader.Function = URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    request = &fixture.urb.UrbBulkOrInterruptTransfer;
    request->PipeHandle = pipe;
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
    request->PipeHandle = (HANDLE)(uintptr_t)0x7fffffff;
    request->TransferBufferLength = 16;
    status = submit_fixture(&fixture);

    CHECK(status == STATUS_INVALID_PARAMETER, "invalid pipe returned %#lx", (long)status);
    CHECK(io24_fake_libusb_alloc_count() == 0, "allocation count is %u",
            io24_fake_libusb_alloc_count());
    CHECK(io24_fake_libusb_free_count() == 0, "free count is %u",
            io24_fake_libusb_free_count());
    CHECK(io24_fake_libusb_submit_count() == 0, "invalid pipe submitted a transfer");
    CHECK(!io24_fake_libusb_has_pending(), "invalid pipe remained pending");
}

static void test_select_configuration_scope_is_unchanged(void)
{
    struct fixture fixture;
    struct _URB_SELECT_CONFIGURATION *request;
    NTSTATUS status;

    reset_fixture(&fixture, URB_FUNCTION_SELECT_CONFIGURATION);
    request = &fixture.urb.UrbSelectConfiguration;
    request->Hdr.Length = offsetof(struct _URB_SELECT_CONFIGURATION, Interface) +
            offsetof(USBD_INTERFACE_INFORMATION, Pipes) + 2 * sizeof(USBD_PIPE_INFORMATION);
    request->Interface.Length = offsetof(USBD_INTERFACE_INFORMATION, Pipes) +
            2 * sizeof(USBD_PIPE_INFORMATION);
    request->Interface.InterfaceNumber = 5;
    request->Interface.AlternateSetting = 1;
    request->Interface.Class = 0xff;
    request->Interface.Protocol = 6;
    request->Interface.NumberOfPipes = 2;
    request->Interface.Pipes[0].EndpointAddress = 0x81;
    request->Interface.Pipes[0].PipeType = UsbdPipeTypeBulk;
    request->Interface.Pipes[0].MaximumPacketSize = 512;
    request->Interface.Pipes[1].EndpointAddress = 0x01;
    request->Interface.Pipes[1].PipeType = UsbdPipeTypeBulk;
    request->Interface.Pipes[1].MaximumPacketSize = 512;
    io24_fake_libusb_enable_mi05_active_descriptor(1);
    status = submit_fixture(&fixture);

    CHECK(status == STATUS_SUCCESS, "select-configuration returned %#lx", (long)status);
    CHECK(request->Interface.Pipes[0].PipeHandle != NULL, "SELECT returned no opaque handle");
    CHECK(io24_fake_libusb_alloc_count() == 0, "select-configuration allocated a transfer");
    CHECK(io24_fake_libusb_submit_count() == 0, "select-configuration submitted a transfer");
}

static void test_descriptor_backed_pipe_lookup(void)
{
    struct fixture fixture;
    struct _URB_PIPE_REQUEST *request;
    HANDLE pipe;

    reset_fixture(&fixture, URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL);
    io24_fake_libusb_enable_mi05_active_descriptor(1);
    pipe = select_pipe(&fixture, 0x81, UsbdPipeTypeBulk);
    fixture.urb.UrbHeader.Function = URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL;
    request = &fixture.urb.UrbPipeRequest;
    request->PipeHandle = pipe;
    CHECK(submit_fixture(&fixture) == STATUS_SUCCESS, "descriptor-backed clear halt failed");
    CHECK(io24_fake_libusb_clear_halt_endpoint() == 0x81, "descriptor-backed endpoint mismatch");
    io24_fake_libusb_enable_mi05_active_descriptor(0);
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
    test_descriptor_backed_pipe_lookup();

    dlclose(module);
    if (failures)
    {
        fprintf(stderr, "%u WineUSB pipe-observe contract check(s) failed\n", failures);
        return 1;
    }
    puts("WineUSB pipe-observe fake-libusb behavior: pass");
    return 0;
}
