/*
 * Device-free behavior contract for WineUSB composite function scoping.
 *
 * It enumerates the real Unix library against a synthetic io24 libusb device,
 * checks the function PDO roots, completes real GET_DESCRIPTOR submissions,
 * and checks SELECT_CONFIGURATION membership enforcement.
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
#include "unixlib.h"

int io24_fake_libusb_get_setup(unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE]);
int io24_fake_libusb_complete(enum libusb_transfer_status status,
        const unsigned char *data, size_t data_length);

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

/*
 * Literal configuration from the sealed passive capture.  Its SHA-256 is
 * 69131e7af6340cb70cdaaf134548e6f6ebab66c869a94b78073d69a9e3aaa51c.
 */
static const unsigned char physical_configuration[] =
{
    0x09, 0x02, 0x88, 0x01, 0x07, 0x01, 0x00, 0x80, 0xfa,
    0x08, 0x0b, 0x00, 0x03, 0x01, 0x00, 0x20, 0x10,
    0x09, 0x04, 0x00, 0x00, 0x00, 0x01, 0x01, 0x20, 0x10,
    0x09, 0x24, 0x01, 0x00, 0x02, 0x08, 0x4b, 0x00, 0x01,
    0x08, 0x24, 0x0a, 0x05, 0x03, 0x07, 0x00, 0x19,
    0x11, 0x24, 0x02, 0x01, 0x03, 0x06, 0x00, 0x05, 0x06, 0x00, 0x00, 0x00,
    0x00, 0x21, 0x00, 0x00, 0x13,
    0x0c, 0x24, 0x03, 0x02, 0x01, 0x01, 0x00, 0x01, 0x05, 0x00, 0x00, 0x13,
    0x11, 0x24, 0x02, 0x03, 0x01, 0x01, 0x00, 0x05, 0x06, 0x00, 0x00, 0x00,
    0x00, 0x27, 0x00, 0x00, 0x16,
    0x0c, 0x24, 0x03, 0x04, 0x03, 0x06, 0x00, 0x03, 0x05, 0x00, 0x00, 0x16,
    0x09, 0x04, 0x01, 0x00, 0x00, 0x01, 0x02, 0x20, 0x13,
    0x09, 0x04, 0x01, 0x01, 0x01, 0x01, 0x02, 0x20, 0x13,
    0x10, 0x24, 0x01, 0x02, 0x05, 0x01, 0x01, 0x00, 0x00, 0x00, 0x06, 0x00,
    0x00, 0x00, 0x00, 0x21,
    0x06, 0x24, 0x02, 0x01, 0x04, 0x18,
    0x07, 0x05, 0x83, 0x25, 0x38, 0x01, 0x01,
    0x08, 0x25, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x09, 0x04, 0x02, 0x00, 0x00, 0x01, 0x02, 0x20, 0x16,
    0x09, 0x04, 0x02, 0x01, 0x02, 0x01, 0x02, 0x20, 0x16,
    0x10, 0x24, 0x01, 0x03, 0x05, 0x01, 0x01, 0x00, 0x00, 0x00, 0x06, 0x00,
    0x00, 0x00, 0x00, 0x27,
    0x06, 0x24, 0x02, 0x01, 0x04, 0x18,
    0x07, 0x05, 0x03, 0x05, 0x38, 0x01, 0x01,
    0x08, 0x25, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x07, 0x05, 0x84, 0x11, 0x04, 0x00, 0x04,
    0x09, 0x04, 0x03, 0x00, 0x00, 0x01, 0x01, 0x00, 0x05,
    0x09, 0x24, 0x01, 0x00, 0x01, 0x09, 0x00, 0x01, 0x04,
    0x09, 0x04, 0x04, 0x00, 0x02, 0x01, 0x03, 0x00, 0x00,
    0x07, 0x24, 0x01, 0x00, 0x01, 0x61, 0x00,
    0x06, 0x24, 0x02, 0x01, 0x0d, 0x00,
    0x09, 0x24, 0x03, 0x02, 0x09, 0x01, 0x0d, 0x01, 0x00,
    0x06, 0x24, 0x02, 0x01, 0x0e, 0x00,
    0x09, 0x24, 0x03, 0x02, 0x0a, 0x01, 0x0e, 0x01, 0x00,
    0x06, 0x24, 0x02, 0x02, 0x01, 0x00,
    0x09, 0x24, 0x03, 0x01, 0x05, 0x01, 0x01, 0x01, 0x00,
    0x06, 0x24, 0x02, 0x02, 0x02, 0x00,
    0x09, 0x24, 0x03, 0x01, 0x06, 0x01, 0x02, 0x01, 0x00,
    0x09, 0x05, 0x02, 0x02, 0x00, 0x02, 0x00, 0x00, 0x00,
    0x06, 0x25, 0x01, 0x02, 0x0d, 0x0e,
    0x09, 0x05, 0x82, 0x02, 0x00, 0x02, 0x00, 0x00, 0x00,
    0x06, 0x25, 0x01, 0x02, 0x05, 0x06,
    0x09, 0x04, 0x05, 0x00, 0x00, 0xff, 0x00, 0x00, 0x06,
    0x09, 0x04, 0x05, 0x01, 0x02, 0xff, 0x00, 0x00, 0x06,
    0x07, 0x05, 0x81, 0x02, 0x00, 0x02, 0x00,
    0x07, 0x05, 0x01, 0x02, 0x00, 0x02, 0x00,
    0x09, 0x04, 0x06, 0x00, 0x00, 0xfe, 0x01, 0x01, 0x07,
    0x09, 0x21, 0x0d, 0xd0, 0x07, 0x00, 0x10, 0x10, 0x01,
};

static const unsigned char function0_configuration[] =
{
    0x09, 0x02, 0xda, 0x00, 0x03, 0x01, 0x00, 0x80, 0xfa,
    0x08, 0x0b, 0x00, 0x03, 0x01, 0x00, 0x20, 0x10,
    0x09, 0x04, 0x00, 0x00, 0x00, 0x01, 0x01, 0x20, 0x10,
    0x09, 0x24, 0x01, 0x00, 0x02, 0x08, 0x4b, 0x00, 0x01,
    0x08, 0x24, 0x0a, 0x05, 0x03, 0x07, 0x00, 0x19,
    0x11, 0x24, 0x02, 0x01, 0x03, 0x06, 0x00, 0x05, 0x06, 0x00, 0x00, 0x00,
    0x00, 0x21, 0x00, 0x00, 0x13,
    0x0c, 0x24, 0x03, 0x02, 0x01, 0x01, 0x00, 0x01, 0x05, 0x00, 0x00, 0x13,
    0x11, 0x24, 0x02, 0x03, 0x01, 0x01, 0x00, 0x05, 0x06, 0x00, 0x00, 0x00,
    0x00, 0x27, 0x00, 0x00, 0x16,
    0x0c, 0x24, 0x03, 0x04, 0x03, 0x06, 0x00, 0x03, 0x05, 0x00, 0x00, 0x16,
    0x09, 0x04, 0x01, 0x00, 0x00, 0x01, 0x02, 0x20, 0x13,
    0x09, 0x04, 0x01, 0x01, 0x01, 0x01, 0x02, 0x20, 0x13,
    0x10, 0x24, 0x01, 0x02, 0x05, 0x01, 0x01, 0x00, 0x00, 0x00, 0x06, 0x00,
    0x00, 0x00, 0x00, 0x21,
    0x06, 0x24, 0x02, 0x01, 0x04, 0x18,
    0x07, 0x05, 0x83, 0x25, 0x38, 0x01, 0x01,
    0x08, 0x25, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x09, 0x04, 0x02, 0x00, 0x00, 0x01, 0x02, 0x20, 0x16,
    0x09, 0x04, 0x02, 0x01, 0x02, 0x01, 0x02, 0x20, 0x16,
    0x10, 0x24, 0x01, 0x03, 0x05, 0x01, 0x01, 0x00, 0x00, 0x00, 0x06, 0x00,
    0x00, 0x00, 0x00, 0x27,
    0x06, 0x24, 0x02, 0x01, 0x04, 0x18,
    0x07, 0x05, 0x03, 0x05, 0x38, 0x01, 0x01,
    0x08, 0x25, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x07, 0x05, 0x84, 0x11, 0x04, 0x00, 0x04,
};

static const unsigned char function3_configuration[] =
{
    0x09, 0x02, 0x85, 0x00, 0x02, 0x01, 0x00, 0x80, 0xfa,
    0x09, 0x04, 0x03, 0x00, 0x00, 0x01, 0x01, 0x00, 0x05,
    0x09, 0x24, 0x01, 0x00, 0x01, 0x09, 0x00, 0x01, 0x04,
    0x09, 0x04, 0x04, 0x00, 0x02, 0x01, 0x03, 0x00, 0x00,
    0x07, 0x24, 0x01, 0x00, 0x01, 0x61, 0x00,
    0x06, 0x24, 0x02, 0x01, 0x0d, 0x00,
    0x09, 0x24, 0x03, 0x02, 0x09, 0x01, 0x0d, 0x01, 0x00,
    0x06, 0x24, 0x02, 0x01, 0x0e, 0x00,
    0x09, 0x24, 0x03, 0x02, 0x0a, 0x01, 0x0e, 0x01, 0x00,
    0x06, 0x24, 0x02, 0x02, 0x01, 0x00,
    0x09, 0x24, 0x03, 0x01, 0x05, 0x01, 0x01, 0x01, 0x00,
    0x06, 0x24, 0x02, 0x02, 0x02, 0x00,
    0x09, 0x24, 0x03, 0x01, 0x06, 0x01, 0x02, 0x01, 0x00,
    0x09, 0x05, 0x02, 0x02, 0x00, 0x02, 0x00, 0x00, 0x00,
    0x06, 0x25, 0x01, 0x02, 0x0d, 0x0e,
    0x09, 0x05, 0x82, 0x02, 0x00, 0x02, 0x00, 0x00, 0x00,
    0x06, 0x25, 0x01, 0x02, 0x05, 0x06,
};

static const unsigned char function5_configuration[] =
{
    0x09, 0x02, 0x29, 0x00, 0x01, 0x01, 0x00, 0x80, 0xfa,
    0x09, 0x04, 0x05, 0x00, 0x00, 0xff, 0x00, 0x00, 0x06,
    0x09, 0x04, 0x05, 0x01, 0x02, 0xff, 0x00, 0x00, 0x06,
    0x07, 0x05, 0x81, 0x02, 0x00, 0x02, 0x00,
    0x07, 0x05, 0x01, 0x02, 0x00, 0x02, 0x00,
};

static const unsigned char function6_configuration[] =
{
    0x09, 0x02, 0x1b, 0x00, 0x01, 0x01, 0x00, 0x80, 0xfa,
    0x09, 0x04, 0x06, 0x00, 0x00, 0xfe, 0x01, 0x01, 0x07,
    0x09, 0x21, 0x0d, 0xd0, 0x07, 0x00, 0x10, 0x10, 0x01,
};

struct enumerated_device
{
    struct unix_device *unix_device;
    bool interface;
    int16_t interface_index;
    uint8_t class, subclass, protocol;
};

struct descriptor_fixture
{
    IRP irp;
    IO_STACK_LOCATION stack;
    URB urb;
    unsigned char output[512];
    struct usb_submit_urb_params params;
};

union select_storage
{
    URB alignment;
    unsigned char bytes[512];
};

struct select_fixture
{
    IRP irp;
    IO_STACK_LOCATION stack;
    union select_storage storage;
    struct usb_submit_urb_params params;
};

static void collect_device(struct enumerated_device *device)
{
    struct usb_event event;
    struct usb_main_loop_params params = { .event = &event };
    NTSTATUS status = unix_calls[unix_usb_main_loop](&params);

    CHECK(status == STATUS_PENDING, "event loop returned %#lx", (long)status);
    CHECK(event.type == USB_EVENT_ADD_DEVICE, "event type is %u", event.type);
    if (status != STATUS_PENDING || event.type != USB_EVENT_ADD_DEVICE)
    {
        memset(device, 0, sizeof(*device));
        return;
    }
    device->unix_device = event.u.added_device.device;
    device->interface = event.u.added_device.interface;
    device->interface_index = event.u.added_device.interface_index;
    device->class = event.u.added_device.class;
    device->subclass = event.u.added_device.subclass;
    device->protocol = event.u.added_device.protocol;
}

static void test_enumerates_function_roots(struct enumerated_device devices[5])
{
    static const int16_t expected_indices[] = {-1, 0, 3, 5, 6};
    static const uint8_t expected_classes[] = {0, 1, 1, 0xff, 0xfe};
    unsigned int i;

    for (i = 0; i < 5; ++i)
    {
        collect_device(&devices[i]);
        CHECK(devices[i].interface == (i != 0),
                "event %u interface flag is %u", i, devices[i].interface);
        CHECK(devices[i].interface_index == expected_indices[i],
                "event %u interface index is %d, expected %d", i,
                devices[i].interface_index, expected_indices[i]);
        CHECK(devices[i].class == expected_classes[i],
                "event %u class is %#x, expected %#x", i,
                devices[i].class, expected_classes[i]);
    }
}

static void test_partial_configuration(struct unix_device *device, unsigned int root,
        const unsigned char *expected, size_t expected_length)
{
    const size_t capacities[] = {LIBUSB_DT_CONFIG_SIZE, expected_length};
    unsigned int i;

    for (i = 0; i < ARRAY_SIZE(capacities); ++i)
    {
        struct descriptor_fixture fixture;
        struct _URB_CONTROL_DESCRIPTOR_REQUEST *request;
        unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE];
        size_t returned_length = capacities[i] < expected_length ? capacities[i] : expected_length;
        unsigned int submitted_length;
        NTSTATUS status;

        memset(&fixture, 0, sizeof(fixture));
        fixture.irp.Tail.Overlay.CurrentStackLocation = &fixture.stack;
        fixture.stack.Parameters.Others.Argument1 = &fixture.urb;
        fixture.params.device = device;
        fixture.params.irp = &fixture.irp;
        fixture.params.transfer_buffer = fixture.output;
        request = &fixture.urb.UrbControlDescriptorRequest;
        request->Hdr.Length = sizeof(*request);
        request->Hdr.Function = URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE;
        request->DescriptorType = LIBUSB_DT_CONFIG;
        request->TransferBufferLength = capacities[i];

        status = unix_calls[unix_usb_submit_urb](&fixture.params);
        CHECK(status == STATUS_PENDING, "descriptor submit returned %#lx", (long)status);
        CHECK(io24_fake_libusb_get_setup(setup) == 0, "descriptor setup is unavailable");
        submitted_length = setup[6] | ((unsigned int)setup[7] << 8);
        CHECK(submitted_length == sizeof(physical_configuration),
                "physical request length is %u, expected %zu", submitted_length,
                sizeof(physical_configuration));
        CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_COMPLETED,
                physical_configuration, sizeof(physical_configuration)) == 0,
                "descriptor completion failed");
        CHECK(request->Hdr.Status == USBD_STATUS_SUCCESS,
                "descriptor USBD status is %#lx", (long)request->Hdr.Status);
        CHECK(request->TransferBufferLength == returned_length,
                "partial descriptor length is %u, expected %zu",
                request->TransferBufferLength, returned_length);
        CHECK(request->TransferBufferLength == returned_length &&
                !memcmp(fixture.output, expected, returned_length),
                "partial descriptor bytes differ for root %u at capacity %zu",
                root, capacities[i]);
    }
}

static USBD_INTERFACE_INFORMATION *append_interface(unsigned char **cursor,
        unsigned char number, ULONG pipe_count)
{
    USBD_INTERFACE_INFORMATION *interface = (USBD_INTERFACE_INFORMATION *)*cursor;
    size_t length = offsetof(USBD_INTERFACE_INFORMATION, Pipes) +
            pipe_count * sizeof(interface->Pipes[0]);

    memset(interface, 0, length);
    interface->Length = length;
    interface->InterfaceNumber = number;
    interface->NumberOfPipes = pipe_count;
    *cursor += length;
    return interface;
}

static struct _URB_SELECT_CONFIGURATION *reset_select_fixture(
        struct select_fixture *fixture, struct unix_device *device)
{
    struct _URB_SELECT_CONFIGURATION *request;

    memset(fixture, 0, sizeof(*fixture));
    fixture->irp.Tail.Overlay.CurrentStackLocation = &fixture->stack;
    request = (struct _URB_SELECT_CONFIGURATION *)fixture->storage.bytes;
    fixture->stack.Parameters.Others.Argument1 = request;
    fixture->params.device = device;
    fixture->params.irp = &fixture->irp;
    request->Hdr.Function = URB_FUNCTION_SELECT_CONFIGURATION;
    return request;
}

static void test_select_configuration_enforces_membership(
        struct unix_device *function0, struct unix_device *function3)
{
    struct select_fixture fixture;
    struct _URB_SELECT_CONFIGURATION *request;
    USBD_INTERFACE_INFORMATION *interface;
    unsigned char *cursor;
    NTSTATUS status;

    request = reset_select_fixture(&fixture, function0);
    cursor = (unsigned char *)&request->Interface;
    interface = append_interface(&cursor, 4, 1);
    interface->Pipes[0].EndpointAddress = 0x82;
    interface->Pipes[0].PipeType = UsbdPipeTypeBulk;
    request->Hdr.Length = cursor - fixture.storage.bytes;
    status = unix_calls[unix_usb_submit_urb](&fixture.params);
    CHECK(status == STATUS_INVALID_PARAMETER,
            "function 0 accepted interface 4 with status %#lx", (long)status);
    CHECK(request->Hdr.Status == USBD_STATUS_INVALID_PARAMETER,
            "out-of-scope USBD status is %#lx", (long)request->Hdr.Status);
    CHECK(interface->Pipes[0].PipeHandle == NULL,
            "out-of-scope interface received handle %p", interface->Pipes[0].PipeHandle);

    request = reset_select_fixture(&fixture, function3);
    cursor = (unsigned char *)&request->Interface;
    append_interface(&cursor, 3, 0);
    interface = append_interface(&cursor, 4, 2);
    interface->Pipes[0].EndpointAddress = 0x02;
    interface->Pipes[0].PipeType = UsbdPipeTypeBulk;
    interface->Pipes[1].EndpointAddress = 0x82;
    interface->Pipes[1].PipeType = UsbdPipeTypeBulk;
    request->Hdr.Length = cursor - fixture.storage.bytes;
    status = unix_calls[unix_usb_submit_urb](&fixture.params);
    CHECK(status == STATUS_SUCCESS,
            "function 3 rejected its collection with status %#lx", (long)status);
    CHECK(interface->Pipes[0].PipeHandle == (HANDLE)(uintptr_t)0x202,
            "function 3 OUT handle is %p", interface->Pipes[0].PipeHandle);
    CHECK(interface->Pipes[1].PipeHandle == (HANDLE)(uintptr_t)0x282,
            "function 3 IN handle is %p", interface->Pipes[1].PipeHandle);
}

int main(int argc, char **argv)
{
    struct enumerated_device devices[5];
    struct usb_main_loop_params loop_params;
    void *module;
    NTSTATUS status;

    if (argc != 2)
    {
        fprintf(stderr, "usage: %s WINEUSB_UNIXLIB\n", argv[0]);
        return 2;
    }
    CHECK(sizeof(physical_configuration) == 392,
            "physical fixture length is %zu", sizeof(physical_configuration));

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

    status = unix_calls[unix_usb_init](NULL);
    CHECK(status == STATUS_SUCCESS, "usb init returned %#lx", (long)status);
    test_enumerates_function_roots(devices);
    test_partial_configuration(devices[1].unix_device, 0,
            function0_configuration, sizeof(function0_configuration));
    test_partial_configuration(devices[2].unix_device, 3,
            function3_configuration, sizeof(function3_configuration));
    test_partial_configuration(devices[3].unix_device, 5,
            function5_configuration, sizeof(function5_configuration));
    test_partial_configuration(devices[4].unix_device, 6,
            function6_configuration, sizeof(function6_configuration));
    test_select_configuration_enforces_membership(
            devices[1].unix_device, devices[2].unix_device);

    unix_calls[unix_usb_exit](NULL);
    memset(&loop_params, 0, sizeof(loop_params));
    status = unix_calls[unix_usb_main_loop](&loop_params);
    CHECK(status == STATUS_SUCCESS, "shutdown loop returned %#lx", (long)status);
    dlclose(module);

    if (failures)
    {
        fprintf(stderr, "%u WineUSB function-scope contract check(s) failed\n", failures);
        return 1;
    }
    puts("WineUSB function-scope contract: pass");
    return 0;
}
