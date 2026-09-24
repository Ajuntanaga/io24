package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.content.Context;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;

/** One physical preamp strip with safe native controls. */
@SuppressLint({"ViewConstructor", "SetTextI18n"})
final class InputStripView extends LinearLayout {
    private final int channel;
    private final CommandSink sink;
    private final LevelMeterView meter;
    private final TextView gainValue;
    private final SeekBar gain;
    private final Switch phantom;
    private final Switch highPass;
    private final Switch mute;
    private final TextView fxMixValue;
    private final SeekBar fxMix;
    private boolean rendering;

    InputStripView(Context context, int channel, CommandSink sink) {
        super(context);
        this.channel = channel;
        this.sink = sink;
        setOrientation(VERTICAL);
        setPadding(Ui.dp(context, 12), Ui.dp(context, 12),
                Ui.dp(context, 12), Ui.dp(context, 12));
        setBackground(Ui.panel(context, R.color.surface_1, 12));

        TextView title = Ui.section(context, "Input " + channel);
        addView(title, Ui.match());
        meter = new LevelMeterView(context);
        addView(meter, Ui.spaced(context));

        gainValue = Ui.label(context, "Gain 0.0 dB");
        addView(gainValue, Ui.spaced(context));
        gain = Ui.seek(context, 120);
        gain.setContentDescription("Input " + channel + " gain");
        gain.setOnSeekBarChangeListener(onStop(
                value -> sink.dispatch(Io24Command.setGain(channel, value / 2.0f)),
                value -> gainValue.setText("Gain " + Ui.db(value / 2.0f))));
        addView(gain, Ui.match());

        LinearLayout toggles = Ui.row(context);
        phantom = Ui.toggle(context, "48V");
        phantom.setContentDescription("Input " + channel + " phantom power");
        phantom.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setPhantom(channel, checked));
            }
        });
        toggles.addView(phantom, Ui.weight(1));
        highPass = Ui.toggle(context, "80 Hz");
        highPass.setContentDescription("Input " + channel + " fixed high pass");
        highPass.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setHighPass(channel, checked));
            }
        });
        toggles.addView(highPass, Ui.weight(1));
        mute = Ui.toggle(context, "Mute");
        mute.setContentDescription("Input " + channel + " mute");
        mute.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setInputMute(channel, checked));
            }
        });
        toggles.addView(mute, Ui.weight(1));
        addView(toggles, Ui.match());

        fxMixValue = Ui.label(context, "Processing 100%");
        addView(fxMixValue, Ui.spaced(context));
        fxMix = Ui.seek(context, 100);
        fxMix.setContentDescription("Input " + channel + " processing mix");
        fxMix.setOnSeekBarChangeListener(onStop(
                value -> sink.dispatch(Io24Command.setFxMix(channel, value / 100.0f)),
                value -> fxMixValue.setText("Processing " + value + "%")));
        addView(fxMix, Ui.match());
    }

    void render(Io24State state, boolean enabled) {
        rendering = true;
        Io24State.Input input = state.input(channel);
        gain.setProgress(Math.round(input.gainDb() * 2.0f));
        gainValue.setText("Gain " + Ui.db(input.gainDb()));
        phantom.setChecked(input.phantom());
        highPass.setChecked(input.highPass());
        mute.setChecked(input.muted());
        fxMix.setProgress(Math.round(input.fxMix() * 100.0f));
        fxMixValue.setText("Processing " + Ui.percent(input.fxMix()));
        meter.setLevel(input.level());
        rendering = false;
        Ui.enabledTree(this, enabled);
    }

    private SeekBar.OnSeekBarChangeListener onStop(
            IntAction stopped,
            IntAction changed) {
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

    private interface IntAction {
        void run(int value);
    }
}
