package dev.ajuntanaga.io24;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/** Pure builder for firmware-1.28 native front-panel preset-block records. */
final class NativePreset {
    private static final int VERSION = 2;
    private static final int MEMP = 0x4d656d50;
    private static final int STAT = 0x53746174;
    private static final int MEMP_SIZE = 0x7ec;
    private static final int FRAGMENT_LIMIT = 0x7ce;
    private static final int VOICE_FX_PARENT_VERSION = 6;
    private static final float[] RATES = {44_100, 48_000, 88_200, 96_000};
    private static final byte[] CHANNEL = ascii("opt ");
    private static final byte[] FILTER = ascii("filt");
    private static final byte[] GATE = ascii("gate");
    private static final byte[] COMPRESSOR = ascii("comp");
    private static final byte[] EQ = ascii("eq  ");
    private static final byte[] LIMITER = ascii("lim ");
    private static final byte[] VOICE_FX = {0, 0, 0, (byte) 201};

    /* Firmware 1.28's smallest complete neutral Stat record. Its hash and
       structure are pinned by the Linux native-slot tests. */
    private static final String STOCK_BASE =
            "AgAAAPgDAAAAAAAAb3B0IOwDAAAAAAAA5AMAAAAAAABmaWx0eAAAAAAAAABnYXRlgAAAAAAAAABj"
          + "b21w5AAAAAAAAABlcSAgsAEAAAAAAABsaW0gHAAAAAAAAAAEAAAAAACAPwAAAAAAAAAAAAAAAAAA"
          + "AAABAEQsRwAAAAAAAIA/AAAAAAAAAAAAAAAAAAAAAAEAgDtHAAAAAAAAgD8AAAAAAAAAAAAAAAAA"
          + "AAAAAQBErEcAAAAAAACAPwAAAAAAAAAAAAAAAAAAAAABAIC7RwAAAAAAAAAAeAAAAOpaizu/UP4/"
          + "AAAAAJTSfb/qWou7bxKDOgAAekRCYGU8hesRP8XJdT+Cvn8/GTEAAAAAAAABAAAAAAAAAAAAgD8A"
          + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAuAsAAAAAAAABAAAAAAAAAAQA"
          + "AAAlQ10/XEHivlxBYj5qoDQ+Y67nvgEARCxHAAAAADX8WT/FeKm+xXgpPk5MCj5+i9a+AQCAO0cA"
          + "AAAAGA9CPw3IDz8NyI++B78qvt3cMr4BAESsRwAAAABx0T4/ZMErP2TBq75Jm1S+H/gQvgEAgLtH"
          + "AAAAAGgAAAAlQ10/XUHivl1BYj5ooDQ+Y67nvoXrUT1cj8I+iCJVPwAAQEAAAPLBlsQXQAEAAAAA"
          + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgD8AAAAAAAAAAAQA"
          + "AAAWWHs/mIvqP4QO6b+Q8VW/ySxZPwAAgD8AAAAAAAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAA"
          + "AAAAAAAHAEQsRwEAAADskns/gC/sP2m/6r+UGFm/SPdbPwAAgD8AAAAAAAAAAAAAAAAAAAAAAACA"
          + "PwAAAAAAAAAAAAAAAAAAAAAHAIA7RwEAAAA05Xw/y+r0P+iq87+ODmq/QhFrPwAAgD8AAAAAAAAA"
          + "AAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAAAAHAESsRwEAAABMCX0/Qsr1P02N9L/FxGu/Ypls"
          + "PwAAgD8AAAAAAAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAAAAHAIC7RwEAAAAEAAAATaOD"
          + "P8KZsz4m+qu+JUYcPm52Ob7fviC+zoURPgEARCxHAAAAAPR/gz98z+o+nOnjvu1ECz7+Wie+lj8k"
          + "vrJ8Fj4BAIA7RwAAAAApcII/sHSUP4Tik79mgF2+ot5JPtPD9r2e2e09AQBErEcAAAAAxEuCPwWd"
          + "nz/IKp+/rAaVvlTGiz4UDNW9WSbOPQEAgLtHAAAAABgAAAABAAAAAACAP6nofz8AAAAA1bCqPwAA"
          + "AAA=";

    private NativePreset() {
    }

    /** Build the complete body written to one of the four front-panel blocks. */
    static byte[] build(Io24State state, int channel, int block) {
        if (state == null) {
            throw new IllegalArgumentException("Preset state is required");
        }
        if (channel != 1 && channel != 2) {
            throw new IllegalArgumentException("Preset input must be 1 or 2");
        }
        if (block != 0 && block != 1) {
            throw new IllegalArgumentException("Preset block must be 0 or 1");
        }

        byte[] base = decodeBase64(STOCK_BASE);
        ByteBuffer header = ByteBuffer.wrap(base).order(ByteOrder.LITTLE_ENDIAN);
        if (header.getInt() != VERSION) {
            throw new IllegalStateException("Embedded native preset version changed");
        }
        List<Chunk> top = decodeGroup(Arrays.copyOfRange(base, 4, base.length));
        Chunk channelChunk = required(top, CHANNEL);
        List<Chunk> leaves = decodeGroup(channelChunk.payload);
        Map<String, Float> processing = state.processing(channel);

        patchFilter(required(leaves, FILTER).payload, processing);
        patchGate(required(leaves, GATE).payload, processing, state.sampleRateHz());
        patchCompressor(required(leaves, COMPRESSOR).payload, processing);
        patchEq(required(leaves, EQ).payload, processing);
        patchLimiter(required(leaves, LIMITER).payload, processing,
                state.sampleRateHz());
        channelChunk.payload = encodeGroup(leaves);

        for (int index = top.size() - 1; index >= 0; index--) {
            if (Arrays.equals(top.get(index).key, VOICE_FX)) {
                top.remove(index);
            }
        }
        Io24State.VoiceFxModel model = state.selectedVoiceFx();
        Io24State.VoiceFxState effect = state.voiceFx(model);
        if (state.voiceFxInput() == channel && effect.on()) {
            top.add(new Chunk(VOICE_FX, voiceFxPayload(
                    model, effect, state.sampleRateHz())));
        }

        byte[] body = encodeGroup(top);
        ByteBuffer result = ByteBuffer.allocate(4 + body.length)
                .order(ByteOrder.LITTLE_ENDIAN);
        result.putInt(VERSION).put(body);
        return result.array();
    }

    /** Build the fixed-size inner MemP/Stat blob consumed by PaeFrame. */
    static byte[] statBlob(int absoluteSlot, byte[] record) {
        if (absoluteSlot < 0 || absoluteSlot > 3) {
            throw new IllegalArgumentException("Device preset slot must be 0..3");
        }
        if (record == null || record.length == 0 || record.length > FRAGMENT_LIMIT) {
            throw new IllegalArgumentException("Native preset body is too large");
        }
        ByteBuffer result = ByteBuffer.allocate(MEMP_SIZE)
                .order(ByteOrder.LITTLE_ENDIAN);
        result.putInt(MEMP).putInt(MEMP_SIZE).putInt(STAT);
        result.putInt(absoluteSlot);
        result.putShort((short) 0);
        result.putInt(0); // fragment offset
        result.put((byte) 0); // final fragment
        result.putShort((short) record.length);
        result.putInt(record.length);
        result.put(record);
        return result.array();
    }

    private static void patchFilter(byte[] component, Map<String, Float> values) {
        requireSize("filter", component, 120);
        boolean on = bool(values, "hpf_on", false);
        float frequency = value(values, "hpf_hz", 80);
        for (int index = 0; index < RATES.length; index++) {
            byte[] blob = NativeDsp.highPassFilter(on, frequency,
                    Math.round(RATES[index]));
            System.arraycopy(blob, 16, component, index * 29 + 4, 20);
        }
    }

    private static void patchGate(
            byte[] component,
            Map<String, Float> values,
            int sampleRateHz) {
        requireSize("gate", component, 128);
        List<byte[]> blobs = NativeDsp.gate(values, sampleRateHz);
        for (int index = 0; index < 2; index++) {
            System.arraycopy(blobs.get(index), 12, component,
                    8 + index * 60, 60);
        }
    }

    private static void patchCompressor(
            byte[] component,
            Map<String, Float> values) {
        requireSize("compressor", component, 228);
        List<byte[]> blobs = NativeDsp.standardCompressor(values);
        for (int rate = 0; rate < RATES.length; rate++) {
            System.arraycopy(blobs.get(0), 12, component, rate * 29 + 4, 20);
        }
        for (int index = 0; index < 2; index++) {
            System.arraycopy(blobs.get(index), 12, component,
                    124 + index * 52, 52);
        }
    }

    private static void patchEq(byte[] component, Map<String, Float> values) {
        requireSize("equalizer", component, 432);
        for (int rate = 0; rate < RATES.length; rate++) {
            List<byte[]> blobs = NativeDsp.standardEq(values, Math.round(RATES[rate]));
            int main = rate * 69 + 4;
            System.arraycopy(blobs.get(1), 16, component, main, 20);
            System.arraycopy(blobs.get(2), 16, component, main + 20, 20);
            System.arraycopy(blobs.get(3), 16, component, main + 40, 20);
            int wide = 280 + rate * 37 + 4;
            System.arraycopy(blobs.get(0), 16, component, wide, 20);
            Arrays.fill(component, wide + 20, wide + 28, (byte) 0);
        }
    }

    private static void patchLimiter(
            byte[] component,
            Map<String, Float> values,
            int sampleRateHz) {
        requireSize("limiter", component, 28);
        byte[] state = NativeDsp.limiterPresetState(values, sampleRateHz);
        System.arraycopy(state, 0, component, 4, state.length);
    }

    private static byte[] voiceFxPayload(
            Io24State.VoiceFxModel model,
            Io24State.VoiceFxState state,
            int sampleRateHz) {
        if (model != Io24State.VoiceFxModel.TRANSFORMER
                && model != Io24State.VoiceFxModel.DELAY) {
            throw new IllegalArgumentException(
                    model.label() + " has no decoded native preset-block body");
        }
        if (model == Io24State.VoiceFxModel.DELAY) {
            throw new IllegalArgumentException(
                    "Delay cannot be stored active in a device block; use a "
                    + "phone scene so safe placement is chosen when it loads");
        }
        List<byte[]> materialized = NativeDsp.voiceFxMaterialization(
                model, state, sampleRateHz);
        byte[] live = materialized.get(materialized.size() - 1);
        byte[] leaf = new byte[4 + live.length - 12];
        ByteBuffer.wrap(leaf).order(ByteOrder.LITTLE_ENDIAN)
                .putInt(live.length - 12)
                .put(live, 12, live.length - 12);
        byte[] child = encodeGroup(List.of(new Chunk(
                new byte[] {0, 0, 0, (byte) model.ordinal()}, leaf)));
        return ByteBuffer.allocate(8 + child.length)
                .order(ByteOrder.LITTLE_ENDIAN)
                .putInt(VOICE_FX_PARENT_VERSION)
                .putInt(model.ordinal())
                .put(child)
                .array();
    }

    private static List<Chunk> decodeGroup(byte[] data) {
        if (data.length < 8) {
            throw new IllegalArgumentException("Native preset group is truncated");
        }
        ByteBuffer bytes = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
        long declared = bytes.getLong();
        if (declared != data.length - 8L) {
            throw new IllegalArgumentException("Native preset group length differs");
        }
        int foundCount = -1;
        long[] foundSizes = null;
        int maximum = Math.min(64, (data.length - 8) / 12);
        for (int count = 0; count <= maximum; count++) {
            long[] sizes = new long[count];
            long payloadBytes = 0;
            boolean valid = true;
            for (int index = 0; index < count; index++) {
                long size = bytes.getLong(8 + index * 12 + 4);
                if (size < 0 || size > Integer.MAX_VALUE) {
                    valid = false;
                    break;
                }
                sizes[index] = size;
                payloadBytes += size;
            }
            if (valid && 8L + 12L * count + payloadBytes == data.length) {
                if (foundCount >= 0) {
                    throw new IllegalArgumentException(
                            "Native preset directory is ambiguous");
                }
                foundCount = count;
                foundSizes = sizes;
            }
        }
        if (foundCount < 0 || foundSizes == null) {
            throw new IllegalArgumentException("Native preset directory is invalid");
        }
        List<Chunk> chunks = new ArrayList<>();
        int payloadAt = 8 + 12 * foundCount;
        for (int index = 0; index < foundCount; index++) {
            byte[] key = Arrays.copyOfRange(
                    data, 8 + 12 * index, 12 + 12 * index);
            int size = (int) foundSizes[index];
            chunks.add(new Chunk(key,
                    Arrays.copyOfRange(data, payloadAt, payloadAt + size)));
            payloadAt += size;
        }
        return chunks;
    }

    private static byte[] encodeGroup(List<Chunk> chunks) {
        int bodySize = 0;
        for (Chunk chunk : chunks) {
            bodySize += 12 + chunk.payload.length;
        }
        ByteBuffer result = ByteBuffer.allocate(8 + bodySize)
                .order(ByteOrder.LITTLE_ENDIAN);
        result.putLong(bodySize);
        for (Chunk chunk : chunks) {
            if (chunk.key.length != 4) {
                throw new IllegalArgumentException("Native preset key is not four bytes");
            }
            result.put(chunk.key).putLong(chunk.payload.length);
        }
        for (Chunk chunk : chunks) {
            result.put(chunk.payload);
        }
        return result.array();
    }

    private static Chunk required(List<Chunk> chunks, byte[] key) {
        Chunk result = null;
        for (Chunk chunk : chunks) {
            if (Arrays.equals(chunk.key, key)) {
                if (result != null) {
                    throw new IllegalArgumentException("Native preset repeats a chunk");
                }
                result = chunk;
            }
        }
        if (result == null) {
            throw new IllegalArgumentException("Native preset is missing a chunk");
        }
        return result;
    }

    private static void requireSize(String label, byte[] data, int expected) {
        if (data.length != expected) {
            throw new IllegalArgumentException(label + " preset state changed size");
        }
    }

    private static float value(
            Map<String, Float> values,
            String name,
            float fallback) {
        Float found = values.get(name);
        return found == null ? fallback : found;
    }

    private static boolean bool(
            Map<String, Float> values,
            String name,
            boolean fallback) {
        Float found = values.get(name);
        return found == null ? fallback : found >= 0.5f;
    }

    private static byte[] ascii(String value) {
        return value.getBytes(java.nio.charset.StandardCharsets.US_ASCII);
    }

    private static byte[] decodeBase64(String text) {
        int padding = text.endsWith("==") ? 2 : text.endsWith("=") ? 1 : 0;
        byte[] result = new byte[text.length() * 3 / 4 - padding];
        int accumulator = 0;
        int bits = 0;
        int output = 0;
        for (int index = 0; index < text.length(); index++) {
            char item = text.charAt(index);
            if (item == '=') {
                break;
            }
            int value;
            if (item >= 'A' && item <= 'Z') {
                value = item - 'A';
            } else if (item >= 'a' && item <= 'z') {
                value = item - 'a' + 26;
            } else if (item >= '0' && item <= '9') {
                value = item - '0' + 52;
            } else if (item == '+') {
                value = 62;
            } else if (item == '/') {
                value = 63;
            } else {
                throw new IllegalArgumentException("Embedded preset base is not Base64");
            }
            accumulator = (accumulator << 6) | value;
            bits += 6;
            if (bits >= 8) {
                bits -= 8;
                result[output++] = (byte) (accumulator >>> bits);
                accumulator &= (1 << bits) - 1;
            }
        }
        if (output != result.length) {
            throw new IllegalArgumentException("Embedded preset base is truncated");
        }
        return result;
    }

    private static final class Chunk {
        final byte[] key;
        byte[] payload;

        Chunk(byte[] key, byte[] payload) {
            this.key = Arrays.copyOf(key, key.length);
            this.payload = Arrays.copyOf(payload, payload.length);
        }
    }
}
