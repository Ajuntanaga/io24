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
void io24_fake_libusb_set_alternate_result(int);
int io24_fake_libusb_complete(enum libusb_transfer_status,const unsigned char*,size_t,int);

struct io24_function_device
{
    struct list entry; libusb_device_handle *handle; void *parent; unsigned int refcount;
    bool function; uint8_t function_interface_count; uint16_t configuration_length;
    uint8_t function_root; unsigned char function_interfaces[32];
};

static void check_forbidden(void)
{
    const struct io24_fake_counts *c=io24_fake_libusb_counts();
    IO24_CHECK(c->detach==0&&c->auto_detach==0&&c->set_configuration==0);
}
static void group_claims(void)
{
    struct fixture f; struct _URB_SELECT_CONFIGURATION *r; const struct io24_fake_counts*c;
    reset_fixture(&f,URB_FUNCTION_SELECT_CONFIGURATION); r=&f.urb.UrbSelectConfiguration;
    r->Hdr.Length=sizeof(*r);r->Interface.Length=sizeof(r->Interface);r->Interface.InterfaceNumber=5;r->Interface.AlternateSetting=0;r->Interface.NumberOfPipes=0;
    IO24_CHECK(submit_fixture(&f)==STATUS_SUCCESS);c=io24_fake_libusb_counts();IO24_CHECK(c->claim==1&&c->release==0);check_forbidden();
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
