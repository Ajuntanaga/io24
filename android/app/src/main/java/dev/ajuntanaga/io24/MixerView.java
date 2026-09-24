package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.content.Context;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;

import java.util.EnumMap;

/** Mixer, routing, preamps, monitoring, and output controls. */
@SuppressLint("SetTextI18n")
final class MixerView implements ControllerView {
    private final View root;
    private final InputStripView input1;
    private final InputStripView input2;
    private final Switch linked;
    private final TextView mainVolumeValue;
    private final SeekBar mainVolume;
    private final TextView headphoneVolumeValue;
    private final SeekBar headphoneVolume;
    private final Switch headphoneMute;
    private final TextView monitorValue;
    private final SeekBar monitor;
    private final Spinner busSelector;
    private final TextView busMasterValue;
    private final SeekBar busMaster;
    private final Switch busMute;
    private final Button mirrorMain;
    private final EnumMap<Io24State.Source, MixerStripView> strips =
            new EnumMap<>(Io24State.Source.class);
    private final CommandSink sink;
    private Io24State.Bus selectedBus = Io24State.Bus.MAIN;
    private Io24State lastState = Io24State.defaults();
    private boolean rendering;

    MixerView(Context context, CommandSink sink) {
        this.sink = sink;
        LinearLayout content = Ui.column(context);
        content.setPadding(Ui.dp(context, 16), Ui.dp(context, 12),
                Ui.dp(context, 16), Ui.dp(context, 24));
        content.addView(Ui.title(context, "Mixer"), Ui.match());
        TextView intro = Ui.caption(context,
                "Preamps, monitor blend, and all Main / Mix A / Mix B routes.");
        content.addView(intro, Ui.spaced(context));

        input1 = new InputStripView(context, 1, sink);
        content.addView(input1, Ui.spaced(context));
        input2 = new InputStripView(context, 2, sink);
        content.addView(input2, Ui.spaced(context));
        linked = Ui.toggle(context, "Link inputs 1–2");
        linked.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setLinked(checked));
            }
        });
        content.addView(linked, Ui.spaced(context));

        LinearLayout monitorPanel = Ui.panel(context);
        monitorPanel.addView(Ui.section(context, "Monitoring"), Ui.match());
        mainVolumeValue = Ui.label(context, "Main 75%");
        monitorPanel.addView(mainVolumeValue, Ui.match());
        mainVolume = Ui.seek(context, 100);
        mainVolume.setContentDescription("Main output volume");
        mainVolume.setOnSeekBarChangeListener(seek(
                value -> mainVolumeValue.setText("Main " + value + "%"),
                value -> sink.dispatch(Io24Command.setMainVolume(value / 100.0f))));
        monitorPanel.addView(mainVolume, Ui.match());

        headphoneVolumeValue = Ui.label(context, "Headphones 75%");
        monitorPanel.addView(headphoneVolumeValue, Ui.spaced(context));
        headphoneVolume = Ui.seek(context, 100);
        headphoneVolume.setContentDescription("Headphone output volume");
        headphoneVolume.setOnSeekBarChangeListener(seek(
                value -> headphoneVolumeValue.setText("Headphones " + value + "%"),
                value -> sink.dispatch(
                        Io24Command.setHeadphoneVolume(value / 100.0f))));
        monitorPanel.addView(headphoneVolume, Ui.match());
        headphoneMute = Ui.toggle(context, "Mute headphones");
        headphoneMute.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setHeadphoneMute(checked));
            }
        });
        monitorPanel.addView(headphoneMute, Ui.match());

        monitorValue = Ui.label(context, "Monitor blend: center");
        monitorPanel.addView(monitorValue, Ui.spaced(context));
        monitor = Ui.seek(context, 200);
        monitor.setProgress(100);
        monitor.setContentDescription("Monitor input playback blend");
        monitor.setOnSeekBarChangeListener(seek(
                value -> monitorValue.setText(blendText(value / 100.0f - 1.0f)),
                value -> sink.dispatch(
                        Io24Command.setMonitorBlend(value / 100.0f - 1.0f))));
        monitorPanel.addView(monitor, Ui.match());
        content.addView(monitorPanel, Ui.spaced(context));

        LinearLayout routes = Ui.panel(context);
        routes.addView(Ui.section(context, "Routing"), Ui.match());
        busSelector = new Spinner(context);
        busSelector.setContentDescription("Selected mixer bus");
        busSelector.setMinimumHeight(Ui.dp(context, 48));
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
                context,
                android.R.layout.simple_spinner_item,
                new String[] {"Main", "Mix A", "Mix B"});
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        busSelector.setAdapter(adapter);
        busSelector.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                selectedBus = Io24State.Bus.values()[position];
                render(lastState);
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        routes.addView(busSelector, Ui.match());

        busMasterValue = Ui.label(context, "Bus master +0.0 dB");
        routes.addView(busMasterValue, Ui.spaced(context));
        busMaster = Ui.seek(context, 106);
        busMaster.setProgress(96);
        busMaster.setContentDescription("Selected bus master trim");
        busMaster.setOnSeekBarChangeListener(seek(
                value -> busMasterValue.setText(
                        "Bus master " + Ui.db(value - 96.0f)),
                value -> sink.dispatch(Io24Command.setBusMaster(
                        selectedBus, value - 96.0f))));
        routes.addView(busMaster, Ui.match());
        LinearLayout busFlags = Ui.row(context);
        busMute = Ui.toggle(context, "Mute bus");
        busMute.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setBusMute(selectedBus, checked));
            }
        });
        busFlags.addView(busMute, Ui.weight(1));
        mirrorMain = Ui.button(context, "Copy Main");
        mirrorMain.setContentDescription("Copy current Main mix levels to selected mix");
        mirrorMain.setOnClickListener(button -> {
            if (!rendering && selectedBus != Io24State.Bus.MAIN) {
                sink.dispatch(Io24Command.setMirrorMain(selectedBus, true));
            }
        });
        busFlags.addView(mirrorMain, Ui.weight(1));
        routes.addView(busFlags, Ui.match());

        for (Io24State.Source source : Io24State.Source.values()) {
            MixerStripView strip = new MixerStripView(context, source, sink);
            strips.put(source, strip);
            routes.addView(strip, Ui.spaced(context));
        }
        content.addView(routes, Ui.spaced(context));
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
        rendering = true;
        input1.render(state, enabled);
        input2.render(state, enabled);
        linked.setChecked(state.linked());
        linked.setEnabled(enabled);
        mainVolume.setProgress(Math.round(state.mainVolume() * 100.0f));
        mainVolumeValue.setText("Main " + Ui.percent(state.mainVolume()));
        mainVolume.setEnabled(enabled);
        headphoneVolume.setProgress(Math.round(state.headphoneVolume() * 100.0f));
        headphoneVolumeValue.setText(
                "Headphones " + Ui.percent(state.headphoneVolume()));
        headphoneVolume.setEnabled(enabled);
        headphoneMute.setChecked(state.headphoneMuted());
        headphoneMute.setEnabled(enabled);
        monitor.setProgress(Math.round((state.monitorBlend() + 1.0f) * 100.0f));
        monitorValue.setText(blendText(state.monitorBlend()));
        monitor.setEnabled(enabled);
        Io24State.BusState bus = state.bus(selectedBus);
        busMaster.setProgress(Math.round(bus.masterDb() + 96.0f));
        busMasterValue.setText("Bus master " + Ui.db(bus.masterDb()));
        busMaster.setEnabled(enabled);
        busMute.setChecked(bus.muted());
        busMute.setEnabled(enabled);
        mirrorMain.setVisibility(selectedBus == Io24State.Bus.MAIN
                ? View.GONE : View.VISIBLE);
        mirrorMain.setEnabled(enabled);
        for (MixerStripView strip : strips.values()) {
            strip.render(state, selectedBus, enabled);
        }
        rendering = false;
    }

    private SeekBar.OnSeekBarChangeListener seek(
            IntAction changed,
            IntAction stopped) {
        return new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(
                    SeekBar seekBar,
                    int progress,
                    boolean fromUser) {
                if (fromUser) {
                    changed.run(progress);
                }
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {
            }

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {
                if (!rendering) {
                    stopped.run(seekBar.getProgress());
                }
            }
        };
    }

    private static String blendText(float value) {
        if (Math.abs(value) < 0.01f) {
            return "Monitor blend: center";
        }
        int percent = Math.round(Math.abs(value) * 100.0f);
        return "Monitor blend: " + percent + "% "
                + (value < 0.0f ? "inputs" : "playback");
    }

    private interface IntAction {
        void run(int value);
    }
}
