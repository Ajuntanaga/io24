package dev.ajuntanaga.io24;

import java.util.Collections;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.Map;

/** Immutable application state shared by the physical and simulated sessions. */
public final class Io24State {
    static final int DELAY_NATIVE_MAX_RATE_HZ = 48_000;

    public enum ConnectionStatus {
        DISCONNECTED,
        CONNECTING,
        CONNECTED,
        ERROR
    }

    public enum Bus {
        MAIN("Main"),
        MIX_A("Mix A"),
        MIX_B("Mix B");

        private final String label;

        Bus(String label) {
            this.label = label;
        }

        public String label() {
            return label;
        }
    }

    public enum Source {
        INPUT_1("Input 1"),
        INPUT_2("Input 2"),
        PLAYBACK_1_2("Playback 1–2"),
        PLAYBACK_3_4("Playback 3–4"),
        PLAYBACK_5_6("Playback 5–6"),
        FX_RETURN("FX Return");

        private final String label;

        Source(String label) {
            this.label = label;
        }

        public String label() {
            return label;
        }
    }

    public enum VoiceFxModel {
        TRANSFORMER("Transformer"),
        DETUNER("De-Tuner"),
        VOCODER("Vocoder"),
        RING_MOD("Ring Modulator"),
        FILTERS("Filters"),
        DELAY("Delay");

        private final String label;

        VoiceFxModel(String label) {
            this.label = label;
        }

        public String label() {
            return label;
        }
    }

    public enum PhoneSource {
        MAIN("Main"),
        MIX_A("Mix A"),
        MIX_B("Mix B");

        private final String label;

        PhoneSource(String label) {
            this.label = label;
        }

        public String label() {
            return label;
        }
    }

    public static final class Input {
        private final float gainDb;
        private final boolean phantom;
        private final boolean highPass;
        private final boolean muted;
        private final float level;
        private final float fxMix;
        private final int presetSlot;

        private Input(
                float gainDb,
                boolean phantom,
                boolean highPass,
                boolean muted,
                float level,
                float fxMix,
                int presetSlot) {
            this.gainDb = gainDb;
            this.phantom = phantom;
            this.highPass = highPass;
            this.muted = muted;
            this.level = level;
            this.fxMix = fxMix;
            this.presetSlot = presetSlot;
        }

        public float gainDb() {
            return gainDb;
        }

        public boolean phantom() {
            return phantom;
        }

        public boolean highPass() {
            return highPass;
        }

        public boolean muted() {
            return muted;
        }

        public float level() {
            return level;
        }

        public float fxMix() {
            return fxMix;
        }

        public int presetSlot() {
            return presetSlot;
        }
    }

    public static final class Send {
        private final float db;
        private final boolean assigned;
        private final float pan;
        private final boolean muted;
        private final boolean soloed;

        private Send(
                float db,
                boolean assigned,
                float pan,
                boolean muted,
                boolean soloed) {
            this.db = db;
            this.assigned = assigned;
            this.pan = pan;
            this.muted = muted;
            this.soloed = soloed;
        }

        public float db() {
            return db;
        }

        public boolean assigned() {
            return assigned;
        }

        public float pan() {
            return pan;
        }

        public boolean muted() {
            return muted;
        }

        public boolean soloed() {
            return soloed;
        }
    }

    public static final class BusState {
        private final float masterDb;
        private final boolean muted;
        private final boolean mirrorsMain;

        private BusState(float masterDb, boolean muted, boolean mirrorsMain) {
            this.masterDb = masterDb;
            this.muted = muted;
            this.mirrorsMain = mirrorsMain;
        }

        public float masterDb() {
            return masterDb;
        }

        public boolean muted() {
            return muted;
        }

        public boolean mirrorsMain() {
            return mirrorsMain;
        }
    }

    public static final class VoiceFxState {
        private final boolean on;
        private final Map<String, Float> parameters;

        private VoiceFxState(boolean on, Map<String, Float> parameters) {
            this.on = on;
            this.parameters = Collections.unmodifiableMap(
                    new LinkedHashMap<>(parameters));
        }

        public boolean on() {
            return on;
        }

        public float parameter(String name) {
            Float value = parameters.get(name);
            if (value == null) {
                throw new IllegalArgumentException(
                        "Unknown parameter " + name);
            }
            return value;
        }

        public Map<String, Float> parameters() {
            return parameters;
        }
    }

    public static final class ReverbState {
        private final boolean on;
        private final float size;
        private final float mix;
        private final float highPassHz;
        private final float preDelaySeconds;

        private ReverbState(
                boolean on,
                float size,
                float mix,
                float highPassHz,
                float preDelaySeconds) {
            this.on = on;
            this.size = size;
            this.mix = mix;
            this.highPassHz = highPassHz;
            this.preDelaySeconds = preDelaySeconds;
        }

        public boolean on() {
            return on;
        }

        public float size() {
            return size;
        }

        public float mix() {
            return mix;
        }

        public float highPassHz() {
            return highPassHz;
        }

        public float preDelaySeconds() {
            return preDelaySeconds;
        }
    }

    private final ConnectionStatus connectionStatus;
    private final String statusMessage;
    private final boolean simulated;
    private final boolean busy;
    private final Input[] inputs;
    private final EnumMap<Bus, BusState> buses;
    private final EnumMap<Source, EnumMap<Bus, Send>> sends;
    private final EnumMap<VoiceFxModel, VoiceFxState> voiceFx;
    private final Map<String, Float>[] processing;
    private final VoiceFxModel selectedVoiceFx;
    private final int voiceFxInput;
    private final ReverbState reverb;
    private final boolean linked;
    private final float mainVolume;
    private final float headphoneVolume;
    private final boolean headphoneMuted;
    private final float monitorBlend;
    private final PhoneSource phoneSource;
    private final int sampleRateHz;
    private final boolean sampleRateConfirmed;
    private final float outputDelaySeconds;
    private final int protocolVersion;
    private final int maxCommandLength;
    private final int maxResponseLength;
    private final int stateSlotCount;
    private final String lastProof;

    @SuppressWarnings("unchecked")
    private Io24State(Builder builder) {
        connectionStatus = builder.connectionStatus;
        statusMessage = builder.statusMessage;
        simulated = builder.simulated;
        busy = builder.busy;
        inputs = new Input[] {builder.inputs[0], builder.inputs[1]};
        buses = new EnumMap<>(builder.buses);
        sends = new EnumMap<>(Source.class);
        for (Map.Entry<Source, EnumMap<Bus, Send>> entry
                : builder.sends.entrySet()) {
            sends.put(entry.getKey(), new EnumMap<>(entry.getValue()));
        }
        voiceFx = new EnumMap<>(builder.voiceFx);
        processing = new Map[] {
                Collections.unmodifiableMap(
                        new LinkedHashMap<>(builder.processing[0])),
                Collections.unmodifiableMap(
                        new LinkedHashMap<>(builder.processing[1]))
        };
        selectedVoiceFx = builder.selectedVoiceFx;
        voiceFxInput = builder.voiceFxInput;
        reverb = builder.reverb;
        linked = builder.linked;
        mainVolume = builder.mainVolume;
        headphoneVolume = builder.headphoneVolume;
        headphoneMuted = builder.headphoneMuted;
        monitorBlend = builder.monitorBlend;
        phoneSource = builder.phoneSource;
        sampleRateHz = builder.sampleRateHz;
        sampleRateConfirmed = builder.sampleRateConfirmed;
        outputDelaySeconds = builder.outputDelaySeconds;
        protocolVersion = builder.protocolVersion;
        maxCommandLength = builder.maxCommandLength;
        maxResponseLength = builder.maxResponseLength;
        stateSlotCount = builder.stateSlotCount;
        lastProof = builder.lastProof;
    }

    public static Io24State defaults() {
        return new Builder().build();
    }

    public Builder buildUpon() {
        return new Builder(this);
    }

    public ConnectionStatus connectionStatus() {
        return connectionStatus;
    }

    public String statusMessage() {
        return statusMessage;
    }

    public boolean simulated() {
        return simulated;
    }

    public boolean busy() {
        return busy;
    }

    public Input input(int channel) {
        requireChannel(channel);
        return inputs[channel - 1];
    }

    public BusState bus(Bus bus) {
        return buses.get(requireNonNull(bus, "Bus"));
    }

    public Send send(Source source, Bus bus) {
        return sends.get(requireNonNull(source, "Source"))
                .get(requireNonNull(bus, "Bus"));
    }

    public VoiceFxState voiceFx(VoiceFxModel model) {
        return voiceFx.get(requireNonNull(model, "Voice FX model"));
    }

    public Map<String, Float> processing(int channel) {
        requireChannel(channel);
        return processing[channel - 1];
    }

    public VoiceFxModel selectedVoiceFx() {
        return selectedVoiceFx;
    }

    public int voiceFxInput() {
        return voiceFxInput;
    }

    public ReverbState reverb() {
        return reverb;
    }

    public boolean linked() {
        return linked;
    }

    public float mainVolume() {
        return mainVolume;
    }

    public float headphoneVolume() {
        return headphoneVolume;
    }

    public boolean headphoneMuted() {
        return headphoneMuted;
    }

    public float monitorBlend() {
        return monitorBlend;
    }

    public PhoneSource phoneSource() {
        return phoneSource;
    }

    public int sampleRateHz() {
        return sampleRateHz;
    }

    public boolean sampleRateConfirmed() {
        return sampleRateConfirmed;
    }

    public float outputDelaySeconds() {
        return outputDelaySeconds;
    }

    public int protocolVersion() {
        return protocolVersion;
    }

    public int maxCommandLength() {
        return maxCommandLength;
    }

    public int maxResponseLength() {
        return maxResponseLength;
    }

    public int stateSlotCount() {
        return stateSlotCount;
    }

    public String lastProof() {
        return lastProof;
    }

    public static final class Builder {
        private ConnectionStatus connectionStatus = ConnectionStatus.DISCONNECTED;
        private String statusMessage = "Connect the Revelator io24";
        private boolean simulated;
        private boolean busy;
        private final Input[] inputs = {
                new Input(0.0f, false, false, false, 0.0f, 1.0f, 0),
                new Input(0.0f, false, false, false, 0.0f, 1.0f, 2)
        };
        private final EnumMap<Bus, BusState> buses = new EnumMap<>(Bus.class);
        private final EnumMap<Source, EnumMap<Bus, Send>> sends =
                new EnumMap<>(Source.class);
        private final EnumMap<VoiceFxModel, VoiceFxState> voiceFx =
                new EnumMap<>(VoiceFxModel.class);
        @SuppressWarnings("unchecked")
        private final Map<String, Float>[] processing = new Map[] {
                new LinkedHashMap<String, Float>(),
                new LinkedHashMap<String, Float>()
        };
        private VoiceFxModel selectedVoiceFx = VoiceFxModel.TRANSFORMER;
        private int voiceFxInput = 1;
        private ReverbState reverb =
                new ReverbState(false, 0.5f, 0.3f, 200.0f, 0.02f);
        private boolean linked;
        private float mainVolume = 0.75f;
        private float headphoneVolume = 0.75f;
        private boolean headphoneMuted;
        private float monitorBlend;
        private PhoneSource phoneSource = PhoneSource.MAIN;
        private int sampleRateHz = 48_000;
        private boolean sampleRateConfirmed;
        private float outputDelaySeconds;
        private int protocolVersion;
        private int maxCommandLength;
        private int maxResponseLength;
        private int stateSlotCount;
        private String lastProof = "Not connected";

        public Builder() {
            for (Bus bus : Bus.values()) {
                buses.put(bus, new BusState(0.0f, false, false));
            }
            for (Source source : Source.values()) {
                EnumMap<Bus, Send> byBus = new EnumMap<>(Bus.class);
                for (Bus bus : Bus.values()) {
                    byBus.put(bus, new Send(0.0f, true, 0.5f, false, false));
                }
                sends.put(source, byBus);
            }
            voiceFx.put(VoiceFxModel.TRANSFORMER,
                    effect(false, "lows", 0.5f, "width", 0.5f, "mix", 0.5f));
            voiceFx.put(VoiceFxModel.DETUNER,
                    effect(false, "detune", 4.0f, "mix", 0.5f));
            voiceFx.put(VoiceFxModel.VOCODER,
                    effect(false, "vol", 1.0f, "carrier_type", 1.0f,
                            "carrier_freq", 80.0f, "voiced", 0.0f,
                            "mix", 0.5f));
            voiceFx.put(VoiceFxModel.RING_MOD,
                    effect(false, "carrier_hz", 30.0f, "carrier2", 0.0f,
                            "carrier2_hz", 50.0f, "dist", 0.5f,
                            "vol", 1.0f, "mix", 0.5f));
            voiceFx.put(VoiceFxModel.FILTERS,
                    effect(false, "pitch", 0.5f, "regeneration", 0.5f,
                            "damping", 0.5f, "distortion", 0.5f,
                            "volume", 1.0f, "mix", 0.5f));
            voiceFx.put(VoiceFxModel.DELAY,
                    effect(false, "time_s", 0.125f, "feedback", 0.5f,
                            "mix", 0.5f));
            seedProcessing(processing[0]);
            seedProcessing(processing[1]);
        }

        private Builder(Io24State state) {
            connectionStatus = state.connectionStatus;
            statusMessage = state.statusMessage;
            simulated = state.simulated;
            busy = state.busy;
            inputs[0] = state.inputs[0];
            inputs[1] = state.inputs[1];
            buses.putAll(state.buses);
            for (Map.Entry<Source, EnumMap<Bus, Send>> entry
                    : state.sends.entrySet()) {
                sends.put(entry.getKey(), new EnumMap<>(entry.getValue()));
            }
            voiceFx.putAll(state.voiceFx);
            processing[0].putAll(state.processing[0]);
            processing[1].putAll(state.processing[1]);
            selectedVoiceFx = state.selectedVoiceFx;
            voiceFxInput = state.voiceFxInput;
            reverb = state.reverb;
            linked = state.linked;
            mainVolume = state.mainVolume;
            headphoneVolume = state.headphoneVolume;
            headphoneMuted = state.headphoneMuted;
            monitorBlend = state.monitorBlend;
            phoneSource = state.phoneSource;
            sampleRateHz = state.sampleRateHz;
            sampleRateConfirmed = state.sampleRateConfirmed;
            outputDelaySeconds = state.outputDelaySeconds;
            protocolVersion = state.protocolVersion;
            maxCommandLength = state.maxCommandLength;
            maxResponseLength = state.maxResponseLength;
            stateSlotCount = state.stateSlotCount;
            lastProof = state.lastProof;
        }

        public Builder setConnection(
                ConnectionStatus status,
                String message,
                boolean isSimulated) {
            connectionStatus = requireNonNull(status, "Connection status");
            statusMessage = message == null ? "" : message;
            simulated = isSimulated;
            return this;
        }

        public Builder setProtocolInfo(
                int version,
                int commandLength,
                int responseLength,
                int slotCount) {
            protocolVersion = version;
            maxCommandLength = commandLength;
            maxResponseLength = responseLength;
            stateSlotCount = slotCount;
            return this;
        }

        public Builder setBusy(boolean value) {
            busy = value;
            return this;
        }

        public Builder setInputGain(int channel, float db) {
            return replaceInput(channel, db, null, null, null, null, null, null);
        }

        public Builder setInputPhantom(int channel, boolean on) {
            return replaceInput(channel, null, on, null, null, null, null, null);
        }

        public Builder setInputHighPass(int channel, boolean on) {
            return replaceInput(channel, null, null, on, null, null, null, null);
        }

        public Builder setInputMute(int channel, boolean on) {
            return replaceInput(channel, null, null, null, on, null, null, null);
        }

        public Builder setInputLevel(int channel, float level) {
            return replaceInput(channel, null, null, null, null, level, null, null);
        }

        public Builder setInputFxMix(int channel, float mix) {
            return replaceInput(channel, null, null, null, null, null, mix, null);
        }

        public Builder setInputPresetSlot(int channel, int slot) {
            return replaceInput(channel, null, null, null, null, null, null, slot);
        }

        private Builder replaceInput(
                int channel,
                Float gain,
                Boolean phantom,
                Boolean highPass,
                Boolean muted,
                Float level,
                Float fxMix,
                Integer slot) {
            requireChannel(channel);
            Input old = inputs[channel - 1];
            inputs[channel - 1] = new Input(
                    gain == null ? old.gainDb : gain,
                    phantom == null ? old.phantom : phantom,
                    highPass == null ? old.highPass : highPass,
                    muted == null ? old.muted : muted,
                    level == null ? old.level : level,
                    fxMix == null ? old.fxMix : fxMix,
                    slot == null ? old.presetSlot : slot);
            return this;
        }

        public Builder setMixerSend(
                Source source,
                Bus bus,
                float db,
                boolean assigned,
                float pan) {
            Source checkedSource = requireNonNull(source, "Source");
            Bus checkedBus = requireNonNull(bus, "Bus");
            Send old = sends.get(checkedSource).get(checkedBus);
            sends.get(checkedSource).put(
                    checkedBus,
                    new Send(db, assigned, pan, old.muted, old.soloed));
            return this;
        }

        public Builder setMixerFlags(
                Source source,
                Bus bus,
                boolean muted,
                boolean soloed) {
            Source checkedSource = requireNonNull(source, "Source");
            Bus checkedBus = requireNonNull(bus, "Bus");
            Send old = sends.get(checkedSource).get(checkedBus);
            sends.get(checkedSource).put(
                    checkedBus,
                    new Send(old.db, old.assigned, old.pan, muted, soloed));
            return this;
        }

        public Builder setBus(
                Bus bus,
                float masterDb,
                boolean muted,
                boolean mirrorsMain) {
            buses.put(requireNonNull(bus, "Bus"),
                    new BusState(masterDb, muted, mirrorsMain));
            return this;
        }

        public Builder setVoiceFxOn(VoiceFxModel model, boolean on) {
            VoiceFxModel checked = requireNonNull(model, "Voice FX model");
            if (on) {
                for (VoiceFxModel candidate : VoiceFxModel.values()) {
                    if (candidate == checked) {
                        continue;
                    }
                    VoiceFxState other = voiceFx.get(candidate);
                    voiceFx.put(candidate,
                            new VoiceFxState(false, other.parameters));
                }
            }
            VoiceFxState old = voiceFx.get(checked);
            voiceFx.put(checked, new VoiceFxState(on, old.parameters));
            return this;
        }

        public Builder setVoiceFxParameter(
                VoiceFxModel model,
                String name,
                float value) {
            VoiceFxModel checked = requireNonNull(model, "Voice FX model");
            VoiceFxState old = voiceFx.get(checked);
            if (!old.parameters.containsKey(name)) {
                throw new IllegalArgumentException(
                        "Unknown " + checked.label() + " parameter " + name);
            }
            Map<String, Float> changed = new LinkedHashMap<>(old.parameters);
            changed.put(name, value);
            voiceFx.put(checked, new VoiceFxState(old.on, changed));
            return this;
        }

        public Builder setSelectedVoiceFx(VoiceFxModel model) {
            selectedVoiceFx = requireNonNull(model, "Voice FX model");
            return this;
        }

        public Builder setVoiceFxInput(int channel) {
            requireChannel(channel);
            voiceFxInput = channel;
            return this;
        }

        public Builder setReverb(
                boolean on,
                float size,
                float mix,
                float highPassHz,
                float preDelaySeconds) {
            reverb = new ReverbState(on, size, mix, highPassHz, preDelaySeconds);
            return this;
        }

        public Builder setProcessingParameter(
                int channel,
                String name,
                float value) {
            requireChannel(channel);
            if (name == null || name.isEmpty()) {
                throw new IllegalArgumentException("Processing parameter is required");
            }
            processing[channel - 1].put(name, value);
            return this;
        }

        public Builder setLinked(boolean value) {
            linked = value;
            return this;
        }

        public Builder setMainVolume(float value) {
            mainVolume = value;
            return this;
        }

        public Builder setHeadphoneVolume(float value) {
            headphoneVolume = value;
            return this;
        }

        public Builder setHeadphoneMuted(boolean value) {
            headphoneMuted = value;
            return this;
        }

        public Builder setMonitorBlend(float value) {
            monitorBlend = value;
            return this;
        }

        public Builder setPhoneSource(PhoneSource value) {
            phoneSource = requireNonNull(value, "Phone source");
            return this;
        }

        public Builder setSampleRateHz(int value) {
            sampleRateHz = checkedSampleRate(value);
            sampleRateConfirmed = true;
            return this;
        }

        public Builder setRememberedSampleRateHz(int value) {
            sampleRateHz = checkedSampleRate(value);
            sampleRateConfirmed = false;
            return this;
        }

        public Builder setOutputDelaySeconds(float value) {
            outputDelaySeconds = value;
            return this;
        }

        public Builder setLastProof(String value) {
            lastProof = value == null ? "" : value;
            return this;
        }

        public Io24State build() {
            return new Io24State(this);
        }

        private static int checkedSampleRate(int value) {
            if (value != 44_100 && value != 48_000
                    && value != 88_200 && value != 96_000) {
                throw new IllegalArgumentException(
                        "Sample rate must be 44100, 48000, 88200, or 96000 Hz");
            }
            return value;
        }

        private static VoiceFxState effect(boolean on, Object... values) {
            Map<String, Float> parameters = new LinkedHashMap<>();
            for (int index = 0; index < values.length; index += 2) {
                parameters.put((String) values[index], (Float) values[index + 1]);
            }
            return new VoiceFxState(on, parameters);
        }

        private static void seedProcessing(Map<String, Float> parameters) {
            parameters.put("hpf_on", 0.0f);
            parameters.put("hpf_hz", 80.0f);
            parameters.put("gate_on", 0.0f);
            parameters.put("gate_threshold", -48.0f);
            parameters.put("gate_range", -48.0f);
            parameters.put("gate_attack", 0.005f);
            parameters.put("gate_release", 0.7f);
            parameters.put("compressor_model", 0.0f);
            parameters.put("compressor_on", 0.0f);
            parameters.put("compressor_threshold", -18.0f);
            parameters.put("compressor_ratio", 3.0f);
            parameters.put("compressor_attack", 0.02f);
            parameters.put("compressor_release", 0.15f);
            parameters.put("compressor_gain", 0.0f);
            parameters.put("limiter_on", 0.0f);
            parameters.put("limiter_threshold", -1.0f);
            parameters.put("eq_model", 0.0f);
            parameters.put("eq_on", 0.0f);
            parameters.put("eq_low_freq", 80.0f);
            parameters.put("eq_low_gain", 0.0f);
            parameters.put("eq_lowmid_freq", 400.0f);
            parameters.put("eq_lowmid_gain", 0.0f);
            parameters.put("eq_himid_freq", 2500.0f);
            parameters.put("eq_himid_gain", 0.0f);
            parameters.put("eq_high_freq", 10000.0f);
            parameters.put("eq_high_gain", 0.0f);
            parameters.put("eq_first", 0.0f);
        }
    }

    private static void requireChannel(int channel) {
        if (channel != 1 && channel != 2) {
            throw new IllegalArgumentException("Channel must be 1 or 2");
        }
    }

    private static <T> T requireNonNull(T value, String label) {
        if (value == null) {
            throw new IllegalArgumentException(label + " is required");
        }
        return value;
    }
}
