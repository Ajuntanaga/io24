/* Executed CP33 lower contract using actual unixlib.c and fake libusb. */
#define main io24_retained_pipe_main
#include "wineusb_pipe_observe_contract.c"
#undef main

#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)
struct io24_fake_counts { unsigned claim,release,detach,auto_detach,set_configuration,set_alternate,control,bulk,interrupt,cancel,clear_halt,transfer_free,close; };
struct io24_fake_record { int interface_number,alternate,configuration; unsigned char endpoint,type; int length; uint8_t request_type,request; uint16_t value,index; };
const struct io24_fake_counts *io24_fake_libusb_counts(void);
const struct io24_fake_record *io24_fake_libusb_record(void);
void io24_fake_libusb_set_claim_result(int);
void io24_fake_libusb_set_claim_failure(unsigned int,int);
void io24_fake_libusb_set_alternate_result(int);
int io24_fake_libusb_complete(enum libusb_transfer_status,const unsigned char*,size_t,int);
int io24_fake_libusb_claim_at(unsigned int);
int io24_fake_libusb_release_at(unsigned int);

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
    unsigned char claimed_interfaces[32]; void *pending_claim_transaction;
};

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
        cursor+=information->Length;
    }
    select->Hdr.Length=cursor;
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

static void group_claims(void)
{
    static const unsigned char mi05[]={5}, multi[]={7,2,5}, bad_scope[]={2,9};
    struct io24_function_device device;
    struct io24_claim_transaction_request finalize;
    struct _URB_SELECT_CONFIGURATION *select;
    const struct io24_fake_counts *c;
    USBD_CONFIGURATION_HANDLE first,second;
    unsigned char buffer[256];

    io24_fake_libusb_reset();
    initialize_function_device(&device,NULL,mi05,ARRAY_SIZE(mi05));
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

    io24_fake_libusb_reset();
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

    io24_fake_libusb_reset();
    initialize_function_device(&device,NULL,multi,ARRAY_SIZE(multi));
    select=build_select(buffer,multi,ARRAY_SIZE(multi));
    io24_fake_libusb_set_claim_failure(1,LIBUSB_ERROR_BUSY);
    IO24_CHECK(submit_request(&device,select)==STATUS_DEVICE_BUSY);
    IO24_CHECK(select->Hdr.Status==USBD_STATUS_REQUEST_FAILED);
    IO24_CHECK(io24_fake_libusb_counts()->claim==1&&io24_fake_libusb_counts()->release==0);
    check_forbidden();

    /* A nonempty explicit rollback releases only its journal in reverse order.
     * A later partial extension must preserve the earlier committed claim. */
    io24_fake_libusb_reset();
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

    io24_fake_libusb_reset();
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

    io24_fake_libusb_reset();
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
}
static void group_alternate(void)
{
    struct fixture f; struct _URB_SELECT_INTERFACE *r; const struct io24_fake_counts*c;
    reset_fixture(&f,URB_FUNCTION_SELECT_INTERFACE);r=&f.urb.UrbSelectInterface;r->Hdr.Length=sizeof(*r);r->Interface.Length=sizeof(r->Interface);r->Interface.InterfaceNumber=5;r->Interface.AlternateSetting=1;r->Interface.NumberOfPipes=2;r->Interface.Pipes[0].EndpointAddress=0x81;r->Interface.Pipes[0].PipeType=UsbdPipeTypeBulk;r->Interface.Pipes[1].EndpointAddress=0x01;r->Interface.Pipes[1].PipeType=UsbdPipeTypeBulk;
    IO24_CHECK(submit_fixture(&f)==STATUS_SUCCESS);c=io24_fake_libusb_counts();IO24_CHECK(c->set_alternate==1);IO24_CHECK(io24_fake_libusb_record()->interface_number==5&&io24_fake_libusb_record()->alternate==1);check_forbidden();
}
static void group_control_descriptor(void)
{
    struct io24_function_device device; IRP irp; IO_STACK_LOCATION stack; URB urb; unsigned char guarded[34]; struct usb_submit_urb_params params; const struct io24_fake_counts*c;
    memset(&device,0,sizeof(device));memset(&irp,0,sizeof(irp));memset(&stack,0,sizeof(stack));memset(&urb,0,sizeof(urb));memset(guarded,GUARD_BYTE,sizeof(guarded));memset(&params,0,sizeof(params));
    device.handle=(void*)(uintptr_t)0x12340000;device.refcount=1;device.function=true;device.function_interface_count=1;device.function_root=5;device.function_interfaces[5/8]|=1u<<(5%8);
    irp.Tail.Overlay.CurrentStackLocation=&stack;stack.Parameters.Others.Argument1=&urb;urb.UrbControlVendorClassRequest.Hdr.Function=URB_FUNCTION_VENDOR_INTERFACE;urb.UrbControlVendorClassRequest.Hdr.Length=sizeof(urb.UrbControlVendorClassRequest);urb.UrbControlVendorClassRequest.TransferFlags=USBD_TRANSFER_DIRECTION_IN;urb.UrbControlVendorClassRequest.TransferBufferLength=32;urb.UrbControlVendorClassRequest.Request=1;urb.UrbControlVendorClassRequest.Index=4;params.device=(struct unix_device*)&device;params.irp=&irp;params.transfer_buffer=guarded+1;io24_fake_libusb_reset();
    IO24_CHECK(unix_calls[unix_usb_submit_urb](&params)==STATUS_INVALID_PARAMETER);c=io24_fake_libusb_counts();IO24_CHECK(c->control==0);IO24_CHECK(guarded[0]==GUARD_BYTE&&guarded[33]==GUARD_BYTE);check_forbidden();if(io24_fake_libusb_has_pending())io24_fake_libusb_discard_pending();
}
static void group_sync_pipes(void)
{
    struct fixture f;struct _URB_PIPE_REQUEST*r;const struct io24_fake_counts*c;reset_fixture(&f,URB_FUNCTION_SYNC_RESET_PIPE_AND_CLEAR_STALL);r=&f.urb.UrbPipeRequest;r->PipeHandle=make_pipe_handle(0x81,UsbdPipeTypeBulk);io24_fake_libusb_set_clear_halt_result(LIBUSB_ERROR_NOT_FOUND);IO24_CHECK(submit_fixture(&f)==STATUS_UNSUCCESSFUL);c=io24_fake_libusb_counts();IO24_CHECK(c->clear_halt==1&&io24_fake_libusb_record()->endpoint==0x81);check_forbidden();
}
static void group_transfer_lifetime(void)
{
    struct fixture f,natural;struct _URB_BULK_OR_INTERRUPT_TRANSFER*r;struct usb_cancel_transfer_params cancel;struct usb_event event;struct usb_main_loop_params loop={.event=&event};const struct io24_fake_counts*c;unsigned char payload[32];
    reset_fixture(&f,URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER);r=&f.urb.UrbBulkOrInterruptTransfer;r->PipeHandle=make_pipe_handle(0x81,UsbdPipeTypeBulk);r->TransferBufferLength=32;r->TransferBuffer=f.buffer;IO24_CHECK(submit_fixture(&f)==STATUS_PENDING);cancel.transfer=f.irp.Tail.Overlay.DriverContext[0];IO24_CHECK(cancel.transfer!=NULL);IO24_CHECK(unix_calls[unix_usb_cancel_transfer](&cancel)==STATUS_SUCCESS);c=io24_fake_libusb_counts();IO24_CHECK(c->cancel==1);IO24_CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_CANCELLED,NULL,0,0)==0);IO24_CHECK(unix_calls[unix_usb_main_loop](&loop)==STATUS_PENDING&&event.type==USB_EVENT_TRANSFER_COMPLETE&&event.u.completed_irp==&f.irp);counts.completions++;IO24_CHECK(f.irp.Tail.Overlay.DriverContext[0]==NULL);check_forbidden();
    memset(payload,0x6d,sizeof(payload));reset_fixture(&natural,URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER);r=&natural.urb.UrbBulkOrInterruptTransfer;r->PipeHandle=make_pipe_handle(0x81,UsbdPipeTypeBulk);r->TransferBufferLength=32;r->TransferBuffer=natural.buffer;IO24_CHECK(submit_fixture(&natural)==STATUS_PENDING);IO24_CHECK(io24_fake_libusb_pending_type()==LIBUSB_TRANSFER_TYPE_BULK&&io24_fake_libusb_pending_length()==32);IO24_CHECK(io24_fake_libusb_complete(LIBUSB_TRANSFER_COMPLETED,payload,sizeof(payload),32)==0);IO24_CHECK(unix_calls[unix_usb_main_loop](&loop)==STATUS_PENDING&&event.u.completed_irp==&natural.irp);IO24_CHECK(!memcmp(natural.buffer,payload,sizeof(payload)));IO24_CHECK(natural.urb.UrbBulkOrInterruptTransfer.TransferBufferLength==32);counts.completions++;check_forbidden();
}
static void run(const char*m){if(!strcmp(m,"--red")||!strcmp(m,"--claims"))group_claims();if(!strcmp(m,"--red")||!strcmp(m,"--alternate"))group_alternate();if(!strcmp(m,"--red")||!strcmp(m,"--control-descriptor"))group_control_descriptor();if(!strcmp(m,"--red")||!strcmp(m,"--sync-pipes"))group_sync_pipes();if(!strcmp(m,"--red")||!strcmp(m,"--transfer-lifetime"))group_transfer_lifetime();}
int main(int argc,char**argv){void*module;char*retained_argv[3];if(argc!=3)return 2;retained_argv[0]=argv[0];retained_argv[1]=argv[1];retained_argv[2]=NULL;if(io24_retained_pipe_main(2,retained_argv)){fprintf(stderr,"HARNESS: retained pipe execution baseline failed\n");return 2;}module=dlopen(argv[1],RTLD_NOW|RTLD_GLOBAL);if(!module){fprintf(stderr,"HARNESS: dlopen actual unixlib: %s\n",dlerror());return 2;}unix_calls=dlsym(module,"__wine_unix_call_funcs");if(!unix_calls){fprintf(stderr,"HARNESS: dlsym actual unix calls: %s\n",dlerror());return 2;}run(argv[2]);dlclose(module);printf("CP33 lower executed mode=%s completions=%u failures=%u\n",argv[2],counts.completions,counts.failures);return counts.failures?1:0;}
