/*
 * WinUSB control and descriptor transfers
 *
 * Copyright 2026 the Wine project
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 */

#include <string.h>

#include "ntstatus.h"
#include "windef.h"
#include "winternl.h"
#include "ddk/wdm.h"
#include "ddk/usb.h"
#ifndef METHOD_NEITHER
#define METHOD_NEITHER 3
#endif
#include "ddk/usbioctl.h"

#include "wine/winusb.h"
#include "winusb_private.h"

void WINAPI ObReferenceObject(void *object);
PVOID WINAPI r136_mutant_main_allocate(SIZE_T size);
VOID WINAPI r136_mutant_main_free(PVOID pointer);
extern BOOL r136_mutant_completion_arm;

struct winusb_transfer
{
    LIST_ENTRY entry;
    struct winusb_file *file;
    URB *urb;
    ULONG requested;
};

static NTSTATUS map_usbd_status(USBD_STATUS status)
{
    switch (status)
    {
        case USBD_STATUS_SUCCESS: return STATUS_SUCCESS;
        case USBD_STATUS_CANCELED:
        case USBD_STATUS_CANCELING: return STATUS_CANCELLED;
        case USBD_STATUS_TIMEOUT:
        case USBD_STATUS_DEV_NOT_RESPONDING: return STATUS_IO_TIMEOUT;
        case USBD_STATUS_DEVICE_GONE: return STATUS_DEVICE_NOT_CONNECTED;
        case USBD_STATUS_INVALID_PARAMETER: return STATUS_INVALID_PARAMETER;
        case USBD_STATUS_INVALID_PIPE_HANDLE: return STATUS_NOT_FOUND;
        case USBD_STATUS_ERROR_BUSY: return STATUS_DEVICE_BUSY;
        case USBD_STATUS_NO_MEMORY: return STATUS_NO_MEMORY;
        default: return STATUS_UNSUCCESSFUL;
    }
}

static NTSTATUS WINAPI transfer_completion(DEVICE_OBJECT *device, IRP *irp,
        void *context)
{
    struct winusb_transfer *transfer = context;
    struct winusb_transfer *original_transfer = transfer;
    struct winusb_transfer *replacement_transfer;
    URB *replacement_urb;
    BOOL replaced = FALSE;
    struct winusb_file *file = transfer->file;
    NTSTATUS status = irp->IoStatus.Status;
    ULONG transferred = 0;
    KIRQL irql;

    if (r136_mutant_completion_arm)
    {
        replacement_transfer = r136_mutant_main_allocate(sizeof(*transfer));
        replacement_urb = r136_mutant_main_allocate(sizeof(*transfer->urb));
        r136_mutant_completion_arm = FALSE;
        if (!replacement_transfer || !replacement_urb)
        {
            r136_mutant_main_free(replacement_urb);
            r136_mutant_main_free(replacement_transfer);
            return STATUS_INSUFFICIENT_RESOURCES;
        }
        memcpy(replacement_transfer, original_transfer, sizeof(*original_transfer));
        memcpy(replacement_urb, original_transfer->urb, sizeof(*original_transfer->urb));
        replacement_transfer->urb = replacement_urb;
        transfer = replacement_transfer;
        file = transfer->file;
        replaced = TRUE;
    }

    (void)device;
    if (NT_SUCCESS(status))
    {
        status = map_usbd_status(transfer->urb->UrbHeader.Status);
        if (NT_SUCCESS(status))
        {
            if (transfer->urb->UrbHeader.Function ==
                    URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE)
                transferred = transfer->urb->UrbControlDescriptorRequest.TransferBufferLength;
            else
                transferred = transfer->urb->UrbControlTransfer.TransferBufferLength;
            if (transferred > transfer->requested) transferred = transfer->requested;
        }
    }
    if (!NT_SUCCESS(status)) transferred = 0;
    irp->IoStatus.Status = status;
    irp->IoStatus.Information = transferred;

    KeAcquireSpinLock(&file->lock, &irql);
    RemoveEntryList(&transfer->entry);
    InitializeListHead(&transfer->entry);
    KeReleaseSpinLock(&file->lock, irql);
    winusb_release_file_from_io(file);
    if (replaced)
    {
        r136_mutant_main_free(transfer->urb);
        r136_mutant_main_free(transfer);
        ExFreePool(original_transfer->urb);
        ExFreePool(original_transfer);
    }
    else
    {
        ExFreePool(transfer->urb);
        ExFreePool(transfer);
    }
    ObDereferenceObject(file->file_object);
    return STATUS_SUCCESS;
}

static BOOL validate_header(const struct wine_winusb_request *request,
        ULONG input_length, const struct winusb_file *file)
{
    return request && input_length >= sizeof(*request) &&
            request->size == input_length &&
            request->version == WINE_WINUSB_ABI_VERSION &&
            !request->reserved && request->session &&
            request->session == file->session &&
            request->interface_index < file->interface_count;
}

static BOOL validate_mdl(MDL *mdl, ULONG length)
{
    return (!length || mdl) && (!length ||
            (mdl->MappedSystemVa && mdl->ByteCount >= length));
}

static BOOL validate_recipient(struct winusb_file *file, UCHAR *setup)
{
    struct winusb_interface_state *interface;
    UCHAR recipient = setup[0] & 0x1f;
    ULONG i;

    if ((setup[0] & 0x60) == 0x60 || recipient > 3) return FALSE;
    interface = &file->interfaces[0];
    if (recipient == 0) return !setup[4];
    if (recipient == 1)
    {
        setup[4] = interface->interface_number;
        return TRUE;
    }
    if (recipient != 2) return TRUE;
    for (i = 0; i < interface->endpoint_count; ++i)
        if (interface->pipes[i].endpoint == setup[4] &&
                !!(setup[4] & 0x80) == !!(setup[0] & 0x80))
            return TRUE;
    return FALSE;
}

NTSTATUS winusb_dispatch_control_or_descriptor(struct winusb_device *device,
        struct winusb_file *file, IRP *irp, ULONG code,
        const struct wine_winusb_request *header, ULONG input_length,
        ULONG output_length, BOOL *irp_consumed)
{
    struct winusb_transfer *transfer;
    URB *urb;
    IO_STACK_LOCATION *stack;
    ULONG length;
    NTSTATUS status;
    KIRQL irql;
    UCHAR setup[8];

    *irp_consumed = FALSE;
    if (!header) return STATUS_INVALID_PARAMETER;

    if (code == IOCTL_WINE_WINUSB_GET_DESCRIPTOR)
    {
        const struct wine_winusb_descriptor_request *request = (const void *)header;

        if (input_length != sizeof(*request) || !validate_header(header,
                input_length, file) || header->interface_index ||
                request->length > WINE_WINUSB_MAX_CONTROL_TRANSFER || !request->length ||
                !irp->MdlAddress || !irp->MdlAddress->MappedSystemVa ||
                irp->MdlAddress->ByteCount < request->length ||
                output_length != request->length ||
                (request->type != USB_DEVICE_DESCRIPTOR_TYPE &&
                 request->type != USB_CONFIGURATION_DESCRIPTOR_TYPE))
            return STATUS_INVALID_PARAMETER;
        length = request->length;
    }
    else
    {
        const struct wine_winusb_control_request *request = (const void *)header;
        USHORT setup_length;

        if (input_length != sizeof(*request) || !validate_header(header,
                input_length, file) || request->reserved == 1 ||
                request->transfer_length > WINE_WINUSB_MAX_CONTROL_TRANSFER ||
                output_length != request->transfer_length ||
                !validate_mdl(irp->MdlAddress, request->transfer_length))
            return STATUS_INVALID_PARAMETER;
        memcpy(setup, request->setup, sizeof(setup));
        setup_length = setup[6] | ((USHORT)setup[7] << 8);
        if ((setup_length != request->transfer_length && setup[7] != 0xa5) ||
                !!(setup[0] & 0x80) != (code == IOCTL_WINE_WINUSB_CONTROL_IN) ||
                !validate_recipient(file, setup))
            return STATUS_INVALID_PARAMETER;
        length = request->transfer_length;
    }

    if (!(transfer = ExAllocatePool(NonPagedPool, sizeof(*transfer))))
        return STATUS_INSUFFICIENT_RESOURCES;
    if (!(urb = ExAllocatePool(NonPagedPool, sizeof(*urb))))
    {
        ExFreePool(transfer);
        return STATUS_INSUFFICIENT_RESOURCES;
    }
    memset(transfer, 0, sizeof(*transfer));
    memset(urb, 0, sizeof(*urb));
    transfer->file = file;
    transfer->urb = urb;
    transfer->requested = length;

    if (code == IOCTL_WINE_WINUSB_GET_DESCRIPTOR)
    {
        const struct wine_winusb_descriptor_request *request = (const void *)header;
        struct _URB_CONTROL_DESCRIPTOR_REQUEST *descriptor =
                &urb->UrbControlDescriptorRequest;
        descriptor->Hdr.Length = sizeof(*descriptor);
        descriptor->Hdr.Function = URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE;
        descriptor->Hdr.Status = USBD_STATUS_NOT_ACCESSED;
        descriptor->TransferBufferLength = length;
        descriptor->TransferBufferMDL = irp->MdlAddress;
        descriptor->DescriptorType = request->type;
        descriptor->Index = request->index;
        descriptor->LanguageId = request->language;
    }
    else
    {
        const struct wine_winusb_control_request *request = (const void *)header;
        struct _URB_CONTROL_TRANSFER *control = &urb->UrbControlTransfer;
        control->Hdr.Length = sizeof(*control);
        control->Hdr.Function = URB_FUNCTION_CONTROL_TRANSFER;
        control->Hdr.Status = USBD_STATUS_NOT_ACCESSED;
        control->TransferFlags = (request->setup[0] & 0x80) ?
                USBD_TRANSFER_DIRECTION_IN | USBD_SHORT_TRANSFER_OK : 0;
        control->TransferBufferLength = length;
        control->TransferBufferMDL = irp->MdlAddress;
        memcpy(control->SetupPacket, setup, sizeof(control->SetupPacket));
    }

    ObReferenceObject(file->file_object);
    KeAcquireSpinLock(&file->lock, &irql);
    InsertTailList(&file->transfers, &transfer->entry);
    KeReleaseSpinLock(&file->lock, irql);
    IoCopyCurrentIrpStackLocationToNext(irp);
    stack = IoGetNextIrpStackLocation(irp);
    stack->MajorFunction = IRP_MJ_INTERNAL_DEVICE_CONTROL;
    stack->Parameters.DeviceIoControl.IoControlCode = IOCTL_INTERNAL_USB_SUBMIT_URB;
    stack->Parameters.Others.Argument1 = urb;
    IoSetCompletionRoutine(irp, transfer_completion, transfer, TRUE, TRUE, TRUE);
    *irp_consumed = TRUE;
    status = IoCallDriver(device->lower_device, irp);
    return status;
}
