/* Executed CP33 contract: actual winusb.sys main.c inside the retained fake WDM. */
#include <stdint.h>
#define main io24_retained_cp32_main
#include "winusb_function_binding_contract.c"
#undef main
#include "wine/winusb.h"

#define IO24_PRIVATE_FIELD(type, member, expected) \
    _Static_assert(_Generic(((struct type *)0)->member, expected: 1, default: 0), #type "." #member " type")
_Static_assert(sizeof(struct wine_winusb_request) == 24, "private request size");
_Static_assert(sizeof(struct wine_winusb_snapshot) == 72, "private snapshot size");
_Static_assert(sizeof(struct wine_winusb_interface_snapshot) == 16, "private interface size");
_Static_assert(sizeof(struct wine_winusb_alternate_snapshot) == 16, "private alternate size");
_Static_assert(sizeof(struct wine_winusb_endpoint_snapshot) == 16, "private endpoint size");
_Static_assert(sizeof(struct wine_winusb_alternate_request) == 32, "private alternate request size");
_Static_assert(sizeof(struct wine_winusb_pipe_request) == 32, "private pipe request size");
_Static_assert(sizeof(struct wine_winusb_descriptor_request) == 40, "private descriptor request size");
_Static_assert(sizeof(struct wine_winusb_policy_request) == 40, "private policy request size");
_Static_assert(sizeof(struct wine_winusb_control_request) == 40, "private control request size");
_Static_assert(offsetof(struct wine_winusb_request, session) == 8, "private request session offset");
_Static_assert(offsetof(struct wine_winusb_snapshot, reserved) == 64, "private snapshot reserved offset");
_Static_assert(offsetof(struct wine_winusb_control_request, setup) == 24, "private control setup offset");
IO24_PRIVATE_FIELD(wine_winusb_request, size, UINT32);
IO24_PRIVATE_FIELD(wine_winusb_request, version, UINT32);
IO24_PRIVATE_FIELD(wine_winusb_request, session, UINT64);
IO24_PRIVATE_FIELD(wine_winusb_request, interface_index, UINT32);
IO24_PRIVATE_FIELD(wine_winusb_request, reserved, UINT32);
IO24_PRIVATE_FIELD(wine_winusb_endpoint_snapshot, alternate_index, UINT32);
IO24_PRIVATE_FIELD(wine_winusb_endpoint_snapshot, pipe_id, UINT32);
IO24_PRIVATE_FIELD(wine_winusb_endpoint_snapshot, pipe_type, UINT32);
IO24_PRIVATE_FIELD(wine_winusb_endpoint_snapshot, maximum_packet_size, UINT32);
_Static_assert(_Generic(((struct wine_winusb_control_request *)0)->setup[0], UINT8: 1, default: 0), "private control setup type");

#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
static ULONG last_ioctl;static NTSTATUS last_status;static unsigned int mode_ioctls;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)

#define IO24_CTL_CODE(type,function,method,access) (((type)<<16)|((access)<<14)|((function)<<2)|(method))
#define IO24_IOCTL_INITIALIZE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x800,2,0)
#define IO24_IOCTL_SET_ALTERNATE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x803,0,0)
#define IO24_IOCTL_SET_POLICY IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x805,0,0)
#define IO24_IOCTL_READ_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x808,2,0)

static const unsigned char mi05_configuration[] =
{
    9,2,41,0,1,1,0,0x80,0xfa, 9,4,5,0,0,0xff,0,0,6,
    9,4,5,1,2,0xff,0,0,6, 7,5,0x81,2,0,2,0, 7,5,0x01,2,0,2,0
};
struct request { uint32_t version,size,session,interface_index,generation,value; unsigned char descriptor[sizeof(mi05_configuration)]; };
struct guarded_request { unsigned char before[16]; struct request request; unsigned char after[16]; };

struct dispatch_effect
{
    NTSTATUS status; ULONG_PTR information; unsigned int lower_before,lower_after,complete_before,complete_after;
};
static void check_guards(const struct guarded_request *guarded)
{
    unsigned int i;for(i=0;i<sizeof(guarded->before);i++)IO24_CHECK(guarded->before[i]==GUARD_BYTE);
    for(i=0;i<sizeof(guarded->after);i++)IO24_CHECK(guarded->after[i]==GUARD_BYTE);
}
static struct dispatch_effect dispatch_request(PDRIVER_OBJECT driver,PDEVICE_OBJECT fdo,UCHAR major,ULONG code,
        struct guarded_request *guarded,FILE_OBJECT *file)
{
    IRP irp; IO_STACK_LOCATION stack[2];struct dispatch_effect effect;
    memset(&irp,0,sizeof(irp)); memset(stack,0,sizeof(stack));
    stack[1].MajorFunction=major;
    stack[1].FileObject=file;
    stack[1].Parameters.DeviceIoControl.IoControlCode=code;
    stack[1].Parameters.DeviceIoControl.InputBufferLength=sizeof(guarded->request);
    stack[1].Parameters.DeviceIoControl.OutputBufferLength=sizeof(guarded->request);
    irp.AssociatedIrp.SystemBuffer=&guarded->request;
    irp.Tail.Overlay.CurrentStackLocation=&stack[1];
    effect.lower_before=lower_calls;effect.complete_before=completes;counts.submits++;
    driver->MajorFunction[major](fdo,&irp);
    effect.lower_after=lower_calls;effect.complete_after=completes;effect.status=irp.IoStatus.Status;effect.information=irp.IoStatus.Information;
    if(major==IRP_MJ_DEVICE_CONTROL){last_ioctl=code;last_status=effect.status;mode_ioctls++;}
    check_guards(guarded);return effect;
}

static void setup_added(DRIVER_OBJECT*d,DRIVER_EXTENSION*e,DEVICE_OBJECT*p,struct guarded_request*g,FILE_OBJECT*file)
{
    unsigned int previous_failures=counts.failures;
    memset(&counts,0,sizeof(counts)); counts.failures=previous_failures;memset(g,GUARD_BYTE,sizeof(*g));memset(file,0,sizeof(*file));last_ioctl=0;last_status=0;mode_ioctls=0;
    g->request.version=1; g->request.size=sizeof(g->request); g->request.interface_index=5;
    memcpy(g->request.descriptor,mi05_configuration,sizeof(mi05_configuration));
    reset(); initialize(d,e,p); IO24_CHECK(NT_SUCCESS(add(d,p)));
}
static void setup(DRIVER_OBJECT*d,DRIVER_EXTENSION*e,DEVICE_OBJECT*p,struct guarded_request*g,FILE_OBJECT*file)
{
    setup_added(d,e,p,g,file);
    IO24_CHECK(NT_SUCCESS(dispatch(d,last_fdo,IRP_MJ_PNP,IRP_MN_START_DEVICE)));
}
static void teardown(DRIVER_OBJECT*d){ if(last_fdo)dispatch(d,last_fdo,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE); }
static BOOL create_file(PDRIVER_OBJECT d,struct guarded_request *g,FILE_OBJECT *file)
{
    struct dispatch_effect effect=dispatch_request(d,last_fdo,IRP_MJ_CREATE,0,g,file);IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(effect.lower_after==effect.lower_before);IO24_CHECK(effect.complete_after==effect.complete_before+1);IO24_CHECK(file->FsContext!=NULL);return effect.status==STATUS_SUCCESS&&file->FsContext!=NULL;
}

struct expected_winusb_file
{
    LIST_ENTRY device_entry;
    FILE_OBJECT *file_object;
    KSPIN_LOCK lock;
    int state;
    UINT64 session;
    LONG references;
    LONG outstanding;
    KEVENT zero_outstanding;
    LIST_ENTRY transfers;
    void *snapshot;
    ULONG snapshot_size;
    void *interfaces;
    ULONG interface_count;
};

static void check_new_file(FILE_OBJECT *file)
{
    const struct expected_winusb_file *context=file->FsContext;
    IO24_CHECK(context!=NULL);
    if(!context)return;
    IO24_CHECK(context->file_object==file);IO24_CHECK(context->state==0);IO24_CHECK(context->session==0);
    IO24_CHECK(context->references==1);IO24_CHECK(context->outstanding==0);
    IO24_CHECK(context->zero_outstanding.Header.SignalState==1);
    IO24_CHECK(context->transfers.Flink==&context->transfers&&context->transfers.Blink==&context->transfers);
    IO24_CHECK(context->snapshot==NULL&&context->snapshot_size==0);
    IO24_CHECK(context->interfaces==NULL&&context->interface_count==0);
}
static BOOL initialize_session(PDRIVER_OBJECT d,struct guarded_request *g,FILE_OBJECT *file)
{
    struct request before=g->request;struct dispatch_effect effect=dispatch_request(d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_INITIALIZE,g,file);
    IO24_CHECK(!memcmp(before.descriptor,mi05_configuration,sizeof(mi05_configuration)));
    IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(effect.lower_after==effect.lower_before+4);IO24_CHECK(effect.complete_after==effect.complete_before+1);
    IO24_CHECK(effect.information>0);IO24_CHECK(g->request.session!=0);IO24_CHECK(memcmp(&before,&g->request,sizeof(before))!=0);
    return effect.status==STATUS_SUCCESS&&g->request.session!=0;
}
static void dispatch_safe_rejection(PDRIVER_OBJECT d,struct guarded_request *g,FILE_OBJECT *file,ULONG code)
{
    struct request before=g->request;struct dispatch_effect effect=dispatch_request(d,last_fdo,IRP_MJ_DEVICE_CONTROL,code,g,file);IO24_CHECK(!NT_SUCCESS(effect.status));IO24_CHECK(effect.lower_after==effect.lower_before);IO24_CHECK(effect.complete_after==effect.complete_before+1);IO24_CHECK(effect.information==0);IO24_CHECK(!memcmp(&before,&g->request,sizeof(before)));
}
static void group_lifecycle(void)
{
    DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT first,second,failed,late;
    struct guarded_request g;struct dispatch_effect effect;struct winusb_device *device;
    void *first_context,*second_context;unsigned int frees_before;int second_state;

    setup_added(&d,&e,&p,&g,&first);
    device=last_fdo->DeviceExtension;
    memset(&second,0,sizeof(second));memset(&failed,0,sizeof(failed));memset(&late,0,sizeof(late));

    effect=dispatch_request(&d,last_fdo,IRP_MJ_CREATE,0,&g,&first);
    IO24_CHECK(effect.status==STATUS_NOT_SUPPORTED);IO24_CHECK(first.FsContext==NULL);
    IO24_CHECK(effect.lower_after==effect.lower_before&&effect.complete_after==effect.complete_before+1);
    IO24_CHECK(pool_allocations==0);

    IO24_CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_START_DEVICE)));
    IO24_CHECK(create_file(&d,&g,&first));check_new_file(&first);first_context=first.FsContext;
    IO24_CHECK(create_file(&d,&g,&second));check_new_file(&second);second_context=second.FsContext;
    IO24_CHECK(first_context!=second_context);IO24_CHECK(pool_allocations==2);
    IO24_CHECK(device->file_count==2&&!device->removal_event.Header.SignalState);

    fail_next_pool_allocation=1;
    effect=dispatch_request(&d,last_fdo,IRP_MJ_CREATE,0,&g,&failed);
    IO24_CHECK(effect.status==STATUS_NO_MEMORY);IO24_CHECK(failed.FsContext==NULL);
    IO24_CHECK(effect.lower_after==effect.lower_before&&effect.complete_after==effect.complete_before+1);
    IO24_CHECK(device->file_count==2);

    IO24_CHECK(d.MajorFunction[IRP_MJ_CLEANUP]!=NULL);
    if(d.MajorFunction[IRP_MJ_CLEANUP])
    {
        second_state=((struct expected_winusb_file *)second_context)->state;
        first.FsContext=second_context;
        effect=dispatch_request(&d,last_fdo,IRP_MJ_CLEANUP,0,&g,&first);
        IO24_CHECK(effect.status==STATUS_INVALID_DEVICE_STATE);
        IO24_CHECK(((struct expected_winusb_file *)second_context)->state==second_state);
        first.FsContext=first_context;
        effect=dispatch_request(&d,last_fdo,IRP_MJ_CLEANUP,0,&g,&first);
        IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(first.FsContext==first_context);
        if(first.FsContext)IO24_CHECK(((struct expected_winusb_file *)first.FsContext)->state==4);
        IO24_CHECK(effect.lower_after==effect.lower_before&&effect.complete_after==effect.complete_before+1);
        effect=dispatch_request(&d,last_fdo,IRP_MJ_CLEANUP,0,&g,&first);
        IO24_CHECK(effect.status==STATUS_SUCCESS&&first.FsContext==first_context);
        if(first.FsContext)IO24_CHECK(((struct expected_winusb_file *)first.FsContext)->state==4);
    }
    IO24_CHECK(pool_frees==0);

    effect=dispatch_request(&d,last_fdo,IRP_MJ_CLOSE,0,&g,&first);
    IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(first.FsContext==NULL);IO24_CHECK(pool_frees==1);
    IO24_CHECK(device->file_count==1&&!device->removal_event.Header.SignalState);
    frees_before=pool_frees;
    effect=dispatch_request(&d,last_fdo,IRP_MJ_CLOSE,0,&g,&first);
    IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(first.FsContext==NULL);IO24_CHECK(pool_frees==frees_before);
    IO24_CHECK(device->file_count==1);

    IO24_CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_SURPRISE_REMOVAL)));
    IO24_CHECK(second.FsContext==second_context);
    if(second.FsContext)IO24_CHECK(((struct expected_winusb_file *)second.FsContext)->state==5);
    effect=dispatch_request(&d,last_fdo,IRP_MJ_CREATE,0,&g,&late);
    IO24_CHECK(effect.status==STATUS_NOT_SUPPORTED);IO24_CHECK(late.FsContext==NULL);
    IO24_CHECK(pool_allocations==3);

    if(d.MajorFunction[IRP_MJ_CLEANUP])
    {
        effect=dispatch_request(&d,last_fdo,IRP_MJ_CLEANUP,0,&g,&second);
        IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(second.FsContext==second_context);
    }
    effect=dispatch_request(&d,last_fdo,IRP_MJ_CLOSE,0,&g,&second);
    IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(second.FsContext==NULL);IO24_CHECK(pool_frees==2);
    IO24_CHECK(device->file_count==0&&device->removal_event.Header.SignalState);
    teardown(&d);
}
static void group_session(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;setup(&d,&e,&p,&g,&file);create_file(&d,&g,&file);initialize_session(&d,&g,&file);teardown(&d);}
static void group_alternate(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;struct dispatch_effect effect;uint32_t generation;BOOL opened,initialized;setup(&d,&e,&p,&g,&file);opened=create_file(&d,&g,&file);initialized=initialize_session(&d,&g,&file);g.request.value=1;if(!opened||!initialized){dispatch_safe_rejection(&d,&g,&file,IO24_IOCTL_SET_ALTERNATE);teardown(&d);return;}generation=g.request.generation;effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_SET_ALTERNATE,&g,&file);IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(effect.lower_after==effect.lower_before+1);IO24_CHECK(effect.complete_after==effect.complete_before+1);IO24_CHECK(g.request.generation==generation+1);teardown(&d);}
static void group_policy(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;struct dispatch_effect effect;BOOL opened,initialized;setup(&d,&e,&p,&g,&file);opened=create_file(&d,&g,&file);initialized=initialize_session(&d,&g,&file);g.request.value=7;if(!opened||!initialized){dispatch_safe_rejection(&d,&g,&file,IO24_IOCTL_SET_POLICY);teardown(&d);return;}effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_SET_POLICY,&g,&file);IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(effect.lower_after==effect.lower_before);IO24_CHECK(effect.complete_after==effect.complete_before+1);teardown(&d);}
static void group_transfer(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;struct dispatch_effect effect;BOOL opened,initialized;setup(&d,&e,&p,&g,&file);opened=create_file(&d,&g,&file);initialized=initialize_session(&d,&g,&file);if(!opened||!initialized){dispatch_safe_rejection(&d,&g,&file,IO24_IOCTL_READ_PIPE);teardown(&d);return;}g.request.value=1;effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_SET_ALTERNATE,&g,&file);IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.lower_after==effect.lower_before+1);effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_READ_PIPE,&g,&file);IO24_CHECK(effect.status==STATUS_PENDING);IO24_CHECK(effect.lower_after==effect.lower_before+1);IO24_CHECK(effect.complete_after==effect.complete_before);teardown(&d);}
static void run(const char*m){if(!strcmp(m,"--red")||!strcmp(m,"--lifecycle"))group_lifecycle();if(!strcmp(m,"--red")||!strcmp(m,"--session"))group_session();if(!strcmp(m,"--red")||!strcmp(m,"--alternate"))group_alternate();if(!strcmp(m,"--red")||!strcmp(m,"--policy"))group_policy();if(!strcmp(m,"--red")||!strcmp(m,"--transfer"))group_transfer();}
int main(int argc,char**argv){unsigned int retained;if(argc!=2)return 2;retained=io24_retained_cp32_main();if(retained){fprintf(stderr,"HARNESS: retained fake-WDM baseline failed\n");return 2;}run(argv[1]);printf("CP33 function executed mode=%s dispatches=%u mode-ioctls=%u last-ioctl=%#lx last-status=%#lx failures=%u\n",argv[1],counts.submits,mode_ioctls,(unsigned long)last_ioctl,(unsigned long)last_status,counts.failures);return counts.failures?1:0;}
