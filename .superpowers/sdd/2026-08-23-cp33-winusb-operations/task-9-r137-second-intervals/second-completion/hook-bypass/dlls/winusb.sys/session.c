/*
 * WinUSB function-driver session support
 *
 * Copyright 2026 the Wine project
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 */

#include <stdarg.h>
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

#include "winusbio.h"
#include "winusb_private.h"
#include "winusb_busif.h"

struct parsed_configuration
{
    SIZE_T interface_count;
    SIZE_T alternate_count;
    SIZE_T endpoint_count;
    SIZE_T total_size;
    SIZE_T device_offset;
    SIZE_T configuration_offset;
    SIZE_T interfaces_offset;
    SIZE_T alternates_offset;
    SIZE_T endpoints_offset;
};

static KSPIN_LOCK session_lock;
static UINT64 session_counter;

static BOOL add_size(SIZE_T left, SIZE_T right, SIZE_T *result)
{
    if (right > ~(SIZE_T)0 - left) return FALSE;
    *result = left + right;
    return TRUE;
}

static BOOL multiply_size(SIZE_T left, SIZE_T right, SIZE_T *result)
{
    if (left && right > ~(SIZE_T)0 / left) return FALSE;
    *result = left * right;
    return TRUE;
}

static BOOL descriptor_next(const UCHAR *buffer, SIZE_T length, SIZE_T offset,
        SIZE_T *next)
{
    SIZE_T header_end;
    UCHAR descriptor_length;

    if (!add_size(offset, 2, &header_end) || header_end > length) return FALSE;
    descriptor_length = buffer[offset];
    if (descriptor_length < 2) return FALSE;
    if (!add_size(offset, descriptor_length, next) || *next > length) return FALSE;
    return TRUE;
}

static NTSTATUS submit_urb(struct winusb_device *device, URB *urb)
{
    IO_STATUS_BLOCK io_status = {{STATUS_UNSUCCESSFUL}, 0};
    IO_STACK_LOCATION *stack;
    KEVENT event;
    NTSTATUS status;
    IRP *irp;

    KeInitializeEvent(&event, NotificationEvent, FALSE);
    urb->UrbHeader.Status = USBD_STATUS_NOT_ACCESSED;
    if (!(irp = IoBuildDeviceIoControlRequest(IOCTL_INTERNAL_USB_SUBMIT_URB,
            device->lower_device, urb, urb->UrbHeader.Length, NULL, 0, TRUE,
            &event, &io_status)))
        return STATUS_NO_MEMORY;
    stack = IoGetNextIrpStackLocation(irp);
    stack->Parameters.Others.Argument1 = urb;
    status = IoCallDriver(device->lower_device, irp);
    if (status == STATUS_PENDING)
    {
        status = KeWaitForSingleObject(&event, Executive, KernelMode,
                FALSE, NULL);
        if (!NT_SUCCESS(status)) return status;
    }
    status = io_status.Status;
    if (!NT_SUCCESS(status)) return status;
    if (urb->UrbHeader.Status != USBD_STATUS_SUCCESS)
        return STATUS_UNSUCCESSFUL;
    return STATUS_SUCCESS;
}

static NTSTATUS finalize_claim_transaction(struct winusb_device *device,
        USBD_CONFIGURATION_HANDLE transaction, ULONG operation)
{
    struct wineusb_claim_transaction_request request;

    memset(&request, 0, sizeof(request));
    request.Hdr.Length = sizeof(request);
    request.Hdr.Function = WINEUSB_URB_FUNCTION_CLAIM_TRANSACTION;
    request.Transaction = transaction;
    request.Operation = operation;
    return submit_urb(device, (URB *)&request);
}

static NTSTATUS read_descriptor(struct winusb_device *device, UCHAR type,
        void *buffer, ULONG requested, ULONG *returned)
{
    URB urb;
    NTSTATUS status;

    memset(&urb, 0, sizeof(urb));
    urb.UrbControlDescriptorRequest.Hdr.Length =
            sizeof(urb.UrbControlDescriptorRequest);
    urb.UrbControlDescriptorRequest.Hdr.Function =
            URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE;
    urb.UrbControlDescriptorRequest.TransferBufferLength = requested;
    urb.UrbControlDescriptorRequest.TransferBuffer = buffer;
    urb.UrbControlDescriptorRequest.DescriptorType = type;
    if (!NT_SUCCESS(status = submit_urb(device, &urb))) return status;
    *returned = urb.UrbControlDescriptorRequest.TransferBufferLength;
    return STATUS_SUCCESS;
}

static BOOL prior_interface(const UCHAR *configuration, SIZE_T current,
        UCHAR number, UCHAR alternate, BOOL *same_interface)
{
    SIZE_T offset = 0, next;

    *same_interface = FALSE;
    while (offset < current)
    {
        if (!descriptor_next(configuration, current, offset, &next)) return TRUE;
        if (configuration[offset + 1] == USB_INTERFACE_DESCRIPTOR_TYPE &&
                configuration[offset] >= sizeof(USB_INTERFACE_DESCRIPTOR))
        {
            const USB_INTERFACE_DESCRIPTOR *interface =
                    (const void *)(configuration + offset);
            if (interface->bInterfaceNumber == number)
            {
                *same_interface = TRUE;
                if (interface->bAlternateSetting == alternate) return TRUE;
            }
        }
        offset = next;
    }
    return FALSE;
}

static BOOL interface_has_default(const UCHAR *configuration, SIZE_T length,
        UCHAR number)
{
    SIZE_T offset = 0, next;

    while (offset < length)
    {
        if (!descriptor_next(configuration, length, offset, &next)) return FALSE;
        if (configuration[offset + 1] == USB_INTERFACE_DESCRIPTOR_TYPE &&
                configuration[offset] >= sizeof(USB_INTERFACE_DESCRIPTOR))
        {
            const USB_INTERFACE_DESCRIPTOR *interface =
                    (const void *)(configuration + offset);
            if (interface->bInterfaceNumber == number &&
                    !interface->bAlternateSetting)
                return TRUE;
        }
        offset = next;
    }
    return FALSE;
}

static BOOL validate_default_alternates(const UCHAR *configuration,
        SIZE_T length)
{
    SIZE_T offset = 0, next;

    while (offset < length)
    {
        if (!descriptor_next(configuration, length, offset, &next)) return FALSE;
        if (configuration[offset + 1] == USB_INTERFACE_DESCRIPTOR_TYPE &&
                configuration[offset] >= sizeof(USB_INTERFACE_DESCRIPTOR))
        {
            const USB_INTERFACE_DESCRIPTOR *interface =
                    (const void *)(configuration + offset);
            BOOL same_interface;

            prior_interface(configuration, offset, interface->bInterfaceNumber,
                    0xff, &same_interface);
            if (!same_interface && !interface_has_default(configuration, length,
                    interface->bInterfaceNumber))
                return FALSE;
        }
        offset = next;
    }
    return TRUE;
}

static BOOL calculate_snapshot_layout(struct parsed_configuration *parsed,
        SIZE_T configuration_length)
{
    SIZE_T bytes, offset = sizeof(struct wine_winusb_snapshot);

    parsed->device_offset = offset;
    if (!add_size(offset, sizeof(USB_DEVICE_DESCRIPTOR), &offset)) return FALSE;
    parsed->configuration_offset = offset;
    if (!add_size(offset, configuration_length, &offset)) return FALSE;
    parsed->interfaces_offset = offset;
    if (!multiply_size(parsed->interface_count,
            sizeof(struct wine_winusb_interface_snapshot), &bytes) ||
            !add_size(offset, bytes, &offset))
        return FALSE;
    parsed->alternates_offset = offset;
    if (!multiply_size(parsed->alternate_count,
            sizeof(struct wine_winusb_alternate_snapshot), &bytes) ||
            !add_size(offset, bytes, &offset))
        return FALSE;
    parsed->endpoints_offset = offset;
    if (!multiply_size(parsed->endpoint_count,
            sizeof(struct wine_winusb_endpoint_snapshot), &bytes) ||
            !add_size(offset, bytes, &offset))
        return FALSE;
    parsed->total_size = offset;
    return offset <= ~(ULONG)0;
}

static BOOL parse_configuration(const UCHAR *configuration, SIZE_T length,
        struct parsed_configuration *parsed)
{
    const USB_CONFIGURATION_DESCRIPTOR *header;
    SIZE_T offset = 0, next;
    ULONG expected_endpoints = 0, seen_endpoints = 0;
    BOOL have_interface = FALSE;
    UCHAR active_interface = 0;

    memset(parsed, 0, sizeof(*parsed));
    if (length < sizeof(*header)) return FALSE;
    header = (const void *)configuration;
    if (header->bLength != sizeof(*header) ||
            header->bDescriptorType != USB_CONFIGURATION_DESCRIPTOR_TYPE ||
            header->wTotalLength != length)
        return FALSE;

    while (offset < length)
    {
        UCHAR type;

        if (!descriptor_next(configuration, length, offset, &next)) return FALSE;
        type = configuration[offset + 1];
        if (offset && type == USB_INTERFACE_DESCRIPTOR_TYPE)
        {
            const USB_INTERFACE_DESCRIPTOR *interface;
            BOOL same_interface;

            if (have_interface && seen_endpoints != expected_endpoints) return FALSE;
            if (configuration[offset] < sizeof(*interface)) return FALSE;
            interface = (const void *)(configuration + offset);
            if (prior_interface(configuration, offset,
                    interface->bInterfaceNumber, interface->bAlternateSetting,
                    &same_interface))
                return FALSE;
            if (same_interface && active_interface != interface->bInterfaceNumber)
                return FALSE;
            if (!same_interface) parsed->interface_count++;
            parsed->alternate_count++;
            have_interface = TRUE;
            active_interface = interface->bInterfaceNumber;
            expected_endpoints = interface->bNumEndpoints;
            seen_endpoints = 0;
        }
        else if (offset && type == USB_ENDPOINT_DESCRIPTOR_TYPE)
        {
            if (!have_interface || configuration[offset] < sizeof(USB_ENDPOINT_DESCRIPTOR))
                return FALSE;
            seen_endpoints++;
            if (seen_endpoints > expected_endpoints) return FALSE;
            parsed->endpoint_count++;
        }
        offset = next;
    }
    if (have_interface && seen_endpoints != expected_endpoints) return FALSE;
    if (!parsed->interface_count ||
            header->bNumInterfaces != parsed->interface_count ||
            !validate_default_alternates(configuration, length))
        return FALSE;
    return calculate_snapshot_layout(parsed, length);
}

static BOOL snapshot_record_offset(SIZE_T total_size, SIZE_T base,
        SIZE_T index, SIZE_T record_size, SIZE_T *offset)
{
    SIZE_T index_offset, end;

    return multiply_size(index, record_size, &index_offset) &&
            add_size(base, index_offset, offset) &&
            add_size(*offset, record_size, &end) && end <= total_size;
}

static BOOL read_snapshot_record(const UCHAR *memory, SIZE_T total_size,
        SIZE_T base, SIZE_T index, SIZE_T record_size, void *record)
{
    SIZE_T offset;

    if (!snapshot_record_offset(total_size, base, index, record_size, &offset))
        return FALSE;
    memcpy(record, memory + offset, record_size);
    return TRUE;
}

static BOOL write_snapshot_record(UCHAR *memory, SIZE_T total_size,
        SIZE_T base, SIZE_T index, SIZE_T record_size, const void *record)
{
    SIZE_T offset;

    if (!snapshot_record_offset(total_size, base, index, record_size, &offset))
        return FALSE;
    memcpy(memory + offset, record, record_size);
    return TRUE;
}

static BOOL find_interface_record(const UCHAR *memory,
        const struct parsed_configuration *parsed, ULONG count, ULONG number,
        ULONG *index)
{
    ULONG i;

    for (i = 0; i < count; ++i)
    {
        struct wine_winusb_interface_snapshot record;

        if (!read_snapshot_record(memory, parsed->total_size,
                parsed->interfaces_offset, i, sizeof(record), &record))
            return FALSE;
        if (record.interface_number == number)
        {
            *index = i;
            return TRUE;
        }
    }
    *index = count;
    return TRUE;
}

static BOOL build_snapshot(void *memory, const USB_DEVICE_DESCRIPTOR *device,
        const UCHAR *configuration, const struct parsed_configuration *parsed,
        UCHAR speed)
{
    struct wine_winusb_snapshot *snapshot = memory;
    SIZE_T offset = 0, next;
    ULONG interface_count = 0, alternate_count = 0, endpoint_count = 0;
    ULONG current_alternate = 0;

    memset(memory, 0, parsed->total_size);
    snapshot->size = sizeof(*snapshot);
    snapshot->version = WINE_WINUSB_ABI_VERSION;
    snapshot->speed = speed;
    snapshot->total_size = parsed->total_size;
    snapshot->device_offset = parsed->device_offset;
    snapshot->device_length = sizeof(*device);
    snapshot->configuration_offset = parsed->configuration_offset;
    snapshot->configuration_length = ((const USB_CONFIGURATION_DESCRIPTOR *)configuration)->wTotalLength;
    snapshot->interfaces_offset = parsed->interfaces_offset;
    snapshot->interface_count = parsed->interface_count;
    snapshot->alternates_offset = parsed->alternates_offset;
    snapshot->alternate_count = parsed->alternate_count;
    snapshot->endpoints_offset = parsed->endpoints_offset;
    snapshot->endpoint_count = parsed->endpoint_count;
    memcpy((UCHAR *)memory + parsed->device_offset, device, sizeof(*device));
    memcpy((UCHAR *)memory + parsed->configuration_offset, configuration,
            snapshot->configuration_length);
    while (offset < snapshot->configuration_length)
    {
        UCHAR type;

        if (!descriptor_next(configuration, snapshot->configuration_length,
                offset, &next))
            return FALSE;
        type = configuration[offset + 1];
        if (offset && type == USB_INTERFACE_DESCRIPTOR_TYPE)
        {
            struct wine_winusb_interface_snapshot interface_record;
            struct wine_winusb_alternate_snapshot alternate_record = {0};
            const USB_INTERFACE_DESCRIPTOR *descriptor =
                    (const void *)(configuration + offset);
            ULONG index;

            if (!find_interface_record(memory, parsed, interface_count,
                    descriptor->bInterfaceNumber, &index))
                return FALSE;
            if (index == interface_count)
            {
                if (interface_count >= parsed->interface_count) return FALSE;
                memset(&interface_record, 0, sizeof(interface_record));
                interface_record.interface_number = descriptor->bInterfaceNumber;
                interface_record.first_alternate = alternate_count;
                interface_count++;
            }
            else if (!read_snapshot_record(memory, parsed->total_size,
                    parsed->interfaces_offset, index, sizeof(interface_record),
                    &interface_record))
                return FALSE;
            interface_record.alternate_count++;
            if (!write_snapshot_record(memory, parsed->total_size,
                    parsed->interfaces_offset, index, sizeof(interface_record),
                    &interface_record))
                return FALSE;
            if (alternate_count >= parsed->alternate_count) return FALSE;
            current_alternate = alternate_count++;
            alternate_record.interface_index = index;
            alternate_record.alternate_setting = descriptor->bAlternateSetting;
            alternate_record.first_endpoint = endpoint_count;
            alternate_record.endpoint_count = descriptor->bNumEndpoints;
            if (!write_snapshot_record(memory, parsed->total_size,
                    parsed->alternates_offset, current_alternate,
                    sizeof(alternate_record), &alternate_record))
                return FALSE;
        }
        else if (offset && type == USB_ENDPOINT_DESCRIPTOR_TYPE)
        {
            struct wine_winusb_endpoint_snapshot endpoint_record = {0};
            const USB_ENDPOINT_DESCRIPTOR *descriptor =
                    (const void *)(configuration + offset);

            if (endpoint_count >= parsed->endpoint_count) return FALSE;
            endpoint_record.alternate_index = current_alternate;
            endpoint_record.pipe_id = descriptor->bEndpointAddress;
            endpoint_record.pipe_type =
                    descriptor->bmAttributes & USB_ENDPOINT_TYPE_MASK;
            endpoint_record.maximum_packet_size =
                    descriptor->wMaxPacketSize;
            if (!write_snapshot_record(memory, parsed->total_size,
                    parsed->endpoints_offset, endpoint_count,
                    sizeof(endpoint_record), &endpoint_record))
                return FALSE;
            endpoint_count++;
        }
        offset = next;
    }
    return interface_count == parsed->interface_count &&
            alternate_count == parsed->alternate_count &&
            endpoint_count == parsed->endpoint_count;
}

static BOOL build_interface_state(const struct wine_winusb_snapshot *snapshot,
        struct winusb_interface_state *state)
{
    const UCHAR *memory = (const UCHAR *)snapshot;
    ULONG i, j;

    for (i = 0; i < snapshot->interface_count; ++i)
    {
        struct wine_winusb_interface_snapshot interface_record;
        SIZE_T alternate_end;
        BOOL found = FALSE;

        if (!read_snapshot_record(memory, snapshot->total_size,
                snapshot->interfaces_offset, i, sizeof(interface_record),
                &interface_record) ||
                !add_size(interface_record.first_alternate,
                interface_record.alternate_count, &alternate_end) ||
                alternate_end > snapshot->alternate_count)
            return FALSE;
        for (j = 0; j < interface_record.alternate_count; ++j)
        {
            struct wine_winusb_alternate_snapshot alternate_record;
            SIZE_T alternate_index;

            if (!add_size(interface_record.first_alternate, j,
                    &alternate_index) ||
                    !read_snapshot_record(memory, snapshot->total_size,
                    snapshot->alternates_offset,
                    alternate_index,
                    sizeof(alternate_record), &alternate_record))
                return FALSE;
            if (!alternate_record.alternate_setting)
            {
                state[i].interface_number = interface_record.interface_number;
                state[i].alternate_setting = 0;
                state[i].first_endpoint = alternate_record.first_endpoint;
                state[i].endpoint_count = alternate_record.endpoint_count;
                found = TRUE;
                break;
            }
        }
        if (!found) return FALSE;
    }
    return TRUE;
}

void winusb_session_free_interfaces(struct winusb_interface_state *state,
        ULONG count)
{
    ULONG i;

    if (!state) return;
    for (i = 0; i < count; ++i)
        if (state[i].pipes) ExFreePool(state[i].pipes);
    ExFreePool(state);
}

static BOOL allocate_pipe_maps(struct winusb_interface_state *state, ULONG count)
{
    ULONG i;

    for (i = 0; i < count; ++i)
    {
        SIZE_T size;

        if (!state[i].endpoint_count) continue;
        if (!multiply_size(state[i].endpoint_count, sizeof(*state[i].pipes), &size) ||
                !(state[i].pipes = ExAllocatePool(NonPagedPool, size)))
            return FALSE;
        state[i].generation = 1;
    }
    return TRUE;
}

static void initialize_pipe_policy(struct winusb_pipe_state *pipe)
{
    memset(&pipe->policy, 0, sizeof(pipe->policy));
    pipe->policy.maximum_transfer_size = WINE_WINUSB_MAXIMUM_TRANSFER_SIZE;
    if (pipe->endpoint & 0x80)
        pipe->policy.allow_partial_reads = TRUE;
}

static BOOL capture_select_pipe_handles(struct _URB_SELECT_CONFIGURATION *select,
        SIZE_T select_size, struct winusb_interface_state *state, ULONG count)
{
    SIZE_T cursor = offsetof(struct _URB_SELECT_CONFIGURATION, Interface);
    ULONG i, j;

    for (i = 0; i < count; ++i)
    {
        USBD_INTERFACE_INFORMATION *information;
        SIZE_T pipes_size, size;

        if (!multiply_size(state[i].endpoint_count, sizeof(USBD_PIPE_INFORMATION), &pipes_size) ||
                !add_size(offsetof(USBD_INTERFACE_INFORMATION, Pipes), pipes_size, &size) ||
                cursor > select_size || size > select_size - cursor)
            return FALSE;
        information = (void *)((UCHAR *)select + cursor);
        if (information->InterfaceNumber != state[i].interface_number ||
                information->AlternateSetting != state[i].alternate_setting ||
                information->NumberOfPipes != state[i].endpoint_count)
            return FALSE;
        for (j = 0; j < state[i].endpoint_count; ++j)
        {
            state[i].pipes[j].handle = information->Pipes[j].PipeHandle;
            state[i].pipes[j].endpoint = information->Pipes[j].EndpointAddress;
            state[i].pipes[j].type = information->Pipes[j].PipeType;
            state[i].pipes[j].maximum_packet_size = information->Pipes[j].MaximumPacketSize;
            initialize_pipe_policy(&state[i].pipes[j]);
        }
        cursor += size;
    }
    return cursor == select_size;
}

static BOOL calculate_select_size(const struct winusb_interface_state *state,
        ULONG interface_count, SIZE_T *size)
{
    SIZE_T total = offsetof(struct _URB_SELECT_CONFIGURATION, Interface);
    ULONG i;

    for (i = 0; i < interface_count; ++i)
    {
        SIZE_T pipes_size, interface_size;

        if (!multiply_size(state[i].endpoint_count,
                sizeof(USBD_PIPE_INFORMATION), &pipes_size) ||
                !add_size(offsetof(USBD_INTERFACE_INFORMATION, Pipes),
                pipes_size, &interface_size) || interface_size > 0xffffu ||
                !add_size(total, interface_size, &total) || total > 0xffffu)
            return FALSE;
    }
    *size = total;
    return TRUE;
}

static BOOL build_select_urb(struct _URB_SELECT_CONFIGURATION *select,
        SIZE_T select_size, USB_CONFIGURATION_DESCRIPTOR *configuration,
        const struct wine_winusb_snapshot *snapshot,
        const struct winusb_interface_state *state)
{
    const UCHAR *memory = (const UCHAR *)snapshot;
    SIZE_T cursor = offsetof(struct _URB_SELECT_CONFIGURATION, Interface);
    ULONG i;

    memset(select, 0, select_size);
    select->Hdr.Length = select_size;
    select->Hdr.Function = URB_FUNCTION_SELECT_CONFIGURATION;
    select->ConfigurationDescriptor = configuration;
    for (i = 0; i < snapshot->interface_count; ++i)
    {
        USBD_INTERFACE_INFORMATION *information;
        SIZE_T endpoint_end, interface_size, pipes_size;
        ULONG j;

        if (!multiply_size(state[i].endpoint_count,
                sizeof(USBD_PIPE_INFORMATION), &pipes_size) ||
                !add_size(offsetof(USBD_INTERFACE_INFORMATION, Pipes),
                pipes_size, &interface_size) || interface_size > 0xffffu ||
                !add_size(state[i].first_endpoint, state[i].endpoint_count,
                &endpoint_end) || endpoint_end > snapshot->endpoint_count ||
                cursor > select_size || interface_size > select_size - cursor)
            return FALSE;
        information = (void *)((UCHAR *)select + cursor);
        information->Length = interface_size;
        information->InterfaceNumber = state[i].interface_number;
        information->AlternateSetting = 0;
        information->NumberOfPipes = state[i].endpoint_count;
        for (j = 0; j < state[i].endpoint_count; ++j)
        {
            struct wine_winusb_endpoint_snapshot endpoint;
            USBD_PIPE_INFORMATION *pipe = &information->Pipes[j];
            SIZE_T endpoint_index;

            if (!add_size(state[i].first_endpoint, j, &endpoint_index) ||
                    !read_snapshot_record(memory, snapshot->total_size,
                    snapshot->endpoints_offset, endpoint_index,
                    sizeof(endpoint), &endpoint) ||
                    endpoint.pipe_id > 0xffu ||
                    endpoint.pipe_type > UsbdPipeTypeInterrupt ||
                    endpoint.maximum_packet_size > 0xffffu)
                return FALSE;
            pipe->MaximumPacketSize = endpoint.maximum_packet_size;
            pipe->EndpointAddress = endpoint.pipe_id;
            pipe->PipeType = endpoint.pipe_type;
        }
        cursor += interface_size;
    }
    return cursor == select_size;
}

static void restore_uninitialized(struct winusb_device *device,
        struct winusb_file *file)
{
    KIRQL device_irql, file_irql;

    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if (file->state == WINUSB_FILE_INITIALIZING)
    {
        file->state = WINUSB_FILE_UNINITIALIZED;
        file->session = 0;
        file->snapshot = NULL;
        file->snapshot_size = 0;
        file->interfaces = NULL;
        file->interface_count = 0;
    }
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
}

static UINT64 allocate_session_cookie(void)
{
    UINT64 cookie;
    KIRQL irql;

    KeAcquireSpinLock(&session_lock, &irql);
    cookie = ++session_counter;
    if (!cookie) cookie = ++session_counter;
    KeReleaseSpinLock(&session_lock, irql);
    return cookie;
}

void winusb_session_driver_init(void)
{
    KeInitializeSpinLock(&session_lock);
    session_counter = 0;
}

/* The lower layer keeps ownership of a failed finalization transaction.  R80
 * relies on the transport contract that an error did not consume its token. */
NTSTATUS winusb_session_recover_claim_transaction(struct winusb_device *device)
{
    NTSTATUS status;
    void *snapshot;
    struct winusb_interface_state *interfaces;

    if (!device->claim_transaction) return STATUS_SUCCESS;
    status = finalize_claim_transaction(device, device->claim_transaction,
            WINEUSB_CLAIM_TRANSACTION_ROLLBACK);
    if (!NT_SUCCESS(status)) return status;

    snapshot = device->claim_snapshot;
    interfaces = device->claim_interfaces;
    device->claim_transaction = NULL;
    device->claim_snapshot = NULL;
    device->claim_interfaces = NULL;
    if (interfaces) winusb_session_free_interfaces(interfaces,
            device->claim_interface_count);
    device->claim_interface_count = 0;
    if (snapshot) ExFreePool(snapshot);
    return STATUS_SUCCESS;
}

/* Called after REMOVE synchronously destroys the lower child.  That teardown
 * releases a still-pending lower journal, so the retained upper ownership can
 * now be discarded even when the one final rollback submission failed. */
void winusb_session_claim_child_removed(struct winusb_device *device)
{
    void *snapshot = device->claim_snapshot;
    struct winusb_interface_state *interfaces = device->claim_interfaces;

    device->claim_transaction = NULL;
    device->claim_snapshot = NULL;
    device->claim_interfaces = NULL;
    if (interfaces) winusb_session_free_interfaces(interfaces,
            device->claim_interface_count);
    device->claim_interface_count = 0;
    if (snapshot) ExFreePool(snapshot);
}

NTSTATUS winusb_session_initialize(struct winusb_device *device,
        struct winusb_file *file, const struct wine_winusb_request *request,
        ULONG input_length, MDL *mdl, ULONG output_length,
        ULONG_PTR *information)
{
    struct parsed_configuration parsed;
    struct wine_winusb_snapshot size_header;
    struct winusb_interface_state *interfaces = NULL;
    struct _URB_SELECT_CONFIGURATION *select = NULL;
    USB_DEVICE_DESCRIPTOR *device_descriptor = NULL;
    USB_CONFIGURATION_DESCRIPTOR *configuration_header = NULL;
    UCHAR *configuration = NULL, *output;
    void *snapshot = NULL;
    SIZE_T mapped_end, interfaces_size, select_size;
    ULONG returned, configuration_size = 0;
    UINT64 cookie;
    USBD_CONFIGURATION_HANDLE claim_transaction = NULL;
    NTSTATUS status = STATUS_INVALID_PARAMETER;
    KIRQL device_irql, file_irql;
    BOOL reserved = FALSE, committed = FALSE, finalization_locked = FALSE;

    *information = 0;
    if (!request || input_length != sizeof(*request) ||
            request->size != sizeof(*request) ||
            request->version != WINE_WINUSB_ABI_VERSION || request->session ||
            request->interface_index || request->reserved)
        return STATUS_INVALID_PARAMETER;
    if (!mdl || mdl->ByteCount < output_length) return STATUS_INVALID_PARAMETER;
    if (!(output = MmGetSystemAddressForMdlSafe(mdl, NormalPagePriority)))
        return STATUS_NO_MEMORY;
    if (!add_size((SIZE_T)output, output_length, &mapped_end))
        return STATUS_INVALID_PARAMETER;
    if (output_length < sizeof(struct wine_winusb_snapshot))
        return STATUS_BUFFER_TOO_SMALL;

    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if (device->state != WINUSB_DEVICE_STARTED ||
            file->state != WINUSB_FILE_UNINITIALIZED || file->session ||
            file->snapshot || file->interfaces)
        status = STATUS_INVALID_DEVICE_STATE;
    else
    {
        file->state = WINUSB_FILE_INITIALIZING;
        reserved = TRUE;
        status = STATUS_SUCCESS;
    }
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
    if (!NT_SUCCESS(status)) return status;

    /* Serializes recovery, SELECT, and finalization for this lower child. */
    ExAcquireFastMutex(&device->finalization_mutex);
    finalization_locked = TRUE;
    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if (device->state != WINUSB_DEVICE_STARTED ||
            file->state != WINUSB_FILE_INITIALIZING)
        status = STATUS_INVALID_DEVICE_STATE;
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
    if (!NT_SUCCESS(status)) goto done;
    if (!NT_SUCCESS(status = winusb_session_recover_claim_transaction(device)))
        goto done;

    if (!(device_descriptor = ExAllocatePool(NonPagedPool,
            sizeof(*device_descriptor))))
    {
        status = STATUS_NO_MEMORY;
        goto done;
    }
    returned = 0;
    if (!NT_SUCCESS(status = read_descriptor(device, USB_DEVICE_DESCRIPTOR_TYPE,
            device_descriptor, sizeof(*device_descriptor), &returned)))
        goto done;
    if (returned != sizeof(*device_descriptor) ||
            device_descriptor->bLength != sizeof(*device_descriptor) ||
            device_descriptor->bDescriptorType != USB_DEVICE_DESCRIPTOR_TYPE)
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }

    if (!(configuration_header = ExAllocatePool(NonPagedPool,
            sizeof(*configuration_header))))
    {
        status = STATUS_NO_MEMORY;
        goto done;
    }
    returned = 0;
    if (!NT_SUCCESS(status = read_descriptor(device,
            USB_CONFIGURATION_DESCRIPTOR_TYPE, configuration_header,
            sizeof(*configuration_header), &returned)))
        goto done;
    if (returned != sizeof(*configuration_header) ||
            configuration_header->bLength != sizeof(*configuration_header) ||
            configuration_header->bDescriptorType != USB_CONFIGURATION_DESCRIPTOR_TYPE ||
            configuration_header->wTotalLength < sizeof(*configuration_header))
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }
    configuration_size = configuration_header->wTotalLength;
    if (!(configuration = ExAllocatePool(NonPagedPool, configuration_size)))
    {
        status = STATUS_NO_MEMORY;
        goto done;
    }
    returned = 0;
    if (!NT_SUCCESS(status = read_descriptor(device,
            USB_CONFIGURATION_DESCRIPTOR_TYPE, configuration,
            configuration_size, &returned)))
        goto done;
    if (returned != configuration_size ||
            !parse_configuration(configuration, configuration_size, &parsed))
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }

    memset(&size_header, 0, sizeof(size_header));
    size_header.size = sizeof(size_header);
    size_header.version = WINE_WINUSB_ABI_VERSION;
    size_header.speed = device->speed;
    size_header.total_size = parsed.total_size;
    size_header.device_offset = parsed.device_offset;
    size_header.device_length = sizeof(*device_descriptor);
    size_header.configuration_offset = parsed.configuration_offset;
    size_header.configuration_length = configuration_size;
    size_header.interfaces_offset = parsed.interfaces_offset;
    size_header.interface_count = parsed.interface_count;
    size_header.alternates_offset = parsed.alternates_offset;
    size_header.alternate_count = parsed.alternate_count;
    size_header.endpoints_offset = parsed.endpoints_offset;
    size_header.endpoint_count = parsed.endpoint_count;
    if (output_length < parsed.total_size)
    {
        memcpy(output, &size_header, sizeof(size_header));
        *information = sizeof(size_header);
        status = STATUS_BUFFER_TOO_SMALL;
        goto done;
    }
    if (output_length != parsed.total_size)
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }

    if (!(snapshot = ExAllocatePool(NonPagedPool, parsed.total_size)))
    {
        status = STATUS_NO_MEMORY;
        goto done;
    }
    if (!build_snapshot(snapshot, device_descriptor, configuration, &parsed,
            device->speed))
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }
    if (!multiply_size(parsed.interface_count, sizeof(*interfaces),
            &interfaces_size) ||
            !(interfaces = ExAllocatePool(NonPagedPool, interfaces_size)))
    {
        status = STATUS_NO_MEMORY;
        goto done;
    }
    if (!build_interface_state(snapshot, interfaces) ||
            !allocate_pipe_maps(interfaces, parsed.interface_count))
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }
    if (!calculate_select_size(interfaces, parsed.interface_count, &select_size) ||
            !(select = ExAllocatePool(NonPagedPool, select_size)))
    {
        status = STATUS_NO_MEMORY;
        goto done;
    }
    if (!build_select_urb(select, select_size, (void *)configuration, snapshot,
            interfaces))
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }
    if (!NT_SUCCESS(status = submit_urb(device, (URB *)select))) goto done;
    claim_transaction = select->ConfigurationHandle;
    if (!capture_select_pipe_handles(select, select_size, interfaces,
            parsed.interface_count))
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }

    cookie = allocate_session_cookie();
    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if (device->state != WINUSB_DEVICE_STARTED ||
            file->state != WINUSB_FILE_INITIALIZING || file->session ||
            file->snapshot || file->interfaces)
        status = STATUS_INVALID_DEVICE_STATE;
    else status = STATUS_SUCCESS;
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);

    if (!NT_SUCCESS(status))
    {
        NTSTATUS rollback_status = STATUS_SUCCESS;

        if (claim_transaction)
            rollback_status = finalize_claim_transaction(device, claim_transaction,
                    WINEUSB_CLAIM_TRANSACTION_ROLLBACK);
        if (!NT_SUCCESS(rollback_status)) status = rollback_status;
        if (!NT_SUCCESS(rollback_status))
        {
            device->claim_transaction = claim_transaction;
            device->claim_snapshot = snapshot;
            device->claim_interfaces = interfaces;
            device->claim_interface_count = parsed.interface_count;
            claim_transaction = NULL;
            snapshot = NULL;
            interfaces = NULL;
        }
        goto done;
    }

    if (claim_transaction && !NT_SUCCESS(status = finalize_claim_transaction(device,
            claim_transaction, WINEUSB_CLAIM_TRANSACTION_COMMIT)))
    {
        NTSTATUS rollback_status = finalize_claim_transaction(device,
                claim_transaction, WINEUSB_CLAIM_TRANSACTION_ROLLBACK);

        if (!NT_SUCCESS(rollback_status))
        {
            device->claim_transaction = claim_transaction;
            device->claim_snapshot = snapshot;
            device->claim_interfaces = interfaces;
            device->claim_interface_count = parsed.interface_count;
            claim_transaction = NULL;
            snapshot = NULL;
            interfaces = NULL;
            status = rollback_status;
        }
        goto done;
    }
    claim_transaction = NULL;

    /* Do not expose a usable file session until the lower COMMIT succeeded. */
    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if (device->state != WINUSB_DEVICE_STARTED ||
            file->state != WINUSB_FILE_INITIALIZING || file->session ||
            file->snapshot || file->interfaces)
        status = STATUS_INVALID_DEVICE_STATE;
    else
    {
        ((struct wine_winusb_snapshot *)snapshot)->session = cookie;
        file->snapshot = snapshot;
        file->snapshot_size = parsed.total_size;
        file->interfaces = interfaces;
        file->interface_count = parsed.interface_count;
        file->session = cookie;
        file->state = WINUSB_FILE_INITIALIZED;
        committed = TRUE;
        status = STATUS_SUCCESS;
    }
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
    if (!committed) goto done;
    memcpy(output, snapshot, parsed.total_size);
    *information = parsed.total_size;
    status = STATUS_SUCCESS;

done:
    if (select) ExFreePool(select);
    if (!committed && interfaces) winusb_session_free_interfaces(interfaces, parsed.interface_count);
    if (!committed && snapshot) ExFreePool(snapshot);
    if (configuration) ExFreePool(configuration);
    if (configuration_header) ExFreePool(configuration_header);
    if (device_descriptor) ExFreePool(device_descriptor);
    if (reserved && !committed) restore_uninitialized(device, file);
    if (finalization_locked) ExReleaseFastMutex(&device->finalization_mutex);
    return status;
}

NTSTATUS winusb_session_set_alternate(struct winusb_device *device,
        struct winusb_file *file, const struct wine_winusb_alternate_request *request,
        ULONG input_length, ULONG_PTR *information)
{
    const struct wine_winusb_snapshot *snapshot;
    const UCHAR *memory;
    struct wine_winusb_interface_snapshot interface_record;
    struct wine_winusb_alternate_snapshot alternate_record;
    struct _URB_SELECT_INTERFACE *select = NULL;
    struct winusb_pipe_state *pipes = NULL, *old_pipes = NULL;
    SIZE_T size, interface_size, i, pipes_size;
    KIRQL device_irql, file_irql;
    ULONG j;
    NTSTATUS status;

    *information = 0;
    if (!request || input_length != sizeof(*request) ||
            request->request.size != sizeof(*request) ||
            request->request.version != WINE_WINUSB_ABI_VERSION ||
            request->request.reserved || request->reserved ||
            !request->request.session)
        return STATUS_INVALID_PARAMETER;

    /* PnP transitions and a physical alternate change must not interleave.
     * The device-control caller holds file->session_mutex, so publication is
     * also atomic with release/cleanup/close for this file. */
    ExAcquireFastMutex(&device->finalization_mutex);
    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if (device->state != WINUSB_DEVICE_STARTED ||
            file->state != WINUSB_FILE_INITIALIZED ||
            request->request.session != file->session || !file->snapshot ||
            !file->interfaces || request->request.interface_index >= file->interface_count ||
            /* This IOCTL itself has one outstanding reference.  Until real
             * transfer records exist, reject every concurrent file request. */
            file->outstanding != 1)
        status = STATUS_INVALID_DEVICE_STATE;
    else
        status = STATUS_SUCCESS;
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
    if (!NT_SUCCESS(status)) goto done;

    snapshot = file->snapshot; memory = (const UCHAR *)snapshot;
    if (!read_snapshot_record(memory, snapshot->total_size, snapshot->interfaces_offset,
            request->request.interface_index, sizeof(interface_record), &interface_record))
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }
    for (i = 0; i < interface_record.alternate_count; ++i)
    {
        if (!read_snapshot_record(memory, snapshot->total_size, snapshot->alternates_offset,
                interface_record.first_alternate + i, sizeof(alternate_record), &alternate_record))
        {
            status = STATUS_INVALID_PARAMETER;
            goto done;
        }
        if (alternate_record.alternate_setting == request->alternate_setting) break;
    }
    if (i == interface_record.alternate_count || alternate_record.interface_index != request->request.interface_index ||
            !multiply_size(alternate_record.endpoint_count, sizeof(*pipes), &pipes_size) ||
            !add_size(offsetof(USBD_INTERFACE_INFORMATION, Pipes), alternate_record.endpoint_count * sizeof(USBD_PIPE_INFORMATION), &interface_size) ||
            !add_size(offsetof(struct _URB_SELECT_INTERFACE, Interface), interface_size, &size) || size > 0xffff)
    {
        status = STATUS_INVALID_PARAMETER;
        goto done;
    }
    if (alternate_record.endpoint_count &&
            !(pipes = ExAllocatePool(NonPagedPool, pipes_size)))
    {
        status = STATUS_NO_MEMORY;
        goto done;
    }
    if (!(select = ExAllocatePool(NonPagedPool, size)))
    {
        status = STATUS_NO_MEMORY;
        goto done;
    }
    memset(select, 0, size); select->Hdr.Length = size; select->Hdr.Function = URB_FUNCTION_SELECT_INTERFACE;
    select->Interface.Length = interface_size; select->Interface.InterfaceNumber = interface_record.interface_number;
    select->Interface.AlternateSetting = alternate_record.alternate_setting; select->Interface.NumberOfPipes = alternate_record.endpoint_count;
    for (j = 0; j < alternate_record.endpoint_count; ++j)
    {
        struct wine_winusb_endpoint_snapshot endpoint;
        if (!read_snapshot_record(memory, snapshot->total_size, snapshot->endpoints_offset,
                alternate_record.first_endpoint + j, sizeof(endpoint), &endpoint))
        {
            status = STATUS_INVALID_PARAMETER;
            goto done;
        }
        select->Interface.Pipes[j].EndpointAddress = endpoint.pipe_id; select->Interface.Pipes[j].PipeType = endpoint.pipe_type;
        select->Interface.Pipes[j].MaximumPacketSize = endpoint.maximum_packet_size;
    }
    status = submit_urb(device, (URB *)select);
    if (!NT_SUCCESS(status)) goto done;

    /* The lower layer owns token generation.  Preserve only the opaque
     * handles it returned, alongside descriptor metadata already validated
     * above. */
    for (j = 0; j < alternate_record.endpoint_count; ++j)
    {
        pipes[j].handle = select->Interface.Pipes[j].PipeHandle;
        pipes[j].endpoint = select->Interface.Pipes[j].EndpointAddress;
        pipes[j].type = select->Interface.Pipes[j].PipeType;
        pipes[j].maximum_packet_size = select->Interface.Pipes[j].MaximumPacketSize;
        initialize_pipe_policy(&pipes[j]);
    }

    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if (device->state != WINUSB_DEVICE_STARTED ||
            file->state != WINUSB_FILE_INITIALIZED ||
            request->request.session != file->session || !file->snapshot ||
            !file->interfaces || request->request.interface_index >= file->interface_count ||
            file->outstanding != 1)
        status = STATUS_INVALID_DEVICE_STATE;
    else
    {
        struct winusb_interface_state *state =
                &file->interfaces[request->request.interface_index];

        old_pipes = state->pipes;
        state->pipes = pipes;
        state->alternate_setting = alternate_record.alternate_setting;
        state->first_endpoint = alternate_record.first_endpoint;
        state->endpoint_count = alternate_record.endpoint_count;
        if (++state->generation == 0) ++state->generation;
        pipes = NULL;
        status = STATUS_SUCCESS;
    }
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
    if (NT_SUCCESS(status) && old_pipes) ExFreePool(old_pipes);

done:
    if (select) ExFreePool(select);
    if (pipes) ExFreePool(pipes);
    ExReleaseFastMutex(&device->finalization_mutex);
    return status;
}

static NTSTATUS validate_policy_header(const struct wine_winusb_policy_request *request,
        ULONG input_length, ULONG output_length, BOOL get)
{
    if (!request || input_length != sizeof(*request) ||
            (get ? output_length != sizeof(*request) : output_length) ||
            request->request.size != sizeof(*request) ||
            request->request.version != WINE_WINUSB_ABI_VERSION ||
            request->request.reserved || !request->request.session)
        return STATUS_INVALID_PARAMETER;
    return STATUS_SUCCESS;
}

static NTSTATUS lookup_policy_pipe(struct winusb_device *device, struct winusb_file *file,
        const struct wine_winusb_policy_request *request, struct winusb_pipe_state **result)
{
    struct winusb_interface_state *interface;
    KIRQL device_irql, file_irql;
    ULONG i;
    NTSTATUS status;

    /* Device-control, cleanup, close, initialize, and alternate selection all
     * hold this file's session_mutex.  The returned map entry therefore stays
     * live after the short spin-lock lookup until this IOCTL releases it. */
    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if (device->state != WINUSB_DEVICE_STARTED || file->state != WINUSB_FILE_INITIALIZED ||
            request->request.session != file->session || !file->interfaces ||
            request->request.interface_index >= file->interface_count)
        status = STATUS_INVALID_DEVICE_STATE;
    else
    {
        interface = &file->interfaces[request->request.interface_index];
        status = STATUS_INVALID_PARAMETER;
        if (request->pipe_id && interface->pipes)
            for (i = 0; i < interface->endpoint_count; ++i)
                if (interface->pipes[i].endpoint == request->pipe_id)
                {
                    *result = &interface->pipes[i];
                    status = STATUS_SUCCESS;
                    break;
                }
    }
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);
    return status;
}

static NTSTATUS validate_pipe_policy(const struct winusb_pipe_state *pipe, ULONG policy,
        ULONG *length)
{
    BOOL in = pipe->endpoint & 0x80;

    if (pipe->type != UsbdPipeTypeBulk) return STATUS_INVALID_PARAMETER;
    switch (policy)
    {
        case SHORT_PACKET_TERMINATE:
            if (in) return STATUS_INVALID_PARAMETER;
            *length = 1;
            break;
        case AUTO_CLEAR_STALL:
        case IGNORE_SHORT_PACKETS:
        case ALLOW_PARTIAL_READS:
        case AUTO_FLUSH:
        case RAW_IO:
            if (!in) return STATUS_INVALID_PARAMETER;
            *length = 1;
            break;
        case PIPE_TRANSFER_TIMEOUT:
        case MAXIMUM_TRANSFER_SIZE:
            *length = sizeof(ULONG);
            break;
        case RESET_PIPE_ON_RESUME:
            *length = 1;
            break;
        default:
            return STATUS_INVALID_PARAMETER;
    }
    return STATUS_SUCCESS;
}

static ULONG get_pipe_policy_value(const struct winusb_pipe_state *pipe, ULONG policy)
{
    switch (policy)
    {
        case SHORT_PACKET_TERMINATE: return pipe->policy.short_packet_terminate;
        case AUTO_CLEAR_STALL: return pipe->policy.auto_clear_stall;
        case PIPE_TRANSFER_TIMEOUT: return pipe->policy.timeout;
        case IGNORE_SHORT_PACKETS: return pipe->policy.ignore_short_packets;
        case ALLOW_PARTIAL_READS: return pipe->policy.allow_partial_reads;
        case AUTO_FLUSH: return pipe->policy.auto_flush;
        case RAW_IO: return pipe->policy.raw_io;
        case MAXIMUM_TRANSFER_SIZE: return pipe->policy.maximum_transfer_size;
        case RESET_PIPE_ON_RESUME: return pipe->policy.reset_pipe_on_resume;
    }
    return 0;
}

NTSTATUS winusb_session_get_pipe_policy(struct winusb_device *device,
        struct winusb_file *file, struct wine_winusb_policy_request *request,
        ULONG input_length, ULONG output_length, ULONG_PTR *information)
{
    struct winusb_pipe_state *pipe;
    ULONG length;
    NTSTATUS status;

    *information = 0;
    if (!NT_SUCCESS(status = validate_policy_header(request, input_length, output_length, TRUE)) ||
            !NT_SUCCESS(status = lookup_policy_pipe(device, file, request, &pipe)) ||
            !NT_SUCCESS(status = validate_pipe_policy(pipe, request->policy_id, &length)))
        return status;
    if (request->value_length < length) return STATUS_INVALID_PARAMETER;

    request->value_length = length;
    request->value = get_pipe_policy_value(pipe, request->policy_id);
    *information = sizeof(*request);
    return STATUS_SUCCESS;
}

NTSTATUS winusb_session_set_pipe_policy(struct winusb_device *device,
        struct winusb_file *file, const struct wine_winusb_policy_request *request,
        ULONG input_length, ULONG output_length, ULONG_PTR *information)
{
    struct winusb_pipe_state *pipe;
    ULONG length;
    NTSTATUS status;

    *information = 0;
    if (!NT_SUCCESS(status = validate_policy_header(request, input_length, output_length, FALSE)) ||
            !NT_SUCCESS(status = lookup_policy_pipe(device, file, request, &pipe)) ||
            !NT_SUCCESS(status = validate_pipe_policy(pipe, request->policy_id, &length)))
        return status;
    if (request->value_length != length || (length == 1 && request->value > 1))
        return STATUS_INVALID_PARAMETER;

    switch (request->policy_id)
    {
        case SHORT_PACKET_TERMINATE:
            if (request->value) return STATUS_NOT_SUPPORTED;
            pipe->policy.short_packet_terminate = FALSE;
            return STATUS_SUCCESS;
        case AUTO_CLEAR_STALL:
            if (request->value) return STATUS_NOT_SUPPORTED;
            pipe->policy.auto_clear_stall = FALSE;
            return STATUS_SUCCESS;
        case IGNORE_SHORT_PACKETS:
            if (request->value) return STATUS_NOT_SUPPORTED;
            pipe->policy.ignore_short_packets = FALSE;
            return STATUS_SUCCESS;
        case AUTO_FLUSH:
            if (request->value) return STATUS_NOT_SUPPORTED;
            pipe->policy.auto_flush = FALSE;
            return STATUS_SUCCESS;
        case RESET_PIPE_ON_RESUME:
            if (request->value) return STATUS_NOT_SUPPORTED;
            pipe->policy.reset_pipe_on_resume = FALSE;
            return STATUS_SUCCESS;
        case PIPE_TRANSFER_TIMEOUT:
            if (request->value) return STATUS_NOT_SUPPORTED;
            pipe->policy.timeout = 0;
            return STATUS_SUCCESS;
        case ALLOW_PARTIAL_READS:
            pipe->policy.allow_partial_reads = request->value;
            return STATUS_SUCCESS;
        case RAW_IO:
            pipe->policy.raw_io = request->value;
            return STATUS_SUCCESS;
        case MAXIMUM_TRANSFER_SIZE:
            return STATUS_INVALID_PARAMETER;
    }
    return STATUS_INVALID_PARAMETER;
}

NTSTATUS winusb_session_release(struct winusb_device *device,
        struct winusb_file *file, const struct wine_winusb_request *request,
        ULONG input_length, ULONG_PTR *information)
{
    struct winusb_interface_state *interfaces;
    void *snapshot;
    ULONG interface_count;
    KIRQL device_irql, file_irql;

    *information = 0;
    if (!request || input_length != sizeof(*request) ||
            request->size != sizeof(*request) ||
            request->version != WINE_WINUSB_ABI_VERSION || !request->session ||
            request->interface_index || request->reserved)
        return STATUS_INVALID_PARAMETER;

    KeAcquireSpinLock(&device->lock, &device_irql);
    KeAcquireSpinLock(&file->lock, &file_irql);
    if ((device->state == WINUSB_DEVICE_SURPRISE_REMOVED ||
            device->state == WINUSB_DEVICE_REMOVED) ||
            file->state != WINUSB_FILE_INITIALIZED ||
            file->session != request->session || !file->snapshot ||
            !file->interfaces)
    {
        KeReleaseSpinLock(&file->lock, file_irql);
        KeReleaseSpinLock(&device->lock, device_irql);
        return STATUS_INVALID_DEVICE_STATE;
    }
    file->state = WINUSB_FILE_RELEASING;
    snapshot = file->snapshot;
    interfaces = file->interfaces;
    interface_count = file->interface_count;
    file->snapshot = NULL;
    file->snapshot_size = 0;
    file->interfaces = NULL;
    file->interface_count = 0;
    file->session = 0;
    file->state = WINUSB_FILE_UNINITIALIZED;
    KeReleaseSpinLock(&file->lock, file_irql);
    KeReleaseSpinLock(&device->lock, device_irql);

    winusb_session_free_interfaces(interfaces, interface_count);
    ExFreePool(snapshot);
    return STATUS_SUCCESS;
}
