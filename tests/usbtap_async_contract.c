#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct io24_libusb_transfer;
typedef void (*io24_libusb_callback)(struct io24_libusb_transfer *);

/* ABI-stable prefix of struct libusb_transfer. */
struct io24_libusb_transfer {
    void *dev_handle;
    unsigned char flags;
    unsigned char endpoint;
    unsigned char type;
    unsigned int timeout;
    int status;
    int length;
    int actual_length;
    io24_libusb_callback callback;
    void *user_data;
    unsigned char *buffer;
};

#ifdef IO24_FAKE_LIBUSB

int libusb_handle_events(void *context)
{
    const char *mode = getenv("IO24_FAKE_LIBUSB_MODE");

    (void)context;
    if (mode && !strcmp(mode, "event-block"))
        for (;;) pause();
    return 0;
}

int libusb_submit_transfer(struct io24_libusb_transfer *transfer)
{
    static const unsigned char response[] = {0x12, 0x01, 0x00, 0x03};
    const char *mode = getenv("IO24_FAKE_LIBUSB_MODE");

    if (!transfer || !transfer->callback || !transfer->buffer ||
        transfer->length < 8 + (int)sizeof(response))
        return -2;

    if (mode && !strcmp(mode, "submit-error"))
        return -6; /* LIBUSB_ERROR_BUSY */
    if (mode && !strcmp(mode, "stall")) {
        transfer->status = 4; /* LIBUSB_TRANSFER_STALL */
        transfer->actual_length = 0;
        transfer->callback(transfer);
        return 0;
    }

    memcpy(transfer->buffer + 8, response, sizeof(response));
    transfer->status = 0; /* LIBUSB_TRANSFER_COMPLETED */
    transfer->actual_length = sizeof(response);
    transfer->callback(transfer);
    return 0;
}

#else

int libusb_submit_transfer(struct io24_libusb_transfer *transfer);
int libusb_handle_events(void *context);

static int callback_count;
static void *expected_user_data;

static void original_callback(struct io24_libusb_transfer *transfer)
{
    if (transfer->user_data != expected_user_data) {
        fprintf(stderr, "FAIL: original callback received replaced user_data\n");
        exit(1);
    }
    callback_count++;
}

int main(int argc, char **argv)
{
    unsigned char buffer[] = {
        0x80, 0x06, 0x00, 0x01, 0x00, 0x00, 0x04, 0x00,
        0xde, 0xad, 0xbe, 0xef,
    };
    int callback_token = 0x24;
    struct io24_libusb_transfer transfer = {
        .endpoint = 0,
        .type = 0, /* LIBUSB_TRANSFER_TYPE_CONTROL */
        .length = sizeof(buffer),
        .callback = original_callback,
        .user_data = &callback_token,
        .buffer = buffer,
    };
    const char *mode = argc > 1 ? argv[1] : "completed";
    int expected_status = !strcmp(mode, "submit-error") ? -6 : 0;
    int expected_callbacks = !strcmp(mode, "submit-error") ? 0 : 1;
    int status;

    expected_user_data = &callback_token;
    status = libusb_submit_transfer(&transfer);
    if (status != expected_status) {
        fprintf(stderr, "FAIL: fake libusb returned %d, expected %d\n",
                status, expected_status);
        return 1;
    }
    if (callback_count != expected_callbacks) {
        fprintf(stderr, "FAIL: original callback count is %d, expected %d\n",
                callback_count, expected_callbacks);
        return 1;
    }
    if (transfer.callback != original_callback ||
        transfer.user_data != &callback_token) {
        fprintf(stderr, "FAIL: interposer did not restore callback state\n");
        return 1;
    }
    status = libusb_handle_events(NULL);
    if (status != 0) {
        fprintf(stderr, "FAIL: fake event handler returned %d\n", status);
        return 1;
    }

    printf("callback contract (%s): pass\n", mode);
    return 0;
}

#endif
