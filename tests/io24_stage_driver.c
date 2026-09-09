#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int BOOL;
typedef uint32_t DWORD;
typedef uint16_t WCHAR;

/* The binary Wine installation has winegcc and import libraries, but no SDK. */
extern BOOL __stdcall SetupCopyOEMInfW(const WCHAR *source,
                                      const WCHAR *location,
                                      DWORD media_type, DWORD style,
                                      WCHAR *destination,
                                      DWORD destination_size,
                                      DWORD *required_size,
                                      WCHAR **destination_component);
extern DWORD __stdcall GetLastError(void);

enum {
    MAX_WINDOWS_PATH = 260,
    SOURCE_MEDIA_PATH = 1,
};

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

static void print_utf16_ascii(const WCHAR *input)
{
    while (*input) {
        uint16_t character = *input++;
        fputc(character <= 0x7f ? (int)character : '?', stdout);
    }
}

int main(int argc, char **argv)
{
    WCHAR destination[MAX_WINDOWS_PATH] = {0};
    WCHAR *source;
    WCHAR *component = NULL;
    DWORD required_size = 0;
    BOOL copied;

    if (argc != 2) {
        fprintf(stderr, "usage: io24-stage-driver.exe WINDOWS_INF_PATH\n");
        return 2;
    }
    source = ascii_to_utf16(argv[1]);
    if (!source) {
        fprintf(stderr, "INF path must be ASCII and fit in memory\n");
        return 2;
    }

    copied = SetupCopyOEMInfW(source, NULL, SOURCE_MEDIA_PATH, 0,
                              destination, MAX_WINDOWS_PATH,
                              &required_size, &component);
    free(source);
    if (!copied) {
        fprintf(stderr, "SetupCopyOEMInfW failed: %u (required=%u)\n",
                GetLastError(), required_size);
        return 1;
    }

    fputs("staged INF: ", stdout);
    print_utf16_ascii(destination);
    fputc('\n', stdout);
    return 0;
}
