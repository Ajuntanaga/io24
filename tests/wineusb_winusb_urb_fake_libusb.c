/* Resettable, queryable, hardware-free libusb ABI boundary. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <libusb.h>

#ifdef IO24_PIPE_TABLE_ALLOC_AUDIT
#include <dlfcn.h>
#endif

struct io24_fake_counts { unsigned claim, release, detach, auto_detach, set_configuration, set_alternate, control, bulk, interrupt, cancel, clear_halt, transfer_free, control_buffer_alloc, control_buffer_free, control_free_buffer_flag, close, api_calls, get_device, get_active_config_descriptor, free_config_descriptor; };
struct io24_fake_record { int interface_number,alternate,configuration; unsigned char endpoint,type; int length; uint8_t request_type,request; uint16_t value,index; unsigned int timeout; size_t payload_length; uint8_t payload[4096]; unsigned get_device_ordinal,get_active_config_descriptor_ordinal,free_config_descriptor_ordinal; uintptr_t get_device_handle,get_device_result,get_active_config_descriptor_device,get_active_config_descriptor_result,free_config_descriptor_input; };
static struct io24_fake_counts counts;
#define IO24_FAKE_API_CALL() (++counts.api_calls)
static struct io24_fake_record record;
static struct libusb_config_descriptor config_view;
static struct libusb_interface config_interface_views[8];
static struct libusb_interface_descriptor config_alt_views[16];
static struct libusb_endpoint_descriptor config_endpoint_views[32];
static int claim_journal[256], release_journal[256];
static int active_descriptor_enabled;
static int interrupt_descriptor_enabled;
static int extended_descriptor_enabled;
static struct libusb_transfer *pending;
static int submit_result,clear_halt_result,claim_result,alternate_result,control_result;
static int reported_actual_length;
static unsigned int claim_failure_call, alloc_failure_call;
static unsigned int alloc_count, alloc_attempts, submit_attempts;
#ifdef IO24_PIPE_TABLE_ALLOC_AUDIT
/* This is deliberately an ABI-shaped copy of unixlib.c's private allocation,
 * used only to identify its calloc(1, sizeof(table)) calls under LD_PRELOAD. */
struct io24_pipe_table_audit_token
{
    uint32_t generation;
    uint8_t endpoint, type, interface_number, alternate, current;
};
struct io24_pipe_table_audit_table
{
    struct io24_pipe_table_audit_token records[256];
    uint8_t alternates[256];
    uint32_t next_generation;
};
struct io24_pipe_table_audit_entry
{
    void *pointer;
    uint64_t identity;
    unsigned int order;
    int live;
};
static struct io24_pipe_table_audit_entry pipe_table_entries[8];
static void *(*pipe_table_real_calloc)(size_t, size_t);
static void (*pipe_table_real_free)(void *);
static unsigned int pipe_table_allocations, pipe_table_frees, pipe_table_order;
static unsigned int pipe_table_last_free_order, pipe_table_close_order, pipe_table_failures;
static uint64_t pipe_table_next_identity;
static void *pipe_table_forced_reuse;
static __thread int pipe_table_resolving;

static void pipe_table_resolve_allocator(void)
{
    if (pipe_table_real_calloc && pipe_table_real_free) return;
    if (pipe_table_resolving) return;
    pipe_table_resolving = 1;
    if (!pipe_table_real_calloc) pipe_table_real_calloc = dlsym(RTLD_NEXT, "calloc");
    if (!pipe_table_real_free) pipe_table_real_free = dlsym(RTLD_NEXT, "free");
    pipe_table_resolving = 0;
}

__attribute__((constructor)) static void pipe_table_allocator_init(void)
{
    pipe_table_resolve_allocator();
}

void *calloc(size_t count, size_t size)
{
    void *pointer;
    unsigned int i;
    uint64_t identity;

    pipe_table_resolve_allocator();
    if (!pipe_table_real_calloc) return NULL;
    if (count == 1 && size == sizeof(struct io24_pipe_table_audit_table) &&
            pipe_table_forced_reuse)
    {
        pointer = pipe_table_forced_reuse;
        pipe_table_forced_reuse = NULL;
        memset(pointer, 0, size);
    }
    else pointer = pipe_table_real_calloc(count, size);
    if (count != 1 || size != sizeof(struct io24_pipe_table_audit_table)) return pointer;
    if (pipe_table_next_identity == UINT64_MAX)
    {
        ++pipe_table_failures;
        if (pipe_table_real_free) pipe_table_real_free(pointer);
        return NULL;
    }
    identity = ++pipe_table_next_identity;
    ++pipe_table_order;
    for (i = 0; i < sizeof(pipe_table_entries) / sizeof(pipe_table_entries[0]); ++i)
        if (!pipe_table_entries[i].live && pipe_table_entries[i].pointer == pointer)
        {
            pipe_table_entries[i] = (struct io24_pipe_table_audit_entry){
                    pointer, identity, pipe_table_order, 1};
            ++pipe_table_allocations;
            return pointer;
        }
    for (i = 0; i < sizeof(pipe_table_entries) / sizeof(pipe_table_entries[0]); ++i)
        if (!pipe_table_entries[i].live)
        {
            pipe_table_entries[i] = (struct io24_pipe_table_audit_entry){
                    pointer, identity, pipe_table_order, 1};
            ++pipe_table_allocations;
            return pointer;
        }
    ++pipe_table_failures;
    return pointer;
}

void free(void *pointer)
{
    unsigned int i;
    int released_pipe_table = 0;

    pipe_table_resolve_allocator();
    for (i = 0; pointer && i < sizeof(pipe_table_entries) / sizeof(pipe_table_entries[0]); ++i)
        if (pipe_table_entries[i].pointer == pointer)
        {
            ++pipe_table_order;
            if (!pipe_table_entries[i].live) ++pipe_table_failures;
            else
            {
                pipe_table_entries[i].live = 0;
                ++pipe_table_frees;
                pipe_table_last_free_order = pipe_table_order;
                released_pipe_table = 1;
            }
            break;
        }
    if (released_pipe_table && getenv("IO24_PIPE_TABLE_FORCE_SAME_ADDRESS"))
    {
        if (pipe_table_forced_reuse && pipe_table_real_free)
            pipe_table_real_free(pipe_table_forced_reuse);
        pipe_table_forced_reuse = pointer;
        return;
    }
    if (pipe_table_real_free) pipe_table_real_free(pointer);
}

void io24_pipe_table_audit_reset(void)
{
    if (pipe_table_forced_reuse && pipe_table_real_free)
        pipe_table_real_free(pipe_table_forced_reuse);
    pipe_table_forced_reuse = NULL;
    memset(pipe_table_entries, 0, sizeof(pipe_table_entries));
    pipe_table_allocations = pipe_table_frees = pipe_table_order = 0;
    pipe_table_last_free_order = pipe_table_close_order = pipe_table_failures = 0;
}
unsigned int io24_pipe_table_audit_allocations(void) { return pipe_table_allocations; }
unsigned int io24_pipe_table_audit_frees(void) { return pipe_table_frees; }
unsigned int io24_pipe_table_audit_live(void)
{
    unsigned int i, live = 0;
    for (i = 0; i < sizeof(pipe_table_entries) / sizeof(pipe_table_entries[0]); ++i)
        live += pipe_table_entries[i].live;
    return live;
}
unsigned int io24_pipe_table_audit_last_free_order(void) { return pipe_table_last_free_order; }
unsigned int io24_pipe_table_audit_close_order(void) { return pipe_table_close_order; }
unsigned int io24_pipe_table_audit_failures(void) { return pipe_table_failures; }
int io24_pipe_table_audit_pointer_live(const void *pointer)
{
    unsigned int i;

    for (i = 0; i < sizeof(pipe_table_entries) / sizeof(pipe_table_entries[0]); ++i)
        if (pipe_table_entries[i].pointer == pointer) return pipe_table_entries[i].live;
    return -1;
}
int io24_pipe_table_audit_capture_live(const void *pointer, uint64_t *identity)
{
    unsigned int i;

    if (!identity) return -1;
    *identity = 0;
    for (i = 0; i < sizeof(pipe_table_entries) / sizeof(pipe_table_entries[0]); ++i)
        if (pipe_table_entries[i].pointer == pointer)
        {
            if (!pipe_table_entries[i].live) return 0;
            if (!pipe_table_entries[i].identity) return -1;
            *identity = pipe_table_entries[i].identity;
            return 1;
        }
    return -1;
}
static void io24_pipe_table_audit_note_close(void)
{
    ++pipe_table_order;
    pipe_table_close_order = pipe_table_order;
    if (io24_pipe_table_audit_live()) ++pipe_table_failures;
}
#endif
static const unsigned char mi05[]={9,2,41,0,1,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,1,2,0xff,0,0,6,7,5,0x81,2,0,2,0,7,5,0x01,2,0,2,0};
/* The lower contract must validate a real active descriptor, rather than
 * accepting caller-supplied endpoint metadata.  This is deliberately static:
 * libusb descriptors are read-only for the duration of each fake call. */
static const struct libusb_endpoint_descriptor mi05_alt1_endpoints[] = {
    { .bLength = 7, .bDescriptorType = LIBUSB_DT_ENDPOINT, .bEndpointAddress = 0x81,
      .bmAttributes = LIBUSB_TRANSFER_TYPE_BULK, .wMaxPacketSize = 512 },
    { .bLength = 7, .bDescriptorType = LIBUSB_DT_ENDPOINT, .bEndpointAddress = 0x01,
      .bmAttributes = LIBUSB_TRANSFER_TYPE_BULK, .wMaxPacketSize = 512 },
};
static const struct libusb_interface_descriptor mi05_alts[] = {
    { .bLength = 9, .bDescriptorType = LIBUSB_DT_INTERFACE, .bInterfaceNumber = 5,
      .bAlternateSetting = 0, .bNumEndpoints = 0, .bInterfaceClass = 0xff,
      .bInterfaceSubClass = 0, .bInterfaceProtocol = 6 },
    { .bLength = 9, .bDescriptorType = LIBUSB_DT_INTERFACE, .bInterfaceNumber = 5,
      .bAlternateSetting = 1, .bNumEndpoints = 2, .bInterfaceClass = 0xff,
      .bInterfaceSubClass = 0, .bInterfaceProtocol = 6,
      .endpoint = mi05_alt1_endpoints },
};
static const struct libusb_interface_descriptor empty_alt2 = {
    .bLength = 9, .bDescriptorType = LIBUSB_DT_INTERFACE, .bInterfaceNumber = 2,
};
static const struct libusb_endpoint_descriptor endpoint7[] = {
    { .bLength = 7, .bDescriptorType = LIBUSB_DT_ENDPOINT, .bEndpointAddress = 0x82,
      .bmAttributes = LIBUSB_TRANSFER_TYPE_BULK, .wMaxPacketSize = 512 },
};
static const struct libusb_interface_descriptor alt7 = {
    .bLength = 9, .bDescriptorType = LIBUSB_DT_INTERFACE, .bInterfaceNumber = 7,
    .bNumEndpoints = 1, .endpoint = endpoint7,
};
static const struct libusb_interface_descriptor empty_alt7 = {
    .bLength = 9, .bDescriptorType = LIBUSB_DT_INTERFACE, .bInterfaceNumber = 7,
};
static const struct libusb_interface scope_interfaces[] = {
    { .altsetting = &empty_alt2, .num_altsetting = 1 },
    { .altsetting = mi05_alts, .num_altsetting = 2 },
    { .altsetting = &alt7, .num_altsetting = 1 },
};
static const struct libusb_interface base_scope_interfaces[] = {
    { .altsetting = &empty_alt2, .num_altsetting = 1 },
    { .altsetting = mi05_alts, .num_altsetting = 2 },
    { .altsetting = &empty_alt7, .num_altsetting = 1 },
};
static const struct libusb_config_descriptor mi05_config = {
    .bLength = 9, .bDescriptorType = LIBUSB_DT_CONFIG, .wTotalLength = sizeof(mi05),
    .bNumInterfaces = 3, .bConfigurationValue = 1, .interface = base_scope_interfaces,
};
static const struct libusb_config_descriptor extended_mi05_config = {
    .bLength = 9, .bDescriptorType = LIBUSB_DT_CONFIG, .wTotalLength = sizeof(mi05),
    .bNumInterfaces = 3, .bConfigurationValue = 1, .interface = scope_interfaces,
};
static const struct libusb_endpoint_descriptor interrupt_endpoints[] = {
    { .bLength = 7, .bDescriptorType = LIBUSB_DT_ENDPOINT, .bEndpointAddress = 0x83,
      .bmAttributes = LIBUSB_TRANSFER_TYPE_INTERRUPT, .wMaxPacketSize = 64, .bInterval = 1 },
};
static const struct libusb_interface_descriptor interrupt_alts[] = {
    { .bLength = 9, .bDescriptorType = LIBUSB_DT_INTERFACE, .bInterfaceNumber = 5,
      .bAlternateSetting = 1, .bNumEndpoints = 1, .bInterfaceClass = 0xff,
      .bInterfaceProtocol = 6, .endpoint = interrupt_endpoints },
};
static const struct libusb_interface interrupt_interfaces[] = {{ .altsetting = interrupt_alts, .num_altsetting = 1 }};
static const struct libusb_config_descriptor interrupt_config = {
    .bLength = 9, .bDescriptorType = LIBUSB_DT_CONFIG, .bNumInterfaces = 1, .interface = interrupt_interfaces,
};

static int copy_config_view(const struct libusb_config_descriptor *source)
{
    size_t interface_count, alt_count = 0, endpoint_count = 0;
    unsigned int i, j;

    if (!source) return LIBUSB_ERROR_INVALID_PARAM;
    interface_count = source->bNumInterfaces;
    if (interface_count > sizeof(config_interface_views) / sizeof(config_interface_views[0]))
        return LIBUSB_ERROR_OVERFLOW;
    if (interface_count && !source->interface) return LIBUSB_ERROR_INVALID_PARAM;

    memset(config_interface_views, 0, sizeof(config_interface_views));
    memset(config_alt_views, 0, sizeof(config_alt_views));
    memset(config_endpoint_views, 0, sizeof(config_endpoint_views));
    config_view = *source;
    config_view.interface = interface_count ? config_interface_views : NULL;

    for (i = 0; i < interface_count; ++i)
    {
        const struct libusb_interface *source_interface = &source->interface[i];
        size_t source_alt_count;

        if (source_interface->num_altsetting < 0) return LIBUSB_ERROR_INVALID_PARAM;
        source_alt_count = source_interface->num_altsetting;
        if (source_alt_count > sizeof(config_alt_views) / sizeof(config_alt_views[0]) - alt_count)
            return LIBUSB_ERROR_OVERFLOW;
        if (source_alt_count && !source_interface->altsetting) return LIBUSB_ERROR_INVALID_PARAM;

        config_interface_views[i] = *source_interface;
        config_interface_views[i].altsetting = source_alt_count ? &config_alt_views[alt_count] : NULL;
        for (j = 0; j < source_alt_count; ++j)
        {
            const struct libusb_interface_descriptor *source_alt = &source_interface->altsetting[j];
            size_t source_endpoint_count = source_alt->bNumEndpoints;

            if (source_endpoint_count > sizeof(config_endpoint_views) / sizeof(config_endpoint_views[0]) - endpoint_count)
                return LIBUSB_ERROR_OVERFLOW;
            if (source_endpoint_count && !source_alt->endpoint) return LIBUSB_ERROR_INVALID_PARAM;
            config_alt_views[alt_count + j] = *source_alt;
            config_alt_views[alt_count + j].endpoint = source_endpoint_count ?
                    &config_endpoint_views[endpoint_count] : NULL;
            if (source_endpoint_count)
                memcpy(&config_endpoint_views[endpoint_count], source_alt->endpoint,
                        source_endpoint_count * sizeof(config_endpoint_views[0]));
            endpoint_count += source_endpoint_count;
        }
        alt_count += source_alt_count;
    }
    return 0;
}

void io24_fake_libusb_reset(void)
{
    if (pending) { libusb_free_transfer(pending); pending = NULL; }
#ifdef IO24_PIPE_TABLE_ALLOC_AUDIT
    io24_pipe_table_audit_reset();
#endif
    memset(&counts, 0, sizeof(counts));
    memset(&record, 0, sizeof(record));
    memset(claim_journal, 0, sizeof(claim_journal));
    memset(release_journal, 0, sizeof(release_journal));
    alloc_count = alloc_attempts = submit_attempts = 0;
    reported_actual_length = 0;
    submit_result = clear_halt_result = claim_result = 0;
    claim_failure_call = alloc_failure_call = 0;
    alternate_result = control_result = 0;
    active_descriptor_enabled = interrupt_descriptor_enabled = extended_descriptor_enabled = 0;
}
const struct io24_fake_counts *io24_fake_libusb_counts(void){return &counts;}
const struct io24_fake_record *io24_fake_libusb_record(void){return &record;}
const unsigned char *io24_fake_mi05(size_t*size){*size=sizeof(mi05);return mi05;}
void io24_fake_libusb_set_submit_result(int r){submit_result=r;} void io24_fake_libusb_set_alloc_fail_at(unsigned int n){alloc_failure_call=n;} void io24_fake_libusb_set_clear_halt_result(int r){clear_halt_result=r;}
void io24_fake_libusb_enable_mi05_active_descriptor(int enable){active_descriptor_enabled=!!enable;}
void io24_fake_libusb_enable_interrupt_active_descriptor(int enable){interrupt_descriptor_enabled=!!enable;}
void io24_fake_libusb_enable_extended_active_descriptor(int enable){extended_descriptor_enabled=!!enable;}
void io24_fake_libusb_set_claim_result(int r){claim_result=r;claim_failure_call=r?1:0;} void io24_fake_libusb_set_claim_failure(unsigned int call,int r){claim_failure_call=call;claim_result=r;} void io24_fake_libusb_set_alternate_result(int r){alternate_result=r;} void io24_fake_libusb_set_control_result(int r){control_result=r;}
int io24_fake_libusb_claim_at(unsigned int i){return i<counts.claim?claim_journal[i]:-1;} int io24_fake_libusb_release_at(unsigned int i){return i<counts.release?release_journal[i]:-1;}
int io24_fake_libusb_has_pending(void){return pending!=NULL;} int io24_fake_libusb_pending_type(void){return pending?pending->type:-1;} int io24_fake_libusb_pending_endpoint(void){return pending?pending->endpoint:-1;} int io24_fake_libusb_pending_length(void){return pending?pending->length:-1;} int io24_fake_libusb_pending_flags(void){return pending?pending->flags:-1;}
unsigned int io24_fake_libusb_alloc_count(void){return alloc_count;} unsigned int io24_fake_libusb_alloc_attempts(void){return alloc_attempts;} unsigned int io24_fake_libusb_free_count(void){return counts.transfer_free;} unsigned int io24_fake_libusb_buffer_alloc_count(void){return counts.control_buffer_alloc;} unsigned int io24_fake_libusb_buffer_free_count(void){return counts.control_buffer_free;} unsigned int io24_fake_libusb_free_buffer_flag_count(void){return counts.control_free_buffer_flag;} unsigned int io24_fake_libusb_submit_count(void){return counts.bulk+counts.interrupt+counts.control;} unsigned int io24_fake_libusb_submit_attempts(void){return submit_attempts;} unsigned int io24_fake_libusb_cancel_count(void){return counts.cancel;} unsigned int io24_fake_libusb_clear_halt_count(void){return counts.clear_halt;} unsigned char io24_fake_libusb_clear_halt_endpoint(void){return record.endpoint;} int io24_fake_libusb_reported_actual_length(void){return reported_actual_length;}
int io24_fake_libusb_get_setup(unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE]){if(!pending||pending->type!=LIBUSB_TRANSFER_TYPE_CONTROL)return -1;memcpy(setup,pending->buffer,LIBUSB_CONTROL_SETUP_SIZE);return 0;}
int io24_fake_libusb_mutate_pending_control_payload(unsigned char value){size_t length;if(!pending||pending->type!=LIBUSB_TRANSFER_TYPE_CONTROL||!pending->buffer)return -1;length=pending->length>(int)LIBUSB_CONTROL_SETUP_SIZE?(size_t)pending->length-LIBUSB_CONTROL_SETUP_SIZE:0;memset(libusb_control_transfer_get_data(pending),value,length);return 0;}
int io24_fake_libusb_complete(enum libusb_transfer_status status,const unsigned char*data,size_t data_length,int actual_length){struct libusb_transfer*t=pending;size_t cap,copied,reported=actual_length>0?(size_t)actual_length:0;if(!t)return -1;pending=NULL;cap=(size_t)t->length;if(t->type==LIBUSB_TRANSFER_TYPE_CONTROL){unsigned char *buffer;size_t old_payload=cap>(size_t)LIBUSB_CONTROL_SETUP_SIZE?cap-LIBUSB_CONTROL_SETUP_SIZE:0;if(reported>old_payload){if(!(buffer=realloc(t->buffer,LIBUSB_CONTROL_SETUP_SIZE+reported)))return -1;t->buffer=buffer;memset(buffer+LIBUSB_CONTROL_SETUP_SIZE+old_payload,0xde,reported-old_payload);cap=LIBUSB_CONTROL_SETUP_SIZE+reported;}}copied=reported;if(t->type==LIBUSB_TRANSFER_TYPE_CONTROL)cap=cap>(size_t)LIBUSB_CONTROL_SETUP_SIZE?cap-LIBUSB_CONTROL_SETUP_SIZE:0;if(copied>cap)copied=cap;if(data&&copied>data_length)copied=data_length;if(data&&copied)memcpy(t->type==LIBUSB_TRANSFER_TYPE_CONTROL?libusb_control_transfer_get_data(t):t->buffer,data,copied);reported_actual_length=actual_length;t->status=status;t->actual_length=actual_length;t->callback(t);if(t->flags&LIBUSB_TRANSFER_FREE_TRANSFER)libusb_free_transfer(t);return 0;}
int io24_fake_libusb_discard_pending(void){struct libusb_transfer*t=pending;if(!t)return -1;pending=NULL;libusb_free_transfer(t);return 0;}

struct libusb_transfer *libusb_alloc_transfer(int iso){IO24_FAKE_API_CALL();size_t n;struct libusb_transfer*t;if(iso<0)return NULL;if(++alloc_attempts==alloc_failure_call)return NULL;n=sizeof(struct libusb_transfer)+(size_t)iso*sizeof(struct libusb_iso_packet_descriptor);t=calloc(1,n);if(t)alloc_count++;return t;}
void libusb_free_transfer(struct libusb_transfer*t){IO24_FAKE_API_CALL();if(!t)return;if(t->type==LIBUSB_TRANSFER_TYPE_CONTROL&&t->buffer){if(t->flags&LIBUSB_TRANSFER_FREE_BUFFER){++counts.control_free_buffer_flag;++counts.control_buffer_free;free(t->buffer);}}counts.transfer_free++;free(t);}
int libusb_submit_transfer(struct libusb_transfer*t){IO24_FAKE_API_CALL();++submit_attempts;if(t->type==LIBUSB_TRANSFER_TYPE_CONTROL&&t->buffer)++counts.control_buffer_alloc;if(submit_result<0)return submit_result;if(pending)return LIBUSB_ERROR_BUSY;pending=t;record.endpoint=t->endpoint;record.type=t->type;record.length=t->length;record.timeout=t->timeout;if(t->type==LIBUSB_TRANSFER_TYPE_CONTROL){struct libusb_control_setup*setup;size_t length,allocation_payload=0;/* Never trust setup.wLength beyond the actual control allocation. */if(t->length>=(int)LIBUSB_CONTROL_SETUP_SIZE)allocation_payload=(size_t)t->length-LIBUSB_CONTROL_SETUP_SIZE;setup=libusb_control_transfer_get_setup(t);length=libusb_le16_to_cpu(setup->wLength);record.request_type=setup->bmRequestType;record.request=setup->bRequest;record.value=libusb_le16_to_cpu(setup->wValue);record.index=libusb_le16_to_cpu(setup->wIndex);record.payload_length=(setup->bmRequestType&LIBUSB_ENDPOINT_IN)?0:length;if(record.payload_length>allocation_payload)record.payload_length=allocation_payload;if(record.payload_length>sizeof(record.payload))record.payload_length=sizeof(record.payload);if(record.payload_length)memcpy(record.payload,libusb_control_transfer_get_data(t),record.payload_length);counts.control++;}else if(t->type==LIBUSB_TRANSFER_TYPE_BULK)counts.bulk++;else if(t->type==LIBUSB_TRANSFER_TYPE_INTERRUPT)counts.interrupt++;return 0;}
int libusb_cancel_transfer(struct libusb_transfer*t){IO24_FAKE_API_CALL();counts.cancel++;return t==pending?0:LIBUSB_ERROR_NOT_FOUND;}
int libusb_clear_halt(libusb_device_handle*h,unsigned char e){IO24_FAKE_API_CALL();(void)h;counts.clear_halt++;record.endpoint=e;return clear_halt_result;}
int libusb_init(libusb_context**c){IO24_FAKE_API_CALL();if(c)*c=(void*)(uintptr_t)0x1000;return 0;} void libusb_exit(libusb_context*c){IO24_FAKE_API_CALL();(void)c;}
int libusb_hotplug_register_callback(libusb_context*c,int e,int f,int v,int p,int k,libusb_hotplug_callback_fn cb,void*u,libusb_hotplug_callback_handle*h){IO24_FAKE_API_CALL();(void)c;(void)e;(void)f;(void)v;(void)p;(void)k;(void)cb;(void)u;if(h)*h=1;return 0;} void libusb_hotplug_deregister_callback(libusb_context*c,libusb_hotplug_callback_handle h){IO24_FAKE_API_CALL();(void)c;(void)h;} int libusb_handle_events(libusb_context*c){IO24_FAKE_API_CALL();(void)c;return 0;} void libusb_interrupt_event_handler(libusb_context*c){IO24_FAKE_API_CALL();(void)c;}
uint8_t libusb_get_bus_number(libusb_device*d){IO24_FAKE_API_CALL();(void)d;return 1;} uint8_t libusb_get_port_number(libusb_device*d){IO24_FAKE_API_CALL();(void)d;return 1;} int libusb_get_device_speed(libusb_device*d){IO24_FAKE_API_CALL();(void)d;return LIBUSB_SPEED_HIGH;}
int libusb_get_device_descriptor(libusb_device*d,struct libusb_device_descriptor*x){IO24_FAKE_API_CALL();(void)d;memset(x,0,sizeof(*x));return 0;} int libusb_open(libusb_device*d,libusb_device_handle**h){IO24_FAKE_API_CALL();(void)d;if(h)*h=(void*)(uintptr_t)0x2000;return 0;} libusb_device *libusb_get_device(libusb_device_handle*h){libusb_device *result;IO24_FAKE_API_CALL();++counts.get_device;record.get_device_ordinal=counts.api_calls;record.get_device_handle=(uintptr_t)h;result=(void*)(uintptr_t)0x3000;record.get_device_result=(uintptr_t)result;return result;} void libusb_close(libusb_device_handle*h){IO24_FAKE_API_CALL();(void)h;counts.close++;
#ifdef IO24_PIPE_TABLE_ALLOC_AUDIT
io24_pipe_table_audit_note_close();
#endif
}
int libusb_get_active_config_descriptor(libusb_device *d,
        struct libusb_config_descriptor **c)
{
    const struct libusb_config_descriptor *source;
    int result;

    IO24_FAKE_API_CALL();
    ++counts.get_active_config_descriptor;
    record.get_active_config_descriptor_ordinal = counts.api_calls;
    record.get_active_config_descriptor_device = (uintptr_t)d;
    if (!active_descriptor_enabled)
    {
        if (c) *c = NULL;
        record.get_active_config_descriptor_result = (uintptr_t)NULL;
        return LIBUSB_ERROR_NOT_FOUND;
    }

    if (interrupt_descriptor_enabled) source = &interrupt_config;
    else if (extended_descriptor_enabled) source = &extended_mi05_config;
    else source = &mi05_config;
    if ((result = copy_config_view(source)))
    {
        if (c) *c = NULL;
        record.get_active_config_descriptor_result = (uintptr_t)NULL;
        return result;
    }
    if (c) *c = &config_view;
    record.get_active_config_descriptor_result = (uintptr_t)&config_view;
    return 0;
}

void libusb_free_config_descriptor(struct libusb_config_descriptor *c)
{
    IO24_FAKE_API_CALL();
    ++counts.free_config_descriptor;
    record.free_config_descriptor_ordinal = counts.api_calls;
    record.free_config_descriptor_input = (uintptr_t)c;
    if (c != &config_view) return;
    memset(config_endpoint_views, 0, sizeof(config_endpoint_views));
    memset(config_alt_views, 0, sizeof(config_alt_views));
    memset(config_interface_views, 0, sizeof(config_interface_views));
    memset(&config_view, 0, sizeof(config_view));
}

int libusb_get_active_interface_association_descriptors(libusb_device*d,struct libusb_interface_association_descriptor_array**a){IO24_FAKE_API_CALL();(void)d;if(a)*a=NULL;return LIBUSB_ERROR_NOT_SUPPORTED;} void libusb_free_interface_association_descriptors(struct libusb_interface_association_descriptor_array*a){IO24_FAKE_API_CALL();free(a);}
int libusb_claim_interface(libusb_device_handle*h,int i){IO24_FAKE_API_CALL();unsigned int call;(void)h;call=++counts.claim;claim_journal[call-1]=i;record.interface_number=i;return claim_failure_call==call?claim_result:0;} int libusb_release_interface(libusb_device_handle*h,int i){IO24_FAKE_API_CALL();unsigned int call;(void)h;call=++counts.release;release_journal[call-1]=i;record.interface_number=i;return 0;} int libusb_detach_kernel_driver(libusb_device_handle*h,int i){IO24_FAKE_API_CALL();(void)h;(void)i;counts.detach++;return 0;} int libusb_set_auto_detach_kernel_driver(libusb_device_handle*h,int e){IO24_FAKE_API_CALL();(void)h;(void)e;counts.auto_detach++;return 0;} int libusb_set_configuration(libusb_device_handle*h,int c){IO24_FAKE_API_CALL();(void)h;counts.set_configuration++;record.configuration=c;return 0;} int libusb_set_interface_alt_setting(libusb_device_handle*h,int i,int a){IO24_FAKE_API_CALL();(void)h;counts.set_alternate++;record.interface_number=i;record.alternate=a;return alternate_result;}
int libusb_control_transfer(libusb_device_handle*h,uint8_t rt,uint8_t r,uint16_t v,uint16_t i,unsigned char*d,uint16_t l,unsigned int t){IO24_FAKE_API_CALL();(void)h;counts.control++;record.request_type=rt;record.request=r;record.value=v;record.index=i;record.length=l;record.timeout=t;record.payload_length=(rt&LIBUSB_ENDPOINT_IN)?0:l;if(record.payload_length>sizeof(record.payload))record.payload_length=sizeof(record.payload);if(record.payload_length&&d)memcpy(record.payload,d,record.payload_length);return control_result<0?control_result:l;} int libusb_bulk_transfer(libusb_device_handle*h,unsigned char e,unsigned char*d,int l,int*x,unsigned int t){IO24_FAKE_API_CALL();(void)h;(void)d;(void)t;counts.bulk++;record.endpoint=e;record.length=l;if(x)*x=l;return 0;} int libusb_interrupt_transfer(libusb_device_handle*h,unsigned char e,unsigned char*d,int l,int*x,unsigned int t){IO24_FAKE_API_CALL();(void)h;(void)d;(void)t;counts.interrupt++;record.endpoint=e;record.length=l;if(x)*x=l;return 0;}
const char *libusb_strerror(int e){IO24_FAKE_API_CALL();(void)e;return "io24 fake libusb";}
