/* Fake-libusb response for retained contracts whose devices have no OS 1.0 descriptor. */

#include <stdint.h>

#include <libusb.h>

int LIBUSB_CALL libusb_control_transfer(libusb_device_handle *handle,
        uint8_t request_type, uint8_t request, uint16_t value, uint16_t index,
        unsigned char *data, uint16_t length, unsigned int timeout)
{
    (void)handle;
    (void)request_type;
    (void)request;
    (void)value;
    (void)index;
    (void)data;
    (void)length;
    (void)timeout;
    return LIBUSB_ERROR_PIPE;
}
