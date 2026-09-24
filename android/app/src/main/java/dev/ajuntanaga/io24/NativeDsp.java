package dev.ajuntanaga.io24;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/** Pure-Java builders for the proven native io24 DSP records. */
final class NativeDsp {
    static final int BLOCK_MIXER = 100;
    static final int BLOCK_VOICE_FX = 201;
    static final int BLOCK_REVERB = 202;
    static final int BLOCK_FILTER = fourCc("filt");
    static final int BLOCK_GATE = fourCc("gate");
    static final int BLOCK_COMPRESSOR = fourCc("comp");
    static final int BLOCK_EQ = fourCc("eq  ");
    static final int BLOCK_LIMITER = fourCc("lim ");
    static final int BLOCK_ORDER = fourCc("opt ");

    private static final int TAG_PARA = 0x50617261;
    private static final int TAG_PARI = 0x50617269;
    private static final int TAG_VOFX = 0x566f4678;
    private static final int TAG_GODV = 0x676f6476;
    private static final int TAG_MAY4 = 0x6d617934;
    private static final int TAG_BOTA = 0x626f7461;
    private static final int TAG_BOTB = 0x626f7462;
    private static final int TAG_BOTC = 0x626f7463;
    private static final int TAG_VECH = 0x76656368;
    private static final int TAG_INIA = 0x696e6961;
    private static final int TAG_BQDF = 0x42716466;
    private static final int TAG_MBDF = 0x4d426466;
    private static final int TAG_VRVB = 0x76727662;
    private static final int TAG_CPXT = 0x63707874;
    private static final int TAG_GATE = 0x67617465;

    private static final float[] IDENTITY = {1, 0, 0, 0, 0};
    private static final float PI_F = Float.intBitsToFloat(0x40490fdb);
    private static final float TWO_PI_F = Float.intBitsToFloat(0x40c90fdb);
    private static final float[] TRANSFORMER_FREQUENCIES = {600, 550};
    private static final float[] NATIVE_RATES = {44_100, 48_000, 88_200, 96_000};
    private static final float[] VOCODER_HP = {
            85, 141, 230, 378, 622, 1024, 1680, 2730, 4450, 7250
    };
    private static final float[] VOCODER_LP = {
            141, 230, 378, 622, 1024, 1690, 2750, 4482, 7300, 11900
    };

    private NativeDsp() {
    }

    static byte[] mixerLevel(int sourceId, float db) {
        ByteBuffer blob = blob(TAG_PARA, 0x14, 0);
        blob.putInt(sourceId);
        blob.putFloat(db);
        return blob.array();
    }

    static byte[] processingOrder(boolean eqFirst) {
        ByteBuffer blob = blob(TAG_PARI, 0x14, 0);
        blob.putInt(0);
        blob.putInt(eqFirst ? 1 : 0);
        return blob.array();
    }

    static byte[] voiceFxSelector(Io24State.VoiceFxModel model) {
        ByteBuffer blob = blob(TAG_VOFX, 0x10, 0);
        blob.putInt(model.ordinal());
        return blob.array();
    }

    static List<byte[]> voiceFxMaterialization(
            Io24State.VoiceFxModel model,
            Io24State.VoiceFxState state,
            int sampleRateHz) {
        switch (model) {
            case TRANSFORMER:
                return transformerBlobs(state, sampleRateHz, true);
            case DETUNER:
                return Arrays.asList(detuner(state), detunerBiquad(sampleRateHz));
            case VOCODER:
                return Arrays.asList(vocoderFilters(sampleRateHz), vocoder(state));
            case RING_MOD:
                return List.of(ringMod(state));
            case FILTERS:
                return List.of(filters(state));
            case DELAY:
                if (sampleRateHz > Io24State.DELAY_NATIVE_MAX_RATE_HZ) {
                    throw new IllegalArgumentException(
                            "Delay cannot run safely on the device above 48 kHz");
                }
                return List.of(delay(state));
            default:
                throw new IllegalArgumentException("Unknown Voice FX model");
        }
    }

    static List<byte[]> voiceFxEdit(
            Io24State.VoiceFxModel model,
            Io24State.VoiceFxState state,
            String changedParameter,
            int sampleRateHz) {
        if (model == Io24State.VoiceFxModel.DELAY
                && sampleRateHz > Io24State.DELAY_NATIVE_MAX_RATE_HZ) {
            throw new IllegalArgumentException(
                    "Delay cannot run safely on the device above 48 kHz");
        }
        switch (model) {
            case TRANSFORMER:
                return transformerBlobs(
                        state, sampleRateHz, "lows".equals(changedParameter));
            case DETUNER:
                return List.of(detuner(state));
            case VOCODER:
                return List.of(vocoder(state));
            case RING_MOD:
                return List.of(ringMod(state));
            case FILTERS:
                return List.of(filters(state));
            case DELAY:
                return List.of(delay(state));
            default:
                throw new IllegalArgumentException("Unknown Voice FX model");
        }
    }

    private static List<byte[]> transformerBlobs(
            Io24State.VoiceFxState state,
            int sampleRateHz,
            boolean refreshTone) {
        List<byte[]> result = new ArrayList<>();
        float lows = state.parameter("lows");
        if (refreshTone) {
            float gainDb = f32(lows * 12.0f);
            for (int band = 0; band < TRANSFORMER_FREQUENCIES.length; band++) {
                result.add(biquadBlob(
                        band,
                        lowShelfFx(
                                TRANSFORMER_FREQUENCIES[band],
                                gainDb,
                                sampleRateHz,
                                0.7f)));
            }
            for (int table = 0; table < TRANSFORMER_FREQUENCIES.length; table++) {
                float[][] coefficients = new float[NATIVE_RATES.length][];
                for (int index = 0; index < NATIVE_RATES.length; index++) {
                    coefficients[index] = lowShelfFx(
                            TRANSFORMER_FREQUENCIES[table],
                            gainDb,
                            NATIVE_RATES[index],
                            0.7f);
                }
                result.add(multiBiquadBlob(table, coefficients));
            }
        }
        ByteBuffer stateBlob = blob(TAG_GODV, 0x20, 0);
        stateBlob.putInt(state.on() ? 1 : 0);
        stateBlob.putFloat(clamp01(lows));
        stateBlob.putFloat(clamp01(state.parameter("width")));
        stateBlob.putFloat(clamp01(lows));
        stateBlob.putFloat(clamp01(state.parameter("mix")));
        result.add(stateBlob.array());
        return result;
    }

    private static byte[] detuner(Io24State.VoiceFxState state) {
        int index = Math.max(0, Math.min(16, Math.round(state.parameter("detune"))));
        ByteBuffer result = blob(TAG_MAY4, 0x24, 0);
        result.putInt(state.on() ? 1 : 0);
        result.putInt(index - 8);
        result.putInt(0).putInt(0).putInt(0);
        result.putFloat(clamp01(state.parameter("mix")));
        return result.array();
    }

    private static byte[] detunerBiquad(int sampleRateHz) {
        return biquadBlob(0, lowPass(6000, sampleRateHz, 0.7f));
    }

    private static byte[] vocoderFilters(int sampleRateHz) {
        ByteBuffer result = blob(TAG_INIA, 0x1c4, 0);
        for (float frequency : VOCODER_HP) {
            putFloats(result, highPass(frequency, sampleRateHz, 2.0f));
        }
        for (float frequency : VOCODER_LP) {
            putFloats(result, lowPass(frequency, sampleRateHz, 2.0f));
        }
        putFloats(result, lowPass(600, sampleRateHz, 0.7f));
        putFloats(result, highPass(2500, sampleRateHz, 0.7f));
        return result.array();
    }

    private static byte[] vocoder(Io24State.VoiceFxState state) {
        ByteBuffer result = blob(TAG_BOTA, 0x28, 0);
        result.putInt(state.on() ? 1 : 0);
        result.putInt(Math.max(0, Math.min(2,
                Math.round(state.parameter("carrier_type")))));
        result.putFloat(state.parameter("carrier_freq"));
        result.putFloat(clamp01(state.parameter("vol")));
        result.putInt(1).putInt(1);
        result.putFloat(clamp01(state.parameter("mix")));
        return result.array();
    }

    private static byte[] ringMod(Io24State.VoiceFxState state) {
        ByteBuffer result = blob(TAG_BOTB, 0x28, 0);
        result.putInt(state.on() ? 1 : 0);
        result.putFloat(state.parameter("carrier_hz"));
        result.putFloat(clamp01(state.parameter("dist")));
        result.putFloat(clamp01(state.parameter("vol")));
        result.putInt(state.parameter("carrier2") >= 0.5f ? 1 : 0);
        result.putFloat(state.parameter("carrier2_hz"));
        result.putFloat(clamp01(state.parameter("mix")));
        return result.array();
    }

    private static byte[] filters(Io24State.VoiceFxState state) {
        float pitch = clamp01(state.parameter("pitch"));
        int samples = (int) f32(f32(pitch * f32(1300.0f)) + f32(250.5f));
        float feedback = f32(f32(clamp01(state.parameter("regeneration"))
                * f32(0.35f)) + f32(0.5f));
        float damping = f32(f32(clamp01(state.parameter("damping"))
                * f32(0.6f)) + f32(0.3f));
        ByteBuffer result = blob(TAG_BOTC, 0x28, 0);
        result.putInt(state.on() ? 1 : 0);
        result.putInt(samples);
        result.putFloat(feedback);
        result.putFloat(damping);
        result.putFloat(clamp01(state.parameter("distortion")));
        result.putFloat(clamp01(state.parameter("volume")));
        result.putFloat(clamp01(state.parameter("mix")));
        return result.array();
    }

    private static byte[] delay(Io24State.VoiceFxState state) {
        ByteBuffer result = blob(TAG_VECH, 0x1c, 0);
        result.putInt(state.on() ? 1 : 0);
        result.putFloat(clamp01(state.parameter("mix")));
        result.putFloat(f32(clamp01(state.parameter("feedback")) * 0.5f));
        result.putFloat(state.parameter("time_s"));
        return result.array();
    }

    static byte[] reverb(Io24State.ReverbState state, int sampleRateHz) {
        float hp = Math.max(0, Math.min(500, state.highPassHz()));
        float preDelay = Math.max(0.0001f, Math.min(0.25f,
                state.preDelaySeconds()));
        float[] coefficients = hp > 0.1f
                ? highPassRbj(hp, sampleRateHz, 0.7f)
                : IDENTITY;
        ByteBuffer result = blob(TAG_VRVB, 0x38, 0);
        result.putInt(state.on() ? 1 : 0);
        result.putFloat(clamp01(state.mix()));
        result.putInt(preDelay > 0.0001f ? 1 : 0);
        result.putFloat(preDelay);
        result.putFloat(clamp01(state.size()));
        result.putFloat(hp);
        putFloats(result, coefficients);
        return result.array();
    }

    static byte[] highPassFilter(boolean on, float frequency, int sampleRateHz) {
        float[] coefficients = on
                ? highPassRbj(Math.max(24, Math.min(1000, frequency)),
                        sampleRateHz, 0.70710678f)
                : IDENTITY;
        return biquadBlob(0, coefficients);
    }

    static List<byte[]> gate(Map<String, Float> values, int sampleRateHz) {
        List<byte[]> result = new ArrayList<>();
        for (int index = 0; index < 2; index++) {
            result.add(gateBlob(
                    index,
                    bool(values, "gate_on", false),
                    value(values, "gate_threshold", -48),
                    value(values, "gate_range", -48),
                    value(values, "gate_attack", 0.005f),
                    value(values, "gate_release", 0.7f),
                    sampleRateHz));
        }
        return result;
    }

    private static byte[] gateBlob(
            int index,
            boolean on,
            float thresholdDb,
            float rangeDb,
            float attackSeconds,
            float releaseSeconds,
            int sampleRateHz) {
        float attack = Math.max(0.00002f, attackSeconds);
        float release = Math.max(0.0001f, releaseSeconds);
        float rate = f32(f32(sampleRateHz) * 0.25f);
        float range = dbToLinear(rangeDb);
        float threshold = dbToInverseLinear(thresholdDb);
        float attackCoefficient = f32(Math.exp(f32(
                f32(f32(-TWO_PI_F / attack) / rate))));
        float kRelease = release; // expander mode uses k=1.0
        float releaseCoefficient = f32(Math.exp(f32(
                f32(f32(-TWO_PI_F / kRelease) / rate))));
        int hold = Math.max(1, (int) Math.ceil(f32(
                f32(kRelease * sampleRateHz) * 0.5f)));
        ByteBuffer result = blob(TAG_GATE, 0x48, index);
        putFloats(result, IDENTITY);
        result.putFloat(range).putFloat(threshold);
        result.putFloat(attack).putFloat(release);
        result.putFloat(attackCoefficient).putFloat(releaseCoefficient);
        result.putInt(hold);
        result.putInt(on ? 1 : 0);
        result.putInt(1); // expander mode
        result.putInt(0); // key listen
        return result.array();
    }

    static List<byte[]> standardCompressor(Map<String, Float> values) {
        boolean on = bool(values, "compressor_on", false);
        List<byte[]> result = new ArrayList<>();
        for (int index = 0; index < 2; index++) {
            result.add(compressorBlob(
                    index,
                    on,
                    value(values, "compressor_threshold", -18),
                    value(values, "compressor_ratio", 3),
                    value(values, "compressor_attack", 0.02f),
                    value(values, "compressor_release", 0.15f),
                    value(values, "compressor_gain", 0)));
        }
        return result;
    }

    private static byte[] compressorBlob(
            int index,
            boolean on,
            float thresholdDb,
            float ratio,
            float attack,
            float release,
            float gainDb) {
        float safeRatio = Math.max(1.0f, ratio);
        float slope = f32(1.0f - f32(1.0f / safeRatio));
        ByteBuffer result = blob(TAG_CPXT, 0x40, index);
        putFloats(result, IDENTITY);
        result.putFloat(Math.max(0.0002f, attack));
        result.putFloat(Math.max(0.0025f, release));
        result.putFloat(slope);
        result.putFloat(0.01f);
        result.putFloat(thresholdDb);
        result.putFloat(dbToLinear(gainDb));
        result.putInt(on ? 1 : 0);
        result.putInt(0);
        return result.array();
    }

    static List<byte[]> limiter(Map<String, Float> values, int sampleRateHz) {
        boolean on = bool(values, "limiter_on", false);
        float threshold = value(values, "limiter_threshold", -1);
        List<byte[]> result = new ArrayList<>();
        for (int index = 0; index < 2; index++) {
            ByteBuffer blob = blob(BLOCK_LIMITER, 0x18, index);
            blob.putInt(on ? 1 : 0);
            blob.putFloat(on
                    ? dbToInverseLinear(threshold)
                    : Float.intBitsToFloat(0x3faab0d5));
            blob.putFloat(on
                    ? f32(Math.exp(f32(-TWO_PI_F
                            / f32(0.4f * sampleRateHz))))
                    : 0.0f);
            result.add(blob.array());
        }
        return result;
    }

    /** Native Stat stores the chosen limiter values even while bypassed. */
    static byte[] limiterPresetState(
            Map<String, Float> values,
            int sampleRateHz) {
        ByteBuffer result = ByteBuffer.allocate(12)
                .order(ByteOrder.LITTLE_ENDIAN);
        result.putInt(bool(values, "limiter_on", false) ? 1 : 0);
        result.putFloat(dbToInverseLinear(
                value(values, "limiter_threshold", -1)));
        result.putFloat(f32(Math.exp(f32(-TWO_PI_F
                / f32(0.4f * sampleRateHz)))));
        return result.array();
    }

    static List<byte[]> standardEq(Map<String, Float> values, int sampleRateHz) {
        boolean on = bool(values, "eq_on", false);
        String[] names = {"low", "lowmid", "himid", "high"};
        float[] defaults = {80, 400, 2500, 10000};
        List<byte[]> result = new ArrayList<>();
        for (int band = 0; band < names.length; band++) {
            float[] coefficients;
            if (!on) {
                coefficients = IDENTITY;
            } else {
                float frequency = value(
                        values, "eq_" + names[band] + "_freq", defaults[band]);
                float gain = value(values, "eq_" + names[band] + "_gain", 0);
                if (band == 0) {
                    coefficients = lowShelfStandard(
                            frequency, gain, sampleRateHz, 0.6f);
                } else if (band == 3) {
                    coefficients = highShelfStandard(
                            frequency, gain, sampleRateHz, 0.6f);
                } else {
                    coefficients = peakingStandard(
                            frequency, gain, sampleRateHz, 0.6f);
                }
            }
            result.add(biquadBlob(band, coefficients));
        }
        return result;
    }

    static byte[] biquadBlob(int band, float[] coefficients) {
        if (coefficients.length != 5) {
            throw new IllegalArgumentException("Biquad requires five coefficients");
        }
        ByteBuffer result = blob(TAG_BQDF, 0x24, 0);
        result.putInt(band);
        putFloats(result, coefficients);
        return result.array();
    }

    private static byte[] multiBiquadBlob(int table, float[][] coefficients) {
        ByteBuffer result = blob(TAG_MBDF, 0x1f4, 0);
        result.putInt(table);
        for (int index = 0; index < coefficients.length; index++) {
            putFloats(result, coefficients[index]);
            result.putFloat(NATIVE_RATES[index]);
        }
        result.position(0x1f0);
        result.putInt(coefficients.length);
        return result.array();
    }

    private static float[] lowPass(float frequency, float sampleRate, float q) {
        float k = f32(Math.tan(f32(f32(frequency)
                * f32(PI_F / f32(sampleRate)))));
        float kk = f32(k * k);
        float n = f32(f32(f32(k / f32(q)) + kk) + 1.0f);
        float b0 = f32(kk / n);
        return new float[] {
                b0,
                f32(f32(f32(1.0f - kk) + f32(1.0f - kk)) / n),
                f32(b0 + b0),
                f32(f32(f32(f32(k / f32(q)) - 1.0f) - kk) / n),
                b0
        };
    }

    private static float[] highPass(float frequency, float sampleRate, float q) {
        float k = f32(Math.tan(f32(f32(frequency)
                * f32(PI_F / f32(sampleRate)))));
        float kk = f32(k * k);
        float n = f32(f32(f32(k / f32(q)) + kk) + 1.0f);
        float b0 = f32(1.0f / n);
        return new float[] {
                b0,
                f32(f32(f32(1.0f - kk) + f32(1.0f - kk)) / n),
                f32(-2.0f / n),
                f32(f32(f32(f32(k / f32(q)) - 1.0f) - kk) / n),
                b0
        };
    }

    private static float[] highPassRbj(
            float frequency, float sampleRate, float q) {
        double k = Math.tan(Math.PI * frequency / sampleRate);
        double n = 1.0 + k / q + k * k;
        return new float[] {
                f32(1.0 / n),
                f32(2.0 * (1.0 - k * k) / n),
                f32(-2.0 / n),
                f32((k / q - 1.0 - k * k) / n),
                f32(1.0 / n)
        };
    }

    private static float[] lowShelfFx(
            float frequency, float gainDb, float sampleRate, float q) {
        float a = f32(Math.pow(10.0, f32(f32(gainDb) * f32(0.025f))));
        float w = f32(f32(f32(frequency) + f32(frequency))
                * f32(PI_F / f32(sampleRate)));
        double sine = Math.sin(w);
        double cosine = Math.cos(w);
        float beta = f32(f32(Math.sqrt(a) / f32(q)) * sine);
        double a0 = (a + 1.0) + (a - 1.0) * cosine + beta;
        return new float[] {
                f32(a * ((a + 1.0) - (a - 1.0) * cosine + beta) / a0),
                f32(2.0 * ((a - 1.0) + (a + 1.0) * cosine) / a0),
                f32(2.0 * a * ((a - 1.0) - (a + 1.0) * cosine) / a0),
                f32(-((a + 1.0) + (a - 1.0) * cosine - beta) / a0),
                f32(a * ((a + 1.0) - (a - 1.0) * cosine - beta) / a0)
        };
    }

    private static float[] peakingStandard(
            float frequency, float gainDb, float sampleRate, float q) {
        float f = f32(frequency);
        float gain = f32(gainDb);
        float quality = f32(q);
        double gainPower = Math.pow(10.0, gain * 0.05);
        double k = Math.tan(f * (Math.PI / sampleRate));
        double k2 = k * k;
        double alphaNumerator = Math.sqrt(gainPower) * k / quality;
        double alphaDenominator = alphaNumerator / gainPower;
        double denominator = alphaDenominator + k2 + 1.0;
        return new float[] {
                f32((k2 + alphaNumerator + 1.0) / denominator),
                f32((2.0 - 2.0 * k2) / denominator),
                f32((2.0 * k2 - 2.0) / denominator),
                f32((alphaDenominator - 1.0 - k2) / denominator),
                f32((k2 - alphaNumerator + 1.0) / denominator)
        };
    }

    private static float[] lowShelfStandard(
            float frequency, float gainDb, float sampleRate, float q) {
        return shelfStandard(frequency, gainDb, sampleRate, q, false);
    }

    private static float[] highShelfStandard(
            float frequency, float gainDb, float sampleRate, float q) {
        return shelfStandard(frequency, gainDb, sampleRate, q, true);
    }

    private static float[] shelfStandard(
            float frequency,
            float gainDb,
            float sampleRate,
            float q,
            boolean high) {
        double f = f32(frequency);
        double gain = f32(gainDb);
        double quality = f32(q);
        double a = Math.pow(10.0, gain * 0.025);
        double w = 2.0 * f * Math.PI / sampleRate;
        double cosine = Math.cos(w);
        double beta = Math.sqrt(a) / quality * Math.sin(w);
        double a0;
        double b0;
        double na1;
        double b1;
        double na2;
        double b2;
        if (high) {
            a0 = (a + 1.0) - (a - 1.0) * cosine + beta;
            b0 = a * ((a + 1.0) + (a - 1.0) * cosine + beta) / a0;
            na1 = -2.0 * ((a - 1.0) - (a + 1.0) * cosine) / a0;
            b1 = -2.0 * a * ((a - 1.0) + (a + 1.0) * cosine) / a0;
            na2 = -((a + 1.0) - (a - 1.0) * cosine - beta) / a0;
            b2 = a * ((a + 1.0) + (a - 1.0) * cosine - beta) / a0;
        } else {
            a0 = (a + 1.0) + (a - 1.0) * cosine + beta;
            b0 = a * ((a + 1.0) - (a - 1.0) * cosine + beta) / a0;
            na1 = 2.0 * ((a - 1.0) + (a + 1.0) * cosine) / a0;
            b1 = 2.0 * a * ((a - 1.0) - (a + 1.0) * cosine) / a0;
            na2 = -((a + 1.0) + (a - 1.0) * cosine - beta) / a0;
            b2 = a * ((a + 1.0) - (a - 1.0) * cosine - beta) / a0;
        }
        return new float[] {
                f32(b0), f32(na1), f32(b1), f32(na2), f32(b2)
        };
    }

    private static float dbToLinear(float db) {
        float rounded = f32(db);
        if (rounded < -144.0f) {
            return Float.intBitsToFloat(0x33877f3f);
        }
        return f32(Math.pow(10.0, f32(rounded * f32(0.05f))));
    }

    private static float dbToInverseLinear(float db) {
        float rounded = f32(db);
        if (rounded > 144.0f) {
            return Float.intBitsToFloat(0x33877f3f);
        }
        return f32(Math.pow(10.0, f32(rounded * f32(-0.05f))));
    }

    private static ByteBuffer blob(int tag, int size, int index) {
        if (size < 12) {
            throw new IllegalArgumentException("Blob size is too small");
        }
        ByteBuffer result = ByteBuffer.allocate(size).order(ByteOrder.LITTLE_ENDIAN);
        result.putInt(tag).putInt(size).putInt(index);
        return result;
    }

    private static void putFloats(ByteBuffer target, float[] values) {
        for (float value : values) {
            target.putFloat(value);
        }
    }

    private static int fourCc(String value) {
        if (value.length() != 4) {
            throw new IllegalArgumentException("FourCC must have four characters");
        }
        return (value.charAt(0) << 24)
                | (value.charAt(1) << 16)
                | (value.charAt(2) << 8)
                | value.charAt(3);
    }

    private static float value(
            Map<String, Float> values,
            String name,
            float fallback) {
        Float result = values.get(name);
        return result == null ? fallback : result;
    }

    private static boolean bool(
            Map<String, Float> values,
            String name,
            boolean fallback) {
        Float result = values.get(name);
        return result == null ? fallback : result >= 0.5f;
    }

    private static float clamp01(float value) {
        return Math.max(0, Math.min(1, value));
    }

    private static float f32(double value) {
        return (float) value;
    }
}
