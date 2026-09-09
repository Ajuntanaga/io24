/*
 * Device-free behavior contract for WineUSB Microsoft OS 1.0 discovery.
 *
 * The real WineUSB Unix library enumerates a synthetic io24 through the fake
 * libusb SONAME.  Each process runs one descriptor scenario and checks exact
 * control-request behavior plus the metadata carried on function events.
 */

#include <dlfcn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libusb.h>

#include "ntstatus.h"
#include "windef.h"
#include "winternl.h"
#include "ddk/wdm.h"
#include "ddk/usb.h"
#include "unixlib.h"

unsigned int io24_fake_libusb_request_count(void);
unsigned int io24_fake_libusb_request_mismatch_count(void);

static unsigned int failures;
static const unixlib_entry_t *unix_calls;

#define CHECK(condition, ...) \
    do \
    { \
        if (!(condition)) \
        { \
            fprintf(stderr, "FAIL %s:%u: ", __func__, __LINE__); \
            fprintf(stderr, __VA_ARGS__); \
            fputc('\n', stderr); \
            ++failures; \
        } \
    } while (0)

struct enumerated_device
{
    struct unix_device *unix_device;
    bool interface;
    int16_t interface_index;
    uint8_t class, subclass, protocol, ms_vendor_code;
    char compatible_id[WINEUSB_MS_OS_10_ID_SIZE];
    char sub_compatible_id[WINEUSB_MS_OS_10_ID_SIZE];
    WCHAR device_interface_guid[WINEUSB_MS_OS_10_GUID_SIZE];
};

struct scenario_contract
{
    const char *name;
    unsigned int request_count;
    const char *id5, *sub5, *guid5;
    const char *id6, *sub6, *guid6;
};

static const struct scenario_contract scenarios[] =
{
    {"valid", 7,
        "WINUSB", "", "{11111111-2222-3333-4444-555555555555}",
        "WINUSB", "", "{aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee}"},
    {"no_string", 1, "", "", "", "", "", ""},
    {"bad_string", 1, "", "", "", "", "", ""},
    {"malformed_compat", 2, "", "", "", "", "", ""},
    {"truncated_compat", 3, "", "", "", "", "", ""},
    {"oversize_compat", 2, "", "", "", "", "", ""},
    {"malformed_properties", 6,
        "WINUSB", "", "", "WINUSB", "", ""},
    {"unrelated_property", 7,
        "WINUSB", "", "{11111111-2222-3333-4444-555555555555}",
        "WINUSB", "", "{aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee}"},
    {"mixed_ids", 7,
        "WINUSB", "", "{11111111-2222-3333-4444-555555555555}",
        "XUSB10", "ABC", "{aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee}"},
    {"unknown_interface", 5,
        "WINUSB", "", "{11111111-2222-3333-4444-555555555555}",
        "", "", ""},
    {"malformed_second_function", 3, "", "", "", "", "", ""},
};

static const struct scenario_contract *find_scenario(const char *name)
{
    unsigned int i;

    for (i = 0; i < ARRAY_SIZE(scenarios); ++i)
        if (!strcmp(name, scenarios[i].name)) return &scenarios[i];
    return NULL;
}

static void collect_device(struct enumerated_device *device)
{
    struct usb_event event;
    struct usb_main_loop_params params = {.event = &event};
    NTSTATUS status;

    memset(&event, 0, sizeof(event));
    status = unix_calls[unix_usb_main_loop](&params);
    CHECK(status == STATUS_PENDING, "event loop returned %#lx", (long)status);
    CHECK(event.type == USB_EVENT_ADD_DEVICE, "event type is %u", event.type);
    if (status != STATUS_PENDING || event.type != USB_EVENT_ADD_DEVICE)
    {
        memset(device, 0, sizeof(*device));
        return;
    }

    memset(device, 0, sizeof(*device));
    device->unix_device = event.u.added_device.device;
    device->interface = event.u.added_device.interface;
    device->interface_index = event.u.added_device.interface_index;
    device->class = event.u.added_device.class;
    device->subclass = event.u.added_device.subclass;
    device->protocol = event.u.added_device.protocol;
    device->ms_vendor_code = event.u.added_device.ms_vendor_code;
    memcpy(device->compatible_id, event.u.added_device.ms_compatible_id,
            sizeof(device->compatible_id));
    memcpy(device->sub_compatible_id, event.u.added_device.ms_sub_compatible_id,
            sizeof(device->sub_compatible_id));
    memcpy(device->device_interface_guid, event.u.added_device.device_interface_guid,
            sizeof(device->device_interface_guid));
}

static bool wide_equals_ascii(const WCHAR *wide, const char *ascii)
{
    size_t i, length = strlen(ascii);

    if (length >= WINEUSB_MS_OS_10_GUID_SIZE) return false;
    for (i = 0; i < length; ++i)
        if (wide[i] != (unsigned char)ascii[i]) return false;
    return wide[length] == 0;
}

static void check_metadata(const struct enumerated_device *device,
        const char *id, const char *sub_id, const char *guid)
{
    CHECK(!strncmp(device->compatible_id, id, sizeof(device->compatible_id)),
            "MI%02d compatible ID is '%.*s', expected '%s'", device->interface_index,
            (int)sizeof(device->compatible_id), device->compatible_id, id);
    CHECK(!strncmp(device->sub_compatible_id, sub_id, sizeof(device->sub_compatible_id)),
            "MI%02d sub-compatible ID is '%.*s', expected '%s'", device->interface_index,
            (int)sizeof(device->sub_compatible_id), device->sub_compatible_id, sub_id);
    CHECK(wide_equals_ascii(device->device_interface_guid, guid),
            "MI%02d device-interface GUID differs", device->interface_index);
    CHECK(device->ms_vendor_code == (id[0] ? 0xa5 : 0),
            "MI%02d vendor code is %#x, expected %#x", device->interface_index,
            device->ms_vendor_code, id[0] ? 0xa5 : 0);
}

static void test_events(const struct scenario_contract *contract)
{
    static const int16_t expected_indices[] = {-1, 0, 3, 5, 6};
    static const uint8_t expected_classes[] = {0, 1, 1, 0xff, 0xfe};
    struct enumerated_device devices[5];
    unsigned int i;

    for (i = 0; i < ARRAY_SIZE(devices); ++i)
    {
        collect_device(&devices[i]);
        CHECK(devices[i].interface == (i != 0),
                "event %u interface flag is %u", i, devices[i].interface);
        CHECK(devices[i].interface_index == expected_indices[i],
                "event %u interface index is %d, expected %d", i,
                devices[i].interface_index, expected_indices[i]);
        CHECK(devices[i].class == expected_classes[i],
                "event %u class is %#x, expected %#x", i,
                devices[i].class, expected_classes[i]);
    }

    check_metadata(&devices[0], "", "", "");
    check_metadata(&devices[1], "", "", "");
    check_metadata(&devices[2], "", "", "");
    check_metadata(&devices[3], contract->id5, contract->sub5, contract->guid5);
    check_metadata(&devices[4], contract->id6, contract->sub6, contract->guid6);
}

int main(int argc, char **argv)
{
    const struct scenario_contract *contract;
    struct usb_main_loop_params loop_params = {0};
    const char *scenario_name = getenv("IO24_MS_OS_SCENARIO");
    void *module;
    NTSTATUS status;

    if (argc != 2)
    {
        fprintf(stderr, "usage: %s WINEUSB_UNIXLIB\n", argv[0]);
        return 2;
    }
    if (!scenario_name) scenario_name = "valid";
    if (!(contract = find_scenario(scenario_name)))
    {
        fprintf(stderr, "unknown IO24_MS_OS_SCENARIO: %s\n", scenario_name);
        return 2;
    }

    module = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
    if (!module)
    {
        fprintf(stderr, "FAIL: dlopen: %s\n", dlerror());
        return 1;
    }
    unix_calls = dlsym(module, "__wine_unix_call_funcs");
    if (!unix_calls)
    {
        fprintf(stderr, "FAIL: dlsym: %s\n", dlerror());
        return 1;
    }

    status = unix_calls[unix_usb_init](NULL);
    CHECK(status == STATUS_SUCCESS, "usb init returned %#lx", (long)status);
    test_events(contract);
    CHECK(io24_fake_libusb_request_count() == contract->request_count,
            "scenario %s made %u descriptor request(s), expected %u", contract->name,
            io24_fake_libusb_request_count(), contract->request_count);
    CHECK(io24_fake_libusb_request_mismatch_count() == 0,
            "scenario %s made %u malformed request(s)", contract->name,
            io24_fake_libusb_request_mismatch_count());

    unix_calls[unix_usb_exit](NULL);
    status = unix_calls[unix_usb_main_loop](&loop_params);
    CHECK(status == STATUS_SUCCESS, "shutdown loop returned %#lx", (long)status);
    dlclose(module);

    if (failures)
    {
        fprintf(stderr, "%u Microsoft OS 1.0 contract check(s) failed in %s\n",
                failures, contract->name);
        return 1;
    }
    printf("WineUSB Microsoft OS 1.0 contract: pass (%s)\n", contract->name);
    return 0;
}
