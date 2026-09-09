/*
 * Device-free behavioral contract for WineUSB SELECT_CONFIGURATION parsing.
 *
 * It calls the real Unix call table against the existing fake libusb SONAME.
 * A valid variable-length request must populate pipes on every embedded
 * interface, while a malformed later record must reject the whole request
 * before mutating an earlier pipe.
 */

#include <dlfcn.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
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
unsigned int io24_fake_libusb_alloc_count(void);
unsigned int io24_fake_libusb_submit_count(void);
unsigned int io24_fake_libusb_clear_halt_count(void);
int io24_fake_libusb_has_pending(void);
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

union select_storage
{
    URB alignment;
    unsigned char bytes[512];
};

struct select_fixture
{
    struct io24_unix_device device;
    IRP irp;
    IO_STACK_LOCATION stack;
    union select_storage storage;
    struct usb_submit_urb_params params;
};

static struct _URB_SELECT_CONFIGURATION *reset_select_fixture(struct select_fixture *fixture)
{
    struct _URB_SELECT_CONFIGURATION *request;

    memset(fixture, 0, sizeof(*fixture));
    fixture->device.handle = (libusb_device_handle *)(uintptr_t)0x12340000;
    fixture->device.refcount = 1;
    fixture->irp.Tail.Overlay.CurrentStackLocation = &fixture->stack;
    request = (struct _URB_SELECT_CONFIGURATION *)fixture->storage.bytes;
    fixture->stack.Parameters.Others.Argument1 = request;
    fixture->params.device = (struct unix_device *)&fixture->device;
    fixture->params.irp = &fixture->irp;
    request->Hdr.Function = URB_FUNCTION_SELECT_CONFIGURATION;
    io24_fake_libusb_reset();
    return request;
}

static USBD_INTERFACE_INFORMATION *append_interface(unsigned char **cursor,
        unsigned char number, unsigned char alternate, ULONG pipe_count)
{
    USBD_INTERFACE_INFORMATION *interface = (USBD_INTERFACE_INFORMATION *)*cursor;
    size_t length = offsetof(USBD_INTERFACE_INFORMATION, Pipes) +
            pipe_count * sizeof(interface->Pipes[0]);

    memset(interface, 0, length);
    interface->Length = (USHORT)length;
    interface->InterfaceNumber = number;
    interface->AlternateSetting = alternate;
    interface->NumberOfPipes = pipe_count;
    *cursor += length;
    return interface;
}

static NTSTATUS submit_fixture(struct select_fixture *fixture)
{
    return unix_calls[unix_usb_submit_urb](&fixture->params);
}

static void test_all_embedded_interfaces_receive_stable_pipe_handles(void)
{
    struct select_fixture fixture;
    struct _URB_SELECT_CONFIGURATION *request;
    USBD_INTERFACE_INFORMATION *interface0, *interface2, *interface4;
    unsigned char *cursor;
    NTSTATUS status;

    request = reset_select_fixture(&fixture);
    cursor = (unsigned char *)&request->Interface;
    interface0 = append_interface(&cursor, 0, 0, 0);
    interface2 = append_interface(&cursor, 2, 0, 1);
    interface2->Pipes[0].EndpointAddress = 0x83;
    interface2->Pipes[0].PipeType = UsbdPipeTypeInterrupt;
    interface4 = append_interface(&cursor, 4, 0, 2);
    interface4->Pipes[0].EndpointAddress = 0x02;
    interface4->Pipes[0].PipeType = UsbdPipeTypeBulk;
    interface4->Pipes[1].EndpointAddress = 0x82;
    interface4->Pipes[1].PipeType = UsbdPipeTypeBulk;
    request->Hdr.Length = (USHORT)(cursor - fixture.storage.bytes);

    status = submit_fixture(&fixture);

    CHECK(status == STATUS_SUCCESS, "select-configuration returned %#lx", (long)status);
    CHECK(interface0->NumberOfPipes == 0, "empty first interface changed pipe count");
    CHECK(interface2->Pipes[0].PipeHandle == (HANDLE)(uintptr_t)0x383,
            "interface 2 handle is %p", interface2->Pipes[0].PipeHandle);
    CHECK(interface4->Pipes[0].PipeHandle == (HANDLE)(uintptr_t)0x202,
            "interface 4 OUT handle is %p", interface4->Pipes[0].PipeHandle);
    CHECK(interface4->Pipes[1].PipeHandle == (HANDLE)(uintptr_t)0x282,
            "interface 4 IN handle is %p", interface4->Pipes[1].PipeHandle);
    CHECK(io24_fake_libusb_alloc_count() == 0,
            "select-configuration allocated a transfer");
    CHECK(io24_fake_libusb_submit_count() == 0,
            "select-configuration submitted a transfer");
    CHECK(io24_fake_libusb_clear_halt_count() == 0,
            "select-configuration cleared a halt");
}

static void test_malformed_later_interface_rejects_before_mutation(void)
{
    struct select_fixture fixture;
    struct _URB_SELECT_CONFIGURATION *request;
    USBD_INTERFACE_INFORMATION *interface0, *interface4;
    unsigned char *cursor;
    NTSTATUS status;

    request = reset_select_fixture(&fixture);
    cursor = (unsigned char *)&request->Interface;
    interface0 = append_interface(&cursor, 0, 0, 1);
    interface0->Pipes[0].EndpointAddress = 0x81;
    interface0->Pipes[0].PipeType = UsbdPipeTypeBulk;
    interface4 = append_interface(&cursor, 4, 0, 1);
    interface4->NumberOfPipes = 2;
    interface4->Pipes[0].EndpointAddress = 0x82;
    interface4->Pipes[0].PipeType = UsbdPipeTypeBulk;
    request->Hdr.Length = (USHORT)(cursor - fixture.storage.bytes);

    status = submit_fixture(&fixture);

    CHECK(status == STATUS_INVALID_PARAMETER, "malformed request returned %#lx", (long)status);
    CHECK(request->Hdr.Status == USBD_STATUS_INVALID_PARAMETER,
            "malformed USBD status is %#lx", (long)request->Hdr.Status);
    CHECK(interface0->Pipes[0].PipeHandle == NULL,
            "earlier interface was partially mutated to %p", interface0->Pipes[0].PipeHandle);
    CHECK(interface4->Pipes[0].PipeHandle == NULL,
            "malformed interface was mutated to %p", interface4->Pipes[0].PipeHandle);
    CHECK(io24_fake_libusb_alloc_count() == 0, "malformed request allocated a transfer");
    CHECK(io24_fake_libusb_submit_count() == 0, "malformed request submitted a transfer");
    CHECK(io24_fake_libusb_clear_halt_count() == 0, "malformed request cleared a halt");
}

static void test_nonzero_transfer_with_null_buffer_fails_before_submission(void)
{
    struct select_fixture fixture;
    URB *urb;
    struct _URB_BULK_OR_INTERRUPT_TRANSFER *request;
    NTSTATUS status;

    memset(&fixture, 0, sizeof(fixture));
    fixture.device.handle = (libusb_device_handle *)(uintptr_t)0x12340000;
    fixture.device.refcount = 1;
    fixture.irp.Tail.Overlay.CurrentStackLocation = &fixture.stack;
    urb = (URB *)fixture.storage.bytes;
    fixture.stack.Parameters.Others.Argument1 = urb;
    fixture.params.device = (struct unix_device *)&fixture.device;
    fixture.params.irp = &fixture.irp;
    fixture.params.transfer_buffer = NULL;
    request = &urb->UrbBulkOrInterruptTransfer;
    request->Hdr.Function = URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    request->PipeHandle = (HANDLE)(uintptr_t)0x202;
    request->TransferBufferLength = 512;
    io24_fake_libusb_reset();

    status = submit_fixture(&fixture);

    CHECK(status == STATUS_INVALID_PARAMETER, "null-buffer transfer returned %#lx", (long)status);
    CHECK(request->Hdr.Status == USBD_STATUS_INVALID_PARAMETER,
            "null-buffer USBD status is %#lx", (long)request->Hdr.Status);
    CHECK(io24_fake_libusb_alloc_count() == 0, "null-buffer transfer allocated libusb state");
    CHECK(io24_fake_libusb_submit_count() == 0, "null-buffer transfer reached libusb submit");
    if (io24_fake_libusb_has_pending())
        CHECK(io24_fake_libusb_discard_pending() == 0, "pending transfer cleanup failed");
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

    test_all_embedded_interfaces_receive_stable_pipe_handles();
    test_malformed_later_interface_rejects_before_mutation();
    test_nonzero_transfer_with_null_buffer_fails_before_submission();

    dlclose(module);
    if (failures)
    {
        fprintf(stderr, "%u WineUSB multi-interface handle contract check(s) failed\n", failures);
        return 1;
    }
    puts("WineUSB multi-interface handle contract: pass");
    return 0;
}
