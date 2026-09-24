package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.content.Context;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;

/** Voice FX racks and the independent shared device reverb. */
@SuppressLint("SetTextI18n")
final class EffectsView implements ControllerView {
    private final Context context;
    private final CommandSink sink;
    private final View root;
    private final Spinner inputSelector;
    private final Spinner modelSelector;
    private final TextView placement;
    private final LinearLayout rackContainer;
    private final Switch reverbOn;
    private final ParameterSlider reverbSize;
    private final ParameterSlider reverbMix;
    private final ParameterSlider reverbHighPass;
    private final ParameterSlider reverbPreDelay;
    private Io24State lastState = Io24State.defaults();
    private Io24State.VoiceFxModel selectedModel =
            Io24State.VoiceFxModel.TRANSFORMER;
    private EffectRackView rack;
    private boolean rendering;
    private boolean modelTouched;

    EffectsView(Context context, CommandSink sink) {
        this.context = context;
        this.sink = sink;
        LinearLayout content = Ui.column(context);
        content.setPadding(Ui.dp(context, 16), Ui.dp(context, 12),
                Ui.dp(context, 16), Ui.dp(context, 24));
        content.addView(Ui.title(context, "Effects"), Ui.match());
        content.addView(Ui.caption(context,
                "One Voice FX rack can be assigned to either input. Turning one model on turns every other model off."),
                Ui.spaced(context));

        LinearLayout assignment = Ui.panel(context);
        assignment.addView(Ui.section(context, "Voice FX assignment"), Ui.match());
        inputSelector = spinner(context, new String[] {"Input 1", "Input 2"});
        inputSelector.setContentDescription("Voice FX input assignment");
        inputSelector.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                if (!rendering) {
                    sink.dispatch(Io24Command.setVoiceFxInput(position + 1));
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        assignment.addView(inputSelector, Ui.match());
        modelSelector = spinner(context, modelLabels());
        modelSelector.setContentDescription("Voice FX model");
        modelSelector.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                Io24State.VoiceFxModel next =
                        Io24State.VoiceFxModel.values()[position];
                if (rendering) {
                    return;
                }
                modelTouched = true;
                selectedModel = next;
                rebuildRack();
                rack.render(lastState, connected(lastState)
                        && !(next == Io24State.VoiceFxModel.DELAY
                        && (!lastState.sampleRateConfirmed()
                        || lastState.sampleRateHz()
                        > Io24State.DELAY_NATIVE_MAX_RATE_HZ)));
                updatePlacement();
                sink.dispatch(Io24Command.setVoiceFxModel(next));
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        assignment.addView(modelSelector, Ui.spaced(context));
        placement = Ui.caption(context, "Runs in the io24 at 48 kHz");
        placement.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        assignment.addView(placement, Ui.spaced(context));
        content.addView(assignment, Ui.spaced(context));

        rackContainer = Ui.column(context);
        content.addView(rackContainer, Ui.spaced(context));
        rebuildRack();

        LinearLayout reverb = Ui.panel(context);
        reverb.addView(Ui.section(context, "Device reverb"), Ui.match());
        reverb.addView(Ui.caption(context,
                "The io24's shared native reverb (block 202)."),
                Ui.match());
        reverbOn = Ui.toggle(context, "On");
        reverbOn.setContentDescription("Shared device reverb power");
        reverbOn.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sendReverb();
            }
        });
        reverb.addView(reverbOn, Ui.spaced(context));
        reverbSize = reverbSlider(
                context, reverb, "Room size", 0, 1, 100,
                ParameterSlider.Scale.LINEAR, Ui::percent);
        reverbMix = reverbSlider(
                context, reverb, "Wet return", 0, 1, 100,
                ParameterSlider.Scale.LINEAR, Ui::percent);
        reverbHighPass = reverbSlider(
                context, reverb, "Input high-pass", 0, 500, 250,
                ParameterSlider.Scale.LINEAR, Ui::hz);
        reverbPreDelay = reverbSlider(
                context, reverb, "Pre-delay", 0.0001f, 0.25f, 250,
                ParameterSlider.Scale.LINEAR,
                value -> String.format(java.util.Locale.US,
                        "%.1f ms", value * 1000.0f));
        content.addView(reverb, Ui.spaced(context));
        root = Ui.scroll(context, content);
    }

    @Override
    public View view() {
        return root;
    }

    @Override
    public void render(Io24State state) {
        lastState = state;
        boolean enabled = connected(state);
        if (!modelTouched) {
            selectedModel = state.selectedVoiceFx();
        }
        boolean delaySafe = selectedModel != Io24State.VoiceFxModel.DELAY
                || state.sampleRateConfirmed()
                && state.sampleRateHz() <= Io24State.DELAY_NATIVE_MAX_RATE_HZ;
        rendering = true;
        inputSelector.setSelection(state.voiceFxInput() - 1, false);
        modelSelector.setSelection(selectedModel.ordinal(), false);
        inputSelector.setEnabled(enabled);
        modelSelector.setEnabled(enabled);
        rack.render(state, enabled && delaySafe);
        Io24State.ReverbState current = state.reverb();
        reverbOn.setChecked(current.on());
        reverbSize.setValue(current.size());
        reverbMix.setValue(current.mix());
        reverbHighPass.setValue(current.highPassHz());
        reverbPreDelay.setValue(current.preDelaySeconds());
        rendering = false;
        reverbOn.setEnabled(enabled);
        for (ParameterSlider slider : new ParameterSlider[] {
                reverbSize, reverbMix, reverbHighPass, reverbPreDelay}) {
            Ui.enabledTree(slider, enabled);
        }
        updatePlacement();
    }

    private void rebuildRack() {
        rackContainer.removeAllViews();
        rack = new EffectRackView(context, selectedModel, sink);
        rackContainer.addView(rack, Ui.match());
    }

    private ParameterSlider reverbSlider(
            Context context,
            LinearLayout parent,
            String label,
            float min,
            float max,
            int steps,
            ParameterSlider.Scale scale,
            ParameterSlider.Formatter formatter) {
        ParameterSlider result = new ParameterSlider(
                context, label, min, max, steps, scale, formatter);
        result.setListener((value, committed) -> {
            if (committed && !rendering) {
                sendReverb();
            }
        });
        parent.addView(result, Ui.spaced(context));
        return result;
    }

    private void sendReverb() {
        sink.dispatch(Io24Command.setReverb(
                reverbOn.isChecked(),
                reverbSize.value(),
                reverbMix.value(),
                reverbHighPass.value(),
                reverbPreDelay.value()));
    }

    private void updatePlacement() {
        if (selectedModel == Io24State.VoiceFxModel.DELAY
                && !lastState.sampleRateConfirmed()) {
            placement.setText(
                    "Confirm the current audio rate on Device. Delay is kept on this phone and hardware Voice FX stays off.");
            placement.setTextColor(context.getColor(R.color.warning));
        } else if (selectedModel == Io24State.VoiceFxModel.DELAY
                && lastState.sampleRateHz()
                > Io24State.DELAY_NATIVE_MAX_RATE_HZ) {
            placement.setText(
                    "Unavailable safely above 48 kHz. Device model 5 remains off.");
            placement.setTextColor(context.getColor(R.color.warning));
        } else {
            placement.setText("Runs in the io24 at "
                    + (lastState.sampleRateHz() / 1000.0f) + " kHz");
            placement.setTextColor(context.getColor(R.color.text_secondary));
        }
    }

    private static boolean connected(Io24State state) {
        return state.connectionStatus() == Io24State.ConnectionStatus.CONNECTED
                && !state.busy();
    }

    private static Spinner spinner(Context context, String[] labels) {
        Spinner result = new Spinner(context);
        result.setMinimumHeight(Ui.dp(context, 48));
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
                context, android.R.layout.simple_spinner_item, labels);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        result.setAdapter(adapter);
        return result;
    }

    private static String[] modelLabels() {
        Io24State.VoiceFxModel[] models = Io24State.VoiceFxModel.values();
        String[] result = new String[models.length];
        for (int index = 0; index < models.length; index++) {
            result[index] = models[index].label();
        }
        return result;
    }
}
