#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct io24_libusb_transfer;
typedef void (*io24_libusb_callback)(struct io24_libusb_transfer *);
typedef void (*io24_libusb_log_callback)(void *, int, const char *);

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

#ifdef IO24_FAKE_LIBUSB_LOG

static io24_libusb_log_callback global_log_callback;

void libusb_set_log_cb(void *context, io24_libusb_log_callback callback,
                       int mode)
{
    (void)context;
    if (mode & 1) global_log_callback = callback;
}

static void fake_log(const char *message)
{
    if (global_log_callback)
        global_log_callback(NULL, 4, message);
    else
        fputs(message, stderr);
}

int libusb_init(void **context)
{
    static int fake_context;

    if (context) *context = &fake_context;
    fake_log("[fake] libusb init\n");
    return 0;
}

int libusb_submit_transfer(struct io24_libusb_transfer *transfer)
{
    static const unsigned char response[] = {0x12, 0x01, 0x00, 0x03};

    fake_log("[fake] libusb submit\n");
    if (!transfer || !transfer->callback || !transfer->buffer ||
        transfer->length < 8 + (int)sizeof(response))
        return -2;
    memcpy(transfer->buffer + 8, response, sizeof(response));
    transfer->status = 0;
    transfer->actual_length = sizeof(response);
    transfer->callback(transfer);
    return 0;
}

int libusb_handle_events(void *context)
{
    (void)context;
    fake_log("[fake] libusb events\n");
    return 0;
}

#else

int libusb_init(void **context);
int libusb_submit_transfer(struct io24_libusb_transfer *transfer);
int libusb_handle_events(void *context);

static int callback_count;
static void *expected_user_data;

static void original_callback(struct io24_libusb_transfer *transfer)
{
    if (transfer->user_data != expected_user_data) {
        fputs("FAIL: durable log probe received replaced user_data\n", stderr);
        exit(1);
    }
    callback_count++;
}

int main(void)
{
    unsigned char buffer[] = {
        0x80, 0x06, 0x00, 0x01, 0x00, 0x00, 0x04, 0x00,
        0xde, 0xad, 0xbe, 0xef,
    };
    int callback_token = 0x24;
    void *context = NULL;
    struct io24_libusb_transfer transfer = {
        .dev_handle = &context,
        .endpoint = 0,
        .type = 0,
        .length = sizeof(buffer),
        .callback = original_callback,
        .user_data = &callback_token,
        .buffer = buffer,
    };

    expected_user_data = &callback_token;
    if (libusb_init(&context) != 0 || !context) {
        fputs("FAIL: fake libusb initialization failed\n", stderr);
        return 1;
    }
    if (libusb_submit_transfer(&transfer) != 0 || callback_count != 1) {
        fputs("FAIL: fake libusb submission failed\n", stderr);
        return 1;
    }
    if (transfer.callback != original_callback ||
        transfer.user_data != &callback_token) {
        fputs("FAIL: durable logging changed callback state\n", stderr);
        return 1;
    }
    if (libusb_handle_events(context) != 0) {
        fputs("FAIL: fake libusb event handler failed\n", stderr);
        return 1;
    }

    puts("durable libusb log probe: pass");
    return 0;
}

#endif
