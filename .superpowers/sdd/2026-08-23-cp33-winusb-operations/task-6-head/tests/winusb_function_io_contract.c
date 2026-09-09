/* Executed CP33 contract: actual winusb.sys main.c inside the retained fake WDM. */
#include <stdint.h>
#define main io24_retained_cp32_main
#define ExAllocatePool io24_retained_ExAllocatePool
#define IoCallDriver io24_retained_IoCallDriver
#include "winusb_function_binding_contract.c"
#undef IoCallDriver
#undef ExAllocatePool
#undef main
#include "wine/winusb.h"
#include "ddk/usb.h"
#ifndef METHOD_NEITHER
#define METHOD_NEITHER 3
#endif
#include "ddk/usbioctl.h"

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
static unsigned int session_allocation_calls, session_fail_allocation;
#define IO24_CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr, "FAIL %s:%u: %s\n", __func__, __LINE__, #expr); \
    ++counts.failures; \
} } while (0)

PVOID WINAPI ExAllocatePool(POOL_TYPE type, SIZE_T size)
{
    (void)type;
    session_allocation_calls++;
    if (session_fail_allocation == session_allocation_calls) return NULL;
    pool_allocations++;
    return calloc(1, size);
}

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
static const unsigned char default_endpoint_configuration[] =
{
    9,2,25,0,1,1,0,0x80,0xfa, 9,4,5,0,1,0xff,0,0,6,
    7,5,0x82,2,64,0,0
};
static const unsigned char mi05_device[] =
{
    18,1,0x00,0x02,0,0,0,64,0x46,0x19,0x24,0x00,0x00,0x01,1,2,3,1
};

static unsigned char lower_configuration[256];
static ULONG lower_configuration_size;
static ULONG lower_header_actual, lower_body_actual;
static NTSTATUS descriptor_nt_status, select_nt_status;
static USBD_STATUS descriptor_urb_status, select_urb_status;
static BOOL descriptor_writes_urb_status, select_writes_urb_status;
static BOOL lower_returns_pending;
static unsigned int descriptor_reads, select_calls;
static unsigned int finalize_calls, finalize_commit_calls, finalize_rollback_calls;
static BOOL mutate_after_select, rollback_saw_unpublished;
static BOOL lower_claim_pending, lower_claim_committed, lower_selected_state;
static unsigned char *active_initialize_output;
static USBD_CONFIGURATION_HANDLE lower_transaction_token;
static unsigned int urb_builds, fail_urb_build;
static unsigned int builder_allocations, builder_frees;
static ULONG expected_select_pipes;
static UCHAR expected_select_endpoint;
static USBD_PIPE_TYPE expected_select_type;
static USHORT expected_select_packet_size;
static FILE_OBJECT *active_session_file;

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

struct session_irp_allocation
{
    IRP irp;
    IO_STACK_LOCATION stack[2];
    PKEVENT event;
    PIO_STATUS_BLOCK iosb;
    URB *urb;
};

static void reset_initialize_lower(void)
{
    memset(lower_configuration, 0, sizeof(lower_configuration));
    memcpy(lower_configuration, mi05_configuration, sizeof(mi05_configuration));
    lower_configuration_size = sizeof(mi05_configuration);
    lower_header_actual = sizeof(USB_CONFIGURATION_DESCRIPTOR);
    lower_body_actual = sizeof(mi05_configuration);
    descriptor_nt_status = select_nt_status = STATUS_SUCCESS;
    descriptor_urb_status = select_urb_status = USBD_STATUS_SUCCESS;
    descriptor_writes_urb_status = select_writes_urb_status = TRUE;
    lower_returns_pending = FALSE;
    descriptor_reads = select_calls = urb_builds = fail_urb_build = 0;
    finalize_calls = finalize_commit_calls = finalize_rollback_calls = 0;
    mutate_after_select = rollback_saw_unpublished = FALSE;
    lower_claim_pending = lower_claim_committed = lower_selected_state = FALSE;
    lower_transaction_token = (void *)(UINT_PTR)0x13570001;
    builder_allocations = builder_frees = 0;
    expected_select_pipes = 0;
    expected_select_endpoint = 0;
    expected_select_type = UsbdPipeTypeControl;
    expected_select_packet_size = 0;
}

PVOID WINAPI MmMapLockedPagesSpecifyCache(PMDLX mdl, KPROCESSOR_MODE mode,
        MEMORY_CACHING_TYPE cache, PVOID address, ULONG bugcheck, MM_PAGE_PRIORITY priority)
{
    (void)mode; (void)cache; (void)address; (void)bugcheck; (void)priority;
    return mdl ? mdl->MappedSystemVa : NULL;
}

PIRP WINAPI IoBuildDeviceIoControlRequest(ULONG code, PDEVICE_OBJECT device,
        PVOID input, ULONG input_length, PVOID output, ULONG output_length,
        BOOLEAN internal, PKEVENT event, PIO_STATUS_BLOCK iosb)
{
    struct session_irp_allocation *allocation;
    URB *urb = input;

    (void)device;
    IO24_CHECK(code == IOCTL_INTERNAL_USB_SUBMIT_URB);
    IO24_CHECK(internal && urb && input_length == urb->UrbHeader.Length);
    IO24_CHECK(!output && !output_length);
    urb_builds++;
    if (fail_urb_build == urb_builds) return NULL;
    if (!(allocation = calloc(1, sizeof(*allocation))))
    {
        fputs("HARNESS: allocating builder IRP failed\n", stderr);
        exit(2);
    }
    builder_allocations++;
    allocation->stack[0].MajorFunction = IRP_MJ_INTERNAL_DEVICE_CONTROL;
    allocation->stack[0].Parameters.DeviceIoControl.IoControlCode = code;
    allocation->stack[0].Parameters.DeviceIoControl.Type3InputBuffer = urb;
    allocation->irp.Tail.Overlay.CurrentStackLocation = &allocation->stack[1];
    allocation->event = event;
    allocation->iosb = iosb;
    allocation->urb = urb;
    return &allocation->irp;
}

NTSTATUS WINAPI IoCallDriver(PDEVICE_OBJECT device, PIRP irp)
{
    struct session_irp_allocation *allocation = (void *)irp;
    IO_STACK_LOCATION *next = IoGetNextIrpStackLocation(irp);
    URB *urb = next->Parameters.Others.Argument1;
    NTSTATUS status = STATUS_NOT_SUPPORTED;
    ULONG actual = 0;

    (void)device;
    lower_calls++;
    IO24_CHECK(active_session_file != NULL && active_session_file->FsContext != NULL);
    if (active_session_file && active_session_file->FsContext)
    {
        const struct winusb_file *file = active_session_file->FsContext;
        IO24_CHECK(file->outstanding == 1);
        IO24_CHECK(!file->zero_outstanding.Header.SignalState);
    }
    IO24_CHECK(next->MajorFunction == IRP_MJ_INTERNAL_DEVICE_CONTROL);
    IO24_CHECK(next->Parameters.DeviceIoControl.IoControlCode == IOCTL_INTERNAL_USB_SUBMIT_URB);
    IO24_CHECK(urb == allocation->urb);
    if (urb) IO24_CHECK(urb->UrbHeader.Status == USBD_STATUS_NOT_ACCESSED);
    if (!urb) goto done;
    if (urb->UrbHeader.Function == URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE)
    {
        struct _URB_CONTROL_DESCRIPTOR_REQUEST *request =
                &urb->UrbControlDescriptorRequest;
        const unsigned char *source = NULL;
        BOOL configuration_header = FALSE;

        IO24_CHECK(request->DescriptorType == USB_DEVICE_DESCRIPTOR_TYPE ||
                request->DescriptorType == USB_CONFIGURATION_DESCRIPTOR_TYPE);
        if (request->DescriptorType == USB_DEVICE_DESCRIPTOR_TYPE)
        {
            IO24_CHECK(descriptor_reads == 0);
            IO24_CHECK(request->TransferBufferLength == sizeof(mi05_device));
            source = mi05_device;
            actual = sizeof(mi05_device);
        }
        else if (descriptor_reads == 1)
        {
            IO24_CHECK(request->TransferBufferLength == sizeof(USB_CONFIGURATION_DESCRIPTOR));
            source = lower_configuration;
            actual = lower_header_actual;
            configuration_header = TRUE;
        }
        else
        {
            IO24_CHECK(descriptor_reads == 2);
            IO24_CHECK(request->TransferBufferLength == lower_configuration_size);
            source = lower_configuration;
            actual = lower_body_actual;
        }
        descriptor_reads++;
        status = descriptor_nt_status;
        if (descriptor_writes_urb_status)
            request->Hdr.Status = descriptor_urb_status;
        if (NT_SUCCESS(status) && descriptor_urb_status == USBD_STATUS_SUCCESS &&
                request->TransferBuffer && source)
        {
            ULONG copy = actual < request->TransferBufferLength ? actual : request->TransferBufferLength;
            memcpy(request->TransferBuffer, source, copy);
            request->TransferBufferLength = actual;
            if (configuration_header && copy >= sizeof(USB_CONFIGURATION_DESCRIPTOR))
                ((USB_CONFIGURATION_DESCRIPTOR *)request->TransferBuffer)->wTotalLength =
                        lower_configuration_size;
        }
    }
    else if (urb->UrbHeader.Function == URB_FUNCTION_SELECT_CONFIGURATION)
    {
        struct _URB_SELECT_CONFIGURATION *request = &urb->UrbSelectConfiguration;
        select_calls++;
        IO24_CHECK(descriptor_reads == 3);
        IO24_CHECK(request->ConfigurationDescriptor != NULL);
        IO24_CHECK(request->Interface.InterfaceNumber == 5);
        IO24_CHECK(request->Interface.AlternateSetting == 0);
        IO24_CHECK(request->Interface.NumberOfPipes == expected_select_pipes);
        IO24_CHECK(request->Interface.Length == offsetof(USBD_INTERFACE_INFORMATION, Pipes) +
                expected_select_pipes * sizeof(USBD_PIPE_INFORMATION));
        IO24_CHECK(request->Hdr.Length == offsetof(struct _URB_SELECT_CONFIGURATION, Interface) +
                request->Interface.Length);
        if (expected_select_pipes)
        {
            const USBD_PIPE_INFORMATION *pipe = &request->Interface.Pipes[0];
            IO24_CHECK(expected_select_pipes == 1);
            IO24_CHECK(pipe->EndpointAddress == expected_select_endpoint);
            IO24_CHECK(pipe->PipeType == expected_select_type);
            IO24_CHECK(pipe->MaximumPacketSize == expected_select_packet_size);
        }
        status = select_nt_status;
        if (select_writes_urb_status)
            request->Hdr.Status = select_urb_status;
        if (NT_SUCCESS(status) && select_writes_urb_status &&
                select_urb_status == USBD_STATUS_SUCCESS)
        {
            request->ConfigurationHandle = lower_transaction_token;
            lower_claim_pending = TRUE;
            lower_selected_state = TRUE;
            if (mutate_after_select && active_session_file && active_session_file->FsContext)
                ((struct winusb_file *)active_session_file->FsContext)->state =
                        WINUSB_FILE_CLOSING;
        }
    }
    else if (urb->UrbHeader.Function == IO24_URB_FUNCTION_CLAIM_TRANSACTION)
    {
        struct io24_claim_transaction_request *request = (void *)urb;
        unsigned int i;

        finalize_calls++;
        IO24_CHECK(request->Hdr.Length == sizeof(*request));
        IO24_CHECK(request->Transaction == lower_transaction_token);
        IO24_CHECK(request->Reserved == 0);
        IO24_CHECK(lower_claim_pending);
        if (request->Operation == IO24_CLAIM_TRANSACTION_COMMIT)
        {
            finalize_commit_calls++;
            lower_claim_committed = TRUE;
        }
        else if (request->Operation == IO24_CLAIM_TRANSACTION_ROLLBACK)
        {
            const struct winusb_file *file = active_session_file ?
                    active_session_file->FsContext : NULL;

            finalize_rollback_calls++;
            IO24_CHECK(file != NULL);
            IO24_CHECK(file && file->session == 0 && file->snapshot == NULL &&
                    file->interfaces == NULL);
            rollback_saw_unpublished = active_initialize_output != NULL;
            for (i = 0; active_initialize_output && i < 211; ++i)
                if (active_initialize_output[i] != GUARD_BYTE)
                    rollback_saw_unpublished = FALSE;
            lower_claim_committed = FALSE;
            lower_selected_state = FALSE;
        }
        else IO24_CHECK(FALSE);
        lower_claim_pending = FALSE;
        request->Hdr.Status = USBD_STATUS_SUCCESS;
        status = STATUS_SUCCESS;
    }
    else
    {
        IO24_CHECK(FALSE);
        status = STATUS_NOT_SUPPORTED;
    }
done:
    irp->IoStatus.Status = status;
    if (allocation->iosb) *allocation->iosb = irp->IoStatus;
    if (allocation->event) allocation->event->Header.SignalState = 1;
    memset(allocation, 0xdd, sizeof(*allocation));
    free(allocation);
    builder_frees++;
    return lower_returns_pending ? STATUS_PENDING : status;
}

struct request { uint32_t version,size,session,interface_index,generation,value; unsigned char descriptor[sizeof(mi05_configuration)]; };
struct guarded_request { unsigned char before[16]; struct request request; unsigned char after[16]; };
struct guarded_initialize { unsigned char before[16]; struct wine_winusb_request request; unsigned char after[16]; };
struct guarded_snapshot { unsigned char before[16]; unsigned char bytes[256]; unsigned char after[16]; };

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

static void reset_initialize_buffers(struct guarded_initialize *input,
        struct guarded_snapshot *output)
{
    memset(input, GUARD_BYTE, sizeof(*input));
    input->request.size = sizeof(input->request);
    input->request.version = WINE_WINUSB_ABI_VERSION;
    input->request.session = 0;
    input->request.interface_index = 0;
    input->request.reserved = 0;
    memset(output, GUARD_BYTE, sizeof(*output));
}

static void check_initialize_guards(const struct guarded_initialize *input,
        const struct guarded_snapshot *output)
{
    unsigned int i;

    for (i = 0; i < sizeof(input->before); ++i) IO24_CHECK(input->before[i] == GUARD_BYTE);
    for (i = 0; i < sizeof(input->after); ++i) IO24_CHECK(input->after[i] == GUARD_BYTE);
    for (i = 0; i < sizeof(output->before); ++i) IO24_CHECK(output->before[i] == GUARD_BYTE);
    for (i = 0; i < sizeof(output->after); ++i) IO24_CHECK(output->after[i] == GUARD_BYTE);
}

static struct dispatch_effect dispatch_session_ioctl(PDRIVER_OBJECT driver, PDEVICE_OBJECT fdo,
        ULONG code, struct guarded_initialize *input, ULONG input_length,
        struct guarded_snapshot *output, ULONG output_length, ULONG mdl_length,
        PVOID system_buffer, PVOID mapped_address, FILE_OBJECT *file)
{
    struct wine_winusb_request before = input->request;
    IRP irp;
    IO_STACK_LOCATION stack[2];
    MDL mdl;
    struct dispatch_effect effect;

    memset(&irp, 0, sizeof(irp));
    memset(stack, 0, sizeof(stack));
    memset(&mdl, 0, sizeof(mdl));
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL;
    stack[1].FileObject = file;
    stack[1].Parameters.DeviceIoControl.IoControlCode = code;
    stack[1].Parameters.DeviceIoControl.InputBufferLength = input_length;
    stack[1].Parameters.DeviceIoControl.OutputBufferLength = output_length;
    irp.AssociatedIrp.SystemBuffer = system_buffer;
    irp.Tail.Overlay.CurrentStackLocation = &stack[1];
    if (mapped_address != (PVOID)(UINT_PTR)1)
    {
        mdl.MdlFlags = MDL_MAPPED_TO_SYSTEM_VA;
        mdl.MappedSystemVa = mapped_address;
        mdl.ByteCount = mdl_length;
        irp.MdlAddress = &mdl;
    }
    effect.lower_before = lower_calls;
    effect.complete_before = completes;
    counts.submits++;
    active_session_file = file;
    active_initialize_output = mapped_address == (PVOID)(UINT_PTR)1 ? NULL : mapped_address;
    driver->MajorFunction[IRP_MJ_DEVICE_CONTROL](fdo, &irp);
    active_session_file = NULL;
    active_initialize_output = NULL;
    IO24_CHECK(builder_allocations == builder_frees);
    if (file && file->FsContext)
    {
        const struct winusb_file *context = file->FsContext;
        IO24_CHECK(context->outstanding == 0);
        IO24_CHECK(context->zero_outstanding.Header.SignalState);
    }
    effect.lower_after = lower_calls;
    effect.complete_after = completes;
    effect.status = irp.IoStatus.Status;
    effect.information = irp.IoStatus.Information;
    last_ioctl = code;
    last_status = effect.status;
    mode_ioctls++;
    check_initialize_guards(input, output);
    IO24_CHECK(!memcmp(&before, &input->request, sizeof(before)));
    return effect;
}

static void setup_added(DRIVER_OBJECT*d,DRIVER_EXTENSION*e,DEVICE_OBJECT*p,struct guarded_request*g,FILE_OBJECT*file)
{
    unsigned int previous_failures=counts.failures;
    memset(&counts,0,sizeof(counts)); counts.failures=previous_failures;memset(g,GUARD_BYTE,sizeof(*g));memset(file,0,sizeof(*file));last_ioctl=0;last_status=0;mode_ioctls=0;
    g->request.version=1; g->request.size=sizeof(g->request); g->request.interface_index=5;
    memcpy(g->request.descriptor,mi05_configuration,sizeof(mi05_configuration));
    reset(); reset_initialize_lower(); session_allocation_calls=session_fail_allocation=0;
    initialize(d,e,p); IO24_CHECK(NT_SUCCESS(add(d,p)));
}
static void setup(DRIVER_OBJECT*d,DRIVER_EXTENSION*e,DEVICE_OBJECT*p,struct guarded_request*g,FILE_OBJECT*file)
{
    setup_added(d,e,p,g,file);
    IO24_CHECK(NT_SUCCESS(dispatch(d,last_fdo,IRP_MJ_PNP,IRP_MN_START_DEVICE)));
}
static void teardown(DRIVER_OBJECT*d,struct guarded_request*g,FILE_OBJECT*file)
{
    struct dispatch_effect effect;
    if(last_fdo&&file&&file->FsContext)
    {
        effect=dispatch_request(d,last_fdo,IRP_MJ_CLEANUP,0,g,file);IO24_CHECK(effect.status==STATUS_SUCCESS);
        effect=dispatch_request(d,last_fdo,IRP_MJ_CLOSE,0,g,file);IO24_CHECK(effect.status==STATUS_SUCCESS);
        IO24_CHECK(file->FsContext==NULL);
    }
    if(last_fdo)IO24_CHECK(NT_SUCCESS(dispatch(d,last_fdo,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE)));
    IO24_CHECK(wait_failures==0);
    IO24_CHECK(pool_allocations==pool_frees);
}
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

struct lifecycle_wait_schedule
{
    DRIVER_OBJECT *driver;
    struct guarded_request *guarded;
    FILE_OBJECT *file;
    struct winusb_device *device;
    struct expected_winusb_file *context;
    unsigned int frees_before;
    unsigned int expected_close_frees;
    unsigned int removal_waits;
    unsigned int drain_waits;
};
static struct lifecycle_wait_schedule lifecycle_wait;

static void lifecycle_wait_hook(void *object)
{
    struct dispatch_effect effect;

    if(object==&lifecycle_wait.device->removal_event)
    {
        lifecycle_wait.removal_waits++;
        IO24_CHECK(lifecycle_wait.file->FsContext==lifecycle_wait.context);
        IO24_CHECK(lifecycle_wait.device->file_count==1);
        IO24_CHECK(!lifecycle_wait.device->removal_event.Header.SignalState);
        effect=dispatch_request(lifecycle_wait.driver,last_fdo,IRP_MJ_CLOSE,0,
                lifecycle_wait.guarded,lifecycle_wait.file);
        IO24_CHECK(effect.status==STATUS_SUCCESS&&lifecycle_wait.file->FsContext==NULL);
        IO24_CHECK(pool_frees==lifecycle_wait.frees_before+
                lifecycle_wait.expected_close_frees);
        IO24_CHECK(lifecycle_wait.device->file_count==0);
        IO24_CHECK(lifecycle_wait.device->removal_event.Header.SignalState);
    }
    else if(object==&lifecycle_wait.context->zero_outstanding)
    {
        lifecycle_wait.drain_waits++;
        IO24_CHECK(lifecycle_wait.device->file_count==1);
        IO24_CHECK(!lifecycle_wait.device->removal_event.Header.SignalState);
        IO24_CHECK(pool_frees==lifecycle_wait.frees_before);
        lifecycle_wait.context->outstanding=0;
        KeSetEvent(&lifecycle_wait.context->zero_outstanding,IO_NO_INCREMENT,FALSE);
    }
    else IO24_CHECK(FALSE);
}

static void check_file_uninitialized(const FILE_OBJECT *file)
{
    const struct winusb_file *context = file->FsContext;

    IO24_CHECK(context != NULL);
    if (!context) return;
    IO24_CHECK(context->state == WINUSB_FILE_UNINITIALIZED);
    IO24_CHECK(context->session == 0);
    IO24_CHECK(context->snapshot == NULL && context->snapshot_size == 0);
    IO24_CHECK(context->interfaces == NULL && context->interface_count == 0);
}

static void check_snapshot_tail(const struct guarded_snapshot *output, ULONG start)
{
    ULONG i;

    for (i = start; i < sizeof(output->bytes); ++i) IO24_CHECK(output->bytes[i] == GUARD_BYTE);
}

static void check_exact_snapshot(const struct guarded_snapshot *output, UINT64 session)
{
    struct wine_winusb_snapshot snapshot;
    struct wine_winusb_interface_snapshot interfaces[1];
    struct wine_winusb_alternate_snapshot alternates[2];
    struct wine_winusb_endpoint_snapshot endpoints[2];

    memcpy(&snapshot, output->bytes, sizeof(snapshot));
    memcpy(interfaces, output->bytes + 131, sizeof(interfaces));
    memcpy(alternates, output->bytes + 147, sizeof(alternates));
    memcpy(endpoints, output->bytes + 179, sizeof(endpoints));
    IO24_CHECK(snapshot.size == 72 && snapshot.version == WINE_WINUSB_ABI_VERSION);
    IO24_CHECK(snapshot.session == session && snapshot.speed == HighSpeed);
    IO24_CHECK(snapshot.total_size == 211);
    IO24_CHECK(snapshot.device_offset == 72 && snapshot.device_length == 18);
    IO24_CHECK(snapshot.configuration_offset == 90 && snapshot.configuration_length == 41);
    IO24_CHECK(snapshot.interfaces_offset == 131 && snapshot.interface_count == 1);
    IO24_CHECK(snapshot.alternates_offset == 147 && snapshot.alternate_count == 2);
    IO24_CHECK(snapshot.endpoints_offset == 179 && snapshot.endpoint_count == 2);
    IO24_CHECK(snapshot.reserved[0] == 0 && snapshot.reserved[1] == 0);
    IO24_CHECK(!memcmp(output->bytes + 72, mi05_device, sizeof(mi05_device)));
    IO24_CHECK(!memcmp(output->bytes + 90, mi05_configuration, sizeof(mi05_configuration)));
    IO24_CHECK(interfaces[0].interface_number == 5 && interfaces[0].first_alternate == 0 &&
            interfaces[0].alternate_count == 2 && interfaces[0].reserved == 0);
    IO24_CHECK(alternates[0].interface_index == 0 && alternates[0].alternate_setting == 0 &&
            alternates[0].first_endpoint == 0 && alternates[0].endpoint_count == 0);
    IO24_CHECK(alternates[1].interface_index == 0 && alternates[1].alternate_setting == 1 &&
            alternates[1].first_endpoint == 0 && alternates[1].endpoint_count == 2);
    IO24_CHECK(endpoints[0].alternate_index == 1 && endpoints[0].pipe_id == 0x81 &&
            endpoints[0].pipe_type == UsbdPipeTypeBulk && endpoints[0].maximum_packet_size == 512);
    IO24_CHECK(endpoints[1].alternate_index == 1 && endpoints[1].pipe_id == 0x01 &&
            endpoints[1].pipe_type == UsbdPipeTypeBulk && endpoints[1].maximum_packet_size == 512);
    check_snapshot_tail(output, 211);
}

static struct dispatch_effect call_initialize(PDRIVER_OBJECT driver, FILE_OBJECT *file,
        struct guarded_initialize *input, struct guarded_snapshot *output,
        ULONG output_length, ULONG mdl_length, PVOID system_buffer, PVOID mapped_address)
{
    return dispatch_session_ioctl(driver, last_fdo, IOCTL_WINE_WINUSB_INITIALIZE,
            input, sizeof(input->request), output, output_length, mdl_length,
            system_buffer, mapped_address, file);
}

static struct dispatch_effect call_release(PDRIVER_OBJECT driver, FILE_OBJECT *file,
        struct guarded_initialize *input, ULONG input_length)
{
    struct guarded_snapshot output;

    memset(&output, GUARD_BYTE, sizeof(output));
    return dispatch_session_ioctl(driver, last_fdo, IOCTL_WINE_WINUSB_RELEASE,
            input, input_length, &output, 0, 0, &input->request,
            (PVOID)(UINT_PTR)1, file);
}

static void expect_malformed_configuration(PDRIVER_OBJECT driver, FILE_OBJECT *file,
        const unsigned char *configuration, ULONG length,
        ULONG header_actual, ULONG body_actual, unsigned int expected_reads)
{
    struct guarded_initialize input;
    struct guarded_snapshot output, before;
    struct dispatch_effect effect;
    unsigned int allocations_before = pool_allocations, frees_before = pool_frees;

    reset_initialize_lower();
    memcpy(lower_configuration, configuration, length);
    lower_configuration_size = length;
    lower_header_actual = header_actual;
    lower_body_actual = body_actual;
    session_allocation_calls = 0;
    reset_initialize_buffers(&input, &output);
    before = output;
    effect = call_initialize(driver, file, &input, &output, 211, 211,
            &input.request, output.bytes);
    IO24_CHECK(effect.status == STATUS_INVALID_PARAMETER);
    IO24_CHECK(effect.information == 0 && effect.complete_after == effect.complete_before + 1);
    IO24_CHECK(effect.lower_after == effect.lower_before + expected_reads);
    IO24_CHECK(descriptor_reads == expected_reads && select_calls == 0);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output)));
    check_file_uninitialized(file);
    IO24_CHECK(pool_allocations - allocations_before == pool_frees - frees_before);
}

static void test_initialize_input_and_buffer_rejections(void)
{
    DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo;
    FILE_OBJECT file, alien = {0};
    struct guarded_request retained;
    struct guarded_initialize input;
    struct guarded_snapshot output, before;
    struct dispatch_effect effect;
    struct winusb_device *device;
    struct winusb_file *context;

    setup(&driver, &extension, &pdo, &retained, &file);
    IO24_CHECK(create_file(&driver, &retained, &file));
    device = last_fdo->DeviceExtension;
    context = file.FsContext;

#define IO24_REJECT_INIT() do { \
    reset_initialize_lower(); session_allocation_calls = 0; before = output; \
    effect = call_initialize(&driver, &file, &input, &output, 211, 211, \
            &input.request, output.bytes); \
    IO24_CHECK(!NT_SUCCESS(effect.status) && effect.information == 0); \
    IO24_CHECK(effect.lower_after == effect.lower_before && descriptor_reads == 0 && select_calls == 0); \
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file); \
} while (0)

    reset_initialize_buffers(&input, &output); input.request.size--; IO24_REJECT_INIT();
    reset_initialize_buffers(&input, &output); input.request.version++; IO24_REJECT_INIT();
    reset_initialize_buffers(&input, &output); input.request.session = 1; IO24_REJECT_INIT();
    reset_initialize_buffers(&input, &output); input.request.interface_index = 1; IO24_REJECT_INIT();
    reset_initialize_buffers(&input, &output); input.request.reserved = 1; IO24_REJECT_INIT();

    reset_initialize_buffers(&input, &output); before = output;
    effect = dispatch_session_ioctl(&driver, last_fdo, IOCTL_WINE_WINUSB_INITIALIZE,
            &input, sizeof(input.request) - 1, &output, 211, 211,
            &input.request, output.bytes, &file);
    IO24_CHECK(effect.status == STATUS_INVALID_PARAMETER && effect.information == 0);
    IO24_CHECK(effect.lower_after == effect.lower_before && !memcmp(&output, &before, sizeof(output)));
    check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    effect = call_initialize(&driver, &file, &input, &output, 211, 211, NULL, output.bytes);
    IO24_CHECK(effect.status == STATUS_INVALID_PARAMETER && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    effect = call_initialize(&driver, &alien, &input, &output, 211, 211,
            &input.request, output.bytes);
    IO24_CHECK(!NT_SUCCESS(effect.status) && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    effect = call_initialize(&driver, &file, &input, &output, 211, 211,
            &input.request, (PVOID)(UINT_PTR)1);
    IO24_CHECK(effect.status == STATUS_INVALID_PARAMETER && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    effect = call_initialize(&driver, &file, &input, &output, 211, 211,
            &input.request, NULL);
    IO24_CHECK(effect.status == STATUS_NO_MEMORY && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    effect = call_initialize(&driver, &file, &input, &output, 211, 210,
            &input.request, output.bytes);
    IO24_CHECK(effect.status == STATUS_INVALID_PARAMETER && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    effect = call_initialize(&driver, &file, &input, &output, 71, 71,
            &input.request, output.bytes);
    IO24_CHECK(effect.status == STATUS_BUFFER_TOO_SMALL && effect.information == 0);
    IO24_CHECK(effect.lower_after == effect.lower_before && !memcmp(&output, &before, sizeof(output)));
    check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    effect = call_initialize(&driver, &file, &input, &output, 72, 72,
            &input.request, (PVOID)(UINT_PTR)(~(SIZE_T)0 - 31));
    IO24_CHECK(effect.status == STATUS_INVALID_PARAMETER && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    device->state = WINUSB_DEVICE_STOPPED;
    effect = call_initialize(&driver, &file, &input, &output, 211, 211,
            &input.request, output.bytes);
    IO24_CHECK(effect.status == STATUS_INVALID_DEVICE_STATE && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output)));
    device->state = WINUSB_DEVICE_STARTED; check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); before = output;
    context->state = WINUSB_FILE_INITIALIZING;
    effect = call_initialize(&driver, &file, &input, &output, 211, 211,
            &input.request, output.bytes);
    IO24_CHECK(effect.status == STATUS_INVALID_DEVICE_STATE && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output)));
    context->state = WINUSB_FILE_UNINITIALIZED; check_file_uninitialized(&file);

#undef IO24_REJECT_INIT
    teardown(&driver, &retained, &file);
}

static void test_initialize_malformed_descriptors(void)
{
    DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo;
    FILE_OBJECT file;
    struct guarded_request retained;
    unsigned char malformed[256];

    setup(&driver, &extension, &pdo, &retained, &file);
    IO24_CHECK(create_file(&driver, &retained, &file));

    memcpy(malformed, mi05_configuration, sizeof(mi05_configuration));
    expect_malformed_configuration(&driver, &file, malformed, 41, 8, 41, 2);
    expect_malformed_configuration(&driver, &file, malformed, 41, 9, 40, 3);

    memcpy(malformed, mi05_configuration, 41); malformed[2] = 40;
    expect_malformed_configuration(&driver, &file, malformed, 41, 9, 41, 3);
    memcpy(malformed, mi05_configuration, 41); malformed[9] = 1;
    expect_malformed_configuration(&driver, &file, malformed, 41, 9, 41, 3);
    memcpy(malformed, mi05_configuration, 41); malformed[9] = 250;
    expect_malformed_configuration(&driver, &file, malformed, 41, 9, 41, 3);

    memcpy(malformed, (unsigned char[]){9,2,16,0,1,1,0,0x80,0xfa,7,5,0x81,2,0,2,0}, 16);
    expect_malformed_configuration(&driver, &file, malformed, 16, 9, 16, 3);
    memcpy(malformed, (unsigned char[]){9,2,9,0,0,1,0,0x80,0xfa}, 9);
    expect_malformed_configuration(&driver, &file, malformed, 9, 9, 9, 3);
    memcpy(malformed, (unsigned char[]){9,2,18,0,1,1,0,0x80,0xfa,9,4,5,1,0,0xff,0,0,6}, 18);
    expect_malformed_configuration(&driver, &file, malformed, 18, 9, 18, 3);
    memcpy(malformed, (unsigned char[]){9,2,27,0,1,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,0,0,0xff,0,0,6}, 27);
    expect_malformed_configuration(&driver, &file, malformed, 27, 9, 27, 3);
    memcpy(malformed, (unsigned char[]){9,2,36,0,2,1,0,0x80,0xfa,
            9,4,5,0,0,0xff,0,0,6, 9,4,6,0,0,0xff,0,0,6,
            9,4,5,1,0,0xff,0,0,6}, 36);
    expect_malformed_configuration(&driver, &file, malformed, 36, 9, 36, 3);

    teardown(&driver, &retained, &file);
}

static void test_initialize_size_full_release_reinitialize(void)
{
    DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo;
    FILE_OBJECT file, other = {0};
    struct guarded_request retained;
    struct guarded_initialize input;
    struct guarded_snapshot output, before;
    struct dispatch_effect effect;
    struct winusb_file *context;
    struct wine_winusb_snapshot snapshot;
    UINT64 first_session, second_session;
    void *committed_snapshot, *committed_interfaces;
    unsigned int frees_before;

    setup(&driver, &extension, &pdo, &retained, &file);
    IO24_CHECK(create_file(&driver, &retained, &file));
    context = file.FsContext;

    reset_initialize_buffers(&input, &output); reset_initialize_lower(); session_allocation_calls = 0;
    effect = call_initialize(&driver, &file, &input, &output, 72, 72,
            &input.request, output.bytes);
    memcpy(&snapshot, output.bytes, sizeof(snapshot));
    IO24_CHECK(effect.status == STATUS_BUFFER_TOO_SMALL && effect.information == 72);
    IO24_CHECK(effect.lower_after == effect.lower_before + 3 && descriptor_reads == 3 && select_calls == 0);
    IO24_CHECK(snapshot.size == 72 && snapshot.version == WINE_WINUSB_ABI_VERSION &&
            snapshot.session == 0 && snapshot.speed == HighSpeed && snapshot.total_size == 211);
    IO24_CHECK(snapshot.device_offset == 72 && snapshot.device_length == 18 &&
            snapshot.configuration_offset == 90 && snapshot.configuration_length == 41);
    IO24_CHECK(snapshot.interfaces_offset == 131 && snapshot.interface_count == 1 &&
            snapshot.alternates_offset == 147 && snapshot.alternate_count == 2 &&
            snapshot.endpoints_offset == 179 && snapshot.endpoint_count == 2);
    check_snapshot_tail(&output, 72); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); reset_initialize_lower(); session_allocation_calls = 0;
    effect = call_initialize(&driver, &file, &input, &output, 100, 100,
            &input.request, output.bytes);
    IO24_CHECK(effect.status == STATUS_BUFFER_TOO_SMALL && effect.information == 72);
    IO24_CHECK(effect.lower_after == effect.lower_before + 3 && select_calls == 0);
    check_snapshot_tail(&output, 72); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); reset_initialize_lower(); session_allocation_calls = 0; before = output;
    effect = call_initialize(&driver, &file, &input, &output, 212, 212,
            &input.request, output.bytes);
    IO24_CHECK(effect.status == STATUS_INVALID_PARAMETER && effect.information == 0);
    IO24_CHECK(effect.lower_after == effect.lower_before + 3 && select_calls == 0);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); reset_initialize_lower(); session_allocation_calls = 0;
    effect = call_initialize(&driver, &file, &input, &output, 211, 211,
            &input.request, output.bytes);
    memcpy(&snapshot, output.bytes, sizeof(snapshot)); first_session = snapshot.session;
    IO24_CHECK(effect.status == STATUS_SUCCESS && effect.information == 211);
    IO24_CHECK(effect.lower_after == effect.lower_before + 5 && descriptor_reads == 3 && select_calls == 1);
    IO24_CHECK(finalize_calls == 1 && finalize_commit_calls == 1 &&
            finalize_rollback_calls == 0 && !lower_claim_pending && lower_claim_committed);
    IO24_CHECK(session_allocation_calls == 6 && first_session != 0);
    check_exact_snapshot(&output, first_session);
    IO24_CHECK(context->state == WINUSB_FILE_INITIALIZED && context->session == first_session);
    IO24_CHECK(context->snapshot && context->snapshot != output.bytes && context->snapshot_size == 211);
    IO24_CHECK(context->interfaces && context->interface_count == 1);
    committed_snapshot = context->snapshot; committed_interfaces = context->interfaces;

    IO24_CHECK(create_file(&driver, &retained, &other));
    reset_initialize_buffers(&input, &output); input.request.session = first_session;
    frees_before = pool_frees;
    effect = call_release(&driver, &other, &input, sizeof(input.request));
    IO24_CHECK(!NT_SUCCESS(effect.status) && pool_frees == frees_before);
    IO24_CHECK(context->state == WINUSB_FILE_INITIALIZED && context->session == first_session &&
            context->snapshot == committed_snapshot && context->interfaces == committed_interfaces);
    check_file_uninitialized(&other);
    IO24_CHECK(dispatch_request(&driver, last_fdo, IRP_MJ_CLEANUP, 0,
            &retained, &other).status == STATUS_SUCCESS);
    IO24_CHECK(dispatch_request(&driver, last_fdo, IRP_MJ_CLOSE, 0,
            &retained, &other).status == STATUS_SUCCESS && other.FsContext == NULL);

    reset_initialize_buffers(&input, &output); reset_initialize_lower(); before = output;
    effect = call_initialize(&driver, &file, &input, &output, 211, 211,
            &input.request, output.bytes);
    IO24_CHECK(effect.status == STATUS_INVALID_DEVICE_STATE && effect.lower_after == effect.lower_before);
    IO24_CHECK(!memcmp(&output, &before, sizeof(output)));
    IO24_CHECK(context->session == first_session && context->snapshot == committed_snapshot &&
            context->interfaces == committed_interfaces);

#define IO24_REJECT_RELEASE(field, value) do { \
    reset_initialize_buffers(&input, &output); input.request.session = first_session; \
    input.request.field = (value); frees_before = pool_frees; \
    effect = call_release(&driver, &file, &input, sizeof(input.request)); \
    IO24_CHECK(!NT_SUCCESS(effect.status) && effect.information == 0); \
    IO24_CHECK(effect.lower_after == effect.lower_before && pool_frees == frees_before); \
    IO24_CHECK(context->state == WINUSB_FILE_INITIALIZED && context->session == first_session && \
            context->snapshot == committed_snapshot && context->interfaces == committed_interfaces); \
} while (0)
    IO24_REJECT_RELEASE(size, sizeof(input.request) - 1);
    IO24_REJECT_RELEASE(version, WINE_WINUSB_ABI_VERSION + 1);
    IO24_REJECT_RELEASE(reserved, 1);
    IO24_REJECT_RELEASE(interface_index, 1);
    IO24_REJECT_RELEASE(session, first_session + 1);
#undef IO24_REJECT_RELEASE

    reset_initialize_buffers(&input, &output); input.request.session = first_session;
    effect = call_release(&driver, &file, &input, sizeof(input.request) - 1);
    IO24_CHECK(!NT_SUCCESS(effect.status) && context->session == first_session);
    reset_initialize_buffers(&input, &output); input.request.session = first_session;
    frees_before = pool_frees;
    effect = call_release(&driver, &file, &input, sizeof(input.request));
    IO24_CHECK(effect.status == STATUS_SUCCESS && effect.information == 0);
    IO24_CHECK(effect.lower_after == effect.lower_before && pool_frees == frees_before + 2);
    check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); input.request.session = first_session;
    effect = call_release(&driver, &file, &input, sizeof(input.request));
    IO24_CHECK(!NT_SUCCESS(effect.status)); check_file_uninitialized(&file);

    reset_initialize_buffers(&input, &output); reset_initialize_lower(); session_allocation_calls = 0;
    effect = call_initialize(&driver, &file, &input, &output, 211, 211,
            &input.request, output.bytes);
    memcpy(&snapshot, output.bytes, sizeof(snapshot)); second_session = snapshot.session;
    IO24_CHECK(effect.status == STATUS_SUCCESS && second_session > first_session && second_session != 0);
    check_exact_snapshot(&output, second_session);
    reset_initialize_buffers(&input, &output); input.request.session = second_session;
    IO24_CHECK(call_release(&driver, &file, &input, sizeof(input.request)).status == STATUS_SUCCESS);
    check_file_uninitialized(&file);
    teardown(&driver, &retained, &file);
}

static void test_initialize_default_endpoint_select_layout(void)
{
    DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo;
    FILE_OBJECT file; struct guarded_request retained;
    struct guarded_initialize input; struct guarded_snapshot output;
    struct wine_winusb_snapshot snapshot;
    struct wine_winusb_interface_snapshot interface;
    struct wine_winusb_alternate_snapshot alternate;
    struct wine_winusb_endpoint_snapshot endpoint;
    struct winusb_file *context;
    struct dispatch_effect effect;

    setup(&driver, &extension, &pdo, &retained, &file);
    IO24_CHECK(create_file(&driver, &retained, &file));
    reset_initialize_buffers(&input, &output); reset_initialize_lower();
    memcpy(lower_configuration, default_endpoint_configuration,
            sizeof(default_endpoint_configuration));
    lower_configuration_size = lower_body_actual = sizeof(default_endpoint_configuration);
    expected_select_pipes = 1;
    expected_select_endpoint = 0x82;
    expected_select_type = UsbdPipeTypeBulk;
    expected_select_packet_size = 64;
    session_allocation_calls = 0;
    effect = call_initialize(&driver, &file, &input, &output, 163, 163,
            &input.request, output.bytes);
    memcpy(&snapshot, output.bytes, sizeof(snapshot));
    memcpy(&interface, output.bytes + 115, sizeof(interface));
    memcpy(&alternate, output.bytes + 131, sizeof(alternate));
    memcpy(&endpoint, output.bytes + 147, sizeof(endpoint));
    IO24_CHECK(effect.status == STATUS_SUCCESS && effect.information == 163);
    IO24_CHECK(descriptor_reads == 3 && select_calls == 1 &&
            finalize_calls == 1 && finalize_commit_calls == 1);
    IO24_CHECK(snapshot.total_size == 163 && snapshot.interfaces_offset == 115 &&
            snapshot.alternates_offset == 131 && snapshot.endpoints_offset == 147);
    IO24_CHECK(interface.interface_number == 5 && interface.first_alternate == 0 &&
            interface.alternate_count == 1);
    IO24_CHECK(alternate.interface_index == 0 && alternate.alternate_setting == 0 &&
            alternate.first_endpoint == 0 && alternate.endpoint_count == 1);
    IO24_CHECK(endpoint.alternate_index == 0 && endpoint.pipe_id == 0x82 &&
            endpoint.pipe_type == UsbdPipeTypeBulk && endpoint.maximum_packet_size == 64);
    context = file.FsContext;
    IO24_CHECK(context->interfaces[0].interface_number == 5 &&
            context->interfaces[0].alternate_setting == 0 &&
            context->interfaces[0].first_endpoint == 0 &&
            context->interfaces[0].endpoint_count == 1);
    teardown(&driver, &retained, &file);
}

static void test_initialize_allocation_and_lower_failures(void)
{
    unsigned int fail;

    for (fail = 1; fail <= 6; ++fail)
    {
        DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo;
        FILE_OBJECT file; struct guarded_request retained;
        struct guarded_initialize input; struct guarded_snapshot output, before;
        struct dispatch_effect effect;

        setup(&driver, &extension, &pdo, &retained, &file);
        IO24_CHECK(create_file(&driver, &retained, &file));
        reset_initialize_buffers(&input, &output); reset_initialize_lower();
        before = output; session_allocation_calls = 0; session_fail_allocation = fail;
        effect = call_initialize(&driver, &file, &input, &output, 211, 211,
                &input.request, output.bytes);
        IO24_CHECK(effect.status == STATUS_NO_MEMORY && effect.information == 0);
        IO24_CHECK(session_allocation_calls == fail && select_calls == 0);
        IO24_CHECK(descriptor_reads == (fail > 3 ? 3 : fail - 1));
        IO24_CHECK(effect.lower_after == effect.lower_before + descriptor_reads);
        IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file);
        session_fail_allocation = 0;
        teardown(&driver, &retained, &file);
    }

#define IO24_BUILDER_FAILURE(build_number, expected_reads) do { \
    DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo; \
    FILE_OBJECT file; struct guarded_request retained; struct guarded_initialize input; \
    struct guarded_snapshot output, before; struct dispatch_effect effect; \
    setup(&driver, &extension, &pdo, &retained, &file); IO24_CHECK(create_file(&driver, &retained, &file)); \
    reset_initialize_buffers(&input, &output); reset_initialize_lower(); before = output; \
    fail_urb_build = (build_number); session_allocation_calls = 0; \
    effect = call_initialize(&driver, &file, &input, &output, 211, 211, &input.request, output.bytes); \
    IO24_CHECK(effect.status == STATUS_NO_MEMORY && effect.information == 0); \
    IO24_CHECK(descriptor_reads == (expected_reads) && select_calls == 0); \
    IO24_CHECK(effect.lower_after == effect.lower_before + (expected_reads)); \
    IO24_CHECK(!memcmp(&output, &before, sizeof(output))); check_file_uninitialized(&file); \
    teardown(&driver, &retained, &file); \
} while (0)
    IO24_BUILDER_FAILURE(1, 0);
    IO24_BUILDER_FAILURE(4, 3);
#undef IO24_BUILDER_FAILURE

#define IO24_LOWER_FAILURE(which_nt, nt_value, which_urb, urb_value, expect_select) do { \
    DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo; \
    FILE_OBJECT file; struct guarded_request retained; struct guarded_initialize input; \
    struct guarded_snapshot output, before; struct dispatch_effect effect; \
    setup(&driver, &extension, &pdo, &retained, &file); IO24_CHECK(create_file(&driver, &retained, &file)); \
    reset_initialize_buffers(&input, &output); reset_initialize_lower(); before = output; \
    which_nt = (nt_value); which_urb = (urb_value); session_allocation_calls = 0; \
    effect = call_initialize(&driver, &file, &input, &output, 211, 211, &input.request, output.bytes); \
    IO24_CHECK(!NT_SUCCESS(effect.status) && effect.information == 0); \
    IO24_CHECK(select_calls == (expect_select)); IO24_CHECK(!memcmp(&output, &before, sizeof(output))); \
    IO24_CHECK(descriptor_reads == ((expect_select) ? 3u : 1u)); \
    IO24_CHECK(effect.lower_after == effect.lower_before + ((expect_select) ? 4u : 1u)); \
    check_file_uninitialized(&file); teardown(&driver, &retained, &file); \
} while (0)
    IO24_LOWER_FAILURE(descriptor_nt_status, STATUS_UNSUCCESSFUL,
            descriptor_urb_status, USBD_STATUS_SUCCESS, 0);
    IO24_LOWER_FAILURE(descriptor_nt_status, STATUS_SUCCESS,
            descriptor_urb_status, USBD_STATUS_STALL_PID, 0);
    IO24_LOWER_FAILURE(descriptor_nt_status, STATUS_SUCCESS,
            descriptor_writes_urb_status, FALSE, 0);
    IO24_LOWER_FAILURE(select_nt_status, STATUS_UNSUCCESSFUL,
            select_urb_status, USBD_STATUS_SUCCESS, 1);
    IO24_LOWER_FAILURE(select_nt_status, STATUS_SUCCESS,
            select_urb_status, USBD_STATUS_STALL_PID, 1);
    IO24_LOWER_FAILURE(select_nt_status, STATUS_SUCCESS,
            select_writes_urb_status, FALSE, 1);
#undef IO24_LOWER_FAILURE

    {
        DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo;
        FILE_OBJECT file; struct guarded_request retained;
        struct guarded_initialize input; struct guarded_snapshot output;
        struct dispatch_effect effect;

        setup(&driver, &extension, &pdo, &retained, &file);
        IO24_CHECK(create_file(&driver, &retained, &file));
        reset_initialize_buffers(&input, &output); reset_initialize_lower();
        lower_returns_pending = TRUE; session_allocation_calls = 0;
        effect = call_initialize(&driver, &file, &input, &output, 211, 211,
                &input.request, output.bytes);
        IO24_CHECK(effect.status == STATUS_SUCCESS && effect.information == 211);
        IO24_CHECK(descriptor_reads == 3 && select_calls == 1 &&
                finalize_calls == 1 && finalize_commit_calls == 1);
        IO24_CHECK(builder_allocations == 5 && builder_frees == 5);
        teardown(&driver, &retained, &file);
    }
}

static void test_initialized_remove_after_outstanding_drain(void);

static void test_initialize_post_select_transaction_finalization(void)
{
    DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo;
    FILE_OBJECT file; struct guarded_request retained;
    struct guarded_initialize input; struct guarded_snapshot output, before;
    struct dispatch_effect effect;
    struct winusb_file *context;

    setup(&driver,&extension,&pdo,&retained,&file);
    IO24_CHECK(create_file(&driver,&retained,&file));
    context=file.FsContext;
    reset_initialize_buffers(&input,&output);reset_initialize_lower();before=output;
    mutate_after_select=TRUE;session_allocation_calls=0;
    effect=call_initialize(&driver,&file,&input,&output,211,211,
            &input.request,output.bytes);
    IO24_CHECK(effect.status==STATUS_INVALID_DEVICE_STATE&&effect.information==0);
    IO24_CHECK(effect.lower_after==effect.lower_before+5);
    IO24_CHECK(descriptor_reads==3&&select_calls==1&&finalize_calls==1);
    IO24_CHECK(finalize_commit_calls==0&&finalize_rollback_calls==1);
    IO24_CHECK(rollback_saw_unpublished&&!lower_claim_pending&&!lower_claim_committed&&
            !lower_selected_state);
    IO24_CHECK(context->session==0&&context->snapshot==NULL&&context->interfaces==NULL);
    IO24_CHECK(!memcmp(&output,&before,sizeof(output)));
    teardown(&driver,&retained,&file);

    setup(&driver,&extension,&pdo,&retained,&file);
    IO24_CHECK(create_file(&driver,&retained,&file));
    reset_initialize_buffers(&input,&output);reset_initialize_lower();session_allocation_calls=0;
    effect=call_initialize(&driver,&file,&input,&output,211,211,
            &input.request,output.bytes);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.information==211);
    IO24_CHECK(effect.lower_after==effect.lower_before+5);
    IO24_CHECK(finalize_calls==1&&finalize_commit_calls==1&&finalize_rollback_calls==0);
    IO24_CHECK(!lower_claim_pending&&lower_claim_committed&&lower_selected_state);
    context=file.FsContext;
    IO24_CHECK(context->state==WINUSB_FILE_INITIALIZED&&context->session!=0&&
            context->snapshot!=NULL&&context->interfaces!=NULL);
    teardown(&driver,&retained,&file);
}

static void group_initialize(void)
{
    test_initialize_input_and_buffer_rejections();
    test_initialize_malformed_descriptors();
    test_initialize_size_full_release_reinitialize();
    test_initialize_default_endpoint_select_layout();
    test_initialize_allocation_and_lower_failures();
    test_initialize_post_select_transaction_finalization();
    test_initialized_remove_after_outstanding_drain();
}

static BOOL initialize_session(PDRIVER_OBJECT d,struct guarded_request *g,FILE_OBJECT *file)
{
    struct guarded_initialize input;struct guarded_snapshot output;struct dispatch_effect effect;
    struct wine_winusb_snapshot snapshot;
    reset_initialize_buffers(&input,&output);reset_initialize_lower();session_allocation_calls=0;
    effect=call_initialize(d,file,&input,&output,211,211,&input.request,output.bytes);
    memcpy(&snapshot,output.bytes,sizeof(snapshot));g->request.session=snapshot.session;
    IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(effect.lower_after==effect.lower_before+5);IO24_CHECK(effect.complete_after==effect.complete_before+1);
    IO24_CHECK(effect.information==211);IO24_CHECK(g->request.session!=0);
    return effect.status==STATUS_SUCCESS&&g->request.session!=0;
}
static void test_initialized_remove_after_outstanding_drain(void)
{
    DRIVER_OBJECT driver; DRIVER_EXTENSION extension; DEVICE_OBJECT pdo;
    FILE_OBJECT file; struct guarded_request guarded;
    struct winusb_device *device; struct expected_winusb_file *context;
    struct dispatch_effect effect;

    setup(&driver,&extension,&pdo,&guarded,&file);
    IO24_CHECK(create_file(&driver,&guarded,&file));
    IO24_CHECK(initialize_session(&driver,&guarded,&file));
    device=last_fdo->DeviceExtension;context=file.FsContext;
    IO24_CHECK(context->snapshot!=NULL&&context->interfaces!=NULL);
    context->outstanding=1;KeClearEvent(&context->zero_outstanding);
    IO24_CHECK(NT_SUCCESS(dispatch(&driver,last_fdo,IRP_MJ_PNP,
            IRP_MN_SURPRISE_REMOVAL)));
    effect=dispatch_request(&driver,last_fdo,IRP_MJ_CLEANUP,0,&guarded,&file);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&file.FsContext==context);
    memset(&lifecycle_wait,0,sizeof(lifecycle_wait));
    lifecycle_wait.driver=&driver;lifecycle_wait.guarded=&guarded;
    lifecycle_wait.file=&file;lifecycle_wait.device=device;
    lifecycle_wait.context=context;lifecycle_wait.frees_before=pool_frees;
    lifecycle_wait.expected_close_frees=3;wait_hook=lifecycle_wait_hook;
    IO24_CHECK(NT_SUCCESS(dispatch(&driver,last_fdo,IRP_MJ_PNP,
            IRP_MN_REMOVE_DEVICE)));
    IO24_CHECK(lifecycle_wait.removal_waits==1&&lifecycle_wait.drain_waits==1);
    IO24_CHECK(wait_failures==0&&file.FsContext==NULL);
    IO24_CHECK(pool_frees==lifecycle_wait.frees_before+3);
    IO24_CHECK(pool_allocations==pool_frees);wait_hook=NULL;
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
    ((struct expected_winusb_file *)second_context)->outstanding=1;
    KeClearEvent(&((struct expected_winusb_file *)second_context)->zero_outstanding);
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
    memset(&lifecycle_wait,0,sizeof(lifecycle_wait));
    lifecycle_wait.driver=&d;lifecycle_wait.guarded=&g;lifecycle_wait.file=&second;
    lifecycle_wait.device=device;lifecycle_wait.context=second_context;lifecycle_wait.frees_before=pool_frees;
    lifecycle_wait.expected_close_frees=1;
    wait_hook=lifecycle_wait_hook;
    IO24_CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE)));
    IO24_CHECK(lifecycle_wait.removal_waits==1&&lifecycle_wait.drain_waits==1);
    IO24_CHECK(wait_failures==0&&second.FsContext==NULL&&pool_frees==2);
    wait_hook=NULL;
}
static void group_session(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;setup(&d,&e,&p,&g,&file);create_file(&d,&g,&file);initialize_session(&d,&g,&file);teardown(&d,&g,&file);}
static void group_alternate(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;struct dispatch_effect effect;uint32_t generation;BOOL opened,initialized;setup(&d,&e,&p,&g,&file);opened=create_file(&d,&g,&file);initialized=initialize_session(&d,&g,&file);g.request.value=1;if(!opened||!initialized){dispatch_safe_rejection(&d,&g,&file,IO24_IOCTL_SET_ALTERNATE);teardown(&d,&g,&file);return;}generation=g.request.generation;effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_SET_ALTERNATE,&g,&file);IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(effect.lower_after==effect.lower_before+1);IO24_CHECK(effect.complete_after==effect.complete_before+1);IO24_CHECK(g.request.generation==generation+1);teardown(&d,&g,&file);}
static void group_policy(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;struct dispatch_effect effect;BOOL opened,initialized;setup(&d,&e,&p,&g,&file);opened=create_file(&d,&g,&file);initialized=initialize_session(&d,&g,&file);g.request.value=7;if(!opened||!initialized){dispatch_safe_rejection(&d,&g,&file,IO24_IOCTL_SET_POLICY);teardown(&d,&g,&file);return;}effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_SET_POLICY,&g,&file);IO24_CHECK(effect.status==STATUS_SUCCESS);IO24_CHECK(effect.lower_after==effect.lower_before);IO24_CHECK(effect.complete_after==effect.complete_before+1);teardown(&d,&g,&file);}
static void group_transfer(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;struct dispatch_effect effect;BOOL opened,initialized;setup(&d,&e,&p,&g,&file);opened=create_file(&d,&g,&file);initialized=initialize_session(&d,&g,&file);if(!opened||!initialized){dispatch_safe_rejection(&d,&g,&file,IO24_IOCTL_READ_PIPE);teardown(&d,&g,&file);return;}g.request.value=1;effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_SET_ALTERNATE,&g,&file);IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.lower_after==effect.lower_before+1);effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_READ_PIPE,&g,&file);IO24_CHECK(effect.status==STATUS_PENDING);IO24_CHECK(effect.lower_after==effect.lower_before+1);IO24_CHECK(effect.complete_after==effect.complete_before);teardown(&d,&g,&file);}
static void run(const char*m){if(!strcmp(m,"--red")||!strcmp(m,"--lifecycle"))group_lifecycle();if(!strcmp(m,"--red")||!strcmp(m,"--initialize"))group_initialize();if(!strcmp(m,"--red")||!strcmp(m,"--session"))group_session();if(!strcmp(m,"--red")||!strcmp(m,"--alternate"))group_alternate();if(!strcmp(m,"--red")||!strcmp(m,"--policy"))group_policy();if(!strcmp(m,"--red")||!strcmp(m,"--transfer"))group_transfer();}
int main(int argc,char**argv){unsigned int retained;if(argc!=2)return 2;retained=io24_retained_cp32_main();if(retained){fprintf(stderr,"HARNESS: retained fake-WDM baseline failed\n");return 2;}run(argv[1]);printf("CP33 function executed mode=%s dispatches=%u mode-ioctls=%u last-ioctl=%#lx last-status=%#lx failures=%u\n",argv[1],counts.submits,mode_ioctls,(unsigned long)last_ioctl,(unsigned long)last_status,counts.failures);return counts.failures?1:0;}
