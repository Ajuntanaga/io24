#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int32_t NTSTATUS;
typedef uint32_t ULONG;
typedef uint16_t USHORT;
typedef uint16_t WCHAR;
typedef void *HANDLE;

typedef struct {
    USHORT Length;
    USHORT MaximumLength;
    WCHAR *Buffer;
} UNICODE_STRING;

typedef struct {
    ULONG Length;
    HANDLE RootDirectory;
    UNICODE_STRING *ObjectName;
    ULONG Attributes;
    void *SecurityDescriptor;
    void *SecurityQualityOfService;
} OBJECT_ATTRIBUTES;

typedef struct {
    ULONG TitleIndex;
    ULONG Type;
    ULONG DataOffset;
    ULONG DataLength;
    ULONG NameLength;
    WCHAR Name[1];
} KEY_VALUE_FULL_INFORMATION;

typedef struct {
    ULONG TitleIndex;
    ULONG Type;
    ULONG DataLength;
    unsigned char Data[1];
} KEY_VALUE_PARTIAL_INFORMATION;

typedef NTSTATUS (__stdcall *RTL_QUERY_REGISTRY_ROUTINE)(
    const WCHAR *value_name, ULONG value_type, void *value_data,
    ULONG value_length, void *context, void *entry_context);

typedef struct {
    RTL_QUERY_REGISTRY_ROUTINE QueryRoutine;
    ULONG Flags;
    WCHAR *Name;
    void *EntryContext;
    ULONG DefaultType;
    void *DefaultData;
    ULONG DefaultLength;
} RTL_QUERY_REGISTRY_TABLE;

typedef struct {
    ULONG ExpectedType;
    void *Buffer;
    ULONG BufferLength;
    NTSTATUS Status;
} DRIVER_QUERY_CONTEXT;

enum {
    KEY_VALUE_FULL_INFORMATION_CLASS = 1,
    KEY_VALUE_PARTIAL_INFORMATION_CLASS = 2,
    KEY_SERVICE_ACCESS = 0x0002001f,
    KEY_READ_ACCESS = 0x00020019,
    OBJECT_ATTRIBUTES_FLAGS = 0x00000240,
    REG_DWORD_TYPE = 4,
    RTL_REGISTRY_HANDLE = 0x40000000,
    RTL_QUERY_REGISTRY_REQUIRED = 0x00000004,
    RTL_QUERY_REGISTRY_DIRECT = 0x00000020,
};

enum {
    DRIVER_TAG_BUFFER_LENGTH = 47,
    DRIVER_TAG_LENGTH = 32,
    REG_BINARY_TYPE = 3,
};

extern NTSTATUS __stdcall NtClose(HANDLE handle);
extern NTSTATUS __stdcall NtCreateKey(HANDLE *handle, ULONG access,
                                      const OBJECT_ATTRIBUTES *attributes,
                                      ULONG title_index,
                                      const UNICODE_STRING *class_name,
                                      ULONG create_options,
                                      ULONG *disposition);
extern NTSTATUS __stdcall NtOpenKey(HANDLE *handle, ULONG access,
                                    const OBJECT_ATTRIBUTES *attributes);
extern NTSTATUS __stdcall NtQueryValueKey(
    HANDLE handle, const UNICODE_STRING *name, int information_class,
    void *information, ULONG information_length, ULONG *result_length);
extern NTSTATUS __stdcall RtlQueryRegistryValues(
    ULONG relative_to, const WCHAR *path, RTL_QUERY_REGISTRY_TABLE *query_table,
    void *context, void *environment);

static WCHAR *ascii_to_utf16(const char *input)
{
    size_t i;
    size_t length = strlen(input);
    WCHAR *output = calloc(length + 1, sizeof(*output));

    if (!output)
        return NULL;
    for (i = 0; i < length; ++i) {
        unsigned char character = (unsigned char)input[i];

        if (character > 0x7f) {
            free(output);
            return NULL;
        }
        output[i] = character;
    }
    return output;
}

static UNICODE_STRING make_unicode_string(WCHAR *buffer)
{
    size_t length = 0;
    UNICODE_STRING string;

    while (buffer[length])
        ++length;
    string.Length = (USHORT)(length * sizeof(*buffer));
    string.MaximumLength = string.Length + sizeof(*buffer);
    string.Buffer = buffer;
    return string;
}

static OBJECT_ATTRIBUTES make_object_attributes(HANDLE root,
                                                UNICODE_STRING *name)
{
    OBJECT_ATTRIBUTES attributes = {0};

    attributes.Length = sizeof(attributes);
    attributes.RootDirectory = root;
    attributes.ObjectName = name;
    attributes.Attributes = OBJECT_ATTRIBUTES_FLAGS;
    return attributes;
}

static NTSTATUS open_license_key(HANDLE *service, HANDLE *parameters,
                                 HANDLE *license)
{
    WCHAR *service_buffer = ascii_to_utf16(
        "\\Registry\\Machine\\System\\CurrentControlSet\\Services\\PaeDSPUSB");
    WCHAR *parameters_buffer = ascii_to_utf16("ParametersDriver");
    WCHAR *license_buffer = ascii_to_utf16("License");
    UNICODE_STRING service_name;
    UNICODE_STRING parameters_name;
    UNICODE_STRING license_name;
    OBJECT_ATTRIBUTES attributes;
    ULONG disposition = 0;
    NTSTATUS status;

    if (!service_buffer || !parameters_buffer || !license_buffer) {
        status = (NTSTATUS)0xc0000017;
        goto out;
    }

    service_name = make_unicode_string(service_buffer);
    attributes = make_object_attributes(NULL, &service_name);
    status = NtOpenKey(service, KEY_SERVICE_ACCESS, &attributes);
    printf("NtOpenKey service status=0x%08" PRIx32 " handle=%p\n",
           (uint32_t)status, *service);
    if (status)
        goto out;

    parameters_name = make_unicode_string(parameters_buffer);
    attributes = make_object_attributes(*service, &parameters_name);
    status = NtCreateKey(parameters, KEY_SERVICE_ACCESS, &attributes, 0, NULL,
                         0, &disposition);
    printf("NtCreateKey ParametersDriver status=0x%08" PRIx32
           " handle=%p disposition=%" PRIu32 "\n",
           (uint32_t)status, *parameters, disposition);
    if (status)
        goto out;

    license_name = make_unicode_string(license_buffer);
    attributes = make_object_attributes(*parameters, &license_name);
    status = NtOpenKey(license, KEY_READ_ACCESS, &attributes);
    printf("NtOpenKey License status=0x%08" PRIx32 " handle=%p\n",
           (uint32_t)status, *license);

out:
    free(license_buffer);
    free(parameters_buffer);
    free(service_buffer);
    return status;
}

static void close_key(HANDLE *handle)
{
    if (*handle) {
        NtClose(*handle);
        *handle = NULL;
    }
}

static NTSTATUS close_key_checked(HANDLE *handle, const char *label)
{
    NTSTATUS status = 0;

    if (*handle) {
        status = NtClose(*handle);
        printf("NtClose caller-owned %s status=0x%08" PRIx32
               " handle=%p\n",
               label, (uint32_t)status, *handle);
        *handle = NULL;
    }
    return status;
}

static void query_value(HANDLE license, const char *value_name)
{
    WCHAR *name_buffer = ascii_to_utf16(value_name);
    UNICODE_STRING name;
    KEY_VALUE_FULL_INFORMATION *information = NULL;
    ULONG required = 0;
    ULONG buffer_length;
    NTSTATUS status;

    if (!name_buffer) {
        printf("NtQueryValueKey name=%s setup=out-of-memory\n", value_name);
        return;
    }
    name = make_unicode_string(name_buffer);
    status = NtQueryValueKey(license, &name,
                             KEY_VALUE_FULL_INFORMATION_CLASS,
                             NULL, 0, &required);
    printf("NtQueryValueKey name=%s phase=size status=0x%08" PRIx32
           " required=%" PRIu32 "\n",
           value_name, (uint32_t)status, required);

    if (required) {
        buffer_length = required + sizeof(ULONG);
        information = calloc(1, buffer_length);
        if (information) {
            status = NtQueryValueKey(license, &name,
                                     KEY_VALUE_FULL_INFORMATION_CLASS,
                                     information, buffer_length, &required);
            printf("NtQueryValueKey name=%s phase=data status=0x%08" PRIx32
                   " returned=%" PRIu32,
                   value_name, (uint32_t)status, required);
            if (!status &&
                information->DataOffset <= buffer_length &&
                information->DataLength <=
                    buffer_length - information->DataOffset) {
                printf(" type=%" PRIu32 " data_length=%" PRIu32,
                       information->Type, information->DataLength);
                if (information->Type == REG_DWORD_TYPE &&
                    information->DataLength == sizeof(ULONG)) {
                    ULONG value;

                    memcpy(&value,
                           (char *)information + information->DataOffset,
                           sizeof(value));
                    printf(" value=0x%08" PRIx32, value);
                }
            }
            putchar('\n');
        } else {
            printf("NtQueryValueKey name=%s phase=data setup=out-of-memory\n",
                   value_name);
        }
    } else {
        printf("NtQueryValueKey name=%s phase=data skipped=zero-length\n",
               value_name);
    }

    free(information);
    free(name_buffer);
}

static NTSTATUS query_driver_sized_tag(HANDLE license)
{
    WCHAR *name_buffer = ascii_to_utf16("tag");
    UNICODE_STRING name;
    unsigned char buffer[DRIVER_TAG_BUFFER_LENGTH] = {0};
    KEY_VALUE_PARTIAL_INFORMATION *information =
        (KEY_VALUE_PARTIAL_INFORMATION *)buffer;
    ULONG returned = 0;
    NTSTATUS status;

    if (!name_buffer)
        return (NTSTATUS)0xc0000017;

    name = make_unicode_string(name_buffer);
    status = NtQueryValueKey(license, &name,
                             KEY_VALUE_PARTIAL_INFORMATION_CLASS,
                             information, sizeof(buffer), &returned);
    printf("NtQueryValueKey name=tag class=partial buffer=%zu"
           " status=0x%08" PRIx32 " returned=%" PRIu32,
           sizeof(buffer), (uint32_t)status, returned);
    if (!status)
        printf(" type=%" PRIu32 " data_length=%" PRIu32,
               information->Type, information->DataLength);
    putchar('\n');

    if (!status &&
        (information->Type != REG_BINARY_TYPE ||
         information->DataLength != DRIVER_TAG_LENGTH))
        status = (NTSTATUS)0xc0000001;

    free(name_buffer);
    return status;
}

static NTSTATUS __stdcall inspect_driver_callback(
    const WCHAR *value_name, ULONG value_type, void *value_data,
    ULONG value_length, void *context, void *entry_context)
{
    DRIVER_QUERY_CONTEXT *query = entry_context;

    (void)value_name;
    (void)context;
    printf("driver-callback type=%" PRIu32 " length=%" PRIu32
           " expected_type=%" PRIu32 " capacity=%" PRIu32 "\n",
           value_type, value_length, query->ExpectedType,
           query->BufferLength);
    if (!value_data || value_type != query->ExpectedType ||
        value_length < sizeof(ULONG) || query->BufferLength < sizeof(ULONG)) {
        query->Status = (NTSTATUS)0xc0000001;
        return 0;
    }

    memcpy(query->Buffer, value_data, sizeof(ULONG));
    query->BufferLength = sizeof(ULONG);
    query->Status = 0;
    return 0;
}

static NTSTATUS query_driver_callback_value(HANDLE license,
                                            const char *value_name,
                                            ULONG expected_value)
{
    WCHAR *name_buffer = ascii_to_utf16(value_name);
    RTL_QUERY_REGISTRY_TABLE table[2] = {{0}};
    ULONG value = 0;
    DRIVER_QUERY_CONTEXT query = {
        REG_DWORD_TYPE,
        &value,
        sizeof(value),
        (NTSTATUS)0xc0000001,
    };
    NTSTATUS status;

    if (!name_buffer)
        return (NTSTATUS)0xc0000017;

    table[0].QueryRoutine = inspect_driver_callback;
    table[0].Flags = RTL_QUERY_REGISTRY_REQUIRED;
    table[0].Name = name_buffer;
    table[0].EntryContext = &query;
    status = RtlQueryRegistryValues(RTL_REGISTRY_HANDLE,
                                    (const WCHAR *)license,
                                    table, NULL, NULL);
    printf("RtlQueryRegistryValues callback name=%s status=0x%08" PRIx32
           " callback_status=0x%08" PRIx32 " value=0x%08" PRIx32
           " expected=0x%08" PRIx32 "\n",
           value_name, (uint32_t)status, (uint32_t)query.Status, value,
           expected_value);
    if (!status)
        status = query.Status;
    if (!status && value != expected_value)
        status = (NTSTATUS)0xc0000001;

    free(name_buffer);
    return status;
}

static int query_rtl_value(const char *value_name)
{
    HANDLE service = NULL;
    HANDLE parameters = NULL;
    HANDLE license = NULL;
    WCHAR *name_buffer = ascii_to_utf16(value_name);
    RTL_QUERY_REGISTRY_TABLE table[2] = {{0}};
    ULONG value = 0xcccccccc;
    NTSTATUS status;
    NTSTATUS close_status;
    int query_failed = 0;
    int setup_failed = 0;

    if (!name_buffer) {
        printf("RtlQueryRegistryValues name=%s setup=out-of-memory\n",
               value_name);
        return 1;
    }

    status = open_license_key(&service, &parameters, &license);
    if (status) {
        setup_failed = 1;
        goto out;
    }

    table[0].Flags = RTL_QUERY_REGISTRY_DIRECT |
                     RTL_QUERY_REGISTRY_REQUIRED;
    table[0].Name = name_buffer;
    table[0].EntryContext = &value;
    status = RtlQueryRegistryValues(RTL_REGISTRY_HANDLE,
                                    (const WCHAR *)license,
                                    table, NULL, NULL);
    printf("RtlQueryRegistryValues name=%s status=0x%08" PRIx32
           " value=0x%08" PRIx32 "\n",
           value_name, (uint32_t)status, value);
    query_failed = !!status;
    close_status = close_key_checked(&license, "License");
    query_failed |= !!close_status;

out:
    close_key(&license);
    close_key(&parameters);
    close_key(&service);
    free(name_buffer);
    return setup_failed || query_failed;
}

int main(void)
{
    HANDLE service = NULL;
    HANDLE parameters = NULL;
    HANDLE license = NULL;
    NTSTATUS status;

    status = open_license_key(&service, &parameters, &license);
    if (status)
        goto out;

    query_value(license, "tag");
    query_value(license, "format");
    query_value(license, "options");
    status = query_driver_sized_tag(license);
    if (status)
        goto out;
    status = query_driver_callback_value(license, "format", 0x00000006);
    if (status)
        goto out;
    status = query_driver_callback_value(license, "options", 0x0000010c);
    if (status)
        goto out;
    status = query_driver_callback_value(license, "customer", 0x00000361);
    if (status)
        goto out;

    status = close_key_checked(&license, "License");
    if (status)
        goto out;

    close_key(&parameters);
    close_key(&service);
    if (query_rtl_value("format") || query_rtl_value("options"))
        status = (NTSTATUS)0xc0000001;

out:
    close_key(&license);
    close_key(&parameters);
    close_key(&service);
    return status ? 1 : 0;
}
