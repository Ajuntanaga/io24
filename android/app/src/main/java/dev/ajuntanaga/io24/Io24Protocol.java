package dev.ajuntanaga.io24;

import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.List;

/** Maps typed commands to the established io24 scalar wire records. */
public final class Io24Protocol {
    static final int VOICE_FX_REPLACE_SETTLE_MS = 60;

    private Io24Protocol() {
    }

    static final class EncodedWrite {
        private final int uid;
        private final byte[] frame;
        private final int settleAfterMillis;
        private final String label;

        EncodedWrite(int uid, byte[] frame, int settleAfterMillis, String label) {
            this.uid = uid;
            this.frame = frame.clone();
            this.settleAfterMillis = settleAfterMillis;
            this.label = label;
        }

        int uid() {
            return uid;
        }

        byte[] frame() {
            return frame.clone();
        }

        int settleAfterMillis() {
            return settleAfterMillis;
        }

        String label() {
            return label;
        }
    }

    static final class Transaction {
        private final List<EncodedWrite> writes;
        private final int nextUid;

        Transaction(List<EncodedWrite> writes, int nextUid) {
            this.writes = Collections.unmodifiableList(new ArrayList<>(writes));
            this.nextUid = nextUid;
        }

        List<EncodedWrite> writes() {
            return writes;
        }

        int nextUid() {
            return nextUid;
        }
    }

    /** Encodes one semantic command as one ordered native USB transaction. */
    static Transaction encodeTransaction(
            Io24Command command,
            Io24State before,
            int firstUid) {
        if (command == null || before == null) {
            throw new IllegalArgumentException("Command and state are required");
        }
        if (firstUid < 1 || firstUid > 255) {
            throw new IllegalArgumentException("UID must be in the range 1..255");
        }
        List<NativeWrite> nativeWrites = nativeWrites(command, before);
        List<EncodedWrite> encoded = new ArrayList<>();
        int uid = firstUid;
        if (nativeWrites == null) {
            encoded.add(new EncodedWrite(
                    uid,
                    encode(command, uid),
                    0,
                    command.kind().name()));
            uid = nextUid(uid);
        } else {
            for (NativeWrite write : nativeWrites) {
                encoded.add(new EncodedWrite(
                        uid,
                        PaeFrame.buildBlockWrite(
                                uid, write.block, write.blockIndex, write.blob),
                        write.settleAfterMillis,
                        write.label));
                uid = nextUid(uid);
            }
        }
        return new Transaction(encoded, uid);
    }

    public static byte[] encode(Io24Command command, int uid) {
        if (command == null) {
            throw new IllegalArgumentException("Command is required");
        }
        switch (command.kind()) {
            case SET_HEADPHONE_VOLUME:
                return floatWrite(uid, 0, 1, command.value());
            case SET_MAIN_VOLUME:
                return floatWrite(uid, 0, 2, command.value());
            case SET_GAIN:
                return floatWrite(uid, command.channel() - 1, 3, command.value());
            case SET_FX_MIX:
                return floatWrite(uid, command.channel() - 1, 4, command.value());
            case SET_MONITOR_BLEND:
                return floatWrite(uid, 0, 10, command.value());
            case SET_OUTPUT_DELAY:
                return floatWrite(uid, 0, 14, command.value());
            case SET_PHANTOM:
                return integerWrite(uid, command.channel() - 1, 0,
                        command.toggle() ? 1 : 0);
            case SET_PRESET_ENABLED:
                return integerWrite(uid, command.channel() - 1, 4,
                        command.toggle() ? 1 : 0);
            case SET_HIGH_PASS:
                return integerWrite(uid, command.channel() - 1, 5,
                        command.toggle() ? 1 : 0);
            case SET_HEADPHONE_MUTE:
                return integerWrite(uid, 0, 6, command.toggle() ? 1 : 0);
            case SET_INPUT_MUTE:
                return integerWrite(uid, command.channel() - 1, 7,
                        command.toggle() ? 1 : 0);
            case SET_LINK:
                return integerWrite(uid, 0, 9, command.toggle() ? 1 : 0);
            case SET_MUTE_SYNC:
                return integerWrite(uid, 0, 8, command.toggle() ? 1 : 0);
            case SET_PHONE_SOURCE:
                return integerWrite(uid, 0, 11, command.phoneSource().ordinal());
            case SET_PROCESSING_CHANNEL:
            case SET_VOICE_FX_INPUT:
                return integerWrite(uid, 0, 12, command.channel() - 1);
            case SET_OUTPUT_DELAY_BUS:
                return integerWrite(uid, 0, 13, Math.round(command.value()));
            case SET_PRESET_SLOT:
                return integerWrite(uid, command.channel() - 1, 16,
                        Math.round(command.value()));
            default:
                throw new IllegalArgumentException(
                        command.kind() + " is not a scalar io24 parameter command");
        }
    }

    public static Io24State decodeState(
            PaeFrame.StateReply reply,
            Io24State base) {
        if (reply == null || base == null) {
            throw new IllegalArgumentException("Reply and base state are required");
        }
        int flags = reply.intSlot(42);
        int phantomBytes = reply.intSlot(50);
        int source1 = reply.intSlot(38);
        int source2 = reply.intSlot(39);
        Io24State.Builder builder = base.buildUpon()
                .setInputLevel(1, reply.floatSlot(4))
                .setInputLevel(2, reply.floatSlot(6))
                .setInputGain(1, reply.floatSlot(46))
                .setInputGain(2, reply.floatSlot(47))
                .setInputPresetSlot(1, reply.intSlot(40))
                .setInputPresetSlot(2, reply.intSlot(41))
                .setInputMute(1, bit(flags, 3))
                .setInputMute(2, bit(flags, 4))
                .setInputPhantom(1, (phantomBytes & 0xff) != 0)
                .setInputPhantom(2, ((phantomBytes >>> 8) & 0xff) != 0)
                .setProcessingParameter(1, "source_input", source1 - 2.0f)
                .setProcessingParameter(2, "source_input", source2 - 2.0f)
                .setVoiceFxInput(source1 == 4 ? 2 : 1)
                .setProcessingParameter(1, "preset_enabled", bit(flags, 5) ? 0 : 1)
                .setProcessingParameter(2, "preset_enabled", bit(flags, 6) ? 0 : 1)
                .setProcessingParameter(1, "main_hardware_muted", bit(flags, 1) ? 1 : 0)
                .setHeadphoneMuted(bit(flags, 2))
                .setLinked(bit(flags, 12))
                .setHeadphoneVolume(reply.floatSlot(43))
                .setMainVolume(reply.floatSlot(44))
                .setMonitorBlend(reply.floatSlot(45))
                .setLastProof("Read back from io24");
        return builder.build();
    }

    public static boolean requiresFreshState(Io24Command command) {
        return command != null && command.proof() == Io24Command.Proof.READBACK;
    }

    private static List<NativeWrite> nativeWrites(
            Io24Command command,
            Io24State before) {
        Io24State after = Io24StateReducer.apply(before, command);
        switch (command.kind()) {
            case SET_SAMPLE_RATE:
                int targetRate = Math.round(command.value());
                if (targetRate > Io24State.DELAY_NATIVE_MAX_RATE_HZ
                        || before.selectedVoiceFx()
                        == Io24State.VoiceFxModel.DELAY) {
                    return withFinalSettle(safeVoiceFxOff(
                            before, before.sampleRateHz()),
                            twoAudioQuantaMillis(before.sampleRateHz()));
                }
                return Collections.emptyList();
            case SET_MIXER_SEND:
            case SET_MIXER_ASSIGN:
                return mixerRouteWrites(
                        after, command.source(), EnumSet.of(command.bus()));
            case SET_MIXER_SOLO:
                return mixerBusWrites(after, command.bus());
            case SET_MIXER_MUTE:
                return mixerRouteWrites(
                        after, command.source(), EnumSet.allOf(Io24State.Bus.class));
            case SET_BUS_MASTER:
            case SET_BUS_MUTE:
                return mixerBusWrites(after, command.bus());
            case SET_MIRROR_MAIN:
                return mirrorMainWrites(after, command.bus(), command.toggle());
            case SET_MIXER_PAN:
                return Collections.emptyList();
            case SET_PROCESSING_PARAMETER:
                return processingWrites(after, command.channel(), command.parameter());
            case SET_VOICE_FX_MODEL:
                if (!command.canRunNatively(before)) {
                    return safeVoiceFxOff(before, before.sampleRateHz());
                }
                return selectVoiceFx(
                        command.model(),
                        after.voiceFx(command.model()),
                        before.sampleRateHz());
            case SET_VOICE_FX_ON:
            case SET_VOICE_FX_PARAMETER:
                if (command.model() != before.selectedVoiceFx()
                        || !command.canRunNatively(before)) {
                    return Collections.emptyList();
                }
                return voiceFxBlobWrites(NativeDsp.voiceFxEdit(
                        command.model(),
                        after.voiceFx(command.model()),
                        command.parameter(),
                        before.sampleRateHz()));
            case SET_VOICE_FX_INPUT:
                List<NativeWrite> reassignment = new ArrayList<>();
                reassignment.add(scalarNative(
                        0, 12, command.channel() - 1,
                        true, "Voice FX input"));
                if (before.selectedVoiceFx() == Io24State.VoiceFxModel.DELAY
                        && !Io24Command.setVoiceFxModel(
                                Io24State.VoiceFxModel.DELAY)
                                .canRunNatively(before)) {
                    reassignment.addAll(safeVoiceFxOff(
                            before, before.sampleRateHz()));
                    return reassignment;
                }
                reassignment.addAll(selectVoiceFx(
                        before.selectedVoiceFx(),
                        before.voiceFx(before.selectedVoiceFx()),
                        before.sampleRateHz()));
                return reassignment;
            case SET_REVERB:
                return List.of(new NativeWrite(
                        NativeDsp.BLOCK_REVERB,
                        0,
                        NativeDsp.reverb(after.reverb(), before.sampleRateHz()),
                        0,
                        "Shared reverb"));
            case SAVE_DEVICE_BLOCK:
                int block = Math.round(command.value());
                int absoluteSlot = (command.channel() - 1) * 2 + block;
                byte[] preset = NativePreset.build(
                        before, command.channel(), block);
                return List.of(new NativeWrite(
                        0x4170706c,
                        0,
                        NativePreset.statBlob(absoluteSlot, preset),
                        0,
                        "Input " + command.channel() + " preset block "
                                + (block + 1)));
            default:
                return null;
        }
    }

    private static List<NativeWrite> selectVoiceFx(
            Io24State.VoiceFxModel model,
            Io24State.VoiceFxState state,
            int sampleRateHz) {
        List<NativeWrite> result = new ArrayList<>();
        result.add(new NativeWrite(
                NativeDsp.BLOCK_VOICE_FX,
                0,
                NativeDsp.voiceFxSelector(model),
                VOICE_FX_REPLACE_SETTLE_MS,
                model.label() + " bypass transition"));
        result.add(new NativeWrite(
                NativeDsp.BLOCK_VOICE_FX,
                0,
                NativeDsp.voiceFxSelector(model),
                0,
                model.label() + " selector replay"));
        result.addAll(voiceFxBlobWrites(
                NativeDsp.voiceFxMaterialization(model, state, sampleRateHz)));
        return result;
    }

    private static List<NativeWrite> safeVoiceFxOff(
            Io24State state,
            int sampleRateHz) {
        Io24State off = state.buildUpon()
                .setVoiceFxOn(Io24State.VoiceFxModel.TRANSFORMER, false)
                .build();
        return selectVoiceFx(
                Io24State.VoiceFxModel.TRANSFORMER,
                off.voiceFx(Io24State.VoiceFxModel.TRANSFORMER),
                sampleRateHz);
    }

    private static List<NativeWrite> withFinalSettle(
            List<NativeWrite> writes,
            int settleMillis) {
        if (writes.isEmpty()) {
            return writes;
        }
        List<NativeWrite> result = new ArrayList<>(writes);
        NativeWrite last = result.get(result.size() - 1);
        result.set(result.size() - 1, new NativeWrite(
                last.block,
                last.blockIndex,
                last.blob,
                settleMillis,
                last.label));
        return result;
    }

    private static int twoAudioQuantaMillis(int sampleRateHz) {
        return (int) Math.ceil(1024_000.0 / sampleRateHz);
    }

    private static List<NativeWrite> voiceFxBlobWrites(List<byte[]> blobs) {
        List<NativeWrite> result = new ArrayList<>();
        for (byte[] blob : blobs) {
            result.add(new NativeWrite(
                    NativeDsp.BLOCK_VOICE_FX, 0, blob, 0,
                    "Voice FX state"));
        }
        return result;
    }

    private static List<NativeWrite> processingWrites(
            Io24State state,
            int channel,
            String parameter) {
        MapView values = new MapView(state.processing(channel));
        int blockIndex = channel - 1;
        List<NativeWrite> result = new ArrayList<>();
        if (parameter.startsWith("hpf_")) {
            result.add(new NativeWrite(
                    NativeDsp.BLOCK_FILTER,
                    blockIndex,
                    NativeDsp.highPassFilter(
                            values.bool("hpf_on", false),
                            values.value("hpf_hz", 80),
                            state.sampleRateHz()),
                    0,
                    "Fat Channel high-pass"));
        } else if (parameter.startsWith("gate_")) {
            addBlobs(result, NativeDsp.BLOCK_GATE, blockIndex,
                    NativeDsp.gate(values.values, state.sampleRateHz()),
                    "Fat Channel gate");
        } else if (parameter.startsWith("compressor_")) {
            if (Math.round(values.value("compressor_model", 0)) != 0) {
                throw new IllegalArgumentException(
                        "Android currently exposes the proven Standard compressor controls");
            }
            addBlobs(result, NativeDsp.BLOCK_COMPRESSOR, blockIndex,
                    NativeDsp.standardCompressor(values.values),
                    "Fat Channel compressor");
        } else if (parameter.startsWith("limiter_")) {
            addBlobs(result, NativeDsp.BLOCK_LIMITER, blockIndex,
                    NativeDsp.limiter(values.values, state.sampleRateHz()),
                    "Fat Channel limiter");
        } else if (parameter.equals("eq_first")) {
            result.add(new NativeWrite(
                    NativeDsp.BLOCK_ORDER,
                    blockIndex,
                    NativeDsp.processingOrder(values.bool("eq_first", false)),
                    0,
                    "Fat Channel order"));
        } else if (parameter.startsWith("eq_")) {
            if (Math.round(values.value("eq_model", 0)) != 0) {
                throw new IllegalArgumentException(
                        "Passive and Vintage EQ require the retained UC designer");
            }
            addBlobs(result, NativeDsp.BLOCK_EQ, blockIndex,
                    NativeDsp.standardEq(values.values, state.sampleRateHz()),
                    "Fat Channel EQ");
        } else {
            throw new IllegalArgumentException(
                    "Unknown Fat Channel parameter " + parameter);
        }
        return result;
    }

    private static void addBlobs(
            List<NativeWrite> target,
            int block,
            int blockIndex,
            List<byte[]> blobs,
            String label) {
        for (byte[] blob : blobs) {
            target.add(new NativeWrite(block, blockIndex, blob, 0, label));
        }
    }

    private static List<NativeWrite> mixerRouteWrites(
            Io24State state,
            Io24State.Source source,
            EnumSet<Io24State.Bus> buses) {
        List<NativeWrite> result = new ArrayList<>();
        for (Io24State.Bus bus : buses) {
            result.add(mixerWrite(state, source, bus, bus));
        }
        return result;
    }

    private static List<NativeWrite> mixerBusWrites(
            Io24State state,
            Io24State.Bus bus) {
        List<NativeWrite> result = new ArrayList<>();
        for (Io24State.Source source : Io24State.Source.values()) {
            result.add(mixerWrite(state, source, bus, bus));
        }
        return result;
    }

    private static List<NativeWrite> mirrorMainWrites(
            Io24State state,
            Io24State.Bus target,
            boolean enabled) {
        if (!enabled) {
            return Collections.emptyList();
        }
        List<NativeWrite> result = new ArrayList<>();
        for (Io24State.Source source : Io24State.Source.values()) {
            result.add(mixerWrite(state, source, Io24State.Bus.MAIN, target));
        }
        return result;
    }

    private static NativeWrite mixerWrite(
            Io24State state,
            Io24State.Source source,
            Io24State.Bus sourceBus,
            Io24State.Bus targetBus) {
        float level = effectiveMixerLevel(state, source, sourceBus, targetBus);
        return new NativeWrite(
                NativeDsp.BLOCK_MIXER,
                targetBus.ordinal(),
                NativeDsp.mixerLevel(sourceId(source), level),
                0,
                source.label() + " to " + targetBus.label());
    }

    private static float effectiveMixerLevel(
            Io24State state,
            Io24State.Source source,
            Io24State.Bus sourceBus,
            Io24State.Bus targetBus) {
        Io24State.Send send = state.send(source, sourceBus);
        Io24State.BusState bus = state.bus(targetBus);
        boolean anySolo = false;
        for (Io24State.Source candidate : Io24State.Source.values()) {
            anySolo |= state.send(candidate, sourceBus).soloed();
        }
        if (!send.assigned() || send.muted() || bus.muted()
                || anySolo && !send.soloed()) {
            return -145.0f;
        }
        return Math.max(-144.0f, Math.min(10.0f,
                send.db() + bus.masterDb()));
    }

    private static int sourceId(Io24State.Source source) {
        switch (source) {
            case PLAYBACK_1_2:
                return 0;
            case PLAYBACK_3_4:
                return 1;
            case PLAYBACK_5_6:
                return 2;
            case INPUT_1:
                return 3;
            case INPUT_2:
                return 4;
            case FX_RETURN:
                return 5;
            default:
                throw new IllegalArgumentException("Unknown mixer source");
        }
    }

    private static NativeWrite scalarNative(
            int index,
            int wireId,
            int value,
            boolean integer,
            String label) {
        byte[] frame = integer
                ? parameterBlob(0x50617269, index, wireId, value)
                : parameterBlob(0x50617261, index, wireId, value);
        return new NativeWrite(0x4170706c, 0, frame, 0, label);
    }

    private static byte[] parameterBlob(
            int tag,
            int index,
            int wireId,
            int valueBits) {
        java.nio.ByteBuffer result = java.nio.ByteBuffer.allocate(0x14)
                .order(java.nio.ByteOrder.LITTLE_ENDIAN);
        result.putInt(tag).putInt(0x14).putInt(index).putInt(wireId)
                .putInt(valueBits);
        return result.array();
    }

    private static int nextUid(int uid) {
        return uid == 255 ? 1 : uid + 1;
    }

    private static final class NativeWrite {
        final int block;
        final int blockIndex;
        final byte[] blob;
        final int settleAfterMillis;
        final String label;

        NativeWrite(
                int block,
                int blockIndex,
                byte[] blob,
                int settleAfterMillis,
                String label) {
            this.block = block;
            this.blockIndex = blockIndex;
            this.blob = blob;
            this.settleAfterMillis = settleAfterMillis;
            this.label = label;
        }
    }

    private static final class MapView {
        final java.util.Map<String, Float> values;

        MapView(java.util.Map<String, Float> values) {
            this.values = values;
        }

        float value(String key, float fallback) {
            Float found = values.get(key);
            return found == null ? fallback : found;
        }

        boolean bool(String key, boolean fallback) {
            Float found = values.get(key);
            return found == null ? fallback : found >= 0.5f;
        }
    }

    private static byte[] floatWrite(
            int uid,
            int index,
            int wireId,
            float value) {
        return PaeFrame.buildFloatParameterWrite(uid, index, wireId, value);
    }

    private static byte[] integerWrite(
            int uid,
            int index,
            int wireId,
            int value) {
        return PaeFrame.buildIntegerParameterWrite(uid, index, wireId, value);
    }

    private static boolean bit(int value, int bit) {
        return (value & (1 << bit)) != 0;
    }
}
