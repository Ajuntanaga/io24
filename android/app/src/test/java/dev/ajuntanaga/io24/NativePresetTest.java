package dev.ajuntanaga.io24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.MessageDigest;

import org.junit.Test;

public final class NativePresetTest {
    @Test
    public void defaultStateMatchesTheLinuxNativeSlotBuilder() throws Exception {
        byte[] body = NativePreset.build(Io24State.defaults(), 1, 0);

        assertEquals(1028, body.length);
        assertEquals(2, ByteBuffer.wrap(body)
                .order(ByteOrder.LITTLE_ENDIAN).getInt());
        assertEquals(
                "81e8a3964b6cf61fd41651d440139d795c9e82418951042db275b985d8f72562",
                digest(body));
    }

    @Test
    public void standardFatChannelMatchesTheLinuxNativeSlotBuilder()
            throws Exception {
        Io24State.Builder builder = Io24State.defaults().buildUpon();
        set(builder, "hpf_on", 1);
        set(builder, "hpf_hz", 120);
        set(builder, "gate_on", 1);
        set(builder, "gate_threshold", -36);
        set(builder, "gate_range", -24);
        set(builder, "gate_attack", 0.012f);
        set(builder, "gate_release", 0.45f);
        set(builder, "compressor_on", 1);
        set(builder, "compressor_threshold", -22);
        set(builder, "compressor_ratio", 4.5f);
        set(builder, "compressor_attack", 0.014f);
        set(builder, "compressor_release", 0.25f);
        set(builder, "compressor_gain", 3);
        set(builder, "limiter_on", 1);
        set(builder, "limiter_threshold", -3);
        set(builder, "eq_on", 1);
        set(builder, "eq_low_freq", 90);
        set(builder, "eq_low_gain", 3);
        set(builder, "eq_lowmid_freq", 550);
        set(builder, "eq_lowmid_gain", -2);
        set(builder, "eq_himid_freq", 3200);
        set(builder, "eq_himid_gain", 1.5f);
        set(builder, "eq_high_freq", 12000);
        set(builder, "eq_high_gain", 4);

        byte[] body = NativePreset.build(builder.build(), 1, 0);

        assertEquals(
                "aa06253cb151e6be307161cdee96a576b11282f0c13b2545d5ad5c50f043f107",
                digest(body));
    }

    @Test
    public void transformerLeafAndMempDestinationAreExact() throws Exception {
        Io24State state = Io24State.defaults().buildUpon()
                .setSelectedVoiceFx(Io24State.VoiceFxModel.TRANSFORMER)
                .setVoiceFxParameter(
                        Io24State.VoiceFxModel.TRANSFORMER, "lows", 0.3f)
                .setVoiceFxParameter(
                        Io24State.VoiceFxModel.TRANSFORMER, "width", 0.7f)
                .setVoiceFxParameter(
                        Io24State.VoiceFxModel.TRANSFORMER, "mix", 0.4f)
                .setVoiceFxOn(Io24State.VoiceFxModel.TRANSFORMER, true)
                .build();
        byte[] body = NativePreset.build(state, 1, 0);
        byte[] memp = NativePreset.statBlob(3, body);
        ByteBuffer fields = ByteBuffer.wrap(memp).order(ByteOrder.LITTLE_ENDIAN);

        assertEquals(1092, body.length);
        assertEquals(0x4d656d50, fields.getInt(0));
        assertEquals(0x7ec, fields.getInt(4));
        assertEquals(0x53746174, fields.getInt(8));
        assertEquals(3, fields.getInt(12));
        assertEquals(body.length, Short.toUnsignedInt(fields.getShort(23)));
        assertEquals(body.length, fields.getInt(25));
    }

    @Test
    public void unsupportedAndUnsafeActiveEffectsAreRefused() {
        Io24State detuner = Io24State.defaults().buildUpon()
                .setSelectedVoiceFx(Io24State.VoiceFxModel.DETUNER)
                .setVoiceFxOn(Io24State.VoiceFxModel.DETUNER, true)
                .build();
        assertThrows(IllegalArgumentException.class,
                () -> NativePreset.build(detuner, 1, 0));

        Io24State activeDelay = Io24State.defaults().buildUpon()
                .setSampleRateHz(48_000)
                .setSelectedVoiceFx(Io24State.VoiceFxModel.DELAY)
                .setVoiceFxOn(Io24State.VoiceFxModel.DELAY, true)
                .build();
        assertThrows(IllegalArgumentException.class,
                () -> NativePreset.build(activeDelay, 1, 0));
    }

    private static void set(Io24State.Builder builder, String key, float value) {
        builder.setProcessingParameter(1, key, value);
    }

    private static String digest(byte[] value) throws Exception {
        byte[] hash = MessageDigest.getInstance("SHA-256").digest(value);
        StringBuilder result = new StringBuilder(hash.length * 2);
        for (byte item : hash) {
            result.append(String.format("%02x", item & 0xff));
        }
        return result.toString();
    }
}
