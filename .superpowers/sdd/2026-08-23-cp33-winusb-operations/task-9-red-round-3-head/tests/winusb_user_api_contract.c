/* Executed host contract for the actual winusb.dll production module. */
#include <dlfcn.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <threads.h>
#include <stdatomic.h>
#include <sys/wait.h>
#include <unistd.h>
#include "windef.h"
#include "winbase.h"
#include "winternl.h"
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
#define IO24_IOCTL_CONTROL_IN IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x806,2,0)
#define IO24_IOCTL_CONTROL_OUT IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x807,1,0)
#define IO24_IOCTL_READ_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x808,2,0)
#define IO24_IOCTL_WRITE_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x809,1,0)
#define IO24_IOCTL_ABORT_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x80a,0,0)
#define IO24_IOCTL_RESET_PIPE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x80b,0,0)
#define IO24_ABI_VERSION 1u
#define IO24_LENGTH_SENTINEL UINT32_C(0xd15c0ded)
#define IO24_VALUE_SENTINEL UINT32_C(0x6a5bc4d3)
#define IO24_GUARD_WORD UINT32_C(0xa5a5a5a5)
#define IO24_POLICY_RESPONSE_VALUE (4u * 1024u * 1024u)
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
    UINT8 bytes[256];
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
static const uint8_t io24_device_descriptor[18]={18,1,0,2,0,0,0,64,0x94,0x19,0x71,0x00,0,1,1,2,3,1};
static const uint8_t io24_mi05_configuration[41]={9,2,41,0,1,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,1,2,0xff,0,0,6,7,5,0x81,2,0,2,0,7,5,0x01,2,0,2,0};
static const uint8_t io24_low_configuration[25]={9,2,25,0,1,1,0,0x80,50,9,4,2,0,1,0xff,0,0,1,7,5,0x82,3,64,0,1};
static const uint8_t io24_descending_configuration[27]={9,2,27,0,2,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,2,0,0,0xff,0,0,6};
static const uint8_t io24_duplicate_interface_configuration[27]={9,2,27,0,2,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,0,0,0xff,0,0,6};
static const uint8_t io24_reuse_endpoint_configuration[41]={9,2,41,0,1,1,0,0x80,0xfa,9,4,5,0,1,0xff,0,0,6,7,5,0x81,2,0,2,0,9,4,5,1,1,0xff,0,0,6,7,5,0x81,2,0,2,0};
static const uint8_t io24_nonadjacent_duplicate_configuration[36]={9,2,36,0,3,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,2,0,0,0xff,0,0,6,9,4,5,0,0,0xff,0,0,6};
static const uint8_t io24_string_descriptor_response[8]={8,3,'R',0,'4',0,'!',0};
static const uint8_t io24_read_response[IO24_READ_OVERLAPPED_LENGTH]={0x91,0x82,0x73,0x64,0x55,0x46,0x37,0x28,0x19,0xaa,0xbb,0xcc,0xdd};

struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)
static atomic_int io24_leave_gate_enabled, io24_leave_gate_count, io24_leave_gate_target, io24_leave_gate_entered, io24_leave_gate_release;
static atomic_int io24_free_drain_entered, io24_free_done;
static atomic_int io24_policy_alt_gate_enabled, io24_policy_alt_gate_entered, io24_policy_alt_gate_release;
struct io24_fake_cs { CRITICAL_SECTION *object; mtx_t lock; };
struct io24_fake_cv { CONDITION_VARIABLE *object; cnd_t condition; };
static struct io24_fake_cs io24_fake_cs[16];
static struct io24_fake_cv io24_fake_cv[16];

static struct io24_fake_cs *io24_cs_slot(CRITICAL_SECTION *object)
{
    unsigned int i;
    for (i=0;i<sizeof(io24_fake_cs)/sizeof(io24_fake_cs[0]);++i)
        if (io24_fake_cs[i].object==object) return &io24_fake_cs[i];
    return NULL;
}
static struct io24_fake_cv *io24_cv_slot(CONDITION_VARIABLE *object)
{
    unsigned int i;
    for (i=0;i<sizeof(io24_fake_cv)/sizeof(io24_fake_cv[0]);++i)
        if (io24_fake_cv[i].object==object) return &io24_fake_cv[i];
    return NULL;
}
enum fake_event_kind { EVENT_IOCTL, EVENT_ALLOC, EVENT_FREE, EVENT_CLOSE, EVENT_DUPLICATE, EVENT_OVERLAPPED };
struct fake_event
{
    enum fake_event_kind kind; BOOL result; HANDLE handle; DWORD code,in_length,out_length,error;
    void *overlapped,*pointer;DWORD *bytes_returned_pointer;HANDLE private_event;union io24_wire_request request;BOOL typed_request;
    unsigned char output_before[512],output_after[512];unsigned int output_saved;DWORD returned_bytes;
};
struct io24_fake_win32
{
    DWORD last_error; BOOL ioctl_result,overlapped_result; DWORD ioctl_error,query_ok; ULONG mode; NTSTATUS query_iosb_status; ULONG_PTR query_information;
    struct { BOOL result,pending; DWORD error,bytes,completion_result,completion_error,completion_bytes; } private_call[8]; unsigned int private_call_count,private_call_index,active_private_call,release_ioctls,event_creates,event_closes,device_closes,alloc_fail_at,alloc_attempts; DWORD wait_result,wait_error;
    OVERLAPPED *caller_overlapped; HANDLE wait_handle; unsigned int snapshot_mutation,header_mutation,event_fail_at,fixture; BOOL low_speed_fixture,two_interface_fixture,three_interface_fixture,policy_associated_fixture;
    /* The policy reply is an ordinary private-ABI transport fixture.  It is
     * deliberately stateful so public readback assertions cannot pass on the
     * former unrelated constant response. */
    ULONG policy_value[2][10]; unsigned int policy_response_mutation; DWORD policy_response_bytes, policy_set_return_bytes;
    /* Task 9 public control/descriptor reply knobs live at the actual
     * DeviceIoControl boundary; they are not a replacement for production. */
    DWORD descriptor_response_length, control_response_length;
    BOOL descriptor_immediate_failure, control_immediate_failure;
    struct fake_event events[512]; unsigned int event_count,duplicates,closes;
};
static struct io24_fake_win32 fake;
enum io24_snapshot_mutation { SNAPSHOT_VALID, SNAPSHOT_BAD_VERSION, SNAPSHOT_BAD_TOTAL, SNAPSHOT_BAD_SPEED,
    SNAPSHOT_BAD_REGION, SNAPSHOT_BAD_CONFIGURATION, SNAPSHOT_BAD_INTERFACE, SNAPSHOT_BAD_ALTERNATE,
    SNAPSHOT_BAD_ENDPOINT, SNAPSHOT_BAD_RAW_ENDPOINT, SNAPSHOT_RAW_ALT_ORDER, SNAPSHOT_DUPLICATE_PIPE };
enum io24_policy_response_mutation { POLICY_RESPONSE_VALID, POLICY_RESPONSE_SHORT, POLICY_RESPONSE_LONG,
    POLICY_RESPONSE_SIZE, POLICY_RESPONSE_VERSION, POLICY_RESPONSE_SESSION, POLICY_RESPONSE_INTERFACE,
    POLICY_RESPONSE_RESERVED, POLICY_RESPONSE_PIPE, POLICY_RESPONSE_POLICY, POLICY_RESPONSE_LENGTH,
    POLICY_RESPONSE_BOOLEAN_VALUE };
enum io24_snapshot_fixture { SNAPSHOT_FIXTURE_MI05, SNAPSHOT_FIXTURE_DESCENDING,
    SNAPSHOT_FIXTURE_DUPLICATE_INTERFACE, SNAPSHOT_FIXTURE_CROSS_ALTERNATE_ENDPOINT_REUSE,
    SNAPSHOT_FIXTURE_NONADJACENT_DUPLICATE_INTERFACE };

struct guarded_buffer { uint8_t before,bytes[32],after; };
struct guarded_configuration_buffer { uint8_t before,bytes[64],after; };
struct guarded_ulong { uint32_t before;ULONG value;uint32_t after; };
struct guarded_policy_value { uint32_t before;uint8_t bytes[IO24_POLICY_PROBE_CAPACITY];uint32_t after; };
_Static_assert(sizeof(ULONG) == IO24_VENDOR_POLICY_CAPACITY, "vendor policy-8 input capacity");

static struct fake_event *record_event(enum fake_event_kind kind)
{
    struct fake_event *event;
    if(fake.event_count>=sizeof(fake.events)/sizeof(fake.events[0])){++counts.failures;return &fake.events[sizeof(fake.events)/sizeof(fake.events[0])-1];}
    event=&fake.events[fake.event_count++];memset(event,0,sizeof(*event));event->kind=kind;return event;
}
static void fake_policy_defaults(void)
{
    fake.policy_value[0][PIPE_TRANSFER_TIMEOUT]=fake.policy_value[1][PIPE_TRANSFER_TIMEOUT]=0;
    fake.policy_value[0][MAXIMUM_TRANSFER_SIZE]=fake.policy_value[1][MAXIMUM_TRANSFER_SIZE]=4u*1024u*1024u;
    fake.policy_value[0][RESET_PIPE_ON_RESUME]=fake.policy_value[1][RESET_PIPE_ON_RESUME]=0;
    fake.policy_value[0][SHORT_PACKET_TERMINATE]=0;
    fake.policy_value[1][AUTO_CLEAR_STALL]=fake.policy_value[1][IGNORE_SHORT_PACKETS]=0;
    fake.policy_value[1][ALLOW_PARTIAL_READS]=1;
    fake.policy_value[1][AUTO_FLUSH]=fake.policy_value[1][RAW_IO]=0;
}
static void fake_reset(void)
{
    unsigned int failures=counts.failures;memset(&fake,0,sizeof(fake));memset(&counts,0,sizeof(counts));counts.failures=failures;
    fake_policy_defaults();
    fake.ioctl_result=TRUE;fake.overlapped_result=TRUE;fake.query_ok=TRUE;fake.query_information=sizeof(FILE_MODE_INFORMATION);fake.wait_result=WAIT_OBJECT_0;fake.wait_error=ERROR_GEN_FAILURE;fake.active_private_call=~0u;
    atomic_store(&io24_leave_gate_enabled,0);atomic_store(&io24_leave_gate_count,0);atomic_store(&io24_leave_gate_target,0);atomic_store(&io24_leave_gate_entered,0);atomic_store(&io24_leave_gate_release,0);atomic_store(&io24_free_drain_entered,0);atomic_store(&io24_free_done,0);
    atomic_store(&io24_policy_alt_gate_enabled,0);atomic_store(&io24_policy_alt_gate_entered,0);atomic_store(&io24_policy_alt_gate_release,0);
}
static void mutate_snapshot(struct io24_wire_snapshot *snapshot)
{
    struct wine_winusb_interface_snapshot iface;
    struct wine_winusb_alternate_snapshot alternate;
    struct wine_winusb_endpoint_snapshot endpoint;

    if(fake.fixture==SNAPSHOT_FIXTURE_DESCENDING||fake.fixture==SNAPSHOT_FIXTURE_DUPLICATE_INTERFACE)
    {
        struct wine_winusb_interface_snapshot interfaces[2]={{5,0,1,0},{fake.fixture==SNAPSHOT_FIXTURE_DESCENDING?2:5,1,1,0}};
        struct wine_winusb_alternate_snapshot alternates[2]={{0,0,0,0},{1,0,0,0}};
        snapshot->header.total_size=181;snapshot->header.configuration_length=27;snapshot->header.interfaces_offset=117;
        snapshot->header.interface_count=2;snapshot->header.alternates_offset=149;snapshot->header.alternate_count=2;
        snapshot->header.endpoints_offset=181;snapshot->header.endpoint_count=0;
        memcpy(snapshot->bytes+18,fake.fixture==SNAPSHOT_FIXTURE_DESCENDING?io24_descending_configuration:io24_duplicate_interface_configuration,27);
        memcpy(snapshot->bytes+45,interfaces,sizeof(interfaces));memcpy(snapshot->bytes+77,alternates,sizeof(alternates));
    }
    else if(fake.fixture==SNAPSHOT_FIXTURE_CROSS_ALTERNATE_ENDPOINT_REUSE)
    {
        struct wine_winusb_alternate_snapshot alternates[2]={{0,0,0,1},{0,1,1,1}};
        struct wine_winusb_endpoint_snapshot endpoints[2]={{0,0x81,2,512},{1,0x81,2,512}};
        memcpy(snapshot->bytes+18,io24_reuse_endpoint_configuration,41);memcpy(snapshot->bytes+75,alternates,sizeof(alternates));
        memcpy(snapshot->bytes+107,endpoints,sizeof(endpoints));
    }
    switch(fake.snapshot_mutation)
    {
        case SNAPSHOT_BAD_VERSION: snapshot->header.version++; break;
        case SNAPSHOT_BAD_TOTAL: snapshot->header.total_size--; break;
        case SNAPSHOT_BAD_SPEED: snapshot->header.speed=FullSpeed; break;
        case SNAPSHOT_BAD_REGION: snapshot->header.alternates_offset--; break;
        case SNAPSHOT_BAD_CONFIGURATION: snapshot->bytes[20]++; break;
        case SNAPSHOT_BAD_INTERFACE: memcpy(&iface,snapshot->bytes+59,sizeof(iface));iface.reserved=1;memcpy(snapshot->bytes+59,&iface,sizeof(iface));break;
        case SNAPSHOT_BAD_ALTERNATE: memcpy(&alternate,snapshot->bytes+75,sizeof(alternate));alternate.alternate_setting=2;memcpy(snapshot->bytes+75,&alternate,sizeof(alternate));break;
        case SNAPSHOT_BAD_ENDPOINT: memcpy(&endpoint,snapshot->bytes+107,sizeof(endpoint));endpoint.maximum_packet_size=1;memcpy(snapshot->bytes+107,&endpoint,sizeof(endpoint));break;
        case SNAPSHOT_BAD_RAW_ENDPOINT: snapshot->bytes[48]=3; break;
        case SNAPSHOT_RAW_ALT_ORDER: snapshot->bytes[30]=1;snapshot->bytes[39]=0;break;
        case SNAPSHOT_DUPLICATE_PIPE: snapshot->bytes[54]=0x81;memcpy(&endpoint,snapshot->bytes+123,sizeof(endpoint));endpoint.pipe_id=0x81;memcpy(snapshot->bytes+123,&endpoint,sizeof(endpoint));break;
        default: break;
    }
}
static void mutate_header(struct io24_wire_snapshot *snapshot)
{
    switch(fake.header_mutation)
    {
        case 1: snapshot->header.size--; break;
        case 2: snapshot->header.version++; break;
        case 3: snapshot->header.session=1; break;
        case 4: snapshot->header.reserved[0]=1; break;
        case 5: snapshot->header.speed=FullSpeed; break;
        case 6: snapshot->header.total_size--; break;
        case 7: snapshot->header.device_offset++; break;
        case 8: snapshot->header.interface_count=0; break;
        case 9: snapshot->header.endpoint_count++; break;
        case 10: snapshot->header.total_size=65651;snapshot->header.configuration_length=9;snapshot->header.interfaces_offset=99;snapshot->header.interface_count=1;snapshot->header.alternates_offset=115;snapshot->header.alternate_count=1;snapshot->header.endpoints_offset=131;snapshot->header.endpoint_count=4095;break;
        default: break;
    }
}
static BOOL bytes_equal(const uint8_t *bytes,size_t length,uint8_t value)
{size_t i;for(i=0;i<length;i++)if(bytes[i]!=value)return FALSE;return TRUE;}
static void guard_buffer_reset(struct guarded_buffer *buffer,uint8_t value)
{buffer->before=GUARD_BYTE;memset(buffer->bytes,value,sizeof(buffer->bytes));buffer->after=GUARD_BYTE;}
static void check_buffer_guards(const struct guarded_buffer *buffer)
{IO24_CHECK(buffer->before==GUARD_BYTE);IO24_CHECK(buffer->after==GUARD_BYTE);}
static void guard_configuration_buffer_reset(struct guarded_configuration_buffer *buffer,uint8_t value)
{buffer->before=GUARD_BYTE;memset(buffer->bytes,value,sizeof(buffer->bytes));buffer->after=GUARD_BYTE;}
static void check_configuration_buffer_guards(const struct guarded_configuration_buffer *buffer)
{IO24_CHECK(buffer->before==GUARD_BYTE);IO24_CHECK(buffer->after==GUARD_BYTE);}
static DWORD transfer_response_length(DWORD code,const OVERLAPPED *overlapped)
{
    BOOL caller=fake.caller_overlapped&&overlapped==fake.caller_overlapped;
    switch(code)
    {
        case IO24_IOCTL_CONTROL_IN:case IO24_IOCTL_CONTROL_OUT:
            return fake.control_response_length ? fake.control_response_length :
                (caller?IO24_CONTROL_OVERLAPPED_LENGTH:IO24_CONTROL_SYNC_LENGTH);
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
        case IO24_IOCTL_CONTROL_IN:case IO24_IOCTL_CONTROL_OUT:return sizeof(struct io24_wire_control);
        case IO24_IOCTL_READ_PIPE:case IO24_IOCTL_WRITE_PIPE:case IO24_IOCTL_ABORT_PIPE:case IO24_IOCTL_RESET_PIPE:return sizeof(struct io24_wire_pipe);
    }
    return 0;
}
static void check_header(const struct fake_event *event,size_t size,uint64_t session,uint32_t interface_index)
{IO24_CHECK(event->typed_request);IO24_CHECK(event->in_length==size);IO24_CHECK(event->request.header.size==size);IO24_CHECK(event->request.header.version==IO24_ABI_VERSION);IO24_CHECK(event->request.header.session==session);IO24_CHECK(event->request.header.interface_index==interface_index);IO24_CHECK(event->request.header.reserved==0);}

static void fill_nonadjacent_duplicate_snapshot(void *output,DWORD output_length)
{
    struct io24_wire_snapshot snapshot;
    struct wine_winusb_interface_snapshot interfaces[3]={{5,0,1,0},{2,1,1,0},{5,2,1,0}};
    struct wine_winusb_alternate_snapshot alternates[3]={{0,0,0,0},{1,0,0,0},{2,0,0,0}};
    memset(&snapshot,0,sizeof(snapshot));snapshot.header.size=72;snapshot.header.version=IO24_ABI_VERSION;
    snapshot.header.session=output_length==72?0:UINT64_C(0x1122334455667788);snapshot.header.speed=HighSpeed;
    snapshot.header.total_size=222;snapshot.header.device_offset=72;snapshot.header.device_length=18;
    snapshot.header.configuration_offset=90;snapshot.header.configuration_length=36;snapshot.header.interfaces_offset=126;
    snapshot.header.interface_count=3;snapshot.header.alternates_offset=174;snapshot.header.alternate_count=3;
    snapshot.header.endpoints_offset=222;snapshot.header.endpoint_count=0;memcpy(snapshot.bytes,io24_device_descriptor,18);
    memcpy(snapshot.bytes+18,io24_nonadjacent_duplicate_configuration,36);memcpy(snapshot.bytes+54,interfaces,sizeof(interfaces));
    memcpy(snapshot.bytes+102,alternates,sizeof(alternates));memcpy(output,&snapshot,output_length==72?72:222);
}

int __cdecl __wine_dbg_header(enum __wine_debug_class c,struct __wine_debug_channel*d,const char*f){(void)c;(void)d;(void)f;return -1;}
int __cdecl __wine_dbg_output(const char*s){(void)s;return 0;}
const char *__cdecl __wine_dbg_strdup(const char*s){return s;}
#ifndef __WINESRC__
HANDLE WINAPI GetProcessHeap(void){return (HANDLE)(uintptr_t)0x4444;}
DWORD WINAPI GetLastError(void){return fake.last_error;}
void WINAPI SetLastError(DWORD error){fake.last_error=error;}
#endif
NTSTATUS WINAPI NtQueryInformationFile(HANDLE h, IO_STATUS_BLOCK *iosb, void *info, ULONG length, FILE_INFORMATION_CLASS cls)
{ FILE_MODE_INFORMATION *mode = info; (void)h; if (!fake.query_ok || cls != FileModeInformation || length != sizeof(*mode)) return STATUS_INVALID_HANDLE; mode->Mode = fake.mode; iosb->Status = fake.query_iosb_status; iosb->Information = fake.query_information; return 0; }
LPVOID WINAPI HeapAlloc(HANDLE h,DWORD f,SIZE_T n){void*p;struct fake_event*e;(void)h;(void)f;p=++fake.alloc_attempts==fake.alloc_fail_at?NULL:calloc(1,n?n:1);e=record_event(EVENT_ALLOC);e->pointer=p;e->out_length=n;if(p)counts.allocations++;return p;}
BOOL WINAPI HeapFree(HANDLE h,DWORD f,LPVOID p){struct fake_event*e;(void)h;(void)f;e=record_event(EVENT_FREE);e->pointer=p;e->result=TRUE;if(p){counts.frees++;free(p);}fake.last_error=ERROR_GEN_FAILURE;return TRUE;}
HANDLE WINAPI CreateEventW(SECURITY_ATTRIBUTES*a,BOOL manual,BOOL initial,LPCWSTR name){struct fake_event*e;(void)a;(void)manual;(void)initial;(void)name;e=record_event(EVENT_ALLOC);fake.event_creates++;if(fake.event_fail_at==fake.event_creates){fake.last_error=ERROR_NOT_ENOUGH_MEMORY;return NULL;}e->pointer=(void*)(uintptr_t)(0xe000+fake.event_count);return e->pointer;}
DWORD WINAPI WaitForSingleObject(HANDLE h,DWORD timeout){(void)timeout;fake.wait_handle=h;if(fake.wait_result==WAIT_FAILED)fake.last_error=fake.wait_error;return fake.wait_result;}
BOOL WINAPI CloseHandle(HANDLE h){struct fake_event*e=record_event(EVENT_CLOSE);e->handle=h;e->result=TRUE;fake.closes++;if(h==IO24_FILE_HANDLE)fake.device_closes++;else fake.event_closes++;fake.last_error=ERROR_GEN_FAILURE;return TRUE;}
BOOL WINAPI DuplicateHandle(HANDLE a,HANDLE source,HANDLE b,HANDLE *target,DWORD c,BOOL d,DWORD flags)
{struct fake_event*e;(void)a;(void)b;(void)c;(void)d;(void)flags;e=record_event(EVENT_DUPLICATE);e->handle=source;e->result=TRUE;fake.duplicates++;if(target)*target=(HANDLE)((uintptr_t)source+0x100);e->pointer=target?*target:NULL;return TRUE;}
void WINAPI InitializeCriticalSection(CRITICAL_SECTION *object)
{unsigned int i;for(i=0;i<sizeof(io24_fake_cs)/sizeof(io24_fake_cs[0]);++i)if(!io24_fake_cs[i].object){io24_fake_cs[i].object=object;mtx_init(&io24_fake_cs[i].lock,mtx_plain);return;}}
void WINAPI DeleteCriticalSection(CRITICAL_SECTION *object)
{struct io24_fake_cs *slot=io24_cs_slot(object);if(slot){mtx_destroy(&slot->lock);slot->object=NULL;}}
void WINAPI EnterCriticalSection(CRITICAL_SECTION *object)
{struct io24_fake_cs *slot=io24_cs_slot(object);if(!slot){InitializeCriticalSection(object);slot=io24_cs_slot(object);}if(slot)mtx_lock(&slot->lock);}
void WINAPI LeaveCriticalSection(CRITICAL_SECTION *object)
{struct io24_fake_cs *slot=io24_cs_slot(object);if(slot){int count=atomic_fetch_add(&io24_leave_gate_count,1)+1;mtx_unlock(&slot->lock);if(atomic_load(&io24_leave_gate_enabled)&&count==atomic_load(&io24_leave_gate_target)){atomic_store(&io24_leave_gate_entered,1);while(!atomic_load(&io24_leave_gate_release))thrd_yield();}}}
BOOL WINAPI TryEnterCriticalSection(CRITICAL_SECTION *object)
{struct io24_fake_cs *slot=io24_cs_slot(object);if(!slot)return FALSE;return mtx_trylock(&slot->lock)==thrd_success;}
void WINAPI InitializeConditionVariable(CONDITION_VARIABLE *object)
{unsigned int i;struct io24_fake_cv *old=io24_cv_slot(object);if(old){cnd_destroy(&old->condition);old->object=NULL;}for(i=0;i<sizeof(io24_fake_cv)/sizeof(io24_fake_cv[0]);++i)if(!io24_fake_cv[i].object){io24_fake_cv[i].object=object;cnd_init(&io24_fake_cv[i].condition);return;}}
BOOL WINAPI SleepConditionVariableCS(CONDITION_VARIABLE *condition,CRITICAL_SECTION *object,DWORD timeout)
{struct io24_fake_cv *cv=io24_cv_slot(condition);struct io24_fake_cs *cs=io24_cs_slot(object);(void)timeout;atomic_store(&io24_free_drain_entered,1);return cv&&cs&&cnd_wait(&cv->condition,&cs->lock)==thrd_success;}
void WINAPI WakeAllConditionVariable(CONDITION_VARIABLE *condition)
{struct io24_fake_cv *cv=io24_cv_slot(condition);if(cv)cnd_broadcast(&cv->condition);}
void WINAPI WakeConditionVariable(CONDITION_VARIABLE *condition)
{struct io24_fake_cv *cv=io24_cv_slot(condition);if(cv)cnd_signal(&cv->condition);}
BOOL WINAPI DeviceIoControl(HANDLE device,DWORD code,void*in,DWORD in_length,void*out,DWORD out_length,DWORD*bytes,OVERLAPPED*ov)
{
    struct fake_event*e=record_event(EVENT_IOCTL);size_t expected=request_size_for_code(code),saved=out_length;DWORD transfer_length;e->handle=device;e->code=code;e->in_length=in_length;e->out_length=out_length;e->pointer=out;e->overlapped=ov;e->private_event=ov?ov->hEvent:NULL;e->bytes_returned_pointer=bytes;e->result=fake.ioctl_result;
    if(code==IO24_IOCTL_RELEASE)fake.release_ioctls++;
    if(code==IO24_IOCTL_INITIALIZE||code==IO24_IOCTL_RELEASE||code==IO24_IOCTL_SET_ALTERNATE){if(fake.private_call_index<fake.private_call_count){unsigned int i=fake.private_call_index++;fake.active_private_call=i;e->result=fake.private_call[i].pending?FALSE:fake.private_call[i].result;if(!e->result)fake.last_error=fake.private_call[i].pending?ERROR_IO_PENDING:fake.private_call[i].error;}}
    if(code==IO24_IOCTL_DESCRIPTOR&&fake.descriptor_immediate_failure)
    { e->result=FALSE; fake.last_error=ERROR_ACCESS_DENIED; }
    if((code==IO24_IOCTL_CONTROL_IN||code==IO24_IOCTL_CONTROL_OUT)&&fake.control_immediate_failure)
    { e->result=FALSE; fake.last_error=ERROR_ACCESS_DENIED; }
    if(in&&expected&&in_length==expected){memcpy(&e->request,in,expected);e->typed_request=TRUE;}
    if(saved>sizeof(e->output_before))saved=sizeof(e->output_before);
    if(out&&saved)memcpy(e->output_before,out,saved);
    e->output_saved=saved;counts.submits++;
    if(code==IO24_IOCTL_SET_ALTERNATE&&atomic_load(&io24_policy_alt_gate_enabled))
    {atomic_store(&io24_policy_alt_gate_entered,1);while(!atomic_load(&io24_policy_alt_gate_release))thrd_yield();}
    e->returned_bytes=0;
    if(out&&out_length&&e->typed_request)
    {
        if(code==IO24_IOCTL_INITIALIZE&&out_length>=sizeof(struct wine_winusb_snapshot)&&e->typed_request){struct io24_wire_snapshot snapshot;struct wine_winusb_interface_snapshot iface={5,0,2,0};struct wine_winusb_alternate_snapshot alternate[2]={{0,0,0,0},{0,1,0,2}};struct wine_winusb_endpoint_snapshot endpoint[2]={{1,0x81,2,512},{1,1,2,512}};DWORD total=211;memset(&snapshot,0,sizeof(snapshot));snapshot.header.size=72;snapshot.header.version=IO24_ABI_VERSION;snapshot.header.session=out_length==72?0:UINT64_C(0x1122334455667788);snapshot.header.total_size=211;snapshot.header.speed=3;snapshot.header.device_offset=72;snapshot.header.device_length=18;snapshot.header.configuration_offset=90;snapshot.header.configuration_length=41;snapshot.header.interfaces_offset=131;snapshot.header.interface_count=1;snapshot.header.alternates_offset=147;snapshot.header.alternate_count=2;snapshot.header.endpoints_offset=179;snapshot.header.endpoint_count=2;memcpy(snapshot.bytes,io24_device_descriptor,18);memcpy(snapshot.bytes+18,io24_mi05_configuration,41);memcpy(snapshot.bytes+59,&iface,sizeof(iface));memcpy(snapshot.bytes+75,alternate,sizeof(alternate));memcpy(snapshot.bytes+107,endpoint,sizeof(endpoint));if(fake.policy_associated_fixture){static const uint8_t configuration[66]={9,2,66,0,2,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,1,2,0xff,0,0,6,7,5,0x81,2,0,2,0,7,5,1,2,0,2,0,9,4,6,0,0,0xff,0,0,1,9,4,6,1,1,0xff,0,0,1,7,5,0x83,2,0,2,0};struct wine_winusb_interface_snapshot interfaces[2]={{5,0,2,0},{6,2,2,0}};struct wine_winusb_alternate_snapshot alternates[4]={{0,0,0,0},{0,1,0,2},{1,0,2,0},{1,1,2,1}};struct wine_winusb_endpoint_snapshot endpoints[3]={{1,0x81,2,512},{1,1,2,512},{3,0x83,2,512}};total=300;snapshot.header.total_size=total;snapshot.header.configuration_length=66;snapshot.header.interfaces_offset=156;snapshot.header.interface_count=2;snapshot.header.alternates_offset=188;snapshot.header.alternate_count=4;snapshot.header.endpoints_offset=252;snapshot.header.endpoint_count=3;memcpy(snapshot.bytes+18,configuration,sizeof(configuration));memcpy(snapshot.bytes+84,interfaces,sizeof(interfaces));memcpy(snapshot.bytes+116,alternates,sizeof(alternates));memcpy(snapshot.bytes+180,endpoints,sizeof(endpoints));}else if(fake.three_interface_fixture){static const uint8_t configuration[59]={9,2,59,0,3,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,1,2,0xff,0,0,6,7,5,0x81,2,0,2,0,7,5,0x01,2,0,2,0,9,4,2,0,0,0xff,0,0,1,9,4,3,0,0,0xff,0,0,1};struct wine_winusb_interface_snapshot interfaces[3]={{5,0,2,0},{2,2,1,0},{3,3,1,0}};struct wine_winusb_alternate_snapshot alternates[4]={{0,0,0,0},{0,1,0,2},{1,0,2,0},{2,0,2,0}};total=293;snapshot.header.total_size=total;snapshot.header.configuration_length=59;snapshot.header.interfaces_offset=149;snapshot.header.interface_count=3;snapshot.header.alternates_offset=197;snapshot.header.alternate_count=4;snapshot.header.endpoints_offset=261;snapshot.header.endpoint_count=2;memcpy(snapshot.bytes+18,configuration,sizeof(configuration));memcpy(snapshot.bytes+77,interfaces,sizeof(interfaces));memcpy(snapshot.bytes+125,alternates,sizeof(alternates));memcpy(snapshot.bytes+189,endpoint,sizeof(endpoint));}else if(fake.two_interface_fixture){static const uint8_t configuration[50]={9,2,50,0,2,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,1,2,0xff,0,0,6,7,5,0x81,2,0,2,0,7,5,0x01,2,0,2,0,9,4,2,0,0,0xff,0,0,1};struct wine_winusb_interface_snapshot interfaces[2]={{5,0,2,0},{2,2,1,0}};struct wine_winusb_alternate_snapshot alternates[3]={{0,0,0,0},{0,1,0,2},{1,0,2,0}};total=252;snapshot.header.total_size=total;snapshot.header.configuration_length=50;snapshot.header.interfaces_offset=140;snapshot.header.interface_count=2;snapshot.header.alternates_offset=172;snapshot.header.alternate_count=3;snapshot.header.endpoints_offset=220;snapshot.header.endpoint_count=2;memcpy(snapshot.bytes+18,configuration,sizeof(configuration));memcpy(snapshot.bytes+68,interfaces,sizeof(interfaces));memcpy(snapshot.bytes+100,alternates,sizeof(alternates));memcpy(snapshot.bytes+148,endpoint,sizeof(endpoint));}else if(fake.fixture==SNAPSHOT_FIXTURE_DESCENDING||fake.fixture==SNAPSHOT_FIXTURE_DUPLICATE_INTERFACE){struct wine_winusb_interface_snapshot interfaces[2]={{5,0,1,0},{fake.fixture==SNAPSHOT_FIXTURE_DESCENDING?2:5,1,1,0}};struct wine_winusb_alternate_snapshot alternates[2]={{0,0,0,0},{1,0,0,0}};total=181;snapshot.header.total_size=total;snapshot.header.configuration_length=27;snapshot.header.interfaces_offset=117;snapshot.header.interface_count=2;snapshot.header.alternates_offset=149;snapshot.header.alternate_count=2;snapshot.header.endpoints_offset=181;snapshot.header.endpoint_count=0;memcpy(snapshot.bytes+18,fake.fixture==SNAPSHOT_FIXTURE_DESCENDING?io24_descending_configuration:io24_duplicate_interface_configuration,27);memcpy(snapshot.bytes+45,interfaces,sizeof(interfaces));memcpy(snapshot.bytes+77,alternates,sizeof(alternates));}else if(fake.fixture==SNAPSHOT_FIXTURE_CROSS_ALTERNATE_ENDPOINT_REUSE){snapshot.bytes[54]=0x81;endpoint[1].pipe_id=0x81;memcpy(snapshot.bytes+107,endpoint,sizeof(endpoint));}if(fake.low_speed_fixture){iface.interface_number=2;iface.first_alternate=0;iface.alternate_count=1;alternate[0]=(struct wine_winusb_alternate_snapshot){0,0,0,1};endpoint[0]=(struct wine_winusb_endpoint_snapshot){0,0x82,3,64};total=163;snapshot.header.total_size=total;snapshot.header.speed=LowSpeed;snapshot.header.configuration_length=25;snapshot.header.interfaces_offset=115;snapshot.header.alternates_offset=131;snapshot.header.alternate_count=1;snapshot.header.endpoints_offset=147;snapshot.header.endpoint_count=1;memcpy(snapshot.bytes+18,io24_low_configuration,25);memcpy(snapshot.bytes+43,&iface,sizeof(iface));memcpy(snapshot.bytes+59,alternate,sizeof(alternate[0]));memcpy(snapshot.bytes+75,endpoint,sizeof(endpoint[0]));}if(out_length==72)mutate_header(&snapshot);else mutate_snapshot(&snapshot);memcpy(out,&snapshot,out_length==72?72:total);e->returned_bytes=out_length==72?72:total;}
        if(code==IO24_IOCTL_DESCRIPTOR)
        {
            DWORD returned=fake.descriptor_response_length ? fake.descriptor_response_length : sizeof(io24_string_descriptor_response);
            DWORD copied=returned<out_length?returned:out_length;
            unsigned int i;
            for(i=0;i<copied;i++)((uint8_t *)out)[i]=i<sizeof(io24_string_descriptor_response)?io24_string_descriptor_response[i]:(uint8_t)(0x40+i);
            e->returned_bytes=returned;
        }
        if(code==IO24_IOCTL_GET_POLICY&&out_length>=sizeof(struct io24_wire_policy)){struct io24_wire_policy response=e->request.policy;unsigned int slot=(response.pipe_id&0x80)!=0;response.value_length=(response.policy_id==PIPE_TRANSFER_TIMEOUT||response.policy_id==MAXIMUM_TRANSFER_SIZE)?4:1;response.value=response.policy_id<=RESET_PIPE_ON_RESUME?fake.policy_value[slot][response.policy_id]:0;memcpy(out,&response,sizeof(response));e->returned_bytes=sizeof(response);}
        transfer_length=transfer_response_length(code,ov);
        if(transfer_length)
        {
            /* For an oversized response do not write beyond the transport
             * buffer.  A public implementation must reject its claimed byte
             * count before copying any staged IN response to the caller. */
            if(code==IO24_IOCTL_READ_PIPE&&out_length>=transfer_length)
                memcpy(out,io24_read_response,transfer_length);
            else if(code==IO24_IOCTL_CONTROL_IN&&out_length>=transfer_length)
            { unsigned int i;for(i=0;i<transfer_length;i++)((uint8_t *)out)[i]=(uint8_t)(0x70+i); }
            e->returned_bytes=transfer_length;
        }
    }
    if(code==IO24_IOCTL_GET_POLICY&&e->typed_request&&out&&out_length>=sizeof(struct io24_wire_policy))
    {
        struct io24_wire_policy *response=out;
        switch(fake.policy_response_mutation)
        {
        case POLICY_RESPONSE_SHORT: e->returned_bytes=sizeof(*response)-1; break;
        case POLICY_RESPONSE_LONG: e->returned_bytes=sizeof(*response)+1; break;
        case POLICY_RESPONSE_SIZE: response->request.size--; break;
        case POLICY_RESPONSE_VERSION: response->request.version++; break;
        case POLICY_RESPONSE_SESSION: response->request.session++; break;
        case POLICY_RESPONSE_INTERFACE: response->request.interface_index++; break;
        case POLICY_RESPONSE_RESERVED: response->request.reserved=1; break;
        case POLICY_RESPONSE_PIPE: response->pipe_id++; break;
        case POLICY_RESPONSE_POLICY: response->policy_id++; break;
        case POLICY_RESPONSE_LENGTH: response->value_length++; break;
        case POLICY_RESPONSE_BOOLEAN_VALUE: response->value=2; break;
        default: break;
        }
    }
    if(code==IO24_IOCTL_SET_POLICY&&e->typed_request&&e->result&&fake.policy_set_return_bytes)
        e->returned_bytes=fake.policy_set_return_bytes;
    if(code==IO24_IOCTL_SET_POLICY&&e->typed_request&&e->result&&e->request.policy.policy_id<=RESET_PIPE_ON_RESUME){unsigned int slot=(e->request.policy.pipe_id&0x80)!=0;fake.policy_value[slot][e->request.policy.policy_id]=e->request.policy.value;}
    if(code==IO24_IOCTL_SET_ALTERNATE&&e->typed_request&&e->result&&e->request.alternate.alternate_setting==1)fake_policy_defaults();
    if(code==IO24_IOCTL_INITIALIZE&&fake.fixture==SNAPSHOT_FIXTURE_NONADJACENT_DUPLICATE_INTERFACE&&out&&e->typed_request){fill_nonadjacent_duplicate_snapshot(out,out_length);e->returned_bytes=out_length==72?72:222;}
    if(code==IO24_IOCTL_INITIALIZE&&out_length==72&&!fake.private_call_count){e->result=FALSE;fake.last_error=ERROR_INSUFFICIENT_BUFFER;}
    if(out&&saved)memcpy(e->output_after,out,saved);
    if(fake.active_private_call!=~0u&&fake.active_private_call<fake.private_call_count&&fake.private_call[fake.active_private_call].bytes)e->returned_bytes=fake.private_call[fake.active_private_call].bytes;
    if(ov)ov->InternalHigh=e->returned_bytes;
    if(bytes && !(code==IO24_IOCTL_INITIALIZE&&out_length==72&&!e->result))*bytes=e->returned_bytes;
    if(!fake.ioctl_result)fake.last_error=fake.ioctl_error;
    return e->result;
}
BOOL WINAPI GetOverlappedResult(HANDLE h,OVERLAPPED*ov,DWORD*b,BOOL wait)
{struct fake_event*e=record_event(EVENT_OVERLAPPED);e->handle=h;e->overlapped=ov;e->in_length=wait;e->result=fake.overlapped_result;e->returned_bytes=IO24_OVERLAPPED_RESULT_LENGTH;if(fake.active_private_call!=~0u&&fake.active_private_call<fake.private_call_count){e->result=fake.private_call[fake.active_private_call].completion_result;e->returned_bytes=fake.private_call[fake.active_private_call].completion_bytes;if(!e->result)fake.last_error=fake.private_call[fake.active_private_call].completion_error;}e->error=e->result?ERROR_SUCCESS:fake.last_error;counts.completions++;if(b)*b=e->returned_bytes;return e->result;}

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
    if(!strcmp(mode,"--alternate"))return SYMBOL_INITIALIZE|SYMBOL_ASSOCIATED|SYMBOL_FREE|SYMBOL_ALTERNATE;
    if(!strcmp(mode,"--initialize"))return SYMBOL_INITIALIZE;
    if(!strcmp(mode,"--handles"))return SYMBOL_INITIALIZE|SYMBOL_ASSOCIATED|SYMBOL_FREE;
    if(!strcmp(mode,"--descriptors"))return SYMBOL_INITIALIZE|SYMBOL_DESCRIPTOR|SYMBOL_QUERY;
    if(!strcmp(mode,"--control-descriptor"))return SYMBOL_INITIALIZE|SYMBOL_CONTROL|SYMBOL_DESCRIPTOR;
    if(!strcmp(mode,"--policy"))return SYMBOL_INITIALIZE|SYMBOL_GET_POLICY|SYMBOL_SET_POLICY|SYMBOL_ALTERNATE;
    if(!strcmp(mode,"--transfer"))return SYMBOL_INITIALIZE|SYMBOL_CONTROL|SYMBOL_READ|SYMBOL_WRITE|SYMBOL_OVERLAPPED;
    if(!strcmp(mode,"--cancel"))return SYMBOL_INITIALIZE|SYMBOL_ABORT|SYMBOL_RESET;
    return SYMBOL_ALL;
}
static void check_target_symbols(const struct functions *f,uint32_t target)
{uint32_t missing=target&~f->present_mask,bit;for(bit=1;bit<=SYMBOL_WRITE;bit<<=1)if(missing&bit)++counts.failures;if((target&SYMBOL_FREE)&&f->free_handle)IO24_CHECK(!f->free_handle(NULL));}

static BOOL initialize_handle(const struct functions*f,WINUSB_INTERFACE_HANDLE *handle)
{
    unsigned int submits=counts.submits,events=fake.event_count,i;const struct fake_event *header=NULL,*full=NULL,*allocation=NULL;struct wine_winusb_snapshot sizing;BOOL ok;*handle=NULL;
    if(!f->initialize){IO24_CHECK(FALSE);return FALSE;}ok=f->initialize(IO24_FILE_HANDLE,handle);
    IO24_CHECK(ok&&*handle&&*handle!=INVALID_HANDLE_VALUE);IO24_CHECK(counts.submits==submits+2);IO24_CHECK(fake.event_count>events);
    for(i=events;i<fake.event_count;i++)if(fake.events[i].kind==EVENT_IOCTL&&fake.events[i].code==IO24_IOCTL_INITIALIZE){if(!header)header=&fake.events[i];else full=&fake.events[i];}
    if(header&&full){IO24_CHECK(header->handle==IO24_FILE_HANDLE&&header->in_length==24&&header->out_length==72&&header->overlapped!=NULL&&!header->result&&header->returned_bytes==72);memcpy(&sizing,header->output_after,sizeof(sizing));for(i=events;i<fake.event_count;i++)if(fake.events[i].kind==EVENT_ALLOC&&fake.events[i].pointer==full->pointer){allocation=&fake.events[i];break;}IO24_CHECK(full->out_length==sizing.total_size&&full->pointer&&allocation&&allocation->pointer==full->pointer&&allocation->out_length==sizing.total_size);}else IO24_CHECK(FALSE);
    return ok&&*handle;
}
static void reject_size_query(const struct functions*f,BOOL result,DWORD error,DWORD bytes){WINUSB_INTERFACE_HANDLE h=(void *)(uintptr_t)1;fake_reset();fake.private_call_count=1;fake.private_call[0].result=result;fake.private_call[0].error=error;fake.private_call[0].bytes=bytes;IO24_CHECK(f->initialize&&!f->initialize(IO24_FILE_HANDLE,&h));IO24_CHECK(h==NULL&&counts.submits==1&&fake.release_ioctls==0&&counts.allocations==0&&counts.frees==0&&fake.event_creates==fake.event_closes&&!fake.device_closes&&!fake.duplicates);}
static void check_release(const struct fake_event *event);
static void reject_full_snapshot(const struct functions *f, unsigned int mutation)
{
    WINUSB_INTERFACE_HANDLE h=(void *)(uintptr_t)1;
    fake_reset();fake.snapshot_mutation=mutation;
    IO24_CHECK(f->initialize&&!f->initialize(IO24_FILE_HANDLE,&h));
    IO24_CHECK(h==NULL&&counts.submits==3&&fake.release_ioctls==1&&fake.last_error==ERROR_BAD_DEVICE&&
            fake.event_creates==fake.event_closes&&counts.allocations==counts.frees&&!fake.device_closes&&!fake.duplicates);
    check_release(find_ioctl_after(0,IO24_IOCTL_RELEASE));
}
static void check_release(const struct fake_event *event)
{unsigned int i,creates=0,closes=0;IO24_CHECK(event&&event->handle==IO24_FILE_HANDLE&&event->overlapped&&event->private_event&&event->in_length==24&&event->typed_request);if(!event)return;check_header(event,24,UINT64_C(0x1122334455667788),0);for(i=0;i<fake.event_count;i++){if(fake.events[i].kind==EVENT_ALLOC&&fake.events[i].pointer==event->private_event)creates++;if(fake.events[i].kind==EVENT_CLOSE&&fake.events[i].handle==event->private_event)closes++;}IO24_CHECK(creates==1&&closes==1);}
static void check_wait_event(const struct fake_event *event,DWORD error)
{IO24_CHECK(event&&event->private_event&&fake.wait_handle==event->private_event&&fake.last_error==error);}
static void release_variant(const struct functions *f, BOOL pending, BOOL result, DWORD error)
{WINUSB_INTERFACE_HANDLE h;const struct fake_event *release;unsigned int completion_start;fake_reset();if(!initialize_handle(f,&h))return;fake.private_call_count=1;fake.private_call[0].result=result;fake.private_call[0].error=error;fake.private_call[0].pending=pending;fake.private_call[0].completion_result=result;fake.private_call[0].completion_error=error;fake.private_call[0].completion_bytes=0;completion_start=counts.completions;IO24_CHECK(f->free_handle&&f->free_handle(h));IO24_CHECK(fake.release_ioctls==1&&counts.allocations==counts.frees);release=find_ioctl_after(0,IO24_IOCTL_RELEASE);check_release(release);if(pending){const struct fake_event *completion=NULL;unsigned int i;for(i=0;i<fake.event_count;i++)if(fake.events[i].kind==EVENT_OVERLAPPED)completion=&fake.events[i];IO24_CHECK(counts.completions==completion_start+1&&completion&&completion->handle==IO24_FILE_HANDLE&&completion->overlapped==release->overlapped&&completion->result==result&&completion->error==(result?ERROR_SUCCESS:error));}else IO24_CHECK(counts.completions==completion_start);}
static void reject_header(const struct functions *f, unsigned int mutation)
{
    WINUSB_INTERFACE_HANDLE h=(void *)(uintptr_t)1;
    fake_reset();fake.header_mutation=mutation;
    IO24_CHECK(f->initialize&&!f->initialize(IO24_FILE_HANDLE,&h));
    IO24_CHECK(h==NULL&&counts.submits==1&&fake.release_ioctls==0&&counts.allocations==0&&counts.frees==0&&
            fake.last_error==ERROR_BAD_DEVICE&&fake.event_creates==fake.event_closes&&!fake.device_closes&&!fake.duplicates);
}
static void test_initialize(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE h;unsigned int mutation;
    fake_reset();if(initialize_handle(f,&h)&&f->free_handle)IO24_CHECK(f->free_handle(h));IO24_CHECK(fake.release_ioctls==1&&!fake.device_closes&&!fake.duplicates);check_release(find_ioctl_after(0,IO24_IOCTL_RELEASE));
    reject_size_query(f,TRUE,0,0);reject_size_query(f,FALSE,ERROR_INVALID_HANDLE,72);reject_size_query(f,FALSE,ERROR_INSUFFICIENT_BUFFER,71);reject_size_query(f,FALSE,ERROR_INSUFFICIENT_BUFFER,73);
    fake_reset();h=(void *)(uintptr_t)1;IO24_CHECK(f->initialize&&!f->initialize(IO24_FILE_HANDLE,NULL)&&fake.last_error==ERROR_INVALID_PARAMETER);IO24_CHECK(!f->initialize(NULL,&h)&&h==NULL&&fake.last_error==ERROR_INVALID_HANDLE);
    fake_reset();h=(void *)(uintptr_t)1;fake.query_ok=FALSE;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_INVALID_HANDLE&&counts.submits==0);
    fake_reset();h=(void *)(uintptr_t)1;fake.query_iosb_status=STATUS_INVALID_HANDLE;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_INVALID_HANDLE&&counts.submits==0);
    fake_reset();h=(void *)(uintptr_t)1;fake.query_information=0;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_INVALID_HANDLE&&counts.submits==0);
    fake_reset();h=(void *)(uintptr_t)1;fake.mode=FILE_SYNCHRONOUS_IO_ALERT;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_INVALID_HANDLE&&counts.submits==0);
    fake_reset();h=(void *)(uintptr_t)1;fake.mode=FILE_SYNCHRONOUS_IO_NONALERT;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_INVALID_HANDLE&&counts.submits==0);
    fake_reset();h=(void *)(uintptr_t)1;IO24_CHECK(!f->initialize(INVALID_HANDLE_VALUE,&h)&&h==NULL&&fake.last_error==ERROR_INVALID_HANDLE&&counts.submits==0);
    fake_reset();h=(void *)(uintptr_t)1;fake.event_fail_at=1;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_NOT_ENOUGH_MEMORY&&counts.submits==0);
    fake_reset();h=(void *)(uintptr_t)1;fake.private_call_count=1;fake.private_call[0].result=FALSE;fake.private_call[0].error=ERROR_ACCESS_DENIED;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_ACCESS_DENIED&&counts.submits==1&&fake.release_ioctls==0);
    fake_reset();h=(void *)(uintptr_t)1;fake.private_call_count=1;fake.private_call[0].pending=TRUE;fake.wait_result=WAIT_FAILED;fake.wait_error=ERROR_ACCESS_DENIED;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_ACCESS_DENIED&&counts.submits==1&&fake.release_ioctls==0);check_wait_event(find_ioctl_after(0,IO24_IOCTL_INITIALIZE),ERROR_ACCESS_DENIED);
    fake_reset();h=(void *)(uintptr_t)1;fake.private_call_count=1;fake.private_call[0].pending=TRUE;fake.wait_result=WAIT_FAILED;fake.wait_error=ERROR_INVALID_HANDLE;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_INVALID_HANDLE&&counts.submits==1&&fake.release_ioctls==0);check_wait_event(find_ioctl_after(0,IO24_IOCTL_INITIALIZE),ERROR_INVALID_HANDLE);
    fake_reset();h=(void *)(uintptr_t)1;fake.private_call_count=1;fake.private_call[0].pending=TRUE;fake.private_call[0].completion_result=TRUE;fake.private_call[0].completion_bytes=72;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_BAD_DEVICE&&counts.submits==1&&fake.release_ioctls==0);
    for(mutation=1;mutation<=10;mutation++)reject_header(f,mutation);
    for(mutation=SNAPSHOT_BAD_VERSION;mutation<=SNAPSHOT_DUPLICATE_PIPE;mutation++)reject_full_snapshot(f,mutation);
    fake_reset();fake.fixture=SNAPSHOT_FIXTURE_DESCENDING;if(initialize_handle(f,&h)&&f->free_handle)IO24_CHECK(f->free_handle(h));IO24_CHECK(fake.release_ioctls==1&&counts.allocations==counts.frees);
    fake_reset();h=(void *)(uintptr_t)1;fake.fixture=SNAPSHOT_FIXTURE_DUPLICATE_INTERFACE;IO24_CHECK(f->initialize&&!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.release_ioctls==1&&fake.last_error==ERROR_BAD_DEVICE&&counts.allocations==counts.frees);check_release(find_ioctl_after(0,IO24_IOCTL_RELEASE));
    fake_reset();h=(void *)(uintptr_t)1;fake.fixture=SNAPSHOT_FIXTURE_NONADJACENT_DUPLICATE_INTERFACE;IO24_CHECK(f->initialize&&!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.release_ioctls==1&&fake.last_error==ERROR_BAD_DEVICE&&counts.allocations==counts.frees);check_release(find_ioctl_after(0,IO24_IOCTL_RELEASE));
    fake_reset();fake.fixture=SNAPSHOT_FIXTURE_CROSS_ALTERNATE_ENDPOINT_REUSE;if(initialize_handle(f,&h)&&f->free_handle)IO24_CHECK(f->free_handle(h));IO24_CHECK(fake.release_ioctls==1&&counts.allocations==counts.frees);
    fake_reset();h=(void *)(uintptr_t)1;fake.alloc_fail_at=1;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_NOT_ENOUGH_MEMORY&&counts.submits==1&&fake.release_ioctls==0);
    fake_reset();h=(void *)(uintptr_t)1;fake.private_call_count=2;fake.private_call[0].result=FALSE;fake.private_call[0].error=ERROR_INSUFFICIENT_BUFFER;fake.private_call[0].bytes=72;fake.private_call[1].pending=TRUE;fake.private_call[1].completion_error=ERROR_ACCESS_DENIED;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_ACCESS_DENIED&&counts.submits==2&&fake.release_ioctls==0&&counts.frees==1);
    fake_reset();h=(void *)(uintptr_t)1;fake.private_call_count=2;fake.private_call[0].result=FALSE;fake.private_call[0].error=ERROR_INSUFFICIENT_BUFFER;fake.private_call[0].bytes=72;fake.private_call[1].result=FALSE;fake.private_call[1].error=ERROR_ACCESS_DENIED;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_ACCESS_DENIED&&counts.submits==2&&fake.release_ioctls==0&&counts.frees==1);
    fake_reset();h=(void *)(uintptr_t)1;fake.alloc_fail_at=2;IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&h)&&h==NULL&&fake.last_error==ERROR_NOT_ENOUGH_MEMORY&&counts.submits==3&&fake.release_ioctls==1&&counts.allocations==counts.frees);
    fake_reset();fake.low_speed_fixture=TRUE;if(initialize_handle(f,&h)&&f->free_handle)IO24_CHECK(f->free_handle(h));IO24_CHECK(fake.release_ioctls==1&&counts.allocations==counts.frees);
    fake_reset();h=NULL;fake.private_call_count=3;fake.private_call[0].result=FALSE;fake.private_call[0].error=ERROR_INSUFFICIENT_BUFFER;fake.private_call[0].bytes=72;fake.private_call[1].pending=TRUE;fake.private_call[1].completion_result=TRUE;fake.private_call[1].completion_bytes=211;fake.private_call[2].result=TRUE;IO24_CHECK(f->initialize&&f->initialize(IO24_FILE_HANDLE,&h)&&h);if(h&&f->free_handle)IO24_CHECK(f->free_handle(h));IO24_CHECK(counts.completions==1&&fake.release_ioctls==1&&counts.allocations==counts.frees);
    fake_reset();h=NULL;fake.private_call_count=3;fake.private_call[0].pending=TRUE;fake.private_call[0].completion_error=ERROR_INSUFFICIENT_BUFFER;fake.private_call[0].completion_bytes=72;fake.private_call[1].result=TRUE;fake.private_call[2].result=TRUE;IO24_CHECK(f->initialize&&f->initialize(IO24_FILE_HANDLE,&h)&&h);if(h&&f->free_handle)IO24_CHECK(f->free_handle(h));IO24_CHECK(counts.completions==1&&counts.submits==3&&fake.release_ioctls==1&&fake.event_creates==fake.event_closes&&counts.allocations==counts.frees&&!fake.device_closes&&!fake.duplicates);
    release_variant(f,FALSE,TRUE,0);release_variant(f,FALSE,FALSE,ERROR_ACCESS_DENIED);release_variant(f,TRUE,TRUE,0);release_variant(f,TRUE,FALSE,ERROR_ACCESS_DENIED);
    fake_reset();if(initialize_handle(f,&h)){fake.event_fail_at=fake.event_creates+1;IO24_CHECK(f->free_handle&&f->free_handle(h));IO24_CHECK(fake.release_ioctls==0&&counts.allocations==counts.frees);}
    fake_reset();if(initialize_handle(f,&h)){unsigned int completion_start=counts.completions;const struct fake_event *release;fake.private_call_count=1;fake.private_call[0].pending=TRUE;fake.wait_result=WAIT_FAILED;fake.wait_error=ERROR_INVALID_HANDLE;IO24_CHECK(f->free_handle&&f->free_handle(h));IO24_CHECK(fake.release_ioctls==1&&counts.allocations==counts.frees&&counts.completions==completion_start);release=find_ioctl_after(0,IO24_IOCTL_RELEASE);check_release(release);IO24_CHECK(release&&fake.wait_handle==release->private_event);}
}
static void check_bad_free(const struct functions *f, WINUSB_INTERFACE_HANDLE handle)
{
    pid_t child;int status;

    if (!f->free_handle) return;
    child=fork();
    IO24_CHECK(child>=0);
    if (!child)
    {
        BOOL ok=f->free_handle(handle);
        _exit(!ok&&GetLastError()==ERROR_INVALID_HANDLE?0:1);
    }
    if (child>0)
    {
        IO24_CHECK(waitpid(child,&status,0)==child);
        IO24_CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);
    }
}

static void check_unreadable_admission(const struct functions *f, unsigned int operation)
{
    pid_t child;int status;
    if ((operation==0&&!f->associated)||(operation==1&&!f->descriptor)||(operation==2&&!f->query)) return;
    child=fork();IO24_CHECK(child>=0);if(!child)
    {
        WINUSB_INTERFACE_HANDLE out=NULL;ULONG length=1;uint8_t byte=0;BOOL ok=FALSE;
        if(operation==0) ok=f->associated((void *)(uintptr_t)1,0,&out);
        else if(operation==1) ok=f->descriptor((void *)(uintptr_t)1,1,0,0,&byte,1,&length);
        else ok=f->query((void *)(uintptr_t)1,DEVICE_SPEED,&length,&byte);
        if(operation==0) _exit(!ok&&GetLastError()==ERROR_INVALID_HANDLE&&out==NULL?0:1);
        if(operation==1) _exit(!ok&&GetLastError()==ERROR_INVALID_HANDLE&&length==0&&byte==0?0:1);
        _exit(!ok&&GetLastError()==ERROR_INVALID_HANDLE&&length==1&&byte==0?0:1);
    }
    if(child>0){IO24_CHECK(waitpid(child,&status,0)==child);IO24_CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);}
}

static void check_stale_admission(const struct functions *f, WINUSB_INTERFACE_HANDLE stale, unsigned int operation)
{
    pid_t child;int status;
    if ((operation==0&&!f->associated)||(operation==1&&!f->descriptor)||(operation==2&&!f->query)) return;
    child=fork();IO24_CHECK(child>=0);if(!child)
    {
        WINUSB_INTERFACE_HANDLE output=(void *)(uintptr_t)1;ULONG length=1;uint8_t byte=0x6d;BOOL ok;
        if(operation==0) ok=f->associated(stale,0,&output);
        else if(operation==1) ok=f->descriptor(stale,1,0,0,&byte,1,&length);
        else ok=f->query(stale,DEVICE_SPEED,&length,&byte);
        if(operation==0) _exit(!ok&&GetLastError()==ERROR_INVALID_HANDLE&&output==NULL?0:1);
        if(operation==1) _exit(!ok&&GetLastError()==ERROR_INVALID_HANDLE&&length==0&&byte==0x6d?0:1);
        _exit(!ok&&GetLastError()==ERROR_INVALID_HANDLE&&length==1&&byte==0x6d?0:1);
    }
    if(child>0){IO24_CHECK(waitpid(child,&status,0)==child);IO24_CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);}
}

static void check_task5_initialize_allocations(const struct functions *f)
{
    unsigned int attempt;WINUSB_INTERFACE_HANDLE handle;
    if(!f->initialize||!f->free_handle) return;
    for(attempt=2;attempt<=4;++attempt)
    {
        fake_reset();handle=(void *)(uintptr_t)1;fake.alloc_fail_at=attempt;
        IO24_CHECK(!f->initialize(IO24_FILE_HANDLE,&handle)&&handle==NULL&&fake.last_error==ERROR_NOT_ENOUGH_MEMORY);
        IO24_CHECK(counts.submits==3&&fake.release_ioctls==1&&counts.allocations==counts.frees&&!fake.device_closes);
        if(handle) f->free_handle(handle);
    }
}

static BOOL initialize_two_interface_handle(const struct functions *f, WINUSB_INTERFACE_HANDLE *root)
{
    fake_reset();fake.two_interface_fixture=TRUE;
    return initialize_handle(f,root);
}
static BOOL initialize_three_interface_handle(const struct functions *f, WINUSB_INTERFACE_HANDLE *root)
{
    fake_reset();fake.three_interface_fixture=TRUE;
    return initialize_handle(f,root);
}

struct io24_cache_thread { const struct functions *functions; WINUSB_INTERFACE_HANDLE root; atomic_int started; BOOL result; ULONG length; uint8_t speed[2]; };
struct io24_free_thread { const struct functions *functions; WINUSB_INTERFACE_HANDLE handle; atomic_int started; BOOL result; };
struct io24_policy_alt_thread { const struct functions *functions; WINUSB_INTERFACE_HANDLE handle; atomic_int started,done; BOOL result; };
struct io24_policy_get_thread { const struct functions *functions; WINUSB_INTERFACE_HANDLE handle; atomic_int started,done; BOOL result; ULONG length,value; };
static int io24_cache_thread_main(void *opaque)
{struct io24_cache_thread *state=opaque;state->length=sizeof(state->speed);atomic_store(&state->started,1);state->result=state->functions->query(state->root,DEVICE_SPEED,&state->length,state->speed);return 0;}
static int io24_free_thread_main(void *opaque)
{struct io24_free_thread *state=opaque;atomic_store(&state->started,1);state->result=state->functions->free_handle(state->handle);atomic_store(&io24_free_done,1);return 0;}
static int io24_policy_alt_thread_main(void *opaque)
{struct io24_policy_alt_thread *state=opaque;atomic_store(&state->started,1);state->result=state->functions->set_alt(state->handle,1);atomic_store(&state->done,1);return 0;}
static int io24_policy_get_thread_main(void *opaque)
{struct io24_policy_get_thread *state=opaque;state->length=sizeof(state->value);state->value=IO24_VALUE_SENTINEL;atomic_store(&state->started,1);state->result=state->functions->get_policy(state->handle,0x81,MAXIMUM_TRANSFER_SIZE,&state->length,&state->value);atomic_store(&state->done,1);return 0;}

static void test_acquire_before_free(const struct functions *f, WINUSB_INTERFACE_HANDLE root)
{
    struct io24_cache_thread acquire={.functions=f,.root=root};struct io24_free_thread retire={.functions=f,.handle=root};thrd_t acquire_thread,retire_thread;unsigned int spins;
    atomic_init(&acquire.started,0);atomic_init(&retire.started,0);atomic_store(&io24_leave_gate_count,0);atomic_store(&io24_leave_gate_target,2);atomic_store(&io24_leave_gate_enabled,1);
    IO24_CHECK(thrd_create(&acquire_thread,io24_cache_thread_main,&acquire)==thrd_success);
    for(spins=0;spins<1000000&&!atomic_load(&io24_leave_gate_entered);++spins) thrd_yield();
    IO24_CHECK(atomic_load(&io24_leave_gate_entered));
    IO24_CHECK(thrd_create(&retire_thread,io24_free_thread_main,&retire)==thrd_success);
    for(spins=0;spins<1000000&&!atomic_load(&retire.started);++spins)thrd_yield();
    for(spins=0;spins<1000000&&!atomic_load(&io24_free_drain_entered);++spins) thrd_yield();
    IO24_CHECK(atomic_load(&io24_free_drain_entered)&&!atomic_load(&io24_free_done));
    atomic_store(&io24_leave_gate_enabled,0);atomic_store(&io24_leave_gate_release,1);IO24_CHECK(thrd_join(acquire_thread,NULL)==thrd_success);IO24_CHECK(thrd_join(retire_thread,NULL)==thrd_success);
    IO24_CHECK(acquire.result&&acquire.length==1&&acquire.speed[0]==HighSpeed&&retire.result&&fake.release_ioctls==1&&!fake.device_closes&&counts.allocations==counts.frees);
}

static void test_handles(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE root,associated=NULL,associated2=NULL,duplicate=(void *)(uintptr_t)1,issued[32];unsigned int frees_before,releases,baseline,i,j;

    check_bad_free(f,(void *)(uintptr_t)1);check_unreadable_admission(f,0);check_unreadable_admission(f,1);check_unreadable_admission(f,2);check_task5_initialize_allocations(f);
    if(!f->associated||!f->free_handle||!f->initialize) return;
    fake_reset();IO24_CHECK(!f->associated(NULL,0,&associated)&&fake.last_error==ERROR_INVALID_HANDLE&&associated==NULL);
    if(!initialize_three_interface_handle(f,&root)) return;
    frees_before=counts.frees;
    associated=(void *)(uintptr_t)1;IO24_CHECK(!f->associated(root,0,NULL)&&fake.last_error==ERROR_INVALID_PARAMETER);
    IO24_CHECK(f->associated(root,0,&associated)&&associated&&associated!=INVALID_HANDLE_VALUE&&associated!=root);
    IO24_CHECK(f->associated(root,1,&associated2)&&associated2&&associated2!=INVALID_HANDLE_VALUE&&associated2!=root&&associated2!=associated);
    duplicate=(void *)(uintptr_t)1;IO24_CHECK(!f->associated(root,0,&duplicate)&&duplicate==NULL&&fake.last_error==ERROR_ALREADY_EXISTS);
    duplicate=(void *)(uintptr_t)1;IO24_CHECK(!f->associated(root,1,&duplicate)&&duplicate==NULL&&fake.last_error==ERROR_ALREADY_EXISTS);
    duplicate=(void *)(uintptr_t)1;IO24_CHECK(!f->associated(root,2,&duplicate)&&duplicate==NULL&&fake.last_error==ERROR_NO_MORE_ITEMS);
    duplicate=(void *)(uintptr_t)1;IO24_CHECK(!f->associated(root,UCHAR_MAX,&duplicate)&&duplicate==NULL&&fake.last_error==ERROR_INVALID_PARAMETER);
    duplicate=(void *)(uintptr_t)1;IO24_CHECK(!f->associated(associated,0,&duplicate)&&duplicate==NULL&&fake.last_error==ERROR_INVALID_PARAMETER);
    if(f->descriptor&&f->query){ULONG length=1;uint8_t byte=0;IO24_CHECK(!f->descriptor(associated,1,0,0,&byte,1,&length)&&fake.last_error==ERROR_INVALID_PARAMETER&&length==0);length=1;IO24_CHECK(!f->query(associated,DEVICE_SPEED,&length,&byte)&&fake.last_error==ERROR_INVALID_PARAMETER&&length==1);length=1;IO24_CHECK(!f->descriptor(associated2,1,0,0,&byte,1,&length)&&fake.last_error==ERROR_INVALID_PARAMETER&&length==0);length=1;IO24_CHECK(!f->query(associated2,DEVICE_SPEED,&length,&byte)&&fake.last_error==ERROR_INVALID_PARAMETER&&length==1);}
    /* Reissuing each slot independently detects a shifted or swapped root slot map. */
    IO24_CHECK(f->free_handle(associated));duplicate=NULL;IO24_CHECK(f->associated(root,0,&duplicate)&&duplicate&&duplicate!=associated);associated=duplicate;
    IO24_CHECK(f->free_handle(associated2));duplicate=NULL;IO24_CHECK(f->associated(root,1,&duplicate)&&duplicate&&duplicate!=associated2);associated2=duplicate;
    releases=fake.release_ioctls;IO24_CHECK(f->free_handle(root));IO24_CHECK(fake.release_ioctls==releases);
    check_bad_free(f,root);
    check_stale_admission(f,root,0);check_stale_admission(f,root,1);check_stale_admission(f,root,2);
    IO24_CHECK(f->free_handle(associated)&&f->free_handle(associated2));IO24_CHECK(fake.release_ioctls==releases+1&&counts.frees>=frees_before+3&&!fake.device_closes);
    fake_reset();if(!initialize_two_interface_handle(f,&root))return;associated=NULL;IO24_CHECK(f->associated(root,0,&associated));
    releases=fake.release_ioctls;IO24_CHECK(f->free_handle(associated));IO24_CHECK(fake.release_ioctls==releases);IO24_CHECK(f->free_handle(root));
    IO24_CHECK(fake.release_ioctls==releases+1&&!fake.device_closes);
    fake_reset();if(!initialize_two_interface_handle(f,&root))return;baseline=counts.allocations-counts.frees;
    for(i=0;i<32;++i){associated=NULL;IO24_CHECK(f->associated(root,0,&associated)&&associated&&associated!=INVALID_HANDLE_VALUE);for(j=0;j<i;++j)IO24_CHECK(associated!=issued[j]);issued[i]=associated;IO24_CHECK(f->free_handle(associated));IO24_CHECK(counts.allocations-counts.frees==baseline&&fake.release_ioctls==0);}
    IO24_CHECK(f->free_handle(root)&&fake.release_ioctls==1&&counts.allocations==counts.frees&&!fake.device_closes);
    duplicate=root;fake_reset();if(!initialize_two_interface_handle(f,&root))return;IO24_CHECK(root!=duplicate);for(i=0;i<32;++i)IO24_CHECK(root!=issued[i]);check_bad_free(f,duplicate);check_stale_admission(f,duplicate,0);check_stale_admission(f,duplicate,1);check_stale_admission(f,duplicate,2);check_bad_free(f,issued[0]);check_stale_admission(f,issued[0],0);IO24_CHECK(f->free_handle(root)&&fake.release_ioctls==1&&counts.allocations==counts.frees&&!fake.device_closes);
    fake_reset();if(!initialize_two_interface_handle(f,&root))return;test_acquire_before_free(f,root);
    fake_reset();if(!initialize_two_interface_handle(f,&root))return;fake.alloc_fail_at=fake.alloc_attempts+1;associated=(void *)(uintptr_t)1;
    IO24_CHECK(!f->associated(root,0,&associated)&&associated==NULL&&fake.last_error==ERROR_NOT_ENOUGH_MEMORY);IO24_CHECK(f->free_handle(root)&&fake.release_ioctls==1&&counts.allocations==counts.frees);
}

/* This uses the real DLL entry point and the ordinary fake DeviceIoControl
 * boundary.  A text scan or a copied request builder cannot satisfy it. */
static void test_alternate(const struct functions *f)
{
    WINUSB_INTERFACE_HANDLE root = NULL, associated = NULL, associated2 = NULL;
    const struct fake_event *event;
    unsigned int submits;

    if (!f->initialize || !f->free_handle || !f->set_alt) return;
    fake_reset();
    IO24_CHECK(!f->set_alt(NULL, 1) && fake.last_error == ERROR_INVALID_HANDLE);
    if (!initialize_handle(f, &root)) return;
    submits = counts.submits;
    IO24_CHECK(f->set_alt(root, 1));
    IO24_CHECK(counts.submits == submits + 1);
    event = find_ioctl_after(submits ? submits - 1 : 0, IO24_IOCTL_SET_ALTERNATE);
    IO24_CHECK(event && event->in_length == sizeof(struct io24_wire_alternate) &&
            event->out_length == 0 && event->typed_request);
    if (event)
    {
        check_header(event, sizeof(struct io24_wire_alternate), UINT64_C(0x1122334455667788), 0);
        IO24_CHECK(event->request.alternate.alternate_setting == 1 &&
                event->request.alternate.reserved == 0);
    }
    submits = counts.submits;
    IO24_CHECK(f->set_alt(root, 0) && counts.submits == submits + 1);
    submits = counts.submits;
    IO24_CHECK(!f->set_alt(root, 2) && fake.last_error == ERROR_INVALID_PARAMETER &&
            counts.submits == submits);
    IO24_CHECK(f->free_handle(root));
    IO24_CHECK(!f->set_alt(root, 1) && fake.last_error == ERROR_INVALID_HANDLE);

    /* R71: the real opaque associated handles must carry their distinct
     * stored interface indices into the actual private request. */
    fake_reset(); fake.three_interface_fixture = TRUE;
    if (!initialize_handle(f, &root)) return;
    IO24_CHECK(f->associated(root, 0, &associated) && associated);
    IO24_CHECK(f->associated(root, 1, &associated2) && associated2);
    submits = counts.submits;
    {
        unsigned int event_start = fake.event_count;
    IO24_CHECK(f->set_alt(associated, 0) && counts.submits == submits + 1);
    event = find_ioctl_after(event_start, IO24_IOCTL_SET_ALTERNATE);
    IO24_CHECK(event && event->request.alternate.request.interface_index == 1);
    }
    submits = counts.submits;
    {
        unsigned int event_start = fake.event_count;
    IO24_CHECK(f->set_alt(associated2, 0) && counts.submits == submits + 1);
    event = find_ioctl_after(event_start, IO24_IOCTL_SET_ALTERNATE);
    IO24_CHECK(event && event->request.alternate.request.interface_index == 2);
    }
    IO24_CHECK(f->free_handle(associated) && f->free_handle(associated2) &&
            f->free_handle(root));
    IO24_CHECK(fake.release_ioctls == 1 && fake.event_creates == fake.event_closes &&
            counts.allocations == counts.frees);

    /* Every submit schedule must acquire/release one root reference, close
     * its event, and leave the eventual final root release balanced. */
    fake_reset();
    if (!initialize_handle(f, &root)) return;
    submits = counts.submits;
    fake.private_call_count = 1;
    fake.private_call[0].pending = FALSE;
    fake.private_call[0].result = FALSE;
    fake.private_call[0].error = ERROR_ACCESS_DENIED;
    IO24_CHECK(!f->set_alt(root, 1) && fake.last_error == ERROR_ACCESS_DENIED &&
            counts.submits == submits + 1);
    IO24_CHECK(f->free_handle(root));
    IO24_CHECK(fake.release_ioctls == 1 && fake.event_creates == fake.event_closes &&
            counts.allocations == counts.frees);

    fake_reset();
    if (!initialize_handle(f, &root)) return;
    submits = counts.submits;
    fake.private_call_count = 1;
    fake.private_call[0].pending = TRUE;
    fake.private_call[0].completion_result = FALSE;
    fake.private_call[0].completion_error = ERROR_ACCESS_DENIED;
    IO24_CHECK(!f->set_alt(root, 1) && fake.last_error == ERROR_ACCESS_DENIED &&
            counts.submits == submits + 1 && counts.completions == 1);
    IO24_CHECK(f->free_handle(root));
    IO24_CHECK(fake.release_ioctls == 1 && fake.event_creates == fake.event_closes &&
            counts.allocations == counts.frees);

    fake_reset();
    if (!initialize_handle(f, &root)) return;
    submits = counts.submits;
    fake.private_call_count = 1;
    fake.private_call[0].pending = TRUE;
    fake.wait_result = WAIT_FAILED;
    fake.wait_error = ERROR_INVALID_HANDLE;
    IO24_CHECK(!f->set_alt(root, 1) && fake.last_error == ERROR_INVALID_HANDLE &&
            counts.submits == submits + 1 && counts.completions == 0);
    IO24_CHECK(f->free_handle(root));
    IO24_CHECK(fake.release_ioctls == 1 && fake.event_creates == fake.event_closes &&
            counts.allocations == counts.frees);
}

static void test_descriptors(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE h;struct guarded_buffer g;struct guarded_configuration_buffer configuration;const struct fake_event *event;uint8_t speed[4];ULONG n,sl;unsigned int submits,start;BOOL ok;

    if(!f->descriptor||!f->query||!f->associated||!f->free_handle||!f->initialize) return;
    fake_reset();if(!initialize_handle(f,&h))return;submits=counts.submits;
    n=IO24_LENGTH_SENTINEL;IO24_CHECK(!f->descriptor(NULL,1,0,0,g.bytes,sizeof(g.bytes),&n)&&fake.last_error==ERROR_INVALID_HANDLE&&n==0);
    sl=sizeof(speed);IO24_CHECK(!f->query(NULL,DEVICE_SPEED,&sl,speed)&&fake.last_error==ERROR_INVALID_HANDLE&&sl==sizeof(speed));
    memset(speed,0x6d,sizeof(speed));sl=sizeof(speed);ok=f->query(h,DEVICE_SPEED,&sl,speed);IO24_CHECK(ok&&sl==1&&speed[0]==HighSpeed&&bytes_equal(speed+1,3,0x6d));
    sl=0;memset(speed,0x6d,sizeof(speed));IO24_CHECK(!f->query(h,DEVICE_SPEED,&sl,speed)&&fake.last_error==ERROR_INSUFFICIENT_BUFFER&&sl==1&&bytes_equal(speed,sizeof(speed),0x6d));
    sl=sizeof(speed);IO24_CHECK(!f->query(h,2,&sl,speed)&&fake.last_error==ERROR_INVALID_PARAMETER&&sl==sizeof(speed));
    sl=sizeof(speed);IO24_CHECK(!f->query(h,DEVICE_SPEED,NULL,speed)&&fake.last_error==ERROR_INVALID_PARAMETER&&sl==sizeof(speed));
    sl=sizeof(speed);IO24_CHECK(!f->query(h,DEVICE_SPEED,&sl,NULL)&&fake.last_error==ERROR_INVALID_PARAMETER&&sl==sizeof(speed));
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->descriptor(h,1,0,0,g.bytes,sizeof(g.bytes),&n);IO24_CHECK(ok&&n==sizeof(io24_device_descriptor)&&!memcmp(g.bytes,io24_device_descriptor,n)&&bytes_equal(g.bytes+n,sizeof(g.bytes)-n,GUARD_BYTE));check_buffer_guards(&g);
    guard_configuration_buffer_reset(&configuration,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;ok=f->descriptor(h,2,0,0,configuration.bytes,sizeof(configuration.bytes),&n);IO24_CHECK(ok&&n==sizeof(io24_mi05_configuration)&&!memcmp(configuration.bytes,io24_mi05_configuration,n)&&bytes_equal(configuration.bytes+n,sizeof(configuration.bytes)-n,GUARD_BYTE));check_configuration_buffer_guards(&configuration);
    guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;IO24_CHECK(!f->descriptor(h,1,0,0,g.bytes,sizeof(io24_device_descriptor)-1,&n)&&fake.last_error==ERROR_INSUFFICIENT_BUFFER&&n==0&&bytes_equal(g.bytes,sizeof(g.bytes),GUARD_BYTE));
    n=IO24_LENGTH_SENTINEL;IO24_CHECK(!f->descriptor(h,1,0,0,NULL,sizeof(io24_device_descriptor),&n)&&fake.last_error==ERROR_INVALID_PARAMETER&&n==0);
    guard_buffer_reset(&g,GUARD_BYTE);IO24_CHECK(!f->descriptor(h,1,0,0,g.bytes,sizeof(g.bytes),NULL)&&fake.last_error==ERROR_INVALID_PARAMETER&&bytes_equal(g.bytes,sizeof(g.bytes),GUARD_BYTE));check_buffer_guards(&g);
    n=IO24_LENGTH_SENTINEL;IO24_CHECK(!f->descriptor(h,1,1,0,g.bytes,sizeof(g.bytes),&n)&&fake.last_error==ERROR_INVALID_PARAMETER&&n==0);
    n=IO24_LENGTH_SENTINEL;IO24_CHECK(!f->descriptor(h,1,0,0x409,g.bytes,sizeof(g.bytes),&n)&&fake.last_error==ERROR_INVALID_PARAMETER&&n==0);
    /* Task 9 changes the retained public contract: noncached descriptors
     * route through GET_DESCRIPTOR rather than ending at NOT_SUPPORTED. */
    fake.descriptor_response_length=sizeof(io24_string_descriptor_response);start=fake.event_count;guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;
    IO24_CHECK(f->descriptor(h,3,1,0x409,g.bytes,sizeof(g.bytes),&n)&&n==sizeof(io24_string_descriptor_response));
    event=find_ioctl_after(start,IO24_IOCTL_DESCRIPTOR);IO24_CHECK(event&&counts.submits==submits+1);
    if(event){check_header(event,sizeof(struct io24_wire_descriptor),UINT64_C(0x1122334455667788),0);IO24_CHECK(event->request.descriptor.type==3&&event->request.descriptor.index==1&&event->request.descriptor.language==0x409&&event->request.descriptor.length==sizeof(g.bytes));}
    fake.descriptor_response_length=12;start=fake.event_count;guard_buffer_reset(&g,GUARD_BYTE);n=IO24_LENGTH_SENTINEL;
    IO24_CHECK(f->descriptor(h,0x22,2,0x409,g.bytes,sizeof(g.bytes),&n)&&n==12);
    event=find_ioctl_after(start,IO24_IOCTL_DESCRIPTOR);IO24_CHECK(event&&counts.submits==submits+2);
    if(event)IO24_CHECK(event->request.descriptor.type==0x22&&event->request.descriptor.index==2&&event->request.descriptor.language==0x409&&event->request.descriptor.length==sizeof(g.bytes));
    IO24_CHECK(f->free_handle(h)&&fake.release_ioctls==1&&!fake.device_closes);
    fake_reset();fake.low_speed_fixture=TRUE;if(!initialize_handle(f,&h))return;sl=sizeof(speed);memset(speed,0x6d,sizeof(speed));IO24_CHECK(f->query(h,DEVICE_SPEED,&sl,speed)&&sl==1&&speed[0]==LowSpeed&&bytes_equal(speed+1,3,0x6d));IO24_CHECK(f->free_handle(h));
}
static void check_policy_submit(unsigned int submits, unsigned int event_start, DWORD code,
        UCHAR pipe, ULONG policy, ULONG length, ULONG value, ULONG response_value, const ULONG *caller_length)
{
    const struct fake_event *event = find_ioctl_after(event_start, code);
    IO24_CHECK(counts.submits == submits + 1);
    IO24_CHECK(event && event->typed_request && event->handle == IO24_FILE_HANDLE);
    if (!event) return;
    check_header(event, sizeof(struct io24_wire_policy), UINT64_C(0x1122334455667788), 0);
    IO24_CHECK(event->request.policy.pipe_id == pipe && event->request.policy.policy_id == policy &&
            event->request.policy.value_length == length && event->request.policy.value == value);
    IO24_CHECK(event->in_length == sizeof(struct io24_wire_policy));
    IO24_CHECK(code == IO24_IOCTL_GET_POLICY ? event->out_length == sizeof(struct io24_wire_policy) :
            event->out_length == 0);
    if (code == IO24_IOCTL_GET_POLICY)
    {
        struct io24_wire_policy response;
        IO24_CHECK(event->bytes_returned_pointer && event->bytes_returned_pointer != caller_length);
        IO24_CHECK(event->output_saved >= sizeof(response) && event->returned_bytes == sizeof(response));
        if (event->output_saved < sizeof(response)) return;
        memcpy(&response, event->output_after, sizeof(response));
        IO24_CHECK(response.request.size == sizeof(response) && response.request.version == IO24_ABI_VERSION &&
                response.request.session == UINT64_C(0x1122334455667788) && response.request.interface_index == 0 &&
                response.request.reserved == 0 && response.pipe_id == pipe && response.policy_id == policy &&
                response.value_length == length && response.value == response_value);
    }
}

static void check_policy_get_capacity_submit(unsigned int submits, unsigned int event_start,
        UCHAR pipe, ULONG policy, ULONG capacity, ULONG required, ULONG response_value, const ULONG *caller_length)
{
    const struct fake_event *event = find_ioctl_after(event_start, IO24_IOCTL_GET_POLICY);
    struct io24_wire_policy response;
    IO24_CHECK(counts.submits == submits + 1);
    IO24_CHECK(event && event->typed_request && event->handle == IO24_FILE_HANDLE &&
            event->out_length == sizeof(response) && event->output_saved >= sizeof(response) &&
            event->returned_bytes == sizeof(response) && event->bytes_returned_pointer &&
            event->bytes_returned_pointer != caller_length);
    if (!event || event->output_saved < sizeof(response)) return;
    check_header(event, sizeof(response), UINT64_C(0x1122334455667788), 0);
    IO24_CHECK(event->request.policy.pipe_id == pipe && event->request.policy.policy_id == policy &&
            event->request.policy.value_length == capacity && event->request.policy.value == 0);
    memcpy(&response, event->output_after, sizeof(response));
    IO24_CHECK(response.request.size == sizeof(response) && response.request.version == IO24_ABI_VERSION &&
            response.request.session == UINT64_C(0x1122334455667788) && response.request.interface_index == 0 &&
            response.request.reserved == 0 && response.pipe_id == pipe && response.policy_id == policy &&
            response.value_length == required && response.value == response_value);
}

static void test_policy_associated_route(const struct functions *f)
{
    WINUSB_INTERFACE_HANDLE root = NULL, associated = NULL;
    struct guarded_policy_value value;
    const struct fake_event *event;
    struct io24_wire_policy response;
    ULONG length, stored = 0;
    unsigned int submits, event_start;
    uint8_t original[IO24_POLICY_PROBE_CAPACITY];

    if (!f->initialize || !f->free_handle || !f->associated || !f->set_alt || !f->set_policy || !f->get_policy) return;
    fake_reset(); fake.policy_associated_fixture = TRUE;
    if (!initialize_handle(f, &root)) return;
    IO24_CHECK(f->associated(root, 0, &associated) && associated && associated != root);
    submits = counts.submits;
    IO24_CHECK(f->set_alt(root, 1) && counts.submits == submits + 1);
    submits = counts.submits;
    IO24_CHECK(f->set_alt(associated, 1) && counts.submits == submits + 1);

    /* Neither opaque handle may route a policy operation through the other
     * interface's current pipe. */
    for (unsigned int i = 0; i < 2; ++i)
    {
        WINUSB_INTERFACE_HANDLE target = i ? associated : root;
        UCHAR foreign_pipe = i ? 0x81 : 0x83;
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        value.bytes[0] = 1; memcpy(original, value.bytes, sizeof(original)); submits = counts.submits;
        IO24_CHECK(!f->set_policy(target, foreign_pipe, RAW_IO, 1, value.bytes) &&
                fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
                !memcmp(value.bytes, original, sizeof(original)) && value.before == IO24_GUARD_WORD &&
                value.after == IO24_GUARD_WORD);
        length = 1; submits = counts.submits;
        IO24_CHECK(!f->get_policy(target, foreign_pipe, RAW_IO, &length, value.bytes) &&
                fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits && length == 1 &&
                !memcmp(value.bytes, original, sizeof(original)) && value.before == IO24_GUARD_WORD &&
                value.after == IO24_GUARD_WORD);
    }

    value.before = value.after = IO24_GUARD_WORD;
    memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes)); value.bytes[0] = 1;
    submits = counts.submits; event_start = fake.event_count;
    IO24_CHECK(f->set_policy(associated, 0x83, RAW_IO, 1, value.bytes) &&
            value.bytes[0] == 1 && bytes_equal(value.bytes + 1, sizeof(value.bytes) - 1,
            IO24_POLICY_STORAGE_SENTINEL) && value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    event = find_ioctl_after(event_start, IO24_IOCTL_SET_POLICY);
    IO24_CHECK(counts.submits == submits + 1 && event && event->typed_request);
    if (event)
    {
        check_header(event, sizeof(struct io24_wire_policy), UINT64_C(0x1122334455667788), 1);
        IO24_CHECK(event->request.policy.pipe_id == 0x83 && event->request.policy.policy_id == RAW_IO &&
                event->request.policy.value_length == 1 && event->request.policy.value == 1 && event->out_length == 0);
    }

    value.before = value.after = IO24_GUARD_WORD;
    memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    length = 2; submits = counts.submits; event_start = fake.event_count;
    IO24_CHECK(f->get_policy(associated, 0x83, RAW_IO, &length, value.bytes));
    memcpy(&stored, value.bytes, 1);
    event = find_ioctl_after(event_start, IO24_IOCTL_GET_POLICY);
    IO24_CHECK(counts.submits == submits + 1 && length == 1 && stored == 1 &&
            bytes_equal(value.bytes + 1, sizeof(value.bytes) - 1, IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD && event && event->typed_request &&
            event->out_length == sizeof(response) && event->output_saved >= sizeof(response) &&
            event->returned_bytes == sizeof(response) && event->bytes_returned_pointer &&
            event->bytes_returned_pointer != &length);
    if (event && event->output_saved >= sizeof(response))
    {
        check_header(event, sizeof(response), UINT64_C(0x1122334455667788), 1);
        IO24_CHECK(event->request.policy.pipe_id == 0x83 && event->request.policy.policy_id == RAW_IO &&
                event->request.policy.value_length == 2 && event->request.policy.value == 0);
        memcpy(&response, event->output_after, sizeof(response));
        IO24_CHECK(response.request.interface_index == 1 && response.pipe_id == 0x83 &&
                response.policy_id == RAW_IO && response.value_length == 1 && response.value == 1);
    }
    IO24_CHECK(f->free_handle(associated)); associated = NULL;
    IO24_CHECK(f->associated(root, 0, &associated) && associated);
    value.before = value.after = IO24_GUARD_WORD; memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    length = 1; IO24_CHECK(f->get_policy(associated, 0x83, RAW_IO, &length, value.bytes) && length == 1 &&
            value.bytes[0] == 1 && value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    IO24_CHECK(f->free_handle(associated) && f->free_handle(root) && fake.release_ioctls == 1 &&
            counts.allocations == counts.frees && !fake.device_closes);
}

static void test_policy_response_validation(const struct functions *f)
{
    WINUSB_INTERFACE_HANDLE h = NULL;
    struct guarded_policy_value value;
    ULONG length;
    unsigned int mutation, submits;

    if (!f->initialize || !f->free_handle || !f->set_alt || !f->get_policy) return;
    for (mutation = POLICY_RESPONSE_SHORT; mutation <= POLICY_RESPONSE_BOOLEAN_VALUE; ++mutation)
    {
        ULONG policy = mutation == POLICY_RESPONSE_BOOLEAN_VALUE ? ALLOW_PARTIAL_READS : MAXIMUM_TRANSFER_SIZE;
        ULONG capacity = mutation == POLICY_RESPONSE_BOOLEAN_VALUE ? 1 : 4;
        fake_reset();
        if (!initialize_handle(f, &h)) return;
        IO24_CHECK(f->set_alt(h, 1));
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        length = capacity; submits = counts.submits; fake.policy_response_mutation = mutation;
        IO24_CHECK(!f->get_policy(h, 0x81, policy, &length, value.bytes) &&
                fake.last_error == ERROR_BAD_DEVICE && counts.submits == submits + 1 && length == capacity &&
                bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
                value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
        fake.policy_response_mutation = POLICY_RESPONSE_VALID;
        IO24_CHECK(f->free_handle(h) && fake.release_ioctls == 1 &&
                counts.allocations == counts.frees && !fake.device_closes);
        h = NULL;
    }
    fake_reset();
    if (!initialize_handle(f, &h)) return;
    IO24_CHECK(f->set_alt(h, 1));
    value.before = value.after = IO24_GUARD_WORD;
    memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    value.bytes[0] = 1; length = 1; submits = counts.submits; fake.policy_set_return_bytes = 1;
    IO24_CHECK(!f->set_policy(h, 0x81, RAW_IO, 1, value.bytes) && fake.last_error == ERROR_BAD_DEVICE &&
            counts.submits == submits + 1 && length == 1 && value.bytes[0] == 1 &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    fake.policy_set_return_bytes = 0;
    IO24_CHECK(f->free_handle(h) && fake.release_ioctls == 1 && counts.allocations == counts.frees && !fake.device_closes);
}

static void test_policy_snapshot_stability(const struct functions *f)
{
    WINUSB_INTERFACE_HANDLE h = NULL;
    const struct fake_event *full = NULL;
    uint8_t snapshot[512], value = 0;
    ULONG length = 1;
    unsigned int i;

    if (!f->initialize || !f->free_handle || !f->set_alt || !f->get_policy) return;
    fake_reset();
    if (!initialize_handle(f, &h)) return;
    for (i = 0; i < fake.event_count; ++i)
        if (fake.events[i].kind == EVENT_IOCTL && fake.events[i].code == IO24_IOCTL_INITIALIZE &&
                fake.events[i].out_length > sizeof(struct wine_winusb_snapshot)) full = &fake.events[i];
    IO24_CHECK(full && full->pointer && full->out_length <= sizeof(snapshot) && full->output_saved == full->out_length);
    if (!full) { f->free_handle(h); return; }
    memcpy(snapshot, full->pointer, full->out_length);
    IO24_CHECK(!((struct wine_winusb_snapshot *)snapshot)->reserved[0] &&
            !((struct wine_winusb_snapshot *)snapshot)->reserved[1]);
    IO24_CHECK(f->set_alt(h, 1));
    IO24_CHECK(f->get_policy(h, 0x81, ALLOW_PARTIAL_READS, &length, &value));
    IO24_CHECK(!memcmp(snapshot, full->pointer, full->out_length) &&
            !((struct wine_winusb_snapshot *)full->pointer)->reserved[0] &&
            !((struct wine_winusb_snapshot *)full->pointer)->reserved[1]);
    IO24_CHECK(f->free_handle(h) && fake.release_ioctls == 1 && counts.allocations == counts.frees);
}

static void test_policy_alternate_serialization(const struct functions *f)
{
    WINUSB_INTERFACE_HANDLE h = NULL;
    struct io24_policy_alt_thread alternate = {.functions=f};
    struct io24_policy_get_thread policy = {.functions=f};
    thrd_t alternate_thread, policy_thread;
    unsigned int spins, submits;

    if (!f->initialize || !f->free_handle || !f->set_alt || !f->get_policy) return;
    fake_reset();
    if (!initialize_handle(f, &h)) return;
    alternate.handle = policy.handle = h;
    atomic_init(&alternate.started,0); atomic_init(&alternate.done,0);
    atomic_init(&policy.started,0); atomic_init(&policy.done,0);
    atomic_store(&io24_policy_alt_gate_enabled,1);
    IO24_CHECK(thrd_create(&alternate_thread,io24_policy_alt_thread_main,&alternate)==thrd_success);
    for(spins=0;spins<1000000&&!atomic_load(&io24_policy_alt_gate_entered);++spins)thrd_yield();
    IO24_CHECK(atomic_load(&io24_policy_alt_gate_entered));
    submits=counts.submits;
    IO24_CHECK(thrd_create(&policy_thread,io24_policy_get_thread_main,&policy)==thrd_success);
    for(spins=0;spins<1000000&&!atomic_load(&policy.started);++spins)thrd_yield();
    for(spins=0;spins<1000000;++spins)thrd_yield();
    IO24_CHECK(!atomic_load(&alternate.done) && !atomic_load(&policy.done) && counts.submits==submits);
    atomic_store(&io24_policy_alt_gate_enabled,0);atomic_store(&io24_policy_alt_gate_release,1);
    IO24_CHECK(thrd_join(alternate_thread,NULL)==thrd_success&&thrd_join(policy_thread,NULL)==thrd_success);
    IO24_CHECK(alternate.result&&policy.result&&policy.length==4&&policy.value==4u*1024u*1024u&&counts.submits==submits+1);
    IO24_CHECK(f->free_handle(h)&&fake.release_ioctls==1&&counts.allocations==counts.frees&&!fake.device_closes);
}

static void test_policy(const struct functions *f)
{
    static const struct { UCHAR pipe; ULONG policy, length, value; } defaults[] = {
        {0x01, PIPE_TRANSFER_TIMEOUT, 4, 0}, {0x01, MAXIMUM_TRANSFER_SIZE, 4, 4u * 1024u * 1024u},
        {0x01, RESET_PIPE_ON_RESUME, 1, 0}, {0x01, SHORT_PACKET_TERMINATE, 1, 0},
        {0x81, PIPE_TRANSFER_TIMEOUT, 4, 0}, {0x81, MAXIMUM_TRANSFER_SIZE, 4, 4u * 1024u * 1024u},
        {0x81, RESET_PIPE_ON_RESUME, 1, 0}, {0x81, AUTO_CLEAR_STALL, 1, 0},
        {0x81, IGNORE_SHORT_PACKETS, 1, 0}, {0x81, ALLOW_PARTIAL_READS, 1, 1},
        {0x81, AUTO_FLUSH, 1, 0}, {0x81, RAW_IO, 1, 0}
    };
    static const struct { UCHAR pipe; ULONG policy, length, value; } writable[] = {
        {0x01, SHORT_PACKET_TERMINATE, 1, 0}, {0x01, RESET_PIPE_ON_RESUME, 1, 0},
        {0x81, AUTO_CLEAR_STALL, 1, 0}, {0x81, IGNORE_SHORT_PACKETS, 1, 0},
        {0x81, ALLOW_PARTIAL_READS, 1, 0}, {0x81, ALLOW_PARTIAL_READS, 1, 1},
        {0x81, AUTO_FLUSH, 1, 0}, {0x81, RAW_IO, 1, 0}, {0x81, RAW_IO, 1, 1}
    };
    static const struct { UCHAR pipe; ULONG policy, length, value; } supported_zero[] = {
        {0x01, PIPE_TRANSFER_TIMEOUT, 4, 0}, {0x01, RESET_PIPE_ON_RESUME, 1, 0},
        {0x81, PIPE_TRANSFER_TIMEOUT, 4, 0}, {0x81, RESET_PIPE_ON_RESUME, 1, 0}
    };
    WINUSB_INTERFACE_HANDLE h = NULL;
    struct guarded_policy_value value;
    unsigned int i, submits, event_start;
    ULONG length, stored;
    uint8_t original[IO24_POLICY_PROBE_CAPACITY];
    BOOL ok, have_lifecycle = f->initialize && f->free_handle && f->set_alt;
    BOOL have_policy = f->set_policy && f->get_policy;

    /* Symbol absence is a feature failure, never evidence that policy behavior ran.
     * Still exercise every safe public prerequisite and retain the complete case map
     * below behind the actual public boundary. */
    fake_reset();
    IO24_CHECK(have_lifecycle);
    if (!have_lifecycle) { IO24_CHECK(have_policy); return; }
    IO24_CHECK(initialize_handle(f, &h));
    if (!h) { IO24_CHECK(have_policy); return; }

    if (!have_policy)
    {
        submits = counts.submits;
        IO24_CHECK(f->set_alt(h, 1) && counts.submits == submits + 1);
        IO24_CHECK(f->free_handle(h));
        IO24_CHECK(have_policy);
        return;
    }

    /* Before alternate 1 no PipeID is a wildcard, and invalid admission cannot
     * touch the caller buffers, lengths, or private transport. */
    for (i = 0; i < 3; ++i)
    {
        UCHAR pipe = (UCHAR[]){0, 0x01, 0x81}[i];
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        length = 1; submits = counts.submits;
        IO24_CHECK(!f->set_policy(h, pipe, RAW_IO, length, value.bytes) &&
                fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
                bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
                value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
        length = sizeof(value.bytes); submits = counts.submits;
        IO24_CHECK(!f->get_policy(h, pipe, RAW_IO, &length, value.bytes) &&
                fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
                length == sizeof(value.bytes) && bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
                value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    }

    submits = counts.submits;
    IO24_CHECK(f->set_alt(h, 1) && counts.submits == submits + 1);

    /* Handle and pointer admission is local: it cannot submit or mutate any
     * caller-owned length/value storage. */
    value.before = value.after = IO24_GUARD_WORD;
    memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    length = 1; submits = counts.submits;
    IO24_CHECK(!f->get_policy(NULL, 0x81, ALLOW_PARTIAL_READS, &length, value.bytes) &&
            fake.last_error == ERROR_INVALID_HANDLE && counts.submits == submits && length == 1 &&
            bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    submits = counts.submits;
    IO24_CHECK(!f->set_policy(NULL, 0x81, RAW_IO, 1, value.bytes) &&
            fake.last_error == ERROR_INVALID_HANDLE && counts.submits == submits &&
            bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    submits = counts.submits;
    IO24_CHECK(!f->get_policy(h, 0x81, ALLOW_PARTIAL_READS, NULL, value.bytes) &&
            fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
            bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    length = 1; submits = counts.submits;
    IO24_CHECK(!f->get_policy(h, 0x81, ALLOW_PARTIAL_READS, &length, NULL) &&
            fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits && length == 1 &&
            bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    submits = counts.submits;
    IO24_CHECK(!f->set_policy(h, 0x81, RAW_IO, 1, NULL) &&
            fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
            bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);

    /* Defaults bind actual public ValueLength/value readback, including the 4 MiB cap. */
    for (i = 0; i < sizeof(defaults) / sizeof(defaults[0]); ++i)
    {
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        length = defaults[i].length; submits = counts.submits; event_start = fake.event_count;
        ok = f->get_policy(h, defaults[i].pipe, defaults[i].policy, &length, value.bytes);
        stored = 0;
        memcpy(&stored, value.bytes, defaults[i].length);
        IO24_CHECK(ok && length == defaults[i].length && stored == defaults[i].value &&
                value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
        check_policy_submit(submits, event_start, IO24_IOCTL_GET_POLICY, defaults[i].pipe,
                defaults[i].policy, defaults[i].length, 0, defaults[i].value, &length);
    }

    /* Capacity zero and capacity-one-short report the exact required size, but
     * do not write a byte or cross either caller guard. */
    for (i = 0; i < 2; ++i)
    {
        unsigned int capacity;
        ULONG required = i ? 4 : 1, policy = i ? MAXIMUM_TRANSFER_SIZE : ALLOW_PARTIAL_READS;
        for (capacity = 0; capacity < 2; ++capacity)
        {
            value.before = value.after = IO24_GUARD_WORD;
            memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
            length = capacity ? required - 1 : 0; submits = counts.submits;
            IO24_CHECK(!f->get_policy(h, 0x81, policy, &length, value.bytes) &&
                    fake.last_error == ERROR_INSUFFICIENT_BUFFER && length == required &&
                    counts.submits == submits && bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
                    value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
        }
    }

    for (i = 0; i < sizeof(writable) / sizeof(writable[0]); ++i)
    {
        submits = counts.submits; event_start = fake.event_count;
        IO24_CHECK(f->set_policy(h, writable[i].pipe, writable[i].policy, writable[i].length,
                (void *)&writable[i].value));
        check_policy_submit(submits, event_start, IO24_IOCTL_SET_POLICY, writable[i].pipe,
                writable[i].policy, writable[i].length, writable[i].value, 0, NULL);
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        length = writable[i].length; stored = 0; submits = counts.submits; event_start = fake.event_count;
        ok = f->get_policy(h, writable[i].pipe, writable[i].policy, &length, value.bytes);
        memcpy(&stored, value.bytes, writable[i].length);
        IO24_CHECK(ok && length == writable[i].length && stored == writable[i].value &&
                value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
        check_policy_submit(submits, event_start, IO24_IOCTL_GET_POLICY, writable[i].pipe,
                writable[i].policy, writable[i].length, 0, writable[i].value, &length);
    }

    /* Both current pipes admit timeout=0 and reset-on-resume=false, and their
     * subsequent public GETs prove the wrapper's state round trip. */
    for (i = 0; i < sizeof(supported_zero) / sizeof(supported_zero[0]); ++i)
    {
        submits = counts.submits; event_start = fake.event_count;
        IO24_CHECK(f->set_policy(h, supported_zero[i].pipe, supported_zero[i].policy,
                supported_zero[i].length, (void *)&supported_zero[i].value));
        check_policy_submit(submits, event_start, IO24_IOCTL_SET_POLICY, supported_zero[i].pipe,
                supported_zero[i].policy, supported_zero[i].length, 0, 0, NULL);
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        length = supported_zero[i].length; stored = 0; submits = counts.submits; event_start = fake.event_count;
        ok = f->get_policy(h, supported_zero[i].pipe, supported_zero[i].policy, &length, value.bytes);
        memcpy(&stored, value.bytes, supported_zero[i].length);
        IO24_CHECK(ok && length == supported_zero[i].length && stored == 0 &&
                value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
        check_policy_submit(submits, event_start, IO24_IOCTL_GET_POLICY, supported_zero[i].pipe,
                supported_zero[i].policy, supported_zero[i].length, 0, 0, &length);
    }

    /* Direction, read-only, unknown, and exact-size rejections preserve state and avoid submission. */
    for (i = 0; i < 6; ++i)
    {
        static const struct { UCHAR pipe; ULONG policy, length, value; } invalid[] = {
            {0x01, RAW_IO, 1, 1}, {0x81, SHORT_PACKET_TERMINATE, 1, 1},
            {0x01, MAXIMUM_TRANSFER_SIZE, 4, 0}, {0x81, MAXIMUM_TRANSFER_SIZE, 4, 0},
            {0x81, PIPE_TRANSFER_TIMEOUT, 1, 0}, {0x81, 0xfeedu, 1, 0}
        };
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        memcpy(value.bytes, &invalid[i].value, invalid[i].length);
        memcpy(original, value.bytes, sizeof(original)); submits = counts.submits;
        IO24_CHECK(!f->set_policy(h, invalid[i].pipe, invalid[i].policy, invalid[i].length,
                value.bytes) && counts.submits == submits && fake.last_error == ERROR_INVALID_PARAMETER &&
                !memcmp(value.bytes, original, sizeof(original)) && value.before == IO24_GUARD_WORD &&
                value.after == IO24_GUARD_WORD);
    }
    value.before = value.after = IO24_GUARD_WORD; memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    stored = 1; memcpy(value.bytes, &stored, sizeof(stored)); memcpy(original, value.bytes, sizeof(original)); submits = counts.submits;
    IO24_CHECK(!f->set_policy(h, 0x81, PIPE_TRANSFER_TIMEOUT, 4, value.bytes) &&
            fake.last_error == ERROR_NOT_SUPPORTED && counts.submits == submits && !memcmp(value.bytes, original, sizeof(original)) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);

    /* Every enabled prohibited setting is rejected before private submission. */
    for (i = 0; i < 8; ++i)
    {
        static const struct { UCHAR pipe; ULONG policy, length; } prohibited[] = {
            {0x01, SHORT_PACKET_TERMINATE, 1}, {0x01, PIPE_TRANSFER_TIMEOUT, 4},
            {0x01, RESET_PIPE_ON_RESUME, 1}, {0x81, PIPE_TRANSFER_TIMEOUT, 4},
            {0x81, RESET_PIPE_ON_RESUME, 1}, {0x81, AUTO_CLEAR_STALL, 1},
            {0x81, IGNORE_SHORT_PACKETS, 1}, {0x81, AUTO_FLUSH, 1}
        };
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        value.bytes[0] = 1; memcpy(original, value.bytes, sizeof(original)); submits = counts.submits;
        IO24_CHECK(!f->set_policy(h, prohibited[i].pipe, prohibited[i].policy, prohibited[i].length, value.bytes) &&
                fake.last_error == ERROR_NOT_SUPPORTED && counts.submits == submits &&
                !memcmp(value.bytes, original, sizeof(original)) && value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    }

    /* SET has exact value-size admission; GET's ValueLength is caller capacity. */
    for (i = 0; i < 4; ++i)
    {
        static const ULONG bad_lengths[] = {0, 1, 3, 5};
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        memcpy(original, value.bytes, sizeof(original)); submits = counts.submits;
        IO24_CHECK(!f->set_policy(h, 0x81, PIPE_TRANSFER_TIMEOUT, bad_lengths[i], value.bytes) &&
                fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
                !memcmp(value.bytes, original, sizeof(original)) && value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    }
    for (i = 0; i < 2; ++i)
    {
        static const ULONG bad_boolean_lengths[] = {0, 2};
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        memcpy(original, value.bytes, sizeof(original)); submits = counts.submits;
        IO24_CHECK(!f->set_policy(h, 0x81, RAW_IO, bad_boolean_lengths[i], value.bytes) &&
                fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
                !memcmp(value.bytes, original, sizeof(original)) && value.before == IO24_GUARD_WORD &&
                value.after == IO24_GUARD_WORD);
    }

    /* Oversized GET capacities are accepted.  Only the returned 1/4 bytes may
     * change, and ValueLength is rewritten to the exact returned size. */
    for (i = 0; i < 2; ++i)
    {
        ULONG required = i ? 4 : 1, policy = i ? MAXIMUM_TRANSFER_SIZE : ALLOW_PARTIAL_READS;
        ULONG expected = i ? 4u * 1024u * 1024u : 1;
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        length = required + 1; stored = 0; submits = counts.submits; event_start = fake.event_count;
        ok = f->get_policy(h, 0x81, policy, &length, value.bytes);
        memcpy(&stored, value.bytes, required);
        IO24_CHECK(ok && length == required && stored == expected &&
                bytes_equal(value.bytes + required, sizeof(value.bytes) - required, IO24_POLICY_STORAGE_SENTINEL) &&
                value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
        check_policy_get_capacity_submit(submits, event_start, 0x81, policy, required + 1, required, expected, &length);
    }
    value.before = value.after = IO24_GUARD_WORD;
    memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    length = 1; submits = counts.submits;
    IO24_CHECK(!f->get_policy(h, 0, ALLOW_PARTIAL_READS, &length, value.bytes) &&
            fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits && length == 1 &&
            bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    for (i = 0; i < 2; ++i)
    {
        UCHAR pipe = (UCHAR[]){0, 0x82}[i];
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        value.bytes[0] = 1; memcpy(original, value.bytes, sizeof(original)); submits = counts.submits;
        IO24_CHECK(!f->set_policy(h, pipe, RAW_IO, 1, value.bytes) &&
                fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
                !memcmp(value.bytes, original, sizeof(original)) && value.before == IO24_GUARD_WORD &&
                value.after == IO24_GUARD_WORD);
    }

    /* GET has the same direction, policy, and current-pipe admission boundary
     * as SET, but uses ValueLength as capacity.  It cannot rewrite caller
     * length/value on invalid admission. */
    for (i = 0; i < 5; ++i)
    {
        static const struct { UCHAR pipe; ULONG policy, length; } get_invalid[] = {
            {0x01, RAW_IO, 1}, {0x81, SHORT_PACKET_TERMINATE, 1}, {0x81, 0xfeedu, 1},
            {0, ALLOW_PARTIAL_READS, 1}, {0x82, ALLOW_PARTIAL_READS, 1}
        };
        value.before = value.after = IO24_GUARD_WORD;
        memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
        length = get_invalid[i].length; submits = counts.submits;
        IO24_CHECK(!f->get_policy(h, get_invalid[i].pipe, get_invalid[i].policy, &length, value.bytes) &&
                fake.last_error == ERROR_INVALID_PARAMETER && counts.submits == submits &&
                length == get_invalid[i].length && bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
                value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    }

    /* Alternate requests are observable at this boundary.  The stateful fake
     * models only returned transport records: these checks do not claim to
     * prove the kernel's authoritative reset/preservation implementation. */
    submits = counts.submits; IO24_CHECK(f->set_alt(h, 1) && counts.submits == submits + 1);
    value.before = value.after = IO24_GUARD_WORD; memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    length = 1; submits = counts.submits; event_start = fake.event_count;
    ok = f->get_policy(h, 0x81, ALLOW_PARTIAL_READS, &length, value.bytes); stored = 0; memcpy(&stored, value.bytes, 1);
    IO24_CHECK(ok && length == 1 && stored == 1 && value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    check_policy_submit(submits, event_start, IO24_IOCTL_GET_POLICY, 0x81, ALLOW_PARTIAL_READS, 1, 0, 1, &length);
    fake.private_call_count = 1; fake.private_call[0].result = FALSE; fake.private_call[0].error = ERROR_ACCESS_DENIED;
    submits = counts.submits; IO24_CHECK(!f->set_alt(h, 0) && fake.last_error == ERROR_ACCESS_DENIED && counts.submits == submits + 1);
    value.before = value.after = IO24_GUARD_WORD; memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    length = 1; IO24_CHECK(f->get_policy(h, 0x81, ALLOW_PARTIAL_READS, &length, value.bytes)); stored = 0; memcpy(&stored, value.bytes, 1);
    IO24_CHECK(length == 1 && stored == 1 && value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);

    /* A transport failure must leave public inputs intact; a failed alternate must
     * likewise retain the policy map.  These calls use the real DLL entry points. */
    value.before = value.after = IO24_GUARD_WORD;
    memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes));
    length = 4; fake.ioctl_result = FALSE; fake.ioctl_error = ERROR_ACCESS_DENIED; submits = counts.submits;
    IO24_CHECK(!f->get_policy(h, 0x81, MAXIMUM_TRANSFER_SIZE, &length, value.bytes) &&
            fake.last_error == ERROR_ACCESS_DENIED && counts.submits == submits + 1 && length == 4 &&
            bytes_equal(value.bytes, sizeof(value.bytes), IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    fake.ioctl_result = TRUE;
    value.before = value.after = IO24_GUARD_WORD;
    memset(value.bytes, IO24_POLICY_STORAGE_SENTINEL, sizeof(value.bytes)); value.bytes[0] = 1;
    submits = counts.submits; fake.ioctl_result = FALSE; fake.ioctl_error = ERROR_ACCESS_DENIED;
    IO24_CHECK(!f->set_policy(h, 0x81, RAW_IO, 1, value.bytes) && fake.last_error == ERROR_ACCESS_DENIED &&
            counts.submits == submits + 1 && value.bytes[0] == 1 &&
            bytes_equal(value.bytes + 1, sizeof(value.bytes) - 1, IO24_POLICY_STORAGE_SENTINEL) &&
            value.before == IO24_GUARD_WORD && value.after == IO24_GUARD_WORD);
    fake.ioctl_result = TRUE;
    if (f->free_handle) IO24_CHECK(f->free_handle(h));
    test_policy_response_validation(f);
    test_policy_snapshot_stability(f);
    test_policy_alternate_serialization(f);
    test_policy_associated_route(f);
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
/* Task 9 deliberately owns only descriptor fallback and generic control.
 * Pipe I/O, overlapped retrieval, and cancellation remain Task 10/12 work. */
static void test_task9_control_descriptor(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE root, associated_root, associated = NULL;
    struct guarded_buffer buffer;
    struct guarded_configuration_buffer configuration;
    WINUSB_SETUP_PACKET setup;
    const struct fake_event *event;
    ULONG length;
    unsigned int submits, start, i;
    uint8_t *large;
    static const struct { UCHAR request_type, request; USHORT value, index, length; DWORD code; }
        cases[] =
    {
        {0x80, 6, 0x0100, 0, 0, IO24_IOCTL_CONTROL_IN},       /* standard device */
        {0xa1, 1, 0x0203, 0xab9b, 1, IO24_IOCTL_CONTROL_IN},  /* class interface; low byte canonicalizes */
        {0xc3, 3, 0x0607, 0x0011, 4096, IO24_IOCTL_CONTROL_IN}/* vendor other; 0xe3 is reserved type */
    };

    if (!f->initialize || !f->descriptor || !f->free_handle) return;
    fake_reset();
    if (!initialize_handle(f, &root)) return;
    submits = counts.submits;
    guard_buffer_reset(&buffer, GUARD_BYTE); length=IO24_LENGTH_SENTINEL;
    IO24_CHECK(f->descriptor(root,1,0,0,buffer.bytes,sizeof(buffer.bytes),&length));
    IO24_CHECK(length==sizeof(io24_device_descriptor) && !memcmp(buffer.bytes,io24_device_descriptor,length));
    IO24_CHECK(counts.submits==submits); check_buffer_guards(&buffer);
    guard_configuration_buffer_reset(&configuration,GUARD_BYTE); length=IO24_LENGTH_SENTINEL;
    IO24_CHECK(f->descriptor(root,2,0,0,configuration.bytes,sizeof(configuration.bytes),&length));
    IO24_CHECK(length==sizeof(io24_mi05_configuration) && !memcmp(configuration.bytes,io24_mi05_configuration,length));
    IO24_CHECK(counts.submits==submits); check_configuration_buffer_guards(&configuration);
    length=IO24_LENGTH_SENTINEL;
    IO24_CHECK(!f->descriptor(root,1,1,0,buffer.bytes,sizeof(buffer.bytes),&length) &&
            fake.last_error==ERROR_INVALID_PARAMETER && length==0 && counts.submits==submits);

    /* Cached descriptors never cross the device boundary; string and another
     * noncached descriptor each do so exactly once with the typed ABI. */
    for(i=0;i<2;i++)
    {
        UCHAR type=i?0x22:3,index=i?2:1; USHORT language=0x0409;
        fake.descriptor_response_length=i?12:sizeof(io24_string_descriptor_response);
        start=fake.event_count; guard_buffer_reset(&buffer,GUARD_BYTE); length=IO24_LENGTH_SENTINEL;
        IO24_CHECK(f->descriptor(root,type,index,language,buffer.bytes,sizeof(buffer.bytes),&length));
        event=find_ioctl_after(start,IO24_IOCTL_DESCRIPTOR);
        IO24_CHECK(event && counts.submits==submits+i+1 && length==fake.descriptor_response_length);
        if(event){check_header(event,sizeof(struct io24_wire_descriptor),UINT64_C(0x1122334455667788),0);
            IO24_CHECK(event->request.descriptor.type==type && event->request.descriptor.index==index &&
                event->request.descriptor.language==language && event->request.descriptor.length==sizeof(buffer.bytes) &&
                event->out_length==sizeof(buffer.bytes));}
        check_buffer_guards(&buffer);
    }
    /* The fake writes malformed/error replies into its output boundary; a
     * correct public fallback stages them and never corrupts caller memory. */
    fake.descriptor_response_length=33; guard_buffer_reset(&buffer,GUARD_BYTE); length=IO24_LENGTH_SENTINEL;
    IO24_CHECK(!f->descriptor(root,3,3,0x0409,buffer.bytes,sizeof(buffer.bytes),&length) && length==0 &&
            bytes_equal(buffer.bytes,sizeof(buffer.bytes),GUARD_BYTE)); check_buffer_guards(&buffer);
    fake.descriptor_response_length=1; guard_buffer_reset(&buffer,GUARD_BYTE); length=IO24_LENGTH_SENTINEL;
    IO24_CHECK(f->descriptor(root,3,4,0x0409,buffer.bytes,sizeof(buffer.bytes),&length) && length==1 &&
            buffer.bytes[0]==io24_string_descriptor_response[0] && bytes_equal(buffer.bytes+1,sizeof(buffer.bytes)-1,GUARD_BYTE)); check_buffer_guards(&buffer);
    fake.descriptor_immediate_failure=TRUE; fake.descriptor_response_length=8; guard_buffer_reset(&buffer,GUARD_BYTE); length=IO24_LENGTH_SENTINEL;
    IO24_CHECK(!f->descriptor(root,3,5,0x0409,buffer.bytes,sizeof(buffer.bytes),&length) &&
            fake.last_error==ERROR_ACCESS_DENIED && length==0 && bytes_equal(buffer.bytes,sizeof(buffer.bytes),GUARD_BYTE));
    check_buffer_guards(&buffer); fake.descriptor_immediate_failure=FALSE;

    /* The remaining matrix is safely deferred until the missing public symbol
     * exists.  Its cache/fallback witness above is nevertheless executable in
     * today's RED binary. */
    if (!f->control) { IO24_CHECK(f->free_handle(root)); return; }
    large=malloc(4096); IO24_CHECK(large!=NULL); if(!large){f->free_handle(root);return;}
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)
    {
        setup=(WINUSB_SETUP_PACKET){cases[i].request_type,cases[i].request,cases[i].value,cases[i].index,cases[i].length};
        memset(large,GUARD_BYTE,4096); fake.control_response_length=cases[i].length; length=IO24_LENGTH_SENTINEL; start=fake.event_count;
        IO24_CHECK(f->control(root,setup,large,cases[i].length,&length,NULL)); event=find_ioctl_after(start,cases[i].code);
        IO24_CHECK(event && length==cases[i].length && event->out_length==cases[i].length);
        if(event){check_header(event,sizeof(struct io24_wire_control),UINT64_C(0x1122334455667788),0);
            IO24_CHECK(event->request.control.transfer_length==cases[i].length && event->request.control.reserved==0 &&
                (event->code&3)==(cases[i].code&3));
            if(i==1)IO24_CHECK(event->request.control.setup[4]==5 && event->request.control.setup[5]==0xab);
            else IO24_CHECK(!memcmp(event->request.control.setup,&setup,8));}
    }
    /* Bad handle, reserved type/recipient, malformed shape and endpoint before
     * alternate 1 are rejected before a private submit. */
    setup=(WINUSB_SETUP_PACKET){0x80,1,0,0,1}; submits=counts.submits; length=IO24_LENGTH_SENTINEL;
    IO24_CHECK(!f->control((void *)(uintptr_t)1,setup,large,1,&length,NULL) && counts.submits==submits);
    IO24_CHECK(!f->control(root,(WINUSB_SETUP_PACKET){0xe3,1,0,0,1},large,1,&length,NULL) && counts.submits==submits);
    IO24_CHECK(!f->control(root,(WINUSB_SETUP_PACKET){0xc4,1,0,0,1},large,1,&length,NULL) && counts.submits==submits);
    IO24_CHECK(!f->control(root,(WINUSB_SETUP_PACKET){0xc2,1,0,0x81,1},large,1,&length,NULL) && counts.submits==submits);
    IO24_CHECK(!f->control(root,setup,NULL,1,&length,NULL) && counts.submits==submits);
    setup.Length=2; IO24_CHECK(!f->control(root,setup,large,1,&length,NULL) && counts.submits==submits);
    setup.Length=4097; IO24_CHECK(!f->control(root,setup,large,4097,&length,NULL) && counts.submits==submits);
    IO24_CHECK(f->set_alt && f->set_alt(root,1));
    /* Exact current endpoints only: 0x81 accepts IN, 0x01 accepts OUT. */
    for(i=0;i<2;i++)
    { setup=(WINUSB_SETUP_PACKET){i?0x42:0xc2,1,0,(USHORT)(i?1:0x81),16}; memset(large,GUARD_BYTE,4096);length=IO24_LENGTH_SENTINEL;start=fake.event_count;fake.control_response_length=16;
      IO24_CHECK(f->control(root,setup,large,16,&length,NULL));event=find_ioctl_after(start,i?IO24_IOCTL_CONTROL_OUT:IO24_IOCTL_CONTROL_IN);IO24_CHECK(event&&length==16); }
    submits=counts.submits;
    IO24_CHECK(!f->control(root,(WINUSB_SETUP_PACKET){0x42,1,0,0x81,16},large,16,&length,NULL) && counts.submits==submits);
    IO24_CHECK(!f->control(root,(WINUSB_SETUP_PACKET){0xc2,1,0,1,16},large,16,&length,NULL) && counts.submits==submits);
    IO24_CHECK(!f->control(root,(WINUSB_SETUP_PACKET){0xc2,1,0,0x83,16},large,16,&length,NULL) && counts.submits==submits);
    /* IN copies only valid bounded replies; OUT never changes caller storage. */
    for(i=0;i<2;i++)
    { BOOL in=!i; setup=(WINUSB_SETUP_PACKET){in?0xc0:0x40,2,0,0,16};
      fake.control_response_length=i?5:16;fake.control_immediate_failure=FALSE;guard_buffer_reset(&buffer,GUARD_BYTE);length=IO24_LENGTH_SENTINEL;
      IO24_CHECK(f->control(root,setup,buffer.bytes,16,&length,NULL)&&length==fake.control_response_length);
      if(in)IO24_CHECK(buffer.bytes[0]==0x70&&bytes_equal(buffer.bytes+length,sizeof(buffer.bytes)-length,GUARD_BYTE));
      else IO24_CHECK(bytes_equal(buffer.bytes,sizeof(buffer.bytes),GUARD_BYTE));
      check_buffer_guards(&buffer);
      fake.control_response_length=17;guard_buffer_reset(&buffer,GUARD_BYTE);length=IO24_LENGTH_SENTINEL;
      IO24_CHECK(!f->control(root,setup,buffer.bytes,16,&length,NULL)&&length==0&&bytes_equal(buffer.bytes,sizeof(buffer.bytes),GUARD_BYTE));check_buffer_guards(&buffer);
      fake.control_response_length=16;fake.control_immediate_failure=TRUE;guard_buffer_reset(&buffer,GUARD_BYTE);length=IO24_LENGTH_SENTINEL;
      IO24_CHECK(!f->control(root,setup,buffer.bytes,16,&length,NULL)&&fake.last_error==ERROR_ACCESS_DENIED&&length==0&&bytes_equal(buffer.bytes,sizeof(buffer.bytes),GUARD_BYTE));check_buffer_guards(&buffer); }
    fake.control_immediate_failure=FALSE;
    IO24_CHECK(f->free_handle(root)); free(large);

    /* A distinct fixture has root interface 5 and associated interface 2.
     * Never reset while a handle is live; each object is freed once. */
    if(f->associated){fake_reset();fake.two_interface_fixture=TRUE;associated_root=NULL;associated=NULL;
      if(initialize_handle(f,&associated_root) && f->associated(associated_root,0,&associated))
      { large=malloc(16);IO24_CHECK(large!=NULL);if(large){setup=(WINUSB_SETUP_PACKET){0xa1,1,0,0xfe9b,1};fake.control_response_length=1;length=IO24_LENGTH_SENTINEL;start=fake.event_count;
          IO24_CHECK(f->control(associated,setup,large,1,&length,NULL));event=find_ioctl_after(start,IO24_IOCTL_CONTROL_IN);
          IO24_CHECK(event&&event->request.header.interface_index==1&&event->request.control.setup[4]==2&&event->request.control.setup[5]==0xfe);
          submits=counts.submits;IO24_CHECK(!f->control(associated,(WINUSB_SETUP_PACKET){0x80,1,0,0,1},large,1,&length,NULL)&&counts.submits==submits);free(large);}
        IO24_CHECK(f->free_handle(associated));IO24_CHECK(f->free_handle(associated_root));
        IO24_CHECK(fake.release_ioctls==1&&counts.allocations==counts.frees); }
      else if(associated_root) f->free_handle(associated_root); }
}
static void test_cancel(const struct functions*f)
{WINUSB_INTERFACE_HANDLE h;unsigned int submits;fake_reset();if(!initialize_handle(f,&h))return;submits=counts.submits;IO24_CHECK(f->abort_pipe&&f->abort_pipe(h,0x81));IO24_CHECK(f->reset_pipe&&f->reset_pipe(h,0x81));IO24_CHECK(counts.submits==submits+2);if(f->free_handle)f->free_handle(h);}

static void validate_vendor_fake_trace(OVERLAPPED *caller)
{
    static const DWORD expected[]={IO24_IOCTL_INITIALIZE,IO24_IOCTL_DESCRIPTOR,IO24_IOCTL_GET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_POLICY,IO24_IOCTL_SET_ALTERNATE,IO24_IOCTL_CONTROL_OUT,IO24_IOCTL_CONTROL_OUT,IO24_IOCTL_READ_PIPE,IO24_IOCTL_READ_PIPE,IO24_IOCTL_WRITE_PIPE,IO24_IOCTL_WRITE_PIPE,IO24_IOCTL_ABORT_PIPE,IO24_IOCTL_RESET_PIPE,IO24_IOCTL_RELEASE};
    static const uint32_t policy[]={3,9,1,2,4,5,6,7};static const uint32_t pipe[]={0,0,1,0x81,0x81,0x81,0x81,0x81};static const uint32_t value[]={0,0,0,0,0,0,0,1};
    static const uint8_t setup[8]={0x41,1,2,0,5,0,32,0};const struct fake_event *ioctls[32];struct io24_wire_policy policy_result;unsigned int i,n=0,overlapped_pos;uint64_t session;
    for(i=0;i<fake.event_count;i++) if(fake.events[i].kind==EVENT_IOCTL&&n<32) ioctls[n++]=&fake.events[i];
    IO24_CHECK(n==sizeof(expected)/sizeof(expected[0]));
    for(i=0;i<n&&i<sizeof(expected)/sizeof(expected[0]);i++){IO24_CHECK(ioctls[i]->code==expected[i]);IO24_CHECK(ioctls[i]->handle==IO24_FILE_HANDLE);IO24_CHECK(ioctls[i]->result);}
    if(n>=21){
        check_header(ioctls[0],sizeof(struct io24_wire_header),0,0);IO24_CHECK(ioctls[0]->out_length==72);session=ioctls[1]->request.header.session;IO24_CHECK(session==UINT64_C(0x1122334455667788));
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
    IO24_CHECK(fake.closes==0);
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
    ok=f->free_handle&&f->free_handle(associated);IO24_CHECK(ok);ok=f->free_handle&&f->free_handle(root);IO24_CHECK(ok);check_buffer_guards(&g);validate_vendor_fake_trace(&ov);
}
static void run_group(const char*m,const struct functions*f){if(!strcmp(m,"--vendor")){test_vendor_sequence(f);return;}if(!strcmp(m,"--control-descriptor")){test_task9_control_descriptor(f);return;}if(!strcmp(m,"--red")||!strcmp(m,"--initialize"))test_initialize(f);if(!strcmp(m,"--red")||!strcmp(m,"--handles"))test_handles(f);if(!strcmp(m,"--red")||!strcmp(m,"--alternate"))test_alternate(f);if(!strcmp(m,"--red")||!strcmp(m,"--descriptors"))test_descriptors(f);if(!strcmp(m,"--red")||!strcmp(m,"--policy"))test_policy(f);if(!strcmp(m,"--red")||!strcmp(m,"--transfer"))test_transfer(f);if(!strcmp(m,"--red")||!strcmp(m,"--cancel"))test_cancel(f);if(!strcmp(m,"--red"))test_vendor_sequence(f);}
int main(int argc,char**argv){void*m;struct functions f;uint32_t target,missing;if(argc!=3)return 2;m=dlopen(!strcmp(argv[1],"self")?NULL:argv[1],RTLD_NOW|RTLD_LOCAL);if(!m){fprintf(stderr,"HARNESS: dlopen production module: %s\n",dlerror());return 2;}fake_reset();load_functions(m,&f);target=target_mask(argv[2]);missing=target&~f.present_mask;check_target_symbols(&f,target);run_group(argv[2],&f);dlclose(m);printf("CP33 public executed mode=%s target-mask=%#x present-mask=%#x missing-mask=%#x fake-events=%u submits=%u releases=%u completions=%u failures=%u\n",argv[2],target,f.present_mask,missing,fake.event_count,counts.submits,fake.release_ioctls,counts.completions,counts.failures);return counts.failures?1:0;}
