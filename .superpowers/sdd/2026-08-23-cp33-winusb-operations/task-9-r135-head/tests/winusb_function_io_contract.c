/* Executed CP33 contract: actual winusb.sys main.c inside the retained fake WDM. */
#include <stdint.h>
#include <stdatomic.h>
#include <threads.h>
static _Atomic(void *) io24_mutex_block_target;
static atomic_bool io24_mutex_block_seen;
void io24_mutex_yield(void *mutex);
#define main io24_retained_cp32_main
#define ExAllocatePool io24_retained_ExAllocatePool
#define ExFreePool io24_retained_ExFreePool
#define IoCallDriver io24_retained_IoCallDriver
#define thrd_yield() io24_mutex_yield(mutex)
#include "winusb_function_binding_contract.c"
#undef thrd_yield
#undef IoCallDriver
#undef ExFreePool
#undef ExAllocatePool
#undef main
#include "wine/winusb.h"
#include "ddk/usb.h"
#ifndef METHOD_NEITHER
#define METHOD_NEITHER 3
#endif
#include "ddk/usbioctl.h"

void io24_mutex_yield(void *mutex)
{
    if (mutex == atomic_load_explicit(&io24_mutex_block_target, memory_order_acquire))
        atomic_store_explicit(&io24_mutex_block_seen, TRUE, memory_order_release);
    thrd_yield();
}

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
struct session_pool_allocation
{
    void *pointer;
    SIZE_T size;
};
static struct session_pool_allocation session_pool_allocations[2048];
static unsigned int unknown_pool_frees;
static BOOL poison_two_interface_state_allocation;
static unsigned int poisoned_two_interface_state_allocations;
/* A Task-9 transfer owns exactly the production allocations made while its
 * original IRP is being dispatched.  Keeping a separate, size-and-identity
 * ledger means session setup allocations cannot make an upper free look real. */
struct control_pool_allocation
{
    void *pointer;
    SIZE_T size;
    unsigned int frees;
};
static struct control_pool_allocation control_pool_allocations[4];
static BOOL control_pool_observing;
static BOOL control_pool_tracking_frees;
static BOOL control_completion_allocation_observing;
static BOOL control_retirement_observing;
static unsigned int control_pool_attempts, control_pool_count;
static unsigned int control_completion_allocation_attempts;
static unsigned int control_completion_pool_allocations_before;
static unsigned int control_pool_fail_ordinal;
static void control_note_free(PVOID pointer);
#define IO24_CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr, "FAIL %s:%u: %s\n", __func__, __LINE__, #expr); \
    ++counts.failures; \
} } while (0)

PVOID WINAPI ExAllocatePool(POOL_TYPE type, SIZE_T size)
{
    void *pointer;
    unsigned int i;

    (void)type;
    if (control_completion_allocation_observing)
        ++control_completion_allocation_attempts;
    session_allocation_calls++;
    if (session_fail_allocation == session_allocation_calls) return NULL;
    if (control_pool_observing)
    {
        ++control_pool_attempts;
        if (control_pool_fail_ordinal == control_pool_attempts) return NULL;
    }
    if (!(pointer = calloc(1, size))) return NULL;
    if (poison_two_interface_state_allocation &&
            size == 2 * sizeof(struct winusb_interface_state))
    {
        struct winusb_interface_state *state = pointer;
        memset(pointer, GUARD_BYTE, size);
        for (unsigned int state_i = 0; state_i < 2; ++state_i)
        {
            state[state_i].interface_number = 0;
            state[state_i].alternate_setting = 0;
            state[state_i].first_endpoint = 0;
            state[state_i].endpoint_count = 0;
            state[state_i].generation = 0;
            state[state_i].pipes = NULL;
        }
        ++poisoned_two_interface_state_allocations;
    }
    for (i = 0; i < ARRAY_SIZE(session_pool_allocations); ++i)
        if (!session_pool_allocations[i].pointer || session_pool_allocations[i].pointer == pointer)
        {
            session_pool_allocations[i].pointer = pointer;
            session_pool_allocations[i].size = size;
            break;
        }
    if (i == ARRAY_SIZE(session_pool_allocations))
    {
        fputs("HARNESS: session pool allocation audit exhausted\n", stderr);
        free(pointer);
        exit(2);
    }
    pool_allocations++;
    if (control_pool_observing)
    {
        if (control_pool_count == ARRAY_SIZE(control_pool_allocations))
        {
            fputs("HARNESS: Task-9 control allocation audit exhausted\n", stderr);
            exit(2);
        }
        control_pool_allocations[control_pool_count].pointer = pointer;
        control_pool_allocations[control_pool_count].size = size;
        control_pool_allocations[control_pool_count].frees = 0;
        ++control_pool_count;
    }
    return pointer;
}

VOID WINAPI ExFreePool(PVOID pointer)
{
    unsigned int i;

    if (!pointer) return;
    for (i = 0; i < ARRAY_SIZE(session_pool_allocations); ++i)
        if (session_pool_allocations[i].pointer == pointer)
        {
            session_pool_allocations[i].pointer = NULL;
            if (control_pool_tracking_frees)
                for (unsigned int control_i = 0; control_i < control_pool_count; ++control_i)
                    if (control_pool_allocations[control_i].pointer == pointer)
                    {
                        ++control_pool_allocations[control_i].frees;
                        if (control_retirement_observing) control_note_free(pointer);
                    }
            pool_frees++;
            free(pointer);
            return;
    }
    ++unknown_pool_frees;
    ++counts.failures;
    fprintf(stderr, "FAIL ExFreePool: rejected unknown session pointer %p\n", pointer);
}

static void control_pool_begin(unsigned int fail_ordinal)
{
    memset(control_pool_allocations, 0, sizeof(control_pool_allocations));
    control_pool_attempts = control_pool_count = 0;
    control_pool_fail_ordinal = fail_ordinal;
    control_pool_observing = TRUE;
    control_pool_tracking_frees = TRUE;
}

static void control_pool_end(void)
{
    control_pool_observing = FALSE;
    control_pool_tracking_frees = FALSE;
    control_pool_fail_ordinal = 0;
}

static void control_pool_pause_allocations(void)
{
    control_pool_observing = FALSE;
    control_pool_fail_ordinal = 0;
}

/* This observer is deliberately independent of the admission allocation
 * journal.  Its interval is only one pending completion, so intervening
 * alternate-selection allocations cannot hide a completion-time clone. */
static void control_completion_allocation_begin(void)
{
    IO24_CHECK(!control_completion_allocation_observing);
    control_completion_allocation_attempts = 0;
    control_completion_pool_allocations_before = pool_allocations;
    control_completion_allocation_observing = TRUE;
}

static void control_completion_allocation_end(void)
{
    control_completion_allocation_observing = FALSE;
    IO24_CHECK(control_completion_allocation_attempts == 0);
    IO24_CHECK(pool_allocations == control_completion_pool_allocations_before);
}

static struct control_pool_allocation *control_pool_find(PVOID pointer)
{
    for (unsigned int i = 0; i < control_pool_count; ++i)
        if (control_pool_allocations[i].pointer == pointer)
            return &control_pool_allocations[i];
    return NULL;
}

static void control_pool_check_pointer(PVOID pointer, SIZE_T size, unsigned int frees)
{
    struct control_pool_allocation *allocation = control_pool_find(pointer);

    IO24_CHECK(allocation != NULL);
    if (allocation)
    {
        IO24_CHECK(allocation->size == size);
        IO24_CHECK(allocation->frees == frees);
    }
}

static SIZE_T control_pool_pointer_size(PVOID pointer)
{
    struct control_pool_allocation *allocation = control_pool_find(pointer);

    IO24_CHECK(allocation != NULL);
    return allocation ? allocation->size : 0;
}

static void control_pool_check_complete(unsigned int expected_attempts,
        unsigned int expected_allocations)
{
    unsigned int urb_allocations = 0;

    IO24_CHECK(control_pool_attempts == expected_attempts);
    IO24_CHECK(control_pool_count == expected_allocations);
    for (unsigned int i = 0; i < control_pool_count; ++i)
    {
        IO24_CHECK(control_pool_allocations[i].pointer != NULL);
        IO24_CHECK(control_pool_allocations[i].size != 0);
        IO24_CHECK(control_pool_allocations[i].frees == 1);
        for (unsigned int j = 0; j < i; ++j)
            IO24_CHECK(control_pool_allocations[i].pointer != control_pool_allocations[j].pointer);
        if (control_pool_allocations[i].size == sizeof(URB) ||
                control_pool_allocations[i].size == sizeof(struct _URB_CONTROL_TRANSFER))
            ++urb_allocations;
    }
    if (expected_allocations == 2)
        IO24_CHECK(urb_allocations == 1); /* one URB plus one upper record */
    else if (expected_allocations == 4)
        IO24_CHECK(urb_allocations == 2); /* two distinct URBs plus two records */
}

__attribute__((noinline)) static void poison_alternate_stack(void)
{
    volatile uintptr_t poison[128];
    unsigned int i;

    for (i = 0; i < ARRAY_SIZE(poison); ++i)
        poison[i] = (uintptr_t)0xa5 * (~(uintptr_t)0 / 0xff);
    atomic_signal_fence(memory_order_seq_cst);
}

#define IO24_CTL_CODE(type,function,method,access) (((type)<<16)|((access)<<14)|((function)<<2)|(method))
#define IO24_IOCTL_INITIALIZE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x800,2,0)
#define IO24_IOCTL_SET_ALTERNATE IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x803,0,0)
#define IO24_IOCTL_GET_POLICY IO24_CTL_CODE(FILE_DEVICE_UNKNOWN,0x804,0,0)
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
static const unsigned char nonbulk_endpoint_configuration[] =
{
    9,2,25,0,1,1,0,0x80,0xfa, 9,4,5,0,1,0xff,0,0,6,
    7,5,0x82,3,64,0,1
};
static const unsigned char two_interface_configuration[] =
{
    9,2,43,0,2,1,0,0x80,0xfa,
    9,4,5,0,0,0xff,0,0,6,
    9,4,6,0,0,0xff,0,0,6,
    9,4,6,1,1,0xff,0,0,6, 7,5,0x83,2,64,0,0
};
/* Policy reset fixture: both interfaces have a selectable alternate with
 * current bulk pipes, so target-only replacement is executable rather than
 * inferred from an impossible MI05 selection. */
static const unsigned char two_interface_policy_configuration[] =
{
    9,2,66,0,2,1,0,0x80,0xfa,
    9,4,5,0,0,0xff,0,0,6,
    9,4,5,1,2,0xff,0,0,6, 7,5,0x81,2,0,2,0, 7,5,0x01,2,0,2,0,
    9,4,6,0,0,0xff,0,0,6,
    9,4,6,1,1,0xff,0,0,6, 7,5,0x83,2,64,0,0
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
static BOOL mutate_after_select, alternate_mutate_after_select, rollback_saw_unpublished;
static BOOL lower_claim_pending, lower_claim_committed, lower_selected_state;
static BOOL select_returns_transaction;
static NTSTATUS commit_failure_status, rollback_failure_status;
static unsigned int rollback_failures_remaining;
static unsigned char *active_initialize_output;
static USBD_CONFIGURATION_HANDLE lower_transaction_token;
static unsigned int urb_builds, fail_urb_build, select_interface_calls;
static unsigned int builder_allocations, builder_frees;
static ULONG expected_select_pipes;
static UCHAR expected_select_endpoint;
static USBD_PIPE_TYPE expected_select_type;
static USHORT expected_select_packet_size;
static ULONG expected_select_interfaces;
static UCHAR expected_select_interface_numbers[2];
static UCHAR expected_alternate_interface, expected_alternate_setting;
static ULONG expected_alternate_pipes;
static UCHAR expected_alternate_endpoints[2];
static USHORT expected_alternate_packets[2];
static FILE_OBJECT *active_session_file;
static void (*commit_reentrant_hook)(void);
static BOOL concurrent_session_allowed;
/* Task 9 control/descriptor lower-boundary oracle.  This belongs to the fake
 * WDM only: it records what the real production transfer path submits. */
static NTSTATUS control_nt_status;
static USBD_STATUS control_urb_status;
static BOOL control_returns_pending, control_writes_urb_status;
static ULONG control_actual_length, control_expected_length, control_expected_flags;
static USHORT control_expected_function;
static UCHAR control_expected_setup[8];
static PMDL control_expected_mdl;
static FILE_OBJECT *control_expected_file;
static PIRP control_expected_irp;
static unsigned int control_calls;
static PIRP control_pending_irp;
static IO_STACK_LOCATION *control_pending_stack;
static PDEVICE_OBJECT control_pending_device;
static PVOID control_pending_context;
static URB *control_pending_urb;
static PIRP control_pending_next_irp;
static IO_STACK_LOCATION *control_pending_next_stack;
static PDEVICE_OBJECT control_pending_next_device;
static PVOID control_pending_next_context;
static URB *control_pending_next_urb;
static unsigned int control_pending_count;
static unsigned int control_lower_completions, control_upper_completions;
static unsigned int control_duplicate_completion_attempts;
static BOOL control_lower_slot0_installed;
static unsigned int control_file_references, control_file_dereferences;
static LONG expected_session_urb_outstanding = 1;
static LONG expected_task9_completion_outstanding = 1;
static unsigned int control_retirement_events, control_retirement_order[8];
static BOOL descriptor_unmapped_mdl;
enum { CONTROL_EVENT_UNLINK = 1, CONTROL_EVENT_FREE = 2, CONTROL_EVENT_DEREF = 3 };
static PVOID control_lower_slot0_sentinel = (PVOID)(UINT_PTR)0x10c0ffee;
static PVOID control_preserved_slots[3] =
{
    (PVOID)(UINT_PTR)0x101, (PVOID)(UINT_PTR)0x202, (PVOID)(UINT_PTR)0x303
};

static void control_note_free(PVOID pointer)
{
    const struct winusb_file *file = control_expected_file ? control_expected_file->FsContext : NULL;
    (void)pointer;
    IO24_CHECK(control_retirement_observing);
    IO24_CHECK(control_file_references > control_file_dereferences);
    /* The first upper free is an observable ordering boundary: the completion
     * must already have unlinked/decremented the record while retaining the
     * FILE_OBJECT reference. */
    if (!control_retirement_events)
    {
        /* Completing the lower IRP may free a close-waiting file as soon as
         * its I/O reference is released.  The upper record, URB, and object
         * reference must therefore retire while that reference still pins it. */
        IO24_CHECK(file && file->outstanding == expected_task9_completion_outstanding);
        IO24_CHECK(file && IsListEmpty(&file->transfers) ==
                (expected_task9_completion_outstanding == 1));
        control_retirement_order[control_retirement_events++] = CONTROL_EVENT_UNLINK;
    }
    if (control_retirement_events < ARRAY_SIZE(control_retirement_order))
        control_retirement_order[control_retirement_events++] = CONTROL_EVENT_FREE;
}

static void control_retirement_begin(void)
{
    IO24_CHECK(!control_retirement_observing);
    IO24_CHECK(control_file_references == control_file_dereferences);
    control_retirement_events = 0;
    memset(control_retirement_order, 0, sizeof(control_retirement_order));
    control_retirement_observing = TRUE;
}

static void control_retirement_end(void)
{
    IO24_CHECK(control_retirement_observing);
    IO24_CHECK(control_retirement_events == 4);
    IO24_CHECK(control_retirement_order[0] == CONTROL_EVENT_UNLINK);
    IO24_CHECK(control_retirement_order[1] == CONTROL_EVENT_FREE);
    IO24_CHECK(control_retirement_order[2] == CONTROL_EVENT_FREE);
    IO24_CHECK(control_retirement_order[3] == CONTROL_EVENT_DEREF);
    IO24_CHECK(control_file_references == control_file_dereferences);
    control_retirement_observing = FALSE;
}

/* Ordinary WDM object-lifetime instrumentation, not a production seam. */
VOID WINAPI ObReferenceObject(PVOID object)
{
    IO24_CHECK(object == control_expected_file);
    IO24_CHECK(control_expected_file && control_expected_file->FsContext);
    IO24_CHECK(((struct winusb_file *)control_expected_file->FsContext)->session_mutex.Owner != NULL);
    ++control_file_references;
}

VOID WINAPI ObDereferenceObject(PVOID object)
{
    IO24_CHECK(object == control_expected_file);
    IO24_CHECK(control_file_references == control_file_dereferences +
            expected_task9_completion_outstanding);
    if (control_retirement_observing)
    {
        const struct winusb_file *file = control_expected_file ?
                control_expected_file->FsContext : NULL;
        IO24_CHECK(control_retirement_events == 3);
        IO24_CHECK(control_retirement_order[0] == CONTROL_EVENT_UNLINK);
        IO24_CHECK(control_retirement_order[1] == CONTROL_EVENT_FREE);
        IO24_CHECK(control_retirement_order[2] == CONTROL_EVENT_FREE);
        IO24_CHECK(file && file->outstanding == expected_task9_completion_outstanding);
        if (control_retirement_events < ARRAY_SIZE(control_retirement_order))
            control_retirement_order[control_retirement_events++] = CONTROL_EVENT_DEREF;
    }
    ++control_file_dereferences;
}

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

/* submit_urb() owns only these synchronous initialization IRPs.  Task 9 must
 * forward the caller's IRP, so never infer ownership from a cast. */
static struct session_irp_allocation *builder_irps[2048];

static struct session_irp_allocation *find_builder_irp(PIRP irp)
{
    for (unsigned int i = 0; i < ARRAY_SIZE(builder_irps); ++i)
        if (builder_irps[i] && &builder_irps[i]->irp == irp) return builder_irps[i];
    return NULL;
}

static void remember_builder_irp(struct session_irp_allocation *allocation)
{
    for (unsigned int i = 0; i < ARRAY_SIZE(builder_irps); ++i)
        if (!builder_irps[i]) { builder_irps[i] = allocation; return; }
    fputs("HARNESS: builder IRP registry exhausted\n", stderr);
    exit(2);
}

static void forget_builder_irp(struct session_irp_allocation *allocation)
{
    for (unsigned int i = 0; i < ARRAY_SIZE(builder_irps); ++i)
        if (builder_irps[i] == allocation) { builder_irps[i] = NULL; return; }
    IO24_CHECK(FALSE);
}

static void complete_task9_original_irp(PDEVICE_OBJECT device, PIRP irp,
        IO_STACK_LOCATION *stack, LONG outstanding_before,
        PVOID expected_context, URB *expected_urb)
{
    struct winusb_file *file = control_expected_file ?
            control_expected_file->FsContext : NULL;
    unsigned int completions_before = completes;
    NTSTATUS completion_status;

    expected_task9_completion_outstanding = outstanding_before;
    IO24_CHECK(irp == control_expected_irp);
    IO24_CHECK(file != NULL && file->outstanding == outstanding_before);
    IO24_CHECK(file && file->transfers.Flink != &file->transfers &&
            file->transfers.Blink != &file->transfers);
    IO24_CHECK(stack->CompletionRoutine != NULL);
    IO24_CHECK(expected_context != NULL && stack->Context == expected_context);
    IO24_CHECK(expected_urb != NULL &&
            stack->Parameters.Others.Argument1 == expected_urb);
    IO24_CHECK((stack->Control & (SL_INVOKE_ON_SUCCESS | SL_INVOKE_ON_ERROR | SL_INVOKE_ON_CANCEL)) ==
            (SL_INVOKE_ON_SUCCESS | SL_INVOKE_ON_ERROR | SL_INVOKE_ON_CANCEL));
    IO24_CHECK(control_file_references == control_file_dereferences + outstanding_before);
    /* Slot 0 belongs to the lower pending queue.  It is retired before upper
     * completion, while unrelated lower slots stay byte-for-byte intact. */
    if (control_lower_slot0_installed)
    {
        IO24_CHECK(irp->Tail.Overlay.DriverContext[0] == control_lower_slot0_sentinel);
        irp->Tail.Overlay.DriverContext[0] = NULL;
    }
    else IO24_CHECK(irp->Tail.Overlay.DriverContext[0] == NULL);
    IO24_CHECK(irp->Tail.Overlay.DriverContext[1] == control_preserved_slots[0] &&
            irp->Tail.Overlay.DriverContext[2] == control_preserved_slots[1] &&
            irp->Tail.Overlay.DriverContext[3] == control_preserved_slots[2]);
    ++control_lower_completions;
    completion_status = stack->CompletionRoutine(device, irp, stack->Context);
    ++control_upper_completions;
    IO24_CHECK(completion_status == STATUS_SUCCESS);
    IO24_CHECK(completes == completions_before); /* upper must not complete */
    IO24_CHECK(irp->Tail.Overlay.DriverContext[0] == NULL &&
            irp->Tail.Overlay.DriverContext[1] == control_preserved_slots[0] &&
            irp->Tail.Overlay.DriverContext[2] == control_preserved_slots[1] &&
            irp->Tail.Overlay.DriverContext[3] == control_preserved_slots[2]);
    /* The lower stack owns the sole terminal completion after upper returns. */
    IoCompleteRequest(irp, IO_NO_INCREMENT);
    IO24_CHECK(completes == completions_before + 1);
    IO24_CHECK(file->outstanding == outstanding_before - 1);
    IO24_CHECK(!!file->zero_outstanding.Header.SignalState == (outstanding_before == 1));
    IO24_CHECK(IsListEmpty(&file->transfers) == (outstanding_before == 1));
    IO24_CHECK(control_file_references == control_file_dereferences + outstanding_before - 1);
}

static BOOL complete_pending_task9_irp(void)
{
    PIRP irp = control_pending_irp;
    IO_STACK_LOCATION *stack = control_pending_stack;
    PDEVICE_OBJECT device = control_pending_device;
    PVOID context = control_pending_context;
    URB *urb = control_pending_urb;
    unsigned int pending_before = control_pending_count;

    if (!irp || !stack)
    {
        ++control_duplicate_completion_attempts;
        return FALSE;
    }
    control_pending_irp = control_pending_next_irp;
    control_pending_stack = control_pending_next_stack;
    control_pending_device = control_pending_next_device;
    control_pending_context = control_pending_next_context;
    control_pending_urb = control_pending_next_urb;
    control_pending_next_irp = NULL;
    control_pending_next_stack = NULL;
    control_pending_next_device = NULL;
    control_pending_next_context = NULL;
    control_pending_next_urb = NULL;
    --control_pending_count;
    control_expected_irp = irp;
    control_lower_slot0_installed = TRUE;
    complete_task9_original_irp(device, irp, stack, pending_before, context, urb);
    control_lower_slot0_installed = FALSE;
    return TRUE;
}

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
    descriptor_reads = select_calls = urb_builds = fail_urb_build = select_interface_calls = 0;
    finalize_calls = finalize_commit_calls = finalize_rollback_calls = 0;
    mutate_after_select = alternate_mutate_after_select = rollback_saw_unpublished = FALSE;
    lower_claim_pending = lower_claim_committed = lower_selected_state = FALSE;
    select_returns_transaction = TRUE;
    commit_failure_status = rollback_failure_status = STATUS_SUCCESS;
    rollback_failures_remaining = 0;
    commit_reentrant_hook = NULL;
    concurrent_session_allowed = FALSE;
    lower_transaction_token = (void *)(UINT_PTR)0x13570001;
    builder_allocations = builder_frees = 0;
    expected_select_pipes = 0;
    expected_select_endpoint = 0;
    expected_select_type = UsbdPipeTypeControl;
    expected_select_packet_size = 0;
    expected_select_interfaces = 1;
    expected_select_interface_numbers[0] = 5;
    expected_select_interface_numbers[1] = 0;
    expected_alternate_interface = 5;
    expected_alternate_setting = 1;
    expected_alternate_pipes = 2;
    expected_alternate_endpoints[0] = 0x81;
    expected_alternate_endpoints[1] = 0x01;
    expected_alternate_packets[0] = expected_alternate_packets[1] = 512;
    control_nt_status = STATUS_SUCCESS;
    control_urb_status = USBD_STATUS_SUCCESS;
    control_returns_pending = FALSE;
    control_writes_urb_status = TRUE;
    control_actual_length = control_expected_length = 0;
    control_expected_flags = 0;
    control_expected_function = URB_FUNCTION_CONTROL_TRANSFER;
    memset(control_expected_setup, 0, sizeof(control_expected_setup));
    control_expected_mdl = NULL;
    control_expected_file = NULL;
    control_expected_irp = NULL;
    control_calls = 0;
    control_pending_irp = NULL;
    control_pending_stack = NULL;
    control_pending_device = NULL;
    control_pending_context = NULL;
    control_pending_urb = NULL;
    control_pending_next_irp = NULL;
    control_pending_next_stack = NULL;
    control_pending_next_device = NULL;
    control_pending_next_context = NULL;
    control_pending_next_urb = NULL;
    control_pending_count = 0;
    control_lower_completions = control_upper_completions = 0;
    control_duplicate_completion_attempts = 0;
    control_lower_slot0_installed = FALSE;
    control_file_references = control_file_dereferences = 0;
    expected_session_urb_outstanding = 1;
    expected_task9_completion_outstanding = 1;
    poison_two_interface_state_allocation = FALSE;
    poisoned_two_interface_state_allocations = 0;
    control_retirement_observing = FALSE;
    control_retirement_events = 0;
    control_pool_tracking_frees = FALSE;
    control_completion_allocation_observing = FALSE;
    control_completion_allocation_attempts = 0;
    control_completion_pool_allocations_before = 0;
    descriptor_unmapped_mdl = FALSE;
    memset(control_retirement_order, 0, sizeof(control_retirement_order));
    memset(builder_irps, 0, sizeof(builder_irps));
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
    remember_builder_irp(allocation);
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
    struct session_irp_allocation *allocation = find_builder_irp(irp);
    BOOL original_task9_irp = control_expected_irp && irp == control_expected_irp;
    IO_STACK_LOCATION *next = IoGetNextIrpStackLocation(irp);
    URB *urb = next->Parameters.Others.Argument1;
    NTSTATUS status = STATUS_NOT_SUPPORTED;
    ULONG actual = 0;

    (void)device;
    /* main.c's synchronous PnP forwarding is not a session URB. */
    if (!active_session_file &&
            next->Parameters.DeviceIoControl.IoControlCode != IOCTL_INTERNAL_USB_SUBMIT_URB)
    {
        irp->IoStatus.Status = STATUS_SUCCESS;
        if (irp == &synchronous_irp)
        {
            if (synchronous_iosb) *synchronous_iosb = irp->IoStatus;
            if (synchronous_event) synchronous_event->Header.SignalState = 1;
        }
        return STATUS_SUCCESS;
    }
    lower_calls++;
    if (original_task9_irp)
    {
        const struct winusb_file *file = active_session_file ?
                active_session_file->FsContext : NULL;

        /* Task 9 owns same-IRP forwarding.  A builder allocation here is an
         * executable nested-IRP mutant, not an implementation detail. */
        IO24_CHECK(irp == control_expected_irp && allocation == NULL);
        IO24_CHECK(active_session_file == control_expected_file && file);
        IO24_CHECK(file->outstanding == (LONG)control_pending_count + 1 &&
                !file->zero_outstanding.Header.SignalState);
        IO24_CHECK(file->session_mutex.Owner == NULL);
    }
    else if (!active_session_file)
        IO24_CHECK(urb && urb->UrbHeader.Function == IO24_URB_FUNCTION_CLAIM_TRANSACTION);
    else if (active_session_file->FsContext)
    {
        const struct winusb_file *file = active_session_file->FsContext;
        IO24_CHECK(file->outstanding == expected_session_urb_outstanding);
        IO24_CHECK(!file->zero_outstanding.Header.SignalState);
    }
    else IO24_CHECK(FALSE);
    IO24_CHECK(next->MajorFunction == IRP_MJ_INTERNAL_DEVICE_CONTROL);
    IO24_CHECK(next->Parameters.DeviceIoControl.IoControlCode == IOCTL_INTERNAL_USB_SUBMIT_URB);
    if (original_task9_irp)
        IO24_CHECK(irp == control_expected_irp && allocation == NULL);
    else
        IO24_CHECK(allocation && urb == allocation->urb);
    if (urb) IO24_CHECK(urb->UrbHeader.Status == USBD_STATUS_NOT_ACCESSED);
    if (!urb) goto done;
    if (urb->UrbHeader.Function == URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE)
    {
        struct _URB_CONTROL_DESCRIPTOR_REQUEST *request =
                &urb->UrbControlDescriptorRequest;
        const unsigned char *source = NULL;
        BOOL configuration_header = FALSE;

        if (control_expected_file && active_session_file == control_expected_file)
        {
            control_calls++;
            IO24_CHECK(original_task9_irp && irp == control_expected_irp);
            IO24_CHECK(request->Hdr.Length == sizeof(*request));
            IO24_CHECK(request->TransferBufferLength == control_expected_length);
            IO24_CHECK(request->TransferBuffer == NULL);
            IO24_CHECK(request->TransferBufferMDL == control_expected_mdl);
            IO24_CHECK(request->DescriptorType == control_expected_setup[0]);
            IO24_CHECK(request->Index == control_expected_setup[1]);
            IO24_CHECK(request->LanguageId == (USHORT)(control_expected_setup[2] |
                    ((USHORT)control_expected_setup[3] << 8)));
            status = control_nt_status;
            if (control_writes_urb_status) request->Hdr.Status = control_urb_status;
            if (NT_SUCCESS(status) && control_urb_status == USBD_STATUS_SUCCESS)
                request->TransferBufferLength = control_actual_length;
            goto done;
        }

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
        SIZE_T cursor = offsetof(struct _URB_SELECT_CONFIGURATION, Interface);
        ULONG interface_index;
        select_calls++;
        IO24_CHECK(descriptor_reads == 3);
        IO24_CHECK(request->ConfigurationDescriptor != NULL);
        for (interface_index = 0; interface_index < expected_select_interfaces;
                ++interface_index)
        {
            USBD_INTERFACE_INFORMATION *information = (void *)((UCHAR *)request + cursor);
            ULONG expected_pipes = interface_index ? 0 : expected_select_pipes;

            IO24_CHECK(information->InterfaceNumber == expected_select_interface_numbers[interface_index]);
            IO24_CHECK(information->AlternateSetting == 0);
            IO24_CHECK(information->NumberOfPipes == expected_pipes);
            IO24_CHECK(information->Length == offsetof(USBD_INTERFACE_INFORMATION, Pipes) +
                    expected_pipes * sizeof(USBD_PIPE_INFORMATION));
            if (expected_pipes)
            {
                const USBD_PIPE_INFORMATION *pipe = &information->Pipes[0];
                IO24_CHECK(expected_pipes == 1);
                IO24_CHECK(pipe->EndpointAddress == expected_select_endpoint);
                IO24_CHECK(pipe->PipeType == expected_select_type);
                IO24_CHECK(pipe->MaximumPacketSize == expected_select_packet_size);
            }
            cursor += information->Length;
        }
        IO24_CHECK(request->Hdr.Length == cursor);
        status = select_nt_status;
        if (select_writes_urb_status)
            request->Hdr.Status = select_urb_status;
        if (NT_SUCCESS(status) && select_writes_urb_status &&
                select_urb_status == USBD_STATUS_SUCCESS)
        {
            if (lower_claim_pending)
            {
                request->Hdr.Status = USBD_STATUS_REQUEST_FAILED;
                status = STATUS_INVALID_DEVICE_STATE;
                goto done;
            }
            request->ConfigurationHandle = select_returns_transaction ?
                    lower_transaction_token : NULL;
            lower_claim_pending = TRUE;
            lower_selected_state = TRUE;
            for (interface_index = 0, cursor = offsetof(struct _URB_SELECT_CONFIGURATION, Interface);
                    interface_index < expected_select_interfaces; ++interface_index)
            {
                USBD_INTERFACE_INFORMATION *information = (void *)((UCHAR *)request + cursor);
                ULONG i;
                for (i = 0; i < information->NumberOfPipes; ++i)
                    information->Pipes[i].PipeHandle = (HANDLE)(UINT_PTR)
                            (0x2000 + information->Pipes[i].EndpointAddress);
                cursor += information->Length;
            }
            if (mutate_after_select && active_session_file && active_session_file->FsContext)
                ((struct winusb_file *)active_session_file->FsContext)->state =
                        WINUSB_FILE_CLOSING;
        }
    }
    else if (urb->UrbHeader.Function == URB_FUNCTION_CONTROL_TRANSFER ||
            urb->UrbHeader.Function == URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE)
    {
        struct _URB_CONTROL_TRANSFER *request = &urb->UrbControlTransfer;

        control_calls++;
        IO24_CHECK(original_task9_irp && irp == control_expected_irp);
        IO24_CHECK(urb->UrbHeader.Function == control_expected_function);
        IO24_CHECK(request->Hdr.Length == sizeof(*request));
        IO24_CHECK(request->TransferFlags == control_expected_flags);
        IO24_CHECK(request->TransferBufferLength == control_expected_length);
        IO24_CHECK(request->TransferBuffer == NULL);
        IO24_CHECK(request->TransferBufferMDL == control_expected_mdl);
        IO24_CHECK(!memcmp(request->SetupPacket, control_expected_setup,
                sizeof(control_expected_setup)));
        if (!(control_expected_setup[0] & 0x80) && control_expected_length)
        {
            const UCHAR *payload = request->TransferBufferMDL->MappedSystemVa;
            for (ULONG i = 0; i < control_expected_length; ++i)
                IO24_CHECK(payload && payload[i] == (UCHAR)(0x30 + i));
        }
        IO24_CHECK(active_session_file == control_expected_file);
        /* The production path must keep the caller IRP and file context; no
         * shadow request or raw user pointer is acceptable at this boundary. */
        IO24_CHECK(control_expected_irp != NULL);
        status = control_nt_status;
        if (control_writes_urb_status) request->Hdr.Status = control_urb_status;
        if (NT_SUCCESS(status) && control_urb_status == USBD_STATUS_SUCCESS)
            request->TransferBufferLength = control_actual_length;
    }
    else if (urb->UrbHeader.Function == URB_FUNCTION_SELECT_INTERFACE)
    {
        struct _URB_SELECT_INTERFACE *request = &urb->UrbSelectInterface;
        IO24_CHECK(request->Hdr.Length == offsetof(struct _URB_SELECT_INTERFACE, Interface) + request->Interface.Length);
        ULONG pipe_index;
        IO24_CHECK(request->Interface.InterfaceNumber == expected_alternate_interface &&
                request->Interface.AlternateSetting == expected_alternate_setting &&
                request->Interface.NumberOfPipes == expected_alternate_pipes);
        for (pipe_index = 0; pipe_index < expected_alternate_pipes; ++pipe_index)
            IO24_CHECK(request->Interface.Pipes[pipe_index].EndpointAddress == expected_alternate_endpoints[pipe_index] &&
                    request->Interface.Pipes[pipe_index].PipeType == UsbdPipeTypeBulk &&
                    request->Interface.Pipes[pipe_index].MaximumPacketSize == expected_alternate_packets[pipe_index]);
        select_interface_calls++;
        status = select_nt_status;
        if (NT_SUCCESS(status) && select_writes_urb_status &&
                select_urb_status == USBD_STATUS_SUCCESS)
        {
            request->Hdr.Status = USBD_STATUS_SUCCESS;
            for (pipe_index = 0; pipe_index < expected_alternate_pipes; ++pipe_index)
                request->Interface.Pipes[pipe_index].PipeHandle = (HANDLE)(UINT_PTR)
                        (0x1000 + 0x100 * select_interface_calls + pipe_index + 1);
            if (alternate_mutate_after_select && active_session_file &&
                    active_session_file->FsContext)
                ((struct winusb_file *)active_session_file->FsContext)->state =
                        WINUSB_FILE_CLOSING;
        }
        else request->Hdr.Status = select_writes_urb_status ?
                select_urb_status : USBD_STATUS_REQUEST_FAILED;
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
            if (commit_reentrant_hook) commit_reentrant_hook();
            if (!NT_SUCCESS(commit_failure_status))
            {
                request->Hdr.Status = USBD_STATUS_REQUEST_FAILED;
                status = commit_failure_status;
                goto done;
            }
            lower_claim_committed = TRUE;
        }
        else if (request->Operation == IO24_CLAIM_TRANSACTION_ROLLBACK)
        {
            const struct winusb_file *file = active_session_file ?
                    active_session_file->FsContext : NULL;

            finalize_rollback_calls++;
            /* REMOVE can perform the terminal recovery after CLOSE has freed
             * the file; retained ownership is device-scoped in that case. */
            if (active_session_file)
                IO24_CHECK(file && file->session == 0 && file->snapshot == NULL &&
                        file->interfaces == NULL);
            else IO24_CHECK(active_initialize_output == NULL);
            rollback_saw_unpublished = active_initialize_output != NULL;
            for (i = 0; active_initialize_output && i < 211; ++i)
                if (active_initialize_output[i] != GUARD_BYTE)
                    rollback_saw_unpublished = FALSE;
            if (rollback_failures_remaining)
            {
                rollback_failures_remaining--;
                request->Hdr.Status = USBD_STATUS_REQUEST_FAILED;
                status = rollback_failure_status;
                goto done;
            }
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
    if (original_task9_irp)
    {
        irp->IoStatus.Information = NT_SUCCESS(status) && urb &&
                urb->UrbHeader.Status == USBD_STATUS_SUCCESS ? control_actual_length : 0;
        if (control_returns_pending)
        {
            IO24_CHECK(irp->Tail.Overlay.DriverContext[0] == NULL);
            irp->Tail.Overlay.DriverContext[0] = control_lower_slot0_sentinel;
            control_lower_slot0_installed = TRUE;
            irp->PendingReturned = TRUE;
            if (!control_pending_count)
            {
                control_pending_irp = irp;
                control_pending_stack = next;
                control_pending_device = device;
                control_pending_context = next->Context;
                control_pending_urb = urb;
            }
            else if (control_pending_count == 1)
            {
                control_pending_next_irp = irp;
                control_pending_next_stack = next;
                control_pending_next_device = device;
                control_pending_next_context = next->Context;
                control_pending_next_urb = urb;
            }
            else
            {
                fputs("HARNESS: Task-9 pending fixture capacity exceeded\n", stderr);
                exit(2);
            }
            ++control_pending_count;
            return STATUS_PENDING;
        }
        complete_task9_original_irp(device, irp, next, 1, next->Context, urb);
        return status;
    }
    IO24_CHECK(allocation != NULL);
    if (!allocation) return status;
    if (allocation->iosb) *allocation->iosb = irp->IoStatus;
    if (allocation->event) allocation->event->Header.SignalState = 1;
    forget_builder_irp(allocation);
    memset(allocation, 0xdd, sizeof(*allocation));
    free(allocation);
    builder_frees++;
    return lower_returns_pending ? STATUS_PENDING : status;
}

struct request { uint32_t version,size,session,interface_index,generation,value; unsigned char descriptor[sizeof(mi05_configuration)]; };
struct guarded_request { unsigned char before[16]; struct request request; unsigned char after[16]; };
struct guarded_initialize { unsigned char before[16]; struct wine_winusb_request request; unsigned char after[16]; };
struct guarded_snapshot { unsigned char before[16]; unsigned char bytes[384]; unsigned char after[16]; };

struct dispatch_effect
{
    NTSTATUS status, dispatch_status; ULONG_PTR information;
    unsigned int lower_before,lower_after,complete_before,complete_after;
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

struct guarded_control
{
    unsigned char before[16];
    struct wine_winusb_control_request request;
    unsigned char after[16];
    unsigned char data[WINE_WINUSB_MAX_CONTROL_TRANSFER + 16];
};

struct guarded_descriptor
{
    unsigned char before[16];
    struct wine_winusb_descriptor_request request;
    unsigned char after[16];
    unsigned char data[WINE_WINUSB_MAX_CONTROL_TRANSFER + 16];
};

/* This is intentionally a real METHOD_* direct-I/O shape: private request in
 * SystemBuffer, payload only through the original IRP MDL. */
static struct dispatch_effect dispatch_control(PDRIVER_OBJECT driver, PDEVICE_OBJECT fdo,
        ULONG code, struct guarded_control *guarded, ULONG input_length,
        ULONG output_length, ULONG mdl_length, BOOL attach_mdl, FILE_OBJECT *file)
{
    IRP irp;
    IO_STACK_LOCATION stack[2];
    MDL mdl;
    struct dispatch_effect effect;

    /* The retained CP32 trace is schedule-scoped and only 512 bytes. */
    trace[0] = 0;
    io24_last_completed_irp = NULL;
    io24_completed_irp_count = 0;
    memset(&irp, 0, sizeof(irp));
    memset(stack, 0, sizeof(stack));
    memset(&mdl, 0, sizeof(mdl));
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL;
    stack[1].FileObject = file;
    stack[1].Parameters.DeviceIoControl.IoControlCode = code;
    stack[1].Parameters.DeviceIoControl.InputBufferLength = input_length;
    stack[1].Parameters.DeviceIoControl.OutputBufferLength = output_length;
    irp.AssociatedIrp.SystemBuffer = &guarded->request;
    irp.Tail.Overlay.CurrentStackLocation = &stack[1];
    irp.Tail.Overlay.DriverContext[1] = control_preserved_slots[0];
    irp.Tail.Overlay.DriverContext[2] = control_preserved_slots[1];
    irp.Tail.Overlay.DriverContext[3] = control_preserved_slots[2];
    if (attach_mdl)
    {
        mdl.MdlFlags = MDL_MAPPED_TO_SYSTEM_VA;
        mdl.MappedSystemVa = guarded->data;
        mdl.ByteCount = mdl_length;
        irp.MdlAddress = &mdl;
    }
    effect.lower_before = lower_calls;
    effect.complete_before = completes;
    counts.submits++;
    active_session_file = file;
    control_expected_mdl = attach_mdl ? &mdl : NULL;
    control_expected_irp = &irp;
    effect.dispatch_status = driver->MajorFunction[IRP_MJ_DEVICE_CONTROL](fdo, &irp);
    if (control_pending_irp == &irp || control_pending_next_irp == &irp)
    {
        IO24_CHECK(effect.dispatch_status == STATUS_PENDING);
        IO24_CHECK(complete_pending_task9_irp());
        IO24_CHECK(!complete_pending_task9_irp());
    }
    IO24_CHECK(io24_completed_irp_count == 1);
    IO24_CHECK(io24_last_completed_irp == &irp);
    active_session_file = NULL;
    control_expected_irp = NULL;
    effect.lower_after = lower_calls;
    effect.complete_after = completes;
    effect.status = irp.IoStatus.Status;
    effect.information = irp.IoStatus.Information;
    last_ioctl = code;
    last_status = effect.status;
    mode_ioctls++;
    for (unsigned int i = 0; i < sizeof(guarded->before); ++i)
        IO24_CHECK(guarded->before[i] == GUARD_BYTE && guarded->after[i] == GUARD_BYTE);
    return effect;
}

/* Unlike dispatch_control(), this fixture deliberately leaves its caller-owned
 * IRP, stacks, and MDL live for an interleaving schedule. */
static struct dispatch_effect begin_pending_control(PDRIVER_OBJECT driver, PDEVICE_OBJECT fdo,
        struct guarded_control *guarded, FILE_OBJECT *file, IRP *irp,
        IO_STACK_LOCATION stack[2], MDL *mdl)
{
    struct dispatch_effect effect;

    trace[0] = 0; io24_last_completed_irp = NULL; io24_completed_irp_count = 0;
    memset(irp, 0, sizeof(*irp)); memset(stack, 0, 2 * sizeof(*stack));
    memset(mdl, 0, sizeof(*mdl));
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL; stack[1].FileObject = file;
    stack[1].Parameters.DeviceIoControl.IoControlCode = IOCTL_WINE_WINUSB_CONTROL_IN;
    stack[1].Parameters.DeviceIoControl.InputBufferLength = sizeof(guarded->request);
    stack[1].Parameters.DeviceIoControl.OutputBufferLength = 0;
    irp->AssociatedIrp.SystemBuffer = &guarded->request;
    irp->Tail.Overlay.CurrentStackLocation = &stack[1];
    irp->Tail.Overlay.DriverContext[1] = control_preserved_slots[0];
    irp->Tail.Overlay.DriverContext[2] = control_preserved_slots[1];
    irp->Tail.Overlay.DriverContext[3] = control_preserved_slots[2];
    mdl->MdlFlags = MDL_MAPPED_TO_SYSTEM_VA; mdl->MappedSystemVa = guarded->data;
    mdl->ByteCount = 0; irp->MdlAddress = mdl;
    effect.lower_before = lower_calls; effect.complete_before = completes; counts.submits++;
    active_session_file = file; control_expected_mdl = mdl; control_expected_irp = irp;
    effect.dispatch_status = driver->MajorFunction[IRP_MJ_DEVICE_CONTROL](fdo, irp);
    active_session_file = NULL;
    effect.lower_after = lower_calls; effect.complete_after = completes;
    effect.status = irp->IoStatus.Status; effect.information = irp->IoStatus.Information;
    return effect;
}

static struct dispatch_effect begin_pending_descriptor(PDRIVER_OBJECT driver, PDEVICE_OBJECT fdo,
        struct guarded_descriptor *guarded, FILE_OBJECT *file, IRP *irp,
        IO_STACK_LOCATION stack[2], MDL *mdl)
{
    struct dispatch_effect effect;

    trace[0] = 0; io24_last_completed_irp = NULL; io24_completed_irp_count = 0;
    memset(irp, 0, sizeof(*irp)); memset(stack, 0, 2 * sizeof(*stack)); memset(mdl, 0, sizeof(*mdl));
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL; stack[1].FileObject = file;
    stack[1].Parameters.DeviceIoControl.IoControlCode = IOCTL_WINE_WINUSB_GET_DESCRIPTOR;
    stack[1].Parameters.DeviceIoControl.InputBufferLength = sizeof(guarded->request);
    stack[1].Parameters.DeviceIoControl.OutputBufferLength = guarded->request.length;
    irp->AssociatedIrp.SystemBuffer = &guarded->request;
    irp->Tail.Overlay.CurrentStackLocation = &stack[1];
    irp->Tail.Overlay.DriverContext[1] = control_preserved_slots[0];
    irp->Tail.Overlay.DriverContext[2] = control_preserved_slots[1];
    irp->Tail.Overlay.DriverContext[3] = control_preserved_slots[2];
    mdl->MdlFlags = MDL_MAPPED_TO_SYSTEM_VA; mdl->MappedSystemVa = guarded->data;
    mdl->ByteCount = guarded->request.length; irp->MdlAddress = mdl;
    effect.lower_before = lower_calls; effect.complete_before = completes; counts.submits++;
    active_session_file = file; control_expected_mdl = mdl; control_expected_irp = irp;
    effect.dispatch_status = driver->MajorFunction[IRP_MJ_DEVICE_CONTROL](fdo, irp);
    active_session_file = NULL;
    effect.lower_after = lower_calls; effect.complete_after = completes;
    effect.status = irp->IoStatus.Status; effect.information = irp->IoStatus.Information;
    return effect;
}

struct control_mutex_schedule
{
    DRIVER_OBJECT *driver; DEVICE_OBJECT *fdo; FILE_OBJECT *file;
    struct guarded_control *control; IRP irp; IO_STACK_LOCATION stack[2]; MDL mdl;
    struct dispatch_effect effect;
};
static struct control_mutex_schedule control_mutex_schedule;
static int control_mutex_worker(void *opaque)
{
    struct control_mutex_schedule *schedule = opaque;
    schedule->effect = begin_pending_control(schedule->driver, schedule->fdo,
            schedule->control, schedule->file, &schedule->irp, schedule->stack, &schedule->mdl);
    return 0;
}

/* A failed create/join cannot safely support any production claim.  In
 * particular, post-failed-join shared-state access is a terminal harness bug. */
static void control_thread_terminal(const char *operation)
{
    fprintf(stderr, "HARNESS: Task-9 mutex worker %s failed\n", operation);
    exit(2);
}

static struct dispatch_effect dispatch_descriptor(PDRIVER_OBJECT driver, PDEVICE_OBJECT fdo,
        struct guarded_descriptor *guarded, ULONG input_length, ULONG output_length,
        ULONG mdl_length, BOOL attach_mdl, FILE_OBJECT *file)
{
    IRP irp; IO_STACK_LOCATION stack[2]; MDL mdl; struct dispatch_effect effect;
    /* Keep this large Task-9 matrix from accumulating unrelated CP32 trace. */
    trace[0] = 0;
    io24_last_completed_irp = NULL;
    io24_completed_irp_count = 0;
    memset(&irp, 0, sizeof(irp)); memset(stack, 0, sizeof(stack)); memset(&mdl, 0, sizeof(mdl));
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL; stack[1].FileObject = file;
    stack[1].Parameters.DeviceIoControl.IoControlCode = IOCTL_WINE_WINUSB_GET_DESCRIPTOR;
    stack[1].Parameters.DeviceIoControl.InputBufferLength = input_length;
    stack[1].Parameters.DeviceIoControl.OutputBufferLength = output_length;
    irp.AssociatedIrp.SystemBuffer = &guarded->request;
    irp.Tail.Overlay.CurrentStackLocation = &stack[1];
    irp.Tail.Overlay.DriverContext[1] = control_preserved_slots[0];
    irp.Tail.Overlay.DriverContext[2] = control_preserved_slots[1];
    irp.Tail.Overlay.DriverContext[3] = control_preserved_slots[2];
    if (attach_mdl) { mdl.MdlFlags = MDL_MAPPED_TO_SYSTEM_VA; mdl.MappedSystemVa =
            descriptor_unmapped_mdl ? NULL : guarded->data;
        mdl.ByteCount = mdl_length; irp.MdlAddress = &mdl; }
    effect.lower_before = lower_calls; effect.complete_before = completes; counts.submits++;
    active_session_file = file; control_expected_mdl = attach_mdl ? &mdl : NULL; control_expected_irp = &irp;
    effect.dispatch_status = driver->MajorFunction[IRP_MJ_DEVICE_CONTROL](fdo, &irp);
    if (control_pending_irp == &irp || control_pending_next_irp == &irp)
    {
        IO24_CHECK(effect.dispatch_status == STATUS_PENDING);
        IO24_CHECK(complete_pending_task9_irp());
        IO24_CHECK(!complete_pending_task9_irp());
    }
    IO24_CHECK(io24_completed_irp_count == 1);
    IO24_CHECK(io24_last_completed_irp == &irp);
    active_session_file = NULL; control_expected_irp = NULL;
    effect.lower_after = lower_calls; effect.complete_after = completes;
    effect.status = irp.IoStatus.Status; effect.information = irp.IoStatus.Information;
    last_ioctl = IOCTL_WINE_WINUSB_GET_DESCRIPTOR; last_status = effect.status; mode_ioctls++;
    for (unsigned int i = 0; i < sizeof(guarded->before); ++i)
        IO24_CHECK(guarded->before[i] == GUARD_BYTE && guarded->after[i] == GUARD_BYTE);
    IO24_CHECK(irp.Tail.Overlay.DriverContext[0] == NULL &&
            irp.Tail.Overlay.DriverContext[1] == control_preserved_slots[0] &&
            irp.Tail.Overlay.DriverContext[2] == control_preserved_slots[1] &&
            irp.Tail.Overlay.DriverContext[3] == control_preserved_slots[2]);
    return effect;
}

/* Build the current endpoint map through the existing session IOCTL, rather
 * than writing the parsed state from this contract. */
static NTSTATUS select_control_alternate_status(DRIVER_OBJECT *driver, PDEVICE_OBJECT fdo,
        FILE_OBJECT *file, ULONG interface_index, UCHAR alternate_setting)
{
    struct wine_winusb_alternate_request request;
    struct winusb_file *context = file->FsContext;
    IRP irp;
    IO_STACK_LOCATION stack[2];

    memset(&request, 0, sizeof(request));
    memset(&irp, 0, sizeof(irp));
    memset(stack, 0, sizeof(stack));
    request.request.size = sizeof(request);
    request.request.version = WINE_WINUSB_ABI_VERSION;
    request.request.session = context ? context->session : 0;
    request.request.interface_index = interface_index;
    request.alternate_setting = alternate_setting;
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL;
    stack[1].FileObject = file;
    stack[1].Parameters.DeviceIoControl.IoControlCode = IOCTL_WINE_WINUSB_SET_ALTERNATE;
    stack[1].Parameters.DeviceIoControl.InputBufferLength = sizeof(request);
    stack[1].Parameters.DeviceIoControl.OutputBufferLength = 0;
    irp.AssociatedIrp.SystemBuffer = &request;
    irp.Tail.Overlay.CurrentStackLocation = &stack[1];
    active_session_file = file;
    driver->MajorFunction[IRP_MJ_DEVICE_CONTROL](fdo, &irp);
    active_session_file = NULL;
    IO24_CHECK(irp.IoStatus.Information == 0);
    return irp.IoStatus.Status;
}

static BOOL select_control_alternate(DRIVER_OBJECT *driver, PDEVICE_OBJECT fdo,
        FILE_OBJECT *file, UCHAR alternate_setting)
{
    return NT_SUCCESS(select_control_alternate_status(driver, fdo, file, 0, alternate_setting));
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
    unsigned int builders_before = builder_allocations - builder_frees;
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
    IO24_CHECK(builder_allocations - builder_frees == builders_before);
    if (file && file->FsContext && !concurrent_session_allowed)
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
    FAST_MUTEX session_mutex;
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

struct reentrant_release_schedule
{
    DRIVER_OBJECT *driver;
    FILE_OBJECT *file;
    struct guarded_initialize input;
    struct guarded_snapshot output;
    thrd_t thread;
    atomic_int entered;
    atomic_int completed;
    NTSTATUS status;
    ULONG_PTR information;
    BOOL launched;
};
static struct reentrant_release_schedule reentrant_release;

static int reentrant_release_thread(void *argument)
{
    struct reentrant_release_schedule *schedule = argument;
    IRP irp;
    IO_STACK_LOCATION stack[2];

    memset(&irp, 0, sizeof(irp));
    memset(stack, 0, sizeof(stack));
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL;
    stack[1].FileObject = schedule->file;
    stack[1].Parameters.DeviceIoControl.IoControlCode = IOCTL_WINE_WINUSB_RELEASE;
    stack[1].Parameters.DeviceIoControl.InputBufferLength = sizeof(schedule->input.request);
    irp.AssociatedIrp.SystemBuffer = &schedule->input.request;
    irp.Tail.Overlay.CurrentStackLocation = &stack[1];
    atomic_store(&schedule->entered, 1);
    schedule->driver->MajorFunction[IRP_MJ_DEVICE_CONTROL](last_fdo, &irp);
    schedule->status = irp.IoStatus.Status;
    schedule->information = irp.IoStatus.Information;
    atomic_store(&schedule->completed, 1);
    return 0;
}

static void begin_reentrant_release(void)
{
    struct winusb_file *context = reentrant_release.file->FsContext;
    unsigned int attempts = 0;

    reentrant_release.launched = thrd_create(&reentrant_release.thread,
            reentrant_release_thread, &reentrant_release) == thrd_success;
    IO24_CHECK(reentrant_release.launched);
    while (reentrant_release.launched && !atomic_load(&reentrant_release.entered))
        thrd_yield();
    while (reentrant_release.launched && context->outstanding < 2 &&
            !atomic_load(&reentrant_release.completed) && attempts++ < 1000000)
        thrd_yield();
    IO24_CHECK(reentrant_release.launched &&
            (context->outstanding == 2 || atomic_load(&reentrant_release.completed)));
}

static void reset_attempt_counters(void)
{
    descriptor_reads = select_calls = urb_builds = fail_urb_build = 0;
    finalize_calls = finalize_commit_calls = finalize_rollback_calls = 0;
    builder_allocations = builder_frees = 0;
    mutate_after_select = rollback_saw_unpublished = FALSE;
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
            context->interfaces[0].endpoint_count == 1 &&
            context->interfaces[0].pipes &&
            context->interfaces[0].pipes[0].handle == (HANDLE)(UINT_PTR)0x2082 &&
            context->interfaces[0].pipes[0].endpoint == 0x82 &&
            context->interfaces[0].pipes[0].type == UsbdPipeTypeBulk &&
            context->interfaces[0].pipes[0].maximum_packet_size == 64);
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
    unsigned int allocations_before, frees_before;
    int thread_result;

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

    /* A legacy non-function SELECT has no claim transaction to finalize. */
    setup(&driver,&extension,&pdo,&retained,&file);
    IO24_CHECK(create_file(&driver,&retained,&file));
    reset_initialize_buffers(&input,&output);reset_initialize_lower();
    select_returns_transaction=FALSE;session_allocation_calls=0;
    effect=call_initialize(&driver,&file,&input,&output,211,211,
            &input.request,output.bytes);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.information==211);
    IO24_CHECK(effect.lower_after==effect.lower_before+4&&select_calls==1);
    IO24_CHECK(finalize_calls==0&&finalize_commit_calls==0&&finalize_rollback_calls==0);
    context=file.FsContext;
    IO24_CHECK(context->state==WINUSB_FILE_INITIALIZED&&context->session!=0&&
            context->snapshot!=NULL&&context->interfaces!=NULL);
    lower_claim_pending=FALSE;lower_selected_state=FALSE;
    teardown(&driver,&retained,&file);

    /* Failed COMMIT plus failed ROLLBACK retains the exact device transaction. */
    setup(&driver,&extension,&pdo,&retained,&file);
    IO24_CHECK(create_file(&driver,&retained,&file));
    context=file.FsContext;
    reset_initialize_buffers(&input,&output);reset_initialize_lower();before=output;
    commit_failure_status=STATUS_UNSUCCESSFUL;
    rollback_failure_status=STATUS_DEVICE_BUSY;rollback_failures_remaining=1;
    allocations_before=pool_allocations;frees_before=pool_frees;
    effect=call_initialize(&driver,&file,&input,&output,211,211,
            &input.request,output.bytes);
    IO24_CHECK(effect.status==STATUS_DEVICE_BUSY&&effect.information==0);
    IO24_CHECK(effect.lower_after==effect.lower_before+6&&finalize_commit_calls==1&&
            finalize_rollback_calls==1&&lower_claim_pending&&!lower_claim_committed);
    IO24_CHECK(context->state==WINUSB_FILE_UNINITIALIZED&&context->session==0&&
            context->snapshot==NULL&&context->interfaces==NULL);
    IO24_CHECK(!memcmp(&output,&before,sizeof(output)));
    IO24_CHECK(pool_allocations-allocations_before==(pool_frees-frees_before)+2);

    /* Each later initialize retries once before any SELECT and never spins. */
    reset_initialize_buffers(&input,&output);before=output;reset_attempt_counters();
    commit_failure_status=STATUS_SUCCESS;rollback_failure_status=STATUS_DEVICE_BUSY;
    rollback_failures_remaining=1;
    effect=call_initialize(&driver,&file,&input,&output,211,211,
            &input.request,output.bytes);
    IO24_CHECK(effect.status==STATUS_DEVICE_BUSY&&effect.information==0);
    IO24_CHECK(effect.lower_after==effect.lower_before+1&&descriptor_reads==0&&
            select_calls==0&&finalize_commit_calls==0&&finalize_rollback_calls==1);
    IO24_CHECK(lower_claim_pending&&!memcmp(&output,&before,sizeof(output)));
    IO24_CHECK(pool_allocations-allocations_before==(pool_frees-frees_before)+2);

    reset_initialize_buffers(&input,&output);reset_attempt_counters();
    rollback_failures_remaining=0;
    effect=call_initialize(&driver,&file,&input,&output,211,211,
            &input.request,output.bytes);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.information==211);
    IO24_CHECK(effect.lower_after==effect.lower_before+6&&descriptor_reads==3&&
            select_calls==1&&finalize_commit_calls==1&&finalize_rollback_calls==1);
    IO24_CHECK(!lower_claim_pending&&lower_claim_committed);
    teardown(&driver,&retained,&file);

    /* REMOVE gets one final rollback try; synchronous lower teardown is terminal. */
    setup(&driver,&extension,&pdo,&retained,&file);
    IO24_CHECK(create_file(&driver,&retained,&file));
    reset_initialize_buffers(&input,&output);reset_initialize_lower();before=output;
    commit_failure_status=STATUS_UNSUCCESSFUL;
    rollback_failure_status=STATUS_DEVICE_BUSY;rollback_failures_remaining=2;
    effect=call_initialize(&driver,&file,&input,&output,211,211,
            &input.request,output.bytes);
    IO24_CHECK(effect.status==STATUS_DEVICE_BUSY&&effect.information==0&&
            finalize_commit_calls==1&&finalize_rollback_calls==1&&lower_claim_pending);
    IO24_CHECK(((struct winusb_device *)last_fdo->DeviceExtension)->claim_transaction ==
            lower_transaction_token);
    IO24_CHECK(!memcmp(&output,&before,sizeof(output)));
    effect=dispatch_request(&driver,last_fdo,IRP_MJ_CLEANUP,0,&retained,&file);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&file.FsContext!=NULL);
    effect=dispatch_request(&driver,last_fdo,IRP_MJ_CLOSE,0,&retained,&file);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&file.FsContext==NULL);
    IO24_CHECK(((struct winusb_device *)last_fdo->DeviceExtension)->claim_transaction ==
            lower_transaction_token);
    IO24_CHECK(NT_SUCCESS(dispatch(&driver,last_fdo,IRP_MJ_PNP,IRP_MN_REMOVE_DEVICE)));
    IO24_CHECK(finalize_rollback_calls==2);
    IO24_CHECK(rollback_failures_remaining==0);
    IO24_CHECK(pool_allocations==pool_frees);

    /* A real same-file RELEASE overlaps COMMIT and can run only after copy-out. */
    setup(&driver,&extension,&pdo,&retained,&file);
    IO24_CHECK(create_file(&driver,&retained,&file));
    reset_initialize_buffers(&input,&output);reset_initialize_lower();
    memset(&reentrant_release,0,sizeof(reentrant_release));
    reentrant_release.driver=&driver;reentrant_release.file=&file;
    reset_initialize_buffers(&reentrant_release.input,&reentrant_release.output);
    reentrant_release.input.request.session=1;
    concurrent_session_allowed=TRUE;commit_reentrant_hook=begin_reentrant_release;
    effect=call_initialize(&driver,&file,&input,&output,211,211,
            &input.request,output.bytes);
    IO24_CHECK(reentrant_release.launched);
    if(reentrant_release.launched)
        IO24_CHECK(thrd_join(reentrant_release.thread,&thread_result)==thrd_success&&
                thread_result==0);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.information==211);
    IO24_CHECK(finalize_commit_calls==1&&finalize_rollback_calls==0);
    IO24_CHECK(atomic_load(&reentrant_release.completed)&&
            reentrant_release.status==STATUS_SUCCESS&&reentrant_release.information==0);
    IO24_CHECK(((struct wine_winusb_snapshot *)output.bytes)->session==1);
    check_file_uninitialized(&file);
    concurrent_session_allowed=FALSE;
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
    IO24_CHECK(device->claim_transaction == NULL &&
            device->claim_snapshot == NULL && device->claim_interfaces == NULL);
    effect=dispatch_request(&driver,last_fdo,IRP_MJ_CLEANUP,0,&guarded,&file);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&file.FsContext==context);
    memset(&lifecycle_wait,0,sizeof(lifecycle_wait));
    lifecycle_wait.driver=&driver;lifecycle_wait.guarded=&guarded;
    lifecycle_wait.file=&file;lifecycle_wait.device=device;
    lifecycle_wait.context=context;lifecycle_wait.frees_before=pool_frees;
    lifecycle_wait.expected_close_frees=3;wait_hook=lifecycle_wait_hook;
    IO24_CHECK(context->outstanding == 1 && !context->zero_outstanding.Header.SignalState);
    IO24_CHECK(NT_SUCCESS(dispatch(&driver,last_fdo,IRP_MJ_PNP,
            IRP_MN_REMOVE_DEVICE)));
    IO24_CHECK(lifecycle_wait.removal_waits==1);
    IO24_CHECK(lifecycle_wait.drain_waits==1);
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
{
    DRIVER_OBJECT d; DRIVER_EXTENSION e; DEVICE_OBJECT p; FILE_OBJECT file;
    struct guarded_request g; struct { UCHAR before[16]; struct wine_winusb_alternate_request request; UCHAR after[16]; } input;
    IRP irp; IO_STACK_LOCATION stack[2]; MDL guarded_mdl; struct dispatch_effect effect; struct winusb_file *context;
    struct guarded_initialize initialize; struct guarded_snapshot output;
    unsigned int i, lower_before, allocations_before, frees_before, unknown_frees_before;
    ULONG input_length, output_length;
    ULONG_PTR information;
    PMDL mdl_address;
    HANDLE first_handle;
    NTSTATUS status;
    struct winusb_device *device;
    struct winusb_interface_state before;
#define DISPATCH_ALTERNATE() do { \
    memset(&irp,0,sizeof(irp)); memset(stack,0,sizeof(stack)); \
    stack[1].MajorFunction=IRP_MJ_DEVICE_CONTROL; stack[1].FileObject=&file; \
    stack[1].Parameters.DeviceIoControl.IoControlCode=IO24_IOCTL_SET_ALTERNATE; \
    stack[1].Parameters.DeviceIoControl.InputBufferLength=input_length; \
    stack[1].Parameters.DeviceIoControl.OutputBufferLength=output_length; \
    irp.AssociatedIrp.SystemBuffer=&input.request; irp.MdlAddress=mdl_address; irp.Tail.Overlay.CurrentStackLocation=&stack[1]; \
    active_session_file=&file; d.MajorFunction[IRP_MJ_DEVICE_CONTROL](last_fdo,&irp); active_session_file=NULL; \
} while(0)

    setup(&d,&e,&p,&g,&file); if (!create_file(&d,&g,&file) || !initialize_session(&d,&g,&file)) { teardown(&d,&g,&file); return; }
    memset(&input,GUARD_BYTE,sizeof(input)); memset(&input.request,0,sizeof(input.request));
    context=file.FsContext; device=last_fdo->DeviceExtension;
    input.request.request.size=sizeof(input.request); input.request.request.version=WINE_WINUSB_ABI_VERSION;
    input.request.request.session=context->session; input.request.request.interface_index=0; input.request.alternate_setting=1;
    input_length=sizeof(input.request);output_length=0;mdl_address=NULL;memset(&guarded_mdl,0,sizeof(guarded_mdl));
    before=context->interfaces[0]; lower_before=lower_calls;

    /* Exercise the real session translation unit with a deterministic dirty
     * stack.  Every early exit must own only initialized pointers: invalid
     * state, unknown alternate, and first allocation failure may free none. */
    unknown_frees_before=unknown_pool_frees; information=(ULONG_PTR)0xdeadbeef;
    poison_alternate_stack();
    status=winusb_session_set_alternate(device,context,&input.request,
            sizeof(input.request),&information);
    IO24_CHECK(status==STATUS_INVALID_DEVICE_STATE&&information==0&&
            unknown_pool_frees==unknown_frees_before);
    context->outstanding=1; KeClearEvent(&context->zero_outstanding);
    input.request.alternate_setting=2; information=(ULONG_PTR)0xdeadbeef;
    poison_alternate_stack();
    status=winusb_session_set_alternate(device,context,&input.request,
            sizeof(input.request),&information);
    IO24_CHECK(status==STATUS_INVALID_PARAMETER&&information==0&&
            unknown_pool_frees==unknown_frees_before);
    input.request.alternate_setting=1;
    session_fail_allocation=session_allocation_calls+1;
    poison_alternate_stack();
    status=winusb_session_set_alternate(device,context,&input.request,
            sizeof(input.request),&information);
    IO24_CHECK(status==STATUS_NO_MEMORY&&unknown_pool_frees==unknown_frees_before);
    session_fail_allocation=0; context->outstanding=0;
    KeSetEvent(&context->zero_outstanding,IO_NO_INCREMENT,FALSE);

    input_length=sizeof(input.request)-1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    input_length=sizeof(input.request)+1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    input_length=sizeof(input.request); input.request.request.size--; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    input.request.request.size=sizeof(input.request); input.request.request.version++; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    input.request.request.version=WINE_WINUSB_ABI_VERSION; input.request.request.reserved=1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    input.request.request.reserved=0; input.request.reserved=1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    input.request.reserved=0; input.request.request.session=0; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    input.request.request.session=context->session+1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_DEVICE_STATE&&lower_calls==lower_before);
    input.request.request.session=context->session; output_length=1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    output_length=0; mdl_address=&guarded_mdl; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    mdl_address=NULL;
    input.request.request.interface_index=1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_DEVICE_STATE&&lower_calls==lower_before);
    IO24_CHECK(!memcmp(&before,&context->interfaces[0],sizeof(before)));
    input.request.request.interface_index=0; input.request.alternate_setting=2; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    IO24_CHECK(!memcmp(&before,&context->interfaces[0],sizeof(before)));
    input.request.alternate_setting=1; input.request.reserved=1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_PARAMETER&&lower_calls==lower_before);
    input.request.reserved=0; context->outstanding=1; KeClearEvent(&context->zero_outstanding); DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_DEVICE_STATE&&lower_calls==lower_before);
    context->outstanding=0; KeSetEvent(&context->zero_outstanding,IO_NO_INCREMENT,FALSE);
    allocations_before=pool_allocations;frees_before=pool_frees;
    session_fail_allocation=session_allocation_calls+1; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_NO_MEMORY&&lower_calls==lower_before&&
            pool_allocations-allocations_before==pool_frees-frees_before);
    session_fail_allocation=session_allocation_calls+2; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_NO_MEMORY&&lower_calls==lower_before&&
            pool_allocations-allocations_before==pool_frees-frees_before);
    session_fail_allocation=0; select_nt_status=STATUS_UNSUCCESSFUL; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_UNSUCCESSFUL&&lower_calls==lower_before+1);
    IO24_CHECK(!memcmp(&before,&context->interfaces[0],sizeof(before)));
    select_nt_status=STATUS_SUCCESS;select_urb_status=USBD_STATUS_REQUEST_FAILED;DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_UNSUCCESSFUL&&lower_calls==lower_before+2);
    IO24_CHECK(!memcmp(&before,&context->interfaces[0],sizeof(before)));
    select_urb_status=USBD_STATUS_SUCCESS;alternate_mutate_after_select=TRUE;DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_INVALID_DEVICE_STATE&&lower_calls==lower_before+3);
    IO24_CHECK(!memcmp(&before,&context->interfaces[0],sizeof(before)));
    context->state=WINUSB_FILE_INITIALIZED;alternate_mutate_after_select=FALSE;
    effect.lower_before=lower_calls; effect.complete_before=completes;
    DISPATCH_ALTERNATE(); effect.lower_after=lower_calls; effect.complete_after=completes; effect.status=irp.IoStatus.Status;
    IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.lower_after==effect.lower_before+1&&effect.complete_after==effect.complete_before+1);
    IO24_CHECK(context->interfaces[0].alternate_setting==1&&context->interfaces[0].endpoint_count==2);
    IO24_CHECK(context->interfaces[0].generation==1&&context->interfaces[0].pipes&&
            context->interfaces[0].pipes[0].handle&&
            context->interfaces[0].pipes[0].endpoint==0x81&&
            context->interfaces[0].pipes[0].type==UsbdPipeTypeBulk&&
            context->interfaces[0].pipes[0].maximum_packet_size==512&&
            context->interfaces[0].pipes[1].handle&&
            context->interfaces[0].pipes[1].endpoint==0x01&&
            context->interfaces[0].pipes[1].maximum_packet_size==512);
    first_handle=context->interfaces[0].pipes[0].handle;before=context->interfaces[0]; DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_SUCCESS&&context->interfaces[0].generation==2&&
            context->interfaces[0].pipes!=before.pipes&&context->interfaces[0].pipes[0].handle!=first_handle);
    for(i=0;i<sizeof(input.before);++i)IO24_CHECK(input.before[i]==GUARD_BYTE&&input.after[i]==GUARD_BYTE);
    teardown(&d,&g,&file);

    /* A second real parsed snapshot proves that replacing index 1 cannot
     * disturb index 0.  The configuration selects both default alternates;
     * only MI06 is then moved to its one-pipe alternate. */
    setup(&d,&e,&p,&g,&file); if (!create_file(&d,&g,&file)) { teardown(&d,&g,&file); return; }
    reset_initialize_lower();
    memcpy(lower_configuration,two_interface_configuration,sizeof(two_interface_configuration));
    lower_configuration_size=lower_body_actual=sizeof(two_interface_configuration);
    expected_select_interfaces=2;expected_select_interface_numbers[0]=5;expected_select_interface_numbers[1]=6;
    reset_initialize_buffers(&initialize,&output);session_allocation_calls=0;
    effect=call_initialize(&d,&file,&initialize,&output,229,229,&initialize.request,output.bytes);
    IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.information==229);
    context=file.FsContext;
    IO24_CHECK(context&&context->interface_count==2&&context->interfaces[0].interface_number==5&&
            context->interfaces[0].alternate_setting==0&&context->interfaces[0].pipes==NULL&&
            context->interfaces[1].interface_number==6&&context->interfaces[1].alternate_setting==0&&
            context->interfaces[1].pipes==NULL);
    before=context->interfaces[0];
    memset(&input,GUARD_BYTE,sizeof(input));memset(&input.request,0,sizeof(input.request));
    input.request.request.size=sizeof(input.request);input.request.request.version=WINE_WINUSB_ABI_VERSION;
    input.request.request.session=context->session;input.request.request.interface_index=1;input.request.alternate_setting=1;
    input_length=sizeof(input.request);output_length=0;mdl_address=NULL;
    expected_alternate_interface=6;expected_alternate_setting=1;expected_alternate_pipes=1;
    expected_alternate_endpoints[0]=0x83;expected_alternate_packets[0]=64;
    DISPATCH_ALTERNATE();
    IO24_CHECK(irp.IoStatus.Status==STATUS_SUCCESS&&!memcmp(&before,&context->interfaces[0],sizeof(before))&&
            context->interfaces[1].alternate_setting==1&&context->interfaces[1].endpoint_count==1&&
            context->interfaces[1].pipes&&context->interfaces[1].pipes[0].endpoint==0x83&&
            context->interfaces[1].pipes[0].type==UsbdPipeTypeBulk&&
            context->interfaces[1].pipes[0].maximum_packet_size==64&&context->interfaces[1].pipes[0].handle);
    teardown(&d,&g,&file);
#undef DISPATCH_ALTERNATE
}
static void group_policy(void)
{
    DRIVER_OBJECT d; DRIVER_EXTENSION e; DEVICE_OBJECT p; FILE_OBJECT file;
    struct guarded_request g; struct dispatch_effect effect;
    struct { UCHAR before[16]; struct wine_winusb_policy_request request; UCHAR after[16]; } input;
    struct wine_winusb_policy_request request_before;
    struct wine_winusb_alternate_request alternate;
    IRP irp; IO_STACK_LOCATION stack[2]; struct winusb_file *context;
    ULONG input_length, output_length, lower_before, policy_interface; NTSTATUS status;
    unsigned int i;
    static const struct { UCHAR pipe, policy; ULONG length, value; } defaults[] =
    {
        {0x01, SHORT_PACKET_TERMINATE, 1, 0},
        {0x01, PIPE_TRANSFER_TIMEOUT, 4, 0},
        {0x01, MAXIMUM_TRANSFER_SIZE, 4, 4 * 1024 * 1024},
        {0x01, RESET_PIPE_ON_RESUME, 1, 0},
        {0x81, AUTO_CLEAR_STALL, 1, 0},
        {0x81, PIPE_TRANSFER_TIMEOUT, 4, 0},
        {0x81, IGNORE_SHORT_PACKETS, 1, 0},
        {0x81, ALLOW_PARTIAL_READS, 1, 1},
        {0x81, AUTO_FLUSH, 1, 0},
        {0x81, RAW_IO, 1, 0},
        {0x81, MAXIMUM_TRANSFER_SIZE, 4, 4 * 1024 * 1024},
        {0x81, RESET_PIPE_ON_RESUME, 1, 0},
    };
    static const UCHAR pre_alternate_pipes[] = {0, 0x01, 0x81};

#define POLICY_CALL(code) do { \
    memset(&irp, 0, sizeof(irp)); memset(stack, 0, sizeof(stack)); \
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL; stack[1].FileObject = &file; \
    stack[1].Parameters.DeviceIoControl.IoControlCode = (code); \
    stack[1].Parameters.DeviceIoControl.InputBufferLength = input_length; \
    stack[1].Parameters.DeviceIoControl.OutputBufferLength = output_length; \
    irp.AssociatedIrp.SystemBuffer = &input.request; irp.Tail.Overlay.CurrentStackLocation = &stack[1]; \
    d.MajorFunction[IRP_MJ_DEVICE_CONTROL](last_fdo, &irp); status = irp.IoStatus.Status; \
    /* The retained lifecycle fake appends every completion to its fixed 512-byte
     * trace. Policy intentionally executes far more than that legacy budget;
     * its trace is not a policy oracle, so retain no stale completion history. */ \
    trace[0] = 0; \
} while (0)
#define POLICY_SEED(PIP, PID, LEN, VAL) do { \
    memset(&input.request, 0, sizeof(input.request)); \
    input.request.request.size = sizeof(input.request); \
    input.request.request.version = WINE_WINUSB_ABI_VERSION; \
    input.request.request.session = context->session; \
    input.request.request.interface_index = policy_interface; \
    input.request.pipe_id = (PIP); input.request.policy_id = (PID); \
    input.request.value_length = (LEN); input.request.value = (VAL); \
} while (0)
#define POLICY_GET(PIP, PID, LEN, VAL) do { \
    POLICY_SEED((PIP), (PID), (LEN), 0xdeadbeef); \
    input_length = output_length = sizeof(input.request); \
    POLICY_CALL(IO24_IOCTL_GET_POLICY); \
    IO24_CHECK(status == STATUS_SUCCESS && irp.IoStatus.Information == sizeof(input.request)); \
    IO24_CHECK(input.request.request.size == sizeof(input.request) && \
            input.request.request.version == WINE_WINUSB_ABI_VERSION && \
            input.request.request.session == context->session && \
            input.request.request.interface_index == policy_interface && input.request.request.reserved == 0); \
    IO24_CHECK(input.request.pipe_id == (PIP) && input.request.policy_id == (PID) && \
            input.request.value_length == (LEN) && input.request.value == (VAL)); \
    IO24_CHECK(lower_calls == lower_before); \
} while (0)
#define POLICY_GET_CAP(PIP, PID, CAP, REQUIRED, VAL) do { \
    POLICY_SEED((PIP), (PID), (CAP), 0xdeadbeef); \
    input_length = output_length = sizeof(input.request); \
    POLICY_CALL(IO24_IOCTL_GET_POLICY); \
    IO24_CHECK(status == STATUS_SUCCESS && irp.IoStatus.Information == sizeof(input.request)); \
    IO24_CHECK(input.request.request.size == sizeof(input.request) && \
            input.request.request.version == WINE_WINUSB_ABI_VERSION && \
            input.request.request.session == context->session && \
            input.request.request.interface_index == policy_interface && input.request.request.reserved == 0); \
    IO24_CHECK(input.request.pipe_id == (PIP) && input.request.policy_id == (PID) && \
            input.request.value_length == (REQUIRED) && input.request.value == (VAL)); \
    IO24_CHECK(lower_calls == lower_before); \
} while (0)
#define POLICY_SET(PIP, PID, LEN, VAL, EXPECT) do { \
    POLICY_SEED((PIP), (PID), (LEN), (VAL)); \
    input_length = sizeof(input.request); output_length = 0; request_before = input.request; \
    POLICY_CALL(IO24_IOCTL_SET_POLICY); \
    IO24_CHECK(status == (EXPECT) && irp.IoStatus.Information == 0 && lower_calls == lower_before); \
    if ((EXPECT) != STATUS_SUCCESS) IO24_CHECK(!memcmp(&input.request, &request_before, sizeof(request_before))); \
} while (0)
#define POLICY_REJECT_GET(PIP, PID, LEN, EXPECT) do { \
    POLICY_SEED((PIP), (PID), (LEN), 0xdeadbeef); \
    input_length = output_length = sizeof(input.request); request_before = input.request; \
    POLICY_CALL(IO24_IOCTL_GET_POLICY); \
    IO24_CHECK(status == (EXPECT) && irp.IoStatus.Information == 0 && \
            !memcmp(&input.request, &request_before, sizeof(request_before)) && \
            lower_calls == lower_before); \
} while (0)
#define POLICY_REJECT_CURRENT_GET(EXPECT) do { \
    input_length = output_length = sizeof(input.request); request_before = input.request; \
    POLICY_CALL(IO24_IOCTL_GET_POLICY); \
    IO24_CHECK(status == (EXPECT) && irp.IoStatus.Information == 0 && \
            !memcmp(&input.request, &request_before, sizeof(request_before)) && \
            lower_calls == lower_before); \
} while (0)
#define POLICY_REJECT_CURRENT_SET(EXPECT) do { \
    input_length = sizeof(input.request); output_length = 0; request_before = input.request; \
    POLICY_CALL(IO24_IOCTL_SET_POLICY); \
    IO24_CHECK(status == (EXPECT) && irp.IoStatus.Information == 0 && \
            !memcmp(&input.request, &request_before, sizeof(request_before)) && \
            lower_calls == lower_before); \
} while (0)
#define ALTERNATE_CALL(index, setting) do { \
    memset(&alternate, 0, sizeof(alternate)); \
    alternate.request.size = sizeof(alternate); alternate.request.version = WINE_WINUSB_ABI_VERSION; \
    alternate.request.session = context->session; alternate.request.interface_index = (index); \
    alternate.alternate_setting = (setting); \
    memset(&irp, 0, sizeof(irp)); memset(stack, 0, sizeof(stack)); \
    stack[1].MajorFunction = IRP_MJ_DEVICE_CONTROL; stack[1].FileObject = &file; \
    stack[1].Parameters.DeviceIoControl.IoControlCode = IO24_IOCTL_SET_ALTERNATE; \
    stack[1].Parameters.DeviceIoControl.InputBufferLength = sizeof(alternate); \
    irp.AssociatedIrp.SystemBuffer = &alternate; irp.Tail.Overlay.CurrentStackLocation = &stack[1]; \
    active_session_file = &file; d.MajorFunction[IRP_MJ_DEVICE_CONTROL](last_fdo, &irp); active_session_file = NULL; \
    trace[0] = 0; \
    status = irp.IoStatus.Status; \
} while (0)

    setup(&d, &e, &p, &g, &file);
    if (!create_file(&d, &g, &file) || !initialize_session(&d, &g, &file)) { teardown(&d, &g, &file); return; }
    context = file.FsContext;
    memset(&input, GUARD_BYTE, sizeof(input)); lower_before = lower_calls; policy_interface = 0;

    /* Pipe ID zero is not a wildcard, and alternate zero exposes no pipes. */
    for (i = 0; i < 3; ++i)
    {
        POLICY_SET(pre_alternate_pipes[i], RAW_IO, 1, 0, STATUS_INVALID_PARAMETER);
        POLICY_SEED(pre_alternate_pipes[i], RAW_IO, 1, 0xdeadbeef);
        input_length = output_length = sizeof(input.request); request_before = input.request;
        POLICY_CALL(IO24_IOCTL_GET_POLICY);
        IO24_CHECK(status == STATUS_INVALID_PARAMETER && irp.IoStatus.Information == 0 &&
                !memcmp(&input.request, &request_before, sizeof(request_before)) && lower_calls == lower_before);
    }

    ALTERNATE_CALL(0, 1);
    IO24_CHECK(status == STATUS_SUCCESS && lower_calls == lower_before + 1);
    lower_before = lower_calls;

    /* Every current pipe has exact defaults, including the 4 MiB maximum. */
    for (i = 0; i < ARRAY_SIZE(defaults); ++i)
        POLICY_GET(defaults[i].pipe, defaults[i].policy, defaults[i].length, defaults[i].value);

    /* After alternate 1, neither zero nor a same-direction stale endpoint is
     * admitted by either private policy operation. */
    POLICY_REJECT_GET(0, RAW_IO, 1, STATUS_INVALID_PARAMETER);
    POLICY_SET(0, RAW_IO, 1, 1, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x82, RAW_IO, 1, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x82, RAW_IO, 1, 1, STATUS_INVALID_PARAMETER);

    /* The private ABI is exactly 40 bytes on both input and GET output. */
    POLICY_SEED(0x81, MAXIMUM_TRANSFER_SIZE, 4, 0);
    input_length = sizeof(input.request) - 1; output_length = sizeof(input.request); request_before = input.request;
    POLICY_CALL(IO24_IOCTL_GET_POLICY); IO24_CHECK(status == STATUS_INVALID_PARAMETER && irp.IoStatus.Information == 0 && !memcmp(&input.request, &request_before, sizeof(request_before)) && lower_calls == lower_before);
    input_length = sizeof(input.request) + 1; POLICY_CALL(IO24_IOCTL_GET_POLICY); IO24_CHECK(status == STATUS_INVALID_PARAMETER && irp.IoStatus.Information == 0 && !memcmp(&input.request, &request_before, sizeof(request_before)) && lower_calls == lower_before);
    input_length = sizeof(input.request); output_length = sizeof(input.request) - 1; POLICY_CALL(IO24_IOCTL_GET_POLICY); IO24_CHECK(status == STATUS_INVALID_PARAMETER && irp.IoStatus.Information == 0 && !memcmp(&input.request, &request_before, sizeof(request_before)) && lower_calls == lower_before);
    output_length = sizeof(input.request) + 1; POLICY_CALL(IO24_IOCTL_GET_POLICY); IO24_CHECK(status == STATUS_INVALID_PARAMETER && irp.IoStatus.Information == 0 && !memcmp(&input.request, &request_before, sizeof(request_before)) && lower_calls == lower_before);
    output_length = sizeof(input.request); input.request.request.size--; POLICY_REJECT_CURRENT_GET(STATUS_INVALID_PARAMETER); input.request.request.size++;
    input.request.request.version++; POLICY_REJECT_CURRENT_GET(STATUS_INVALID_PARAMETER); input.request.request.version--;
    input.request.request.session = 0; POLICY_REJECT_CURRENT_GET(STATUS_INVALID_PARAMETER); input.request.request.session = context->session + 1;
    POLICY_REJECT_CURRENT_GET(STATUS_INVALID_DEVICE_STATE); input.request.request.session = context->session;
    input.request.request.interface_index = 1; POLICY_REJECT_CURRENT_GET(STATUS_INVALID_DEVICE_STATE); input.request.request.interface_index = 0;
    input.request.request.reserved = 1; POLICY_REJECT_CURRENT_GET(STATUS_INVALID_PARAMETER); input.request.request.reserved = 0;
    IO24_CHECK(lower_calls == lower_before);

    /* GET validates the same direction/policy/value-size profile without
     * changing the caller buffer, policy state, or lower transport count. */
    POLICY_REJECT_GET(0x81, SHORT_PACKET_TERMINATE, 1, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x01, AUTO_CLEAR_STALL, 1, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x01, IGNORE_SHORT_PACKETS, 1, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x01, ALLOW_PARTIAL_READS, 1, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x01, AUTO_FLUSH, 1, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x01, RAW_IO, 1, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x81, 10, 1, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x81, RAW_IO, 0, STATUS_INVALID_PARAMETER);
    POLICY_REJECT_GET(0x81, PIPE_TRANSFER_TIMEOUT, 1, STATUS_INVALID_PARAMETER);
    /* GET's value_length is caller capacity, then the exact required length.
     * This mirrors the accepted public 8-byte-capacity / 4-byte-result path. */
    POLICY_GET_CAP(0x81, RAW_IO, 2, 1, 0);
    POLICY_GET_CAP(0x81, MAXIMUM_TRANSFER_SIZE, 5, 4, 4 * 1024 * 1024);

    /* SET has its own complete header validator; a permissive SET path must
     * not inherit confidence from the corresponding GET checks above. */
    POLICY_SEED(0x81, RAW_IO, 1, 0);
    input.request.request.size--; POLICY_REJECT_CURRENT_SET(STATUS_INVALID_PARAMETER); input.request.request.size++;
    input.request.request.version++; POLICY_REJECT_CURRENT_SET(STATUS_INVALID_PARAMETER); input.request.request.version--;
    input.request.request.session = 0; POLICY_REJECT_CURRENT_SET(STATUS_INVALID_PARAMETER); input.request.request.session = context->session + 1;
    POLICY_REJECT_CURRENT_SET(STATUS_INVALID_DEVICE_STATE); input.request.request.session = context->session;
    input.request.request.interface_index = 1; POLICY_REJECT_CURRENT_SET(STATUS_INVALID_DEVICE_STATE); input.request.request.interface_index = 0;
    input.request.request.reserved = 1; POLICY_REJECT_CURRENT_SET(STATUS_INVALID_PARAMETER); input.request.request.reserved = 0;

    /* Direction, exact lengths, and read-only maximum all reject without mutation. */
    POLICY_SET(0x81, SHORT_PACKET_TERMINATE, 1, 0, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x01, AUTO_CLEAR_STALL, 1, 0, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x01, IGNORE_SHORT_PACKETS, 1, 0, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x01, ALLOW_PARTIAL_READS, 1, 0, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x01, AUTO_FLUSH, 1, 0, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x01, RAW_IO, 1, 0, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x81, PIPE_TRANSFER_TIMEOUT, 1, 1, STATUS_INVALID_PARAMETER);
    POLICY_GET(0x81, PIPE_TRANSFER_TIMEOUT, 4, 0);
    POLICY_SET(0x81, PIPE_TRANSFER_TIMEOUT, 3, 1, STATUS_INVALID_PARAMETER);
    POLICY_GET(0x81, PIPE_TRANSFER_TIMEOUT, 4, 0);
    POLICY_SET(0x81, PIPE_TRANSFER_TIMEOUT, 5, 0, STATUS_INVALID_PARAMETER);
    POLICY_GET(0x81, PIPE_TRANSFER_TIMEOUT, 4, 0);
    POLICY_SET(0x81, RAW_IO, 1, 1, STATUS_SUCCESS);
    POLICY_SET(0x81, RAW_IO, 0, 0, STATUS_INVALID_PARAMETER);
    POLICY_GET(0x81, RAW_IO, 1, 1);
    POLICY_SET(0x81, RAW_IO, 2, 0, STATUS_INVALID_PARAMETER);
    POLICY_GET(0x81, RAW_IO, 1, 1);
    POLICY_SET(0x01, MAXIMUM_TRANSFER_SIZE, 4, 0x01000000, STATUS_INVALID_PARAMETER);
    POLICY_GET(0x01, MAXIMUM_TRANSFER_SIZE, 4, 4 * 1024 * 1024);
    POLICY_SET(0x81, MAXIMUM_TRANSFER_SIZE, 4, 0x01000000, STATUS_INVALID_PARAMETER);
    POLICY_GET(0x81, MAXIMUM_TRANSFER_SIZE, 4, 4 * 1024 * 1024);
    POLICY_SET(0x81, 10, 1, 0, STATUS_INVALID_PARAMETER);

    /* SET is exactly 40 input bytes and no output bytes. */
    POLICY_SEED(0x81, RAW_IO, 1, 0); request_before = input.request;
    input_length = sizeof(input.request) - 1; output_length = 0; POLICY_CALL(IO24_IOCTL_SET_POLICY);
    IO24_CHECK(status == STATUS_INVALID_PARAMETER && irp.IoStatus.Information == 0 &&
            !memcmp(&input.request, &request_before, sizeof(request_before)) && lower_calls == lower_before);
    input_length = sizeof(input.request) + 1; POLICY_CALL(IO24_IOCTL_SET_POLICY);
    IO24_CHECK(status == STATUS_INVALID_PARAMETER && irp.IoStatus.Information == 0 &&
            !memcmp(&input.request, &request_before, sizeof(request_before)) && lower_calls == lower_before);
    input_length = sizeof(input.request); output_length = 1; POLICY_CALL(IO24_IOCTL_SET_POLICY);
    IO24_CHECK(status == STATUS_INVALID_PARAMETER && irp.IoStatus.Information == 0 &&
            !memcmp(&input.request, &request_before, sizeof(request_before)) && lower_calls == lower_before);

    /* Supported false settings commit and read back; both IN toggles accept both values. */
    POLICY_SET(0x01, SHORT_PACKET_TERMINATE, 1, 0, STATUS_SUCCESS); POLICY_GET(0x01, SHORT_PACKET_TERMINATE, 1, 0);
    POLICY_SET(0x81, AUTO_CLEAR_STALL, 1, 0, STATUS_SUCCESS); POLICY_GET(0x81, AUTO_CLEAR_STALL, 1, 0);
    POLICY_SET(0x01, PIPE_TRANSFER_TIMEOUT, 4, 0, STATUS_SUCCESS); POLICY_GET(0x01, PIPE_TRANSFER_TIMEOUT, 4, 0);
    POLICY_SET(0x81, PIPE_TRANSFER_TIMEOUT, 4, 0, STATUS_SUCCESS); POLICY_GET(0x81, PIPE_TRANSFER_TIMEOUT, 4, 0);
    POLICY_SET(0x81, IGNORE_SHORT_PACKETS, 1, 0, STATUS_SUCCESS); POLICY_GET(0x81, IGNORE_SHORT_PACKETS, 1, 0);
    POLICY_SET(0x81, ALLOW_PARTIAL_READS, 1, 0, STATUS_SUCCESS); POLICY_GET(0x81, ALLOW_PARTIAL_READS, 1, 0);
    POLICY_SET(0x81, ALLOW_PARTIAL_READS, 1, 1, STATUS_SUCCESS); POLICY_GET(0x81, ALLOW_PARTIAL_READS, 1, 1);
    POLICY_SET(0x81, AUTO_FLUSH, 1, 0, STATUS_SUCCESS); POLICY_GET(0x81, AUTO_FLUSH, 1, 0);
    POLICY_SET(0x81, RAW_IO, 1, 1, STATUS_SUCCESS); POLICY_GET(0x81, RAW_IO, 1, 1);
    POLICY_SET(0x81, RAW_IO, 1, 0, STATUS_SUCCESS); POLICY_GET(0x81, RAW_IO, 1, 0);
    POLICY_SET(0x01, RESET_PIPE_ON_RESUME, 1, 0, STATUS_SUCCESS); POLICY_GET(0x01, RESET_PIPE_ON_RESUME, 1, 0);
    POLICY_SET(0x81, RESET_PIPE_ON_RESUME, 1, 0, STATUS_SUCCESS); POLICY_GET(0x81, RESET_PIPE_ON_RESUME, 1, 0);

    /* Every prohibited enabled value returns NOT_SUPPORTED and leaves prior state intact. */
    POLICY_SET(0x01, SHORT_PACKET_TERMINATE, 1, 1, STATUS_NOT_SUPPORTED); POLICY_GET(0x01, SHORT_PACKET_TERMINATE, 1, 0);
    POLICY_SET(0x81, AUTO_CLEAR_STALL, 1, 1, STATUS_NOT_SUPPORTED); POLICY_GET(0x81, AUTO_CLEAR_STALL, 1, 0);
    POLICY_SET(0x01, PIPE_TRANSFER_TIMEOUT, 4, 1, STATUS_NOT_SUPPORTED); POLICY_GET(0x01, PIPE_TRANSFER_TIMEOUT, 4, 0);
    POLICY_SET(0x81, PIPE_TRANSFER_TIMEOUT, 4, 1, STATUS_NOT_SUPPORTED); POLICY_GET(0x81, PIPE_TRANSFER_TIMEOUT, 4, 0);
    POLICY_SET(0x81, IGNORE_SHORT_PACKETS, 1, 1, STATUS_NOT_SUPPORTED); POLICY_GET(0x81, IGNORE_SHORT_PACKETS, 1, 0);
    POLICY_SET(0x81, AUTO_FLUSH, 1, 1, STATUS_NOT_SUPPORTED); POLICY_GET(0x81, AUTO_FLUSH, 1, 0);
    POLICY_SET(0x01, RESET_PIPE_ON_RESUME, 1, 1, STATUS_NOT_SUPPORTED); POLICY_GET(0x01, RESET_PIPE_ON_RESUME, 1, 0);
    POLICY_SET(0x81, RESET_PIPE_ON_RESUME, 1, 1, STATUS_NOT_SUPPORTED); POLICY_GET(0x81, RESET_PIPE_ON_RESUME, 1, 0);

    /* A lower alternate failure preserves the complete current policy map. */
    POLICY_SET(0x01, SHORT_PACKET_TERMINATE, 1, 0, STATUS_SUCCESS);
    POLICY_SET(0x81, ALLOW_PARTIAL_READS, 1, 0, STATUS_SUCCESS);
    POLICY_SET(0x81, RAW_IO, 1, 1, STATUS_SUCCESS);
    select_nt_status = STATUS_UNSUCCESSFUL; ALTERNATE_CALL(0, 1);
    IO24_CHECK(status == STATUS_UNSUCCESSFUL && lower_calls == lower_before + 1);
    select_nt_status = STATUS_SUCCESS; lower_before = lower_calls;
    POLICY_GET(0x01, SHORT_PACKET_TERMINATE, 1, 0);
    POLICY_GET(0x81, ALLOW_PARTIAL_READS, 1, 0);
    POLICY_GET(0x81, RAW_IO, 1, 1);

    select_urb_status = USBD_STATUS_REQUEST_FAILED; ALTERNATE_CALL(0, 1);
    IO24_CHECK(status == STATUS_UNSUCCESSFUL && lower_calls == lower_before + 1);
    select_urb_status = USBD_STATUS_SUCCESS; lower_before = lower_calls;
    POLICY_GET(0x01, SHORT_PACKET_TERMINATE, 1, 0);
    POLICY_GET(0x81, ALLOW_PARTIAL_READS, 1, 0);
    POLICY_GET(0x81, RAW_IO, 1, 1);

    alternate_mutate_after_select = TRUE; ALTERNATE_CALL(0, 1);
    IO24_CHECK(status == STATUS_INVALID_DEVICE_STATE && lower_calls == lower_before + 1);
    context->state = WINUSB_FILE_INITIALIZED; alternate_mutate_after_select = FALSE;
    lower_before = lower_calls;
    POLICY_GET(0x01, SHORT_PACKET_TERMINATE, 1, 0);
    POLICY_GET(0x81, ALLOW_PARTIAL_READS, 1, 0);
    POLICY_GET(0x81, RAW_IO, 1, 1);

    /* A successful replacement resets only its target's new pipes. */
    ALTERNATE_CALL(0, 1); IO24_CHECK(status == STATUS_SUCCESS && lower_calls == lower_before + 1); lower_before = lower_calls;
    for (i = 0; i < ARRAY_SIZE(defaults); ++i)
        POLICY_GET(defaults[i].pipe, defaults[i].policy, defaults[i].length, defaults[i].value);

    /* An associated interface retains its map while the root is replaced. */
    teardown(&d, &g, &file);
    setup(&d, &e, &p, &g, &file);
    if (!create_file(&d, &g, &file)) { teardown(&d, &g, &file); return; }
    reset_initialize_lower();
    memcpy(lower_configuration, two_interface_policy_configuration, sizeof(two_interface_policy_configuration));
    lower_configuration_size = lower_body_actual = sizeof(two_interface_policy_configuration);
    expected_select_interfaces = 2; expected_select_interface_numbers[0] = 5;
    expected_select_interface_numbers[1] = 6;
    {
        struct guarded_initialize initialize;
        struct guarded_snapshot output;
        reset_initialize_buffers(&initialize, &output); session_allocation_calls = 0;
        effect = call_initialize(&d, &file, &initialize, &output, 300, 300,
                &initialize.request, output.bytes);
        IO24_CHECK(effect.status == STATUS_SUCCESS && effect.information == 300);
    }
    context = file.FsContext; policy_interface = 0;
    lower_before = lower_calls; ALTERNATE_CALL(0, 1);
    IO24_CHECK(status == STATUS_SUCCESS && lower_calls == lower_before + 1);
    expected_alternate_interface = 6; expected_alternate_setting = 1;
    expected_alternate_pipes = 1; expected_alternate_endpoints[0] = 0x83;
    expected_alternate_packets[0] = 64; lower_before = lower_calls;
    ALTERNATE_CALL(1, 1); IO24_CHECK(status == STATUS_SUCCESS && lower_calls == lower_before + 1);
    lower_before = lower_calls;
    /* A handle resolves only its own current interface pipes. */
    policy_interface = 0; POLICY_REJECT_GET(0x83, RAW_IO, 1, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x83, RAW_IO, 1, 1, STATUS_INVALID_PARAMETER);
    policy_interface = 1; POLICY_REJECT_GET(0x81, RAW_IO, 1, STATUS_INVALID_PARAMETER);
    POLICY_SET(0x81, RAW_IO, 1, 1, STATUS_INVALID_PARAMETER);
    policy_interface = 0;
    POLICY_SET(0x81, RAW_IO, 1, 1, STATUS_SUCCESS);
    policy_interface = 1; POLICY_SET(0x83, RAW_IO, 1, 1, STATUS_SUCCESS);
    policy_interface = 0; expected_alternate_interface = 5; expected_alternate_pipes = 2;
    expected_alternate_endpoints[0] = 0x81; expected_alternate_endpoints[1] = 0x01;
    expected_alternate_packets[0] = expected_alternate_packets[1] = 512;
    ALTERNATE_CALL(0, 1); IO24_CHECK(status == STATUS_SUCCESS && lower_calls == lower_before + 1);
    lower_before = lower_calls; POLICY_GET(0x81, RAW_IO, 1, 0);
    policy_interface = 1; POLICY_GET(0x83, RAW_IO, 1, 1);
    policy_interface = 0;
    for (unsigned int i = 0; i < sizeof(input.before); ++i) IO24_CHECK(input.before[i] == GUARD_BYTE && input.after[i] == GUARD_BYTE);
    teardown(&d, &g, &file);

    /* The parsed current map can contain a non-bulk endpoint; policy applies
     * only to the exact bulk vendor profile, before either value is touched. */
    setup(&d, &e, &p, &g, &file); if (!create_file(&d, &g, &file)) { teardown(&d, &g, &file); return; }
    reset_initialize_lower();
    memcpy(lower_configuration, nonbulk_endpoint_configuration, sizeof(nonbulk_endpoint_configuration));
    lower_configuration_size = lower_body_actual = sizeof(nonbulk_endpoint_configuration);
    expected_select_pipes = 1; expected_select_endpoint = 0x82;
    expected_select_type = UsbdPipeTypeInterrupt; expected_select_packet_size = 64;
    {
        struct guarded_initialize initialize;
        struct guarded_snapshot output;
        struct winusb_pipe_state pipe_before;
        reset_initialize_buffers(&initialize, &output); session_allocation_calls = 0;
        effect = call_initialize(&d, &file, &initialize, &output, 163, 163,
                &initialize.request, output.bytes);
        IO24_CHECK(effect.status == STATUS_SUCCESS && effect.information == 163);
        context = file.FsContext; policy_interface = 0; lower_before = lower_calls;
        IO24_CHECK(context && context->interfaces[0].endpoint_count == 1 &&
                context->interfaces[0].pipes[0].endpoint == 0x82 &&
                context->interfaces[0].pipes[0].type == UsbdPipeTypeInterrupt);
        pipe_before = context->interfaces[0].pipes[0];
        POLICY_REJECT_GET(0x82, RAW_IO, 1, STATUS_INVALID_PARAMETER);
        IO24_CHECK(!memcmp(&pipe_before, &context->interfaces[0].pipes[0], sizeof(pipe_before)));
        POLICY_SET(0x82, RAW_IO, 1, 1, STATUS_INVALID_PARAMETER);
        IO24_CHECK(!memcmp(&pipe_before, &context->interfaces[0].pipes[0], sizeof(pipe_before)));
    }
    teardown(&d, &g, &file);
#undef POLICY_CALL
#undef POLICY_SEED
#undef POLICY_GET
#undef POLICY_GET_CAP
#undef POLICY_SET
#undef POLICY_REJECT_GET
#undef POLICY_REJECT_CURRENT_GET
#undef POLICY_REJECT_CURRENT_SET
#undef ALTERNATE_CALL
}
static void group_transfer(void)
{DRIVER_OBJECT d;DRIVER_EXTENSION e;DEVICE_OBJECT p;FILE_OBJECT file;struct guarded_request g;struct dispatch_effect effect;BOOL opened,initialized;setup(&d,&e,&p,&g,&file);opened=create_file(&d,&g,&file);initialized=initialize_session(&d,&g,&file);if(!opened||!initialized){dispatch_safe_rejection(&d,&g,&file,IO24_IOCTL_READ_PIPE);teardown(&d,&g,&file);return;}g.request.value=1;effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_SET_ALTERNATE,&g,&file);IO24_CHECK(effect.status==STATUS_SUCCESS&&effect.lower_after==effect.lower_before+1);effect=dispatch_request(&d,last_fdo,IRP_MJ_DEVICE_CONTROL,IO24_IOCTL_READ_PIPE,&g,&file);IO24_CHECK(effect.status==STATUS_PENDING);IO24_CHECK(effect.lower_after==effect.lower_before+1);IO24_CHECK(effect.complete_after==effect.complete_before);teardown(&d,&g,&file);}
static void group_control_descriptor(void)
{
    DRIVER_OBJECT d; DRIVER_EXTENSION e; DEVICE_OBJECT p; FILE_OBJECT file;
    struct guarded_request g; struct guarded_control control; struct guarded_descriptor descriptor;
    struct dispatch_effect effect; BOOL opened, initialized;
    const ULONG lengths[] = {0, 1, 37, WINE_WINUSB_MAX_CONTROL_TRANSFER};
    const ULONG codes[] = {IOCTL_WINE_WINUSB_CONTROL_IN, IOCTL_WINE_WINUSB_CONTROL_OUT};
    const UCHAR types[] = {0x00, 0x20, 0x40}; /* standard, class, vendor */
    const UCHAR recipients[] = {0, 1, 2, 3}; /* device, interface, endpoint, other */

    setup(&d, &e, &p, &g, &file);
    opened = create_file(&d, &g, &file);
    initialized = initialize_session(&d, &g, &file);
    if (!opened || !initialized)
    {
        dispatch_safe_rejection(&d, &g, &file, IOCTL_WINE_WINUSB_CONTROL_IN);
        teardown(&d, &g, &file);
        return;
    }

    /* ABI and IOCTL-method contract.  These assertions keep the test bound
     * to the production private interface rather than a test-only surrogate. */
    IO24_CHECK(sizeof(control.request) == 40);
    IO24_CHECK((IOCTL_WINE_WINUSB_CONTROL_IN & 3) == METHOD_OUT_DIRECT);
    IO24_CHECK((IOCTL_WINE_WINUSB_CONTROL_OUT & 3) == METHOD_IN_DIRECT);
    IO24_CHECK((IOCTL_WINE_WINUSB_GET_DESCRIPTOR & 3) == METHOD_OUT_DIRECT);

#define CONTROL_SEED() do { \
    memset(&control, GUARD_BYTE, sizeof(control)); \
    control.request.request.size = sizeof(control.request); \
    control.request.request.version = WINE_WINUSB_ABI_VERSION; \
    control.request.request.session = ((struct winusb_file *)file.FsContext)->session; \
    control.request.request.interface_index = 0; \
    control.request.request.reserved = 0; \
    control.request.reserved = 0; \
    control.request.setup[0] = 0x80; control.request.setup[1] = 6; \
    control.request.setup[2] = 1; control.request.setup[3] = 0; \
    control.request.setup[4] = 0; control.request.setup[5] = 0; \
    control.request.setup[6] = 0; control.request.setup[7] = 0; \
    control.request.transfer_length = 0; \
    control_expected_file = &file; control_expected_function = URB_FUNCTION_CONTROL_TRANSFER; \
    control_expected_flags = USBD_TRANSFER_DIRECTION_IN | USBD_SHORT_TRANSFER_OK; \
    memcpy(control_expected_setup, control.request.setup, 8); \
} while (0)
#define CONTROL_REJECT_STATUS(expected, code, in, out, bytes, mdl) do { \
    unsigned int before = control_calls; \
    effect = dispatch_control(&d, last_fdo, (code), &control, (in), (out), (bytes), (mdl), &file); \
    IO24_CHECK(effect.status == (expected) && effect.information == 0); \
    IO24_CHECK(control_calls == before && effect.lower_after == effect.lower_before); \
} while (0)
#define CONTROL_REJECT(code, in, out, bytes, mdl) \
    CONTROL_REJECT_STATUS(STATUS_INVALID_PARAMETER, code, in, out, bytes, mdl)
#define CONTROL_ACCEPT(code, expected_status) do { \
    unsigned int before = control_calls, completes_before = completes, \
            lower_completion_before = control_lower_completions, \
            upper_completion_before = control_upper_completions, \
            references_before = control_file_references, \
            dereferences_before = control_file_dereferences; \
    control_retirement_begin(); \
    control_pool_begin(0); \
    effect = dispatch_control(&d, last_fdo, (code), &control, sizeof(control.request), \
            control.request.transfer_length, control.request.transfer_length, TRUE, &file); \
    control_pool_end(); \
    control_retirement_end(); \
    IO24_CHECK(effect.status == (expected_status)); \
    IO24_CHECK(control_calls == before + 1 && effect.lower_after == effect.lower_before + 1); \
    IO24_CHECK(effect.complete_after == completes_before + 1); \
    IO24_CHECK(control_lower_completions == lower_completion_before + 1 && \
            control_upper_completions == upper_completion_before + 1); \
    IO24_CHECK(control_file_references == references_before + 1 && \
            control_file_dereferences == dereferences_before + 1); \
    control_pool_check_complete(2, 2); \
} while (0)
#define CONTROL_ALLOC_REJECT(code, fail_ordinal, expected_status) do { \
    unsigned int calls_before = control_calls, lower_before = lower_calls, \
            completes_before = completes; \
    control_pool_begin((fail_ordinal)); \
    effect = dispatch_control(&d, last_fdo, (code), &control, sizeof(control.request), \
            control.request.transfer_length, control.request.transfer_length, TRUE, &file); \
    control_pool_end(); \
    IO24_CHECK(effect.status == (expected_status) && effect.information == 0); \
    IO24_CHECK(control_calls == calls_before && lower_calls == lower_before); \
    IO24_CHECK(effect.complete_after == completes_before + 1); \
    control_pool_check_complete((fail_ordinal), (fail_ordinal) - 1); \
} while (0)
#define CONTROL_PENDING(code, expected_status) do { \
    unsigned int duplicate_before = control_duplicate_completion_attempts; \
    CONTROL_ACCEPT((code), (expected_status)); \
    IO24_CHECK(effect.dispatch_status == STATUS_PENDING && \
            control_duplicate_completion_attempts == duplicate_before + 1); \
} while (0)

    /* Exact 40-byte request, all header/session/interface/reserved guards,
     * setup wLength agreement, and direct-MDL shape. */
    CONTROL_SEED(); CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 39, 0, 0, FALSE);
    CONTROL_SEED(); CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 41, 0, 0, FALSE);
    CONTROL_SEED(); control.request.request.size--; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.request.version++; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.request.session = 0; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.request.interface_index = 1; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.request.reserved = 1; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.request.reserved = 2; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.reserved = 1; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.reserved = 2; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.transfer_length = 1; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 1, 1, FALSE);
    CONTROL_SEED(); control.request.transfer_length = 1; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 1, 0, TRUE);
    CONTROL_SEED(); control.request.transfer_length = 4097; control.request.setup[6] = 1; control.request.setup[7] = 0x10; CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 4097, 4097, TRUE);
    CONTROL_SEED(); control.request.transfer_length = 1; control.request.setup[6] = 1; control.request.setup[7] = 1;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 1, 1, TRUE);
    CONTROL_SEED(); control.request.transfer_length = 1; control.request.setup[6] = 1; control.request.setup[7] = 0xa5;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 1, 1, TRUE);
    /* The IOCTL method is selected solely by setup bit 7.  A nonzero direct
     * MDL with the opposite method must be rejected before a lower submit. */
    CONTROL_SEED(); control.request.transfer_length = 1; control.request.setup[6] = 1;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_OUT, 40, 1, 1, TRUE);
    CONTROL_SEED(); control.request.setup[0] = 0x00; control.request.transfer_length = 1; control.request.setup[6] = 1;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 1, 1, TRUE);

    /* Every supported size has exact little-endian wLength and MDL capacity.
     * The successful calls are deliberately feature RED at the frozen head. */
    for (unsigned int n = 0; n < ARRAY_SIZE(lengths); ++n)
    {
        CONTROL_SEED();
        control.request.transfer_length = lengths[n];
        control.request.setup[6] = lengths[n] & 0xff;
        control.request.setup[7] = lengths[n] >> 8;
        memcpy(control_expected_setup, control.request.setup, 8);
        control_expected_length = lengths[n];
        control_expected_mdl = NULL; /* dispatch_control supplies the caller MDL */
        /* The fake can only compare the production-owned MDL after transfer.c
         * is present; this invocation still proves the rejected frozen seam. */
        CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_SUCCESS);
    }

    /* Transfer admission is a live session/device operation.  Its helper
     * must reject stale state before allocation or lower dispatch. */
    CONTROL_SEED();
    ((struct winusb_file *)file.FsContext)->state = WINUSB_FILE_UNINITIALIZED;
    CONTROL_REJECT_STATUS(STATUS_INVALID_DEVICE_STATE, IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    ((struct winusb_file *)file.FsContext)->state = WINUSB_FILE_INITIALIZED;
    CONTROL_SEED();
    ((struct winusb_device *)last_fdo->DeviceExtension)->state = WINUSB_DEVICE_STOPPED;
    CONTROL_REJECT_STATUS(STATUS_INVALID_DEVICE_STATE, IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    ((struct winusb_device *)last_fdo->DeviceExtension)->state = WINUSB_DEVICE_STARTED;

    /* Admission must take the session mutex.  Once main.c has acquired the
     * file I/O reference, the worker remains blocked until state changes. */
    {
        struct winusb_file *mutex_file = file.FsContext;
        thrd_t worker; int worker_result; unsigned int lower_before = lower_calls, spins = 0;
        int worker_created;
        BOOL blocked_seen;
        CONTROL_SEED(); control_expected_length = 0;
        memset(&control_mutex_schedule, 0, sizeof(control_mutex_schedule));
        control_mutex_schedule.driver = &d; control_mutex_schedule.fdo = last_fdo;
        control_mutex_schedule.file = &file; control_mutex_schedule.control = &control;
        atomic_store_explicit(&io24_mutex_block_seen, FALSE, memory_order_release);
        atomic_store_explicit(&io24_mutex_block_target, &mutex_file->session_mutex, memory_order_release);
        ExAcquireFastMutex(&mutex_file->session_mutex);
        worker_created = thrd_create(&worker, control_mutex_worker, &control_mutex_schedule) == thrd_success;
        if (!worker_created)
        {
            ExReleaseFastMutex(&mutex_file->session_mutex);
            atomic_store_explicit(&io24_mutex_block_target, NULL, memory_order_release);
            control_thread_terminal("creation");
        }
        while (!atomic_load_explicit(&io24_mutex_block_seen, memory_order_acquire) && spins++ < 1000000)
            thrd_yield();
        blocked_seen = atomic_load_explicit(&io24_mutex_block_seen, memory_order_acquire);
        IO24_CHECK(blocked_seen);
        if (blocked_seen) mutex_file->state = WINUSB_FILE_UNINITIALIZED;
        ExReleaseFastMutex(&mutex_file->session_mutex);
        atomic_store_explicit(&io24_mutex_block_target, NULL, memory_order_release);
        if (thrd_join(worker, &worker_result) != thrd_success)
            control_thread_terminal("join");
        if (worker_result != 0) control_thread_terminal("result");
        IO24_CHECK(control_mutex_schedule.effect.status == STATUS_INVALID_DEVICE_STATE &&
                lower_calls == lower_before && !control_pending_irp);
        if (control_pending_irp) complete_pending_task9_irp();
        mutex_file->state = WINUSB_FILE_INITIALIZED;
        control_expected_irp = NULL;
    }

    /* Current alternate zero has no pipes, so endpoint admission must fail
     * before the real selection path installs the map. */
    CONTROL_SEED(); control.request.setup[0] = 0x82; control.request.setup[4] = 0x81;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    if (!select_control_alternate(&d, last_fdo, &file, 1))
    {
        teardown(&d, &g, &file);
        return;
    }
    IO24_CHECK(((struct winusb_file *)file.FsContext)->interfaces[0].alternate_setting == 1 &&
            ((struct winusb_file *)file.FsContext)->interfaces[0].endpoint_count == 2);

    /* Endpoint lookup must happen after acquisition of this exact session
     * mutex.  Changing the real current pipe map while the worker is blocked
     * catches a stale pre-lock endpoint lookup. */
    {
        struct winusb_file *mutex_file = file.FsContext;
        struct winusb_interface_state *interface = &mutex_file->interfaces[0];
        UCHAR original_endpoint = interface->pipes[0].endpoint;
        thrd_t worker;
        int worker_result;
        unsigned int lower_before = lower_calls, spins = 0;
        BOOL blocked_seen;

        CONTROL_SEED();
        control.request.setup[0] = 0x82;
        control.request.setup[4] = original_endpoint;
        memcpy(control_expected_setup, control.request.setup, sizeof(control_expected_setup));
        control_expected_length = control_actual_length = 0;
        control_returns_pending = FALSE;
        memset(&control_mutex_schedule, 0, sizeof(control_mutex_schedule));
        control_mutex_schedule.driver = &d;
        control_mutex_schedule.fdo = last_fdo;
        control_mutex_schedule.file = &file;
        control_mutex_schedule.control = &control;
        atomic_store_explicit(&io24_mutex_block_seen, FALSE, memory_order_release);
        atomic_store_explicit(&io24_mutex_block_target, &mutex_file->session_mutex,
                memory_order_release);
        ExAcquireFastMutex(&mutex_file->session_mutex);
        if (thrd_create(&worker, control_mutex_worker, &control_mutex_schedule) != thrd_success)
        {
            ExReleaseFastMutex(&mutex_file->session_mutex);
            atomic_store_explicit(&io24_mutex_block_target, NULL, memory_order_release);
            control_thread_terminal("creation");
        }
        while (!atomic_load_explicit(&io24_mutex_block_seen, memory_order_acquire) &&
                spins++ < 1000000)
            thrd_yield();
        blocked_seen = atomic_load_explicit(&io24_mutex_block_seen, memory_order_acquire);
        IO24_CHECK(blocked_seen);
        if (blocked_seen) interface->pipes[0].endpoint = 0x84;
        ExReleaseFastMutex(&mutex_file->session_mutex);
        atomic_store_explicit(&io24_mutex_block_target, NULL, memory_order_release);
        if (thrd_join(worker, &worker_result) != thrd_success)
            control_thread_terminal("join");
        if (worker_result != 0) control_thread_terminal("result");
        IO24_CHECK(control_mutex_schedule.effect.status == STATUS_INVALID_PARAMETER &&
                control_mutex_schedule.effect.information == 0 &&
                lower_calls == lower_before && !control_pending_count);
        interface->pipes[0].endpoint = original_endpoint;
        control_expected_irp = NULL;
    }

    /* A real nonzero CONTROL_IN uses the current IN pipe (0x81), not merely a
     * zero-length scope check.  The mapped direct MDL is the only data path;
     * bytes past the reported completion stay guarded. */
    CONTROL_SEED();
    control.request.setup[0] = 0x82; control.request.setup[4] = 0x81;
    control.request.transfer_length = 37; control.request.setup[6] = 37;
    control.request.setup[7] = 0;
    memset(control.data, GUARD_BYTE, sizeof(control.data));
    control_expected_length = 37;
    memcpy(control_expected_setup, control.request.setup, 8);
    control_actual_length = 37;
    CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_SUCCESS);
    IO24_CHECK(effect.information == 37 && control.data[37] == GUARD_BYTE);
    control_actual_length = 0;

    /* Scope validation: device is root-only; interface canonicalizes the low
     * byte; endpoint is an exact current pipe with matching direction; Other
     * is forwarded after its reserved-bit check. */
    for (unsigned int t = 0; t < ARRAY_SIZE(types); ++t)
        for (unsigned int r = 0; r < ARRAY_SIZE(recipients); ++r)
        {
            BOOL in_direction;

            CONTROL_SEED();
            control.request.setup[0] = 0x80 | types[t] | recipients[r];
            in_direction = !!(control.request.setup[0] & 0x80);
            control.request.setup[4] = recipients[r] == 1 ? 0x9d :
                    recipients[r] == 2 ? (in_direction ? 0x81 : 0x01) : 0;
            control.request.setup[5] = recipients[r] == 1 ? 0xa5 : 0;
            memcpy(control_expected_setup, control.request.setup, 8);
            if (recipients[r] == 1) control_expected_setup[4] = 5;
            control_expected_length = 0;
            CONTROL_ACCEPT(codes[in_direction ? 0 : 1], STATUS_SUCCESS);
        }
    /* A nonzero CONTROL_OUT must retain its direct MDL payload through the
     * actual function boundary for every representative recipient scope. */
#define CONTROL_OUT_ACCEPT(request_type, request_index) do { \
    CONTROL_SEED(); \
    control.request.setup[0] = (request_type); control.request.setup[1] = 0x5a; \
    control.request.setup[4] = (request_index) & 0xff; \
    control.request.setup[5] = (request_index) >> 8; \
    control.request.transfer_length = 3; control.request.setup[6] = 3; \
    control.request.setup[7] = 0; \
    control_expected_flags = 0; control_expected_length = 3; \
    memcpy(control_expected_setup, control.request.setup, 8); \
    if (((request_type) & 3) == 1) control_expected_setup[4] = 5; \
    for (unsigned int payload_i = 0; payload_i < 3; ++payload_i) \
        control.data[payload_i] = (UCHAR)(0x30 + payload_i); \
    CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_OUT, STATUS_SUCCESS); \
} while (0)
    CONTROL_OUT_ACCEPT(0x00, 0);       /* device */
    CONTROL_OUT_ACCEPT(0x21, 0xab9d);  /* interface canonicalizes low byte */
    CONTROL_OUT_ACCEPT(0x02, 0x01);    /* current exact OUT endpoint */
    CONTROL_OUT_ACCEPT(0x43, 0);       /* vendor other */
#undef CONTROL_OUT_ACCEPT
    /* High device Index bytes are not reserved by the source contract; the
     * represented root/default handle is the device-recipient scope check. */
    CONTROL_SEED(); control.request.setup[0] = 0x80; control.request.setup[5] = 1;
    memcpy(control_expected_setup, control.request.setup, 8); control_expected_length = 0;
    CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_SUCCESS);
    CONTROL_SEED(); control.request.setup[0] = 0x82; control.request.setup[4] = 0x83;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.setup[0] = 0x82; control.request.setup[4] = 0x01;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.setup[0] = 0x02; control.request.setup[4] = 0x81;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_OUT, 40, 0, 0, FALSE);
    expected_alternate_setting = 0; expected_alternate_pipes = 0;
    if (select_control_alternate(&d, last_fdo, &file, 0))
    {
        CONTROL_SEED(); control.request.setup[0] = 0x82; control.request.setup[4] = 0x81;
        CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
        expected_alternate_setting = 1; expected_alternate_pipes = 2;
        expected_alternate_endpoints[0] = 0x81; expected_alternate_endpoints[1] = 0x01;
        expected_alternate_packets[0] = expected_alternate_packets[1] = 512;
        IO24_CHECK(select_control_alternate(&d, last_fdo, &file, 1));
    }
    CONTROL_SEED(); control.request.setup[0] = 0xe0;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.setup[0] = 0x00 | 2; control.request.setup[4] = 0x81;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_OUT, 40, 0, 0, FALSE);

    /* Allocation failure is terminal, completes once, and never submits a
     * partially-built URB.  The exact allocator is production-owned. */
    CONTROL_SEED(); control_expected_length = 0;
    CONTROL_ALLOC_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 1, STATUS_INSUFFICIENT_RESOURCES);
    CONTROL_SEED(); control_expected_length = 0;
    CONTROL_ALLOC_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 2, STATUS_INSUFFICIENT_RESOURCES);

    /* Lower NT/URB mapping is table-driven so every terminal lower status is
     * observed through the original IRP, and failure never gains bytes merely
     * because the NT transport status happened to be successful. */
    static const struct { USBD_STATUS urb; NTSTATUS upper; } status_cases[] = {
        { USBD_STATUS_CANCELED, STATUS_CANCELLED },
        { USBD_STATUS_CANCELING, STATUS_CANCELLED },
        { USBD_STATUS_TIMEOUT, STATUS_IO_TIMEOUT },
        { USBD_STATUS_DEV_NOT_RESPONDING, STATUS_IO_TIMEOUT },
        { USBD_STATUS_DEVICE_GONE, STATUS_DEVICE_NOT_CONNECTED },
        { USBD_STATUS_INVALID_PARAMETER, STATUS_INVALID_PARAMETER },
        { USBD_STATUS_INVALID_PIPE_HANDLE, STATUS_NOT_FOUND },
        { USBD_STATUS_ERROR_BUSY, STATUS_DEVICE_BUSY },
        { USBD_STATUS_NO_MEMORY, STATUS_NO_MEMORY },
        { USBD_STATUS_STALL_PID, STATUS_UNSUCCESSFUL },
        { USBD_STATUS_REQUEST_FAILED, STATUS_UNSUCCESSFUL },
    };

    /* Lower NT/URB mapping, pending completion ownership, and result bounds. */
    CONTROL_SEED(); control_expected_length = 37; control.request.transfer_length = 37;
    control.request.setup[6] = 37; control_expected_setup[6] = 37;
    control_nt_status = STATUS_UNSUCCESSFUL; CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_UNSUCCESSFUL);
    control_nt_status = STATUS_SUCCESS; control_urb_status = USBD_STATUS_STALL_PID;
    CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_UNSUCCESSFUL);
    IO24_CHECK(effect.information == 0);
    for (unsigned int status_i = 0; status_i < ARRAY_SIZE(status_cases); ++status_i)
    {
        CONTROL_SEED(); control_expected_length = 37; control.request.transfer_length = 37;
        control.request.setup[6] = 37; control_expected_setup[6] = 37;
        control_nt_status = STATUS_SUCCESS;
        control_urb_status = status_cases[status_i].urb;
        CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, status_cases[status_i].upper);
        IO24_CHECK(effect.information == 0);
    }
    /* An NT failure overrides even a successful URB and reports no bytes. */
    CONTROL_SEED(); control_expected_length = 37; control.request.transfer_length = 37;
    control.request.setup[6] = 37; control_expected_setup[6] = 37;
    control_nt_status = STATUS_UNSUCCESSFUL; control_urb_status = USBD_STATUS_SUCCESS;
    CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_UNSUCCESSFUL);
    IO24_CHECK(effect.information == 0);
    control_nt_status = STATUS_SUCCESS; control_urb_status = USBD_STATUS_SUCCESS;
    control_urb_status = USBD_STATUS_SUCCESS; control_returns_pending = TRUE;
    CONTROL_PENDING(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_SUCCESS);
    control_nt_status = STATUS_UNSUCCESSFUL;
    CONTROL_PENDING(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_UNSUCCESSFUL);
    control_nt_status = STATUS_SUCCESS; control_returns_pending = FALSE; control_actual_length = 4096;
    CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_SUCCESS);
    IO24_CHECK(effect.information == 37); /* min(request, MDL, lower actual) */
    control_actual_length = 0;

    /* Exercise the recipient map through an actual two-interface session,
     * not a hand-written test context.  Index 1 owns MI06/0x83; index 0 owns
     * MI05/0x81 and must not leak that map into the associated handle. */
    teardown(&d, &g, &file);
    setup(&d, &e, &p, &g, &file);
    if (!create_file(&d, &g, &file)) { teardown(&d, &g, &file); return; }
    reset_initialize_lower();
    memcpy(lower_configuration, two_interface_configuration, sizeof(two_interface_configuration));
    lower_configuration_size = lower_body_actual = sizeof(two_interface_configuration);
    expected_select_interfaces = 2;
    expected_select_interface_numbers[0] = 5;
    expected_select_interface_numbers[1] = 6;
    poison_two_interface_state_allocation = TRUE;
    {
        struct guarded_initialize initialize;
        struct guarded_snapshot output;
        reset_initialize_buffers(&initialize, &output);
        session_allocation_calls = 0;
        effect = call_initialize(&d, &file, &initialize, &output, 229, 229,
                &initialize.request, output.bytes);
        IO24_CHECK(effect.status == STATUS_SUCCESS && effect.information == 229);
    }
    poison_two_interface_state_allocation = FALSE;
    IO24_CHECK(poisoned_two_interface_state_allocations == 1);
    IO24_CHECK(((struct winusb_file *)file.FsContext)->interface_count == 2);
    /* Both poisoned interface records must nevertheless admit their initial
     * no-transfer alternate selections: any added ownership field must be
     * explicitly initialized rather than inherited from allocator zeroing. */
    expected_alternate_interface = 5; expected_alternate_setting = 0; expected_alternate_pipes = 0;
    IO24_CHECK(NT_SUCCESS(select_control_alternate_status(&d, last_fdo, &file, 0, 0)));
    expected_alternate_interface = 6; expected_alternate_setting = 1;
    expected_alternate_pipes = 1; expected_alternate_endpoints[0] = 0x83;
    expected_alternate_packets[0] = 64;
    if (!NT_SUCCESS(select_control_alternate_status(&d, last_fdo, &file, 1, 1)))
    {
        teardown(&d, &g, &file);
        return;
    }
    CONTROL_SEED(); control.request.request.interface_index = 1;
    control.request.setup[0] = 0x81; control.request.setup[4] = 0x9d;
    control.request.setup[5] = 0xab;
    memcpy(control_expected_setup, control.request.setup, 8);
    control_expected_setup[4] = 6;
    CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_SUCCESS);
    CONTROL_SEED(); control.request.request.interface_index = 1;
    control.request.setup[0] = 0x82; control.request.setup[4] = 0x83;
    CONTROL_ACCEPT(IOCTL_WINE_WINUSB_CONTROL_IN, STATUS_SUCCESS);
    CONTROL_SEED(); control.request.request.interface_index = 1;
    control.request.setup[0] = 0x82; control.request.setup[4] = 0x81;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);
    CONTROL_SEED(); control.request.request.interface_index = 1;
    control.request.setup[0] = 0x80; control.request.setup[4] = 0x9d;
    control.request.setup[5] = 0xab;
    CONTROL_REJECT(IOCTL_WINE_WINUSB_CONTROL_IN, 40, 0, 0, FALSE);

    /* Two caller-owned generic controls on MI06 remain pending together.
     * Root MI05 remains independent, while completing only one MI06 request
     * must leave MI06 blocked.  This catches Boolean accounting masquerading
     * as a real per-interface transfer count. */
    {
        struct guarded_control pending_controls[2];
        IRP pending_irps[2];
        IO_STACK_LOCATION pending_stacks[2][2];
        MDL pending_mdls[2];
        PVOID pending_contexts[2];
        URB *pending_urbs[2];
        SIZE_T pending_context_sizes[2];
        unsigned int lower_before;

        CONTROL_SEED(); control.request.request.interface_index = 1;
        control.request.setup[0] = 0x81; control.request.setup[4] = 0x9d;
        control.request.setup[5] = 0xab;
        memcpy(control_expected_setup, control.request.setup, 8);
        control_expected_setup[4] = 6;
        pending_controls[0] = control;
        pending_controls[1] = control;
        control_returns_pending = TRUE;
        control_nt_status = STATUS_SUCCESS;
        control_urb_status = USBD_STATUS_SUCCESS;
        control_pool_begin(0);
        effect = begin_pending_control(&d, last_fdo, &pending_controls[0], &file,
                &pending_irps[0], pending_stacks[0], &pending_mdls[0]);
        pending_contexts[0] = pending_stacks[0][0].Context;
        pending_urbs[0] = pending_stacks[0][0].Parameters.Others.Argument1;
        IO24_CHECK(effect.dispatch_status == STATUS_PENDING &&
                control_pending_irp == &pending_irps[0] && control_pending_count == 1);
        control_urb_status = USBD_STATUS_TIMEOUT;
        effect = begin_pending_control(&d, last_fdo, &pending_controls[1], &file,
                &pending_irps[1], pending_stacks[1], &pending_mdls[1]);
        pending_contexts[1] = pending_stacks[1][0].Context;
        pending_urbs[1] = pending_stacks[1][0].Parameters.Others.Argument1;
        IO24_CHECK(effect.dispatch_status == STATUS_PENDING &&
                control_pending_irp == &pending_irps[0] &&
                control_pending_next_irp == &pending_irps[1] && control_pending_count == 2);
        IO24_CHECK(pending_contexts[0] && pending_contexts[1] &&
                pending_contexts[0] != pending_contexts[1]);
        IO24_CHECK(pending_urbs[0] && pending_urbs[1] && pending_urbs[0] != pending_urbs[1]);
        IO24_CHECK(control_pool_attempts == 4 && control_pool_count == 4);
        pending_context_sizes[0] = control_pool_pointer_size(pending_contexts[0]);
        pending_context_sizes[1] = control_pool_pointer_size(pending_contexts[1]);
        IO24_CHECK(pending_context_sizes[0] &&
                pending_context_sizes[0] == pending_context_sizes[1] &&
                pending_context_sizes[0] != sizeof(URB));
        control_pool_check_pointer(pending_contexts[0], pending_context_sizes[0], 0);
        control_pool_check_pointer(pending_urbs[0], sizeof(URB), 0);
        control_pool_check_pointer(pending_contexts[1], pending_context_sizes[1], 0);
        control_pool_check_pointer(pending_urbs[1], sizeof(URB), 0);
        IO24_CHECK(pending_stacks[0][0].Context == pending_contexts[0] &&
                pending_stacks[0][0].Parameters.Others.Argument1 == pending_urbs[0]);
        IO24_CHECK(pending_stacks[1][0].Context == pending_contexts[1] &&
                pending_stacks[1][0].Parameters.Others.Argument1 == pending_urbs[1]);
        control_pool_pause_allocations();
        control_urb_status = USBD_STATUS_SUCCESS;
        expected_alternate_interface = 5; expected_alternate_setting = 0;
        expected_alternate_pipes = 0;
        expected_session_urb_outstanding = 3;
        IO24_CHECK(NT_SUCCESS(select_control_alternate_status(&d, last_fdo, &file, 0, 0)));
        expected_session_urb_outstanding = 2;
        expected_alternate_interface = 6; expected_alternate_setting = 1;
        expected_alternate_pipes = 1; expected_alternate_endpoints[0] = 0x83;
        expected_alternate_packets[0] = 64;
        lower_before = lower_calls;
        IO24_CHECK(select_control_alternate_status(&d, last_fdo, &file, 1, 1) ==
                STATUS_INVALID_DEVICE_STATE);
        IO24_CHECK(lower_calls == lower_before);
        io24_last_completed_irp = NULL; io24_completed_irp_count = 0;
        control_completion_allocation_begin();
        IO24_CHECK(complete_pending_task9_irp());
        control_completion_allocation_end();
        IO24_CHECK(io24_completed_irp_count == 1 &&
                io24_last_completed_irp == &pending_irps[0] && control_pending_count == 1);
        IO24_CHECK(pending_irps[0].IoStatus.Status == STATUS_SUCCESS &&
                pending_irps[0].IoStatus.Information == 0);
        control_pool_check_pointer(pending_contexts[0], pending_context_sizes[0], 1);
        control_pool_check_pointer(pending_urbs[0], sizeof(URB), 1);
        control_pool_check_pointer(pending_contexts[1], pending_context_sizes[1], 0);
        control_pool_check_pointer(pending_urbs[1], sizeof(URB), 0);
        expected_session_urb_outstanding = 2;
        lower_before = lower_calls;
        IO24_CHECK(select_control_alternate_status(&d, last_fdo, &file, 1, 1) ==
                STATUS_INVALID_DEVICE_STATE);
        IO24_CHECK(lower_calls == lower_before);
        io24_last_completed_irp = NULL; io24_completed_irp_count = 0;
        control_completion_allocation_begin();
        IO24_CHECK(complete_pending_task9_irp());
        control_completion_allocation_end();
        IO24_CHECK(io24_completed_irp_count == 1 &&
                io24_last_completed_irp == &pending_irps[1] && !control_pending_count);
        IO24_CHECK(pending_irps[1].IoStatus.Status == STATUS_IO_TIMEOUT &&
                pending_irps[1].IoStatus.Information == 0);
        control_pool_check_pointer(pending_contexts[0], pending_context_sizes[0], 1);
        control_pool_check_pointer(pending_urbs[0], sizeof(URB), 1);
        control_pool_check_pointer(pending_contexts[1], pending_context_sizes[1], 1);
        control_pool_check_pointer(pending_urbs[1], sizeof(URB), 1);
        control_pool_check_complete(4, 4);
        control_pool_end();
        control_expected_irp = NULL; control_returns_pending = FALSE;
        expected_session_urb_outstanding = 1;
        IO24_CHECK(NT_SUCCESS(select_control_alternate_status(&d, last_fdo, &file, 1, 1)));
    }

    /* Descriptor fallback has its own complete original-IRP/METHOD_OUT_DIRECT
     * matrix.  It is intentionally not inferred from control coverage. */
#define DESCRIPTOR_SEED() do { \
    memset(&descriptor, GUARD_BYTE, sizeof(descriptor)); \
    descriptor.request.request.size = sizeof(descriptor.request); \
    descriptor.request.request.version = WINE_WINUSB_ABI_VERSION; \
    descriptor.request.request.session = ((struct winusb_file *)file.FsContext)->session; \
    descriptor.request.request.interface_index = 0; descriptor.request.request.reserved = 0; \
    descriptor.request.type = USB_DEVICE_DESCRIPTOR_TYPE; descriptor.request.index = 0; \
    descriptor.request.language = 0; descriptor.request.length = 18; \
    control_expected_function = URB_FUNCTION_GET_DESCRIPTOR_FROM_DEVICE; \
    control_expected_file = &file; control_expected_length = descriptor.request.length; \
    memset(control_expected_setup, 0, sizeof(control_expected_setup)); \
    control_expected_setup[0] = descriptor.request.type; control_expected_setup[1] = descriptor.request.index; \
    control_expected_setup[2] = descriptor.request.language & 0xff; \
    control_expected_setup[3] = descriptor.request.language >> 8; \
} while (0)
#define DESCRIPTOR_REJECT(in, out, bytes, mdl) do { \
    struct winusb_file *descriptor_file = file.FsContext; \
    struct winusb_interface_state descriptor_interface_before = descriptor_file->interfaces[0]; \
    unsigned char descriptor_data_before[sizeof(descriptor.data)]; \
    LONG descriptor_references_before = descriptor_file->references; \
    LONG descriptor_outstanding_before = descriptor_file->outstanding; \
    LONG descriptor_event_before = descriptor_file->zero_outstanding.Header.SignalState; \
    unsigned int descriptor_before = control_calls, completes_before = completes, \
            lower_completion_before = control_lower_completions, \
            upper_completion_before = control_upper_completions, \
            object_references_before = control_file_references, \
            object_dereferences_before = control_file_dereferences; \
    BOOL descriptor_list_empty_before = IsListEmpty(&descriptor_file->transfers); \
    memcpy(descriptor_data_before, descriptor.data, sizeof(descriptor_data_before)); \
    effect = dispatch_descriptor(&d, last_fdo, &descriptor, (in), (out), (bytes), (mdl), &file); \
    IO24_CHECK(effect.status == STATUS_INVALID_PARAMETER && effect.information == 0); \
    IO24_CHECK(control_calls == descriptor_before && effect.lower_after == effect.lower_before); \
    IO24_CHECK(effect.complete_after == completes_before + 1); \
    IO24_CHECK(control_lower_completions == lower_completion_before && \
            control_upper_completions == upper_completion_before); \
    IO24_CHECK(!memcmp(descriptor.data, descriptor_data_before, sizeof(descriptor_data_before))); \
    IO24_CHECK(descriptor_file->references == descriptor_references_before && \
            descriptor_file->outstanding == descriptor_outstanding_before && \
            descriptor_file->zero_outstanding.Header.SignalState == descriptor_event_before); \
    IO24_CHECK(descriptor_list_empty_before && IsListEmpty(&descriptor_file->transfers)); \
    IO24_CHECK(!memcmp(&descriptor_file->interfaces[0], &descriptor_interface_before, \
            sizeof(descriptor_interface_before))); \
    IO24_CHECK(control_file_references - object_references_before == \
            control_file_dereferences - object_dereferences_before); \
    IO24_CHECK(control_file_references == control_file_dereferences); \
    IO24_CHECK(!control_pending_irp && !control_pending_stack && !control_pending_device && \
            !control_pending_context && !control_pending_urb && \
            !control_pending_next_irp && !control_pending_next_stack && \
            !control_pending_next_device && !control_pending_next_context && \
            !control_pending_next_urb && !control_pending_count && \
            !control_lower_slot0_installed); \
} while (0)
#define DESCRIPTOR_ACCEPT(expected, expected_information) do { \
    unsigned int descriptor_before = control_calls, completes_before = completes, \
            references_before = control_file_references, \
            dereferences_before = control_file_dereferences; \
    control_retirement_begin(); \
    control_pool_begin(0); \
    effect = dispatch_descriptor(&d, last_fdo, &descriptor, sizeof(descriptor.request), \
            descriptor.request.length, descriptor.request.length, TRUE, &file); \
    control_pool_end(); \
    control_retirement_end(); \
    IO24_CHECK(effect.status == (expected)); \
    IO24_CHECK(control_calls == descriptor_before + 1 && effect.lower_after == effect.lower_before + 1); \
    IO24_CHECK(effect.complete_after == completes_before + 1); \
    IO24_CHECK(effect.information == (expected_information)); \
    IO24_CHECK(control_file_references == references_before + 1 && \
            control_file_dereferences == dereferences_before + 1); \
    control_pool_check_complete(2, 2); \
} while (0)
#define DESCRIPTOR_ALLOC_REJECT(ordinal) do { \
    struct winusb_file *descriptor_file = file.FsContext; \
    struct winusb_interface_state descriptor_interface_before = descriptor_file->interfaces[0]; \
    LONG descriptor_references_before = descriptor_file->references; \
    LONG descriptor_outstanding_before = descriptor_file->outstanding; \
    LONG descriptor_event_before = descriptor_file->zero_outstanding.Header.SignalState; \
    unsigned int descriptor_before = control_calls, lower_before = lower_calls, \
            completes_before = completes, lower_completion_before = control_lower_completions, \
            upper_completion_before = control_upper_completions, \
            object_references_before = control_file_references, \
            object_dereferences_before = control_file_dereferences; \
    BOOL descriptor_list_empty_before = IsListEmpty(&descriptor_file->transfers); \
    control_pool_begin((ordinal)); \
    effect = dispatch_descriptor(&d, last_fdo, &descriptor, sizeof(descriptor.request), \
            descriptor.request.length, descriptor.request.length, TRUE, &file); \
    control_pool_end(); \
    IO24_CHECK(effect.status == STATUS_INSUFFICIENT_RESOURCES && effect.information == 0); \
    IO24_CHECK(control_calls == descriptor_before && lower_calls == lower_before); \
    IO24_CHECK(effect.complete_after == completes_before + 1); \
    IO24_CHECK(control_lower_completions == lower_completion_before && \
            control_upper_completions == upper_completion_before); \
    IO24_CHECK(descriptor_file->references == descriptor_references_before && \
            descriptor_file->outstanding == descriptor_outstanding_before && \
            descriptor_file->zero_outstanding.Header.SignalState == descriptor_event_before); \
    IO24_CHECK(descriptor_list_empty_before && IsListEmpty(&descriptor_file->transfers)); \
    IO24_CHECK(!memcmp(&descriptor_file->interfaces[0], &descriptor_interface_before, \
            sizeof(descriptor_interface_before))); \
    IO24_CHECK(control_file_references - object_references_before == \
            control_file_dereferences - object_dereferences_before); \
    IO24_CHECK(control_file_references == control_file_dereferences); \
    IO24_CHECK(!control_pending_irp && !control_pending_stack && !control_pending_device && \
            !control_pending_context && !control_pending_urb && \
            !control_pending_next_irp && !control_pending_next_stack && \
            !control_pending_next_device && !control_pending_next_context && \
            !control_pending_next_urb && !control_pending_count && \
            !control_lower_slot0_installed); \
    control_pool_check_complete((ordinal), (ordinal) - 1); \
} while (0)

    IO24_CHECK(sizeof(descriptor.request) == 40);
    IO24_CHECK((IOCTL_WINE_WINUSB_GET_DESCRIPTOR & 3) == METHOD_OUT_DIRECT);
    DESCRIPTOR_SEED(); DESCRIPTOR_REJECT(39, 18, 18, TRUE);
    DESCRIPTOR_SEED(); DESCRIPTOR_REJECT(41, 18, 18, TRUE);
    DESCRIPTOR_SEED(); descriptor.request.request.size--; DESCRIPTOR_REJECT(40, 18, 18, TRUE);
    DESCRIPTOR_SEED(); descriptor.request.request.version++; DESCRIPTOR_REJECT(40, 18, 18, TRUE);
    DESCRIPTOR_SEED(); descriptor.request.request.session = 0; DESCRIPTOR_REJECT(40, 18, 18, TRUE);
    DESCRIPTOR_SEED(); descriptor.request.request.interface_index = 1; DESCRIPTOR_REJECT(40, 18, 18, TRUE);
    DESCRIPTOR_SEED(); descriptor.request.request.reserved = 1; DESCRIPTOR_REJECT(40, 18, 18, TRUE);
    DESCRIPTOR_SEED(); DESCRIPTOR_REJECT(40, 18, 18, FALSE); /* missing MDL */
    DESCRIPTOR_SEED(); descriptor_unmapped_mdl = TRUE; DESCRIPTOR_REJECT(40, 18, 18, TRUE);
    descriptor_unmapped_mdl = FALSE;
    DESCRIPTOR_SEED(); DESCRIPTOR_REJECT(40, 18, 17, TRUE);  /* undersized mapped MDL */
    DESCRIPTOR_SEED(); descriptor.request.length = 0; control_expected_length = 0; DESCRIPTOR_REJECT(40, 0, 0, FALSE);
    DESCRIPTOR_SEED(); descriptor.request.length = 4097; DESCRIPTOR_REJECT(40, 4097, 4097, TRUE);
    DESCRIPTOR_SEED(); descriptor.request.type = 0; DESCRIPTOR_REJECT(40, 18, 18, TRUE);
    /* A root descriptor is an interface-0 transfer.  Its pending lifetime
     * blocks only alternate0; alternate1 is still a real lower session URB. */
    {
        IRP pending_irp;
        IO_STACK_LOCATION pending_stack[2];
        MDL pending_mdl;
        unsigned int lower_before;

        DESCRIPTOR_SEED(); control_returns_pending = TRUE;
        effect = begin_pending_descriptor(&d, last_fdo, &descriptor, &file,
                &pending_irp, pending_stack, &pending_mdl);
        IO24_CHECK(effect.dispatch_status == STATUS_PENDING && control_pending_irp == &pending_irp);
        expected_alternate_interface = 5; expected_alternate_setting = 0; expected_alternate_pipes = 0;
        lower_before = lower_calls;
        IO24_CHECK(select_control_alternate_status(&d, last_fdo, &file, 0, 0) ==
                STATUS_INVALID_DEVICE_STATE && lower_calls == lower_before);
        expected_alternate_interface = 6; expected_alternate_setting = 1;
        expected_alternate_pipes = 1; expected_alternate_endpoints[0] = 0x83;
        expected_alternate_packets[0] = 64; expected_session_urb_outstanding = 2;
        IO24_CHECK(NT_SUCCESS(select_control_alternate_status(&d, last_fdo, &file, 1, 1)));
        expected_session_urb_outstanding = 1;
        io24_last_completed_irp = NULL; io24_completed_irp_count = 0;
        IO24_CHECK(complete_pending_task9_irp());
        IO24_CHECK(io24_completed_irp_count == 1 && io24_last_completed_irp == &pending_irp);
        control_expected_irp = NULL; control_returns_pending = FALSE;
        expected_alternate_interface = 5; expected_alternate_setting = 0;
        expected_alternate_pipes = 0;
        IO24_CHECK(NT_SUCCESS(select_control_alternate_status(&d, last_fdo, &file, 0, 0)));
    }
    DESCRIPTOR_SEED(); descriptor.request.type = USB_CONFIGURATION_DESCRIPTOR_TYPE;
    descriptor.request.index = 2; descriptor.request.language = 0x0409;
    control_expected_setup[0] = descriptor.request.type; control_expected_setup[1] = descriptor.request.index;
    control_expected_setup[2] = 0x09; control_expected_setup[3] = 0x04;
    control_actual_length = 18; DESCRIPTOR_ACCEPT(STATUS_SUCCESS, 18);
    /* Fallback is generic for every valid nonzero descriptor type, not just
     * the two types used by initialization. */
    DESCRIPTOR_SEED(); descriptor.request.type = USB_STRING_DESCRIPTOR_TYPE;
    descriptor.request.index = 3; descriptor.request.language = 0x0409;
    control_expected_setup[0] = descriptor.request.type; control_expected_setup[1] = 3;
    control_expected_setup[2] = 0x09; control_expected_setup[3] = 0x04;
    control_actual_length = 18; DESCRIPTOR_ACCEPT(STATUS_SUCCESS, 18);
    DESCRIPTOR_SEED(); descriptor.request.type = 0x22;
    control_expected_setup[0] = descriptor.request.type;
    control_actual_length = 18; DESCRIPTOR_ACCEPT(STATUS_SUCCESS, 18);
    DESCRIPTOR_SEED(); control_actual_length = 9; DESCRIPTOR_ACCEPT(STATUS_SUCCESS, 9); /* short */
    DESCRIPTOR_SEED(); control_actual_length = 4097; DESCRIPTOR_ACCEPT(STATUS_SUCCESS, 18); /* bounded */
    DESCRIPTOR_SEED(); control_nt_status = STATUS_UNSUCCESSFUL; DESCRIPTOR_ACCEPT(STATUS_UNSUCCESSFUL, 0);
    DESCRIPTOR_SEED(); control_nt_status = STATUS_SUCCESS; control_urb_status = USBD_STATUS_TIMEOUT;
    DESCRIPTOR_ACCEPT(STATUS_IO_TIMEOUT, 0);
    DESCRIPTOR_SEED(); control_urb_status = USBD_STATUS_SUCCESS; control_returns_pending = TRUE;
    DESCRIPTOR_ACCEPT(STATUS_SUCCESS, 18); IO24_CHECK(effect.dispatch_status == STATUS_PENDING);
    DESCRIPTOR_SEED(); control_returns_pending = TRUE; control_nt_status = STATUS_UNSUCCESSFUL;
    DESCRIPTOR_ACCEPT(STATUS_UNSUCCESSFUL, 0); IO24_CHECK(effect.dispatch_status == STATUS_PENDING);
    control_returns_pending = FALSE; control_nt_status = STATUS_SUCCESS; control_urb_status = USBD_STATUS_SUCCESS;
    DESCRIPTOR_SEED(); DESCRIPTOR_ALLOC_REJECT(1);
    DESCRIPTOR_SEED(); DESCRIPTOR_ALLOC_REJECT(2);
    control_actual_length = 0;
#undef DESCRIPTOR_ALLOC_REJECT
#undef DESCRIPTOR_ACCEPT
#undef DESCRIPTOR_REJECT
#undef DESCRIPTOR_SEED

#undef CONTROL_ACCEPT
#undef CONTROL_PENDING
#undef CONTROL_ALLOC_REJECT
#undef CONTROL_REJECT
#undef CONTROL_REJECT_STATUS
#undef CONTROL_SEED
    teardown(&d, &g, &file);
}
static void run(const char*m){if(!strcmp(m,"--red")||!strcmp(m,"--lifecycle"))group_lifecycle();if(!strcmp(m,"--red")||!strcmp(m,"--initialize"))group_initialize();if(!strcmp(m,"--red")||!strcmp(m,"--session"))group_session();if(!strcmp(m,"--red")||!strcmp(m,"--alternate"))group_alternate();if(!strcmp(m,"--red")||!strcmp(m,"--policy"))group_policy();if(!strcmp(m,"--red")||!strcmp(m,"--transfer"))group_transfer();if(!strcmp(m,"--red")||!strcmp(m,"--control-descriptor"))group_control_descriptor();}
int main(int argc,char**argv){unsigned int retained;if(argc!=2)return 2;retained=io24_retained_cp32_main();if(retained){fprintf(stderr,"HARNESS: retained fake-WDM baseline failed\n");return 2;}run(argv[1]);printf("CP33 function executed mode=%s dispatches=%u mode-ioctls=%u last-ioctl=%#lx last-status=%#lx failures=%u\n",argv[1],counts.submits,mode_ioctls,(unsigned long)last_ioctl,(unsigned long)last_status,counts.failures);return counts.failures?1:0;}
