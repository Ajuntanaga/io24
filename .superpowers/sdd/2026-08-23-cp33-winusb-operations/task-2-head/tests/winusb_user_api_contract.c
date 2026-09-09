/* Executed host contract for the actual winusb.dll production module. */
#include <dlfcn.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "windef.h"
#include "winbase.h"
#include "winusb.h"
#include "wine/winusb.h"
#include "wine/debug.h"

#define IO24_FIELD_TYPE(type, member, expected) \
    _Static_assert(_Generic(((struct type *)0)->member, expected: 1, default: 0), #type "." #member " type")

_Static_assert(SHORT_PACKET_TERMINATE == 0x01 && AUTO_CLEAR_STALL == 0x02 && PIPE_TRANSFER_TIMEOUT == 0x03, "policy ids 1-3");
_Static_assert(IGNORE_SHORT_PACKETS == 0x04 && ALLOW_PARTIAL_READS == 0x05 && AUTO_FLUSH == 0x06, "policy ids 4-6");
_Static_assert(RAW_IO == 0x07 && MAXIMUM_TRANSFER_SIZE == 0x08 && RESET_PIPE_ON_RESUME == 0x09, "policy ids 7-9");
_Static_assert(DEVICE_SPEED == 0x01 && LowSpeed == 0x01 && FullSpeed == 0x02 && HighSpeed == 0x03 && SuperSpeed == 0x04, "speed ids");
_Static_assert(WINE_WINUSB_ABI_VERSION == 1, "private ABI version");
_Static_assert(WINE_WINUSB_MAX_CONTROL_TRANSFER == 4096u, "control transfer cap");
_Static_assert(WINE_WINUSB_MAXIMUM_TRANSFER_SIZE == 4u * 1024u * 1024u, "pipe transfer cap");
_Static_assert(sizeof(WINUSB_SETUP_PACKET) == 8, "WINUSB_SETUP_PACKET size");
_Static_assert(offsetof(WINUSB_SETUP_PACKET, RequestType) == 0, "setup RequestType offset");
_Static_assert(offsetof(WINUSB_SETUP_PACKET, Request) == 1, "setup Request offset");
_Static_assert(offsetof(WINUSB_SETUP_PACKET, Value) == 2, "setup Value offset");
_Static_assert(offsetof(WINUSB_SETUP_PACKET, Index) == 4, "setup Index offset");
_Static_assert(offsetof(WINUSB_SETUP_PACKET, Length) == 6, "setup Length offset");

_Static_assert(sizeof(struct wine_winusb_request) == 24, "request size");
_Static_assert(offsetof(struct wine_winusb_request, size) == 0, "request size offset");
_Static_assert(offsetof(struct wine_winusb_request, version) == 4, "request version offset");
_Static_assert(offsetof(struct wine_winusb_request, session) == 8, "request session offset");
_Static_assert(offsetof(struct wine_winusb_request, interface_index) == 16, "request interface offset");
_Static_assert(offsetof(struct wine_winusb_request, reserved) == 20, "request reserved offset");
IO24_FIELD_TYPE(wine_winusb_request, size, UINT32);
IO24_FIELD_TYPE(wine_winusb_request, version, UINT32);
IO24_FIELD_TYPE(wine_winusb_request, session, UINT64);
IO24_FIELD_TYPE(wine_winusb_request, interface_index, UINT32);
IO24_FIELD_TYPE(wine_winusb_request, reserved, UINT32);

_Static_assert(sizeof(struct wine_winusb_snapshot) == 72, "snapshot size");
_Static_assert(offsetof(struct wine_winusb_snapshot, session) == 8, "snapshot session offset");
_Static_assert(offsetof(struct wine_winusb_snapshot, speed) == 16, "snapshot speed offset");
_Static_assert(offsetof(struct wine_winusb_snapshot, reserved) == 64, "snapshot reserved offset");
IO24_FIELD_TYPE(wine_winusb_snapshot, size, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, version, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, session, UINT64);
IO24_FIELD_TYPE(wine_winusb_snapshot, speed, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, total_size, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, device_offset, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, device_length, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, configuration_offset, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, configuration_length, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, interfaces_offset, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, interface_count, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, alternates_offset, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, alternate_count, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, endpoints_offset, UINT32);
IO24_FIELD_TYPE(wine_winusb_snapshot, endpoint_count, UINT32);
_Static_assert(_Generic(((struct wine_winusb_snapshot *)0)->reserved[0], UINT32: 1, default: 0), "snapshot reserved element type");
_Static_assert(sizeof(((struct wine_winusb_snapshot *)0)->reserved) == 2 * sizeof(UINT32), "snapshot reserved count");

#define IO24_ASSERT_RECORD(type, f0, f1, f2, f3) \
    _Static_assert(sizeof(struct type) == 16, #type " size"); \
    _Static_assert(offsetof(struct type, f0) == 0, #type " first offset"); \
    _Static_assert(offsetof(struct type, f1) == 4, #type " second offset"); \
    _Static_assert(offsetof(struct type, f2) == 8, #type " third offset"); \
    _Static_assert(offsetof(struct type, f3) == 12, #type " fourth offset"); \
    IO24_FIELD_TYPE(type, f0, UINT32); \
    IO24_FIELD_TYPE(type, f1, UINT32); \
    IO24_FIELD_TYPE(type, f2, UINT32); \
    IO24_FIELD_TYPE(type, f3, UINT32)
IO24_ASSERT_RECORD(wine_winusb_interface_snapshot, interface_number, first_alternate, alternate_count, reserved);
IO24_ASSERT_RECORD(wine_winusb_alternate_snapshot, interface_index, alternate_setting, first_endpoint, endpoint_count);
IO24_ASSERT_RECORD(wine_winusb_endpoint_snapshot, alternate_index, pipe_id, pipe_type, maximum_packet_size);

_Static_assert(sizeof(struct wine_winusb_alternate_request) == 32, "alternate request size");
_Static_assert(sizeof(struct wine_winusb_pipe_request) == 32, "pipe request size");
_Static_assert(sizeof(struct wine_winusb_descriptor_request) == 40, "descriptor request size");
_Static_assert(sizeof(struct wine_winusb_policy_request) == 40, "policy request size");
_Static_assert(sizeof(struct wine_winusb_control_request) == 40, "control request size");
_Static_assert(offsetof(struct wine_winusb_alternate_request, request) == 0 && offsetof(struct wine_winusb_alternate_request, alternate_setting) == 24 && offsetof(struct wine_winusb_alternate_request, reserved) == 28, "alternate request offsets");
_Static_assert(offsetof(struct wine_winusb_pipe_request, request) == 0 && offsetof(struct wine_winusb_pipe_request, pipe_id) == 24 && offsetof(struct wine_winusb_pipe_request, transfer_length) == 28, "pipe request offsets");
_Static_assert(offsetof(struct wine_winusb_descriptor_request, request) == 0 && offsetof(struct wine_winusb_descriptor_request, type) == 24 && offsetof(struct wine_winusb_descriptor_request, index) == 28 && offsetof(struct wine_winusb_descriptor_request, language) == 32 && offsetof(struct wine_winusb_descriptor_request, length) == 36, "descriptor request offsets");
_Static_assert(offsetof(struct wine_winusb_policy_request, request) == 0 && offsetof(struct wine_winusb_policy_request, pipe_id) == 24 && offsetof(struct wine_winusb_policy_request, policy_id) == 28 && offsetof(struct wine_winusb_policy_request, value_length) == 32 && offsetof(struct wine_winusb_policy_request, value) == 36, "policy request offsets");
_Static_assert(offsetof(struct wine_winusb_control_request, request) == 0 && offsetof(struct wine_winusb_control_request, setup) == 24 && offsetof(struct wine_winusb_control_request, transfer_length) == 32 && offsetof(struct wine_winusb_control_request, reserved) == 36, "control request offsets");
IO24_FIELD_TYPE(wine_winusb_alternate_request, alternate_setting, UINT32);
IO24_FIELD_TYPE(wine_winusb_alternate_request, reserved, UINT32);
IO24_FIELD_TYPE(wine_winusb_pipe_request, pipe_id, UINT32);
IO24_FIELD_TYPE(wine_winusb_pipe_request, transfer_length, UINT32);
IO24_FIELD_TYPE(wine_winusb_descriptor_request, type, UINT32);
IO24_FIELD_TYPE(wine_winusb_descriptor_request, index, UINT32);
IO24_FIELD_TYPE(wine_winusb_descriptor_request, language, UINT32);
IO24_FIELD_TYPE(wine_winusb_descriptor_request, length, UINT32);
IO24_FIELD_TYPE(wine_winusb_policy_request, pipe_id, UINT32);
IO24_FIELD_TYPE(wine_winusb_policy_request, policy_id, UINT32);
IO24_FIELD_TYPE(wine_winusb_policy_request, value_length, UINT32);
IO24_FIELD_TYPE(wine_winusb_policy_request, value, UINT32);
_Static_assert(_Generic(((struct wine_winusb_control_request *)0)->setup[0], UINT8: 1, default: 0), "control setup element type");
_Static_assert(sizeof(((struct wine_winusb_control_request *)0)->setup) == 8, "control setup count");
IO24_FIELD_TYPE(wine_winusb_control_request, transfer_length, UINT32);
IO24_FIELD_TYPE(wine_winusb_control_request, reserved, UINT32);

#define IO24_ASSERT_IOCTL(name, function, method) \
    _Static_assert(((name >> 2) & 0xfff) == function && (name & 3) == method, #name " function/method")
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_INITIALIZE, 0x800, METHOD_OUT_DIRECT);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_RELEASE, 0x801, METHOD_BUFFERED);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_GET_DESCRIPTOR, 0x802, METHOD_OUT_DIRECT);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_SET_ALTERNATE, 0x803, METHOD_BUFFERED);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_GET_PIPE_POLICY, 0x804, METHOD_BUFFERED);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_SET_PIPE_POLICY, 0x805, METHOD_BUFFERED);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_CONTROL_IN, 0x806, METHOD_OUT_DIRECT);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_CONTROL_OUT, 0x807, METHOD_IN_DIRECT);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_READ_PIPE, 0x808, METHOD_OUT_DIRECT);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_WRITE_PIPE, 0x809, METHOD_IN_DIRECT);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_ABORT_PIPE, 0x80a, METHOD_BUFFERED);
IO24_ASSERT_IOCTL(IOCTL_WINE_WINUSB_RESET_PIPE, 0x80b, METHOD_BUFFERED);

typedef BOOL (WINAPI *io24_proto_abort)(WINUSB_INTERFACE_HANDLE, UCHAR);
typedef BOOL (WINAPI *io24_proto_control)(WINUSB_INTERFACE_HANDLE, WINUSB_SETUP_PACKET, PUCHAR, ULONG, PULONG, LPOVERLAPPED);
typedef BOOL (WINAPI *io24_proto_free)(WINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *io24_proto_associated)(WINUSB_INTERFACE_HANDLE, UCHAR, PWINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *io24_proto_descriptor)(WINUSB_INTERFACE_HANDLE, UCHAR, UCHAR, USHORT, PUCHAR, ULONG, PULONG);
typedef BOOL (WINAPI *io24_proto_overlapped)(WINUSB_INTERFACE_HANDLE, LPOVERLAPPED, LPDWORD, BOOL);
typedef BOOL (WINAPI *io24_proto_get_policy)(WINUSB_INTERFACE_HANDLE, UCHAR, ULONG, PULONG, PVOID);
typedef BOOL (WINAPI *io24_proto_initialize)(HANDLE, PWINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *io24_proto_query)(WINUSB_INTERFACE_HANDLE, ULONG, PULONG, PVOID);
typedef BOOL (WINAPI *io24_proto_pipe_io)(WINUSB_INTERFACE_HANDLE, UCHAR, PUCHAR, ULONG, PULONG, LPOVERLAPPED);
typedef BOOL (WINAPI *io24_proto_reset)(WINUSB_INTERFACE_HANDLE, UCHAR);
typedef BOOL (WINAPI *io24_proto_alternate)(WINUSB_INTERFACE_HANDLE, UCHAR);
typedef BOOL (WINAPI *io24_proto_set_policy)(WINUSB_INTERFACE_HANDLE, UCHAR, ULONG, ULONG, PVOID);
#define IO24_ASSERT_PROTOTYPE(name, type) _Static_assert(_Generic(&name, type: 1, default: 0), #name " prototype")
IO24_ASSERT_PROTOTYPE(WinUsb_AbortPipe, io24_proto_abort);
IO24_ASSERT_PROTOTYPE(WinUsb_ControlTransfer, io24_proto_control);
IO24_ASSERT_PROTOTYPE(WinUsb_Free, io24_proto_free);
IO24_ASSERT_PROTOTYPE(WinUsb_GetAssociatedInterface, io24_proto_associated);
IO24_ASSERT_PROTOTYPE(WinUsb_GetDescriptor, io24_proto_descriptor);
IO24_ASSERT_PROTOTYPE(WinUsb_GetOverlappedResult, io24_proto_overlapped);
IO24_ASSERT_PROTOTYPE(WinUsb_GetPipePolicy, io24_proto_get_policy);
IO24_ASSERT_PROTOTYPE(WinUsb_Initialize, io24_proto_initialize);
IO24_ASSERT_PROTOTYPE(WinUsb_QueryDeviceInformation, io24_proto_query);
IO24_ASSERT_PROTOTYPE(WinUsb_ReadPipe, io24_proto_pipe_io);
IO24_ASSERT_PROTOTYPE(WinUsb_ResetPipe, io24_proto_reset);
IO24_ASSERT_PROTOTYPE(WinUsb_SetCurrentAlternateSetting, io24_proto_alternate);
IO24_ASSERT_PROTOTYPE(WinUsb_SetPipePolicy, io24_proto_set_policy);
IO24_ASSERT_PROTOTYPE(WinUsb_WritePipe, io24_proto_pipe_io);

#define GUARD_BYTE 0xa5
#define IO24_FILE_HANDLE ((HANDLE)(uintptr_t)0x1110)
#ifndef FILE_DEVICE_UNKNOWN
#define FILE_DEVICE_UNKNOWN 0x22
#endif
#define IO24_CTL_CODE(type,function,method,access) (((type)<<16)|((access)<<14)|((function)<<2)|(method))
#define IO24_IOCTL_INITIALIZE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x800,2,0)
#define IO24_IOCTL_RELEASE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x801,0,0)
#define IO24_IOCTL_DESCRIPTOR IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x802,2,0)
#define IO24_IOCTL_SET_ALTERNATE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x803,0,0)
#define IO24_IOCTL_GET_POLICY IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x804,0,0)
#define IO24_IOCTL_SET_POLICY IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x805,0,0)
#define IO24_IOCTL_CONTROL_OUT IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x807,1,0)
#define IO24_IOCTL_READ_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x808,2,0)
#define IO24_IOCTL_WRITE_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x809,1,0)
#define IO24_IOCTL_ABORT_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x80a,0,0)
#define IO24_IOCTL_RESET_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x80b,0,0)
#define IO24_ABI_VERSION 1u
#define IO24_LENGTH_SENTINEL UINT32_C(0xd15c0ded)
#define IO24_VALUE_SENTINEL UINT32_C(0x6a5bc4d3)
#define IO24_GUARD_WORD UINT32_C(0xa5a5a5a5)
#define IO24_POLICY_RESPONSE_VALUE UINT32_C(0x13579bdf)
#define IO24_POLICY_RESPONSE_LENGTH 4u
#define IO24_POLICY_PROBE_CAPACITY 8u
#define IO24_VENDOR_POLICY_CAPACITY 4u
#define IO24_POLICY_STORAGE_SENTINEL UINT8_C(0x6d)
#define IO24_CONTROL_SYNC_LENGTH 5u
#define IO24_CONTROL_OVERLAPPED_LENGTH 7u
#define IO24_READ_SYNC_LENGTH 11u
#define IO24_READ_OVERLAPPED_LENGTH 13u
#define IO24_WRITE_SYNC_LENGTH 17u
#define IO24_WRITE_OVERLAPPED_LENGTH 19u
#define IO24_OVERLAPPED_RESULT_LENGTH 23u

/* Runtime requests use the production private ABI directly. */
#define io24_wire_header wine_winusb_request
#define io24_wire_descriptor wine_winusb_descriptor_request
#define io24_wire_policy wine_winusb_policy_request
#define io24_wire_alternate wine_winusb_alternate_request
#define io24_wire_pipe wine_winusb_pipe_request
#define io24_wire_control wine_winusb_control_request
struct io24_wire_snapshot
{
    struct wine_winusb_snapshot header;
    UINT8 descriptor_bytes[59];
};
union io24_wire_request
{
    struct io24_wire_header header;struct io24_wire_descriptor descriptor;struct io24_wire_policy policy;
    struct io24_wire_alternate alternate;struct io24_wire_pipe pipe;struct io24_wire_control control;
};
_Static_assert(sizeof(struct io24_wire_header)==24,"wire header size");
_Static_assert(sizeof(struct io24_wire_descriptor)==40,"descriptor request size");
_Static_assert(sizeof(struct io24_wire_policy)==40,"policy request size");
_Static_assert(sizeof(struct io24_wire_alternate)==32,"alternate request size");
_Static_assert(sizeof(struct io24_wire_pipe)==32,"pipe request size");
_Static_assert(sizeof(struct io24_wire_control)==40,"control request size");
_Static_assert(sizeof(struct io24_wire_snapshot)==136,"snapshot response capacity");
static const uint8_t io24_device_descriptor[18]={18,1,0,2,0,0,0,64,0x94,0x19,0x71,0x00,0,1,1,2,3,1};
static const uint8_t io24_mi05_configuration[41]={9,2,41,0,1,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,1,2,0xff,0,0,6,7,5,0x81,2,0,2,0,7,5,0x01,2,0,2,0};
static const uint8_t io24_string_descriptor_response[8]={8,3,'R',0,'4',0,'!',0};
static const uint8_t io24_read_response[IO24_READ_OVERLAPPED_LENGTH]={0x91,0x82,0x73,0x64,0x55,0x46,0x37,0x28,0x19,0xaa,0xbb,0xcc,0xdd};

struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)
enum fake_event_kind { EVENT_IOCTL, EVENT_ALLOC, EVENT_FREE, EVENT_CLOSE, EVENT_DUPLICATE, EVENT_OVERLAPPED };
struct fake_event
{
    enum fake_event_kind kind; BOOL result; HANDLE handle; DWORD code,in_length,out_length;
    void *overlapped,*pointer;DWORD *bytes_returned_pointer;union io24_wire_request request;BOOL typed_request;
    unsigned char output_before[160],output_after[160];unsigned int output_saved;DWORD returned_bytes;
};
struct io24_fake_win32
{
    DWORD last_error; BOOL ioctl_result,overlapped_result; DWORD ioctl_error;
    OVERLAPPED *caller_overlapped;
    struct fake_event events[128]; unsigned int event_count,duplicates,closes;
};
static struct io24_fake_win32 fake;

struct guarded_buffer { uint8_t before,bytes[32],after; };
struct guarded_ulong { uint32_t before;ULONG value;uint32_t after; };
struct guarded_policy_value { uint32_t before;uint8_t bytes[IO24_POLICY_PROBE_CAPACITY];uint32_t after; };
_Static_assert(sizeof(ULONG) == IO24_VENDOR_POLICY_CAPACITY, "vendor policy-8 input capacity");

static struct fake_event *record_event(enum fake_event_kind kind)
{
    struct fake_event *event;
    if(fake.event_count>=sizeof(fake.events)/sizeof(fake.events[0])){++counts.failures;return &fake.events[127];}
    event=&fake.events[fake.event_count++];memset(event,0,sizeof(*event));event->kind=kind;return event;
}
static void fake_reset(void)
{
    unsigned int failures=counts.failures;memset(&fake,0,sizeof(fake));memset(&counts,0,sizeof(counts));counts.failures=failures;
    fake.ioctl_result=TRUE;fake.overlapped_result=TRUE;
}
static BOOL bytes_equal(const uint8_t *bytes,size_t length,uint8_t value)
{size_t i;for(i=0;i<length;i++)if(bytes[i]!=value)return FALSE;return TRUE;}
static void guard_buffer_reset(struct guarded_buffer *buffer,uint8_t value)
{buffer->before=GUARD_BYTE;memset(buffer->bytes,value,sizeof(buffer->bytes));buffer->after=GUARD_BYTE;}
static void check_buffer_guards(const struct guarded_buffer *buffer)
{IO24_CHECK(buffer->before==GUARD_BYTE);IO24_CHECK(buffer->after==GUARD_BYTE);}
static DWORD transfer_response_length(DWORD code,const OVERLAPPED *overlapped)
{
    BOOL caller=fake.caller_overlapped&&overlapped==fake.caller_overlapped;
    switch(code)
    {
        case IO24_IOCTL_CONTROL_OUT:return caller?IO24_CONTROL_OVERLAPPED_LENGTH:IO24_CONTROL_SYNC_LENGTH;
        case IO24_IOCTL_READ_PIPE:return caller?IO24_READ_OVERLAPPED_LENGTH:IO24_READ_SYNC_LENGTH;
        case IO24_IOCTL_WRITE_PIPE:return caller?IO24_WRITE_OVERLAPPED_LENGTH:IO24_WRITE_SYNC_LENGTH;
    }
    return 0;
}
static unsigned int event_position(enum fake_event_kind kind,const void *pointer)
{
    unsigned int i;for(i=0;i<fake.event_count;i++)if(fake.events[i].kind==kind&&(!pointer||fake.events[i].pointer==pointer))return i;return ~0u;
}
static const struct fake_event *find_ioctl_after(unsigned int start,DWORD code)
{
    unsigned int i;for(i=start;i<fake.event_count;i++)if(fake.events[i].kind==EVENT_IOCTL&&fake.events[i].code==code)return &fake.events[i];return NULL;
}
static size_t request_size_for_code(DWORD code)
{
    switch(code)
    {
        case IO24_IOCTL_INITIALIZE:case IO24_IOCTL_RELEASE:return sizeof(struct io24_wire_header);
        case IO24_IOCTL_DESCRIPTOR:return sizeof(struct io24_wire_descriptor);
        case IO24_IOCTL_GET_POLICY:case IO24_IOCTL_SET_POLICY:return sizeof(struct io24_wire_policy);
        case IO24_IOCTL_SET_ALTERNATE:return sizeof(struct io24_wire_alternate);
        case IO24_IOCTL_CONTROL_OUT:return sizeof(struct io24_wire_control);
        case IO24_IOCTL_READ_PIPE:case IO24_IOCTL_WRITE_PIPE:case IO24_IOCTL_ABORT_PIPE:case IO24_IOCTL_RESET_PIPE:return sizeof(struct io24_wire_pipe);
    }
    return 0;
}
static void check_header(const struct fake_event *event,size_t size,uint64_t session,uint32_t interface_index)
{IO24_CHECK(event->typed_request);IO24_CHECK(event->in_length==size);IO24_CHECK(event->request.header.size==size);IO24_CHECK(event->request.header.version==IO24_ABI_VERSION);IO24_CHECK(event->request.header.session==session);IO24_CHECK(event->request.header.interface_index==interface_index);IO24_CHECK(event->request.header.reserved==0);}

int __cdecl __wine_dbg_header(enum __wine_debug_class c,struct __wine_debug_channel*d,const char*f){(void)c;(void)d;(void)f;return -1;}
int __cdecl __wine_dbg_output(const char*s){(void)s;return 0;}
const char *__cdecl __wine_dbg_strdup(const char*s){return s;}
LPVOID WINAPI HeapAlloc(HANDLE h,DWORD f,SIZE_T n){void*p;struct fake_event*e;(void)h;(void)f;p=calloc(1,n?n:1);e=record_event(EVENT_ALLOC);e->pointer=p;e->out_length=n;if(p)counts.allocations++;return p;}
BOOL WINAPI HeapFree(HANDLE h,DWORD f,LPVOID p){struct fake_event*e;(void)h;(void)f;e=record_event(EVENT_FREE);e->pointer=p;e->result=TRUE;if(p){counts.frees++;free(p);}return TRUE;}
HANDLE WINAPI CreateEventW(SECURITY_ATTRIBUTES*a,BOOL manual,BOOL initial,LPCWSTR name){struct fake_event*e;(void)a;(void)manual;(void)initial;(void)name;e=record_event(EVENT_ALLOC);e->pointer=(void*)(uintptr_t)(0xe000+fake.event_count);return e->pointer;}
DWORD WINAPI WaitForSingleObject(HANDLE h,DWORD timeout){(void)h;(void)timeout;return WAIT_OBJECT_0;}
BOOL WINAPI CloseHandle(HANDLE h){struct fake_event*e=record_event(EVENT_CLOSE);e->handle=h;e->result=TRUE;fake.closes++;counts.releases++;return TRUE;}
BOOL WINAPI DuplicateHandle(HANDLE a,HANDLE source,HANDLE b,HANDLE *target,DWORD c,BOOL d,DWORD flags)
{struct fake_event*e;(void)a;(void)b;(void)c;(void)d;(void)flags;e=record_event(EVENT_DUPLICATE);e->handle=source;e->result=TRUE;fake.duplicates++;if(target)*target=(HANDLE)((uintptr_t)source+0x100);e->pointer=target?*target:NULL;return TRUE;}
BOOL WINAPI DeviceIoControl(HANDLE device,DWORD code,void*in,DWORD in_length,void*out,DWORD out_length,DWORD*bytes,OVERLAPPED*ov)
{
    struct fake_event*e=record_event(EVENT_IOCTL);size_t expected=request_size_for_code(code),saved=out_length;DWORD transfer_length;e->handle=device;e->code=code;e->in_length=in_length;e->out_length=out_length;e->overlapped=ov;e->bytes_returned_pointer=bytes;e->result=fake.ioctl_result;
    if(in&&expected&&in_length==expected){memcpy(&e->request,in,expected);e->typed_request=TRUE;}
    if(saved>sizeof(e->output_before))saved=sizeof(e->output_before);
    if(out&&saved)memcpy(e->output_before,out,saved);
    e->output_saved=saved;counts.submits++;
    e->returned_bytes=0;
    if(out&&out_length&&e->typed_request)
    {
        if(code==IO24_IOCTL_INITIALIZE&&out_length>=sizeof(struct io24_wire_snapshot)&&e->typed_request){struct io24_wire_snapshot snapshot;memset(&snapshot,0,sizeof(snapshot));snapshot.header.size=sizeof(snapshot.header);snapshot.header.version=IO24_ABI_VERSION;snapshot.header.session=UINT64_C(0x1122334455667788);snapshot.header.total_size=offsetof(struct io24_wire_snapshot,descriptor_bytes)+sizeof(snapshot.descriptor_bytes);snapshot.header.speed=3;snapshot.header.device_offset=offsetof(struct io24_wire_snapshot,descriptor_bytes);snapshot.header.device_length=sizeof(io24_device_descriptor);snapshot.header.configuration_offset=snapshot.header.device_offset+snapshot.header.device_length;snapshot.header.configuration_length=sizeof(io24_mi05_configuration);snapshot.header.interface_count=1;memcpy(snapshot.descriptor_bytes,io24_device_descriptor,sizeof(io24_device_descriptor));memcpy(snapshot.descriptor_bytes+sizeof(io24_device_descriptor),io24_mi05_configuration,sizeof(io24_mi05_configuration));memcpy(out,&snapshot,sizeof(snapshot));e->returned_bytes=snapshot.header.total_size;}
        if(code==IO24_IOCTL_DESCRIPTOR&&out_length>=sizeof(io24_string_descriptor_response)){memcpy(out,io24_string_descriptor_response,sizeof(io24_string_descriptor_response));e->returned_bytes=sizeof(io24_string_descriptor_response);}
        if(code==IO24_IOCTL_GET_POLICY&&out_length>=sizeof(struct io24_wire_policy)){struct io24_wire_policy response=e->request.policy;response.value_length=IO24_POLICY_RESPONSE_LENGTH;response.value=IO24_POLICY_RESPONSE_VALUE;memcpy(out,&response,sizeof(response));e->returned_bytes=sizeof(response);}
        transfer_length=transfer_response_length(code,ov);
        if(transfer_length&&out_length>=transfer_length)
        {
            if(code==IO24_IOCTL_READ_PIPE)memcpy(out,io24_read_response,transfer_length);
            e->returned_bytes=transfer_length;
        }
    }
    if(out&&saved)memcpy(e->output_after,out,saved);
    if(bytes)*bytes=e->returned_bytes;
    if(!fake.ioctl_result)fake.last_error=fake.ioctl_error;
    return fake.ioctl_result;
}
BOOL WINAPI GetOverlappedResult(HANDLE h,OVERLAPPED*ov,DWORD*b,BOOL wait)
{struct fake_event*e=record_event(EVENT_OVERLAPPED);e->handle=h;e->overlapped=ov;e->in_length=wait;e->result=fake.overlapped_result;e->returned_bytes=IO24_OVERLAPPED_RESULT_LENGTH;counts.completions++;if(b)*b=e->returned_bytes;return fake.overlapped_result;}

typedef BOOL (WINAPI *fn_abort)(WINUSB_INTERFACE_HANDLE,UCHAR);
typedef BOOL (WINAPI *fn_control)(WINUSB_INTERFACE_HANDLE,WINUSB_SETUP_PACKET,UCHAR*,ULONG,ULONG*,OVERLAPPED*);
typedef BOOL (WINAPI *fn_free)(WINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *fn_associated)(WINUSB_INTERFACE_HANDLE,UCHAR,PWINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *fn_descriptor)(WINUSB_INTERFACE_HANDLE,UCHAR,UCHAR,USHORT,UCHAR*,ULONG,ULONG*);
typedef BOOL (WINAPI *fn_overlapped)(WINUSB_INTERFACE_HANDLE,OVERLAPPED*,ULONG*,BOOL);
typedef BOOL (WINAPI *fn_get_policy)(WINUSB_INTERFACE_HANDLE,UCHAR,ULONG,ULONG*,void*);
typedef BOOL (WINAPI *fn_initialize)(HANDLE,PWINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *fn_query)(WINUSB_INTERFACE_HANDLE,ULONG,ULONG*,void*);
typedef BOOL (WINAPI *fn_pipe_io)(WINUSB_INTERFACE_HANDLE,UCHAR,UCHAR*,ULONG,ULONG*,OVERLAPPED*);
typedef BOOL (WINAPI *fn_reset)(WINUSB_INTERFACE_HANDLE,UCHAR);
typedef BOOL (WINAPI *fn_alt)(WINUSB_INTERFACE_HANDLE,UCHAR);
typedef BOOL (WINAPI *fn_set_policy)(WINUSB_INTERFACE_HANDLE,UCHAR,ULONG,ULONG,void*);
enum symbol_bit
{
    SYMBOL_ABORT=1u<<0,SYMBOL_CONTROL=1u<<1,SYMBOL_FREE=1u<<2,SYMBOL_ASSOCIATED=1u<<3,
    SYMBOL_DESCRIPTOR=1u<<4,SYMBOL_OVERLAPPED=1u<<5,SYMBOL_GET_POLICY=1u<<6,SYMBOL_INITIALIZE=1u<<7,
    SYMBOL_QUERY=1u<<8,SYMBOL_READ=1u<<9,SYMBOL_RESET=1u<<10,SYMBOL_ALTERNATE=1u<<11,
    SYMBOL_SET_POLICY=1u<<12,SYMBOL_WRITE=1u<<13,SYMBOL_ALL=(1u<<14)-1
};
struct functions { fn_abort abort_pipe;fn_control control;fn_free free_handle;fn_associated associated;fn_descriptor descriptor;fn_overlapped overlapped;fn_get_policy get_policy;fn_initialize initialize;fn_query query;fn_pipe_io read_pipe;fn_reset reset_pipe;fn_alt set_alt;fn_set_policy set_policy;fn_pipe_io write_pipe;uint32_t present_mask; };
static void *feature_symbol(void*m,const char*n){return dlsym(m,n);}
#define LOAD(field,name) *(void **)&f->field=feature_symbol(module,name)
static void load_functions(void*module,struct functions*f)
{memset(f,0,sizeof(*f));LOAD(abort_pipe,"WinUsb_AbortPipe");LOAD(control,"WinUsb_ControlTransfer");LOAD(free_handle,"WinUsb_Free");LOAD(associated,"WinUsb_GetAssociatedInterface");LOAD(descriptor,"WinUsb_GetDescriptor");LOAD(overlapped,"WinUsb_GetOverlappedResult");LOAD(get_policy,"WinUsb_GetPipePolicy");LOAD(initialize,"WinUsb_Initialize");LOAD(query,"WinUsb_QueryDeviceInformation");LOAD(read_pipe,"WinUsb_ReadPipe");LOAD(reset_pipe,"WinUsb_ResetPipe");LOAD(set_alt,"WinUsb_SetCurrentAlternateSetting");LOAD(set_policy,"WinUsb_SetPipePolicy");LOAD(write_pipe,"WinUsb_WritePipe");
if(f->abort_pipe)f->present_mask|=SYMBOL_ABORT;
if(f->control)f->present_mask|=SYMBOL_CONTROL;
if(f->free_handle)f->present_mask|=SYMBOL_FREE;
if(f->associated)f->present_mask|=SYMBOL_ASSOCIATED;
if(f->descriptor)f->present_mask|=SYMBOL_DESCRIPTOR;
if(f->overlapped)f->present_mask|=SYMBOL_OVERLAPPED;
if(f->get_policy)f->present_mask|=SYMBOL_GET_POLICY;
if(f->initialize)f->present_mask|=SYMBOL_INITIALIZE;
if(f->query)f->present_mask|=SYMBOL_QUERY;
if(f->read_pipe)f->present_mask|=SYMBOL_READ;
if(f->reset_pipe)f->present_mask|=SYMBOL_RESET;
if(f->set_alt)f->present_mask|=SYMBOL_ALTERNATE;
if(f->set_policy)f->present_mask|=SYMBOL_SET_POLICY;
if(f->write_pipe)f->present_mask|=SYMBOL_WRITE;}
static uint32_t target_mask(const char *mode)
{
    if(!strcmp(mode,"--initialize"))return SYMBOL_INITIALIZE;
    if(!strcmp(mode,"--handles"))return SYMBOL_INITIALIZE|SYMBOL_ASSOCIATED|SYMBOL_FREE;
    if(!strcmp(mode,"--descriptors"))return SYMBOL_INITIALIZE|SYMBOL_DESCRIPTOR|SYMBOL_QUERY;
    if(!strcmp(mode,"--policy"))return SYMBOL_INITIALIZE|SYMBOL_GET_POLICY|SYMBOL_SET_POLICY|SYMBOL_ALTERNATE;
    if(!strcmp(mode,"--transfer"))return SYMBOL_INITIALIZE|SYMBOL_CONTROL|SYMBOL_READ|SYMBOL_WRITE|SYMBOL_OVERLAPPED;
    if(!strcmp(mode,"--cancel"))return SYMBOL_INITIALIZE|SYMBOL_ABORT|SYMBOL_RESET;
    return SYMBOL_ALL;
}
static void check_target_symbols(const struct functions *f,uint32_t target)
{uint32_t missing=target&~f->present_mask,bit;for(bit=1;bit<=SYMBOL_WRITE;bit<<=1)if(missing&bit)++counts.failures;if((target&SYMBOL_FREE)&&f->free_handle)IO24_CHECK(!f->free_handle(NULL));}

static BOOL initialize_handle(const struct functions*f,WINUSB_INTERFACE_HANDLE *handle)
{
    unsigned int submits=counts.submits,events=fake.event_count;BOOL ok;*handle=NULL;
    if(!f->initialize){IO24_CHECK(FALSE);return FALSE;}ok=f->initialize(IO24_FILE_HANDLE,handle);
    IO24_CHECK(ok&&*handle);IO24_CHECK(counts.submits==submits+1);IO24_CHECK(fake.event_count>events);
    if(fake.event_count>events){struct fake_event*e=&fake.events[events];IO24_CHECK(e->kind==EVENT_IOCTL&&e->code==IO24_IOCTL_INITIALIZE&&e->handle==IO24_FILE_HANDLE&&e->overlapped!=NULL&&e->result);}
    return ok&&*handle;
}
static void test_initialize(const struct functions*f){WINUSB_INTERFACE_HANDLE h;fake_reset();if(initialize_handle(f,&h)&&f->free_handle)IO24_CHECK(f->free_handle(h));}
static void test_handles(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE root,associated=NULL;unsigned int frees_before,assoc_pos,root_pos;fake_reset();if(!initialize_handle(f,&root))return;frees_before=counts.frees;
    IO24_CHECK(f->associated&&f->associated(root,0,&associated)&&associated&&associated!=root);if(!associated){if(f->free_handle)f->free_handle(root);return;}
    IO24_CHECK(f->free_handle&&f->free_handle(associated));IO24_CHECK(f->free_handle&&f->free_handle(root));assoc_pos=event_position(EVENT_FREE,associated);root_pos=event_position(EVENT_FREE,root);
    IO24_CHECK(assoc_pos!=~0u&&root_pos!=~0u&&assoc_pos<root_pos);IO24_CHECK(counts.frees>=frees_before+2);IO24_CHECK(fake.closes==0);
}
static void test_descriptors(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE h;struct guarded_buffer g;uint8_t speed[4];ULONG n,sl;unsigned int submits;BOOL ok;fake_reset();if(!initialize_handle(f,&h))return;submits=counts.submits;
    memset(speed,0x6d,sizeof(speed));sl=sizeof(speed);ok=f->query&&f->query(h,1,&sl,speed);IO24_CHECK(ok);IO24_CHECK(sl==1);IO24_CHECK(speed[0]==3&&bytes_equal(speed+1,3,0x6d));
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->descriptor&&f->descriptor(h,1,0,0,g.bytes,sizeof(g.bytes),&n);IO24_CHECK(ok);IO24_CHECK(n==sizeof(io24_device_descriptor));IO24_CHECK(!memcmp(g.bytes,io24_device_descriptor,sizeof(io24_device_descriptor)));IO24_CHECK(bytes_equal(g.bytes+sizeof(io24_device_descriptor),sizeof(g.bytes)-sizeof(io24_device_descriptor),GUARD_BYTE));check_buffer_guards(&g);
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->descriptor&&f->descriptor(h,3,1,0x409,g.bytes,sizeof(g.bytes),&n);IO24_CHECK(ok);IO24_CHECK(n==sizeof(io24_string_descriptor_response));IO24_CHECK(!memcmp(g.bytes,io24_string_descriptor_response,sizeof(io24_string_descriptor_response)));IO24_CHECK(bytes_equal(g.bytes+sizeof(io24_string_descriptor_response),sizeof(g.bytes)-sizeof(io24_string_descriptor_response),GUARD_BYTE));check_buffer_guards(&g);
    IO24_CHECK(counts.submits==submits+1);if(f->free_handle)f->free_handle(h);
}
static void test_policy(const struct functions*f)
{
    static const struct{UCHAR pipe,policy;ULONG length,value;}q[]={{0,3,1,0},{0,9,1,0},{1,1,1,0},{0x81,2,1,0},{0x81,4,1,0},{0x81,5,1,0},{0x81,6,1,0},{0x81,7,1,1}};WINUSB_INTERFACE_HANDLE h;struct guarded_policy_value v;struct io24_wire_policy response;const struct fake_event *event;uint32_t actual;unsigned int i,submits,event_start;ULONG n;BOOL ok;
    fake_reset();if(!initialize_handle(f,&h))return;submits=counts.submits;for(i=0;i<sizeof(q)/sizeof(q[0]);i++)IO24_CHECK(f->set_policy&&f->set_policy(h,q[i].pipe,q[i].policy,q[i].length,(void*)&q[i].value));
    v.before=IO24_GUARD_WORD;memset(v.bytes,IO24_POLICY_STORAGE_SENTINEL,sizeof(v.bytes));v.after=IO24_GUARD_WORD;n=sizeof(v.bytes);event_start=fake.event_count;ok=f->get_policy&&f->get_policy(h,0x81,8,&n,v.bytes);IO24_CHECK(ok);memcpy(&actual,v.bytes,sizeof(actual));IO24_CHECK(actual==IO24_POLICY_RESPONSE_VALUE);IO24_CHECK(n==IO24_POLICY_RESPONSE_LENGTH);IO24_CHECK(bytes_equal(v.bytes+sizeof(actual),sizeof(v.bytes)-sizeof(actual),IO24_POLICY_STORAGE_SENTINEL));IO24_CHECK(v.before==IO24_GUARD_WORD&&v.after==IO24_GUARD_WORD);
    event=find_ioctl_after(event_start,IO24_IOCTL_GET_POLICY);IO24_CHECK(event!=NULL);if(event){check_header(event,sizeof(struct io24_wire_policy),UINT64_C(0x1122334455667788),0);IO24_CHECK(event->bytes_returned_pointer!=&n);IO24_CHECK(event->request.policy.pipe_id==0x81&&event->request.policy.policy_id==8&&event->request.policy.value_length==IO24_POLICY_PROBE_CAPACITY&&event->request.policy.value==0);IO24_CHECK(event->out_length==sizeof(response)&&event->output_saved>=sizeof(response)&&event->returned_bytes==sizeof(response));if(event->output_saved>=sizeof(response)){memcpy(&response,event->output_after,sizeof(response));IO24_CHECK(response.request.size==sizeof(response)&&response.request.version==IO24_ABI_VERSION&&response.request.session==UINT64_C(0x1122334455667788)&&response.request.interface_index==0&&response.request.reserved==0);IO24_CHECK(response.pipe_id==0x81&&response.policy_id==8&&response.value_length==IO24_POLICY_RESPONSE_LENGTH&&response.value==IO24_POLICY_RESPONSE_VALUE);}}
    IO24_CHECK(f->set_alt&&f->set_alt(h,1));IO24_CHECK(counts.submits==submits+10);if(f->free_handle)f->free_handle(h);
}
static void test_transfer(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE h;struct guarded_buffer g;ULONG n;OVERLAPPED ov={0};WINUSB_SETUP_PACKET setup={0x41,1,2,5,32};unsigned int submits,completions;BOOL ok;
    fake_reset();if(!initialize_handle(f,&h))return;fake.caller_overlapped=&ov;submits=counts.submits;completions=counts.completions;
    guard_buffer_reset(&g,0x4a);n=IO24_LENGTH_SENTINEL;ok=f->control&&f->control(h,setup,g.bytes,sizeof(g.bytes),&n,NULL);IO24_CHECK(ok);IO24_CHECK(n==IO24_CONTROL_SYNC_LENGTH);IO24_CHECK(bytes_equal(g.bytes,sizeof(g.bytes),0x4a));check_buffer_guards(&g);
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->read_pipe&&f->read_pipe(h,0x81,g.bytes,sizeof(g.bytes),&n,&ov);IO24_CHECK(ok);IO24_CHECK(n==IO24_READ_OVERLAPPED_LENGTH);IO24_CHECK(!memcmp(g.bytes,io24_read_response,IO24_READ_OVERLAPPED_LENGTH));IO24_CHECK(bytes_equal(g.bytes+IO24_READ_OVERLAPPED_LENGTH,sizeof(g.bytes)-IO24_READ_OVERLAPPED_LENGTH,GUARD_BYTE));check_buffer_guards(&g);
    guard_buffer_reset(&g,0x6c);n=IO24_LENGTH_SENTINEL;ok=f->write_pipe&&f->write_pipe(h,1,g.bytes,sizeof(g.bytes),&n,NULL);IO24_CHECK(ok);IO24_CHECK(n==IO24_WRITE_SYNC_LENGTH);IO24_CHECK(bytes_equal(g.bytes,sizeof(g.bytes),0x6c));check_buffer_guards(&g);
    n=IO24_LENGTH_SENTINEL;ok=f->overlapped&&f->overlapped(h,&ov,&n,TRUE);IO24_CHECK(ok);IO24_CHECK(n==IO24_OVERLAPPED_RESULT_LENGTH);
    IO24_CHECK(counts.submits==submits+3&&counts.completions==completions+1);if(f->free_handle)f->free_handle(h);
}
static void test_cancel(const struct functions*f)
{WINUSB_INTERFACE_HANDLE h;unsigned int submits;fake_reset();if(!initialize_handle(f,&h))return;submits=counts.submits;IO24_CHECK(f->abort_pipe&&f->abort_pipe(h,0x81));IO24_CHECK(f->reset_pipe&&f->reset_pipe(h,0x81));IO24_CHECK(counts.submits==submits+2);if(f->free_handle)f->free_handle(h);}

static void validate_vendor_fake_trace(WINUSB_INTERFACE_HANDLE root,WINUSB_INTERFACE_HANDLE associated,OVERLAPPED *caller)
{
    static const DWORD expected[]={IO24_IOCTL_INITIALIZE,IO24_IOCTL_DESCRIPTOR,IO24_IOCTL_GET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_ALTERNATE,IO24_IOCTL_CONTROL_OUT,IO24_IOCTL_CONTROL_OUT,IO24_IOCTL_READ_PIPE,IO24_IOCTL_READ_PIPE,IO24_IOCTL_WRITE_PIPE,IO24_IOCTL_WRITE_PIPE,IO24_IOCTL_ABORT_PIPE,IO24_IOCTL_RESET_PIPE,IO24_IOCTL_RELEASE};
    static const uint32_t policy[]={3,9,1,2,4,5,6,7};static const uint32_t pipe[]={0,0,1,0x81,0x81,0x81,0x81,0x81};static const uint32_t value[]={0,0,0,0,0,0,0,1};
    static const uint8_t setup[8]={0x41,1,2,0,5,0,32,0};const struct fake_event *ioctls[32];struct io24_wire_policy policy_result;struct io24_wire_snapshot snapshot;unsigned int i,n=0,assoc_pos,root_pos,overlapped_pos;uint64_t session;
    for(i=0;i<fake.event_count;i++) if(fake.events[i].kind==EVENT_IOCTL&&n<32) ioctls[n++]=&fake.events[i];
    IO24_CHECK(n==sizeof(expected)/sizeof(expected[0]));
    for(i=0;i<n&&i<sizeof(expected)/sizeof(expected[0]);i++){IO24_CHECK(ioctls[i]->code==expected[i]);IO24_CHECK(ioctls[i]->handle==IO24_FILE_HANDLE);IO24_CHECK(ioctls[i]->result);}
    if(n>=21){
        check_header(ioctls[0],sizeof(struct io24_wire_header),0,0);IO24_CHECK(ioctls[0]->out_length==sizeof(snapshot)&&ioctls[0]->output_saved>=sizeof(snapshot));memset(&snapshot,0,sizeof(snapshot));if(ioctls[0]->output_saved>=sizeof(snapshot))memcpy(&snapshot,ioctls[0]->output_after,sizeof(snapshot));IO24_CHECK(snapshot.header.size==sizeof(snapshot.header)&&snapshot.header.version==IO24_ABI_VERSION&&snapshot.header.session==UINT64_C(0x1122334455667788));IO24_CHECK(snapshot.header.total_size==offsetof(struct io24_wire_snapshot,descriptor_bytes)+59&&ioctls[0]->returned_bytes==snapshot.header.total_size&&snapshot.header.speed==3&&snapshot.header.device_offset==offsetof(struct io24_wire_snapshot,descriptor_bytes)&&snapshot.header.device_length==18&&snapshot.header.configuration_offset==snapshot.header.device_offset+18&&snapshot.header.configuration_length==41&&snapshot.header.interface_count==1);IO24_CHECK(!memcmp(snapshot.descriptor_bytes,io24_device_descriptor,18)&&!memcmp(snapshot.descriptor_bytes+18,io24_mi05_configuration,41));session=ioctls[1]->request.header.session;IO24_CHECK(session==snapshot.header.session);
        check_header(ioctls[1],sizeof(struct io24_wire_descriptor),session,0);IO24_CHECK(ioctls[1]->request.descriptor.type==3&&ioctls[1]->request.descriptor.index==1&&ioctls[1]->request.descriptor.language==0x409&&ioctls[1]->request.descriptor.length==32);IO24_CHECK(ioctls[1]->out_length==32&&ioctls[1]->returned_bytes==sizeof(io24_string_descriptor_response)&&ioctls[1]->output_before[0]==GUARD_BYTE);IO24_CHECK(ioctls[1]->output_saved>=sizeof(io24_string_descriptor_response)&&!memcmp(ioctls[1]->output_after,io24_string_descriptor_response,sizeof(io24_string_descriptor_response)));
        check_header(ioctls[2],sizeof(struct io24_wire_policy),session,0);IO24_CHECK(ioctls[2]->request.policy.pipe_id==0x81&&ioctls[2]->request.policy.policy_id==8&&ioctls[2]->request.policy.value_length==IO24_VENDOR_POLICY_CAPACITY&&ioctls[2]->request.policy.value==0);IO24_CHECK(ioctls[2]->out_length==sizeof(policy_result)&&ioctls[2]->output_saved>=sizeof(policy_result)&&ioctls[2]->returned_bytes==sizeof(policy_result));if(ioctls[2]->output_saved>=sizeof(policy_result)){memcpy(&policy_result,ioctls[2]->output_after,sizeof(policy_result));IO24_CHECK(policy_result.request.size==sizeof(policy_result)&&policy_result.request.version==IO24_ABI_VERSION&&policy_result.request.session==session&&policy_result.request.interface_index==0&&policy_result.request.reserved==0);IO24_CHECK(policy_result.pipe_id==0x81&&policy_result.policy_id==8&&policy_result.value==IO24_POLICY_RESPONSE_VALUE&&policy_result.value_length==IO24_POLICY_RESPONSE_LENGTH);}
        for(i=0;i<8;i++){check_header(ioctls[3+i],sizeof(struct io24_wire_policy),session,0);IO24_CHECK(ioctls[3+i]->request.policy.pipe_id==pipe[i]&&ioctls[3+i]->request.policy.policy_id==policy[i]&&ioctls[3+i]->request.policy.value_length==1&&ioctls[3+i]->request.policy.value==value[i]);}
        check_header(ioctls[11],sizeof(struct io24_wire_alternate),session,0);IO24_CHECK(ioctls[11]->request.alternate.alternate_setting==1&&ioctls[11]->request.alternate.reserved==0);
        for(i=12;i<=13;i++){check_header(ioctls[i],sizeof(struct io24_wire_control),session,0);IO24_CHECK(!memcmp(ioctls[i]->request.control.setup,setup,sizeof(setup)));IO24_CHECK(ioctls[i]->request.control.transfer_length==32&&ioctls[i]->request.control.reserved==0&&ioctls[i]->out_length==32&&((ioctls[i]->code&3)==1));}IO24_CHECK(ioctls[12]->returned_bytes==IO24_CONTROL_SYNC_LENGTH&&ioctls[13]->returned_bytes==IO24_CONTROL_OVERLAPPED_LENGTH);
        for(i=14;i<=15;i++){check_header(ioctls[i],sizeof(struct io24_wire_pipe),session,0);IO24_CHECK(ioctls[i]->request.pipe.pipe_id==0x81&&ioctls[i]->request.pipe.transfer_length==32&&ioctls[i]->out_length==32&&((ioctls[i]->code&3)==2));}IO24_CHECK(ioctls[14]->returned_bytes==IO24_READ_SYNC_LENGTH&&ioctls[15]->returned_bytes==IO24_READ_OVERLAPPED_LENGTH);IO24_CHECK(!memcmp(ioctls[14]->output_after,io24_read_response,IO24_READ_SYNC_LENGTH)&&!memcmp(ioctls[15]->output_after,io24_read_response,IO24_READ_OVERLAPPED_LENGTH));
        for(i=16;i<=17;i++){check_header(ioctls[i],sizeof(struct io24_wire_pipe),session,0);IO24_CHECK(ioctls[i]->request.pipe.pipe_id==1&&ioctls[i]->request.pipe.transfer_length==32&&ioctls[i]->out_length==32&&((ioctls[i]->code&3)==1));}IO24_CHECK(ioctls[16]->returned_bytes==IO24_WRITE_SYNC_LENGTH&&ioctls[17]->returned_bytes==IO24_WRITE_OVERLAPPED_LENGTH);
        check_header(ioctls[18],sizeof(struct io24_wire_pipe),session,0);IO24_CHECK(ioctls[18]->request.pipe.pipe_id==0x81&&ioctls[18]->request.pipe.transfer_length==0&&((ioctls[18]->code&3)==0));
        check_header(ioctls[19],sizeof(struct io24_wire_pipe),session,0);IO24_CHECK(ioctls[19]->request.pipe.pipe_id==0x81&&ioctls[19]->request.pipe.transfer_length==0&&((ioctls[19]->code&3)==0));
        check_header(ioctls[20],sizeof(struct io24_wire_header),session,0);IO24_CHECK((ioctls[20]->code&3)==0);
        IO24_CHECK(ioctls[13]->overlapped==caller&&ioctls[15]->overlapped==caller&&ioctls[17]->overlapped==caller);IO24_CHECK(ioctls[12]->overlapped&&ioctls[12]->overlapped!=caller&&ioctls[14]->overlapped&&ioctls[14]->overlapped!=caller&&ioctls[16]->overlapped&&ioctls[16]->overlapped!=caller);
    }
    overlapped_pos=event_position(EVENT_OVERLAPPED,NULL);IO24_CHECK(overlapped_pos!=~0u&&fake.events[overlapped_pos].handle==IO24_FILE_HANDLE&&fake.events[overlapped_pos].overlapped==caller&&fake.events[overlapped_pos].result&&fake.events[overlapped_pos].returned_bytes==IO24_OVERLAPPED_RESULT_LENGTH);
    assoc_pos=event_position(EVENT_FREE,associated);root_pos=event_position(EVENT_FREE,root);IO24_CHECK(assoc_pos!=~0u&&root_pos!=~0u&&assoc_pos<root_pos);IO24_CHECK(fake.closes==0);
}
static void test_vendor_sequence(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE root,associated=NULL;struct guarded_buffer g;struct guarded_ulong v;uint8_t speed[4];ULONG n,vl;OVERLAPPED ov={0};BOOL ok;unsigned int i;WINUSB_SETUP_PACKET setup={0x41,1,2,5,32};
    static const struct{UCHAR pipe,policy;ULONG length,value;}q[]={{0,3,1,0},{0,9,1,0},{1,1,1,0},{0x81,2,1,0},{0x81,4,1,0},{0x81,5,1,0},{0x81,6,1,0},{0x81,7,1,1}};
    fake_reset();if(!initialize_handle(f,&root))return;fake.caller_overlapped=&ov;
    memset(speed,0x6d,sizeof(speed));vl=sizeof(speed);ok=f->query&&f->query(root,1,&vl,speed);IO24_CHECK(ok);IO24_CHECK(vl==1);IO24_CHECK(speed[0]==3&&bytes_equal(speed+1,3,0x6d));
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->descriptor&&f->descriptor(root,1,0,0,g.bytes,sizeof(g.bytes),&n);IO24_CHECK(ok);IO24_CHECK(n==sizeof(io24_device_descriptor));IO24_CHECK(!memcmp(g.bytes,io24_device_descriptor,sizeof(io24_device_descriptor)));IO24_CHECK(bytes_equal(g.bytes+sizeof(io24_device_descriptor),sizeof(g.bytes)-sizeof(io24_device_descriptor),GUARD_BYTE));check_buffer_guards(&g);
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->descriptor&&f->descriptor(root,3,1,0x409,g.bytes,sizeof(g.bytes),&n);IO24_CHECK(ok);IO24_CHECK(n==sizeof(io24_string_descriptor_response));IO24_CHECK(!memcmp(g.bytes,io24_string_descriptor_response,sizeof(io24_string_descriptor_response)));IO24_CHECK(bytes_equal(g.bytes+sizeof(io24_string_descriptor_response),sizeof(g.bytes)-sizeof(io24_string_descriptor_response),GUARD_BYTE));check_buffer_guards(&g);
    v.before=IO24_GUARD_WORD;v.value=IO24_VALUE_SENTINEL;v.after=IO24_GUARD_WORD;vl=sizeof(v.value);ok=f->get_policy&&f->get_policy(root,0x81,8,&vl,&v.value);IO24_CHECK(ok);IO24_CHECK(v.value==IO24_POLICY_RESPONSE_VALUE);IO24_CHECK(vl==IO24_POLICY_RESPONSE_LENGTH);IO24_CHECK(v.before==IO24_GUARD_WORD&&v.after==IO24_GUARD_WORD);
    for(i=0;i<sizeof(q)/sizeof(q[0]);i++){ok=f->set_policy&&f->set_policy(root,q[i].pipe,q[i].policy,q[i].length,(void*)&q[i].value);IO24_CHECK(ok);}
    ok=f->set_alt&&f->set_alt(root,1);IO24_CHECK(ok);
    guard_buffer_reset(&g,0x4a);n=IO24_LENGTH_SENTINEL;ok=f->control&&f->control(root,setup,g.bytes,sizeof(g.bytes),&n,NULL);IO24_CHECK(ok);IO24_CHECK(n==IO24_CONTROL_SYNC_LENGTH);IO24_CHECK(bytes_equal(g.bytes,sizeof(g.bytes),0x4a));check_buffer_guards(&g);
    guard_buffer_reset(&g,0x4b);n=IO24_LENGTH_SENTINEL;ok=f->control&&f->control(root,setup,g.bytes,sizeof(g.bytes),&n,&ov);IO24_CHECK(ok);IO24_CHECK(n==IO24_CONTROL_OVERLAPPED_LENGTH);IO24_CHECK(bytes_equal(g.bytes,sizeof(g.bytes),0x4b));check_buffer_guards(&g);
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->read_pipe&&f->read_pipe(root,0x81,g.bytes,sizeof(g.bytes),&n,NULL);IO24_CHECK(ok);IO24_CHECK(n==IO24_READ_SYNC_LENGTH);IO24_CHECK(!memcmp(g.bytes,io24_read_response,IO24_READ_SYNC_LENGTH));IO24_CHECK(bytes_equal(g.bytes+IO24_READ_SYNC_LENGTH,sizeof(g.bytes)-IO24_READ_SYNC_LENGTH,GUARD_BYTE));check_buffer_guards(&g);
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->read_pipe&&f->read_pipe(root,0x81,g.bytes,sizeof(g.bytes),&n,&ov);IO24_CHECK(ok);IO24_CHECK(n==IO24_READ_OVERLAPPED_LENGTH);IO24_CHECK(!memcmp(g.bytes,io24_read_response,IO24_READ_OVERLAPPED_LENGTH));IO24_CHECK(bytes_equal(g.bytes+IO24_READ_OVERLAPPED_LENGTH,sizeof(g.bytes)-IO24_READ_OVERLAPPED_LENGTH,GUARD_BYTE));check_buffer_guards(&g);
    guard_buffer_reset(&g,0x6c);n=IO24_LENGTH_SENTINEL;ok=f->write_pipe&&f->write_pipe(root,1,g.bytes,sizeof(g.bytes),&n,NULL);IO24_CHECK(ok);IO24_CHECK(n==IO24_WRITE_SYNC_LENGTH);IO24_CHECK(bytes_equal(g.bytes,sizeof(g.bytes),0x6c));check_buffer_guards(&g);
    guard_buffer_reset(&g,0x6d);n=IO24_LENGTH_SENTINEL;ok=f->write_pipe&&f->write_pipe(root,1,g.bytes,sizeof(g.bytes),&n,&ov);IO24_CHECK(ok);IO24_CHECK(n==IO24_WRITE_OVERLAPPED_LENGTH);IO24_CHECK(bytes_equal(g.bytes,sizeof(g.bytes),0x6d));check_buffer_guards(&g);
    n=IO24_LENGTH_SENTINEL;ok=f->overlapped&&f->overlapped(root,&ov,&n,TRUE);IO24_CHECK(ok);IO24_CHECK(n==IO24_OVERLAPPED_RESULT_LENGTH);ok=f->abort_pipe&&f->abort_pipe(root,0x81);IO24_CHECK(ok);ok=f->reset_pipe&&f->reset_pipe(root,0x81);IO24_CHECK(ok);ok=f->associated&&f->associated(root,0,&associated);IO24_CHECK(ok&&associated&&associated!=root);if(!associated){if(f->free_handle)f->free_handle(root);return;}
    ok=f->free_handle&&f->free_handle(associated);IO24_CHECK(ok);ok=f->free_handle&&f->free_handle(root);IO24_CHECK(ok);check_buffer_guards(&g);validate_vendor_fake_trace(root,associated,&ov);
}
static void run_group(const char*m,const struct functions*f){if(!strcmp(m,"--vendor")){test_vendor_sequence(f);return;}if(!strcmp(m,"--red")||!strcmp(m,"--initialize"))test_initialize(f);if(!strcmp(m,"--red")||!strcmp(m,"--handles"))test_handles(f);if(!strcmp(m,"--red")||!strcmp(m,"--descriptors"))test_descriptors(f);if(!strcmp(m,"--red")||!strcmp(m,"--policy"))test_policy(f);if(!strcmp(m,"--red")||!strcmp(m,"--transfer"))test_transfer(f);if(!strcmp(m,"--red")||!strcmp(m,"--cancel"))test_cancel(f);if(!strcmp(m,"--red"))test_vendor_sequence(f);}
int main(int argc,char**argv){void*m;struct functions f;uint32_t target,missing;if(argc!=3)return 2;m=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!m){fprintf(stderr,"HARNESS: dlopen production module: %s\n",dlerror());return 2;}fake_reset();load_functions(m,&f);target=target_mask(argv[2]);missing=target&~f.present_mask;check_target_symbols(&f,target);run_group(argv[2],&f);dlclose(m);printf("CP33 public executed mode=%s target-mask=%#x present-mask=%#x missing-mask=%#x fake-events=%u submits=%u releases=%u completions=%u failures=%u\n",argv[2],target,f.present_mask,missing,fake.event_count,counts.submits,counts.releases,counts.completions,counts.failures);return counts.failures?1:0;}
