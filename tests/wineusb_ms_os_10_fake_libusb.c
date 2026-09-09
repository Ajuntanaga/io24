/*
 * Device-free libusb fixture for Microsoft OS 1.0 discovery in WineUSB.
 *
 * It enumerates one synthetic 194f:0422 device with the sealed io24 topology
 * and serves scenario-controlled OS string, compatible-ID, and extended-
 * properties descriptors.  It has no host USB access.
 */

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <libusb.h>

static libusb_device *const fake_device = (libusb_device *)(uintptr_t)0x194f0001;
static libusb_device_handle *const fake_handle = (libusb_device_handle *)(uintptr_t)0x194f0422;
static struct libusb_transfer *pending_transfer;

enum ms_os_scenario
{
    SCENARIO_VALID,
    SCENARIO_NO_STRING,
    SCENARIO_BAD_STRING,
    SCENARIO_MALFORMED_COMPAT,
    SCENARIO_TRUNCATED_COMPAT,
    SCENARIO_OVERSIZE_COMPAT,
    SCENARIO_MALFORMED_PROPERTIES,
    SCENARIO_UNRELATED_PROPERTY,
    SCENARIO_MIXED_IDS,
    SCENARIO_UNKNOWN_INTERFACE,
    SCENARIO_MALFORMED_SECOND_FUNCTION,
};

static enum ms_os_scenario scenario;
static unsigned int request_count, request_mismatch_count;

static const unsigned char ms_os_string[] =
{
    0x12, LIBUSB_DT_STRING,
    'M', 0, 'S', 0, 'F', 0, 'T', 0, '1', 0, '0', 0, '0', 0,
    0xa5, 0,
};

static const char guid5[] = "{11111111-2222-3333-4444-555555555555}";
static const char guid6[] = "{aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee}";

unsigned int io24_fake_libusb_request_count(void) { return request_count; }
unsigned int io24_fake_libusb_request_mismatch_count(void) { return request_mismatch_count; }

static void put_u16(unsigned char *buffer, unsigned int value)
{
    buffer[0] = value;
    buffer[1] = value >> 8;
}

static void put_u32(unsigned char *buffer, uint32_t value)
{
    buffer[0] = value;
    buffer[1] = value >> 8;
    buffer[2] = value >> 16;
    buffer[3] = value >> 24;
}

static size_t put_utf16le(unsigned char *buffer, const char *text)
{
    size_t i, length = strlen(text) + 1;

    for (i = 0; i < length; ++i)
    {
        buffer[2 * i] = text[i];
        buffer[2 * i + 1] = 0;
    }
    return 2 * length;
}

static size_t build_compatible_ids(unsigned char buffer[64])
{
    static const char winusb[8] = {'W', 'I', 'N', 'U', 'S', 'B', 0, 0};
    static const char xusb10[8] = {'X', 'U', 'S', 'B', '1', '0', 0, 0};
    static const char sub_id[8] = {'A', 'B', 'C', 0, 0, 0, 0, 0};

    memset(buffer, 0, 64);
    put_u32(buffer, scenario == SCENARIO_OVERSIZE_COMPAT ? 4097 :
            scenario == SCENARIO_MALFORMED_COMPAT ? 63 : 64);
    put_u16(buffer + 4, 0x0100);
    put_u16(buffer + 6, 0x0004);
    buffer[8] = 2;

    buffer[16] = 5;
    buffer[17] = 1;
    memcpy(buffer + 18, winusb, sizeof(winusb));

    buffer[40] = scenario == SCENARIO_UNKNOWN_INTERFACE ? 200 : 6;
    buffer[41] = 1;
    memcpy(buffer + 42, scenario == SCENARIO_MIXED_IDS ? xusb10 : winusb, 8);
    if (scenario == SCENARIO_MIXED_IDS) memcpy(buffer + 50, sub_id, sizeof(sub_id));
    if (scenario == SCENARIO_MALFORMED_SECOND_FUNCTION) buffer[63] = 1;
    return 64;
}

static size_t append_property(unsigned char *buffer, const char *name,
        uint32_t type, const unsigned char *data, size_t data_length)
{
    size_t name_length = 2 * (strlen(name) + 1);
    size_t section_length = 14 + name_length + data_length;

    put_u32(buffer, section_length);
    put_u32(buffer + 4, type);
    put_u16(buffer + 8, name_length);
    put_utf16le(buffer + 10, name);
    put_u32(buffer + 10 + name_length, data_length);
    memcpy(buffer + 14 + name_length, data, data_length);
    return section_length;
}

static size_t build_properties(unsigned char *buffer, unsigned int interface)
{
    unsigned char guid_data[78], unrelated_data[4] = {1, 0, 0, 0};
    size_t offset = 10, count = 1;
    const char *guid = interface == 5 ? guid5 : guid6;

    memset(buffer, 0, 256);
    if (scenario == SCENARIO_UNRELATED_PROPERTY)
    {
        offset += append_property(buffer + offset, "DeviceIdleEnabled", 4,
                unrelated_data, sizeof(unrelated_data));
        count = 2;
    }

    put_utf16le(guid_data, guid);
    offset += append_property(buffer + offset, "DeviceInterfaceGUID", 1,
            guid_data, sizeof(guid_data));

    put_u32(buffer, offset);
    put_u16(buffer + 4, 0x0100);
    put_u16(buffer + 6, 0x0005);
    put_u16(buffer + 8, count);
    if (scenario == SCENARIO_MALFORMED_PROPERTIES && interface == 5)
        put_u32(buffer + 10, 0xffffffff);
    return offset;
}

static enum ms_os_scenario get_scenario(void)
{
    const char *name = getenv("IO24_MS_OS_SCENARIO");

    if (!name || !strcmp(name, "valid")) return SCENARIO_VALID;
    if (!strcmp(name, "no_string")) return SCENARIO_NO_STRING;
    if (!strcmp(name, "bad_string")) return SCENARIO_BAD_STRING;
    if (!strcmp(name, "malformed_compat")) return SCENARIO_MALFORMED_COMPAT;
    if (!strcmp(name, "truncated_compat")) return SCENARIO_TRUNCATED_COMPAT;
    if (!strcmp(name, "oversize_compat")) return SCENARIO_OVERSIZE_COMPAT;
    if (!strcmp(name, "malformed_properties")) return SCENARIO_MALFORMED_PROPERTIES;
    if (!strcmp(name, "unrelated_property")) return SCENARIO_UNRELATED_PROPERTY;
    if (!strcmp(name, "mixed_ids")) return SCENARIO_MIXED_IDS;
    if (!strcmp(name, "unknown_interface")) return SCENARIO_UNKNOWN_INTERFACE;
    if (!strcmp(name, "malformed_second_function"))
        return SCENARIO_MALFORMED_SECOND_FUNCTION;
    abort();
}

static int return_descriptor(unsigned char *data, uint16_t length,
        const unsigned char *descriptor, size_t descriptor_length)
{
    if (descriptor_length > length) descriptor_length = length;
    if (descriptor_length) memcpy(data, descriptor, descriptor_length);
    return descriptor_length;
}

int LIBUSB_CALL libusb_control_transfer(libusb_device_handle *handle,
        uint8_t request_type, uint8_t request, uint16_t value, uint16_t index,
        unsigned char *data, uint16_t length, unsigned int timeout)
{
    unsigned char descriptor[256];
    size_t descriptor_length;

    ++request_count;
    if (handle != fake_handle || !data || timeout != 1000)
    {
        ++request_mismatch_count;
        return LIBUSB_ERROR_INVALID_PARAM;
    }

    if (request_type == 0x80 && request == LIBUSB_REQUEST_GET_DESCRIPTOR &&
            value == 0x03ee && index == 0 && length == sizeof(ms_os_string))
    {
        if (scenario == SCENARIO_NO_STRING) return LIBUSB_ERROR_PIPE;
        memcpy(descriptor, ms_os_string, sizeof(ms_os_string));
        if (scenario == SCENARIO_BAD_STRING) descriptor[2] = 'N';
        return return_descriptor(data, length, descriptor, sizeof(ms_os_string));
    }

    if (request_type == 0xc0 && request == 0xa5 && value == 0 && index == 4 &&
            (length == 16 || length == 64))
    {
        descriptor_length = build_compatible_ids(descriptor);
        if (scenario == SCENARIO_TRUNCATED_COMPAT && length == 64)
            descriptor_length = 40;
        return return_descriptor(data, length, descriptor, descriptor_length);
    }

    if (request_type == 0xc1 && request == 0xa5 && index == 5 &&
            (value == 0x0500 || value == 0x0600) && length >= 10)
    {
        unsigned int interface = value >> 8;

        if (scenario == SCENARIO_MALFORMED_PROPERTIES && interface == 6)
            return LIBUSB_ERROR_PIPE;
        descriptor_length = build_properties(descriptor, interface);
        if (length != 10 && length != descriptor_length)
        {
            ++request_mismatch_count;
            return LIBUSB_ERROR_INVALID_PARAM;
        }
        return return_descriptor(data, length, descriptor, descriptor_length);
    }

    ++request_mismatch_count;
    return LIBUSB_ERROR_PIPE;
}

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
    scenario = get_scenario();
    request_count = request_mismatch_count = 0;
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
    return "io24 Microsoft OS 1.0 fake libusb";
}
