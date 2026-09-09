/* Offline CP32 contract: compile the real winusb.sys driver into a fake WDM. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ntstatus.h"
#include "windef.h"
#include "winternl.h"
#include "ddk/wdm.h"
#include "winusbio.h"
#include "winusb_busif.h"
#include "wine/debug.h"

#undef WINE_DEFAULT_DEBUG_CHANNEL
#undef TRACE
#undef WARN
#define WINE_DEFAULT_DEBUG_CHANNEL(name)
#define TRACE(...) ((void)0)
#define WARN(...) ((void)0)

static unsigned int failures, references, dereferences, creates, attaches, detaches;
static unsigned int registrations, enables, disables, frees, deletes, lower_calls, completes;
static unsigned int pool_allocations, pool_frees, speed_queries, fail_next_pool_allocation;
static NTSTATUS query_status = STATUS_SUCCESS, getter_status = STATUS_SUCCESS, speed_status = STATUS_SUCCESS;
static NTSTATUS create_status = STATUS_SUCCESS, attach_status = STATUS_SUCCESS;
static NTSTATUS register_status = STATUS_SUCCESS, lower_status = STATUS_SUCCESS;
static NTSTATUS enable_status = STATUS_SUCCESS, disable_status = STATUS_SUCCESS;
static USHORT query_returned_size, query_returned_version;
static BOOLEAN query_omits_getter, query_omits_speed;
static UCHAR query_returned_speed;
static PDEVICE_OBJECT last_fdo, current_pdo;
static IRP synchronous_irp;
static IO_STACK_LOCATION synchronous_stack[2];
static PKEVENT synchronous_event;
static PIO_STATUS_BLOCK synchronous_iosb;
static BOOLEAN registration_returns_partial_link;
static char trace[512];

static const GUID expected_interface_guid =
    {0x6b3c1a02, 0x9f2e, 0x4a83, {0x91,0x77,0x35,0x46,0x9b,0x10,0x42,0xee}};
static const GUID expected_metadata_guid =
    WINEUSB_MS_OS_10_METADATA_INTERFACE_INIT;

#define CHECK(x, ...) do { if (!(x)) { fprintf(stderr, "FAIL %s:%u: ", __func__, __LINE__); \
    fprintf(stderr, __VA_ARGS__); fputc('\n', stderr); failures++; } } while (0)
#define RECORD(x) do { strcat(trace, x ","); } while (0)

static void WINAPI metadata_ref(void *context) { CHECK(context == current_pdo, "wrong metadata context"); references++; RECORD("ref"); }
static void WINAPI metadata_deref(void *context) { CHECK(context == current_pdo, "wrong metadata context"); dereferences++; RECORD("deref"); }
static NTSTATUS WINAPI get_guid(void *context, GUID *guid)
{
    CHECK(context == current_pdo, "wrong getter context"); RECORD("get");
    if (NT_SUCCESS(getter_status)) *guid = expected_interface_guid;
    return getter_status;
}
static NTSTATUS WINAPI get_speed(void *context, UCHAR *speed)
{
    CHECK(context == current_pdo, "wrong speed context"); speed_queries++; RECORD("speed");
    if (NT_SUCCESS(speed_status)) *speed = query_returned_speed;
    return speed_status;
}

/* main.c is deliberately included: this is the production driver, not a copy. */
#include "main.c"

NTSTATUS WINAPI IoCreateDevice(PDRIVER_OBJECT driver, ULONG extension, UNICODE_STRING *name,
        DEVICE_TYPE type, ULONG characteristics, BOOLEAN exclusive, PDEVICE_OBJECT *out)
{
    DEVICE_OBJECT *object;
    (void)name; (void)type; (void)characteristics; (void)exclusive; RECORD("create"); creates++;
    if (!NT_SUCCESS(create_status)) return create_status;
    object = calloc(1, sizeof(*object));
    object->DriverObject = driver; object->Flags = DO_DEVICE_INITIALIZING;
    object->DeviceExtension = calloc(1, extension); object->NextDevice = driver->DeviceObject;
    driver->DeviceObject = object; *out = object; last_fdo = object;
    return STATUS_SUCCESS;
}
VOID WINAPI IoDeleteDevice(PDEVICE_OBJECT object)
{
    RECORD("delete"); deletes++;
    if (object->DriverObject && object->DriverObject->DeviceObject == object)
        object->DriverObject->DeviceObject = object->NextDevice;
    free(object->DeviceExtension); free(object);
}
PDEVICE_OBJECT WINAPI IoAttachDeviceToDeviceStack(PDEVICE_OBJECT source, PDEVICE_OBJECT target)
{
    RECORD("attach"); attaches++; if (!NT_SUCCESS(attach_status)) return NULL;
    source->AttachedDevice = target; return target;
}
VOID WINAPI IoDetachDevice(PDEVICE_OBJECT target) { (void)target; RECORD("detach"); detaches++; }
NTSTATUS WINAPI IoRegisterDeviceInterface(PDEVICE_OBJECT pdo, const GUID *guid,
        PUNICODE_STRING ref, PUNICODE_STRING link)
{
    static WCHAR names[][13] = {{'\\','?','?','\\','w','i','n','u','s','b','-', '0', 0},
                                {'\\','?','?','\\','w','i','n','u','s','b','-', '1', 0}};
    (void)pdo; (void)guid; (void)ref; RECORD("register"); registrations++;
    CHECK(pdo == current_pdo, "registered against wrong PDO");
    CHECK(IsEqualGUID(guid, &expected_interface_guid), "registered the wrong device-interface GUID");
    if (NT_SUCCESS(register_status) || registration_returns_partial_link)
    {
        link->Buffer = names[(registrations - 1) & 1]; link->Length = (ARRAY_SIZE(names[0]) - 1) * sizeof(WCHAR);
        link->MaximumLength = sizeof(names[0]);
    }
    return register_status;
}
NTSTATUS WINAPI IoSetDeviceInterfaceState(UNICODE_STRING *link, BOOLEAN enable)
{
    CHECK(link && link->Buffer, "interface link was not retained"); RECORD(enable ? "enable" : "disable");
    if (enable) { enables++; return enable_status; } disables++; return disable_status;
}
VOID WINAPI RtlFreeUnicodeString(PUNICODE_STRING string) { RECORD("free"); frees++; string->Buffer = NULL; string->Length = string->MaximumLength = 0; }
VOID WINAPI IoCompleteRequest(PIRP irp, UCHAR boost) { (void)boost; completes++; RECORD("complete"); }
PVOID WINAPI ExAllocatePool(POOL_TYPE type, SIZE_T size)
{
    (void)type; pool_allocations++;
    if (fail_next_pool_allocation) { fail_next_pool_allocation = 0; return NULL; }
    return calloc(1, size);
}
VOID WINAPI ExFreePool(PVOID ptr) { if (ptr) { pool_frees++; free(ptr); } }
KIRQL WINAPI KeAcquireSpinLockRaiseToDpc(KSPIN_LOCK *lock) { (void)lock; return 0; }
void WINAPI KeReleaseSpinLock(KSPIN_LOCK *lock, KIRQL irql) { (void)lock; (void)irql; }
void WINAPI KeClearEvent(PRKEVENT event) { event->Header.SignalState = 0; }

static NTSTATUS WINAPI lower_dispatch(PDEVICE_OBJECT device, PIRP irp)
{
    PIO_STACK_LOCATION stack = irp->Tail.Overlay.CurrentStackLocation;
    (void)device; lower_calls++;
    if (stack->MajorFunction == IRP_MJ_PNP && stack->MinorFunction == IRP_MN_QUERY_INTERFACE)
    {
        struct wineusb_ms_os_10_metadata_interface_v2 *iface = (void *)stack->Parameters.QueryInterface.Interface;
        RECORD("query");
        CHECK(IsEqualGUID(stack->Parameters.QueryInterface.InterfaceType, &expected_metadata_guid), "wrong metadata query GUID");
        CHECK(stack->Parameters.QueryInterface.Size == sizeof(*iface), "wrong metadata query size %u", stack->Parameters.QueryInterface.Size);
        CHECK(stack->Parameters.QueryInterface.Version == WINEUSB_MS_OS_10_METADATA_VERSION_2,
                "wrong metadata query version %u", stack->Parameters.QueryInterface.Version);
        if (NT_SUCCESS(query_status))
        {
            iface->Size = query_returned_size; iface->Version = query_returned_version; iface->BusContext = current_pdo;
            iface->InterfaceReference = metadata_ref; iface->InterfaceDereference = metadata_deref;
            iface->GetDeviceInterfaceGuid = query_omits_getter ? NULL : get_guid;
            iface->GetDeviceSpeed = query_omits_speed ? NULL : get_speed; metadata_ref(current_pdo);
        }
        irp->IoStatus.Status = query_status; return query_status;
    }
    RECORD("lower"); irp->IoStatus.Status = lower_status; return lower_status;
}
NTSTATUS WINAPI IoCallDriver(PDEVICE_OBJECT device, PIRP irp)
{
    PIO_STACK_LOCATION current = irp->Tail.Overlay.CurrentStackLocation;
    NTSTATUS status;

    irp->Tail.Overlay.CurrentStackLocation = current - 1;
    status = lower_dispatch(device, irp);
    irp->Tail.Overlay.CurrentStackLocation = current;
    if (irp == &synchronous_irp)
    {
        if (synchronous_iosb) *synchronous_iosb = irp->IoStatus;
        if (synchronous_event) synchronous_event->Header.SignalState = 1;
    }
    return status;
}

/* The driver uses a synchronous local IRP for metadata query and PnP forwarding. */
PIRP WINAPI IoBuildSynchronousFsdRequest(ULONG major, PDEVICE_OBJECT device, PVOID buffer,
        ULONG length, PLARGE_INTEGER offset, PKEVENT event, PIO_STATUS_BLOCK iosb)
{
    (void)device; (void)buffer; (void)length; (void)offset; RECORD("build");
    memset(&synchronous_irp, 0, sizeof(synchronous_irp)); memset(synchronous_stack, 0, sizeof(synchronous_stack));
    synchronous_stack[0].MajorFunction = major;
    synchronous_irp.Tail.Overlay.CurrentStackLocation = &synchronous_stack[1];
    synchronous_event = event; synchronous_iosb = iosb;
    return &synchronous_irp;
}
VOID WINAPI KeInitializeEvent(PRKEVENT event, EVENT_TYPE type, BOOLEAN state)
{ (void)type; event->Header.SignalState = state; }
LONG WINAPI KeSetEvent(PRKEVENT event, KPRIORITY increment, BOOLEAN wait)
{ (void)increment; (void)wait; event->Header.SignalState = 1; return 0; }
NTSTATUS WINAPI KeWaitForSingleObject(void *object, KWAIT_REASON reason, KPROCESSOR_MODE mode,
        BOOLEAN alertable, LARGE_INTEGER *timeout)
{ (void)reason; (void)mode; (void)alertable; (void)timeout; CHECK(((PKEVENT)object)->Header.SignalState, "synchronous request was not completed"); return STATUS_SUCCESS; }

static void reset(void)
{
    references = dereferences = creates = attaches = detaches = registrations = enables = disables = frees = deletes = lower_calls = completes = 0;
    pool_allocations = pool_frees = speed_queries = fail_next_pool_allocation = 0;
    query_status = getter_status = speed_status = create_status = attach_status = register_status = lower_status = enable_status = disable_status = STATUS_SUCCESS;
    query_returned_size = sizeof(struct wineusb_ms_os_10_metadata_interface_v2);
    query_returned_version = WINEUSB_MS_OS_10_METADATA_VERSION_2; query_returned_speed = HighSpeed;
    last_fdo = NULL; synchronous_event = NULL; synchronous_iosb = NULL; registration_returns_partial_link = FALSE;
    query_omits_getter = query_omits_speed = FALSE; trace[0] = 0;
}
static NTSTATUS add(PDRIVER_OBJECT driver, PDEVICE_OBJECT pdo)
{ current_pdo = pdo; return driver->DriverExtension->AddDevice(driver, pdo); }
static NTSTATUS dispatch(PDRIVER_OBJECT driver, PDEVICE_OBJECT fdo, UCHAR major, UCHAR minor)
{
    IRP irp; IO_STACK_LOCATION stack[2]; memset(&irp, 0, sizeof(irp)); memset(stack, 0, sizeof(stack));
    stack[1].MajorFunction = major; stack[1].MinorFunction = minor; irp.Tail.Overlay.CurrentStackLocation = &stack[1];
    driver->MajorFunction[major](fdo, &irp); CHECK(irp.IoStatus.Information == 0, "information %#lx", (long)irp.IoStatus.Information);
    return irp.IoStatus.Status;
}
static void initialize(PDRIVER_OBJECT driver, DRIVER_EXTENSION *extension, DEVICE_OBJECT *pdo)
{
    memset(driver, 0, sizeof(*driver)); memset(extension, 0, sizeof(*extension)); memset(pdo, 0, sizeof(*pdo));
    driver->DriverExtension = extension; pdo->DriverObject = driver;
    CHECK(DriverEntry(driver, NULL) == STATUS_SUCCESS, "DriverEntry failed");
    CHECK(driver->DriverExtension->AddDevice, "AddDevice missing"); CHECK(driver->MajorFunction[IRP_MJ_PNP], "PnP dispatch missing");
}
static struct winusb_device *extension(void) { return last_fdo ? last_fdo->DeviceExtension : NULL; }

static void test_add_start_stop_restart_remove(void)
{
    DRIVER_OBJECT driver; DRIVER_EXTENSION ext; DEVICE_OBJECT pdo; struct winusb_device *dev; NTSTATUS status;
    reset(); initialize(&driver, &ext, &pdo); status = add(&driver, &pdo); dev = extension();
    CHECK(status == STATUS_SUCCESS && dev, "AddDevice %#lx", (long)status);
    CHECK(references == 1 && dereferences == 1, "unbalanced metadata refs %u/%u", references, dereferences);
    CHECK(dev->pdo == &pdo && dev->lower_device == &pdo && dev->registered && !dev->enabled, "bad added extension state");
    CHECK(!dev->lock && dev->files.Flink == &dev->files && dev->files.Blink == &dev->files &&
            !dev->file_count && dev->removal_event.Header.SignalState,
            "bad initial file/removal state");
    CHECK(dev->metadata_interface_version == WINEUSB_MS_OS_10_METADATA_VERSION_2 && dev->speed == HighSpeed,
            "bad cached metadata version/speed %u/%#x", dev->metadata_interface_version, dev->speed);
    CHECK(!(last_fdo->Flags & DO_DEVICE_INITIALIZING), "published before initialization completed");
    CHECK(!strcmp(trace, "build,query,ref,get,speed,deref,create,attach,register,"), "add trace %s", trace);
    status = dispatch(&driver, last_fdo, IRP_MJ_PNP, IRP_MN_START_DEVICE); CHECK(status == STATUS_SUCCESS && dev->enabled, "start %#lx", (long)status);
    status = dispatch(&driver, last_fdo, IRP_MJ_PNP, IRP_MN_STOP_DEVICE); CHECK(status == STATUS_SUCCESS && dev->enabled, "stop disabled interface");
    status = dispatch(&driver, last_fdo, IRP_MJ_PNP, IRP_MN_START_DEVICE); CHECK(status == STATUS_SUCCESS && enables == 1, "restart reenabled interface");
    status = dispatch(&driver, last_fdo, IRP_MJ_PNP, IRP_MN_REMOVE_DEVICE); CHECK(status == STATUS_SUCCESS, "remove %#lx", (long)status);
    CHECK(disables == 1 && detaches == 1 && frees == 1 && deletes == 1, "remove cleanup %u/%u/%u/%u", disables, detaches, frees, deletes);
}
static void test_add_failures_are_balanced(void)
{
    DRIVER_OBJECT d; DRIVER_EXTENSION e; DEVICE_OBJECT p;
    reset(); initialize(&d,&e,&p); query_status = STATUS_NOT_SUPPORTED; CHECK(!NT_SUCCESS(add(&d,&p)), "missing metadata query accepted"); CHECK(!references && !dereferences && !creates && !last_fdo, "query failure leaked refs/FDO");
    reset(); initialize(&d,&e,&p); query_returned_version = 1; CHECK(!NT_SUCCESS(add(&d,&p)), "wrong metadata interface version accepted"); CHECK(references == dereferences && !creates, "invalid metadata interface leaked refs/FDO");
    reset(); initialize(&d,&e,&p); query_returned_size--; CHECK(!NT_SUCCESS(add(&d,&p)), "short metadata interface accepted"); CHECK(references == dereferences && !creates, "short metadata interface leaked refs/FDO");
    reset(); initialize(&d,&e,&p); query_omits_getter = TRUE; CHECK(!NT_SUCCESS(add(&d,&p)), "missing metadata getter accepted"); CHECK(references == dereferences && !creates, "missing metadata getter leaked refs/FDO");
    reset(); initialize(&d,&e,&p); query_omits_speed = TRUE; CHECK(!NT_SUCCESS(add(&d,&p)), "missing metadata speed getter accepted"); CHECK(references == dereferences && !creates, "missing metadata speed getter leaked refs/FDO");
    reset(); initialize(&d,&e,&p); getter_status = STATUS_NOT_FOUND; CHECK(!NT_SUCCESS(add(&d,&p)), "getter failure accepted"); CHECK(references == dereferences && !creates, "getter cleanup refs=%u/%u creates=%u", references,dereferences,creates);
    reset(); initialize(&d,&e,&p); speed_status = STATUS_DEVICE_NOT_CONNECTED; CHECK(!NT_SUCCESS(add(&d,&p)), "speed failure accepted"); CHECK(references == dereferences && !creates, "speed failure cleanup refs=%u/%u creates=%u", references,dereferences,creates);
    reset(); initialize(&d,&e,&p); query_returned_speed = SuperSpeed; CHECK(!NT_SUCCESS(add(&d,&p)), "noncanonical speed accepted"); CHECK(references == dereferences && !creates, "invalid speed leaked refs/FDO");
    reset(); initialize(&d,&e,&p); create_status = STATUS_NO_MEMORY; CHECK(!NT_SUCCESS(add(&d,&p)) && !attaches && !registrations, "create failure leaked construction");
    reset(); initialize(&d,&e,&p); attach_status = STATUS_NO_SUCH_DEVICE; CHECK(!NT_SUCCESS(add(&d,&p)) && deletes == 1 && !registrations, "attach cleanup missing");
    reset(); initialize(&d,&e,&p); register_status = STATUS_UNSUCCESSFUL; registration_returns_partial_link = TRUE; CHECK(!NT_SUCCESS(add(&d,&p)) && detaches == 1 && frees == 1 && deletes == 1, "partial registration cleanup missing");
}
static void test_start_surprise_and_failed_disable_retry(void)
{
    DRIVER_OBJECT d; DRIVER_EXTENSION e; DEVICE_OBJECT p; struct winusb_device *dev;
    reset(); initialize(&d,&e,&p); add(&d,&p); dev=extension(); lower_status=STATUS_UNSUCCESSFUL; CHECK(!NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_START_DEVICE)) && !dev->enabled, "failed first start enabled");
    lower_status=STATUS_SUCCESS; enable_status=STATUS_UNSUCCESSFUL; CHECK(!NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_START_DEVICE)) && !dev->enabled, "enable failure retained enabled");
    enable_status=STATUS_SUCCESS; CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_START_DEVICE)), "start failed"); disable_status=STATUS_UNSUCCESSFUL;
    CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_STOP_DEVICE)), "stop unexpectedly failed"); lower_status=STATUS_UNSUCCESSFUL;
    CHECK(!NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_START_DEVICE)) && dev->enabled, "failed restart did not retain retry state"); lower_status=STATUS_SUCCESS;
    trace[0] = 0;
    CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_SURPRISE_REMOVAL)) && dev->enabled, "surprise removal lost failed disable retry");
    CHECK(!strcmp(trace, "disable,lower,complete,"), "surprise-removal order %s", trace);
    CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE)) && detaches == 1 && deletes == 1, "mandatory teardown blocked");
    CHECK(disables == 3, "expected three bounded disable attempts, got %u", disables);
}
static void test_informational_distinct_and_no_io(void)
{
    DRIVER_OBJECT d; DRIVER_EXTENSION e; DEVICE_OBJECT a,b; PDEVICE_OBJECT first; struct winusb_device *one, *two; unsigned int i;
    reset(); initialize(&d,&e,&a); register_status=STATUS_OBJECT_NAME_EXISTS; CHECK(NT_SUCCESS(add(&d,&a)), "informational registration rejected"); first=last_fdo; one=extension(); CHECK(NT_SUCCESS(add(&d,&b)) && last_fdo != first, "same GUID PDOs shared an FDO"); two=extension();
    CHECK(one->symbolic_link.Buffer != two->symbolic_link.Buffer, "same-GUID PDOs shared a symbolic link");
    for (i=0; i<5; i++) { static const UCHAR major[] = {IRP_MJ_CREATE,IRP_MJ_READ,IRP_MJ_WRITE,IRP_MJ_DEVICE_CONTROL,IRP_MJ_INTERNAL_DEVICE_CONTROL}; CHECK(dispatch(&d,last_fdo,major[i],0)==STATUS_NOT_SUPPORTED, "I/O major %#x accepted",major[i]); }
    CHECK(dispatch(&d,last_fdo,IRP_MJ_CLOSE,0)==STATUS_SUCCESS, "close was not idempotent success");
    CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE)), "remove second PDO");
    CHECK(NT_SUCCESS(dispatch(&d,first,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE)), "remove first PDO");
}
static void test_remove_before_start_and_failed_start_cleanup(void)
{
    DRIVER_OBJECT d; DRIVER_EXTENSION e; DEVICE_OBJECT p;
    reset(); initialize(&d,&e,&p); CHECK(NT_SUCCESS(add(&d,&p)), "add failed");
    CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE)), "remove-before-start failed");
    CHECK(enables == 0 && !strstr(trace, "disable,"), "remove-before-start disabled an unenabled interface");
    reset(); initialize(&d,&e,&p); CHECK(NT_SUCCESS(add(&d,&p)), "add failed"); lower_status=STATUS_UNSUCCESSFUL;
    CHECK(!NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_START_DEVICE)), "failed start accepted");
    lower_status=STATUS_SUCCESS;
    CHECK(NT_SUCCESS(dispatch(&d,last_fdo,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE)), "failed-start removal failed");
    CHECK(detaches == 1 && frees == 1 && deletes == 1 && !strstr(trace, "disable,"), "failed-start teardown incorrect: %s", trace);
}
int main(void)
{
    test_add_start_stop_restart_remove(); test_add_failures_are_balanced(); test_start_surprise_and_failed_disable_retry(); test_informational_distinct_and_no_io(); test_remove_before_start_and_failed_start_cleanup();
    if (failures) { fprintf(stderr, "%u CP32 function-binding checks failed\n", failures); return 1; }
    puts("CP32 winusb function-binding lifecycle checks passed"); return 0;
}
