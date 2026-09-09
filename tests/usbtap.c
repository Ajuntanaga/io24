/* usbtap — record every libusb transfer, with no root and no usbmon.
 *
 * Universal Control's hardware-access module expects WinUSB (PROTOCOL §13v),
 * while this project's own driver reaches libusb through pyusb. CP30 corrected
 * an earlier assumption: Wine's user-mode WinUSB API is not implemented, so
 * this interposer records only traffic that actually reaches libusb. Proving
 * the tap against our own driver does not prove Universal Control's missing
 * discovery, function-driver, or API layers.
 *
 * It writes usbmon text format so tests/usbmon_decode.py reads the output
 * unchanged, whether it came from here or from a real usbmon capture.
 *
 *   gcc -shared -fPIC -o usbtap.so usbtap.c -ldl
 *   IO24_USBLOG=cap.txt LD_PRELOAD=./usbtap.so python3 something.py
 *   python3 tests/usbmon_decode.py cap.txt
 *
 * Only the io24's control traffic is interesting, but filtering by device here
 * would mean tracking handles; it is simpler and more honest to record
 * everything and let the decoder ignore what it cannot parse.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static FILE *lg;
static _Atomic unsigned long seq;
static atomic_flag open_lock = ATOMIC_FLAG_INIT;
static atomic_flag resolver_lock = ATOMIC_FLAG_INIT;
static void *libusb_handle;

typedef void (*io24_libusb_log_callback)(void *, int, const char *);

static void tap_open(void)
{
    while (atomic_flag_test_and_set_explicit(&open_lock, memory_order_acquire))
        ;
    if (!lg) {
        const char *p = getenv("IO24_USBLOG");
        lg = p ? fopen(p, "a") : NULL;
        if (!lg) lg = stderr;
    }
    atomic_flag_clear_explicit(&open_lock, memory_order_release);
}

static unsigned long now_us(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (unsigned long)t.tv_sec * 1000000UL + t.tv_nsec / 1000UL;
}

static unsigned long next_id(void)
{
    return atomic_fetch_add_explicit(&seq, 1, memory_order_relaxed);
}

static long tap_tid(void)
{
    return syscall(SYS_gettid);
}

static void emit_event_marker(const char *event, int with_status, int status)
{
    tap_open();
    flockfile(lg);
    fprintf(lg, "# usbtap pid=%ld tid=%ld event=%s",
            (long)getpid(), tap_tid(), event);
    if (with_status) fprintf(lg, " status=%d", status);
    fputc('\n', lg);
    fflush(lg);
    funlockfile(lg);
}

static void emit_symbol_marker(const char *event, const void *address,
                               const char *requested_symbol)
{
    Dl_info info = {0};
    const char *object = "unknown";
    const char *symbol = requested_symbol;

    if (address && dladdr(address, &info)) {
        if (info.dli_fname) object = info.dli_fname;
        if (info.dli_sname) symbol = info.dli_sname;
    }

    tap_open();
    flockfile(lg);
    fprintf(lg, "# usbtap pid=%ld tid=%ld event=%s object=%s symbol=%s\n",
            (long)getpid(), tap_tid(), event, object, symbol);
    fflush(lg);
    funlockfile(lg);
}

static int valid_libusb_symbol(const void *address, const char *symbol)
{
    Dl_info target = {0};
    Dl_info self = {0};

    return address && dladdr(address, &target) && target.dli_sname &&
           !strcmp(target.dli_sname, symbol) &&
           dladdr((const void *)valid_libusb_symbol, &self) &&
           target.dli_fbase != self.dli_fbase;
}

static void *resolve_libusb_symbol(const char *symbol)
{
    void *address = dlsym(RTLD_NEXT, symbol);

    if (valid_libusb_symbol(address, symbol)) return address;

    while (atomic_flag_test_and_set_explicit(&resolver_lock,
                                             memory_order_acquire))
        ;
    if (!libusb_handle)
        libusb_handle = dlopen("libusb-1.0.so.0",
                               RTLD_NOW | RTLD_LOCAL | RTLD_NOLOAD);
    address = libusb_handle ? dlsym(libusb_handle, symbol) : NULL;
    atomic_flag_clear_explicit(&resolver_lock, memory_order_release);

    return valid_libusb_symbol(address, symbol) ? address : NULL;
}

static void durable_libusb_log(void *context, int level, const char *message)
{
    size_t length = message ? strlen(message) : 0;

    (void)context;
    while (length && (message[length - 1] == '\n' ||
                      message[length - 1] == '\r'))
        length--;

    tap_open();
    flockfile(lg);
    fprintf(lg, "# libusb pid=%ld tid=%ld level=%d ",
            (long)getpid(), tap_tid(), level);
    for (size_t i = 0; i < length; i++) {
        if (message[i] == '\n')
            fputs("\\n", lg);
        else if (message[i] == '\r')
            fputs("\\r", lg);
        else
            fputc((unsigned char)message[i], lg);
    }
    fputc('\n', lg);
    fflush(lg);
    funlockfile(lg);
}

int libusb_init(void **context)
{
    static int (*real_init)(void **);
    static void (*real_set_log_cb)(void *, io24_libusb_log_callback, int);

    if (!real_init) {
        real_init = resolve_libusb_symbol("libusb_init");
        emit_symbol_marker("R-init", (const void *)real_init, "libusb_init");
    }
    if (!real_set_log_cb)
        real_set_log_cb = resolve_libusb_symbol("libusb_set_log_cb");
    if (!real_init || !real_set_log_cb) {
        emit_event_marker("L-global-unavailable", 0, 0);
        return -12;
    }

    real_set_log_cb(NULL, durable_libusb_log, 1);
    emit_event_marker("L-global-installed", 0, 0);
    return real_init(context);
}

/* usbmon text: <urb> <ts> <type> <pipe> <status> <len> = <hex in 4-byte groups> */
static void emit_record(unsigned long id, const char *event, const char *dir,
                        unsigned char ep, int status, int length,
                        const unsigned char *d, int data_length)
{
    tap_open();
    flockfile(lg);
    fprintf(lg, "# usbtap pid=%ld tid=%ld transfer=ffff8800%08lx event=%s\n",
            (long)getpid(), tap_tid(), id, event);
    fprintf(lg, "ffff8800%08lx %lu %s %s:1:004:%02x %d %d",
            id, now_us(), event, dir, ep & 0x7f, status, length);
    if (d && data_length > 0) {
        fputs(" =", lg);
        for (int i = 0; i < data_length; i++) {
            if (i % 4 == 0) fputc(' ', lg);
            fprintf(lg, "%02x", d[i]);
        }
    }
    fputc('\n', lg);
    fflush(lg);
    funlockfile(lg);
}

static void emit(const char *dir, unsigned char ep, const unsigned char *d, int n)
{
    if (n <= 0) return;
    emit_record(next_id(), "S", dir, ep, -115, n, d, n);
}

int libusb_bulk_transfer(void *h, unsigned char ep, unsigned char *data,
                         int length, int *transferred, unsigned int timeout)
{
    static int (*real)(void *, unsigned char, unsigned char *, int, int *,
                       unsigned int);
    if (!real) real = resolve_libusb_symbol("libusb_bulk_transfer");
    if (!real) return -12;
    if (!(ep & 0x80)) emit("Bo", ep, data, length);
    int r = real(h, ep, data, length, transferred, timeout);
    if ((ep & 0x80) && r == 0 && transferred) emit("Bi", ep, data, *transferred);
    return r;
}

int libusb_interrupt_transfer(void *h, unsigned char ep, unsigned char *data,
                              int length, int *transferred, unsigned int timeout)
{
    static int (*real)(void *, unsigned char, unsigned char *, int, int *,
                       unsigned int);
    if (!real) real = resolve_libusb_symbol("libusb_interrupt_transfer");
    if (!real) return -12;
    if (!(ep & 0x80)) emit("Io", ep, data, length);
    int r = real(h, ep, data, length, transferred, timeout);
    if ((ep & 0x80) && r == 0 && transferred) emit("Ii", ep, data, *transferred);
    return r;
}

int libusb_control_transfer(void *h, unsigned char rt, unsigned char req,
                            unsigned short val, unsigned short idx,
                            unsigned char *data, unsigned short len,
                            unsigned int timeout)
{
    static int (*real)(void *, unsigned char, unsigned char, unsigned short,
                       unsigned short, unsigned char *, unsigned short,
                       unsigned int);
    if (!real) real = resolve_libusb_symbol("libusb_control_transfer");
    if (!real) return -12;
    if (!(rt & 0x80) && len) emit("Co", 0, data, len);
    int r = real(h, rt, req, val, idx, data, len, timeout);
    if ((rt & 0x80) && r > 0) emit("Ci", 0, data, r);
    return r;
}

/* Wine's wineusb.sys uses the ASYNC path, so the sync wrappers above are not
 * enough on their own — submit_transfer is where its bulk writes actually go. */
struct lu_transfer;
typedef void (*lu_transfer_callback)(struct lu_transfer *);

struct lu_transfer {          /* prefix of struct libusb_transfer, ABI-stable */
    void *dev_handle;
    unsigned char flags;
    unsigned char endpoint;
    unsigned char type;
    unsigned int timeout;
    int status;
    int length;
    int actual_length;
    lu_transfer_callback callback;
    void *user_data;
    unsigned char *buffer;
};

struct async_control_context {
    unsigned long id;
    int direction_in;
    lu_transfer_callback callback;
    void *user_data;
};

static void async_control_complete(struct lu_transfer *t)
{
    struct async_control_context *ctx = t->user_data;
    lu_transfer_callback callback = ctx->callback;
    void *user_data = ctx->user_data;
    const unsigned char *data = NULL;
    int data_length = 0;

    t->callback = callback;
    t->user_data = user_data;

    if (ctx->direction_in && t->buffer && t->actual_length > 0 &&
        t->length > 8) {
        data_length = t->actual_length;
        if (data_length > t->length - 8) data_length = t->length - 8;
        data = t->buffer + 8;
    }
    emit_record(ctx->id, "C", ctx->direction_in ? "Ci" : "Co", 0,
                t->status, t->actual_length, data, data_length);
    free(ctx);

    if (callback) callback(t);
}

int libusb_submit_transfer(struct lu_transfer *t)
{
    static int (*real)(struct lu_transfer *);
    struct async_control_context *ctx;
    int status;

    if (!real) {
        real = resolve_libusb_symbol("libusb_submit_transfer");
        emit_symbol_marker("R-submit", (const void *)real,
                           "libusb_submit_transfer");
    }
    if (!real) return -12;
    if (!t || !t->buffer || t->type != 0 || t->length < 8) {
        if (t && t->buffer && !(t->endpoint & 0x80))
            emit("Bo", t->endpoint, t->buffer, t->length);
        return real(t);
    }

    ctx = malloc(sizeof(*ctx));
    if (!ctx) return real(t);
    ctx->id = next_id();
    ctx->direction_in = !!(t->buffer[0] & 0x80);
    ctx->callback = t->callback;
    ctx->user_data = t->user_data;

    emit_record(ctx->id, "S", ctx->direction_in ? "Ci" : "Co", 0,
                -115, ctx->direction_in ? 8 : t->length, t->buffer,
                ctx->direction_in ? 8 : t->length);
    t->callback = async_control_complete;
    t->user_data = ctx;
    status = real(t);
    if (status != 0) {
        t->callback = ctx->callback;
        t->user_data = ctx->user_data;
        emit_record(ctx->id, "E", ctx->direction_in ? "Ci" : "Co", 0,
                    status, 0, NULL, 0);
        free(ctx);
    }
    return status;
}

/* Wine's wineusb event thread calls this exact entry point. The paired
 * markers show whether that thread entered the event pump and whether it ever
 * returned; a lone H-enter alongside accepted submissions distinguishes a
 * blocked pump from an immediate submission error or observed callback. */
int libusb_handle_events(void *context)
{
    static int (*real)(void *);
    int status;

    if (!real) real = resolve_libusb_symbol("libusb_handle_events");
    if (!real) return -12;
    emit_event_marker("H-enter", 0, 0);
    status = real(context);
    emit_event_marker("H-return", 1, status);
    return status;
}
