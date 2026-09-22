/*
 * io24 Voice FX Delay -- sample-rate-safe mono LADSPA processor.
 *
 * The device implementation cannot safely materialize its rate-scaled Delay
 * histories at 96 kHz.  This Host processor keeps the same public controls,
 * allocates once at instantiation, and performs no allocation in its realtime
 * callback.  It is used only by the Linux Host's per-input insert.
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

#define LADSPA_PORT_INPUT 0x1UL
#define LADSPA_PORT_OUTPUT 0x2UL
#define LADSPA_PORT_CONTROL 0x4UL
#define LADSPA_PORT_AUDIO 0x8UL
#define LADSPA_PROPERTY_HARD_RT_CAPABLE 0x4UL
#define LADSPA_HINT_BOUNDED_BELOW 0x1UL
#define LADSPA_HINT_BOUNDED_ABOVE 0x2UL
#define LADSPA_HINT_TOGGLED 0x4UL
#define LADSPA_HINT_LOGARITHMIC 0x10UL

#define MAX_TIME_S 0.25f

enum {
    P_ON,
    P_TIME,
    P_FEEDBACK,
    P_MIX,
    P_INPUT,
    P_OUTPUT,
    PORT_COUNT
};

typedef struct {
    unsigned long sample_rate;
    unsigned long length;
    unsigned long write_at;
    float *history;
    LADSPA_Data *ports[PORT_COUNT];
} Io24Delay;

static float finite_or(float value, float fallback)
{
    return isfinite(value) ? value : fallback;
}

static float bounded(float value, float low, float high)
{
    return value < low ? low : value > high ? high : value;
}

static int init_delay(Io24Delay *self, unsigned long sample_rate)
{
    if (self == NULL || sample_rate == 0)
        return -1;
    self->sample_rate = sample_rate;
    self->length = (unsigned long)ceil((double)sample_rate * MAX_TIME_S) + 2UL;
    self->history = (float *)calloc(self->length, sizeof(float));
    return self->history == NULL ? -1 : 0;
}

static void reset_delay(Io24Delay *self)
{
    if (self != NULL && self->history != NULL) {
        memset(self->history, 0, self->length * sizeof(*self->history));
        self->write_at = 0;
    }
}

static void process(Io24Delay *self, const float *input, float *output,
                    unsigned long frames, const float *controls)
{
    const int on = finite_or(controls[P_ON], 0.0f) >= 0.5f;
    const float time_s = bounded(finite_or(controls[P_TIME], 0.125f),
                                 0.0001f, MAX_TIME_S);
    /* Unity feedback is intentionally pulled just inside the stable region. */
    const float feedback = bounded(finite_or(controls[P_FEEDBACK], 0.5f),
                                   0.0f, 0.995f);
    const float mix = bounded(finite_or(controls[P_MIX], 0.5f), 0.0f, 1.0f);
    const float delay_f = bounded(time_s * (float)self->sample_rate,
                                  1.0f, (float)(self->length - 2UL));
    const unsigned long delay_i = (unsigned long)floorf(delay_f);
    const float fraction = delay_f - (float)delay_i;
    unsigned long write_at = self->write_at;

    for (unsigned long i = 0; i < frames; ++i) {
        const float dry = finite_or(input[i], 0.0f);
        const unsigned long newer =
            (write_at + self->length - delay_i) % self->length;
        const unsigned long older =
            (newer + self->length - 1UL) % self->length;
        const float wet = self->history[newer] * (1.0f - fraction) +
                          self->history[older] * fraction;
        self->history[write_at] = dry + (on ? wet * feedback : 0.0f);
        output[i] = on ? dry * (1.0f - mix) + wet * mix : dry;
        if (++write_at == self->length)
            write_at = 0;
    }
    self->write_at = write_at;
}

static LADSPA_Handle instantiate(const LADSPA_Descriptor *descriptor,
                                 unsigned long sample_rate)
{
    (void)descriptor;
    Io24Delay *self = (Io24Delay *)calloc(1, sizeof(*self));
    if (self == NULL || init_delay(self, sample_rate) != 0) {
        if (self != NULL)
            free(self->history);
        free(self);
        return NULL;
    }
    return (LADSPA_Handle)self;
}

static void connect_port(LADSPA_Handle instance, unsigned long port,
                         LADSPA_Data *data)
{
    Io24Delay *self = (Io24Delay *)instance;
    if (self != NULL && port < PORT_COUNT)
        self->ports[port] = data;
}

static void activate(LADSPA_Handle instance)
{
    reset_delay((Io24Delay *)instance);
}

static void run(LADSPA_Handle instance, unsigned long frames)
{
    Io24Delay *self = (Io24Delay *)instance;
    if (self == NULL || self->ports[P_INPUT] == NULL ||
            self->ports[P_OUTPUT] == NULL)
        return;
    float controls[4];
    for (unsigned long i = 0; i < 4UL; ++i)
        controls[i] = self->ports[i] != NULL ? *self->ports[i] : 0.0f;
    process(self, self->ports[P_INPUT], self->ports[P_OUTPUT], frames, controls);
}

static void cleanup(LADSPA_Handle instance)
{
    Io24Delay *self = (Io24Delay *)instance;
    if (self != NULL)
        free(self->history);
    free(self);
}

/* Deterministic hardware-free test entry point. */
int io24_voicefx_delay_process(const float *input, float *output,
                               unsigned long frames,
                               unsigned long sample_rate,
                               const float *controls)
{
    if (input == NULL || output == NULL || controls == NULL || sample_rate == 0)
        return -1;
    Io24Delay self;
    memset(&self, 0, sizeof(self));
    if (init_delay(&self, sample_rate) != 0)
        return -1;
    process(&self, input, output, frames, controls);
    free(self.history);
    return 0;
}

static const LADSPA_PortDescriptor port_descriptors[PORT_COUNT] = {
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_CONTROL,
    LADSPA_PORT_INPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_OUTPUT | LADSPA_PORT_AUDIO,
};

static const char *const port_names[PORT_COUNT] = {
    "On", "Time (s)", "Feedback", "WetDry", "Input", "Output",
};

#define RANGE(low, high) \
    { LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE, (low), (high) }

static const LADSPA_PortRangeHint port_hints[PORT_COUNT] = {
    { LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE |
      LADSPA_HINT_TOGGLED, 0.0f, 1.0f },
    { LADSPA_HINT_BOUNDED_BELOW | LADSPA_HINT_BOUNDED_ABOVE |
      LADSPA_HINT_LOGARITHMIC, 0.0001f, MAX_TIME_S },
    RANGE(0.0f, 1.0f), RANGE(0.0f, 1.0f),
    { 0, 0.0f, 0.0f }, { 0, 0.0f, 0.0f },
};

static const LADSPA_Descriptor descriptor = {
    422026UL,
    "io24_voicefx_delay",
    LADSPA_PROPERTY_HARD_RT_CAPABLE,
    "io24 Voice FX Delay",
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
