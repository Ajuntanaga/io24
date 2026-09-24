package dev.ajuntanaga.io24;

import java.util.Map;

/** Pure graph geometry so every displayed parameter has testable visual input. */
public final class GraphMath {
    private static final int POINTS = 72;

    private GraphMath() {
    }

    public static float[] effectTrace(
            Io24State.VoiceFxModel model,
            Map<String, Float> parameters,
            int width,
            int height) {
        if (model == null || parameters == null || width <= 0 || height <= 0) {
            throw new IllegalArgumentException(
                    "Model, parameters, and positive dimensions are required");
        }
        float[] trace = new float[POINTS];
        double signature = 0.0;
        int order = 1;
        for (Map.Entry<String, Float> entry : parameters.entrySet()) {
            signature += entry.getValue() * (0.013 * order);
            order++;
        }
        for (int index = 0; index < POINTS; index++) {
            double x = index / (double) (POINTS - 1);
            double y;
            switch (model) {
                case TRANSFORMER:
                    y = transformer(parameters, x);
                    break;
                case DETUNER:
                    y = detuner(parameters, x);
                    break;
                case VOCODER:
                    y = vocoder(parameters, x);
                    break;
                case RING_MOD:
                    y = ringMod(parameters, x);
                    break;
                case FILTERS:
                    y = filters(parameters, x);
                    break;
                case DELAY:
                    y = delay(parameters, x);
                    break;
                default:
                    y = 0.5;
            }
            // A small ordered signature makes the read-only Vocoder meter and
            // every storable field observable without overwhelming the model shape.
            y += 0.025 * Math.sin((index + 1) * 0.61 + signature * 11.0);
            trace[index] = clamp((float) (y * height), 2.0f, height - 2.0f);
        }
        return trace;
    }

    public static float[] dynamicsCurve(
            float thresholdDb,
            float ratio,
            float makeupDb,
            int width,
            int height) {
        if (width <= 0 || height <= 0 || ratio <= 0.0f) {
            throw new IllegalArgumentException("Positive dimensions and ratio are required");
        }
        float[] trace = new float[POINTS];
        for (int index = 0; index < POINTS; index++) {
            float inputDb = -60.0f + 60.0f * index / (POINTS - 1.0f);
            float outputDb = inputDb;
            if (inputDb > thresholdDb) {
                outputDb = thresholdDb + (inputDb - thresholdDb) / ratio;
            }
            outputDb += makeupDb;
            float normalized = (outputDb + 60.0f) / 60.0f;
            trace[index] = height - clamp(normalized * height, 0.0f, height);
        }
        return trace;
    }

    public static float[] eqCurve(
            float[] frequencies,
            float[] gainsDb,
            int width,
            int height) {
        if (frequencies == null
                || gainsDb == null
                || frequencies.length != gainsDb.length
                || frequencies.length == 0
                || width <= 0
                || height <= 0) {
            throw new IllegalArgumentException("Matching EQ bands and dimensions are required");
        }
        float[] trace = new float[POINTS];
        double lowLog = Math.log(20.0);
        double rangeLog = Math.log(20_000.0) - lowLog;
        for (int index = 0; index < POINTS; index++) {
            double logFrequency = lowLog + rangeLog * index / (POINTS - 1.0);
            double response = 0.0;
            for (int band = 0; band < frequencies.length; band++) {
                double center = Math.log(Math.max(20.0, frequencies[band]));
                double distance = (logFrequency - center) / 0.72;
                response += gainsDb[band] * Math.exp(-distance * distance);
            }
            double normalized = 0.5 - response / 30.0;
            trace[index] = clamp((float) (normalized * height), 2.0f, height - 2.0f);
        }
        return trace;
    }

    private static double transformer(Map<String, Float> p, double x) {
        double lows = value(p, "lows");
        double width = value(p, "width");
        double mix = value(p, "mix");
        double wave = Math.sin(x * Math.PI * (3.0 + width * 8.0));
        double doubled = Math.sin(x * Math.PI * (3.2 + width * 8.5));
        return 0.5 + (wave + doubled * width) * (0.08 + mix * 0.17)
                + (0.5 - x) * (lows - 0.5) * 0.35;
    }

    private static double detuner(Map<String, Float> p, double x) {
        double semitones = 8.0 - value(p, "detune");
        double mix = value(p, "mix");
        return 0.5
                + Math.sin(x * Math.PI * 8.0) * 0.12
                + Math.sin(x * Math.PI * (8.0 + semitones * 0.23))
                * (0.04 + mix * 0.18);
    }

    private static double vocoder(Map<String, Float> p, double x) {
        double volume = value(p, "vol");
        double carrier = value(p, "carrier_type");
        double frequency = value(p, "carrier_freq");
        double voiced = value(p, "voiced");
        double mix = value(p, "mix");
        double bands = 6.0 + carrier * 3.0;
        double envelope = 0.45 + 0.55 * Math.sin(x * Math.PI);
        double carrierWave = carrier == 0.0
                ? Math.sin(x * frequency * 0.09)
                : Math.sin(x * Math.PI * bands);
        return 0.5 + carrierWave * envelope
                * (0.04 + 0.15 * volume) * (0.35 + 0.65 * mix)
                + (voiced - 0.5) * 0.09 * Math.cos(x * Math.PI * 4.0);
    }

    private static double ringMod(Map<String, Float> p, double x) {
        double primary = value(p, "carrier_hz");
        double subOn = value(p, "carrier2");
        double secondary = value(p, "carrier2_hz");
        double distortion = value(p, "dist");
        double volume = value(p, "vol");
        double mix = value(p, "mix");
        double a = Math.sin(x * Math.PI * (2.0 + Math.log10(primary + 1.0) * 4.0));
        double b = Math.sin(x * Math.PI * (2.0 + Math.log10(secondary + 1.0) * 3.0));
        double ring = a * (subOn > 0.5 ? b : 1.0);
        ring = Math.tanh(ring * (1.0 + distortion * 5.0));
        return 0.5 + ring * (0.05 + 0.22 * volume) * (0.3 + 0.7 * mix);
    }

    private static double filters(Map<String, Float> p, double x) {
        double pitch = value(p, "pitch");
        double regeneration = value(p, "regeneration");
        double damping = value(p, "damping");
        double distortion = value(p, "distortion");
        double volume = value(p, "volume");
        double mix = value(p, "mix");
        double center = 0.12 + pitch * 0.76;
        double distance = (x - center) / (0.05 + damping * 0.22);
        double peak = Math.exp(-distance * distance) * (0.2 + regeneration * 0.65);
        double grit = Math.sin(x * Math.PI * (4.0 + distortion * 18.0))
                * distortion * 0.12;
        return 0.72 - (peak + grit) * volume * (0.25 + mix * 0.75);
    }

    private static double delay(Map<String, Float> p, double x) {
        double time = value(p, "time_s");
        double feedback = value(p, "feedback");
        double mix = value(p, "mix");
        double spacing = 0.06 + time / 0.25 * 0.24;
        double nearest = Math.abs((x / spacing) - Math.rint(x / spacing));
        double pulse = Math.exp(-nearest * nearest * 180.0);
        double repeat = Math.pow(Math.max(0.01, feedback), x / spacing);
        return 0.72 - pulse * repeat * (0.08 + mix * 0.34);
    }

    private static float value(Map<String, Float> values, String name) {
        Float value = values.get(name);
        if (value == null) {
            throw new IllegalArgumentException("Missing graph parameter " + name);
        }
        return value;
    }

    private static float clamp(float value, float min, float max) {
        return Math.max(min, Math.min(max, value));
    }
}
