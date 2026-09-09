/*
 * Generic WinUSB function driver
 *
 * Copyright 2026 the Wine project
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This layer deliberately implements only Plug and Play binding and device-
 * interface lifetime. WinUSB transfer semantics belong to a later layer.
 */

#include <stdarg.h>
#include <string.h>

#include "ntstatus.h"
#include "windef.h"
#include "winternl.h"
#include "ddk/wdm.h"

#include "wine/debug.h"
#include "winusbio.h"

#include "../wineusb.sys/winusb_busif.h"
#include "winusb_private.h"

WINE_DEFAULT_DEBUG_CHANNEL(winusb);

static const GUID metadata_interface =
        WINEUSB_MS_OS_10_METADATA_INTERFACE_INIT;

unsigned int r136_mutant_failed_helper_calls, r136_mutant_failed_helper_frees;
BOOL r136_mutant_failed_completion_arm, r136_mutant_failed_helper_returned_null;

PVOID WINAPI r136_mutant_main_allocate(SIZE_T size)
{
    PVOID pointer;

    ++r136_mutant_failed_helper_calls;
    pointer = ExAllocatePool(NonPagedPool, size);
    r136_mutant_failed_helper_returned_null = !pointer;
    return pointer;
}

VOID WINAPI r136_mutant_main_free(PVOID pointer)
{
    if (pointer) ++r136_mutant_failed_helper_frees;
    ExFreePool(pointer);
}

static NTSTATUS WINAPI set_event_completion(DEVICE_OBJECT *device, IRP *irp,
        void *context)
{
    if (irp->PendingReturned) KeSetEvent(context, IO_NO_INCREMENT, FALSE);
    return STATUS_MORE_PROCESSING_REQUIRED;
}

static NTSTATUS forward_irp_synchronously(struct winusb_device *device, IRP *irp)
{
    KEVENT event;
    NTSTATUS status;

    KeInitializeEvent(&event, NotificationEvent, FALSE);
    IoCopyCurrentIrpStackLocationToNext(irp);
    IoSetCompletionRoutine(irp, set_event_completion, &event, TRUE, TRUE, TRUE);

    status = IoCallDriver(device->lower_device, irp);
    if (status == STATUS_PENDING)
        KeWaitForSingleObject(&event, Executive, KernelMode, FALSE, NULL);
    return irp->IoStatus.Status;
}

static NTSTATUS query_metadata_interface(DEVICE_OBJECT *pdo, GUID *guid,
        USHORT *metadata_version, UCHAR *speed)
{
    struct wineusb_ms_os_10_metadata_interface_v2 interface = {0};
    IO_STACK_LOCATION *stack;
    IO_STATUS_BLOCK io_status = {{STATUS_NOT_SUPPORTED}, 0};
    KEVENT event;
    GUID queried_guid;
    UCHAR queried_speed = 0;
    NTSTATUS status;
    IRP *irp;

    KeInitializeEvent(&event, NotificationEvent, FALSE);
    if (!(irp = IoBuildSynchronousFsdRequest(IRP_MJ_PNP, pdo, NULL, 0, NULL,
            &event, &io_status)))
        return STATUS_NO_MEMORY;

    stack = IoGetNextIrpStackLocation(irp);
    stack->MinorFunction = IRP_MN_QUERY_INTERFACE;
    stack->Parameters.QueryInterface.InterfaceType =
            &metadata_interface;
    stack->Parameters.QueryInterface.Size = sizeof(interface);
    stack->Parameters.QueryInterface.Version =
            WINEUSB_MS_OS_10_METADATA_VERSION_2;
    stack->Parameters.QueryInterface.Interface = (INTERFACE *)&interface;
    stack->Parameters.QueryInterface.InterfaceSpecificData = NULL;
    irp->IoStatus.Status = STATUS_NOT_SUPPORTED;

    status = IoCallDriver(pdo, irp);
    if (status == STATUS_PENDING)
        KeWaitForSingleObject(&event, Executive, KernelMode, FALSE, NULL);
    status = io_status.Status;
    if (!NT_SUCCESS(status)) return status;

    if (interface.Size != sizeof(interface) ||
            interface.Version != WINEUSB_MS_OS_10_METADATA_VERSION_2 ||
            !interface.BusContext || !interface.InterfaceReference ||
            !interface.InterfaceDereference ||
            !interface.GetDeviceInterfaceGuid || !interface.GetDeviceSpeed)
    {
        if (interface.BusContext && interface.InterfaceDereference)
            interface.InterfaceDereference(interface.BusContext);
        return STATUS_NOT_SUPPORTED;
    }

    status = interface.GetDeviceInterfaceGuid(interface.BusContext, &queried_guid);
    if (NT_SUCCESS(status))
        status = interface.GetDeviceSpeed(interface.BusContext, &queried_speed);
    interface.InterfaceDereference(interface.BusContext);
    if (!NT_SUCCESS(status)) return status;
    if (queried_speed != LowSpeed && queried_speed != HighSpeed)
        return STATUS_NOT_SUPPORTED;

    *guid = queried_guid;
    *metadata_version = interface.Version;
    *speed = queried_speed;
    return status;
}

static void disable_interface(struct winusb_device *device, const char *phase)
{
    NTSTATUS status;

    if (!device->enabled) return;
    status = IoSetDeviceInterfaceState(&device->symbolic_link, FALSE);
    if (NT_SUCCESS(status) || status == STATUS_OBJECT_NAME_NOT_FOUND)
        device->enabled = FALSE;
    else
        WARN("Failed to disable interface %s during %s, status %#lx.\n",
                debugstr_w(device->symbolic_link.Buffer), phase,
                (unsigned long)status);
}

static NTSTATUS complete_irp(IRP *irp, NTSTATUS status)
{
    irp->IoStatus.Status = status;
    irp->IoStatus.Information = 0;
    IoCompleteRequest(irp, IO_NO_INCREMENT);
    return status;
}

static NTSTATUS complete_irp_with_information(IRP *irp, NTSTATUS status,
        ULONG_PTR information)
{
    irp->IoStatus.Status = status;
    irp->IoStatus.Information = information;
    IoCompleteRequest(irp, IO_NO_INCREMENT);
    return status;
}

static BOOL file_is_linked(const struct winusb_device *device,
        const struct winusb_file *file, const FILE_OBJECT *file_object)
{
    const LIST_ENTRY *entry;

    for (entry = device->files.Flink; entry != &device->files; entry = entry->Flink)
    {
        const struct winusb_file *linked = CONTAINING_RECORD(entry,
                struct winusb_file, device_entry);
        if (linked == file) return linked->file_object == file_object;
    }
    return FALSE;
}

static NTSTATUS acquire_file_for_io(struct winusb_device *device,
        FILE_OBJECT *file_object, struct winusb_file **ret_file)
{
    struct winusb_file *file;
    KIRQL device_irql, file_irql;
    NTSTATUS status = STATUS_INVALID_DEVICE_STATE;

    KeAcquireSpinLock(&device->lock, &device_irql);
    file = file_object->FsContext;
    if (device->state == WINUSB_DEVICE_STARTED && file &&
            file_is_linked(device, file, file_object))
    {
        KeAcquireSpinLock(&file->lock, &file_irql);
        if (file->state < WINUSB_FILE_RELEASING)
        {
            if (!file->outstanding++)
                KeClearEvent(&file->zero_outstanding);
            *ret_file = file;
            status = STATUS_SUCCESS;
        }
        KeReleaseSpinLock(&file->lock, file_irql);
    }
    KeReleaseSpinLock(&device->lock, device_irql);
    return status;
}

void winusb_release_file_from_io(struct winusb_file *file)
{
    KIRQL irql;

    KeAcquireSpinLock(&file->lock, &irql);
    if (file->outstanding && !--file->outstanding)
        KeSetEvent(&file->zero_outstanding, IO_NO_INCREMENT, FALSE);
    KeReleaseSpinLock(&file->lock, irql);
}

static void mark_files_removed(struct winusb_device *device)
{
    LIST_ENTRY *entry;

    for (entry = device->files.Flink; entry != &device->files; entry = entry->Flink)
    {
        struct winusb_file *file = CONTAINING_RECORD(entry,
                struct winusb_file, device_entry);
        KIRQL file_irql;

        KeAcquireSpinLock(&file->lock, &file_irql);
        file->state = WINUSB_FILE_REMOVED;
        if (!file->outstanding)
            KeSetEvent(&file->zero_outstanding, IO_NO_INCREMENT, FALSE);
        KeReleaseSpinLock(&file->lock, file_irql);
    }
}

static NTSTATUS WINAPI driver_create(DEVICE_OBJECT *device_obj, IRP *irp)
{
    IO_STACK_LOCATION *stack = IoGetCurrentIrpStackLocation(irp);
    struct winusb_device *device = device_obj->DeviceExtension;
    FILE_OBJECT *file_object = stack->FileObject;
    struct winusb_file *file;
    KIRQL irql;

    KeAcquireSpinLock(&device->lock, &irql);
    if (device->state != WINUSB_DEVICE_STARTED)
    {
        KeReleaseSpinLock(&device->lock, irql);
        return complete_irp(irp, STATUS_NOT_SUPPORTED);
    }
    if (!file_object)
    {
        KeReleaseSpinLock(&device->lock, irql);
        return complete_irp(irp, STATUS_INVALID_PARAMETER);
    }
    if (file_object->FsContext)
    {
        KeReleaseSpinLock(&device->lock, irql);
        return complete_irp(irp, STATUS_INVALID_DEVICE_STATE);
    }
    KeReleaseSpinLock(&device->lock, irql);

    if (!(file = ExAllocatePool(NonPagedPool, sizeof(*file))))
        return complete_irp(irp, STATUS_NO_MEMORY);
    memset(file, 0, sizeof(*file));
    file->file_object = file_object;
    KeInitializeSpinLock(&file->lock);
    ExInitializeFastMutex(&file->session_mutex);
    file->state = WINUSB_FILE_UNINITIALIZED;
    file->references = 1;
    KeInitializeEvent(&file->zero_outstanding, NotificationEvent, TRUE);
    InitializeListHead(&file->transfers);

    KeAcquireSpinLock(&device->lock, &irql);
    if (device->state != WINUSB_DEVICE_STARTED)
    {
        KeReleaseSpinLock(&device->lock, irql);
        ExFreePool(file);
        return complete_irp(irp, STATUS_NOT_SUPPORTED);
    }
    if (file_object->FsContext)
    {
        KeReleaseSpinLock(&device->lock, irql);
        ExFreePool(file);
        return complete_irp(irp, STATUS_INVALID_DEVICE_STATE);
    }
    InsertTailList(&device->files, &file->device_entry);
    ++device->file_count;
    KeClearEvent(&device->removal_event);
    file_object->FsContext = file;
    KeReleaseSpinLock(&device->lock, irql);

    return complete_irp(irp, STATUS_SUCCESS);
}

static NTSTATUS WINAPI driver_cleanup(DEVICE_OBJECT *device_obj, IRP *irp)
{
    IO_STACK_LOCATION *stack = IoGetCurrentIrpStackLocation(irp);
    struct winusb_device *device = device_obj->DeviceExtension;
    FILE_OBJECT *file_object = stack->FileObject;
    struct winusb_file *file;
    KIRQL device_irql, file_irql;

    if (!file_object) return complete_irp(irp, STATUS_INVALID_PARAMETER);

    KeAcquireSpinLock(&device->lock, &device_irql);
    file = file_object->FsContext;
    if (!file)
    {
        KeReleaseSpinLock(&device->lock, device_irql);
        return complete_irp(irp, STATUS_SUCCESS);
    }
    if (!file_is_linked(device, file, file_object))
    {
        KeReleaseSpinLock(&device->lock, device_irql);
        return complete_irp(irp, STATUS_INVALID_DEVICE_STATE);
    }
    KeReleaseSpinLock(&device->lock, device_irql);

    ExAcquireFastMutex(&file->session_mutex);
    KeAcquireSpinLock(&device->lock, &device_irql);
    if (file_object->FsContext != file ||
            !file_is_linked(device, file, file_object))
    {
        KeReleaseSpinLock(&device->lock, device_irql);
        ExReleaseFastMutex(&file->session_mutex);
        return complete_irp(irp, STATUS_INVALID_DEVICE_STATE);
    }

    KeAcquireSpinLock(&file->lock, &file_irql);
    if (file->state != WINUSB_FILE_REMOVED && file->state < WINUSB_FILE_RELEASING)
        file->state = WINUSB_FILE_RELEASING;
    if (!file->outstanding)
        KeSetEvent(&file->zero_outstanding, IO_NO_INCREMENT, FALSE);
    if (file->state != WINUSB_FILE_REMOVED)
        file->state = WINUSB_FILE_CLOSING;
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
    ExReleaseFastMutex(&file->session_mutex);

    return complete_irp(irp, STATUS_SUCCESS);
}

static NTSTATUS WINAPI driver_close(DEVICE_OBJECT *device_obj, IRP *irp)
{
    IO_STACK_LOCATION *stack = IoGetCurrentIrpStackLocation(irp);
    struct winusb_device *device = device_obj->DeviceExtension;
    FILE_OBJECT *file_object = stack->FileObject;
    struct winusb_file *file;
    KIRQL device_irql, file_irql;
    LONG outstanding;
    BOOL signal_after_unlock = FALSE;

    if (!file_object) return complete_irp(irp, STATUS_SUCCESS);

    KeAcquireSpinLock(&device->lock, &device_irql);
    file = file_object->FsContext;
    if (!file)
    {
        KeReleaseSpinLock(&device->lock, device_irql);
        return complete_irp(irp, STATUS_SUCCESS);
    }
    if (!file_is_linked(device, file, file_object))
    {
        KeReleaseSpinLock(&device->lock, device_irql);
        return complete_irp(irp, STATUS_INVALID_DEVICE_STATE);
    }
    KeReleaseSpinLock(&device->lock, device_irql);

    ExAcquireFastMutex(&file->session_mutex);
    KeAcquireSpinLock(&device->lock, &device_irql);
    if (file_object->FsContext != file ||
            !file_is_linked(device, file, file_object))
    {
        KeReleaseSpinLock(&device->lock, device_irql);
        ExReleaseFastMutex(&file->session_mutex);
        return complete_irp(irp, STATUS_INVALID_DEVICE_STATE);
    }

    KeAcquireSpinLock(&file->lock, &file_irql);
    if (file->state != WINUSB_FILE_REMOVED)
        file->state = WINUSB_FILE_CLOSING;
    outstanding = file->outstanding;
    file_object->FsContext = NULL;
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
    ExReleaseFastMutex(&file->session_mutex);

    if (outstanding)
        KeWaitForSingleObject(&file->zero_outstanding, Executive,
                KernelMode, FALSE, NULL);

    KeAcquireSpinLock(&device->lock, &device_irql);
    RemoveEntryList(&file->device_entry);
    InitializeListHead(&file->device_entry);
    KeReleaseSpinLock(&device->lock, device_irql);

    if (file->snapshot) ExFreePool(file->snapshot);
    if (file->interfaces) winusb_session_free_interfaces(file->interfaces,
            file->interface_count);
    ExFreePool(file);

    KeAcquireSpinLock(&device->lock, &device_irql);
    --device->file_count;
    if (!device->file_count)
    {
        if (device->state == WINUSB_DEVICE_SURPRISE_REMOVED ||
                device->state == WINUSB_DEVICE_REMOVED)
            signal_after_unlock = TRUE;
        else
            KeSetEvent(&device->removal_event, IO_NO_INCREMENT, FALSE);
    }
    KeReleaseSpinLock(&device->lock, device_irql);
    if (signal_after_unlock)
        KeSetEvent(&device->removal_event, IO_NO_INCREMENT, FALSE);
    return complete_irp(irp, STATUS_SUCCESS);
}

static NTSTATUS WINAPI driver_device_control(DEVICE_OBJECT *device_obj, IRP *irp)
{
    IO_STACK_LOCATION *stack = IoGetCurrentIrpStackLocation(irp);
    struct winusb_device *device = device_obj->DeviceExtension;
    FILE_OBJECT *file_object = stack->FileObject;
    const struct wine_winusb_request *request = irp->AssociatedIrp.SystemBuffer;
    struct winusb_file *file;
    ULONG code = stack->Parameters.DeviceIoControl.IoControlCode;
    ULONG input_length = stack->Parameters.DeviceIoControl.InputBufferLength;
    ULONG output_length = stack->Parameters.DeviceIoControl.OutputBufferLength;
    ULONG_PTR information = 0;
    NTSTATUS status;
    BOOL irp_consumed = FALSE;

    if (code != IOCTL_WINE_WINUSB_INITIALIZE && code != IOCTL_WINE_WINUSB_RELEASE &&
            code != IOCTL_WINE_WINUSB_SET_ALTERNATE &&
            code != IOCTL_WINE_WINUSB_GET_PIPE_POLICY &&
            code != IOCTL_WINE_WINUSB_SET_PIPE_POLICY &&
            code != IOCTL_WINE_WINUSB_GET_DESCRIPTOR &&
            code != IOCTL_WINE_WINUSB_CONTROL_IN &&
            code != IOCTL_WINE_WINUSB_CONTROL_OUT)
        return complete_irp(irp, STATUS_NOT_SUPPORTED);
    if (!file_object || !request)
        return complete_irp(irp, STATUS_INVALID_PARAMETER);

    if (!NT_SUCCESS(status = acquire_file_for_io(device, file_object, &file)))
        return complete_irp(irp, status);

    if (code == IOCTL_WINE_WINUSB_GET_DESCRIPTOR ||
            code == IOCTL_WINE_WINUSB_CONTROL_IN ||
            code == IOCTL_WINE_WINUSB_CONTROL_OUT)
    {
        /* A transfer can complete inline in the lower driver.  In either
         * schedule do not retain the per-file session mutex across dispatch. */
        status = winusb_dispatch_control_or_descriptor(device, file, irp, code,
                request, input_length, output_length, &irp_consumed);
        if (irp_consumed) return status;
        winusb_release_file_from_io(file);
        return complete_irp(irp, status);
    }

    ExAcquireFastMutex(&file->session_mutex);
    if (code == IOCTL_WINE_WINUSB_INITIALIZE)
        status = winusb_session_initialize(device, file, request, input_length,
                irp->MdlAddress, output_length, &information);
    else if (code == IOCTL_WINE_WINUSB_GET_PIPE_POLICY)
    {
        if (irp->MdlAddress)
            status = STATUS_INVALID_PARAMETER;
        else
            status = winusb_session_get_pipe_policy(device, file,
                    (struct wine_winusb_policy_request *)request,
                    input_length, output_length, &information);
    }
    else if (code == IOCTL_WINE_WINUSB_SET_PIPE_POLICY)
    {
        if (irp->MdlAddress)
            status = STATUS_INVALID_PARAMETER;
        else
            status = winusb_session_set_pipe_policy(device, file,
                    (const struct wine_winusb_policy_request *)request,
                    input_length, output_length, &information);
    }
    else if (code == IOCTL_WINE_WINUSB_SET_ALTERNATE)
    {
        if (output_length || irp->MdlAddress)
            status = STATUS_INVALID_PARAMETER;
        else
            status = winusb_session_set_alternate(device, file,
                    (const struct wine_winusb_alternate_request *)request,
                    input_length, &information);
    }
    else if (output_length || irp->MdlAddress)
        status = STATUS_INVALID_PARAMETER;
    else
        status = winusb_session_release(device, file, request, input_length,
                &information);
    ExReleaseFastMutex(&file->session_mutex);
    winusb_release_file_from_io(file);
    return complete_irp_with_information(irp, status, information);
}

static NTSTATUS WINAPI driver_pnp(DEVICE_OBJECT *device_obj, IRP *irp)
{
    IO_STACK_LOCATION *stack = IoGetCurrentIrpStackLocation(irp);
    struct winusb_device *device = device_obj->DeviceExtension;
    NTSTATUS status;

    TRACE("device %p, irp %p, minor function %#x.\n",
            device_obj, irp, stack->MinorFunction);

    switch (stack->MinorFunction)
    {
        case IRP_MN_START_DEVICE:
        {
            BOOL restarting;
            KIRQL irql;

            KeAcquireSpinLock(&device->lock, &irql);
            restarting = device->state == WINUSB_DEVICE_STOPPED;
            KeReleaseSpinLock(&device->lock, irql);

            status = forward_irp_synchronously(device, irp);
            if (!NT_SUCCESS(status))
            {
                if (restarting) disable_interface(device, "failed restart");
                return complete_irp(irp, status);
            }

            if (!device->enabled)
            {
                status = IoSetDeviceInterfaceState(&device->symbolic_link, TRUE);
                if (!NT_SUCCESS(status)) return complete_irp(irp, status);
                device->enabled = TRUE;
            }
            ExAcquireFastMutex(&device->finalization_mutex);
            KeAcquireSpinLock(&device->lock, &irql);
            device->state = WINUSB_DEVICE_STARTED;
            KeReleaseSpinLock(&device->lock, irql);
            ExReleaseFastMutex(&device->finalization_mutex);
            return complete_irp(irp, STATUS_SUCCESS);
        }

        case IRP_MN_STOP_DEVICE:
        {
            KIRQL irql;

            /* Keep lower STOP and the visible state transition indivisible
             * from a session's SELECT/COMMIT/publication sequence. */
            ExAcquireFastMutex(&device->finalization_mutex);
            status = forward_irp_synchronously(device, irp);
            if (NT_SUCCESS(status))
            {
                KeAcquireSpinLock(&device->lock, &irql);
                device->state = WINUSB_DEVICE_STOPPED;
                KeReleaseSpinLock(&device->lock, irql);
            }
            ExReleaseFastMutex(&device->finalization_mutex);
            return complete_irp(irp, status);
        }

        case IRP_MN_SURPRISE_REMOVAL:
        {
            KIRQL irql;

            ExAcquireFastMutex(&device->finalization_mutex);
            KeAcquireSpinLock(&device->lock, &irql);
            device->state = WINUSB_DEVICE_SURPRISE_REMOVED;
            mark_files_removed(device);
            KeReleaseSpinLock(&device->lock, irql);
            ExReleaseFastMutex(&device->finalization_mutex);
            disable_interface(device, "surprise removal");
            status = forward_irp_synchronously(device, irp);
            return complete_irp(irp, status);
        }

        case IRP_MN_REMOVE_DEVICE:
        {
            KIRQL irql;

            ExAcquireFastMutex(&device->finalization_mutex);
            KeAcquireSpinLock(&device->lock, &irql);
            device->state = WINUSB_DEVICE_REMOVED;
            mark_files_removed(device);
            if (!device->file_count)
                KeSetEvent(&device->removal_event, IO_NO_INCREMENT, FALSE);
            KeReleaseSpinLock(&device->lock, irql);
            /* CLOSE may wait for an in-flight per-file session operation.
             * Do not hold the device finalization mutex across that drain. */
            ExReleaseFastMutex(&device->finalization_mutex);
            KeWaitForSingleObject(&device->removal_event, Executive,
                    KernelMode, FALSE, NULL);

            ExAcquireFastMutex(&device->finalization_mutex);
            winusb_session_recover_claim_transaction(device);
            disable_interface(device, "removal");
            device->enabled = FALSE;
            status = forward_irp_synchronously(device, irp);
            winusb_session_claim_child_removed(device);
            ExReleaseFastMutex(&device->finalization_mutex);
            IoDetachDevice(device->lower_device);
            if (device->symbolic_link.Buffer)
                RtlFreeUnicodeString(&device->symbolic_link);
            IoDeleteDevice(device_obj);
            return complete_irp(irp, status);
        }

        default:
            IoSkipCurrentIrpStackLocation(irp);
            return IoCallDriver(device->lower_device, irp);
    }
}

static NTSTATUS WINAPI driver_unsupported(DEVICE_OBJECT *device, IRP *irp)
{
    TRACE("device %p, irp %p.\n", device, irp);
    return complete_irp(irp, STATUS_NOT_SUPPORTED);
}

static NTSTATUS WINAPI driver_add_device(DRIVER_OBJECT *driver, DEVICE_OBJECT *pdo)
{
    struct winusb_device *device;
    DEVICE_OBJECT *device_obj;
    GUID interface_guid;
    USHORT metadata_version;
    UCHAR speed;
    NTSTATUS status;

    TRACE("driver %p, pdo %p.\n", driver, pdo);

    if ((status = query_metadata_interface(pdo, &interface_guid,
            &metadata_version, &speed)))
        return status;

    if ((status = IoCreateDevice(driver, sizeof(*device), NULL,
            FILE_DEVICE_UNKNOWN, 0, FALSE, &device_obj)))
        return status;

    device = device_obj->DeviceExtension;
    memset(device, 0, sizeof(*device));
    device->pdo = pdo;
    device->interface_guid = interface_guid;
    device->state = WINUSB_DEVICE_ADDED;
    KeInitializeSpinLock(&device->lock);
    ExInitializeFastMutex(&device->finalization_mutex);
    InitializeListHead(&device->files);
    KeInitializeEvent(&device->removal_event, NotificationEvent, TRUE);
    device->metadata_interface_version = metadata_version;
    device->speed = speed;

    if (!(device->lower_device = IoAttachDeviceToDeviceStack(device_obj, pdo)))
    {
        IoDeleteDevice(device_obj);
        return STATUS_NO_SUCH_DEVICE;
    }

    status = IoRegisterDeviceInterface(pdo, &device->interface_guid, NULL,
            &device->symbolic_link);
    if (!NT_SUCCESS(status))
    {
        IoDetachDevice(device->lower_device);
        if (device->symbolic_link.Buffer)
            RtlFreeUnicodeString(&device->symbolic_link);
        IoDeleteDevice(device_obj);
        return status;
    }

    device->registered = TRUE;
    device_obj->Flags &= ~DO_DEVICE_INITIALIZING;
    return STATUS_SUCCESS;
}

static void WINAPI driver_unload(DRIVER_OBJECT *driver)
{
    TRACE("driver %p.\n", driver);
}

NTSTATUS WINAPI DriverEntry(DRIVER_OBJECT *driver, UNICODE_STRING *path)
{
    TRACE("driver %p, path %s.\n", driver,
            path ? debugstr_w(path->Buffer) : "(null)");

    winusb_session_driver_init();
    driver->DriverExtension->AddDevice = driver_add_device;
    driver->DriverUnload = driver_unload;
    driver->MajorFunction[IRP_MJ_CREATE] = driver_create;
    driver->MajorFunction[IRP_MJ_CLOSE] = driver_close;
    driver->MajorFunction[IRP_MJ_CLEANUP] = driver_cleanup;
    driver->MajorFunction[IRP_MJ_READ] = driver_unsupported;
    driver->MajorFunction[IRP_MJ_WRITE] = driver_unsupported;
    driver->MajorFunction[IRP_MJ_DEVICE_CONTROL] = driver_device_control;
    driver->MajorFunction[IRP_MJ_INTERNAL_DEVICE_CONTROL] = driver_unsupported;
    driver->MajorFunction[IRP_MJ_PNP] = driver_pnp;
    return STATUS_SUCCESS;
}
