/*
 * Device-free libusb fixture for WineUSB composite-function scoping.
 *
 * It enumerates one synthetic 194f:0422 device with the io24 function
 * topology and lets the contract complete descriptor transfers explicitly.
 */

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <libusb.h>

static libusb_device *const fake_device = (libusb_device *)(uintptr_t)0x194f0001;
static libusb_device_handle *const fake_handle = (libusb_device_handle *)(uintptr_t)0x194f0422;
static struct libusb_transfer *pending_transfer;

static const unsigned char interface3_extra[] =
{
    0x09, 0x24, 0x01, 0x00, 0x01, 0x09, 0x00, 0x01, 0x04,
};

static const struct libusb_endpoint_descriptor interface4_endpoints[] =
{
    {
        .bLength = 9,
        .bDescriptorType = LIBUSB_DT_ENDPOINT,
        .bEndpointAddress = 0x02,
        .bmAttributes = LIBUSB_TRANSFER_TYPE_BULK,
        .wMaxPacketSize = 512,
    },
    {
        .bLength = 9,
        .bDescriptorType = LIBUSB_DT_ENDPOINT,
        .bEndpointAddress = 0x82,
        .bmAttributes = LIBUSB_TRANSFER_TYPE_BULK,
        .wMaxPacketSize = 512,
    },
};

static const struct libusb_endpoint_descriptor interface5_endpoints[] =
{
    {
        .bLength = LIBUSB_DT_ENDPOINT_SIZE,
        .bDescriptorType = LIBUSB_DT_ENDPOINT,
        .bEndpointAddress = 0x81,
        .bmAttributes = LIBUSB_TRANSFER_TYPE_BULK,
        .wMaxPacketSize = 512,
    },
    {
        .bLength = LIBUSB_DT_ENDPOINT_SIZE,
        .bDescriptorType = LIBUSB_DT_ENDPOINT,
        .bEndpointAddress = 0x01,
        .bmAttributes = LIBUSB_TRANSFER_TYPE_BULK,
        .wMaxPacketSize = 512,
    },
};

static const struct libusb_interface_descriptor interface0_alt[] =
{
    {
        .bLength = LIBUSB_DT_INTERFACE_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE,
        .bInterfaceNumber = 0,
        .bInterfaceClass = LIBUSB_CLASS_AUDIO,
        .bInterfaceSubClass = 1,
        .bInterfaceProtocol = 0x20,
        .iInterface = 0x10,
    },
};

static const struct libusb_interface_descriptor interface1_alt[] =
{
    {
        .bLength = LIBUSB_DT_INTERFACE_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE,
        .bInterfaceNumber = 1,
        .bInterfaceClass = LIBUSB_CLASS_AUDIO,
        .bInterfaceSubClass = 2,
        .bInterfaceProtocol = 0x20,
        .iInterface = 0x13,
    },
};

static const struct libusb_interface_descriptor interface2_alt[] =
{
    {
        .bLength = LIBUSB_DT_INTERFACE_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE,
        .bInterfaceNumber = 2,
        .bInterfaceClass = LIBUSB_CLASS_AUDIO,
        .bInterfaceSubClass = 2,
        .bInterfaceProtocol = 0x20,
        .iInterface = 0x16,
    },
};

static const struct libusb_interface_descriptor interface3_alt[] =
{
    {
        .bLength = LIBUSB_DT_INTERFACE_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE,
        .bInterfaceNumber = 3,
        .bInterfaceClass = LIBUSB_CLASS_AUDIO,
        .bInterfaceSubClass = 1,
        .bInterfaceProtocol = 0,
        .iInterface = 5,
        .extra = interface3_extra,
        .extra_length = sizeof(interface3_extra),
    },
};

static const struct libusb_interface_descriptor interface4_alt[] =
{
    {
        .bLength = LIBUSB_DT_INTERFACE_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE,
        .bInterfaceNumber = 4,
        .bNumEndpoints = 2,
        .bInterfaceClass = LIBUSB_CLASS_AUDIO,
        .bInterfaceSubClass = 3,
        .endpoint = interface4_endpoints,
    },
};

static const struct libusb_interface_descriptor interface5_alt[] =
{
    {
        .bLength = LIBUSB_DT_INTERFACE_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE,
        .bInterfaceNumber = 5,
        .bInterfaceClass = LIBUSB_CLASS_VENDOR_SPEC,
        .iInterface = 6,
    },
    {
        .bLength = LIBUSB_DT_INTERFACE_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE,
        .bInterfaceNumber = 5,
        .bAlternateSetting = 1,
        .bNumEndpoints = 2,
        .bInterfaceClass = LIBUSB_CLASS_VENDOR_SPEC,
        .iInterface = 6,
        .endpoint = interface5_endpoints,
    },
};

static const struct libusb_interface_descriptor interface6_alt[] =
{
    {
        .bLength = LIBUSB_DT_INTERFACE_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE,
        .bInterfaceNumber = 6,
        .bInterfaceClass = LIBUSB_CLASS_APPLICATION,
        .bInterfaceSubClass = 1,
        .bInterfaceProtocol = 1,
        .iInterface = 7,
    },
};

static const struct libusb_interface interfaces[] =
{
    { .altsetting = interface0_alt, .num_altsetting = 1 },
    { .altsetting = interface1_alt, .num_altsetting = 1 },
    { .altsetting = interface2_alt, .num_altsetting = 1 },
    { .altsetting = interface3_alt, .num_altsetting = 1 },
    { .altsetting = interface4_alt, .num_altsetting = 1 },
    { .altsetting = interface5_alt, .num_altsetting = 2 },
    { .altsetting = interface6_alt, .num_altsetting = 1 },
};

static struct libusb_config_descriptor configuration =
{
    .bLength = LIBUSB_DT_CONFIG_SIZE,
    .bDescriptorType = LIBUSB_DT_CONFIG,
    .wTotalLength = 392,
    .bNumInterfaces = 7,
    .bConfigurationValue = 1,
    .bmAttributes = 0x80,
    .MaxPower = 250,
    .interface = interfaces,
};

static const struct libusb_interface_association_descriptor associations[] =
{
    {
        .bLength = LIBUSB_DT_INTERFACE_ASSOCIATION_SIZE,
        .bDescriptorType = LIBUSB_DT_INTERFACE_ASSOCIATION,
        .bFirstInterface = 0,
        .bInterfaceCount = 3,
        .bFunctionClass = LIBUSB_CLASS_AUDIO,
        .bFunctionProtocol = 0x20,
        .iFunction = 0x10,
    },
};

static struct libusb_interface_association_descriptor_array association_array =
{
    .iad = associations,
    .length = 1,
};

int io24_fake_libusb_get_setup(unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE])
{
    if (!pending_transfer || !pending_transfer->buffer) return -1;
    memcpy(setup, pending_transfer->buffer, LIBUSB_CONTROL_SETUP_SIZE);
    return 0;
}

int io24_fake_libusb_complete(enum libusb_transfer_status status,
        const unsigned char *data, size_t data_length)
{
    struct libusb_transfer *transfer = pending_transfer;
    size_t requested_length;

    if (!transfer) return -1;
    pending_transfer = NULL;
    requested_length = transfer->length > (int)LIBUSB_CONTROL_SETUP_SIZE
            ? (size_t)transfer->length - LIBUSB_CONTROL_SETUP_SIZE : 0;
    if (data_length > requested_length) data_length = requested_length;
    if (data_length)
        memcpy(libusb_control_transfer_get_data(transfer), data, data_length);
    transfer->status = status;
    transfer->actual_length = data_length;
    transfer->callback(transfer);
    if (transfer->flags & LIBUSB_TRANSFER_FREE_TRANSFER)
        libusb_free_transfer(transfer);
    return 0;
}

struct libusb_transfer * LIBUSB_CALL libusb_alloc_transfer(int iso_packets)
{
    size_t size;

    if (iso_packets < 0) return NULL;
    size = sizeof(struct libusb_transfer) +
            (size_t)iso_packets * sizeof(struct libusb_iso_packet_descriptor);
    return calloc(1, size);
}

void LIBUSB_CALL libusb_free_transfer(struct libusb_transfer *transfer)
{
    if (!transfer) return;
    if (transfer->flags & LIBUSB_TRANSFER_FREE_BUFFER) free(transfer->buffer);
    free(transfer);
}

int LIBUSB_CALL libusb_submit_transfer(struct libusb_transfer *transfer)
{
    if (pending_transfer) return LIBUSB_ERROR_BUSY;
    pending_transfer = transfer;
    return 0;
}

int LIBUSB_CALL libusb_cancel_transfer(struct libusb_transfer *transfer)
{
    return transfer == pending_transfer ? 0 : LIBUSB_ERROR_NOT_FOUND;
}

int LIBUSB_CALL libusb_init(libusb_context **context)
{
    if (context) *context = (libusb_context *)(uintptr_t)0x1000;
    return 0;
}

void LIBUSB_CALL libusb_exit(libusb_context *context) { (void)context; }

int LIBUSB_CALL libusb_hotplug_register_callback(libusb_context *context,
        int events, int flags, int vendor_id, int product_id, int dev_class,
        libusb_hotplug_callback_fn callback, void *user_data,
        libusb_hotplug_callback_handle *callback_handle)
{
    (void)context;
    (void)events;
    (void)vendor_id;
    (void)product_id;
    (void)dev_class;
    if (callback_handle) *callback_handle = 1;
    if (flags & LIBUSB_HOTPLUG_ENUMERATE)
        callback(NULL, fake_device, LIBUSB_HOTPLUG_EVENT_DEVICE_ARRIVED, user_data);
    return 0;
}

void LIBUSB_CALL libusb_hotplug_deregister_callback(libusb_context *context,
        libusb_hotplug_callback_handle callback_handle)
{
    (void)context;
    (void)callback_handle;
}

void LIBUSB_CALL libusb_interrupt_event_handler(libusb_context *context) { (void)context; }
int LIBUSB_CALL libusb_handle_events(libusb_context *context) { (void)context; return 0; }
int LIBUSB_CALL libusb_clear_halt(libusb_device_handle *handle, unsigned char endpoint)
{
    (void)handle;
    (void)endpoint;
    return LIBUSB_ERROR_NOT_SUPPORTED;
}

int LIBUSB_CALL libusb_open(libusb_device *device, libusb_device_handle **handle)
{
    if (device != fake_device) return LIBUSB_ERROR_NO_DEVICE;
    *handle = fake_handle;
    return 0;
}

void LIBUSB_CALL libusb_close(libusb_device_handle *handle) { (void)handle; }

libusb_device * LIBUSB_CALL libusb_get_device(libusb_device_handle *handle)
{
    return handle == fake_handle ? fake_device : NULL;
}

uint8_t LIBUSB_CALL libusb_get_bus_number(libusb_device *device)
{
    return device == fake_device ? 3 : 0;
}

uint8_t LIBUSB_CALL libusb_get_port_number(libusb_device *device)
{
    return device == fake_device ? 1 : 0;
}

int LIBUSB_CALL libusb_get_device_speed(libusb_device *device)
{
    return device == fake_device ? LIBUSB_SPEED_HIGH : LIBUSB_SPEED_UNKNOWN;
}

int LIBUSB_CALL libusb_get_device_descriptor(libusb_device *device,
        struct libusb_device_descriptor *descriptor)
{
    if (device != fake_device || !descriptor) return LIBUSB_ERROR_NO_DEVICE;
    memset(descriptor, 0, sizeof(*descriptor));
    descriptor->bLength = LIBUSB_DT_DEVICE_SIZE;
    descriptor->bDescriptorType = LIBUSB_DT_DEVICE;
    descriptor->bcdUSB = 0x0200;
    descriptor->bMaxPacketSize0 = 64;
    descriptor->idVendor = 0x194f;
    descriptor->idProduct = 0x0422;
    descriptor->bcdDevice = 0x0128;
    descriptor->bNumConfigurations = 1;
    return 0;
}

int LIBUSB_CALL libusb_get_active_config_descriptor(libusb_device *device,
        struct libusb_config_descriptor **config)
{
    if (device != fake_device || !config) return LIBUSB_ERROR_NO_DEVICE;
    *config = &configuration;
    return 0;
}

void LIBUSB_CALL libusb_free_config_descriptor(struct libusb_config_descriptor *config)
{
    (void)config;
}

int LIBUSB_CALL libusb_get_active_interface_association_descriptors(libusb_device *device,
        struct libusb_interface_association_descriptor_array **array)
{
    if (device != fake_device || !array) return LIBUSB_ERROR_NO_DEVICE;
    *array = &association_array;
    return 0;
}

void LIBUSB_CALL libusb_free_interface_association_descriptors(
        struct libusb_interface_association_descriptor_array *array)
{
    (void)array;
}

const char * LIBUSB_CALL libusb_strerror(int error_code)
{
    (void)error_code;
    return "io24 function-scope fake libusb";
}
