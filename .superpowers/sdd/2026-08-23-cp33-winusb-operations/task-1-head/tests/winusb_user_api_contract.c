/* Hardware-free CP33 public WinUSB surface contract. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)

static const char *const imports[] = {
    "WinUsb_AbortPipe", "WinUsb_ControlTransfer", "WinUsb_Free",
    "WinUsb_GetAssociatedInterface", "WinUsb_GetDescriptor",
    "WinUsb_GetOverlappedResult", "WinUsb_GetPipePolicy", "WinUsb_Initialize",
    "WinUsb_QueryDeviceInformation", "WinUsb_ReadPipe", "WinUsb_ResetPipe",
    "WinUsb_SetCurrentAlternateSetting", "WinUsb_SetPipePolicy", "WinUsb_WritePipe"
};

static char *read_file(const char *path)
{
    FILE *file; long size; char *data;
    if (!(file = fopen(path, "rb"))) return NULL;
    if (fseek(file, 0, SEEK_END) || (size = ftell(file)) < 0 || fseek(file, 0, SEEK_SET)) { fclose(file); return NULL; }
    if (!(data = malloc((size_t)size + 1))) { fclose(file); return NULL; }
    counts.allocations++;
    if (fread(data, 1, (size_t)size, file) != (size_t)size) { free(data); counts.frees++; fclose(file); return NULL; }
    data[size] = 0; fclose(file); return data;
}

int main(int argc, char **argv)
{
    char path[4096], *header, *main_source, *io_source = NULL, *spec;
    unsigned char guarded[18]; unsigned int prototypes = 0, definitions = 0, exports = 0, i;
    if (argc != 2) return 2;
    memset(guarded, GUARD_BYTE, sizeof(guarded));
    snprintf(path, sizeof(path), "%s/include/winusb.h", argv[1]); header = read_file(path);
    snprintf(path, sizeof(path), "%s/dlls/winusb/main.c", argv[1]); main_source = read_file(path);
    snprintf(path, sizeof(path), "%s/dlls/winusb/io.c", argv[1]); io_source = read_file(path);
    snprintf(path, sizeof(path), "%s/dlls/winusb/winusb.spec", argv[1]); spec = read_file(path);
    if (!header || !main_source || !spec) { fputs("HARNESS: missing public production input\n", stderr); return 2; }
    for (i = 0; i < sizeof(imports) / sizeof(imports[0]); ++i)
    {
        char definition[128], export_name[128];
        if (strstr(header, imports[i])) prototypes++;
        snprintf(definition, sizeof(definition), "WINAPI %s(", imports[i]);
        if (strstr(main_source, definition) || (io_source && strstr(io_source, definition))) definitions++;
        snprintf(export_name, sizeof(export_name), "stdcall %s(", imports[i]);
        if (strstr(spec, export_name)) exports++;
    }
    for (i = 0; i < sizeof(guarded); ++i) IO24_CHECK(guarded[i] == GUARD_BYTE);
    IO24_CHECK(prototypes == 14); IO24_CHECK(definitions == 14); IO24_CHECK(exports == 14);
    free(header); free(main_source); free(io_source); free(spec); counts.frees += 3 + !!io_source;
    IO24_CHECK(counts.allocations == counts.frees);
    printf("CP33 public RED: prototypes=%u/14 definitions=%u/14 callable-exports=%u/14 failures=%u\n",
            prototypes, definitions, exports, counts.failures);
    return counts.failures ? 1 : 0;
}
