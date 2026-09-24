package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.content.Context;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.Switch;
import android.widget.TextView;

import java.util.LinkedHashMap;
import java.util.Map;

/** Exact XML-ordered rack editor for one of the six Voice FX models. */
@SuppressLint({"ViewConstructor", "SetTextI18n"})
final class EffectRackView extends LinearLayout {
    private final Io24State.VoiceFxModel model;
    private final CommandSink sink;
    private final Switch on;
    private final EffectGraphView graph;
    private final Map<String, Float> working = new LinkedHashMap<>();
    private final Map<String, ParameterSlider> sliders = new LinkedHashMap<>();
    private final Map<String, Switch> toggles = new LinkedHashMap<>();
    private final TextView voicedValue;
    private final LevelMeterView voicedMeter;
    private boolean rendering;

    EffectRackView(
            Context context,
            Io24State.VoiceFxModel model,
            CommandSink sink) {
        super(context);
        this.model = model;
        this.sink = sink;
        setOrientation(VERTICAL);
        setPadding(Ui.dp(context, 12), Ui.dp(context, 12),
                Ui.dp(context, 12), Ui.dp(context, 12));
        setBackground(Ui.panel(context, R.color.surface_1, 12));

        LinearLayout header = Ui.row(context);
        header.addView(Ui.section(context, model.label()), Ui.weight(1));
        on = Ui.toggle(context, "On");
        on.setContentDescription(model.label() + " power; enabling it disables other Voice FX models");
        on.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setVoiceFxOn(model, checked));
            }
        });
        header.addView(on, Ui.weight(1));
        addView(header, Ui.match());

        graph = new EffectGraphView(context);
        addView(graph, Ui.spaced(context));

        TextView localVoicedValue = null;
        LevelMeterView localVoicedMeter = null;
        switch (model) {
            case TRANSFORMER:
                addFloat(context, "lows", "Lows", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addFloat(context, "width", "Width", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addWetDry(context);
                break;
            case DETUNER:
                addFloat(context, "detune", "Detune", 0, 8, 8,
                        ParameterSlider.Scale.LINEAR,
                        value -> Integer.toString(Math.round(value) - 8));
                addWetDry(context);
                break;
            case VOCODER:
                addFloat(context, "vol", "Volume", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addFloat(context, "carrier_type", "Carrier", 0, 2, 2,
                        ParameterSlider.Scale.LINEAR,
                        EffectRackView::carrierName);
                addFloat(context, "carrier_freq", "Carrier frequency",
                        50, 500, 225, ParameterSlider.Scale.LOG, Ui::hz);
                localVoicedValue = Ui.label(context, "Voiced signal 0%");
                addView(localVoicedValue, Ui.spaced(context));
                localVoicedMeter = new LevelMeterView(context);
                localVoicedMeter.setContentDescription(
                        "Read-only voiced signal detector");
                addView(localVoicedMeter, Ui.spaced(context));
                addView(Ui.caption(context,
                        "Voiced is a live detector from the effect, not an editable control."),
                        Ui.spaced(context));
                addWetDry(context);
                break;
            case RING_MOD:
                addFloat(context, "carrier_hz", "Frequency",
                        0.1f, 2000, 300, ParameterSlider.Scale.LOG, Ui::hz);
                addToggle(context, "carrier2", "Sub carrier");
                addFloat(context, "carrier2_hz", "Sub carrier frequency",
                        0.1f, 2000, 300, ParameterSlider.Scale.LOG, Ui::hz);
                addFloat(context, "dist", "Distortion", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addFloat(context, "vol", "Volume", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addWetDry(context);
                break;
            case FILTERS:
                addFloat(context, "pitch", "Pitch", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addFloat(context, "regeneration", "Regeneration", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addFloat(context, "damping", "Damping", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addFloat(context, "distortion", "Distortion", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addFloat(context, "volume", "Volume", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addWetDry(context);
                break;
            case DELAY:
                addFloat(context, "time_s", "Time", 0.0001f, 0.25f, 250,
                        ParameterSlider.Scale.LINEAR,
                        value -> String.format(java.util.Locale.US,
                                "%.1f ms", value * 1000.0f));
                addFloat(context, "feedback", "Feedback", 0, 1, 100,
                        ParameterSlider.Scale.LINEAR, Ui::percent);
                addWetDry(context);
                break;
            default:
                throw new IllegalArgumentException("Unknown Voice FX model");
        }
        voicedValue = localVoicedValue;
        voicedMeter = localVoicedMeter;
    }

    void render(Io24State state, boolean enabled) {
        rendering = true;
        Io24State.VoiceFxState effect = state.voiceFx(model);
        working.clear();
        working.putAll(effect.parameters());
        on.setChecked(effect.on());
        on.setEnabled(enabled);
        for (Map.Entry<String, ParameterSlider> entry : sliders.entrySet()) {
            entry.getValue().setValue(working.get(entry.getKey()));
            Ui.enabledTree(entry.getValue(), enabled);
        }
        for (Map.Entry<String, Switch> entry : toggles.entrySet()) {
            entry.getValue().setChecked(working.get(entry.getKey()) >= 0.5f);
            entry.getValue().setEnabled(enabled);
        }
        if (voicedValue != null && voicedMeter != null) {
            float voiced = working.get("voiced");
            voicedValue.setText("Voiced signal " + Ui.percent(voiced));
            voicedMeter.setLevel(voiced);
        }
        graph.setEffect(model, working);
        rendering = false;
    }

    private void addWetDry(Context context) {
        addFloat(context, "mix", "Wet / Dry", 0, 1, 100,
                ParameterSlider.Scale.LINEAR,
                value -> Ui.percent(value) + " wet");
    }

    private void addFloat(
            Context context,
            String key,
            String label,
            float min,
            float max,
            int steps,
            ParameterSlider.Scale scale,
            ParameterSlider.Formatter formatter) {
        ParameterSlider slider = new ParameterSlider(
                context, label, min, max, steps, scale, formatter);
        slider.setListener((value, committed) -> {
            working.put(key, value);
            graph.setEffect(model, working);
            if (committed && !rendering) {
                sink.dispatch(Io24Command.setVoiceFxParameter(model, key, value));
            }
        });
        sliders.put(key, slider);
        addView(slider, Ui.spaced(context));
    }

    private void addToggle(Context context, String key, String label) {
        Switch toggle = Ui.toggle(context, label);
        toggle.setOnCheckedChangeListener((button, checked) -> {
            working.put(key, checked ? 1.0f : 0.0f);
            graph.setEffect(model, working);
            if (!rendering) {
                sink.dispatch(Io24Command.setVoiceFxParameter(
                        model, key, checked ? 1.0f : 0.0f));
            }
        });
        toggles.put(key, toggle);
        addView(toggle, Ui.spaced(context));
    }

    private static String carrierName(float value) {
        switch (Math.round(value)) {
            case 0:
                return "Noise";
            case 1:
                return "Sawtooth";
            default:
                return "Rect";
        }
    }
}
