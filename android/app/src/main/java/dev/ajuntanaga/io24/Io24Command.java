package dev.ajuntanaga.io24;

import java.util.Collections;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.Map;

/** Validated command allowlist. UI code cannot name raw wire parameters. */
public final class Io24Command {
    public enum Proof {
        READBACK,
        SENT,
        LOCAL,
        HOST_ONLY
    }

    public enum Kind {
        SET_GAIN,
        SET_PHANTOM,
        SET_HIGH_PASS,
        SET_INPUT_MUTE,
        SET_FX_MIX,
        SET_LINK,
        SET_MUTE_SYNC,
        SET_MAIN_VOLUME,
        SET_HEADPHONE_VOLUME,
        SET_HEADPHONE_MUTE,
        SET_MONITOR_BLEND,
        SET_PHONE_SOURCE,
        SET_PROCESSING_CHANNEL,
        SET_OUTPUT_DELAY,
        SET_OUTPUT_DELAY_BUS,
        SET_SAMPLE_RATE,
        SET_MIXER_SEND,
        SET_MIXER_ASSIGN,
        SET_MIXER_PAN,
        SET_MIXER_MUTE,
        SET_MIXER_SOLO,
        SET_BUS_MASTER,
        SET_BUS_MUTE,
        SET_MIRROR_MAIN,
        SET_PROCESSING_PARAMETER,
        SET_VOICE_FX_MODEL,
        SET_VOICE_FX_ON,
        SET_VOICE_FX_PARAMETER,
        SET_VOICE_FX_INPUT,
        SET_REVERB,
        SET_PRESET_SLOT,
        SET_PRESET_ENABLED,
        SAVE_DEVICE_BLOCK,
        SAVE_LOCAL_SCENE,
        LOAD_LOCAL_SCENE
    }

    private static final class Range {
        final float min;
        final float max;
        final boolean integer;
        final boolean writable;

        Range(float min, float max, boolean integer, boolean writable) {
            this.min = min;
            this.max = max;
            this.integer = integer;
            this.writable = writable;
        }
    }

    private static final EnumMap<Io24State.VoiceFxModel, Map<String, Range>>
            VOICE_FX = buildVoiceFxCatalog();
    private static final Map<String, Range> PROCESSING = buildProcessingCatalog();

    private final Kind kind;
    private final Proof proof;
    private final int channel;
    private final Io24State.Source source;
    private final Io24State.Bus bus;
    private final Io24State.VoiceFxModel model;
    private final String parameter;
    private final float value;
    private final boolean toggle;
    private final Io24State.PhoneSource phoneSource;
    private final Map<String, Float> values;

    private Io24Command(
            Kind kind,
            Proof proof,
            int channel,
            Io24State.Source source,
            Io24State.Bus bus,
            Io24State.VoiceFxModel model,
            String parameter,
            float value,
            boolean toggle,
            Io24State.PhoneSource phoneSource,
            Map<String, Float> values) {
        this.kind = kind;
        this.proof = proof;
        this.channel = channel;
        this.source = source;
        this.bus = bus;
        this.model = model;
        this.parameter = parameter;
        this.value = value;
        this.toggle = toggle;
        this.phoneSource = phoneSource;
        this.values = values == null
                ? Collections.emptyMap()
                : Collections.unmodifiableMap(new LinkedHashMap<>(values));
    }

    public static Io24Command setGain(int channel, float db) {
        requireChannel(channel);
        requireRange("Gain", db, 0.0f, 60.0f);
        return scalar(Kind.SET_GAIN, Proof.READBACK, channel, db);
    }

    public static Io24Command setPhantom(int channel, boolean on) {
        requireChannel(channel);
        return toggle(Kind.SET_PHANTOM, Proof.READBACK, channel, on);
    }

    public static Io24Command setHighPass(int channel, boolean on) {
        requireChannel(channel);
        return toggle(Kind.SET_HIGH_PASS, Proof.SENT, channel, on);
    }

    public static Io24Command setInputMute(int channel, boolean on) {
        requireChannel(channel);
        return toggle(Kind.SET_INPUT_MUTE, Proof.READBACK, channel, on);
    }

    public static Io24Command setFxMix(int channel, float mix) {
        requireChannel(channel);
        requireRange("FX mix", mix, 0.0f, 1.0f);
        return scalar(Kind.SET_FX_MIX, Proof.SENT, channel, mix);
    }

    public static Io24Command setLinked(boolean on) {
        return toggle(Kind.SET_LINK, Proof.SENT, 0, on);
    }

    public static Io24Command setMuteSync(boolean on) {
        return toggle(Kind.SET_MUTE_SYNC, Proof.SENT, 0, on);
    }

    public static Io24Command setMainVolume(float volume) {
        requireRange("Main volume", volume, 0.0f, 1.0f);
        return scalar(Kind.SET_MAIN_VOLUME, Proof.READBACK, 0, volume);
    }

    public static Io24Command setHeadphoneVolume(float volume) {
        requireRange("Headphone volume", volume, 0.0f, 1.0f);
        return scalar(Kind.SET_HEADPHONE_VOLUME, Proof.READBACK, 0, volume);
    }

    public static Io24Command setHeadphoneMute(boolean on) {
        return toggle(Kind.SET_HEADPHONE_MUTE, Proof.SENT, 0, on);
    }

    public static Io24Command setMonitorBlend(float blend) {
        requireRange("Monitor blend", blend, -1.0f, 1.0f);
        return scalar(Kind.SET_MONITOR_BLEND, Proof.READBACK, 0, blend);
    }

    public static Io24Command setPhoneSource(Io24State.PhoneSource source) {
        if (source == null) {
            throw new IllegalArgumentException("Phone source is required");
        }
        return new Io24Command(
                Kind.SET_PHONE_SOURCE,
                Proof.SENT,
                0,
                null,
                null,
                null,
                null,
                0.0f,
                false,
                source,
                null);
    }

    public static Io24Command setProcessingChannel(int channel) {
        requireChannel(channel);
        return scalar(Kind.SET_PROCESSING_CHANNEL, Proof.READBACK, channel,
                channel);
    }

    public static Io24Command setOutputDelay(float seconds) {
        requireRange("Output delay", seconds, 0.0f, 0.5f);
        float stepped = Math.round(seconds / 0.002f) * 0.002f;
        return scalar(Kind.SET_OUTPUT_DELAY, Proof.SENT, 0, stepped);
    }

    public static Io24Command setOutputDelayBus(int bus) {
        if (bus < -1 || bus > 4) {
            throw new IllegalArgumentException("Output delay bus must be -1..4");
        }
        return scalar(Kind.SET_OUTPUT_DELAY_BUS, Proof.SENT, 0, bus);
    }

    public static Io24Command setSampleRate(int sampleRateHz) {
        if (sampleRateHz != 44_100
                && sampleRateHz != 48_000
                && sampleRateHz != 88_200
                && sampleRateHz != 96_000) {
            throw new IllegalArgumentException(
                    "Sample rate must be 44100, 48000, 88200, or 96000 Hz");
        }
        return scalar(Kind.SET_SAMPLE_RATE, Proof.LOCAL, 0, sampleRateHz);
    }

    public static Io24Command setMixerSend(
            Io24State.Source source,
            Io24State.Bus bus,
            float db) {
        requireSourceBus(source, bus);
        requireRange("Mixer send", db, -144.0f, 10.0f);
        return routed(Kind.SET_MIXER_SEND, Proof.SENT, source, bus, db, false);
    }

    public static Io24Command setMixerAssigned(
            Io24State.Source source,
            Io24State.Bus bus,
            boolean on) {
        requireSourceBus(source, bus);
        return routed(Kind.SET_MIXER_ASSIGN, Proof.SENT, source, bus, 0.0f, on);
    }

    public static Io24Command setMixerPan(
            Io24State.Source source,
            Io24State.Bus bus,
            float pan) {
        requireSourceBus(source, bus);
        requireRange("Pan", pan, 0.0f, 1.0f);
        return routed(Kind.SET_MIXER_PAN, Proof.LOCAL, source, bus, pan, false);
    }

    public static Io24Command setMixerMute(
            Io24State.Source source,
            boolean on) {
        if (source == null) {
            throw new IllegalArgumentException("Source is required");
        }
        return new Io24Command(
                Kind.SET_MIXER_MUTE, Proof.SENT, 0, source, null, null,
                null, 0.0f, on, null, null);
    }

    public static Io24Command setMixerSolo(
            Io24State.Source source,
            Io24State.Bus bus,
            boolean on) {
        requireSourceBus(source, bus);
        return routed(Kind.SET_MIXER_SOLO, Proof.SENT, source, bus, 0.0f, on);
    }

    public static Io24Command setBusMaster(Io24State.Bus bus, float db) {
        if (bus == null) {
            throw new IllegalArgumentException("Bus is required");
        }
        requireRange("Bus master", db, -96.0f, 10.0f);
        return routed(Kind.SET_BUS_MASTER, Proof.SENT, null, bus, db, false);
    }

    public static Io24Command setBusMute(Io24State.Bus bus, boolean on) {
        if (bus == null) {
            throw new IllegalArgumentException("Bus is required");
        }
        return routed(Kind.SET_BUS_MUTE, Proof.SENT, null, bus, 0.0f, on);
    }

    public static Io24Command setMirrorMain(Io24State.Bus bus, boolean on) {
        if (bus != Io24State.Bus.MIX_A && bus != Io24State.Bus.MIX_B) {
            throw new IllegalArgumentException("Only Mix A or Mix B can mirror Main");
        }
        return routed(Kind.SET_MIRROR_MAIN, Proof.SENT, null, bus, 0.0f, on);
    }

    public static Io24Command setProcessingParameter(
            int channel,
            String parameter,
            float value) {
        requireChannel(channel);
        if (parameter == null || parameter.isEmpty()) {
            throw new IllegalArgumentException("Processing parameter is required");
        }
        Range range = PROCESSING.get(parameter);
        if (range == null) {
            throw new IllegalArgumentException(
                    "Unknown Fat Channel parameter " + parameter);
        }
        requireRange("Fat Channel " + parameter, value, range.min, range.max);
        if (range.integer && value != Math.round(value)) {
            throw new IllegalArgumentException(
                    "Fat Channel " + parameter + " must be an integer");
        }
        return new Io24Command(
                Kind.SET_PROCESSING_PARAMETER,
                Proof.SENT,
                channel,
                null,
                null,
                null,
                parameter,
                value,
                value != 0.0f,
                null,
                null);
    }

    public static Io24Command setVoiceFxModel(Io24State.VoiceFxModel model) {
        requireModel(model);
        return new Io24Command(
                Kind.SET_VOICE_FX_MODEL,
                Proof.SENT,
                0,
                null,
                null,
                model,
                null,
                0.0f,
                false,
                null,
                null);
    }

    public static Io24Command setVoiceFxOn(
            Io24State.VoiceFxModel model,
            boolean on) {
        requireModel(model);
        return new Io24Command(
                Kind.SET_VOICE_FX_ON,
                Proof.SENT,
                0,
                null,
                null,
                model,
                "on",
                on ? 1.0f : 0.0f,
                on,
                null,
                null);
    }

    public static Io24Command setVoiceFxParameter(
            Io24State.VoiceFxModel model,
            String parameter,
            float value) {
        requireModel(model);
        Map<String, Range> ranges = VOICE_FX.get(model);
        Range range = ranges.get(parameter);
        if (range == null) {
            throw new IllegalArgumentException(
                    "Unknown " + model.label() + " parameter " + parameter);
        }
        if (!range.writable) {
            throw new IllegalArgumentException(
                    model.label() + " " + parameter + " is read-only");
        }
        requireRange(model.label() + " " + parameter, value, range.min, range.max);
        if (range.integer && value != Math.round(value)) {
            throw new IllegalArgumentException(
                    model.label() + " " + parameter + " must be an integer");
        }
        return new Io24Command(
                Kind.SET_VOICE_FX_PARAMETER,
                Proof.SENT,
                0,
                null,
                null,
                model,
                parameter,
                value,
                value != 0.0f,
                null,
                null);
    }

    public static Io24Command setVoiceFxInput(int channel) {
        requireChannel(channel);
        return scalar(Kind.SET_VOICE_FX_INPUT, Proof.READBACK, channel, channel);
    }

    public static Io24Command setReverb(
            boolean on,
            float size,
            float mix,
            float highPassHz,
            float preDelaySeconds) {
        requireRange("Reverb size", size, 0.0f, 1.0f);
        requireRange("Reverb mix", mix, 0.0f, 1.0f);
        requireRange("Reverb high-pass", highPassHz, 0.0f, 500.0f);
        requireRange("Reverb pre-delay", preDelaySeconds, 0.0001f, 0.25f);
        Map<String, Float> values = new LinkedHashMap<>();
        values.put("size", size);
        values.put("mix", mix);
        values.put("high_pass_hz", highPassHz);
        values.put("pre_delay_s", preDelaySeconds);
        return new Io24Command(
                Kind.SET_REVERB,
                Proof.SENT,
                0,
                null,
                null,
                null,
                null,
                0.0f,
                on,
                null,
                values);
    }

    public static Io24Command setPresetSlot(int channel, int slot) {
        requireChannel(channel);
        int first = (channel - 1) * 2;
        if (slot != first && slot != first + 1) {
            throw new IllegalArgumentException(
                    "Preset slot does not belong to Input " + channel);
        }
        return scalar(Kind.SET_PRESET_SLOT, Proof.READBACK, channel, slot);
    }

    public static Io24Command setPresetEnabled(int channel, boolean on) {
        requireChannel(channel);
        return toggle(Kind.SET_PRESET_ENABLED, Proof.SENT, channel, on);
    }

    public static Io24Command saveDeviceBlock(int channel, int block) {
        requireChannel(channel);
        if (block != 0 && block != 1) {
            throw new IllegalArgumentException("Preset block must be 0 or 1");
        }
        return scalar(Kind.SAVE_DEVICE_BLOCK, Proof.SENT, channel, block);
    }

    public Kind kind() {
        return kind;
    }

    public Proof proof() {
        return proof;
    }

    public int channel() {
        return channel;
    }

    public Io24State.Source source() {
        return source;
    }

    public Io24State.Bus bus() {
        return bus;
    }

    public Io24State.VoiceFxModel model() {
        return model;
    }

    public String parameter() {
        return parameter;
    }

    public float value() {
        return value;
    }

    public boolean toggle() {
        return toggle;
    }

    public Io24State.PhoneSource phoneSource() {
        return phoneSource;
    }

    public Map<String, Float> values() {
        return values;
    }

    public boolean canRunNatively(Io24State state) {
        if (state == null) {
            throw new IllegalArgumentException("Current state is required");
        }
        return !(model == Io24State.VoiceFxModel.DELAY
                && (!state.sampleRateConfirmed()
                || state.sampleRateHz() > Io24State.DELAY_NATIVE_MAX_RATE_HZ));
    }

    private static Io24Command scalar(
            Kind kind,
            Proof proof,
            int channel,
            float value) {
        return new Io24Command(
                kind, proof, channel, null, null, null, null, value, false,
                null, null);
    }

    private static Io24Command toggle(
            Kind kind,
            Proof proof,
            int channel,
            boolean value) {
        return new Io24Command(
                kind, proof, channel, null, null, null, null,
                value ? 1.0f : 0.0f, value, null, null);
    }

    private static Io24Command routed(
            Kind kind,
            Proof proof,
            Io24State.Source source,
            Io24State.Bus bus,
            float value,
            boolean toggle) {
        return new Io24Command(
                kind, proof, 0, source, bus, null, null, value, toggle,
                null, null);
    }

    private static void requireChannel(int channel) {
        if (channel != 1 && channel != 2) {
            throw new IllegalArgumentException("Channel must be 1 or 2");
        }
    }

    private static void requireSourceBus(
            Io24State.Source source,
            Io24State.Bus bus) {
        if (source == null || bus == null) {
            throw new IllegalArgumentException("Source and bus are required");
        }
    }

    private static void requireModel(Io24State.VoiceFxModel model) {
        if (model == null) {
            throw new IllegalArgumentException("Voice FX model is required");
        }
    }

    private static void requireRange(
            String label,
            float value,
            float min,
            float max) {
        if (!Float.isFinite(value) || value < min || value > max) {
            throw new IllegalArgumentException(
                    label + " must be " + min + ".." + max);
        }
    }

    private static EnumMap<Io24State.VoiceFxModel, Map<String, Range>>
            buildVoiceFxCatalog() {
        EnumMap<Io24State.VoiceFxModel, Map<String, Range>> result =
                new EnumMap<>(Io24State.VoiceFxModel.class);
        result.put(Io24State.VoiceFxModel.TRANSFORMER,
                ranges("lows", range(0, 1), "width", range(0, 1),
                        "mix", range(0, 1)));
        result.put(Io24State.VoiceFxModel.DETUNER,
                ranges("detune", integer(0, 8), "mix", range(0, 1)));
        result.put(Io24State.VoiceFxModel.VOCODER,
                ranges("vol", range(0, 1), "carrier_type", integer(0, 2),
                        "carrier_freq", range(50, 500),
                        "voiced", readonly(0, 1), "mix", range(0, 1)));
        result.put(Io24State.VoiceFxModel.RING_MOD,
                ranges("carrier_hz", range(0.1f, 2000),
                        "carrier2", integer(0, 1),
                        "carrier2_hz", range(0.1f, 2000),
                        "dist", range(0, 1), "vol", range(0, 1),
                        "mix", range(0, 1)));
        result.put(Io24State.VoiceFxModel.FILTERS,
                ranges("pitch", range(0, 1), "regeneration", range(0, 1),
                        "damping", range(0, 1), "distortion", range(0, 1),
                        "volume", range(0, 1), "mix", range(0, 1)));
        result.put(Io24State.VoiceFxModel.DELAY,
                ranges("time_s", range(0.0001f, 0.25f),
                        "feedback", range(0, 1), "mix", range(0, 1)));
        return result;
    }

    private static Map<String, Range> buildProcessingCatalog() {
        return ranges(
                "hpf_on", integer(0, 1), "hpf_hz", range(24, 1000),
                "gate_on", integer(0, 1),
                "gate_threshold", range(-84, 0),
                "gate_range", range(-84, 0),
                "gate_attack", range(0.00002f, 0.5f),
                "gate_release", range(0.05f, 2.0f),
                "compressor_model", integer(0, 0),
                "compressor_on", integer(0, 1),
                "compressor_threshold", range(-56, 0),
                "compressor_ratio", range(1, 20),
                "compressor_attack", range(0.0002f, 0.15f),
                "compressor_release", range(0.0025f, 0.9f),
                "compressor_gain", range(0, 28),
                "limiter_on", integer(0, 1),
                "limiter_threshold", range(-28, 0),
                "eq_model", integer(0, 0),
                "eq_on", integer(0, 1),
                "eq_low_freq", range(20, 500),
                "eq_low_gain", range(-15, 15),
                "eq_lowmid_freq", range(80, 3000),
                "eq_lowmid_gain", range(-15, 15),
                "eq_himid_freq", range(400, 12000),
                "eq_himid_gain", range(-15, 15),
                "eq_high_freq", range(1000, 20000),
                "eq_high_gain", range(-15, 15),
                "eq_first", integer(0, 1));
    }

    private static Map<String, Range> ranges(Object... entries) {
        Map<String, Range> values = new LinkedHashMap<>();
        for (int index = 0; index < entries.length; index += 2) {
            values.put((String) entries[index], (Range) entries[index + 1]);
        }
        return Collections.unmodifiableMap(values);
    }

    private static Range range(float min, float max) {
        return new Range(min, max, false, true);
    }

    private static Range integer(float min, float max) {
        return new Range(min, max, true, true);
    }

    private static Range readonly(float min, float max) {
        return new Range(min, max, false, false);
    }
}
