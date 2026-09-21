/*
 * io24 Host spring reverb -- wet-only stereo LADSPA processor.
 *
 * The tank is intentionally algorithmic rather than an IR dressed up as a
 * spring: short dispersive all-pass sections feed two decorrelated banks of
 * damped resonators.  Dwell controls feedback, Tone the loss filter, Drip the
 * transient/dispersion emphasis, and Width the final mid/side spread.
 */

#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef float LADSPA_Data;
typedef void *LADSPA_Handle;
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

#define LADSPA_PORT_INPUT 0x1
#define LADSPA_PORT_OUTPUT 0x2
#define LADSPA_PORT_CONTROL 0x4
#define LADSPA_PORT_AUDIO 0x8
#define LADSPA_PROPERTY_HARD_RT_CAPABLE 0x4
#define LADSPA_HINT_BOUNDED_BELOW 0x1
#define LADSPA_HINT_BOUNDED_ABOVE 0x2
#define LADSPA_HINT_LOGARITHMIC 0x10

enum {
    P_INPUT1_GAIN,
    P_INPUT2_GAIN,
    P_DWELL,
    P_TONE,
    P_DRIP,
    P_WIDTH,
    P_PREDELAY,
    P_OUTPUT_GAIN,
    P_INPUT1,
    P_INPUT2,
    P_OUTPUT_L,
    P_OUTPUT_R,
    PORT_COUNT
};

enum { CONTROL_COUNT = P_OUTPUT_GAIN + 1 };
enum { ALLPASS_COUNT = 4, RESONATOR_COUNT = 4 };

typedef struct {
    float *samples;
    unsigned long size;
    unsigned long pos;
} Delay;

typedef struct {
    Delay delay;
    float loss;
} Resonator;

typedef struct {
    unsigned long sample_rate;
    LADSPA_Data *ports[PORT_COUNT];
    Delay predelay;
    Delay allpass_l[ALLPASS_COUNT];
    Delay allpass_r[ALLPASS_COUNT];
    Resonator resonator_l[RESONATOR_COUNT];
    Resonator resonator_r[RESONATOR_COUNT];
    float input_previous;
    float highpass_previous;
    float highpass_input_previous;
} Io24Spring;

static float finite_or(float value, float fallback)
{
    return isfinite(value) ? value : fallback;
}

static float bounded(float value, float low, float high)
{
    return value < low ? low : value > high ? high : value;
}

static int delay_init(Delay *delay, unsigned long size)
{
    delay->size = size > 1 ? size : 2;
    delay->pos = 0;
    delay->samples = (float *)calloc(delay->size, sizeof(float));
    return delay->samples != NULL;
}

static void delay_clear(Delay *delay)
{
    if (delay->samples != NULL)
        memset(delay->samples, 0, delay->size * sizeof(float));
    delay->pos = 0;
}

static void delay_free(Delay *delay)
{
    free(delay->samples);
    delay->samples = NULL;
    delay->size = 0;
    delay->pos = 0;
}

static unsigned long millis_samples(unsigned long sample_rate, float millis)
{
    unsigned long result = (unsigned long)(millis * 0.001f *
                                            (float)sample_rate + 0.5f);
    return result > 1 ? result : 2;
}

static void free_state(Io24Spring *self)
{
    delay_free(&self->predelay);
    for (int i = 0; i < ALLPASS_COUNT; ++i) {
        delay_free(&self->allpass_l[i]);
        delay_free(&self->allpass_r[i]);
    }
    for (int i = 0; i < RESONATOR_COUNT; ++i) {
        delay_free(&self->resonator_l[i].delay);
        delay_free(&self->resonator_r[i].delay);
    }
}

static int initialise_state(Io24Spring *self, unsigned long sample_rate)
{
    static const float allpass_l_ms[ALLPASS_COUNT] = {
        3.10f, 4.73f, 6.37f, 8.91f
    };
    static const float allpass_r_ms[ALLPASS_COUNT] = {
        3.67f, 5.29f, 7.13f, 9.79f
    };
    static const float resonator_l_ms[RESONATOR_COUNT] = {
        29.71f, 34.93f, 39.89f, 44.53f
    };
    static const float resonator_r_ms[RESONATOR_COUNT] = {
        31.13f, 36.71f, 41.59f, 46.31f
    };

    memset(self, 0, sizeof(*self));
    self->sample_rate = sample_rate;
    if (!delay_init(&self->predelay,
                    (unsigned long)(0.1f * (float)sample_rate) + 2))
        goto fail;
    for (int i = 0; i < ALLPASS_COUNT; ++i) {
        if (!delay_init(&self->allpass_l[i],
                        millis_samples(sample_rate, allpass_l_ms[i])) ||
                !delay_init(&self->allpass_r[i],
                            millis_samples(sample_rate, allpass_r_ms[i])))
            goto fail;
    }
    for (int i = 0; i < RESONATOR_COUNT; ++i) {
        if (!delay_init(&self->resonator_l[i].delay,
                        millis_samples(sample_rate, resonator_l_ms[i])) ||
                !delay_init(&self->resonator_r[i].delay,
                            millis_samples(sample_rate, resonator_r_ms[i])))
            goto fail;
    }
    return 1;

fail:
    free_state(self);
    return 0;
}

static void reset_state(Io24Spring *self)
{
    delay_clear(&self->predelay);
    for (int i = 0; i < ALLPASS_COUNT; ++i) {
        delay_clear(&self->allpass_l[i]);
        delay_clear(&self->allpass_r[i]);
    }
    for (int i = 0; i < RESONATOR_COUNT; ++i) {
        delay_clear(&self->resonator_l[i].delay);
        delay_clear(&self->resonator_r[i].delay);
        self->resonator_l[i].loss = 0.0f;
        self->resonator_r[i].loss = 0.0f;
    }
    self->input_previous = 0.0f;
    self->highpass_previous = 0.0f;
    self->highpass_input_previous = 0.0f;
}

static float predelay_process(Delay *delay, float input,
                              unsigned long delay_samples)
{
    if (delay_samples >= delay->size)
        delay_samples = delay->size - 1;
    delay->samples[delay->pos] = input;
    const unsigned long read = (delay->pos + delay->size - delay_samples) %
                               delay->size;
    const float output = delay->samples[read];
    delay->pos = (delay->pos + 1) % delay->size;
    return output;
}

static float allpass_process(Delay *delay, float input, float feedback)
{
    const float delayed = delay->samples[delay->pos];
    const float output = delayed - feedback * input;
    delay->samples[delay->pos] = input + feedback * delayed;
    delay->pos = (delay->pos + 1) % delay->size;
    return output;
}

static float resonator_process(Resonator *resonator, float input,
                               float feedback, float tone_take)
{
    Delay *delay = &resonator->delay;
    const float output = delay->samples[delay->pos];
    resonator->loss += tone_take * (output - resonator->loss);
    delay->samples[delay->pos] = input + feedback * resonator->loss;
    delay->pos = (delay->pos + 1) % delay->size;
    return output;
}

static void process(Io24Spring *self, const float *input1, const float *input2,
                    float *output_l, float *output_r, unsigned long frames,
                    const float *controls)
{
    const float gain1 = bounded(finite_or(controls[P_INPUT1_GAIN], 0.5f),
                                0.0f, 1.0f);
    const float gain2 = bounded(finite_or(controls[P_INPUT2_GAIN], 0.5f),
                                0.0f, 1.0f);
    const float dwell = bounded(finite_or(controls[P_DWELL], 0.64f), 0.0f, 1.0f);
    const float tone = bounded(finite_or(controls[P_TONE], 0.55f), 0.0f, 1.0f);
    const float drip = bounded(finite_or(controls[P_DRIP], 0.42f), 0.0f, 1.0f);
    const float width = bounded(finite_or(controls[P_WIDTH], 0.82f), 0.0f, 1.0f);
    const float predelay_s = bounded(
        finite_or(controls[P_PREDELAY], 0.008f), 0.0f, 0.1f);
    const float output_db = bounded(
        finite_or(controls[P_OUTPUT_GAIN], -12.0f), -60.0f, 10.0f);
    const float output_gain = powf(10.0f, output_db / 20.0f);
    const unsigned long predelay_samples = (unsigned long)(
        predelay_s * (float)self->sample_rate + 0.5f);
    /* A spring's useful decay is measured in seconds, not a few echoes.  The
     * range stays below unity at maximum Dwell but gives the default tank a
     * clearly sustained tail after the initial drip. */
    const float feedback = bounded(0.845f + 0.15f * dwell, 0.0f, 0.992f);
    const float dispersion = 0.42f + 0.40f * drip;
    const float tone_take = 0.025f + 0.40f * tone;
    float input_previous = self->input_previous;
    float hp_previous = self->highpass_previous;
    float hp_input_previous = self->highpass_input_previous;

    for (unsigned long frame = 0; frame < frames; ++frame) {
        float input = finite_or(input1[frame], 0.0f) * gain1 +
                      finite_or(input2[frame], 0.0f) * gain2;

        /* Fixed low cut keeps rumble from pumping the tank.  The derivative
         * term gives Drip the sharp, splashy excitation of a struck spring. */
        const float highpass = input - hp_input_previous + 0.988f * hp_previous;
        hp_input_previous = input;
        hp_previous = highpass;
        float excitation = highpass + drip * 5.0f * (highpass - input_previous);
        input_previous = highpass;
        excitation = tanhf(excitation * (1.0f + 1.4f * drip));
        excitation = predelay_process(&self->predelay, excitation,
                                      predelay_samples);

        float dispersed_l = excitation;
        float dispersed_r = excitation;
        for (int i = 0; i < ALLPASS_COUNT; ++i) {
            dispersed_l = allpass_process(&self->allpass_l[i], dispersed_l,
                                          dispersion);
            dispersed_r = allpass_process(&self->allpass_r[i], dispersed_r,
                                          dispersion * 0.97f);
        }

        float wet_l = 0.0f;
        float wet_r = 0.0f;
        for (int i = 0; i < RESONATOR_COUNT; ++i) {
            const float sign = (i & 1) ? -1.0f : 1.0f;
            wet_l += sign * resonator_process(
                &self->resonator_l[i], dispersed_l + 0.11f * dispersed_r,
                feedback - 0.006f * (float)i, tone_take);
            wet_r += sign * resonator_process(
                &self->resonator_r[i], dispersed_r + 0.11f * dispersed_l,
                feedback - 0.007f * (float)i, tone_take * 0.985f);
        }
        wet_l *= 0.19f;
        wet_r *= 0.19f;
        const float mid = 0.5f * (wet_l + wet_r);
        const float side = 0.5f * (wet_l - wet_r) * width;
        output_l[frame] = tanhf(mid + side) * output_gain;
        output_r[frame] = tanhf(mid - side) * output_gain;
    }

    self->input_previous = input_previous;
    self->highpass_previous = hp_previous;
    self->highpass_input_previous = hp_input_previous;
}

static LADSPA_Handle instantiate(const LADSPA_Descriptor *descriptor,
                                 unsigned long sample_rate)
{
    (void)descriptor;
    Io24Spring *self = (Io24Spring *)calloc(1, sizeof(*self));
    if (self != NULL && !initialise_state(self, sample_rate)) {
        free(self);
        self = NULL;
    }
    return (LADSPA_Handle)self;
}

static void connect_port(LADSPA_Handle instance, unsigned long port,
                         LADSPA_Data *data)
{
    Io24Spring *self = (Io24Spring *)instance;
    if (self != NULL && port < PORT_COUNT)
        self->ports[port] = data;
}

static void activate(LADSPA_Handle instance)
{
    if (instance != NULL)
        reset_state((Io24Spring *)instance);
}

static void run(LADSPA_Handle instance, unsigned long frames)
{
    Io24Spring *self = (Io24Spring *)instance;
    if (self == NULL || self->ports[P_INPUT1] == NULL ||
            self->ports[P_INPUT2] == NULL || self->ports[P_OUTPUT_L] == NULL ||
            self->ports[P_OUTPUT_R] == NULL)
        return;
    float controls[CONTROL_COUNT];
    for (unsigned long i = 0; i < CONTROL_COUNT; ++i)
        controls[i] = self->ports[i] != NULL ? *self->ports[i] : 0.0f;
    process(self, self->ports[P_INPUT1], self->ports[P_INPUT2],
            self->ports[P_OUTPUT_L], self->ports[P_OUTPUT_R], frames, controls);
}

static void cleanup(LADSPA_Handle instance)
{
    Io24Spring *self = (Io24Spring *)instance;
    if (self != NULL) {
        free_state(self);
        free(self);
    }
}

/* Stateless entry point used by deterministic hardware-free tests. */
int io24_spring_process(const float *input1, const float *input2,
                        float *output_l, float *output_r,
                        unsigned long frames, unsigned long sample_rate,
                        const float *controls)
{
    if (input1 == NULL || input2 == NULL || output_l == NULL ||
            output_r == NULL || controls == NULL || sample_rate == 0)
        return -1;
    Io24Spring self;
    if (!initialise_state(&self, sample_rate))
        return -2;
    process(&self, input1, input2, output_l, output_r, frames, controls);
    free_state(&self);
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
    LADSPA_PORT_INPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_INPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_OUTPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_OUTPUT | LADSPA_PORT_AUDIO,
};

static const char *const port_names[PORT_COUNT] = {
    "Input 1 gain", "Input 2 gain", "Dwell", "Tone", "Drip", "Width",
    "Pre-delay (s)", "Output gain (dB)",
    "Input 1", "Input 2", "Output L", "Output R",
};

#define RANGE(low, high) \
    { LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE, (low), (high) }

static const LADSPA_PortRangeHint port_hints[PORT_COUNT] = {
    RANGE(0.001f, 1.0f), RANGE(0.001f, 1.0f),
    RANGE(0.0f, 1.0f), RANGE(0.0f, 1.0f), RANGE(0.0f, 1.0f),
    RANGE(0.0f, 1.0f), RANGE(0.0f, 0.1f), RANGE(-60.0f, 10.0f),
    { 0, 0.0f, 0.0f }, { 0, 0.0f, 0.0f },
    { 0, 0.0f, 0.0f }, { 0, 0.0f, 0.0f },
};

static const LADSPA_Descriptor descriptor = {
    422025UL,
    "io24_spring",
    LADSPA_PROPERTY_HARD_RT_CAPABLE,
    "io24 Host spring reverb",
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
