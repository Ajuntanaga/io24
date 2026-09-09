/* Offline contract for Microsoft OS 1.0 PnP compatible-ID formatting. */

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "msos_id.h"

static unsigned int failures;

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

struct guarded_ids
{
    struct wineusb_ms_os_10_pnp_ids ids;
    unsigned char guard[32];
};

static bool wide_equals_ascii(const WCHAR *wide, const char *ascii)
{
    size_t i, length = strlen(ascii);

    for (i = 0; i < length; ++i)
        if (wide[i] != (unsigned char)ascii[i]) return false;
    return wide[length] == 0;
}

static void reset_guarded(struct guarded_ids *guarded)
{
    memset(guarded, 0xa5, sizeof(*guarded));
}

static void check_guard(const struct guarded_ids *guarded)
{
    static const unsigned char expected[32] =
    {
        0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
        0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
        0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
        0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5,
    };

    CHECK(!memcmp(guarded->guard, expected, sizeof(expected)), "output guard changed");
}

static void test_winusb_id(void)
{
    const char compatible[WINEUSB_MS_OS_10_SOURCE_ID_SIZE] = "WINUSB";
    const char sub_compatible[WINEUSB_MS_OS_10_SOURCE_ID_SIZE] = "";
    struct guarded_ids guarded;

    reset_guarded(&guarded);
    CHECK(wineusb_ms_os_10_build_pnp_ids(compatible, sub_compatible, &guarded.ids),
            "WINUSB was rejected");
    CHECK(guarded.ids.count == 1, "ID count is %u", guarded.ids.count);
    CHECK(wide_equals_ascii(guarded.ids.ids[0], "USB\\MS_COMP_WINUSB"),
            "WINUSB PnP ID differs");
    CHECK(guarded.ids.ids[1][0] == 0, "unused ID is not empty");
    check_guard(&guarded);
}

static void test_subcompatible_ranking(void)
{
    const char compatible[WINEUSB_MS_OS_10_SOURCE_ID_SIZE] = "XUSB10";
    const char sub_compatible[WINEUSB_MS_OS_10_SOURCE_ID_SIZE] = "ABC";
    struct guarded_ids guarded;

    reset_guarded(&guarded);
    CHECK(wineusb_ms_os_10_build_pnp_ids(compatible, sub_compatible, &guarded.ids),
            "sub-compatible ID was rejected");
    CHECK(guarded.ids.count == 2, "ID count is %u", guarded.ids.count);
    CHECK(wide_equals_ascii(guarded.ids.ids[0],
            "USB\\MS_COMP_XUSB10&MS_SUBCOMP_ABC"), "specific PnP ID differs");
    CHECK(wide_equals_ascii(guarded.ids.ids[1], "USB\\MS_COMP_XUSB10"),
            "fallback PnP ID differs");
    check_guard(&guarded);
}

static void test_full_width_id(void)
{
    const char compatible[WINEUSB_MS_OS_10_SOURCE_ID_SIZE] = "BLUTUTH";
    const char sub_compatible[WINEUSB_MS_OS_10_SOURCE_ID_SIZE] = "EDR";
    struct guarded_ids guarded;

    reset_guarded(&guarded);
    CHECK(wineusb_ms_os_10_build_pnp_ids(compatible, sub_compatible, &guarded.ids),
            "eight-byte compatible ID was rejected");
    CHECK(wide_equals_ascii(guarded.ids.ids[0],
            "USB\\MS_COMP_BLUTUTH&MS_SUBCOMP_EDR"), "full-width PnP ID differs");
    check_guard(&guarded);
}

static void test_invalid_ids_fail_closed(void)
{
    static const char cases[][2][WINEUSB_MS_OS_10_SOURCE_ID_SIZE] =
    {
        {{0}, {0}},
        {{'W', 'i', 'N', 'U', 'S', 'B', 0, 0, 0}, {0}},
        {{'W', 0, 'N', 0, 0, 0, 0, 0, 0}, {0}},
        {{'W', 'I', 'N', '-', 'U', 'S', 'B', 0, 0}, {0}},
        {{'W', 'I', 'N', 'U', 'S', 'B', 0, 0, 1}, {0}},
        {{'W', 'I', 'N', 'U', 'S', 'B', 0, 0, 0}, {'a', 0}},
    };
    unsigned int i;

    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
    {
        struct guarded_ids guarded;

        reset_guarded(&guarded);
        CHECK(!wineusb_ms_os_10_build_pnp_ids(cases[i][0], cases[i][1], &guarded.ids),
                "invalid case %u was accepted", i);
        CHECK(guarded.ids.count == 0, "invalid case %u left count %u",
                i, guarded.ids.count);
        CHECK(guarded.ids.ids[0][0] == 0 && guarded.ids.ids[1][0] == 0,
                "invalid case %u left output", i);
        check_guard(&guarded);
    }
}

int main(void)
{
    test_winusb_id();
    test_subcompatible_ranking();
    test_full_width_id();
    test_invalid_ids_fail_closed();

    if (failures)
    {
        fprintf(stderr, "%u Microsoft OS 1.0 ID contract check(s) failed\n", failures);
        return 1;
    }
    puts("WineUSB Microsoft OS 1.0 PnP ID contract: pass");
    return 0;
}
