/*
 * io24 UC-derived compressor -- a small mono LADSPA processor.
 *
 * Universal Control's Standard, Tube and FET builders all reduce their public
 * controls to the same cpxt tuple.  This plugin consumes that tuple directly:
 * the five device-order side-chain biquad coefficients, attack, release,
 * slope, knee, threshold, linear makeup and key-listen flag.
 *
 * It deliberately contains no model presets.  io24_uc_comp.py remains the
 * single source of truth for translating each UC model into this common form.
 */

#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef float LADSPA_Data;
typedef void *LADSPA_Handle;
/* LADSPA's descriptor and hint words are 32-bit `int`, including on LP64.
 * Keeping these ABI types exact matters: an unsigned long array would make
 * PipeWire read every second port as zero and stride range hints incorrectly. */
typedef int LADSPA_PortDescriptor;
typedef int LADSPA_Properties;
typedef int LADSPA_PortRangeHintDescriptor;

typedef struct {
    LADSPA_PortRangeHintDescriptor HintDescriptor;
    LADSPA_Data LowerBound;
    LADSPA_Data UpperBound;
} LADSPA_PortRangeHint;

typedef struct _LADSPA_Descriptor {
    unsigned long UniqueID;
    const char *Label;
    LADSPA_Properties Properties;
    const char *Name;
    const char *Maker;
    const char *Copyright;
    unsigned long PortCount;
    const LADSPA_PortDescriptor *PortDescriptors;
    const char *const *PortNames;
    const LADSPA_PortRangeHint *PortRangeHints;
    void *ImplementationData;
    LADSPA_Handle (*instantiate)(const struct _LADSPA_Descriptor *,
                                 unsigned long);
    void (*connect_port)(LADSPA_Handle, unsigned long, LADSPA_Data *);
    void (*activate)(LADSPA_Handle);
    void (*run)(LADSPA_Handle, unsigned long);
    void (*run_adding)(LADSPA_Handle, unsigned long);
    void (*set_run_adding_gain)(LADSPA_Handle, LADSPA_Data);
    void (*deactivate)(LADSPA_Handle);
    void (*cleanup)(LADSPA_Handle);
} LADSPA_Descriptor;

#define LADSPA_PORT_INPUT 0x1UL
#define LADSPA_PORT_OUTPUT 0x2UL
#define LADSPA_PORT_CONTROL 0x4UL
#define LADSPA_PORT_AUDIO 0x8UL
#define LADSPA_PROPERTY_HARD_RT_CAPABLE 0x4UL
#define LADSPA_HINT_BOUNDED_BELOW 0x1UL
#define LADSPA_HINT_BOUNDED_ABOVE 0x2UL
#define LADSPA_HINT_TOGGLED 0x4UL
#define LADSPA_HINT_LOGARITHMIC 0x10UL

enum {
    P_B0,
    P_NA1,
    P_B1,
    P_NA2,
    P_B2,
    P_ATTACK,
    P_RELEASE,
    P_SLOPE,
    P_KNEE,
    P_THRESHOLD,
    P_MAKEUP,
    P_KEY_LISTEN,
    P_INPUT,
    P_OUTPUT,
    PORT_COUNT
};

enum { CONTROL_COUNT = P_KEY_LISTEN + 1 };

typedef struct {
    unsigned long sample_rate;
    LADSPA_Data *ports[PORT_COUNT];
    float x1;
    float x2;
    float y1;
    float y2;
    float rms_power;
    float reduction_db;
} Io24Comp;

static float finite_or(float value, float fallback)
{
    return isfinite(value) ? value : fallback;
}

static float bounded(float value, float low, float high)
{
    return value < low ? low : value > high ? high : value;
}

static void reset_state(Io24Comp *self)
{
    self->x1 = 0.0f;
    self->x2 = 0.0f;
    self->y1 = 0.0f;
    self->y2 = 0.0f;
    self->rms_power = 0.0f;
    self->reduction_db = 0.0f;
}

static float knee_reduction(float level_db, float threshold_db,
                            float slope, float knee_db)
{
    const float over = level_db - threshold_db;
    if (knee_db <= 0.011f)
        return over > 0.0f ? slope * over : 0.0f;

    /* Firmware derives knee_a=0.5/sqrt(K), knee_b=0.5*sqrt(K).
     * Therefore K is the half-width and the curved region is the square of
     * knee_a*over+knee_b from -K to +K. */
    if (over <= -knee_db)
        return 0.0f;
    if (over >= knee_db)
        return slope * over;
    const float root = sqrtf(knee_db);
    const float curved = 0.5f * over / root + 0.5f * root;
    return slope * curved * curved;
}

static void process(Io24Comp *self, const float *input, float *output,
                    unsigned long frames, const float *controls)
{
    const float b0 = finite_or(controls[P_B0], 1.0f);
    const float na1 = finite_or(controls[P_NA1], 0.0f);
    const float b1 = finite_or(controls[P_B1], 0.0f);
    const float na2 = finite_or(controls[P_NA2], 0.0f);
    const float b2 = finite_or(controls[P_B2], 0.0f);
    const float attack_s = bounded(finite_or(controls[P_ATTACK], 0.02f),
                                   0.000001f, 10.0f);
    const float release_s = bounded(finite_or(controls[P_RELEASE], 0.15f),
                                    0.000001f, 20.0f);
    const float slope = bounded(finite_or(controls[P_SLOPE], 0.5f), 0.0f, 1.0f);
    const float knee = bounded(finite_or(controls[P_KNEE], 0.01f),
                               0.001f, 24.0f);
    const float threshold = bounded(finite_or(controls[P_THRESHOLD], 0.0f),
                                    -120.0f, 24.0f);
    const float makeup = bounded(finite_or(controls[P_MAKEUP], 1.0f),
                                 0.0000001f, 1024.0f);
    const int key_listen = controls[P_KEY_LISTEN] >= 0.5f;
    const float fs = (float)(self->sample_rate ? self->sample_rate : 48000UL);

    /* The firmware derives these exact two time constants from cpxt. */
    const float attack_step = bounded(1.0f / (attack_s * fs), 0.0f, 1.0f);
    const float release_keep = expf(-6.2831853071795864769f / (release_s * fs));

    /* A 10 ms power average makes the detector genuinely RMS.  Attack and
     * release then govern gain reduction, independently of the RMS window. */
    const float rms_keep = expf(-1.0f / (0.010f * fs));
    const float rms_take = 1.0f - rms_keep;

    float x1 = self->x1, x2 = self->x2;
    float y1 = self->y1, y2 = self->y2;
    float power = self->rms_power;
    float reduction = self->reduction_db;

    for (unsigned long i = 0; i < frames; ++i) {
        const float x = finite_or(input[i], 0.0f);
        const float key = b0 * x + b1 * x1 + b2 * x2 + na1 * y1 + na2 * y2;
        x2 = x1;
        x1 = x;
        y2 = y1;
        y1 = key;

        power = rms_keep * power + rms_take * key * key;
        if (power < 1.0e-30f)
            power = 0.0f;
        const float level_db = power > 0.0f ? 10.0f * log10f(power) : -200.0f;
        const float target = knee_reduction(level_db, threshold, slope, knee);
        if (target > reduction)
            reduction += attack_step * (target - reduction);
        else
            reduction = release_keep * reduction + (1.0f - release_keep) * target;

        if (key_listen)
            output[i] = key;
        else
            output[i] = x * makeup * powf(10.0f, -0.05f * reduction);
    }

    self->x1 = x1;
    self->x2 = x2;
    self->y1 = y1;
    self->y2 = y2;
    self->rms_power = power;
    self->reduction_db = reduction;
}

static LADSPA_Handle instantiate(const LADSPA_Descriptor *descriptor,
                                 unsigned long sample_rate)
{
    (void)descriptor;
    Io24Comp *self = (Io24Comp *)calloc(1, sizeof(*self));
    if (self != NULL)
        self->sample_rate = sample_rate;
    return (LADSPA_Handle)self;
}

static void connect_port(LADSPA_Handle instance, unsigned long port,
                         LADSPA_Data *data)
{
    Io24Comp *self = (Io24Comp *)instance;
    if (self != NULL && port < PORT_COUNT)
        self->ports[port] = data;
}

static void activate(LADSPA_Handle instance)
{
    if (instance != NULL)
        reset_state((Io24Comp *)instance);
}

static void run(LADSPA_Handle instance, unsigned long frames)
{
    Io24Comp *self = (Io24Comp *)instance;
    if (self == NULL || self->ports[P_INPUT] == NULL ||
            self->ports[P_OUTPUT] == NULL)
        return;

    float controls[CONTROL_COUNT];
    for (unsigned long i = 0; i < CONTROL_COUNT; ++i)
        controls[i] = self->ports[i] != NULL ? *self->ports[i] : 0.0f;
    process(self, self->ports[P_INPUT], self->ports[P_OUTPUT], frames, controls);
}

static void cleanup(LADSPA_Handle instance)
{
    free(instance);
}

/* A direct, stateless entry point for deterministic hardware-free tests. */
int io24_uc_comp_process(const float *input, float *output,
                         unsigned long frames, unsigned long sample_rate,
                         const float *controls)
{
    if (input == NULL || output == NULL || controls == NULL || sample_rate == 0)
        return -1;
    Io24Comp self;
    memset(&self, 0, sizeof(self));
    self.sample_rate = sample_rate;
    process(&self, input, output, frames, controls);
    return 0;
}

static const LADSPA_PortDescriptor port_descriptors[PORT_COUNT] = {
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_OUTPUT | LADSPA_PORT_AUDIO,
};

static const char *const port_names[PORT_COUNT] = {
    "Biquad b0", "Biquad -a1", "Biquad b1", "Biquad -a2", "Biquad b2",
    "Attack time (s)", "Release time (s)", "Slope", "Knee width (dB)",
    "Threshold level (dB)", "Makeup gain (linear)", "Key listen",
    "Input", "Output",
};

#define RANGE(low, high) \
    { LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE, (low), (high) }
#define LOG_RANGE(low, high) \
    { LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE | \
      LADSPA_HINT_LOGARITHMIC, (low), (high) }

static const LADSPA_PortRangeHint port_hints[PORT_COUNT] = {
    RANGE(-8.0f, 8.0f), RANGE(-2.0f, 2.0f), RANGE(-8.0f, 8.0f),
    RANGE(-2.0f, 2.0f), RANGE(-8.0f, 8.0f),
    LOG_RANGE(0.000001f, 10.0f), LOG_RANGE(0.000001f, 20.0f),
    RANGE(0.0f, 1.0f), LOG_RANGE(0.001f, 24.0f), RANGE(-120.0f, 24.0f),
    LOG_RANGE(0.0000001f, 1024.0f),
    { LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE |
      LADSPA_HINT_TOGGLED, 0.0f, 1.0f },
    { 0, 0.0f, 0.0f }, { 0, 0.0f, 0.0f },
};

static const LADSPA_Descriptor descriptor = {
    422024UL,
    "io24_uc_comp",
    LADSPA_PROPERTY_HARD_RT_CAPABLE,
    "io24 UC-derived compressor",
    "UniCont",
    "GPL-3.0-or-later",
    PORT_COUNT,
    port_descriptors,
    port_names,
    port_hints,
    NULL,
    instantiate,
    connect_port,
    activate,
    run,
    NULL,
    NULL,
    NULL,
    cleanup,
};

const LADSPA_Descriptor *ladspa_descriptor(unsigned long index)
{
    return index == 0 ? &descriptor : NULL;
}
