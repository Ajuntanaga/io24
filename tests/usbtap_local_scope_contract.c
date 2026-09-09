#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

#ifdef IO24_LOCAL_SCOPE_CLIENT

struct io24_libusb_transfer;
typedef void (*io24_libusb_callback)(struct io24_libusb_transfer *);

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

int libusb_init(void **context);
int libusb_submit_transfer(struct io24_libusb_transfer *transfer);
int libusb_handle_events(void *context);

static int callback_count;

static void local_scope_callback(struct io24_libusb_transfer *transfer)
{
    if (transfer->status == 0 && transfer->actual_length == 4)
        callback_count++;
}

int io24_local_scope_probe(void)
{
    unsigned char buffer[] = {
        0x80, 0x06, 0x00, 0x01, 0x00, 0x00, 0x04, 0x00,
        0xde, 0xad, 0xbe, 0xef,
    };
    void *context = NULL;
    struct io24_libusb_transfer transfer = {
        .dev_handle = &context,
        .endpoint = 0,
        .type = 0,
        .length = sizeof(buffer),
        .callback = local_scope_callback,
        .buffer = buffer,
    };
    int status = libusb_init(&context);

    if (status != 0) return status;
    if (!context) return -2;
    if ((status = libusb_submit_transfer(&transfer)) != 0) return status;
    if (callback_count != 1) return -3;
    return libusb_handle_events(context);
}

#else

typedef int (*io24_local_scope_probe)(void);

int main(int argc, char **argv)
{
    io24_local_scope_probe probe;
    void *client;
    int status;

    if (argc != 2) {
        fputs("FAIL: local-scope contract requires one client library\n",
              stderr);
        return 2;
    }
    if (!(client = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL))) {
        fprintf(stderr, "FAIL: cannot load local client: %s\n", dlerror());
        return 2;
    }
    if (!(probe = (io24_local_scope_probe)dlsym(
              client, "io24_local_scope_probe"))) {
        fprintf(stderr, "FAIL: cannot resolve local probe: %s\n", dlerror());
        dlclose(client);
        return 2;
    }

    status = probe();
    dlclose(client);
    if (status != 0) {
        fprintf(stderr,
                "FAIL: local-scope libusb initialization returned %d\n",
                status);
        return 1;
    }

    puts("usbtap local-scope resolution contract: pass");
    return 0;
}

#endif
