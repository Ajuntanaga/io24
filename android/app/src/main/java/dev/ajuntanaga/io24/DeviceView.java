package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.content.Context;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;

/** Device settings, sample-rate safety, and protocol diagnostics. */
@SuppressLint("SetTextI18n")
final class DeviceView implements ControllerView {
    private final View root;
    private final CommandSink sink;
    private final Spinner sampleRate;
    private final TextView rateNote;
    private final Spinner delayBus;
    private final ParameterSlider outputDelay;
    private final Spinner phoneSource;
    private final Switch muteSync;
    private final TextView hardwareMute;
    private final TextView diagnostics;
    private final Button refresh;
    private final Runnable refreshAction;
    private boolean rendering;

    DeviceView(Context context, CommandSink sink, Runnable refreshAction) {
        this.sink = sink;
        this.refreshAction = refreshAction;
        LinearLayout content = Ui.column(context);
        content.setPadding(Ui.dp(context, 16), Ui.dp(context, 12),
                Ui.dp(context, 16), Ui.dp(context, 24));
        content.addView(Ui.title(context, "Device"), Ui.match());
        content.addView(Ui.caption(context,
                "Hardware settings and exact connection evidence."),
                Ui.spaced(context));

        LinearLayout clock = Ui.panel(context);
        clock.addView(Ui.section(context, "Sample rate"), Ui.match());
        sampleRate = spinner(context,
                new String[] {"Confirm current audio rate…", "44.1 kHz",
                        "48 kHz", "88.2 kHz", "96 kHz"});
        sampleRate.setContentDescription("Current session sample rate");
        sampleRate.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                if (!rendering) {
                    if (position > 0) {
                        sink.dispatch(Io24Command.setSampleRate(
                                new int[] {44_100, 48_000, 88_200, 96_000}[
                                        position - 1]));
                    }
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        clock.addView(sampleRate, Ui.match());
        rateNote = Ui.caption(context,
                "Android does not expose the USB audio clock here. Confirm the current rate after your audio app opens the io24; scenes cannot confirm it.");
        clock.addView(rateNote, Ui.spaced(context));
        content.addView(clock, Ui.spaced(context));

        LinearLayout delay = Ui.panel(context);
        delay.addView(Ui.section(context, "Output alignment"), Ui.match());
        delayBus = spinner(context,
                new String[] {"Off", "None", "Mix A", "Mix B"});
        delayBus.setContentDescription("Output delay bus");
        delayBus.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                if (!rendering) {
                    sink.dispatch(Io24Command.setOutputDelayBus(
                            new int[] {-1, 0, 1, 2}[position]));
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        delay.addView(delayBus, Ui.match());
        outputDelay = new ParameterSlider(
                context, "Delay", 0, 0.5f, 250,
                ParameterSlider.Scale.LINEAR,
                value -> String.format(java.util.Locale.US,
                        "%.0f ms", value * 1000.0f));
        outputDelay.setListener((value, committed) -> {
            if (committed && !rendering) {
                sink.dispatch(Io24Command.setOutputDelay(value));
            }
        });
        delay.addView(outputDelay, Ui.spaced(context));
        content.addView(delay, Ui.spaced(context));

        LinearLayout behavior = Ui.panel(context);
        behavior.addView(Ui.section(context, "Monitor behavior"), Ui.match());
        phoneSource = spinner(context, new String[] {"Headphones: Main",
                "Headphones: Mix A", "Headphones: Mix B"});
        phoneSource.setContentDescription("Headphone source");
        phoneSource.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                if (!rendering) {
                    sink.dispatch(Io24Command.setPhoneSource(
                            Io24State.PhoneSource.values()[position]));
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        behavior.addView(phoneSource, Ui.match());
        muteSync = Ui.toggle(context, "Channel mute affects every mix");
        muteSync.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setMuteSync(checked));
            }
        });
        behavior.addView(muteSync, Ui.spaced(context));
        hardwareMute = Ui.label(context, "Front-panel Main mute: not active");
        behavior.addView(hardwareMute, Ui.spaced(context));
        behavior.addView(Ui.caption(context,
                "The front-panel Main mute latch is readable but is not writable over the proven io24 protocol."),
                Ui.spaced(context));
        content.addView(behavior, Ui.spaced(context));

        LinearLayout evidence = Ui.panel(context);
        evidence.addView(Ui.section(context, "Connection"), Ui.match());
        diagnostics = Ui.caption(context, "Not connected");
        diagnostics.setTextIsSelectable(true);
        evidence.addView(diagnostics, Ui.match());
        refresh = Ui.button(context, "Refresh device state");
        refresh.setOnClickListener(view -> this.refreshAction.run());
        evidence.addView(refresh, Ui.spaced(context));
        content.addView(evidence, Ui.spaced(context));
        root = Ui.scroll(context, content);
    }

    @Override
    public View view() {
        return root;
    }

    @Override
    public void render(Io24State state) {
        boolean enabled = state.connectionStatus()
                == Io24State.ConnectionStatus.CONNECTED && !state.busy();
        rendering = true;
        sampleRate.setSelection(state.sampleRateConfirmed()
                ? ratePosition(state.sampleRateHz()) + 1 : 0, false);
        int delayValue = Math.round(value(
                state, "output_delay_bus", 0));
        delayBus.setSelection(delayPosition(delayValue), false);
        outputDelay.setValue(state.outputDelaySeconds());
        phoneSource.setSelection(state.phoneSource().ordinal(), false);
        muteSync.setChecked(value(state, "mute_sync", 0) >= 0.5f);
        boolean mainMuted = value(state, "main_hardware_muted", 0) >= 0.5f;
        hardwareMute.setText("Front-panel Main mute: "
                + (mainMuted ? "Active" : "Not active"));
        hardwareMute.setTextColor(getColor(
                hardwareMute, mainMuted ? R.color.warning : R.color.text_primary));
        diagnostics.setText(diagnostics(state));
        if (!state.sampleRateConfirmed()) {
            rateNote.setText(
                    "Before an app opens or changes the io24 above 48 kHz, turn Delay off. Then confirm its rate here; this app cannot observe Android's USB audio clock.");
            rateNote.setTextColor(getColor(rateNote, R.color.warning));
        } else if (state.sampleRateHz() > Io24State.DELAY_NATIVE_MAX_RATE_HZ) {
            rateNote.setText(
                    "High-rate safety is active. Native Delay model 5 stays off.");
            rateNote.setTextColor(getColor(rateNote, R.color.warning));
        } else {
            rateNote.setText(
                    "Confirmed. Device Delay remains off until you turn it on. Turn it off before another app changes the audio clock.");
            rateNote.setTextColor(getColor(rateNote, R.color.text_secondary));
        }
        rendering = false;
        sampleRate.setEnabled(enabled);
        delayBus.setEnabled(enabled);
        Ui.enabledTree(outputDelay, enabled);
        phoneSource.setEnabled(enabled);
        muteSync.setEnabled(enabled);
        refresh.setEnabled(enabled);
    }

    private static String diagnostics(Io24State state) {
        if (state.connectionStatus() != Io24State.ConnectionStatus.CONNECTED) {
            return state.statusMessage();
        }
        return (state.simulated() ? "Emulator test device" : "Revelator io24")
                + "\nProtocol: " + state.protocolVersion()
                + "\nCommand limit: " + state.maxCommandLength() + " B"
                + "\nResponse limit: " + state.maxResponseLength() + " B"
                + "\nState slots: " + state.stateSlotCount()
                + "\nLast result: " + state.lastProof();
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

    private static int ratePosition(int rate) {
        if (rate == 44_100) {
            return 0;
        }
        if (rate == 88_200) {
            return 2;
        }
        if (rate == 96_000) {
            return 3;
        }
        return 1;
    }

    private static int delayPosition(int value) {
        switch (value) {
            case -1:
                return 0;
            case 1:
                return 2;
            case 2:
                return 3;
            default:
                return 1;
        }
    }

    private static float value(Io24State state, String key, float fallback) {
        Float value = state.processing(1).get(key);
        return value == null ? fallback : value;
    }

    private static int getColor(View view, int resource) {
        return view.getContext().getColor(resource);
    }
}
