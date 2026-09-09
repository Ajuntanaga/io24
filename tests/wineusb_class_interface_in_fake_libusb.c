/*
 * Device-free libusb fixture for the WineUSB class-interface-IN contract.
 *
 * This library deliberately uses libusb's real ABI and SONAME while exposing
 * no device enumeration or host USB access.  The contract controls submission
 * and completion explicitly.
 */

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <libusb.h>

static struct libusb_transfer *pending_transfer;
static int submit_result;
static unsigned int alloc_count;
static unsigned int free_count;
static unsigned int buffer_free_count;
static unsigned int submit_count;
static unsigned int cancel_count;

void io24_fake_libusb_reset(void)
{
    if (pending_transfer) abort();
    submit_result = 0;
    alloc_count = 0;
    free_count = 0;
    buffer_free_count = 0;
    submit_count = 0;
    cancel_count = 0;
}

void io24_fake_libusb_set_submit_result(int result)
{
    submit_result = result;
}

unsigned int io24_fake_libusb_alloc_count(void) { return alloc_count; }
unsigned int io24_fake_libusb_free_count(void) { return free_count; }
unsigned int io24_fake_libusb_buffer_free_count(void) { return buffer_free_count; }
unsigned int io24_fake_libusb_submit_count(void) { return submit_count; }
unsigned int io24_fake_libusb_cancel_count(void) { return cancel_count; }

int io24_fake_libusb_has_pending(void)
{
    return pending_transfer != NULL;
}

int io24_fake_libusb_pending_flags(void)
{
    return pending_transfer ? pending_transfer->flags : -1;
}

int io24_fake_libusb_pending_length(void)
{
    return pending_transfer ? pending_transfer->length : -1;
}

int io24_fake_libusb_get_setup(unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE])
{
    if (!pending_transfer || !pending_transfer->buffer) return -1;
    memcpy(setup, pending_transfer->buffer, LIBUSB_CONTROL_SETUP_SIZE);
    return 0;
}

int io24_fake_libusb_complete(enum libusb_transfer_status status,
        const unsigned char *data, size_t data_length, int actual_length)
{
    struct libusb_transfer *transfer = pending_transfer;
    size_t requested_length;

    if (!transfer) return -1;
    pending_transfer = NULL;

    requested_length = transfer->length > (int)LIBUSB_CONTROL_SETUP_SIZE
            ? (size_t)transfer->length - LIBUSB_CONTROL_SETUP_SIZE : 0;
    if (data && data_length)
    {
        if (data_length > requested_length) data_length = requested_length;
        memcpy(libusb_control_transfer_get_data(transfer), data, data_length);
    }

    transfer->status = status;
    transfer->actual_length = actual_length;
    transfer->callback(transfer);

    if (transfer->flags & LIBUSB_TRANSFER_FREE_TRANSFER)
        libusb_free_transfer(transfer);
    return 0;
}

struct libusb_transfer * LIBUSB_CALL libusb_alloc_transfer(int iso_packets)
{
    struct libusb_transfer *transfer;
    size_t size;

    if (iso_packets < 0) return NULL;
    size = sizeof(*transfer) + (size_t)iso_packets * sizeof(struct libusb_iso_packet_descriptor);
    transfer = calloc(1, size);
    if (transfer) ++alloc_count;
    return transfer;
}

void LIBUSB_CALL libusb_free_transfer(struct libusb_transfer *transfer)
{
    if (!transfer) return;
    if (transfer->flags & LIBUSB_TRANSFER_FREE_BUFFER)
    {
        free(transfer->buffer);
        ++buffer_free_count;
    }
    free(transfer);
    ++free_count;
}

int LIBUSB_CALL libusb_submit_transfer(struct libusb_transfer *transfer)
{
    ++submit_count;
    if (submit_result < 0) return submit_result;
    if (pending_transfer) return LIBUSB_ERROR_BUSY;
    pending_transfer = transfer;
    return 0;
}

int LIBUSB_CALL libusb_cancel_transfer(struct libusb_transfer *transfer)
{
    ++cancel_count;
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
    (void)flags;
    (void)vendor_id;
    (void)product_id;
    (void)dev_class;
    (void)callback;
    (void)user_data;
    if (callback_handle) *callback_handle = 1;
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
    (void)device;
    if (handle) *handle = NULL;
    return LIBUSB_ERROR_NO_DEVICE;
}

void LIBUSB_CALL libusb_close(libusb_device_handle *handle) { (void)handle; }
libusb_device * LIBUSB_CALL libusb_get_device(libusb_device_handle *handle)
{
    (void)handle;
    return NULL;
}

uint8_t LIBUSB_CALL libusb_get_bus_number(libusb_device *device) { (void)device; return 0; }
uint8_t LIBUSB_CALL libusb_get_port_number(libusb_device *device) { (void)device; return 0; }
int LIBUSB_CALL libusb_get_device_speed(libusb_device *device)
{
    (void)device;
    return LIBUSB_SPEED_UNKNOWN;
}

int LIBUSB_CALL libusb_get_device_descriptor(libusb_device *device,
        struct libusb_device_descriptor *descriptor)
{
    (void)device;
    if (descriptor) memset(descriptor, 0, sizeof(*descriptor));
    return LIBUSB_ERROR_NO_DEVICE;
}

int LIBUSB_CALL libusb_get_active_config_descriptor(libusb_device *device,
        struct libusb_config_descriptor **config)
{
    (void)device;
    if (config) *config = NULL;
    return LIBUSB_ERROR_NO_DEVICE;
}

int LIBUSB_CALL libusb_get_active_interface_association_descriptors(libusb_device *device,
        struct libusb_interface_association_descriptor_array **array)
{
    (void)device;
    if (array) *array = NULL;
    return LIBUSB_ERROR_NOT_FOUND;
}

void LIBUSB_CALL libusb_free_interface_association_descriptors(
        struct libusb_interface_association_descriptor_array *array)
{
    (void)array;
}

void LIBUSB_CALL libusb_free_config_descriptor(struct libusb_config_descriptor *config)
{
    (void)config;
}

const char * LIBUSB_CALL libusb_strerror(int error_code)
{
    (void)error_code;
    return "io24 fake libusb";
}
