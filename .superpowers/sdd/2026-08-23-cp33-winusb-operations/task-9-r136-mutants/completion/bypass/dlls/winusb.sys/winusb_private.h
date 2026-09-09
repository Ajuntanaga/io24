/*
 * Private state for the generic WinUSB function driver
 *
 * Copyright 2026 the Wine project
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 */

#ifndef __WINE_WINUSB_PRIVATE_H
#define __WINE_WINUSB_PRIVATE_H

#include "windef.h"
#include "ddk/wdm.h"
#include "wine/winusb.h"

struct winusb_interface_state
{
    ULONG interface_number;
    ULONG alternate_setting;
    ULONG first_endpoint;
    ULONG endpoint_count;
    ULONG generation;
    struct winusb_pipe_state *pipes;
};

struct winusb_pipe_policy
{
    ULONG timeout;
    ULONG maximum_transfer_size;
    BOOL short_packet_terminate;
    BOOL auto_clear_stall;
    BOOL ignore_short_packets;
    BOOL allow_partial_reads;
    BOOL auto_flush;
    BOOL raw_io;
    BOOL reset_pipe_on_resume;
};

/* Pipe handles are opaque lower-layer tokens.  This driver only retains the
 * values returned in a successful select URB; it never manufactures one. */
struct winusb_pipe_state
{
    USBD_PIPE_HANDLE handle;
    UCHAR endpoint;
    UCHAR type;
    USHORT maximum_packet_size;
    struct winusb_pipe_policy policy;
};

enum winusb_device_state
{
    WINUSB_DEVICE_ADDED,
    WINUSB_DEVICE_STARTED,
    WINUSB_DEVICE_STOPPED,
    WINUSB_DEVICE_SURPRISE_REMOVED,
    WINUSB_DEVICE_REMOVED,
};

enum winusb_file_state
{
    WINUSB_FILE_UNINITIALIZED,
    WINUSB_FILE_INITIALIZING,
    WINUSB_FILE_INITIALIZED,
    WINUSB_FILE_RELEASING,
    WINUSB_FILE_CLOSING,
    WINUSB_FILE_REMOVED,
};

struct winusb_file
{
    LIST_ENTRY device_entry;
    FILE_OBJECT *file_object;
    KSPIN_LOCK lock;
    FAST_MUTEX session_mutex;
    enum winusb_file_state state;
    UINT64 session;
    LONG references;
    LONG outstanding;
    KEVENT zero_outstanding;
    LIST_ENTRY transfers;
    void *snapshot;
    ULONG snapshot_size;
    struct winusb_interface_state *interfaces;
    ULONG interface_count;
};

struct winusb_device
{
    DEVICE_OBJECT *pdo;
    DEVICE_OBJECT *lower_device;
    GUID interface_guid;
    UNICODE_STRING symbolic_link;
    BOOL registered;
    BOOL enabled;
    enum winusb_device_state state;
    KSPIN_LOCK lock;
    FAST_MUTEX finalization_mutex;
    LIST_ENTRY files;
    ULONG file_count;
    KEVENT removal_event;
    USHORT metadata_interface_version;
    UCHAR speed;
    USBD_CONFIGURATION_HANDLE claim_transaction;
    void *claim_snapshot;
    struct winusb_interface_state *claim_interfaces;
    ULONG claim_interface_count;
};

void winusb_session_driver_init(void);
NTSTATUS winusb_session_initialize(struct winusb_device *device,
        struct winusb_file *file, const struct wine_winusb_request *request,
        ULONG input_length, MDL *mdl, ULONG output_length,
        ULONG_PTR *information);
NTSTATUS winusb_session_release(struct winusb_device *device,
        struct winusb_file *file, const struct wine_winusb_request *request,
        ULONG input_length, ULONG_PTR *information);
NTSTATUS winusb_session_set_alternate(struct winusb_device *device,
        struct winusb_file *file, const struct wine_winusb_alternate_request *request,
        ULONG input_length, ULONG_PTR *information);
NTSTATUS winusb_session_get_pipe_policy(struct winusb_device *device,
        struct winusb_file *file, struct wine_winusb_policy_request *request,
        ULONG input_length, ULONG output_length, ULONG_PTR *information);
NTSTATUS winusb_session_set_pipe_policy(struct winusb_device *device,
        struct winusb_file *file, const struct wine_winusb_policy_request *request,
        ULONG input_length, ULONG output_length, ULONG_PTR *information);
NTSTATUS winusb_session_recover_claim_transaction(struct winusb_device *device);
void winusb_session_claim_child_removed(struct winusb_device *device);
void winusb_session_free_interfaces(struct winusb_interface_state *interfaces,
        ULONG count);
void winusb_release_file_from_io(struct winusb_file *file);
NTSTATUS winusb_dispatch_control_or_descriptor(struct winusb_device *device,
        struct winusb_file *file, IRP *irp, ULONG code,
        const struct wine_winusb_request *request, ULONG input_length,
        ULONG output_length, BOOL *irp_consumed);

#endif /* __WINE_WINUSB_PRIVATE_H */
