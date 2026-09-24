package dev.ajuntanaga.io24;

import android.content.Context;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.Switch;

import java.util.LinkedHashMap;
import java.util.Map;

/** Full two-channel dynamics and EQ editor. */
final class FatChannelView implements ControllerView {
    private final View root;
    private final CommandSink sink;
    private final Spinner inputSelector;
    private final Switch highPassOn;
    private final ParameterSlider highPassFrequency;
    private final Switch gateOn;
    private final ParameterSlider gateThreshold;
    private final ParameterSlider gateRange;
    private final ParameterSlider gateAttack;
    private final ParameterSlider gateRelease;
    private final Spinner compressorModel;
    private final Switch compressorOn;
    private final ParameterSlider compressorThreshold;
    private final ParameterSlider compressorRatio;
    private final ParameterSlider compressorAttack;
    private final ParameterSlider compressorRelease;
    private final ParameterSlider compressorGain;
    private final DynamicsGraphView dynamicsGraph;
    private final Switch limiterOn;
    private final ParameterSlider limiterThreshold;
    private final Spinner eqModel;
    private final Switch eqOn;
    private final ParameterSlider[] eqFrequencies = new ParameterSlider[4];
    private final ParameterSlider[] eqGains = new ParameterSlider[4];
    private final EqGraphView eqGraph;
    private final Switch eqFirst;
    private final Map<String, ParameterSlider> sliders = new LinkedHashMap<>();
    private Io24State lastState = Io24State.defaults();
    private int channel = 1;
    private boolean rendering;

    FatChannelView(Context context, CommandSink sink) {
        this.sink = sink;
        LinearLayout content = Ui.column(context);
        content.setPadding(Ui.dp(context, 16), Ui.dp(context, 12),
                Ui.dp(context, 16), Ui.dp(context, 24));
        content.addView(Ui.title(context, "Fat Channel"), Ui.match());
        content.addView(Ui.caption(context,
                "Gate, compression, limiting, and equalization for one input."),
                Ui.spaced(context));

        inputSelector = spinner(context, new String[] {"Input 1", "Input 2"});
        inputSelector.setContentDescription("Fat Channel input");
        inputSelector.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                channel = position + 1;
                render(lastState);
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        content.addView(inputSelector, Ui.spaced(context));

        LinearLayout filter = Ui.panel(context);
        filter.addView(Ui.section(context, "High-pass filter"), Ui.match());
        highPassOn = toggle(context, "On", "hpf_on");
        filter.addView(highPassOn, Ui.match());
        highPassFrequency = slider(
                context, filter, "hpf_hz", "Cutoff", 24, 1000, 244,
                ParameterSlider.Scale.LOG, Ui::hz);
        content.addView(filter, Ui.spaced(context));

        LinearLayout gate = Ui.panel(context);
        gate.addView(Ui.section(context, "Gate / Expander"), Ui.match());
        gateOn = toggle(context, "On", "gate_on");
        gate.addView(gateOn, Ui.match());
        gateThreshold = slider(context, gate, "gate_threshold", "Threshold",
                -84, 0, 168, ParameterSlider.Scale.LINEAR, Ui::db);
        gateRange = slider(context, gate, "gate_range", "Range",
                -84, 0, 168, ParameterSlider.Scale.LINEAR, Ui::db);
        gateAttack = slider(context, gate, "gate_attack", "Attack",
                0.00002f, 0.5f, 250, ParameterSlider.Scale.LOG,
                value -> millis(value));
        gateRelease = slider(context, gate, "gate_release", "Release",
                0.05f, 2.0f, 195, ParameterSlider.Scale.LOG,
                value -> millis(value));
        content.addView(gate, Ui.spaced(context));

        LinearLayout compressor = Ui.panel(context);
        compressor.addView(Ui.section(context, "Compressor"), Ui.match());
        compressorModel = spinner(
                context, new String[] {"Standard"});
        compressorModel.setContentDescription("Compressor model");
        compressorModel.setOnItemSelectedListener(parameterSpinner(
                "compressor_model"));
        compressor.addView(compressorModel, Ui.match());
        compressor.addView(Ui.caption(context,
                "Exact Standard model controls."), Ui.match());
        compressorOn = toggle(context, "On", "compressor_on");
        compressor.addView(compressorOn, Ui.match());
        dynamicsGraph = new DynamicsGraphView(context);
        compressor.addView(dynamicsGraph, Ui.spaced(context));
        compressorThreshold = slider(
                context, compressor, "compressor_threshold", "Threshold",
                -56, 0, 112, ParameterSlider.Scale.LINEAR, Ui::db);
        compressorRatio = slider(
                context, compressor, "compressor_ratio", "Ratio",
                1, 20, 190, ParameterSlider.Scale.LINEAR,
                value -> String.format(java.util.Locale.US, "%.1f:1", value));
        compressorAttack = slider(
                context, compressor, "compressor_attack", "Attack",
                0.0002f, 0.15f, 250, ParameterSlider.Scale.LOG,
                value -> millis(value));
        compressorRelease = slider(
                context, compressor, "compressor_release", "Release",
                0.0025f, 0.9f, 250, ParameterSlider.Scale.LOG,
                value -> millis(value));
        compressorGain = slider(
                context, compressor, "compressor_gain", "Makeup",
                0, 28, 112, ParameterSlider.Scale.LINEAR, Ui::db);
        content.addView(compressor, Ui.spaced(context));

        LinearLayout limiter = Ui.panel(context);
        limiter.addView(Ui.section(context, "Limiter"), Ui.match());
        limiterOn = toggle(context, "On", "limiter_on");
        limiter.addView(limiterOn, Ui.match());
        limiterThreshold = slider(
                context, limiter, "limiter_threshold", "Ceiling",
                -28, 0, 112, ParameterSlider.Scale.LINEAR, Ui::db);
        content.addView(limiter, Ui.spaced(context));

        LinearLayout equalizer = Ui.panel(context);
        equalizer.addView(Ui.section(context, "Equalizer"), Ui.match());
        eqModel = spinner(
                context, new String[] {"Standard"});
        eqModel.setContentDescription("Equalizer model");
        eqModel.setOnItemSelectedListener(parameterSpinner("eq_model"));
        equalizer.addView(eqModel, Ui.match());
        equalizer.addView(Ui.caption(context,
                "Passive and Vintage depend on UC's retained desktop designer."),
                Ui.match());
        eqOn = toggle(context, "On", "eq_on");
        equalizer.addView(eqOn, Ui.match());
        eqGraph = new EqGraphView(context);
        equalizer.addView(eqGraph, Ui.spaced(context));
        String[] bandNames = {"Low", "Low mid", "High mid", "High"};
        String[] keys = {"low", "lowmid", "himid", "high"};
        float[] defaultMin = {20, 80, 400, 1000};
        float[] defaultMax = {500, 3000, 12000, 20000};
        for (int index = 0; index < 4; index++) {
            equalizer.addView(Ui.label(context, bandNames[index]), Ui.spaced(context));
            eqFrequencies[index] = slider(
                    context, equalizer, "eq_" + keys[index] + "_freq",
                    "Frequency", defaultMin[index], defaultMax[index], 300,
                    ParameterSlider.Scale.LOG, Ui::hz);
            eqGains[index] = slider(
                    context, equalizer, "eq_" + keys[index] + "_gain",
                    "Gain", -15, 15, 120,
                    ParameterSlider.Scale.LINEAR, Ui::db);
        }
        eqFirst = toggle(context, "EQ before compressor", "eq_first");
        equalizer.addView(eqFirst, Ui.spaced(context));
        content.addView(equalizer, Ui.spaced(context));
        root = Ui.scroll(context, content);
    }

    @Override
    public View view() {
        return root;
    }

    @Override
    public void render(Io24State state) {
        lastState = state;
        boolean enabled = state.connectionStatus()
                == Io24State.ConnectionStatus.CONNECTED && !state.busy();
        Map<String, Float> values = state.processing(channel);
        rendering = true;
        highPassOn.setChecked(on(values, "hpf_on"));
        highPassFrequency.setValue(value(values, "hpf_hz", 80));
        gateOn.setChecked(on(values, "gate_on"));
        gateThreshold.setValue(value(values, "gate_threshold", -48));
        gateRange.setValue(value(values, "gate_range", -48));
        gateAttack.setValue(value(values, "gate_attack", 0.005f));
        gateRelease.setValue(value(values, "gate_release", 0.7f));
        compressorModel.setSelection(0, false);
        compressorOn.setChecked(on(values, "compressor_on"));
        compressorThreshold.setValue(
                value(values, "compressor_threshold", -18));
        compressorRatio.setValue(value(values, "compressor_ratio", 3));
        compressorAttack.setValue(value(values, "compressor_attack", 0.02f));
        compressorRelease.setValue(
                value(values, "compressor_release", 0.15f));
        compressorGain.setValue(value(values, "compressor_gain", 0));
        limiterOn.setChecked(on(values, "limiter_on"));
        limiterThreshold.setValue(value(values, "limiter_threshold", -1));
        eqModel.setSelection(0, false);
        eqOn.setChecked(on(values, "eq_on"));
        String[] keys = {"low", "lowmid", "himid", "high"};
        float[] frequencyDefaults = {80, 400, 2500, 10000};
        for (int index = 0; index < 4; index++) {
            eqFrequencies[index].setValue(value(
                    values, "eq_" + keys[index] + "_freq",
                    frequencyDefaults[index]));
            eqGains[index].setValue(value(
                    values, "eq_" + keys[index] + "_gain", 0));
        }
        eqFirst.setChecked(on(values, "eq_first"));
        rendering = false;
        updateGraphs();
        highPassOn.setEnabled(enabled);
        compressorModel.setEnabled(enabled);
        eqModel.setEnabled(enabled);
        for (ParameterSlider slider : sliders.values()) {
            Ui.enabledTree(slider, enabled);
        }
        for (Switch toggle : new Switch[] {
                gateOn, compressorOn, limiterOn, eqOn, eqFirst}) {
            toggle.setEnabled(enabled);
        }
    }

    private ParameterSlider slider(
            Context context,
            LinearLayout parent,
            String key,
            String name,
            float min,
            float max,
            int steps,
            ParameterSlider.Scale scale,
            ParameterSlider.Formatter formatter) {
        ParameterSlider slider = new ParameterSlider(
                context, name, min, max, steps, scale, formatter);
        slider.setListener((value, committed) -> {
            updateGraphs();
            if (committed && !rendering) {
                sink.dispatch(Io24Command.setProcessingParameter(
                        channel, key, value));
            }
        });
        sliders.put(key, slider);
        parent.addView(slider, Ui.spaced(context));
        return slider;
    }

    private Switch toggle(Context context, String label, String key) {
        Switch result = Ui.toggle(context, label);
        result.setContentDescription(label + " " + key.replace('_', ' '));
        result.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setProcessingParameter(
                        channel, key, checked ? 1.0f : 0.0f));
            }
        });
        return result;
    }

    private AdapterView.OnItemSelectedListener parameterSpinner(String key) {
        return new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                if (!rendering) {
                    sink.dispatch(Io24Command.setProcessingParameter(
                            channel, key, position));
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        };
    }

    private void updateGraphs() {
        dynamicsGraph.setDynamics(
                compressorThreshold.value(),
                compressorRatio.value(),
                compressorGain.value());
        float[] frequencies = new float[4];
        float[] gains = new float[4];
        for (int index = 0; index < 4; index++) {
            frequencies[index] = eqFrequencies[index].value();
            gains[index] = eqGains[index].value();
        }
        eqGraph.setEq(frequencies, gains);
    }

    private static Spinner spinner(Context context, String[] labels) {
        Spinner spinner = new Spinner(context);
        spinner.setMinimumHeight(Ui.dp(context, 48));
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
                context, android.R.layout.simple_spinner_item, labels);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(adapter);
        return spinner;
    }

    private static boolean on(Map<String, Float> values, String key) {
        return value(values, key, 0) >= 0.5f;
    }

    private static float value(
            Map<String, Float> values,
            String key,
            float fallback) {
        Float result = values.get(key);
        return result == null ? fallback : result;
    }

    private static String millis(float seconds) {
        return String.format(java.util.Locale.US, "%.1f ms", seconds * 1000.0f);
    }
}
