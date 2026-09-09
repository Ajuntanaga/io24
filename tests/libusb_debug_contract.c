#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>

struct libusb_context;

int main(void)
{
    void *library;
    struct libusb_context *context = NULL;
    int (*init)(struct libusb_context **);
    void (*exit_libusb)(struct libusb_context *);
    int status;

    if (!access("/dev/bus/usb", F_OK) ||
        !access("/sys/bus/usb/devices", F_OK) ||
        !access("/run/udev", F_OK)) {
        fputs("FAIL: hardware or udev path is visible in debug contract\n",
              stderr);
        return 1;
    }

    if (!(library = dlopen("libusb-1.0.so.0", RTLD_NOW | RTLD_LOCAL))) {
        fprintf(stderr, "FAIL: cannot load libusb: %s\n", dlerror());
        return 1;
    }
    if (!(init = dlsym(RTLD_DEFAULT, "libusb_init")) ||
        !(exit_libusb = dlsym(library, "libusb_exit"))) {
        fprintf(stderr, "FAIL: cannot resolve libusb lifecycle: %s\n",
                dlerror());
        dlclose(library);
        return 1;
    }

    if ((status = init(&context))) {
        fprintf(stderr, "FAIL: isolated libusb_init returned %d\n", status);
        dlclose(library);
        return 1;
    }
    exit_libusb(context);
    dlclose(library);

    puts("isolated libusb debug lifecycle: pass");
    return 0;
}
