package dev.ajuntanaga.io24;

import static org.junit.Assert.assertFalse;

import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.Test;

public final class GraphMathTest {
    @Test
    public void everyVoiceFxParameterChangesItsGraphTrace() {
        Io24State defaults = Io24State.defaults();
        for (Io24State.VoiceFxModel model : Io24State.VoiceFxModel.values()) {
            Map<String, Float> base = defaults.voiceFx(model).parameters();
            float[] baseline = GraphMath.effectTrace(model, base, 320, 120);
            for (Map.Entry<String, Float> entry : base.entrySet()) {
                Map<String, Float> changed = new LinkedHashMap<>(base);
                changed.put(entry.getKey(), changedValue(model, entry));
                float[] trace = GraphMath.effectTrace(model, changed, 320, 120);
                assertFalse(
                        model + " " + entry.getKey() + " did not affect its graph",
                        same(baseline, trace));
            }
        }
    }

    @Test
    public void dynamicsAndEqParametersChangeTheirCurves() {
        float[] dynamics = GraphMath.dynamicsCurve(-18, 4, 3, 320, 120);
        assertFalse(same(dynamics,
                GraphMath.dynamicsCurve(-30, 4, 3, 320, 120)));
        assertFalse(same(dynamics,
                GraphMath.dynamicsCurve(-18, 10, 3, 320, 120)));
        assertFalse(same(dynamics,
                GraphMath.dynamicsCurve(-18, 4, 9, 320, 120)));

        float[] eq = GraphMath.eqCurve(
                new float[] {80, 400, 2500, 10000},
                new float[] {0, 0, 0, 0},
                320,
                120);
        assertFalse(same(eq, GraphMath.eqCurve(
                new float[] {120, 400, 2500, 10000},
                new float[] {6, 0, 0, 0},
                320,
                120)));
    }

    private static float changedValue(
            Io24State.VoiceFxModel model,
            Map.Entry<String, Float> entry) {
        String name = entry.getKey();
        float value = entry.getValue();
        if (name.equals("voiced")) {
            return value < 0.5f ? 1.0f : 0.0f;
        }
        if (name.equals("detune")) {
            return value == 8.0f ? 0.0f : value + 1.0f;
        }
        if (name.equals("carrier_type")) {
            return (value + 1.0f) % 3.0f;
        }
        if (name.equals("carrier2")) {
            return value < 0.5f ? 1.0f : 0.0f;
        }
        if (name.equals("carrier_freq")) {
            return value + 25.0f;
        }
        if (name.contains("carrier") && name.contains("hz")) {
            return value + 17.0f;
        }
        if (name.equals("time_s")) {
            return value + 0.01f;
        }
        return value > 0.75f ? value - 0.2f : value + 0.2f;
    }

    private static boolean same(float[] left, float[] right) {
        if (left.length != right.length) {
            return false;
        }
        for (int index = 0; index < left.length; index++) {
            if (Float.floatToIntBits(left[index])
                    != Float.floatToIntBits(right[index])) {
                return false;
            }
        }
        return true;
    }
}
