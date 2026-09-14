/* Executed CP33 lower contract using actual unixlib.c and fake libusb. */
#include <sys/wait.h>
#include <unistd.h>

#define main io24_retained_pipe_main
#include "wineusb_pipe_observe_contract.c"
#undef main

#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) { fprintf(stderr, "FAIL %s:%u: %s\n", __func__, __LINE__, #expr); ++counts.failures; } } while (0)
struct io24_fake_counts { unsigned claim,release,detach,auto_detach,set_configuration,set_alternate,control,bulk,interrupt,cancel,clear_halt,transfer_free,control_buffer_alloc,control_buffer_free,control_free_buffer_flag,close,api_calls,get_device,get_active_config_descriptor,free_config_descriptor; };
struct io24_fake_record { int interface_number,alternate,configuration; unsigned char endpoint,type; int length; uint8_t request_type,request; uint16_t value,index; unsigned int timeout; size_t payload_length; uint8_t payload[4096]; unsigned get_device_ordinal,get_active_config_descriptor_ordinal,free_config_descriptor_ordinal; uintptr_t get_device_handle,get_device_result,get_active_config_descriptor_device,get_active_config_descriptor_result,free_config_descriptor_input; };
const struct io24_fake_counts *io24_fake_libusb_counts(void);
const struct io24_fake_record *io24_fake_libusb_record(void);
void io24_fake_libusb_set_claim_result(int);
void io24_fake_libusb_set_claim_failure(unsigned int,int);
void io24_fake_libusb_set_alternate_result(int);
void io24_fake_libusb_enable_extended_active_descriptor(int);
int io24_fake_libusb_complete(enum libusb_transfer_status,const unsigned char*,size_t,int);
int io24_fake_libusb_claim_at(unsigned int);
int io24_fake_libusb_release_at(unsigned int);
int io24_fake_libusb_get_setup(unsigned char[LIBUSB_CONTROL_SETUP_SIZE]);
int io24_fake_libusb_mutate_pending_control_payload(unsigned char);
int io24_fake_libusb_pending_flags(void);
void io24_fake_libusb_set_submit_result(int);
void io24_fake_libusb_set_alloc_fail_at(unsigned int);
unsigned int io24_fake_libusb_alloc_attempts(void);
unsigned int io24_fake_libusb_submit_attempts(void);
unsigned int io24_fake_libusb_buffer_alloc_count(void);
unsigned int io24_fake_libusb_buffer_free_count(void);
unsigned int io24_fake_libusb_free_buffer_flag_count(void);
int io24_fake_libusb_reported_actual_length(void);
int io24_pipe_table_audit_pointer_live(const void *);
int io24_pipe_table_audit_capture_live(const void *, uint64_t *);

#define IO24_URB_FUNCTION_CLAIM_TRANSACTION 0x002f
#define IO24_CLAIM_TRANSACTION_COMMIT 1
#define IO24_CLAIM_TRANSACTION_ROLLBACK 2
struct io24_claim_transaction_request
{
    struct _URB_HEADER Hdr;
    USBD_CONFIGURATION_HANDLE Transaction;
    ULONG Operation;
    ULONG Reserved;
};

struct io24_function_device
{
    struct list entry; libusb_device_handle *handle; void *parent; unsigned int refcount;
    bool function; uint8_t function_interface_count; uint16_t configuration_length;
    uint8_t function_root; unsigned char function_interfaces[32];
    unsigned char claimed_interfaces[32]; void *pipe_table; void *pending_claim_transaction;
};

/* ABI-shaped inspection storage used only to seed an already-committed lower
 * table.  The contract never manufactures a HANDLE; production still mints
 * every observed token. */
struct io24_pipe_token { uint32_t generation; uint8_t endpoint,type,interface_number,alternate; bool current; };
struct io24_pipe_table { struct io24_pipe_token records[256]; uint8_t alternates[256]; uint32_t next_generation; };
#define IO24_GENERATION_MAX 0x7fffff

struct io24_pipe_table_audit
{
    void (*reset)(void);
    unsigned int (*allocations)(void);
    unsigned int (*frees)(void);
    unsigned int (*live)(void);
    unsigned int (*last_free_order)(void);
    unsigned int (*close_order)(void);
    unsigned int (*failures)(void);
};

static BOOL get_pipe_table_audit(struct io24_pipe_table_audit *audit)
{
    if (!getenv("IO24_PIPE_TABLE_ALLOC_AUDIT")) return FALSE;
    memset(audit, 0, sizeof(*audit));
    *(void **)&audit->reset = dlsym(RTLD_DEFAULT, "io24_pipe_table_audit_reset");
    *(void **)&audit->allocations = dlsym(RTLD_DEFAULT, "io24_pipe_table_audit_allocations");
    *(void **)&audit->frees = dlsym(RTLD_DEFAULT, "io24_pipe_table_audit_frees");
    *(void **)&audit->live = dlsym(RTLD_DEFAULT, "io24_pipe_table_audit_live");
    *(void **)&audit->last_free_order = dlsym(RTLD_DEFAULT, "io24_pipe_table_audit_last_free_order");
    *(void **)&audit->close_order = dlsym(RTLD_DEFAULT, "io24_pipe_table_audit_close_order");
    *(void **)&audit->failures = dlsym(RTLD_DEFAULT, "io24_pipe_table_audit_failures");
    return audit->reset && audit->allocations && audit->frees && audit->live &&
            audit->last_free_order && audit->close_order && audit->failures;
}

static void check_pipe_table_reclaimed(const struct io24_pipe_table_audit *audit,
        BOOL closed)
{
    IO24_CHECK(audit->allocations() == 1 && audit->frees() == 1 && audit->live() == 0);
    IO24_CHECK(audit->failures() == 0);
    if (closed)
    {
        IO24_CHECK(audit->close_order() != 0);
        IO24_CHECK(audit->last_free_order() < audit->close_order());
    }
    else IO24_CHECK(audit->close_order() == 0);
}

static void check_forbidden(void)
{
    const struct io24_fake_counts *c=io24_fake_libusb_counts();
    IO24_CHECK(c->detach==0&&c->auto_detach==0&&c->set_configuration==0);
}

static void initialize_function_device(struct io24_function_device *device,
        struct io24_function_device *parent, const unsigned char *interfaces,
        size_t interface_count)
{
    size_t i;

    memset(device,0,sizeof(*device));
    list_init(&device->entry);
    device->handle=(void*)(uintptr_t)0x12340000;
    device->parent=parent;
    device->refcount=1;
    device->function=true;
    device->function_root=interfaces[0];
    for(i=0;i<interface_count;++i)
    {
        device->function_interfaces[interfaces[i]/8]|=1u<<(interfaces[i]%8);
        device->function_interface_count++;
    }
}

static NTSTATUS submit_request(struct io24_function_device *device, void *request)
{
    IRP irp;
    IO_STACK_LOCATION stack;
    struct usb_submit_urb_params params;

    memset(&irp,0,sizeof(irp));memset(&stack,0,sizeof(stack));memset(&params,0,sizeof(params));
    irp.Tail.Overlay.CurrentStackLocation=&stack;
    stack.Parameters.Others.Argument1=request;
    params.device=(struct unix_device*)device;
    params.irp=&irp;
    return unix_calls[unix_usb_submit_urb](&params);
}

static void release_transfer(void *transfer)
{
    struct usb_release_transfer_params release = {.transfer = transfer};

    IO24_CHECK(transfer != NULL);
    if (transfer)
        IO24_CHECK(unix_calls[unix_usb_release_transfer](&release) == STATUS_SUCCESS);
}

/* R87: retained paths obtain opaque tokens from the actual lower SELECT
 * implementation; they never construct or decode a pipe handle. */
static HANDLE fixture_select_pipe(struct fixture *fixture, unsigned char endpoint,
        USBD_PIPE_TYPE type)
{
    struct _URB_SELECT_CONFIGURATION *select;
    unsigned int pipes = endpoint == 0x83 ? 1 : 2;

    reset_fixture(fixture, URB_FUNCTION_SELECT_CONFIGURATION);
    io24_fake_libusb_enable_mi05_active_descriptor(1);
    select = &fixture->urb.UrbSelectConfiguration;
    select->Hdr.Length = offsetof(struct _URB_SELECT_CONFIGURATION, Interface) +
            offsetof(USBD_INTERFACE_INFORMATION, Pipes) + pipes * sizeof(USBD_PIPE_INFORMATION);
    select->Interface.Length = offsetof(USBD_INTERFACE_INFORMATION, Pipes) +
            pipes * sizeof(USBD_PIPE_INFORMATION);
    select->Interface.InterfaceNumber = 5;
    select->Interface.AlternateSetting = 1;
    select->Interface.Class = 0xff;
    select->Interface.Protocol = 6;
    select->Interface.NumberOfPipes = pipes;
    select->Interface.Pipes[0].EndpointAddress = endpoint;
    select->Interface.Pipes[0].PipeType = type;
    select->Interface.Pipes[0].MaximumPacketSize = endpoint == 0x83 ? 64 : 512;
    select->Interface.Pipes[0].Interval = endpoint == 0x83 ? 1 : 0;
    if (pipes == 2)
    {
        select->Interface.Pipes[1].EndpointAddress = 0x01;
        select->Interface.Pipes[1].PipeType = UsbdPipeTypeBulk;
        select->Interface.Pipes[1].MaximumPacketSize = 512;
    }
    IO24_CHECK(submit_fixture(fixture) == STATUS_SUCCESS);
    return select->Interface.Pipes[0].PipeHandle;
}

static struct _URB_SELECT_CONFIGURATION *build_select(unsigned char buffer[256],
        const unsigned char *interfaces, size_t interface_count)
{
    struct _URB_SELECT_CONFIGURATION *select=(void*)buffer;
    size_t cursor=offsetof(struct _URB_SELECT_CONFIGURATION,Interface),i;

    memset(buffer,0,256);
    select->Hdr.Function=URB_FUNCTION_SELECT_CONFIGURATION;
    for(i=0;i<interface_count;++i)
    {
        USBD_INTERFACE_INFORMATION *information=(void*)(buffer+cursor);
        information->Length=offsetof(USBD_INTERFACE_INFORMATION,Pipes);
        information->InterfaceNumber=interfaces[i];
        information->AlternateSetting=0;
        if (interfaces[i] == 5)
        {
            information->Class=0xff;
            information->Protocol=6;
        }
        cursor+=information->Length;
    }
    select->Hdr.Length=cursor;
    return select;
}

static struct _URB_SELECT_CONFIGURATION *build_two_pipe_select(unsigned char buffer[512])
{
    struct _URB_SELECT_CONFIGURATION *select=(void *)buffer;
    USBD_INTERFACE_INFORMATION *interface;
    size_t cursor=offsetof(struct _URB_SELECT_CONFIGURATION,Interface);

    memset(buffer,0,512); select->Hdr.Function=URB_FUNCTION_SELECT_CONFIGURATION;
    interface=(void *)(buffer+cursor); interface->Length=offsetof(USBD_INTERFACE_INFORMATION,Pipes)+sizeof(USBD_PIPE_INFORMATION);
    interface->InterfaceNumber=7; interface->NumberOfPipes=1;
    interface->Pipes[0].EndpointAddress=0x82; interface->Pipes[0].PipeType=UsbdPipeTypeBulk;
    interface->Pipes[0].MaximumPacketSize=512; cursor+=interface->Length;
    interface=(void *)(buffer+cursor); interface->Length=offsetof(USBD_INTERFACE_INFORMATION,Pipes)+2*sizeof(USBD_PIPE_INFORMATION);
    interface->InterfaceNumber=5; interface->AlternateSetting=1; interface->Class=0xff; interface->Protocol=6; interface->NumberOfPipes=2;
    interface->Pipes[0].EndpointAddress=0x81; interface->Pipes[0].PipeType=UsbdPipeTypeBulk; interface->Pipes[0].MaximumPacketSize=512;
    interface->Pipes[1].EndpointAddress=0x01; interface->Pipes[1].PipeType=UsbdPipeTypeBulk; interface->Pipes[1].MaximumPacketSize=512;
    cursor+=interface->Length; select->Hdr.Length=cursor; return select;
}

static struct _URB_SELECT_CONFIGURATION *build_claim_pipe_select(
        unsigned char buffer[256], unsigned char interface_number)
{
    struct _URB_SELECT_CONFIGURATION *select=(void *)buffer;
    USBD_INTERFACE_INFORMATION *interface=&select->Interface;
    unsigned int pipes=interface_number==5?2:1;

    memset(buffer,0,256); select->Hdr.Function=URB_FUNCTION_SELECT_CONFIGURATION;
    interface->Length=offsetof(USBD_INTERFACE_INFORMATION,Pipes)+
            pipes*sizeof(USBD_PIPE_INFORMATION);
    select->Hdr.Length=offsetof(struct _URB_SELECT_CONFIGURATION,Interface)+
            interface->Length;
    interface->InterfaceNumber=interface_number;
    interface->AlternateSetting=interface_number==5?1:0;
    interface->Class=interface_number==5?0xff:0;
    interface->Protocol=interface_number==5?6:0;
    interface->NumberOfPipes=pipes;
    interface->Pipes[0].EndpointAddress=interface_number==5?0x81:0x82;
    interface->Pipes[0].PipeType=UsbdPipeTypeBulk;
    interface->Pipes[0].MaximumPacketSize=512;
    if(pipes==2)
    {
        interface->Pipes[1].EndpointAddress=0x01;
        interface->Pipes[1].PipeType=UsbdPipeTypeBulk;
        interface->Pipes[1].MaximumPacketSize=512;
    }
    return select;
}

static NTSTATUS finalize_claim(struct io24_function_device *device,
        USBD_CONFIGURATION_HANDLE token, ULONG operation,
        struct io24_claim_transaction_request *request)
{
    memset(request,0,sizeof(*request));
    request->Hdr.Length=sizeof(*request);
    request->Hdr.Function=IO24_URB_FUNCTION_CLAIM_TRANSACTION;
    request->Hdr.Status=USBD_STATUS_NOT_ACCESSED;
    request->Transaction=token;
    request->Operation=operation;
    return submit_request(device,request);
}

static void audit_pipe_table_reclamation(void)
{
    static const unsigned char mi05[]={5};
    struct io24_pipe_table_audit audit;
    struct io24_function_device *parent, *child;
    struct io24_claim_transaction_request finalize;
    struct _URB_SELECT_CONFIGURATION *select;
    struct usb_destroy_device_params destroy;
    unsigned char buffer[256];

    if (!getenv("IO24_PIPE_TABLE_ALLOC_AUDIT")) return;
    if (!get_pipe_table_audit(&audit))
    {
        IO24_CHECK(FALSE);
        return;
    }

#define PREPARE_AUDIT_PAIR() do { \
    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1); audit.reset(); \
    parent=calloc(1,sizeof(*parent)); child=calloc(1,sizeof(*child)); \
    IO24_CHECK(parent&&child); if(!parent||!child){free(parent);free(child);return;} \
    list_init(&parent->entry); parent->handle=(void *)(uintptr_t)0x12340000; parent->refcount=2; \
    initialize_function_device(child,parent,mi05,ARRAY_SIZE(mi05)); \
    select=build_select(buffer,mi05,ARRAY_SIZE(mi05)); \
    IO24_CHECK(submit_request(child,select)==STATUS_SUCCESS); \
} while(0)
#define DESTROY_AUDIT_PAIR() do { \
    destroy.device=(struct unix_device *)child; \
    IO24_CHECK(unix_calls[unix_usb_destroy_device](&destroy)==STATUS_SUCCESS); \
    IO24_CHECK(parent->refcount==1&&io24_fake_libusb_counts()->release==1&& \
            io24_fake_libusb_release_at(0)==5&&io24_fake_libusb_counts()->close==0); \
    destroy.device=(struct unix_device *)parent; \
    IO24_CHECK(unix_calls[unix_usb_destroy_device](&destroy)==STATUS_SUCCESS); \
    IO24_CHECK(io24_fake_libusb_counts()->close==1); \
} while(0)

    /* Explicit rollback frees the staged table before either device is closed. */
    PREPARE_AUDIT_PAIR();
    IO24_CHECK(finalize_claim(child,select->ConfigurationHandle,
            IO24_CLAIM_TRANSACTION_ROLLBACK,&finalize)==STATUS_SUCCESS);
    check_pipe_table_reclaimed(&audit,FALSE); DESTROY_AUDIT_PAIR();
    check_pipe_table_reclaimed(&audit,TRUE);

    /* Destruction of an unresolved transaction owns the staged table exactly once. */
    PREPARE_AUDIT_PAIR();
    DESTROY_AUDIT_PAIR(); check_pipe_table_reclaimed(&audit,TRUE);

    /* After COMMIT the child owns the table; its destruction precedes parent close. */
    PREPARE_AUDIT_PAIR();
    IO24_CHECK(finalize_claim(child,select->ConfigurationHandle,
            IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_SUCCESS);
    DESTROY_AUDIT_PAIR(); check_pipe_table_reclaimed(&audit,TRUE);
#undef DESTROY_AUDIT_PAIR
#undef PREPARE_AUDIT_PAIR
}

static void group_claims(void)
{
    static const unsigned char mi05[]={5}, multi[]={7,2,5}, bad_scope[]={2,9};
    struct io24_function_device device;
    struct io24_claim_transaction_request finalize;
    struct _URB_SELECT_CONFIGURATION *select;
    const struct io24_fake_counts *c;
    USBD_CONFIGURATION_HANDLE first,second;
    unsigned char buffer[256];

    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    initialize_function_device(&device,NULL,mi05,ARRAY_SIZE(mi05));
    /* A function configuration is descriptor-backed before claims and must
     * preserve its caller token on a missing descriptor. */
    select=build_select(buffer,mi05,ARRAY_SIZE(mi05));
    select->ConfigurationHandle=(void *)(uintptr_t)0xaaaa;
    io24_fake_libusb_enable_mi05_active_descriptor(0);
    IO24_CHECK(submit_request(&device,select)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(select->ConfigurationHandle==(void *)(uintptr_t)0xaaaa);
    IO24_CHECK(io24_fake_libusb_counts()->claim==0&&device.pending_claim_transaction==NULL);
    io24_fake_libusb_enable_mi05_active_descriptor(1);
    select=build_select(buffer,mi05,ARRAY_SIZE(mi05));
    IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
    first=select->ConfigurationHandle;
    c=io24_fake_libusb_counts();
    IO24_CHECK(first!=NULL&&select->Hdr.Status==USBD_STATUS_SUCCESS);
    IO24_CHECK(c->claim==1&&c->release==0&&io24_fake_libusb_claim_at(0)==5);
    check_forbidden();

    select=build_select(buffer,mi05,ARRAY_SIZE(mi05));
    IO24_CHECK(submit_request(&device,select)==STATUS_INVALID_DEVICE_STATE);
    IO24_CHECK(select->Hdr.Status==USBD_STATUS_REQUEST_FAILED);
    IO24_CHECK(io24_fake_libusb_counts()->claim==1&&io24_fake_libusb_counts()->release==0);

    memset(&finalize,0,sizeof(finalize));finalize.Hdr.Length=sizeof(finalize)-1;
    finalize.Hdr.Function=IO24_URB_FUNCTION_CLAIM_TRANSACTION;
    finalize.Transaction=first;finalize.Operation=IO24_CLAIM_TRANSACTION_COMMIT;
    IO24_CHECK(submit_request(&device,&finalize)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(finalize_claim(&device,(void*)(uintptr_t)0x5a5a,
            IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(finalize_claim(&device,first,IO24_CLAIM_TRANSACTION_COMMIT,
            &finalize)==STATUS_SUCCESS);
    IO24_CHECK(finalize.Hdr.Status==USBD_STATUS_SUCCESS);
    IO24_CHECK(finalize_claim(&device,first,IO24_CLAIM_TRANSACTION_ROLLBACK,
            &finalize)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->claim==1&&io24_fake_libusb_counts()->release==0);

    select=build_select(buffer,mi05,ARRAY_SIZE(mi05));
    IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
    second=select->ConfigurationHandle;
    IO24_CHECK(second&&second!=first&&io24_fake_libusb_counts()->claim==1);
    IO24_CHECK(finalize_claim(&device,second,IO24_CLAIM_TRANSACTION_COMMIT,
            &finalize)==STATUS_SUCCESS);
    IO24_CHECK(io24_fake_libusb_counts()->claim==1&&io24_fake_libusb_counts()->release==0);

    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    initialize_function_device(&device,NULL,multi,ARRAY_SIZE(multi));
    select=build_select(buffer,bad_scope,ARRAY_SIZE(bad_scope));
    IO24_CHECK(submit_request(&device,select)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->claim==0&&io24_fake_libusb_counts()->release==0);
    select=build_select(buffer,multi,ARRAY_SIZE(multi));
    io24_fake_libusb_set_claim_failure(2,LIBUSB_ERROR_IO);
    IO24_CHECK(submit_request(&device,select)==STATUS_UNSUCCESSFUL);
    c=io24_fake_libusb_counts();
    IO24_CHECK(select->Hdr.Status==USBD_STATUS_REQUEST_FAILED);
    IO24_CHECK(c->claim==2&&io24_fake_libusb_claim_at(0)==2&&io24_fake_libusb_claim_at(1)==5);
    IO24_CHECK(c->release==1&&io24_fake_libusb_release_at(0)==2);
    check_forbidden();

    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    initialize_function_device(&device,NULL,multi,ARRAY_SIZE(multi));
    select=build_select(buffer,multi,ARRAY_SIZE(multi));
    io24_fake_libusb_set_claim_failure(1,LIBUSB_ERROR_BUSY);
    IO24_CHECK(submit_request(&device,select)==STATUS_DEVICE_BUSY);
    IO24_CHECK(select->Hdr.Status==USBD_STATUS_REQUEST_FAILED);
    IO24_CHECK(io24_fake_libusb_counts()->claim==1&&io24_fake_libusb_counts()->release==0);
    check_forbidden();

    /* A nonempty explicit rollback releases only its journal in reverse order.
     * A later partial extension must preserve the earlier committed claim. */
    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    {
        static const unsigned char scope[]={2,5,7}, committed[]={2};
        static const unsigned char extension[]={5,7}, all[]={2,5,7};

        initialize_function_device(&device,NULL,scope,ARRAY_SIZE(scope));
        select=build_select(buffer,committed,ARRAY_SIZE(committed));
        IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
        IO24_CHECK(finalize_claim(&device,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->claim==1&&
                io24_fake_libusb_claim_at(0)==2&&io24_fake_libusb_counts()->release==0);

        select=build_select(buffer,extension,ARRAY_SIZE(extension));
        IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
        IO24_CHECK(finalize_claim(&device,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_ROLLBACK,&finalize)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->claim==3&&
                io24_fake_libusb_claim_at(1)==5&&io24_fake_libusb_claim_at(2)==7);
        IO24_CHECK(io24_fake_libusb_counts()->release==2&&
                io24_fake_libusb_release_at(0)==7&&io24_fake_libusb_release_at(1)==5);

        select=build_select(buffer,committed,ARRAY_SIZE(committed));
        IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
        IO24_CHECK(finalize_claim(&device,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->claim==3&&
                io24_fake_libusb_counts()->release==2);

        io24_fake_libusb_set_claim_failure(5,LIBUSB_ERROR_IO);
        select=build_select(buffer,all,ARRAY_SIZE(all));
        IO24_CHECK(submit_request(&device,select)==STATUS_UNSUCCESSFUL);
        IO24_CHECK(select->Hdr.Status==USBD_STATUS_REQUEST_FAILED);
        IO24_CHECK(io24_fake_libusb_counts()->claim==5&&
                io24_fake_libusb_claim_at(3)==5&&io24_fake_libusb_claim_at(4)==7);
        IO24_CHECK(io24_fake_libusb_counts()->release==3&&
                io24_fake_libusb_release_at(2)==5);

        select=build_select(buffer,committed,ARRAY_SIZE(committed));
        IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
        IO24_CHECK(finalize_claim(&device,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->claim==5&&
                io24_fake_libusb_counts()->release==3);
        check_forbidden();
    }

    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    {
        struct io24_function_device *parent=calloc(1,sizeof(*parent));
        struct io24_function_device *left=calloc(1,sizeof(*left));
        struct io24_function_device *right=calloc(1,sizeof(*right));
        static const unsigned char left_interfaces[]={5},right_interfaces[]={7};
        struct usb_destroy_device_params destroy;

        IO24_CHECK(parent&&left&&right);
        if(!parent||!left||!right){free(parent);free(left);free(right);return;}
        list_init(&parent->entry);parent->handle=(void*)(uintptr_t)0x12340000;parent->refcount=3;
        initialize_function_device(left,parent,left_interfaces,ARRAY_SIZE(left_interfaces));
        initialize_function_device(right,parent,right_interfaces,ARRAY_SIZE(right_interfaces));
        select=build_select(buffer,left_interfaces,ARRAY_SIZE(left_interfaces));
        IO24_CHECK(submit_request(left,select)==STATUS_SUCCESS);
        IO24_CHECK(finalize_claim(left,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_SUCCESS);
        select=build_select(buffer,right_interfaces,ARRAY_SIZE(right_interfaces));
        IO24_CHECK(submit_request(right,select)==STATUS_SUCCESS);
        IO24_CHECK(finalize_claim(right,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->claim==2&&
                io24_fake_libusb_claim_at(0)==5&&io24_fake_libusb_claim_at(1)==7);
        destroy.device=(struct unix_device*)left;
        IO24_CHECK(unix_calls[unix_usb_destroy_device](&destroy)==STATUS_SUCCESS);
        IO24_CHECK(parent->refcount==2&&io24_fake_libusb_counts()->release==1&&
                io24_fake_libusb_release_at(0)==5&&io24_fake_libusb_counts()->close==0);
        select=build_select(buffer,right_interfaces,ARRAY_SIZE(right_interfaces));
        IO24_CHECK(submit_request(right,select)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->claim==2);
        IO24_CHECK(finalize_claim(right,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_ROLLBACK,&finalize)==STATUS_SUCCESS);
        destroy.device=(struct unix_device*)right;
        IO24_CHECK(unix_calls[unix_usb_destroy_device](&destroy)==STATUS_SUCCESS);
        IO24_CHECK(parent->refcount==1&&io24_fake_libusb_counts()->release==2&&
                io24_fake_libusb_release_at(1)==7&&io24_fake_libusb_counts()->close==0);
        destroy.device=(struct unix_device*)parent;
        IO24_CHECK(unix_calls[unix_usb_destroy_device](&destroy)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->close==1);
        check_forbidden();
    }

    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    {
        struct io24_function_device *parent=calloc(1,sizeof(*parent));
        struct io24_function_device *child=calloc(1,sizeof(*child));
        static const unsigned char pending_interfaces[]={2,5};
        struct usb_destroy_device_params destroy;

        IO24_CHECK(parent&&child);
        if(!parent||!child){free(parent);free(child);return;}
        list_init(&parent->entry);parent->handle=(void*)(uintptr_t)0x12340000;parent->refcount=2;
        initialize_function_device(child,parent,pending_interfaces,ARRAY_SIZE(pending_interfaces));
        select=build_select(buffer,pending_interfaces,ARRAY_SIZE(pending_interfaces));
        IO24_CHECK(submit_request(child,select)==STATUS_SUCCESS);
        destroy.device=(struct unix_device*)child;
        IO24_CHECK(unix_calls[unix_usb_destroy_device](&destroy)==STATUS_SUCCESS);
        IO24_CHECK(parent->refcount==1&&io24_fake_libusb_counts()->release==2&&
                io24_fake_libusb_release_at(0)==5&&io24_fake_libusb_release_at(1)==2);
        destroy.device=(struct unix_device*)parent;
        IO24_CHECK(unix_calls[unix_usb_destroy_device](&destroy)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->close==1);
        check_forbidden();
    }

    /* A committed map at terminal generation is preserved; SELECT_CONFIG
     * rejects before a new claim transaction or caller-field publication. */
    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    initialize_function_device(&device,NULL,mi05,ARRAY_SIZE(mi05));
    {
        struct io24_pipe_table terminal={0};
        terminal.next_generation=IO24_GENERATION_MAX+1;
        device.pipe_table=&terminal;
        select=build_select(buffer,mi05,ARRAY_SIZE(mi05));
        select->ConfigurationHandle=(void *)(uintptr_t)0xcccc;
        IO24_CHECK(submit_request(&device,select)==STATUS_INSUFFICIENT_RESOURCES);
        IO24_CHECK(select->ConfigurationHandle==(void *)(uintptr_t)0xcccc&&
                device.pipe_table==&terminal&&device.pending_claim_transaction==NULL&&
                io24_fake_libusb_counts()->claim==0);
        device.pipe_table=NULL;
    }

    /* A partial claim extension stages from the committed pipe table.  The
     * second transaction replaces only MI05, so MI07's committed claim and
     * production-issued descriptor-backed token must remain usable. */
    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    io24_fake_libusb_enable_extended_active_descriptor(1);
    {
        static const unsigned char scope[]={5,7};
        struct io24_function_device extension_device;
        struct io24_claim_transaction_request extension_finalize;
        struct _URB_PIPE_REQUEST pipe;
        HANDLE token7;
        unsigned int clear_before;

        initialize_function_device(&extension_device,NULL,scope,ARRAY_SIZE(scope));
        select=build_claim_pipe_select(buffer,7);
        IO24_CHECK(submit_request(&extension_device,select)==STATUS_SUCCESS);
        token7=select->Interface.Pipes[0].PipeHandle;
        IO24_CHECK(token7!=NULL);
        IO24_CHECK(finalize_claim(&extension_device,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_COMMIT,&extension_finalize)==STATUS_SUCCESS);
        IO24_CHECK((extension_device.claimed_interfaces[7/8]&(1u<<(7%8)))!=0);

        memset(&pipe,0,sizeof(pipe)); pipe.Hdr.Function=URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL;
        pipe.PipeHandle=token7; clear_before=io24_fake_libusb_counts()->clear_halt;
        IO24_CHECK(submit_request(&extension_device,&pipe)==STATUS_SUCCESS);

        select=build_claim_pipe_select(buffer,5);
        IO24_CHECK(submit_request(&extension_device,select)==STATUS_SUCCESS);
        IO24_CHECK(finalize_claim(&extension_device,select->ConfigurationHandle,
                IO24_CLAIM_TRANSACTION_COMMIT,&extension_finalize)==STATUS_SUCCESS);
        IO24_CHECK((extension_device.claimed_interfaces[7/8]&(1u<<(7%8)))!=0&&
                (extension_device.claimed_interfaces[5/8]&(1u<<(5%8)))!=0);
        pipe.PipeHandle=token7;
        IO24_CHECK(submit_request(&extension_device,&pipe)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->clear_halt==clear_before+2);
        free(extension_device.pipe_table); extension_device.pipe_table=NULL;
    }
    audit_pipe_table_reclamation();
}
static void group_alternate(void)
{
    static const unsigned char mi05[]={5};
    struct io24_function_device device; struct io24_claim_transaction_request finalize;
    struct _URB_SELECT_CONFIGURATION *select; const struct io24_fake_counts*c;
    struct _URB_PIPE_REQUEST stale;
    HANDLE old0, old1;
    struct io24_pipe_table *observed;
    struct io24_pipe_token saved;
    unsigned int slot;
    unsigned char config[256], storage[16+offsetof(struct _URB_SELECT_INTERFACE,Interface)+offsetof(USBD_INTERFACE_INFORMATION,Pipes)+2*sizeof(USBD_PIPE_INFORMATION)+16];
    struct _URB_SELECT_INTERFACE *r=(void*)(storage+16); size_t size=offsetof(struct _URB_SELECT_INTERFACE,Interface)+offsetof(USBD_INTERFACE_INFORMATION,Pipes)+2*sizeof(USBD_PIPE_INFORMATION); unsigned i, before;

    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1); initialize_function_device(&device,NULL,mi05,ARRAY_SIZE(mi05));
    select=build_select(config,mi05,ARRAY_SIZE(mi05));
    IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
    IO24_CHECK(finalize_claim(&device,select->ConfigurationHandle,IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_SUCCESS);
    memset(storage,GUARD_BYTE,sizeof(storage));memset(r,0,size);r->Hdr.Function=URB_FUNCTION_SELECT_INTERFACE;r->Hdr.Length=size;r->Interface.Length=size-offsetof(struct _URB_SELECT_INTERFACE,Interface);r->Interface.InterfaceNumber=5;r->Interface.AlternateSetting=1;r->Interface.Class=0xff;r->Interface.SubClass=0;r->Interface.Protocol=6;r->Interface.NumberOfPipes=2;r->Interface.Pipes[0].EndpointAddress=0x81;r->Interface.Pipes[0].PipeType=UsbdPipeTypeBulk;r->Interface.Pipes[0].MaximumPacketSize=512;r->Interface.Pipes[1].EndpointAddress=0x01;r->Interface.Pipes[1].PipeType=UsbdPipeTypeBulk;r->Interface.Pipes[1].MaximumPacketSize=512;
    IO24_CHECK(submit_request(&device,r)==STATUS_SUCCESS);c=io24_fake_libusb_counts();IO24_CHECK(c->set_alternate==1);IO24_CHECK(io24_fake_libusb_record()->interface_number==5&&io24_fake_libusb_record()->alternate==1);IO24_CHECK(r->Interface.Pipes[0].PipeHandle&&r->Interface.Pipes[1].PipeHandle);old0=r->Interface.Pipes[0].PipeHandle;old1=r->Interface.Pipes[1].PipeHandle;IO24_CHECK(((uintptr_t)old0>>9)==((uintptr_t)old1>>9));for(i=0;i<16;++i)IO24_CHECK(storage[i]==GUARD_BYTE&&storage[sizeof(storage)-16+i]==GUARD_BYTE);

    before=c->set_alternate; r->Interface.Pipes[0].MaximumPacketSize=256;
    IO24_CHECK(submit_request(&device,r)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before&&r->Interface.Pipes[0].PipeHandle==old0);
    r->Interface.Pipes[0].MaximumPacketSize=512; r->Interface.Pipes[0].Interval=1;
    IO24_CHECK(submit_request(&device,r)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before&&r->Interface.Pipes[0].PipeHandle==old0);
    r->Interface.Pipes[0].Interval=0;

    before=c->set_alternate; r->Interface.InterfaceNumber=7;
    IO24_CHECK(submit_request(&device,r)==STATUS_INVALID_PARAMETER);IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before);
    r->Interface.InterfaceNumber=5; r->Hdr.Length--;
    IO24_CHECK(submit_request(&device,r)==STATUS_INVALID_PARAMETER);IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before);
    r->Hdr.Length=size; r->Interface.Length++; before=io24_fake_libusb_counts()->set_alternate;
    IO24_CHECK(submit_request(&device,r)==STATUS_INVALID_PARAMETER);IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before);
    r->Interface.Length--; io24_fake_libusb_set_alternate_result(LIBUSB_ERROR_IO);
    r->Interface.Pipes[0].PipeHandle=(HANDLE)(uintptr_t)0x1111;
    IO24_CHECK(submit_request(&device,r)==STATUS_UNSUCCESSFUL);IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before+1);IO24_CHECK(r->Interface.Pipes[0].PipeHandle==(HANDLE)(uintptr_t)0x1111);
    io24_fake_libusb_set_alternate_result(0); r->Interface.AlternateSetting=2;
    IO24_CHECK(submit_request(&device,r)==STATUS_INVALID_PARAMETER);IO24_CHECK(r->Interface.Pipes[0].PipeHandle==(HANDLE)(uintptr_t)0x1111);
    r->Interface.AlternateSetting=1; r->Interface.Pipes[0].PipeHandle=NULL; r->Interface.Pipes[1].PipeHandle=NULL;
    IO24_CHECK(submit_request(&device,r)==STATUS_SUCCESS);
    memset(&stale,0,sizeof(stale)); stale.Hdr.Function=URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL; stale.PipeHandle=old0;
    before=io24_fake_libusb_counts()->clear_halt;
    IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->clear_halt==before&&old0!=r->Interface.Pipes[0].PipeHandle);
    /* The current production-issued token is rejected for every independently
     * validated record field, without reaching the clear-halt backend. */
    stale.PipeHandle=r->Interface.Pipes[0].PipeHandle;
    observed=device.pipe_table; slot=((uintptr_t)stale.PipeHandle&0x1ff)-1;
    saved=observed->records[slot]; before=io24_fake_libusb_counts()->clear_halt;
    stale.PipeHandle=(HANDLE)((uintptr_t)stale.PipeHandle ^ 2);
    IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER);
    stale.PipeHandle=(HANDLE)((uintptr_t)stale.PipeHandle ^ (1u<<9));
    IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER);
    stale.PipeHandle=r->Interface.Pipes[0].PipeHandle;
    observed->records[slot].endpoint=0x82; IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER); observed->records[slot]=saved;
    observed->records[slot].type=UsbdPipeTypeInterrupt; IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER); observed->records[slot]=saved;
    observed->records[slot].interface_number=7; IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER); observed->records[slot]=saved;
    observed->records[slot].alternate=0; IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER); observed->records[slot]=saved;
    observed->records[slot].current=false; IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER); observed->records[slot]=saved;
    device.claimed_interfaces[5/8]&=~(1u<<(5%8)); IO24_CHECK(submit_request(&device,&stale)==STATUS_INVALID_PARAMETER); device.claimed_interfaces[5/8]|=1u<<(5%8);
    IO24_CHECK(io24_fake_libusb_counts()->clear_halt==before);
    check_forbidden();
}

static void group_atomicity(void)
{
    static const unsigned char mi05[]={5};
    struct io24_function_device device;
    struct io24_pipe_table *table;
    unsigned char storage[offsetof(struct _URB_SELECT_INTERFACE,Interface)+
            offsetof(USBD_INTERFACE_INFORMATION,Pipes)+2*sizeof(USBD_PIPE_INFORMATION)];
    struct _URB_SELECT_INTERFACE *r=(void *)storage;
    size_t size=sizeof(storage);
    unsigned int i, before;
    unsigned char *oversized;
    struct _URB_SELECT_CONFIGURATION *configuration;
    size_t configuration_size;

    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1);
    initialize_function_device(&device,NULL,mi05,ARRAY_SIZE(mi05));
    device.claimed_interfaces[5/8]|=1u<<(5%8);
    memset(r,0,size); r->Hdr.Function=URB_FUNCTION_SELECT_INTERFACE;
    r->Hdr.Length=size; r->Interface.Length=size-offsetof(struct _URB_SELECT_INTERFACE,Interface);
    r->Interface.InterfaceNumber=5; r->Interface.AlternateSetting=1;
    r->Interface.Class=0xff; r->Interface.Protocol=6; r->Interface.NumberOfPipes=2;
    r->Interface.Pipes[0].EndpointAddress=0x81; r->Interface.Pipes[0].PipeType=UsbdPipeTypeBulk; r->Interface.Pipes[0].MaximumPacketSize=512;
    r->Interface.Pipes[1].EndpointAddress=0x01; r->Interface.Pipes[1].PipeType=UsbdPipeTypeBulk; r->Interface.Pipes[1].MaximumPacketSize=512;

    /* Exact capacity: 255 occupied unrelated slots leave one, so staging two
     * replacements must fail before libusb. */
    table=calloc(1,sizeof(*table)); IO24_CHECK(table!=NULL);
    if (!table) return;
    for(i=0;i<255;++i) table->records[i]=(struct io24_pipe_token){1,0x81,UsbdPipeTypeBulk,2,0,true};
    table->next_generation=2; device.pipe_table=table;
    before=io24_fake_libusb_counts()->set_alternate;
    IO24_CHECK(submit_request(&device,r)==STATUS_INSUFFICIENT_RESOURCES);
    IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before);
    IO24_CHECK(r->Interface.Pipes[0].PipeHandle==NULL&&r->Interface.Pipes[1].PipeHandle==NULL);
    free(device.pipe_table); device.pipe_table=NULL;

    /* The maximum generation is usable exactly once; the next operation is
     * terminal and cannot reach the backend or overwrite returned fields. */
    table=calloc(1,sizeof(*table)); IO24_CHECK(table!=NULL);
    if (!table) return;
    table->next_generation=IO24_GENERATION_MAX; device.pipe_table=table;
    IO24_CHECK(submit_request(&device,r)==STATUS_SUCCESS);
    before=io24_fake_libusb_counts()->set_alternate;
    r->Interface.Pipes[0].PipeHandle=(HANDLE)(uintptr_t)0x5555;
    IO24_CHECK(submit_request(&device,r)==STATUS_INSUFFICIENT_RESOURCES);
    IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before);
    IO24_CHECK(r->Interface.Pipes[0].PipeHandle==(HANDLE)(uintptr_t)0x5555);
    free(device.pipe_table); device.pipe_table=NULL;

    /* Both undersize and trailing-byte variable layouts are rejected before
     * an alternate backend call. */
    r->Hdr.Length=size-1; before=io24_fake_libusb_counts()->set_alternate;
    IO24_CHECK(submit_request(&device,r)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->set_alternate==before);
    check_forbidden();

    /* SELECT_CONFIGURATION rejects a map larger than the exact 256-slot
     * table before it can allocate tokens, claim, or publish any pipe field. */
    io24_fake_libusb_reset();
    initialize_function_device(&device,NULL,mi05,ARRAY_SIZE(mi05));
    device.function=false;
    configuration_size=offsetof(struct _URB_SELECT_CONFIGURATION,Interface)+
            offsetof(USBD_INTERFACE_INFORMATION,Pipes)+257*sizeof(USBD_PIPE_INFORMATION);
    oversized=calloc(1,configuration_size); IO24_CHECK(oversized!=NULL);
    if (!oversized) return;
    configuration=(void *)oversized;
    configuration->Hdr.Function=URB_FUNCTION_SELECT_CONFIGURATION;
    configuration->Hdr.Length=configuration_size;
    configuration->Interface.Length=configuration_size-offsetof(struct _URB_SELECT_CONFIGURATION,Interface);
    configuration->Interface.NumberOfPipes=257;
    for(i=0;i<257;++i)
    {
        configuration->Interface.Pipes[i].EndpointAddress=0x81;
        configuration->Interface.Pipes[i].PipeType=UsbdPipeTypeBulk;
        configuration->Interface.Pipes[i].PipeHandle=(HANDLE)(uintptr_t)0x3333;
    }
    IO24_CHECK(submit_request(&device,configuration)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->claim==0&&
            io24_fake_libusb_counts()->set_configuration==0);
    IO24_CHECK(configuration->Interface.Pipes[0].PipeHandle==(HANDLE)(uintptr_t)0x3333&&
            configuration->Interface.Pipes[256].PipeHandle==(HANDLE)(uintptr_t)0x3333);
    free(oversized);
}

static void group_target_only(void)
{
    static const unsigned char both[]={5,7};
    struct io24_function_device device;
    struct io24_claim_transaction_request finalize;
    unsigned char config[512], storage[offsetof(struct _URB_SELECT_INTERFACE,Interface)+
            offsetof(USBD_INTERFACE_INFORMATION,Pipes)+2*sizeof(USBD_PIPE_INFORMATION)];
    struct _URB_SELECT_CONFIGURATION *select;
    struct _URB_SELECT_INTERFACE *alternate=(void *)storage;
    struct _URB_PIPE_REQUEST pipe;
    HANDLE old5, token7;
    void *committed;
    size_t size=sizeof(storage);
    unsigned before;

    io24_fake_libusb_reset(); io24_fake_libusb_enable_mi05_active_descriptor(1); io24_fake_libusb_enable_extended_active_descriptor(1);
    initialize_function_device(&device,NULL,both,ARRAY_SIZE(both));
    select=build_two_pipe_select(config);
    IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
    IO24_CHECK(finalize_claim(&device,select->ConfigurationHandle,IO24_CLAIM_TRANSACTION_COMMIT,&finalize)==STATUS_SUCCESS);
    committed=device.pipe_table;
    token7=((USBD_INTERFACE_INFORMATION *)(config+offsetof(struct _URB_SELECT_CONFIGURATION,Interface)))->Pipes[0].PipeHandle;
    old5=((USBD_INTERFACE_INFORMATION *)(config+offsetof(struct _URB_SELECT_CONFIGURATION,Interface)+
            ((USBD_INTERFACE_INFORMATION *)(config+offsetof(struct _URB_SELECT_CONFIGURATION,Interface)))->Length))->Pipes[0].PipeHandle;
    memset(alternate,0,size); alternate->Hdr.Function=URB_FUNCTION_SELECT_INTERFACE; alternate->Hdr.Length=size;
    alternate->Interface.Length=size-offsetof(struct _URB_SELECT_INTERFACE,Interface); alternate->Interface.InterfaceNumber=5;
    alternate->Interface.AlternateSetting=1; alternate->Interface.Class=0xff; alternate->Interface.Protocol=6; alternate->Interface.NumberOfPipes=2;
    alternate->Interface.Pipes[0].EndpointAddress=0x81; alternate->Interface.Pipes[0].PipeType=UsbdPipeTypeBulk; alternate->Interface.Pipes[0].MaximumPacketSize=512;
    alternate->Interface.Pipes[1].EndpointAddress=0x01; alternate->Interface.Pipes[1].PipeType=UsbdPipeTypeBulk; alternate->Interface.Pipes[1].MaximumPacketSize=512;
    IO24_CHECK(submit_request(&device,alternate)==STATUS_SUCCESS);
    committed=device.pipe_table;
    memset(&pipe,0,sizeof(pipe)); pipe.Hdr.Function=URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL; pipe.PipeHandle=token7;
    before=io24_fake_libusb_counts()->clear_halt; IO24_CHECK(submit_request(&device,&pipe)==STATUS_SUCCESS);
    pipe.PipeHandle=old5; IO24_CHECK(submit_request(&device,&pipe)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->clear_halt==before+1);

    /* A staged replacement cannot publish its new handles.  Rollback leaves
     * the committed table pointer/token usable exactly as before. */
    io24_fake_libusb_enable_mi05_active_descriptor(0);
    select=build_two_pipe_select(config); select->ConfigurationHandle=(void *)(uintptr_t)0xfeed;
    IO24_CHECK(submit_request(&device,select)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(device.pipe_table==committed&&select->ConfigurationHandle==(void *)(uintptr_t)0xfeed);
    io24_fake_libusb_enable_mi05_active_descriptor(1); io24_fake_libusb_enable_extended_active_descriptor(1);
    pipe.PipeHandle=token7; IO24_CHECK(submit_request(&device,&pipe)==STATUS_SUCCESS);
    select=build_two_pipe_select(config);
    IO24_CHECK(submit_request(&device,select)==STATUS_SUCCESS);
    IO24_CHECK(device.pipe_table==committed);
    pipe.PipeHandle=((USBD_INTERFACE_INFORMATION *)(config+offsetof(struct _URB_SELECT_CONFIGURATION,Interface)))->Pipes[0].PipeHandle;
    before=io24_fake_libusb_counts()->clear_halt;
    IO24_CHECK(submit_request(&device,&pipe)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(finalize_claim(&device,select->ConfigurationHandle,IO24_CLAIM_TRANSACTION_ROLLBACK,&finalize)==STATUS_SUCCESS);
    IO24_CHECK(device.pipe_table==committed);
    pipe.PipeHandle=token7; IO24_CHECK(submit_request(&device,&pipe)==STATUS_SUCCESS);
    IO24_CHECK(io24_fake_libusb_counts()->clear_halt==before+1);
}

static void group_isolated_record_checks(void)
{
    struct fixture fixture;
    struct io24_function_device *device=(struct io24_function_device *)&fixture.device;
    struct io24_pipe_table *table;
    struct io24_pipe_token saved;
    struct _URB_PIPE_REQUEST request;
    HANDLE token;
    unsigned int slot, before;

    token=fixture_select_pipe(&fixture,0x81,UsbdPipeTypeBulk);
    table=device->pipe_table; slot=((uintptr_t)token&0x1ff)-1; saved=table->records[slot];
    memset(&request,0,sizeof(request)); request.Hdr.Function=URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL;
    request.PipeHandle=token; before=io24_fake_libusb_counts()->clear_halt;

    /* Root token: scope/claim are vacuous.  Interface 7's descriptor has
     * only 0x82, so deleting just descriptor-interface comparison would let
     * the MI05 0x81 descriptor spuriously validate. */
    table->records[slot].interface_number=7; table->alternates[7]=1;
    IO24_CHECK(submit_request(device,&request)==STATUS_INVALID_PARAMETER);
    table->records[slot]=saved; table->alternates[7]=0;

    /* The active alt0 has no endpoints; table current-alt agrees, isolating
     * descriptor alternate selection from the separate table-current check. */
    table->records[slot].alternate=0; table->alternates[5]=0;
    IO24_CHECK(submit_request(device,&request)==STATUS_INVALID_PARAMETER);
    table->records[slot]=saved; table->alternates[5]=1;

    /* Descriptor record is exact but committed table says a different alt. */
    table->alternates[5]=0;
    IO24_CHECK(submit_request(device,&request)==STATUS_INVALID_PARAMETER);
    table->alternates[5]=1;

    /* Function membership and committed claim are independent lower guards. */
    device->function=true; device->function_interfaces[5/8]|=1u<<(5%8);
    device->claimed_interfaces[5/8]|=1u<<(5%8);
    device->function_interfaces[5/8]&=~(1u<<(5%8));
    IO24_CHECK(submit_request(device,&request)==STATUS_INVALID_PARAMETER);
    device->function_interfaces[5/8]|=1u<<(5%8);
    device->claimed_interfaces[5/8]&=~(1u<<(5%8));
    IO24_CHECK(submit_request(device,&request)==STATUS_INVALID_PARAMETER);
    device->function=false; device->function_interfaces[5/8]=0; device->claimed_interfaces[5/8]=0;
    IO24_CHECK(io24_fake_libusb_counts()->clear_halt==before);
}
/* Task 9's generic-control route is deliberately exercised through the real
 * unixlib entry point, not a hand-written surrogate.  Until transfer.c grows
 * the corresponding upper route this group is expected to be feature RED. */
struct io24_control_fixture
{
    struct io24_function_device device;
    IRP irp;
    IO_STACK_LOCATION stack;
    URB urb;
    struct usb_submit_urb_params params;
    unsigned char storage[4098];
};

static BOOL control_select_current_alt(struct io24_control_fixture *f, UCHAR alternate)
{
    unsigned char configuration[256];
    unsigned char selection[128];
    unsigned char interfaces[] = {5};
    struct _URB_SELECT_CONFIGURATION *select;
    struct _URB_SELECT_INTERFACE *set = (void *)selection;
    struct io24_claim_transaction_request finalize;
    size_t size = offsetof(struct _URB_SELECT_INTERFACE, Interface) +
            offsetof(USBD_INTERFACE_INFORMATION, Pipes) +
            (alternate ? 2 * sizeof(USBD_PIPE_INFORMATION) : 0);

    initialize_function_device(&f->device, NULL, interfaces, ARRAY_SIZE(interfaces));
    f->params.device = (struct unix_device *)&f->device;
    io24_fake_libusb_enable_mi05_active_descriptor(1);
    select = build_select(configuration, interfaces, ARRAY_SIZE(interfaces));
    if (submit_request(&f->device, select) != STATUS_SUCCESS ||
            finalize_claim(&f->device, select->ConfigurationHandle,
            IO24_CLAIM_TRANSACTION_COMMIT, &finalize) != STATUS_SUCCESS) return FALSE;
    memset(selection, 0, sizeof(selection));
    set->Hdr.Function = URB_FUNCTION_SELECT_INTERFACE;
    set->Hdr.Length = size;
    set->Interface.Length = size - offsetof(struct _URB_SELECT_INTERFACE, Interface);
    set->Interface.InterfaceNumber = 5;
    set->Interface.AlternateSetting = alternate;
    set->Interface.Class = 0xff;
    set->Interface.Protocol = 6;
    set->Interface.NumberOfPipes = alternate ? 2 : 0;
    if (alternate)
    {
        set->Interface.Pipes[0].EndpointAddress = 0x81;
        set->Interface.Pipes[0].PipeType = UsbdPipeTypeBulk;
        set->Interface.Pipes[0].MaximumPacketSize = 512;
        set->Interface.Pipes[1].EndpointAddress = 0x01;
        set->Interface.Pipes[1].PipeType = UsbdPipeTypeBulk;
        set->Interface.Pipes[1].MaximumPacketSize = 512;
    }
    return submit_request(&f->device, set) == STATUS_SUCCESS;
}

static void reset_control(struct io24_control_fixture *f, uint8_t type,
        uint8_t request, uint16_t value, uint16_t index, ULONG length)
{
    memset(f, 0, sizeof(*f)); memset(f->storage, GUARD_BYTE, sizeof(f->storage));
    f->device.handle=(void *)(uintptr_t)0x12340000; f->device.refcount=1;
    f->device.function=true; f->device.function_interface_count=1;
    f->device.function_root=5; f->device.function_interfaces[5/8]|=1u<<(5%8);
    f->irp.Tail.Overlay.CurrentStackLocation=&f->stack;
    f->stack.Parameters.Others.Argument1=&f->urb;
    f->urb.UrbControlTransfer.Hdr.Function=URB_FUNCTION_CONTROL_TRANSFER;
    f->urb.UrbControlTransfer.Hdr.Length=sizeof(f->urb.UrbControlTransfer);
    f->urb.UrbControlTransfer.TransferBufferLength=length;
    f->urb.UrbControlTransfer.TransferBuffer=f->storage+1;
    f->urb.UrbControlTransfer.SetupPacket[0]=type;
    f->urb.UrbControlTransfer.SetupPacket[1]=request;
    f->urb.UrbControlTransfer.SetupPacket[2]=value;
    f->urb.UrbControlTransfer.SetupPacket[3]=value>>8;
    f->urb.UrbControlTransfer.SetupPacket[4]=index;
    f->urb.UrbControlTransfer.SetupPacket[5]=index>>8;
    f->urb.UrbControlTransfer.SetupPacket[6]=length;
    f->urb.UrbControlTransfer.SetupPacket[7]=length>>8;
    f->params.device=(struct unix_device *)&f->device; f->params.irp=&f->irp;
    f->params.transfer_buffer=f->storage+1; io24_fake_libusb_reset();
    IO24_CHECK(control_select_current_alt(f, 1));
}

static void expect_control_pending(struct io24_control_fixture *f, uint8_t type,
        uint8_t request, uint16_t value, uint16_t index, ULONG length, BOOL out)
{
    const struct io24_fake_counts *c;
    const struct io24_fake_record *r;
    unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE];
    unsigned int i;

    if (out) for (i=0; i<length; ++i) f->storage[1+i]=(unsigned char)(0x30+i);
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&f->params)==STATUS_PENDING);
    c=io24_fake_libusb_counts(); r=io24_fake_libusb_record();
    IO24_CHECK(c->control==1 && io24_fake_libusb_has_pending());
    IO24_CHECK(io24_fake_libusb_pending_type()==LIBUSB_TRANSFER_TYPE_CONTROL);
    IO24_CHECK(io24_fake_libusb_pending_flags() & LIBUSB_TRANSFER_FREE_BUFFER);
    IO24_CHECK(io24_fake_libusb_buffer_alloc_count()==1 &&
            io24_fake_libusb_buffer_free_count()==0 &&
            io24_fake_libusb_free_buffer_flag_count()==0);
    IO24_CHECK(io24_fake_libusb_get_setup(setup)==0);
    IO24_CHECK(setup[0]==type && setup[1]==request && setup[2]==(unsigned char)value &&
            setup[3]==(unsigned char)(value>>8) && setup[4]==(unsigned char)index &&
            setup[5]==(unsigned char)(index>>8) && setup[6]==(unsigned char)length &&
            setup[7]==(unsigned char)(length>>8));
    IO24_CHECK(r->request_type==type && r->request==request && r->value==value &&
            r->index==index && r->timeout==5000 && r->payload_length==(out?length:0));
    if (out && io24_fake_libusb_has_pending()) for (i=0; i<length; ++i)
        IO24_CHECK(r->payload[i]==(unsigned char)(0x30+i));
    IO24_CHECK(f->storage[0]==GUARD_BYTE && f->storage[length+1]==GUARD_BYTE);
    check_forbidden();
}

static void expect_control_event(struct io24_control_fixture *f,
        enum libusb_transfer_status status, const unsigned char *data,
        size_t data_length, int reported_actual, USBD_STATUS expected_status)
{
    struct usb_event event;
    struct usb_main_loop_params loop={.event=&event};
    unsigned int before_free=io24_fake_libusb_free_count();
    unsigned int before_buffer_free=io24_fake_libusb_buffer_free_count();
    IO24_CHECK(io24_fake_libusb_complete(status,data,data_length,reported_actual)==0);
    IO24_CHECK(io24_fake_libusb_reported_actual_length()==reported_actual);
    IO24_CHECK(unix_calls[unix_usb_main_loop](&loop)==STATUS_PENDING &&
            event.type==USB_EVENT_TRANSFER_COMPLETE &&
            event.u.completed_transfer.irp==&f->irp &&
            event.u.completed_transfer.transfer==f->params.transfer);
    IO24_CHECK(f->urb.UrbHeader.Status==expected_status);
    IO24_CHECK(f->irp.Tail.Overlay.DriverContext[0]==NULL);
    IO24_CHECK(!io24_fake_libusb_has_pending());
    IO24_CHECK(io24_fake_libusb_free_count()==before_free);
    IO24_CHECK(io24_fake_libusb_buffer_free_count()==before_buffer_free);
    release_transfer(event.u.completed_transfer.transfer);
    f->params.transfer = NULL;
    IO24_CHECK(io24_fake_libusb_free_count()==before_free+1);
    IO24_CHECK(io24_fake_libusb_buffer_free_count()==before_buffer_free+1 &&
            io24_fake_libusb_free_buffer_flag_count()==before_buffer_free+1);
    if (expected_status != USBD_STATUS_SUCCESS)
    {
        IO24_CHECK(f->urb.UrbControlTransfer.TransferBufferLength == 0);
    }
    IO24_CHECK(io24_fake_libusb_complete(status,data,data_length,reported_actual)==-1);
    check_forbidden();
}

static void discard_control_pending(void)
{
    unsigned int transfers = io24_fake_libusb_free_count();
    unsigned int buffers = io24_fake_libusb_buffer_free_count();

    IO24_CHECK(io24_fake_libusb_discard_pending() == 0);
    IO24_CHECK(io24_fake_libusb_free_count() == transfers + 1 &&
            io24_fake_libusb_buffer_free_count() == buffers + 1 &&
            io24_fake_libusb_free_buffer_flag_count() == buffers + 1 &&
            !io24_fake_libusb_has_pending());
}

static void add_range_scope_interfaces(struct io24_control_fixture *f)
{
    IO24_CHECK(f->device.function && f->device.function_interface_count == 1);
    IO24_CHECK(f->device.function_interfaces[0] == (1u << 5));
    f->device.function_interfaces[0] |= (1u << 0) | (1u << 1);
    f->device.function_interface_count += 2;
}

static void make_nonfunction_device(struct io24_control_fixture *f)
{
    IO24_CHECK(f->device.function && f->device.function_interface_count == 1);
    IO24_CHECK(f->device.function_root == 5);
    IO24_CHECK(f->device.function_interfaces[0] == (1u << 5));
    f->device.function = FALSE;
    f->device.function_interface_count = 0;
    f->device.function_root = 0;
    memset(f->device.function_interfaces, 0,
            sizeof(f->device.function_interfaces));
}

struct io24_backend_snapshot
{
    struct io24_fake_counts counts;
    struct io24_fake_record record;
    unsigned int alloc_count;
    unsigned int alloc_attempts;
    unsigned int submit_attempts;
    int reported_actual_length;
    BOOL pending;
};

struct io24_control_reject_snapshot
{
    struct io24_control_fixture expected;
    struct io24_pipe_table *pipe_table;
    struct io24_pipe_table pipe_table_value;
    uint64_t pipe_table_identity;
    BOOL has_pipe_table;
    BOOL captured_pipe_table;
    libusb_device_handle *device_handle;
};

static struct io24_control_reject_snapshot capture_control_reject(
        struct io24_control_fixture *f)
{
    struct io24_control_reject_snapshot snapshot;

    snapshot.expected = *f;
    snapshot.pipe_table = f->device.pipe_table;
    snapshot.has_pipe_table = snapshot.pipe_table != NULL;
    snapshot.captured_pipe_table = FALSE;
    snapshot.pipe_table_identity = 0;
    if (snapshot.has_pipe_table &&
            io24_pipe_table_audit_capture_live(snapshot.pipe_table,
            &snapshot.pipe_table_identity) == 1)
    {
        snapshot.pipe_table_value = *snapshot.pipe_table;
        snapshot.captured_pipe_table = TRUE;
    }
    snapshot.device_handle = f->device.handle;
    snapshot.expected.urb.UrbHeader.Status = USBD_STATUS_INVALID_PARAMETER;
    f->urb.UrbHeader.Status = USBD_STATUS_NOT_ACCESSED;
    return snapshot;
}

static BOOL control_reject_fixture_matches(struct io24_control_fixture *f,
        const struct io24_control_reject_snapshot *snapshot)
{
    return !memcmp(f, &snapshot->expected, sizeof(*f));
}

static BOOL control_reject_pipe_table_matches(struct io24_control_fixture *f,
        const struct io24_control_reject_snapshot *snapshot)
{
    uint64_t identity;

    if (f->device.pipe_table != snapshot->pipe_table) return FALSE;
    if (!snapshot->has_pipe_table) return TRUE;
    if (!snapshot->captured_pipe_table) return FALSE;
    if (io24_pipe_table_audit_capture_live(snapshot->pipe_table, &identity) != 1)
        return FALSE;
    if (identity != snapshot->pipe_table_identity) return FALSE;
    return !memcmp(snapshot->pipe_table, &snapshot->pipe_table_value,
            sizeof(snapshot->pipe_table_value));
}

static void expect_control_reject_snapshot(struct io24_control_fixture *f,
        const struct io24_control_reject_snapshot *snapshot)
{
    IO24_CHECK(control_reject_fixture_matches(f, snapshot));
    IO24_CHECK(control_reject_pipe_table_matches(f, snapshot));
}

static struct io24_backend_snapshot capture_control_backend(void)
{
    struct io24_backend_snapshot snapshot;

    snapshot.counts = *io24_fake_libusb_counts();
    snapshot.record = *io24_fake_libusb_record();
    snapshot.alloc_count = io24_fake_libusb_alloc_count();
    snapshot.alloc_attempts = io24_fake_libusb_alloc_attempts();
    snapshot.submit_attempts = io24_fake_libusb_submit_attempts();
    snapshot.reported_actual_length = io24_fake_libusb_reported_actual_length();
    snapshot.pending = !!io24_fake_libusb_has_pending();
    return snapshot;
}

static BOOL control_backend_matches(
        const struct io24_backend_snapshot *expected)
{
    return !memcmp(io24_fake_libusb_counts(), &expected->counts,
            sizeof(expected->counts)) && !memcmp(io24_fake_libusb_record(),
            &expected->record, sizeof(expected->record)) &&
            io24_fake_libusb_alloc_count() == expected->alloc_count &&
            io24_fake_libusb_alloc_attempts() == expected->alloc_attempts &&
            io24_fake_libusb_submit_attempts() == expected->submit_attempts &&
            io24_fake_libusb_reported_actual_length() ==
            expected->reported_actual_length &&
            !!io24_fake_libusb_has_pending() == expected->pending;
}

static BOOL control_backend_unchanged(
        const struct io24_backend_snapshot *before)
{
    return control_backend_matches(before);
}

static void expect_control_backend_unchanged(
        const struct io24_backend_snapshot *before)
{
    IO24_CHECK(control_backend_unchanged(before));
}

static void expect_control_reject(struct io24_control_fixture *f)
{
    struct io24_backend_snapshot backend = capture_control_backend();
    struct io24_control_reject_snapshot fixture = capture_control_reject(f);

    if (fixture.has_pipe_table && !fixture.captured_pipe_table)
    {
        IO24_CHECK(FALSE);
        return;
    }
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&f->params)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->control==0 && !io24_fake_libusb_has_pending());
    expect_control_backend_unchanged(&backend);
    expect_control_reject_snapshot(f, &fixture);
    IO24_CHECK(f->irp.Tail.Overlay.DriverContext[0]==NULL); check_forbidden();
}

/* Endpoint-recipient rejection performs the retained active-endpoint
 * descriptor lookup.  It is not a pre-backend generic rejection. */
static void expect_control_endpoint_reject(struct io24_control_fixture *f)
{
    struct io24_backend_snapshot expected = capture_control_backend();
    struct io24_control_reject_snapshot fixture = capture_control_reject(f);
    const struct io24_fake_record *actual;

    if (fixture.has_pipe_table && !fixture.captured_pipe_table)
    {
        IO24_CHECK(FALSE);
        return;
    }
    /* Retained endpoint validation reads exactly this active-config sequence. */
    expected.counts.api_calls += 3;
    ++expected.counts.get_device;
    ++expected.counts.get_active_config_descriptor;
    ++expected.counts.free_config_descriptor;
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&f->params)==STATUS_INVALID_PARAMETER);
    IO24_CHECK(io24_fake_libusb_counts()->control==0 && !io24_fake_libusb_has_pending());
    actual = io24_fake_libusb_record();
    IO24_CHECK(actual->get_device_ordinal == expected.counts.api_calls - 2);
    IO24_CHECK(actual->get_active_config_descriptor_ordinal == expected.counts.api_calls - 1);
    IO24_CHECK(actual->free_config_descriptor_ordinal == expected.counts.api_calls);
    IO24_CHECK(actual->get_device_handle == (uintptr_t)fixture.device_handle);
    IO24_CHECK(actual->get_device_result != 0 && actual->get_device_result ==
            actual->get_active_config_descriptor_device);
    IO24_CHECK(actual->get_active_config_descriptor_result != 0 &&
            actual->get_active_config_descriptor_result ==
            actual->free_config_descriptor_input);
    expected.record.get_device_ordinal = actual->get_device_ordinal;
    expected.record.get_active_config_descriptor_ordinal =
            actual->get_active_config_descriptor_ordinal;
    expected.record.free_config_descriptor_ordinal =
            actual->free_config_descriptor_ordinal;
    expected.record.get_device_handle = actual->get_device_handle;
    expected.record.get_device_result = actual->get_device_result;
    expected.record.get_active_config_descriptor_device =
            actual->get_active_config_descriptor_device;
    expected.record.get_active_config_descriptor_result =
            actual->get_active_config_descriptor_result;
    expected.record.free_config_descriptor_input =
            actual->free_config_descriptor_input;
    IO24_CHECK(control_backend_matches(&expected));
    expect_control_reject_snapshot(f, &fixture);
    IO24_CHECK(f->irp.Tail.Overlay.DriverContext[0]==NULL); check_forbidden();
}

static void expect_exact_range_success(struct io24_control_fixture *f,
        const unsigned char *captured, size_t captured_length)
{
    struct io24_backend_snapshot backend = capture_control_backend();
    size_t i;

    f->urb.UrbHeader.Status = USBD_STATUS_NOT_ACCESSED;
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&f->params) == STATUS_SUCCESS);
    IO24_CHECK(f->urb.UrbHeader.Status == USBD_STATUS_SUCCESS &&
            f->urb.UrbControlTransfer.TransferBufferLength == (ULONG)captured_length);
    IO24_CHECK(!memcmp(f->storage + 1, captured, captured_length));
    IO24_CHECK(f->storage[0] == GUARD_BYTE);
    for (i = captured_length + 1; i < sizeof(f->storage); ++i)
        IO24_CHECK(f->storage[i] == GUARD_BYTE);
    expect_control_backend_unchanged(&backend);
    IO24_CHECK(f->irp.Tail.Overlay.DriverContext[0] == NULL);
    check_forbidden();
}

static void expect_control_scope_reject(struct io24_control_fixture *f)
{
    struct io24_backend_snapshot backend = capture_control_backend();
    unsigned char before[sizeof(f->storage)];
    ULONG length = f->urb.UrbControlTransfer.TransferBufferLength;
    struct io24_control_reject_snapshot fixture;

    memcpy(before, f->storage, sizeof(before));
    fixture = capture_control_reject(f);
    if (fixture.has_pipe_table && !fixture.captured_pipe_table)
    {
        IO24_CHECK(FALSE);
        return;
    }
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&f->params) == STATUS_INVALID_PARAMETER);
    IO24_CHECK(f->urb.UrbHeader.Status == USBD_STATUS_INVALID_PARAMETER);
    IO24_CHECK(f->urb.UrbControlTransfer.TransferBufferLength == length);
    IO24_CHECK(!memcmp(f->storage, before, sizeof(f->storage)));
    expect_control_backend_unchanged(&backend);
    expect_control_reject_snapshot(f, &fixture);
    IO24_CHECK(f->irp.Tail.Overlay.DriverContext[0] == NULL);
    check_forbidden();
}

static void expect_control_generic_no_range(struct io24_control_fixture *f,
        BOOL out)
{
    const unsigned char *setup = f->urb.UrbControlTransfer.SetupPacket;
    ULONG length = f->urb.UrbControlTransfer.TransferBufferLength;
    unsigned char before[sizeof(f->storage)];
    unsigned int i;

    if (out) for (i = 0; i < length; ++i)
        f->storage[1 + i] = (unsigned char)(0x30 + i);
    memcpy(before, f->storage, sizeof(before));
    expect_control_pending(f, setup[0], setup[1], setup[2] | (setup[3] << 8),
            setup[4] | (setup[5] << 8), length, out);
    IO24_CHECK(!memcmp(f->storage, before, sizeof(f->storage)));
    discard_control_pending();
}

/* The generic RANGE tuple is a response optimization, not an admission
 * bypass.  Each malformed request below must be rejected before either the
 * captured payload or the backend observes it. */
static void expect_exact_range_admission_reject(struct io24_control_fixture *f,
        ULONG declared_length, const unsigned char before[sizeof(f->storage)])
{
    struct io24_backend_snapshot backend = capture_control_backend();
    struct io24_control_reject_snapshot fixture = capture_control_reject(f);

    if (fixture.has_pipe_table && !fixture.captured_pipe_table)
    {
        IO24_CHECK(FALSE);
        return;
    }
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&f->params) == STATUS_INVALID_PARAMETER);
    IO24_CHECK(f->urb.UrbHeader.Status == USBD_STATUS_INVALID_PARAMETER);
    IO24_CHECK(f->urb.UrbControlTransfer.TransferBufferLength == declared_length);
    IO24_CHECK(!memcmp(f->storage, before, sizeof(f->storage)));
    IO24_CHECK(io24_fake_libusb_counts()->control == 0 &&
            io24_fake_libusb_alloc_count() == 0 &&
            io24_fake_libusb_submit_attempts() == 0 &&
            !io24_fake_libusb_has_pending() &&
            f->irp.Tail.Overlay.DriverContext[0] == NULL);
    expect_control_backend_unchanged(&backend);
    expect_control_reject_snapshot(f, &fixture);
    check_forbidden();
}

/* Current buggy code dereferences NULL while trying to synthesize RANGE.
 * Exercise it in a child so this contract remains a feature RED, not a
 * harness crash; the fixed path must reject without touching caller storage. */
static void expect_exact_range_null_buffer_reject(void)
{
    struct io24_control_fixture f;
    struct io24_backend_snapshot backend;
    struct io24_control_reject_snapshot fixture;
    unsigned char before[sizeof(f.storage)];
    pid_t child;
    int status;

    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS | LIBUSB_RECIPIENT_INTERFACE |
            LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    memcpy(before, f.storage, sizeof(before));
    backend = capture_control_backend();
    f.params.transfer_buffer = NULL;
    fixture = capture_control_reject(&f);
    child = fork();
    IO24_CHECK(child >= 0);
    if (!child)
    {
        NTSTATUS result = unix_calls[unix_usb_submit_urb](&f.params);
        _exit(result == STATUS_INVALID_PARAMETER &&
                f.urb.UrbHeader.Status == USBD_STATUS_INVALID_PARAMETER &&
                f.urb.UrbControlTransfer.TransferBufferLength == 256 &&
                !memcmp(f.storage, before, sizeof(before)) &&
                io24_fake_libusb_counts()->control == 0 &&
                io24_fake_libusb_alloc_count() == 0 &&
                io24_fake_libusb_submit_attempts() == 0 &&
                !io24_fake_libusb_has_pending() &&
                control_backend_unchanged(&backend) &&
                control_reject_fixture_matches(&f, &fixture) &&
                control_reject_pipe_table_matches(&f, &fixture) &&
                f.irp.Tail.Overlay.DriverContext[0] == NULL ? 0 : 1);
    }
    if (child > 0)
    {
        IO24_CHECK(waitpid(child, &status, 0) == child);
        IO24_CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0);
    }
}

static void group_control_descriptor(void)
{
    struct io24_control_fixture f;
    static const unsigned char reply[]={0x91,0x92,0x93,0x94};
    static const unsigned char captured_range[50] =
    {0x04,0x00,0x44,0xac,0x00,0x00,0x44,0xac,0x00,0x00,0x00,0x00,0x00,0x00,
     0x80,0xbb,0x00,0x00,0x80,0xbb,0x00,0x00,0x00,0x00,0x00,0x00,
     0x88,0x58,0x01,0x00,0x88,0x58,0x01,0x00,0x00,0x00,0x00,0x00,
     0x00,0x77,0x01,0x00,0x00,0x77,0x01,0x00,0x00,0x00,0x00,0x00};
    static const uint8_t request_types[]={LIBUSB_REQUEST_TYPE_STANDARD,
        LIBUSB_REQUEST_TYPE_CLASS,LIBUSB_REQUEST_TYPE_VENDOR};
    static const uint8_t recipients[]={LIBUSB_RECIPIENT_DEVICE,
        LIBUSB_RECIPIENT_INTERFACE,LIBUSB_RECIPIENT_ENDPOINT,LIBUSB_RECIPIENT_OTHER};
    static const uint16_t recipient_indexes[]={0,5,0x81,0};
    unsigned int i,j;

    /* A committed claim at alternate zero has no current endpoint.  Only the
     * actual SELECT_INTERFACE path may install the endpoint map used below. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_ENDPOINT|
            LIBUSB_ENDPOINT_IN, 1, 0, 0x81, 0);
    IO24_CHECK(control_select_current_alt(&f, 0));
    expect_control_reject(&f);
    IO24_CHECK(control_select_current_alt(&f, 1));

    /* Type and recipient matrix: all legal generic requests must preserve the
     * setup packet exactly.  Interface 5 and endpoint 0x81 are the committed
     * function scope; device root and OTHER are intentionally covered too. */
    for (i=0;i<ARRAY_SIZE(request_types);++i) for (j=0;j<ARRAY_SIZE(recipients);++j)
    {
        uint8_t type=request_types[i]|recipients[j]|LIBUSB_ENDPOINT_IN;
        reset_control(&f,type,(uint8_t)(1+i*4+j),0x3412,recipient_indexes[j],0);
        expect_control_pending(&f,type,(uint8_t)(1+i*4+j),0x3412,recipient_indexes[j],0,FALSE);
        io24_fake_libusb_discard_pending();
    }
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 5, 1);
    expect_control_pending(&f, f.urb.UrbControlTransfer.SetupPacket[0], 2, 0x0100, 5, 1, FALSE); io24_fake_libusb_discard_pending();
    /* Exact generic RANGE is the same shared synthetic answer as the legacy
     * class-interface request: no allocation, submission, or pending IRP. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    expect_exact_range_success(&f, captured_range, sizeof(captured_range));
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    make_nonfunction_device(&f);
    expect_exact_range_success(&f, captured_range, sizeof(captured_range));
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    add_range_scope_interfaces(&f);
    expect_exact_range_success(&f, captured_range, sizeof(captured_range));
    /* The RANGE fast path is reached only after generic URB admission.  The
     * fixed tuple may never turn malformed headers or mismatched/undersized
     * caller declarations into a synthetic response. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN,
            2, 0x0100, 0x0500, 256);
    {
        unsigned char before[sizeof(f.storage)];
        f.urb.UrbControlTransfer.Hdr.Length--;
        memcpy(before, f.storage, sizeof(before));
        expect_exact_range_admission_reject(&f, 256, before);
    }
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN,
            2, 0x0100, 0x0500, 256);
    {
        unsigned char before[sizeof(f.storage)];
        f.urb.UrbControlTransfer.TransferBufferLength=255;
        memcpy(before, f.storage, sizeof(before));
        expect_exact_range_admission_reject(&f, 255, before);
    }
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN,
            2, 0x0100, 0x0500, 256);
    {
        unsigned char before[sizeof(f.storage)];
        f.urb.UrbControlTransfer.TransferBufferLength=sizeof(captured_range)-1;
        memcpy(before, f.storage, sizeof(before));
        expect_exact_range_admission_reject(&f, sizeof(captured_range)-1, before);
    }
    expect_exact_range_null_buffer_reject();
    /* Exercise the exact positive and every one-field RANGE miss under the
     * same three device-scope classes: non-function, function/out-of-scope,
     * and function/in-scope with the consistent {0,1,5} interface set.
     * Out-of-scope interface misses reject without backend activity; all
     * other misses route generically without synthesizing captured bytes. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE, 2, 0x0100, 0x0500, 256);
    expect_control_scope_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE, 2, 0x0100, 0x0500, 256);
    make_nonfunction_device(&f);
    expect_control_generic_no_range(&f, TRUE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE, 2, 0x0100, 0x0500, 256);
    add_range_scope_interfaces(&f);
    expect_control_generic_no_range(&f, TRUE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    expect_control_scope_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    make_nonfunction_device(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    add_range_scope_interfaces(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_DEVICE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_DEVICE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    make_nonfunction_device(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_DEVICE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 256);
    add_range_scope_interfaces(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 3, 0x0100, 0x0500, 256);
    expect_control_scope_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 3, 0x0100, 0x0500, 256);
    make_nonfunction_device(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 3, 0x0100, 0x0500, 256);
    add_range_scope_interfaces(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0101, 0x0500, 256);
    expect_control_scope_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0101, 0x0500, 256);
    make_nonfunction_device(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0101, 0x0500, 256);
    add_range_scope_interfaces(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0501, 256);
    expect_control_scope_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0501, 256);
    make_nonfunction_device(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0501, 256);
    add_range_scope_interfaces(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 255);
    expect_control_scope_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 255);
    make_nonfunction_device(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_CLASS|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 2, 0x0100, 0x0500, 255);
    add_range_scope_interfaces(&f);
    expect_control_generic_no_range(&f, FALSE);
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_ENDPOINT|LIBUSB_ENDPOINT_IN, 3, 0xabcd, 0x81, 16);
    expect_control_pending(&f, f.urb.UrbControlTransfer.SetupPacket[0], 3, 0xabcd, 0x81, 16, FALSE); io24_fake_libusb_discard_pending();
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_ENDPOINT, 3, 0xabcd, 0x01, 16);
    expect_control_pending(&f, f.urb.UrbControlTransfer.SetupPacket[0], 3, 0xabcd, 0x01, 16, TRUE); io24_fake_libusb_discard_pending();
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_OTHER|LIBUSB_ENDPOINT_IN, 4, 0, 0, 4096);
    expect_control_pending(&f, f.urb.UrbControlTransfer.SetupPacket[0], 4, 0, 0, 4096, FALSE); io24_fake_libusb_discard_pending();
    /* The interface number is the low byte of wIndex; a vendor high byte is
     * preserved on the wire but must not evade function-scope admission. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN,
            4, 0x2211, 0xab05, 16);
    expect_control_pending(&f, f.urb.UrbControlTransfer.SetupPacket[0], 4, 0x2211,
            0xab05, 16, FALSE); io24_fake_libusb_discard_pending();
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN,
            4, 0x2211, 0xab07, 16);
    expect_control_reject(&f);

    /* Submit and allocation failures balance every accepted fake allocation. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 5, 0x2211, 5, 32);
    io24_fake_libusb_set_submit_result(LIBUSB_ERROR_IO);
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&f.params)==STATUS_UNSUCCESSFUL);
    IO24_CHECK(f.urb.UrbHeader.Status==USBD_STATUS_REQUEST_FAILED && io24_fake_libusb_submit_attempts()==1 &&
            !io24_fake_libusb_has_pending() && io24_fake_libusb_alloc_count()==io24_fake_libusb_free_count() &&
            io24_fake_libusb_buffer_alloc_count()==1 && io24_fake_libusb_buffer_free_count()==1 &&
            io24_fake_libusb_free_buffer_flag_count()==1);
    check_forbidden();
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 5, 0x2211, 5, 32);
    io24_fake_libusb_set_alloc_fail_at(1);
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&f.params)==STATUS_NO_MEMORY);
    IO24_CHECK(f.urb.UrbHeader.Status==USBD_STATUS_REQUEST_FAILED && io24_fake_libusb_alloc_attempts()==1 &&
            io24_fake_libusb_alloc_count()==0 && io24_fake_libusb_free_count()==0 && !io24_fake_libusb_has_pending());
    check_forbidden();

    /* Natural IN completion is bounded by the declared transfer, while the
     * fake reports its raw backend actual length independently and safely. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 5, 0x2211, 5, 32);
    expect_control_pending(&f, f.urb.UrbControlTransfer.SetupPacket[0], 5, 0x2211, 5, 32, FALSE);
    if (io24_fake_libusb_has_pending())
    {
        expect_control_event(&f,LIBUSB_TRANSFER_COMPLETED,reply,sizeof(reply),4,USBD_STATUS_SUCCESS);
        IO24_CHECK(f.urb.UrbControlTransfer.TransferBufferLength==4 && !memcmp(f.storage+1,reply,4));
        for(i=5;i<33;++i) IO24_CHECK(f.storage[i]==GUARD_BYTE);
        counts.completions++;
    }
    check_forbidden();
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 6, 0x2211, 5, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],6,0x2211,5,32,FALSE);
    if(io24_fake_libusb_has_pending())
    {
        expect_control_event(&f,LIBUSB_TRANSFER_COMPLETED,reply,sizeof(reply),1,USBD_STATUS_SUCCESS);
        IO24_CHECK(f.urb.UrbControlTransfer.TransferBufferLength==1 && f.storage[1]==reply[0]);
        for(i=2;i<33;++i) IO24_CHECK(f.storage[i]==GUARD_BYTE);
    }
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 7, 0x2211, 5, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],7,0x2211,5,32,FALSE);
    if(io24_fake_libusb_has_pending())
    {
        expect_control_event(&f,LIBUSB_TRANSFER_COMPLETED,reply,sizeof(reply),4097,USBD_STATUS_SUCCESS);
        IO24_CHECK(f.urb.UrbControlTransfer.TransferBufferLength==32 && !memcmp(f.storage+1,reply,sizeof(reply)));
        for(i=5;i<33;++i) IO24_CHECK(f.storage[i]==0xde);
        IO24_CHECK(f.storage[0]==GUARD_BYTE && f.storage[33]==GUARD_BYTE);
    }
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 8, 0x2211, 5, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],8,0x2211,5,32,FALSE);
    if(io24_fake_libusb_has_pending()) expect_control_event(&f,LIBUSB_TRANSFER_ERROR,NULL,0,0,USBD_STATUS_REQUEST_FAILED);
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 9, 0x2211, 5, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],9,0x2211,5,32,FALSE);
    if(io24_fake_libusb_has_pending()) expect_control_event(&f,LIBUSB_TRANSFER_TIMED_OUT,NULL,0,0,USBD_STATUS_TIMEOUT);
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 10, 0x2211, 5, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],10,0x2211,5,32,FALSE);
    if(io24_fake_libusb_has_pending())
    {
        struct usb_cancel_transfer_params cancel={.transfer=f.params.transfer};
        IO24_CHECK(cancel.transfer!=NULL && unix_calls[unix_usb_cancel_transfer](&cancel)==STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->cancel==1);
        expect_control_event(&f,LIBUSB_TRANSFER_CANCELLED,NULL,0,0,USBD_STATUS_CANCELED);
    }
    /* OUT staging belongs to libusb only.  Mutating that staging must never
     * feed back into the caller's direct buffer or either guard. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_ENDPOINT, 11, 0x2211, 0x01, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],11,0x2211,0x01,32,TRUE);
    if (io24_fake_libusb_has_pending())
    {
        unsigned char caller_before[sizeof(f.storage)];
        memcpy(caller_before, f.storage, sizeof(caller_before));
        IO24_CHECK(io24_fake_libusb_mutate_pending_control_payload(0x6d) == 0);
        expect_control_event(&f,LIBUSB_TRANSFER_COMPLETED,NULL,0,32,USBD_STATUS_SUCCESS);
        IO24_CHECK(f.urb.UrbControlTransfer.TransferBufferLength == 32 &&
                !memcmp(f.storage, caller_before, sizeof(caller_before)));
    }
    /* OUT completion length is the lower-reported actual, bounded by the
     * submitted request; backend staging must remain isolated from caller
     * bytes for both short and oversized reports. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_ENDPOINT, 17, 0x2211, 0x01, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],17,0x2211,0x01,32,TRUE);
    if (io24_fake_libusb_has_pending())
    {
        unsigned char caller_before[sizeof(f.storage)];
        memcpy(caller_before, f.storage, sizeof(caller_before));
        expect_control_event(&f,LIBUSB_TRANSFER_COMPLETED,NULL,0,7,USBD_STATUS_SUCCESS);
        IO24_CHECK(f.urb.UrbControlTransfer.TransferBufferLength == 7 &&
                !memcmp(f.storage, caller_before, sizeof(caller_before)));
    }
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_ENDPOINT, 18, 0x2211, 0x01, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],18,0x2211,0x01,32,TRUE);
    if (io24_fake_libusb_has_pending())
    {
        unsigned char caller_before[sizeof(f.storage)];
        memcpy(caller_before, f.storage, sizeof(caller_before));
        expect_control_event(&f,LIBUSB_TRANSFER_COMPLETED,NULL,0,4097,USBD_STATUS_SUCCESS);
        IO24_CHECK(f.urb.UrbControlTransfer.TransferBufferLength == 32 &&
                !memcmp(f.storage, caller_before, sizeof(caller_before)));
    }
    /* Failed OUT completion may mutate only backend staging.  Caller bytes,
     * tail, and guards remain exact while every control buffer is released. */
    for (unsigned int out_failure = 0; out_failure < 3; ++out_failure)
    {
        enum libusb_transfer_status status = out_failure == 0 ? LIBUSB_TRANSFER_ERROR :
                out_failure == 1 ? LIBUSB_TRANSFER_TIMED_OUT : LIBUSB_TRANSFER_CANCELLED;
        USBD_STATUS expected = out_failure == 0 ? USBD_STATUS_REQUEST_FAILED :
                out_failure == 1 ? USBD_STATUS_TIMEOUT : USBD_STATUS_CANCELED;
        reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_ENDPOINT, 13 + out_failure,
                0x2211, 0x01, 32);
        /* This baseline is deliberately taken before submit: backend staging
         * is then mutated and completed/cancelled, so a post-submit snapshot
         * cannot hide an eager or aliasing write into the caller MDL. */
        for (unsigned int payload_i = 0; payload_i < 32; ++payload_i)
            f.storage[1 + payload_i] = (unsigned char)(0x30 + payload_i);
        unsigned char caller_before_submit[sizeof(f.storage)];
        memcpy(caller_before_submit, f.storage, sizeof(caller_before_submit));
        expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],13 + out_failure,
                0x2211,0x01,32,TRUE);
        if (io24_fake_libusb_has_pending())
        {
            IO24_CHECK(io24_fake_libusb_mutate_pending_control_payload((unsigned char)(0x71 + out_failure)) == 0);
            if (status == LIBUSB_TRANSFER_CANCELLED)
            {
                struct usb_cancel_transfer_params cancel={.transfer=f.params.transfer};
                IO24_CHECK(cancel.transfer && unix_calls[unix_usb_cancel_transfer](&cancel)==STATUS_SUCCESS &&
                        io24_fake_libusb_counts()->cancel==1);
            }
            expect_control_event(&f,status,NULL,0,0,expected);
            IO24_CHECK(f.urb.UrbControlTransfer.TransferBufferLength == 0);
            IO24_CHECK(!memcmp(f.storage, caller_before_submit, sizeof(caller_before_submit)));
            IO24_CHECK(f.storage[0] == GUARD_BYTE && f.storage[33] == GUARD_BYTE);
        }
    }
    reset_control(&f, LIBUSB_REQUEST_TYPE_VENDOR|LIBUSB_RECIPIENT_INTERFACE|LIBUSB_ENDPOINT_IN, 12, 0x2211, 5, 32);
    expect_control_pending(&f,f.urb.UrbControlTransfer.SetupPacket[0],12,0x2211,5,32,FALSE);
    if (io24_fake_libusb_has_pending()) discard_control_pending();

    /* Shape and scope rejects must fail before any backend allocation/submit. */
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_DEVICE, 1,0,0,4097); expect_control_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_DEVICE, 1,0,0,1); f.urb.UrbControlTransfer.SetupPacket[6]=2; expect_control_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_DEVICE, 1,0,0,1); f.params.transfer_buffer=NULL; expect_control_reject(&f);
    reset_control(&f, 0x60|LIBUSB_RECIPIENT_DEVICE, 1,0,0,0); expect_control_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|0x04, 1,0,0,0); expect_control_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_INTERFACE, 1,0,7,0); expect_control_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_ENDPOINT, 1,0,0x82,0); expect_control_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_ENDPOINT|LIBUSB_ENDPOINT_IN, 1,0,0x01,0); expect_control_endpoint_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_ENDPOINT, 1,0,0x81,0); expect_control_endpoint_reject(&f);
    reset_control(&f, LIBUSB_REQUEST_TYPE_STANDARD|LIBUSB_RECIPIENT_ENDPOINT|LIBUSB_ENDPOINT_IN, 1,0,0x81,0);
    f.device.function_interfaces[5/8]&=~(1u<<(5%8)); expect_control_endpoint_reject(&f);
}
static void group_sync_pipes(void)
{
    struct fixture f; struct _URB_PIPE_REQUEST *r; HANDLE pipe;
    struct _URB_BULK_OR_INTERRUPT_TRANSFER *bulk;
    const struct io24_fake_counts *c;

    pipe = fixture_select_pipe(&f, 0x81, UsbdPipeTypeBulk);
    f.urb.UrbHeader.Function = URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL;
    r = &f.urb.UrbPipeRequest; r->PipeHandle = pipe;
    io24_fake_libusb_set_clear_halt_result(LIBUSB_ERROR_NOT_FOUND);
    IO24_CHECK(submit_fixture(&f) == STATUS_UNSUCCESSFUL);
    IO24_CHECK(r->Hdr.Status == USBD_STATUS_REQUEST_FAILED);
    c = io24_fake_libusb_counts();
    IO24_CHECK(c->clear_halt == 1 &&
            io24_fake_libusb_record()->endpoint == 0x81);
    check_forbidden();

    pipe = fixture_select_pipe(&f, 0x81, UsbdPipeTypeBulk);
    f.urb.UrbHeader.Function = URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    bulk = &f.urb.UrbBulkOrInterruptTransfer;
    bulk->PipeHandle = pipe;
    bulk->TransferFlags = USBD_TRANSFER_DIRECTION_IN | USBD_SHORT_TRANSFER_OK;
    bulk->TransferBufferLength = 32;
    bulk->TransferBuffer = f.buffer;
    io24_fake_libusb_set_submit_result(LIBUSB_ERROR_BUSY);
    IO24_CHECK(submit_fixture(&f) == STATUS_UNSUCCESSFUL);
    IO24_CHECK(bulk->Hdr.Status == USBD_STATUS_REQUEST_FAILED &&
            f.irp.Tail.Overlay.DriverContext[0] == NULL &&
            io24_fake_libusb_alloc_count() == 1 &&
            io24_fake_libusb_free_count() == 1 &&
            !io24_fake_libusb_has_pending());
    check_forbidden();
}
static void group_transfer_lifetime(void)
{
    struct fixture f, natural; struct _URB_BULK_OR_INTERRUPT_TRANSFER *r;
    HANDLE pipe; struct usb_cancel_transfer_params cancel;
    struct usb_event event; struct usb_main_loop_params loop = {.event = &event};
    const struct io24_fake_counts *c; unsigned char payload[32];

    pipe = fixture_select_pipe(&f, 0x81, UsbdPipeTypeBulk);
    f.urb.UrbHeader.Function = URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    r = &f.urb.UrbBulkOrInterruptTransfer; r->PipeHandle = pipe;
    r->TransferBufferLength = 32; r->TransferBuffer = f.buffer;
    IO24_CHECK(submit_fixture(&f) == STATUS_PENDING);
    cancel.transfer = f.params.transfer;
    IO24_CHECK(cancel.transfer != NULL);
    IO24_CHECK(unix_calls[unix_usb_cancel_transfer](&cancel) == STATUS_SUCCESS);
    IO24_CHECK(unix_calls[unix_usb_cancel_transfer](&cancel) == STATUS_SUCCESS);
    c = io24_fake_libusb_counts(); IO24_CHECK(c->cancel == 1);
    IO24_CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_CANCELLED,
            NULL, 0, 0) == 0);
    c = io24_fake_libusb_counts();
    {
        unsigned int cancel_count = c->cancel;
        IO24_CHECK(unix_calls[unix_usb_cancel_transfer](&cancel) == STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->cancel == cancel_count);
    }
    IO24_CHECK(unix_calls[unix_usb_main_loop](&loop) == STATUS_PENDING &&
            event.type == USB_EVENT_TRANSFER_COMPLETE &&
            event.u.completed_transfer.irp == &f.irp &&
            event.u.completed_transfer.transfer == f.params.transfer);
    IO24_CHECK(io24_fake_libusb_free_count() == 0);
    release_transfer(event.u.completed_transfer.transfer);
    f.params.transfer = NULL;
    IO24_CHECK(io24_fake_libusb_free_count() == 1);
    counts.completions++; IO24_CHECK(f.irp.Tail.Overlay.DriverContext[0] == NULL);
    check_forbidden();

    memset(payload, 0x6d, sizeof(payload));
    pipe = fixture_select_pipe(&natural, 0x81, UsbdPipeTypeBulk);
    natural.urb.UrbHeader.Function = URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    r = &natural.urb.UrbBulkOrInterruptTransfer; r->PipeHandle = pipe;
    r->TransferBufferLength = 32; r->TransferBuffer = natural.buffer;
    IO24_CHECK(submit_fixture(&natural) == STATUS_PENDING);
    IO24_CHECK(io24_fake_libusb_pending_type() == LIBUSB_TRANSFER_TYPE_BULK &&
            io24_fake_libusb_pending_length() == 32);
    IO24_CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_COMPLETED,
            payload, sizeof(payload), 32) == 0);
    cancel.transfer = natural.params.transfer;
    c = io24_fake_libusb_counts();
    {
        unsigned int cancel_count = c->cancel;
        IO24_CHECK(unix_calls[unix_usb_cancel_transfer](&cancel) == STATUS_SUCCESS);
        IO24_CHECK(io24_fake_libusb_counts()->cancel == cancel_count);
    }
    IO24_CHECK(unix_calls[unix_usb_main_loop](&loop) == STATUS_PENDING &&
            event.u.completed_transfer.irp == &natural.irp &&
            event.u.completed_transfer.transfer == natural.params.transfer);
    IO24_CHECK(!memcmp(natural.buffer, payload, sizeof(payload)));
    IO24_CHECK(natural.urb.UrbBulkOrInterruptTransfer.TransferBufferLength == 32);
    IO24_CHECK(io24_fake_libusb_free_count() == 0);
    release_transfer(event.u.completed_transfer.transfer);
    natural.params.transfer = NULL;
    IO24_CHECK(io24_fake_libusb_free_count() == 1);
    counts.completions++; check_forbidden();
}
static void run(const char*m){if(!strcmp(m,"--red")||!strcmp(m,"--claims"))group_claims();if(!strcmp(m,"--red")||!strcmp(m,"--alternate")){group_alternate();group_atomicity();group_target_only();group_isolated_record_checks();}if(!strcmp(m,"--red")||!strcmp(m,"--control-descriptor"))group_control_descriptor();if(!strcmp(m,"--red")||!strcmp(m,"--sync-pipes"))group_sync_pipes();if(!strcmp(m,"--red")||!strcmp(m,"--transfer-lifetime"))group_transfer_lifetime();}
int main(int argc,char**argv)
{
    void *module;
    char *retained_argv[3];
    int retained_result;
    unsigned int retained_failures = 0;

    if(argc!=3)return 2;
    retained_argv[0]=argv[0];retained_argv[1]=argv[1];retained_argv[2]=NULL;
    retained_result=io24_retained_pipe_main(2,retained_argv);
    if(retained_result)
    {
        if(retained_result!=1||!failures)
        {
            fprintf(stderr,"HARNESS: retained pipe execution baseline failed\n");
            return 2;
        }
        retained_failures=failures;
    }
    module=dlopen(argv[1],RTLD_NOW|RTLD_GLOBAL);
    if(!module){fprintf(stderr,"HARNESS: dlopen actual unixlib: %s\n",dlerror());return 2;}
    unix_calls=dlsym(module,"__wine_unix_call_funcs");
    if(!unix_calls){fprintf(stderr,"HARNESS: dlsym actual unix calls: %s\n",dlerror());return 2;}
    counts.failures+=retained_failures;
    run(argv[2]);
    dlclose(module);
    printf("CP33 lower executed mode=%s completions=%u failures=%u\n",argv[2],counts.completions,counts.failures);
    return counts.failures?1:0;
}
