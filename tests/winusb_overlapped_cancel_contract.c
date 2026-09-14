/* Executed cancellation contract for actual wineusb.c and unixlib.c paths. */
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ntstatus.h"
#include "windef.h"
#include "winternl.h"
#include "ddk/wdm.h"
#include "ddk/usb.h"
#include "wine/debug.h"
#undef WINE_DEFAULT_DEBUG_CHANNEL
#undef TRACE
#undef WARN
#undef ERR
#undef FIXME
#define WINE_DEFAULT_DEBUG_CHANNEL(name)
#define TRACE(...) ((void)0)
#define WARN(...) ((void)0)
#define ERR(...) ((void)0)
#define FIXME(...) ((void)0)
#undef DEVICE_TYPE
#include "wineusb.c"

#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations,frees,submits,cancels,releases,completions,failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)
typedef NTSTATUS (*io24_unix_entry_t)(void *);
static const io24_unix_entry_t *real_unix_calls;
static char order[128];
static void *expected_cancel_transfer;
static struct usb_device *cancel_during_submit_device;
static IRP *cancel_during_submit_irp;
static IRP *complete_during_cancel_irp;
static BOOL complete_during_submit;
static unsigned int cancel_during_submit_phase;
unsigned int io24_fake_libusb_cancel_count(void);

unixlib_handle_t __wine_unixlib_handle=1;
static NTSTATUS WINAPI fake_dispatch(unixlib_handle_t h,unsigned int code,void*args)
{
    NTSTATUS status;unsigned int before,after;(void)h;
    if(code==unix_usb_cancel_transfer)
    {
        struct usb_cancel_transfer_params *params=args;
        (void)before; (void)after; status=STATUS_SUCCESS;
        strcat(order,"cancel,");IO24_CHECK(params->transfer==expected_cancel_transfer);
        counts.cancels++;
        if(complete_during_cancel_irp)
        {
            IRP *irp=complete_during_cancel_irp;
            complete_during_cancel_irp=NULL;
            complete_irp(irp,params->transfer);
        }
        return status;
    }
    if(code==unix_usb_submit_urb)
    {
        struct usb_submit_urb_params*p=args;
        counts.submits++;
        if(cancel_during_submit_phase==1&&cancel_during_submit_device&&cancel_during_submit_irp)
            usb_submit_urb(cancel_during_submit_device,cancel_during_submit_irp);
        p->transfer=(void*)(uintptr_t)0x7000;
        if(cancel_during_submit_phase==2&&cancel_during_submit_device&&cancel_during_submit_irp)
            usb_submit_urb(cancel_during_submit_device,cancel_during_submit_irp);
        if(complete_during_submit)complete_irp(p->irp,p->transfer);
        return STATUS_PENDING;
    }
    if(code==unix_usb_release_transfer){counts.releases++;strcat(order,"release,");return STATUS_SUCCESS;}
    if(code==unix_usb_destroy_device)return STATUS_SUCCESS;
    return real_unix_calls?real_unix_calls[code](args):STATUS_SUCCESS;
}
NTSTATUS (WINAPI *__wine_unix_call_dispatcher)(unixlib_handle_t,unsigned int,void*)=fake_dispatch;
NTSTATUS WINAPI __wine_init_unix_call(void){return STATUS_SUCCESS;}

void WINAPI EnterCriticalSection(CRITICAL_SECTION*c){(void)c;} void WINAPI LeaveCriticalSection(CRITICAL_SECTION*c){(void)c;}
HANDLE WINAPI CreateThread(SECURITY_ATTRIBUTES*a,SIZE_T s,LPTHREAD_START_ROUTINE f,void*p,DWORD flags,DWORD*id){(void)a;(void)s;(void)f;(void)p;(void)flags;if(id)*id=1;return (HANDLE)(uintptr_t)1;}
DWORD WINAPI WaitForSingleObject(HANDLE h,DWORD t){(void)h;(void)t;return 0;} BOOL WINAPI CloseHandle(HANDLE h){(void)h;return TRUE;}
PVOID WINAPI ExAllocatePool(POOL_TYPE t,SIZE_T n){(void)t;counts.allocations++;return calloc(1,n);} VOID WINAPI ExFreePool(PVOID p){if(p){counts.frees++;free(p);}}
VOID WINAPI IoCompleteRequest(PIRP irp,UCHAR b){(void)irp;(void)b;strcat(order,"complete,");counts.completions++;}
VOID WINAPI IoDeleteDevice(PDEVICE_OBJECT d){(void)d;} VOID WINAPI IoDetachDevice(PDEVICE_OBJECT d){(void)d;} VOID WINAPI IoInvalidateDeviceRelations(PDEVICE_OBJECT d,DEVICE_RELATION_TYPE t){(void)d;(void)t;}
PDEVICE_OBJECT WINAPI IoAttachDeviceToDeviceStack(PDEVICE_OBJECT a,PDEVICE_OBJECT b){(void)a;return b;} NTSTATUS WINAPI IoCallDriver(PDEVICE_OBJECT d,PIRP i){(void)d;return i->IoStatus.Status;}
NTSTATUS WINAPI IoCreateDevice(PDRIVER_OBJECT d,ULONG e,PUNICODE_STRING n,DEVICE_TYPE t,ULONG c,BOOLEAN x,PDEVICE_OBJECT*out){(void)n;(void)t;(void)c;(void)x;*out=calloc(1,sizeof(**out));if(!*out)return STATUS_NO_MEMORY;(*out)->DriverObject=d;(*out)->DeviceExtension=calloc(1,e?e:1);return STATUS_SUCCESS;}
PVOID WINAPI MmMapLockedPagesSpecifyCache(PMDL m,KPROCESSOR_MODE a,MEMORY_CACHING_TYPE c,PVOID p,ULONG b,MM_PAGE_PRIORITY q){(void)a;(void)c;(void)p;(void)b;(void)q;return m?(void *)m->StartVa:NULL;}
void FASTCALL ObfReferenceObject(void*o){(void)o;} BOOL WINAPI IsBadStringPtrW(LPCWSTR s,UINT_PTR n){(void)s;(void)n;return FALSE;}
VOID WINAPI RtlInitUnicodeString(PUNICODE_STRING s,PCWSTR p){s->Buffer=(WCHAR*)p;s->Length=0;s->MaximumLength=0;}
int _vsnwprintf(WCHAR*b,size_t n,const WCHAR*f,va_list a){(void)b;(void)n;(void)f;(void)a;return 0;}
bool wineusb_ms_os_10_build_pnp_ids(const char a[WINEUSB_MS_OS_10_SOURCE_ID_SIZE],const char b[WINEUSB_MS_OS_10_SOURCE_ID_SIZE],struct wineusb_ms_os_10_pnp_ids*i){(void)a;(void)b;(void)i;return false;}
NTSTATUS wineusb_ms_os_10_get_device_interface_guid(const struct wineusb_ms_os_10_metadata_source*c,GUID*g){(void)c;(void)g;return STATUS_NOT_SUPPORTED;}
NTSTATUS wineusb_query_ms_os_10_metadata_interface(const GUID*g,USHORT s,USHORT v,INTERFACE*i,void*c,const struct wineusb_ms_os_10_metadata_routines*r){(void)g;(void)s;(void)v;(void)i;(void)c;(void)r;return STATUS_NOT_SUPPORTED;}
NTSTATUS wineusb_query_usbdi_interface(const GUID*g,USHORT s,USHORT v,INTERFACE*i,void*c,const struct wineusb_usbdi_routines*r){(void)g;(void)s;(void)v;(void)i;(void)c;(void)r;return STATUS_NOT_SUPPORTED;}

struct pending_fixture { IRP irp; IO_STACK_LOCATION stack; URB urb; unsigned char guarded[34]; };
static void prepare_device(struct usb_device*d,DEVICE_OBJECT*o)
{memset(d,0,sizeof(*d));memset(o,0,sizeof(*o));o->DeviceExtension=d;d->device_obj=o;d->unix_device=(void*)(uintptr_t)0x12340000;InitializeListHead(&d->irp_list);list_init(&d->entry);list_add_tail(&device_list,&d->entry);}
static void prepare_bulk(struct pending_fixture *f,HANDLE pipe)
{
    memset(f,0,sizeof(*f));
    memset(f->guarded,GUARD_BYTE,sizeof(f->guarded));
    f->irp.Tail.Overlay.CurrentStackLocation=&f->stack;
    f->stack.Parameters.DeviceIoControl.IoControlCode=IOCTL_INTERNAL_USB_SUBMIT_URB;
    f->stack.Parameters.Others.Argument1=&f->urb;
    f->urb.UrbBulkOrInterruptTransfer.Hdr.Function=URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    f->urb.UrbBulkOrInterruptTransfer.PipeHandle=pipe;
    f->urb.UrbBulkOrInterruptTransfer.TransferBufferLength=32;
    f->urb.UrbBulkOrInterruptTransfer.TransferBuffer=f->guarded+1;
}
static void prepare_abort(struct pending_fixture *f,HANDLE pipe)
{
    memset(f,0,sizeof(*f));
    f->irp.Tail.Overlay.CurrentStackLocation=&f->stack;
    f->stack.Parameters.Others.Argument1=&f->urb;
    f->urb.UrbPipeRequest.Hdr.Function=URB_FUNCTION_ABORT_PIPE;
    f->urb.UrbPipeRequest.PipeHandle=pipe;
}
static void group_kernel_lifetime(void)
{
    struct usb_device d;DEVICE_OBJECT o;
    struct pending_fixture natural,early,cancelled,publishing,racing,abort;
    unsigned int allocations,frees,releases,completions,cancels;
    HANDLE pipe=(HANDLE)(uintptr_t)0x281;

    prepare_device(&d,&o);
    allocations=counts.allocations;frees=counts.frees;releases=counts.releases;
    completions=counts.completions;
    prepare_bulk(&natural,pipe);
    IO24_CHECK(driver_internal_ioctl(&o,&natural.irp)==STATUS_PENDING);
    IO24_CHECK(!IsListEmpty(&d.irp_list)&&natural.irp.Tail.Overlay.DriverContext[0]);
    complete_irp(&natural.irp,(void*)(uintptr_t)0x7000);
    IO24_CHECK(IsListEmpty(&d.irp_list)&&!natural.irp.Tail.Overlay.DriverContext[0]);
    IO24_CHECK(counts.allocations==allocations+1&&counts.frees==frees+1&&
            counts.releases==releases+1&&counts.completions==completions+1);

    allocations=counts.allocations;frees=counts.frees;releases=counts.releases;
    completions=counts.completions;prepare_bulk(&early,pipe);complete_during_submit=TRUE;
    IO24_CHECK(driver_internal_ioctl(&o,&early.irp)==STATUS_PENDING);
    complete_during_submit=FALSE;
    IO24_CHECK(IsListEmpty(&d.irp_list)&&!early.irp.Tail.Overlay.DriverContext[0]);
    IO24_CHECK(counts.allocations==allocations+1&&counts.frees==frees+1&&
            counts.releases==releases+1&&counts.completions==completions+1);

    allocations=counts.allocations;frees=counts.frees;releases=counts.releases;
    completions=counts.completions;cancels=counts.cancels;
    prepare_bulk(&cancelled,pipe);prepare_abort(&abort,pipe);
    cancel_during_submit_device=&d;cancel_during_submit_irp=&abort.irp;
    cancel_during_submit_phase=1;
    expected_cancel_transfer=(void*)(uintptr_t)0x7000;
    IO24_CHECK(driver_internal_ioctl(&o,&cancelled.irp)==STATUS_PENDING);
    cancel_during_submit_device=NULL;cancel_during_submit_irp=NULL;
    cancel_during_submit_phase=0;
    IO24_CHECK(counts.cancels==cancels+1);
    IO24_CHECK(usb_submit_urb(&d,&abort.irp)==STATUS_SUCCESS);
    IO24_CHECK(counts.cancels==cancels+1);
    complete_during_cancel_irp=&cancelled.irp;
    /* The already-issued cancel owns a reference until this synthetic
     * callback is consumed; a duplicate abort must not issue another one. */
    complete_irp(&cancelled.irp,(void*)(uintptr_t)0x7000);
    complete_during_cancel_irp=NULL;
    IO24_CHECK(IsListEmpty(&d.irp_list)&&!cancelled.irp.Tail.Overlay.DriverContext[0]);
    IO24_CHECK(counts.allocations==allocations+1&&counts.frees==frees+1&&
            counts.releases==releases+1&&counts.completions==completions+1);

    allocations=counts.allocations;frees=counts.frees;releases=counts.releases;
    completions=counts.completions;cancels=counts.cancels;
    prepare_bulk(&publishing,pipe);prepare_abort(&abort,pipe);
    cancel_during_submit_device=&d;cancel_during_submit_irp=&abort.irp;
    cancel_during_submit_phase=2;
    expected_cancel_transfer=(void*)(uintptr_t)0x7000;
    IO24_CHECK(driver_internal_ioctl(&o,&publishing.irp)==STATUS_PENDING);
    cancel_during_submit_device=NULL;cancel_during_submit_irp=NULL;
    cancel_during_submit_phase=0;
    IO24_CHECK(counts.cancels==cancels+1);
    complete_irp(&publishing.irp,(void*)(uintptr_t)0x7000);
    IO24_CHECK(IsListEmpty(&d.irp_list)&&!publishing.irp.Tail.Overlay.DriverContext[0]);
    IO24_CHECK(counts.allocations==allocations+1&&counts.frees==frees+1&&
            counts.releases==releases+1&&counts.completions==completions+1);

    allocations=counts.allocations;frees=counts.frees;releases=counts.releases;
    completions=counts.completions;cancels=counts.cancels;
    prepare_bulk(&racing,pipe);prepare_abort(&abort,pipe);
    IO24_CHECK(driver_internal_ioctl(&o,&racing.irp)==STATUS_PENDING);
    expected_cancel_transfer=(void*)(uintptr_t)0x7000;
    complete_during_cancel_irp=&racing.irp;
    IO24_CHECK(usb_submit_urb(&d,&abort.irp)==STATUS_SUCCESS);
    IO24_CHECK(!complete_during_cancel_irp&&counts.cancels==cancels+1);
    IO24_CHECK(IsListEmpty(&d.irp_list)&&!racing.irp.Tail.Overlay.DriverContext[0]);
    IO24_CHECK(counts.allocations==allocations+1&&counts.frees==frees+1&&
            counts.releases==releases+1&&counts.completions==completions+1);
    list_remove(&d.entry);
}
static void group_lower(void)
{
    struct usb_device d; DEVICE_OBJECT o;
    struct pending_fixture matching, other_pipe, control, abort;
    struct wineusb_transfer matching_transfer, other_transfer, control_transfer;
    unsigned int lower_before;

    prepare_device(&d, &o);
    memset(&matching, 0, sizeof(matching));
    memset(&other_pipe, 0, sizeof(other_pipe));
    memset(&control, 0, sizeof(control));
    memset(&abort, 0, sizeof(abort));
    memset(&matching_transfer, 0, sizeof(matching_transfer));
    memset(&other_transfer, 0, sizeof(other_transfer));
    memset(&control_transfer, 0, sizeof(control_transfer));
    matching.irp.Tail.Overlay.CurrentStackLocation = &matching.stack;
    matching.stack.Parameters.Others.Argument1 = &matching.urb;
    matching.urb.UrbBulkOrInterruptTransfer.Hdr.Function =
            URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    matching.urb.UrbBulkOrInterruptTransfer.PipeHandle =
            (HANDLE)(uintptr_t)0x281;
    matching_transfer.unix_transfer = (void *)(uintptr_t)0x5081;
    matching_transfer.pipe_handle = (HANDLE)(uintptr_t)0x281;
    matching_transfer.urb_function = URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    matching_transfer.references = 1;
    matching_transfer.state = WINEUSB_TRANSFER_PENDING;
    matching.irp.Tail.Overlay.DriverContext[0] = &matching_transfer;
    other_pipe.irp.Tail.Overlay.CurrentStackLocation = &other_pipe.stack;
    other_pipe.stack.Parameters.Others.Argument1 = &other_pipe.urb;
    other_pipe.urb.UrbBulkOrInterruptTransfer.Hdr.Function =
            URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    other_pipe.urb.UrbBulkOrInterruptTransfer.PipeHandle =
            (HANDLE)(uintptr_t)0x201;
    other_transfer.unix_transfer = (void *)(uintptr_t)0x5001;
    other_transfer.pipe_handle = (HANDLE)(uintptr_t)0x201;
    other_transfer.urb_function = URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;
    other_transfer.references = 1;
    other_transfer.state = WINEUSB_TRANSFER_PENDING;
    other_pipe.irp.Tail.Overlay.DriverContext[0] = &other_transfer;
    control.irp.Tail.Overlay.CurrentStackLocation = &control.stack;
    control.stack.Parameters.Others.Argument1 = &control.urb;
    control.urb.UrbControlTransfer.Hdr.Function = URB_FUNCTION_CONTROL_TRANSFER;
    control_transfer.unix_transfer = (void *)(uintptr_t)0x4000;
    control_transfer.urb_function = URB_FUNCTION_CONTROL_TRANSFER;
    control_transfer.references = 1;
    control_transfer.state = WINEUSB_TRANSFER_PENDING;
    control.irp.Tail.Overlay.DriverContext[0] = &control_transfer;
    InsertTailList(&d.irp_list, &matching.irp.Tail.Overlay.ListEntry);
    InsertTailList(&d.irp_list, &other_pipe.irp.Tail.Overlay.ListEntry);
    InsertTailList(&d.irp_list, &control.irp.Tail.Overlay.ListEntry);
    abort.irp.Tail.Overlay.CurrentStackLocation = &abort.stack;
    abort.stack.Parameters.Others.Argument1 = &abort.urb;
    abort.urb.UrbPipeRequest.Hdr.Function = URB_FUNCTION_ABORT_PIPE;
    abort.urb.UrbPipeRequest.PipeHandle = (HANDLE)(uintptr_t)0x281;
    counts.cancels = 0; order[0] = 0;
    lower_before = counts.cancels;
    expected_cancel_transfer = matching_transfer.unix_transfer;
    IO24_CHECK(usb_submit_urb(&d, &abort.irp) == STATUS_SUCCESS);
    IO24_CHECK(abort.urb.UrbPipeRequest.Hdr.Status == USBD_STATUS_SUCCESS);
    IO24_CHECK(counts.cancels == lower_before + 1);
    IO24_CHECK(counts.cancels == 1);
    IO24_CHECK(!strcmp(order, "cancel,"));
    list_remove(&d.entry);
    group_kernel_lifetime();
}
static void group_upper(void)
{
    struct usb_device d;DEVICE_OBJECT o;struct pending_fixture f;prepare_device(&d,&o);memset(&f,0,sizeof(f));memset(f.guarded,GUARD_BYTE,sizeof(f.guarded));f.irp.Tail.Overlay.CurrentStackLocation=&f.stack;f.stack.Parameters.DeviceIoControl.IoControlCode=IOCTL_INTERNAL_USB_SUBMIT_URB;f.stack.Parameters.Others.Argument1=&f.urb;f.urb.UrbBulkOrInterruptTransfer.Hdr.Function=URB_FUNCTION_BULK_OR_INTERRUPT_TRANSFER;f.urb.UrbBulkOrInterruptTransfer.PipeHandle=(HANDLE)(uintptr_t)0x281;f.urb.UrbBulkOrInterruptTransfer.TransferBufferLength=32;f.urb.UrbBulkOrInterruptTransfer.TransferBuffer=f.guarded+1;IO24_CHECK(driver_internal_ioctl(&o,&f.irp)==STATUS_PENDING);IO24_CHECK(f.irp.CancelRoutine!=NULL);IO24_CHECK(f.guarded[0]==GUARD_BYTE&&f.guarded[33]==GUARD_BYTE);list_remove(&d.entry);
}
static void group_teardown(void)
{
    struct usb_device d;DEVICE_OBJECT o;struct pending_fixture f;IRP pnp;IO_STACK_LOCATION stack;unsigned int lower_before;prepare_device(&d,&o);memset(&f,0,sizeof(f));f.irp.Tail.Overlay.DriverContext[0]=(void*)(uintptr_t)0x5081;InsertTailList(&d.irp_list,&f.irp.Tail.Overlay.ListEntry);memset(&pnp,0,sizeof(pnp));memset(&stack,0,sizeof(stack));pnp.Tail.Overlay.CurrentStackLocation=&stack;stack.MinorFunction=IRP_MN_SURPRISE_REMOVAL;order[0]=0;counts.cancels=counts.completions=0;lower_before=io24_fake_libusb_cancel_count();IO24_CHECK(pdo_pnp(&o,&pnp)==STATUS_SUCCESS);IO24_CHECK(io24_fake_libusb_cancel_count()==lower_before+1);IO24_CHECK(counts.cancels==1&&counts.completions>=2);IO24_CHECK(!strncmp(order,"cancel,complete,",16));
}
static void run(const char*m){if(!strcmp(m,"--red")||!strcmp(m,"--lower"))group_lower();if(!strcmp(m,"--red")||!strcmp(m,"--upper"))group_upper();if(!strcmp(m,"--red")||!strcmp(m,"--teardown"))group_teardown();}
int main(int argc,char**argv){void*module;if(argc!=3)return 2;module=dlopen(argv[1],RTLD_NOW|RTLD_GLOBAL);if(!module){fprintf(stderr,"HARNESS: dlopen actual unixlib: %s\n",dlerror());return 2;}real_unix_calls=dlsym(module,"__wine_unix_call_funcs");if(!real_unix_calls){fprintf(stderr,"HARNESS: dlsym actual unix calls: %s\n",dlerror());return 2;}if(real_unix_calls[unix_usb_init](NULL)!=STATUS_SUCCESS){fprintf(stderr,"HARNESS: actual unix init failed\n");return 2;}run(argv[2]);real_unix_calls[unix_usb_exit](NULL);dlclose(module);printf("CP33 cancel executed mode=%s cancels=%u completions=%u failures=%u\n",argv[2],counts.cancels,counts.completions,counts.failures);return counts.failures?1:0;}
