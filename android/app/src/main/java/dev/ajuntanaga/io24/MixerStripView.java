package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.content.Context;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;

/** One source row for the selected Main/Mix A/Mix B bus. */
@SuppressLint("ViewConstructor")
final class MixerStripView extends LinearLayout {
    private final Io24State.Source source;
    private final CommandSink sink;
    private final TextView levelValue;
    private final SeekBar level;
    private final Switch assigned;
    private final Switch mute;
    private final Switch solo;
    private Io24State.Bus bus = Io24State.Bus.MAIN;
    private boolean rendering;

    MixerStripView(Context context, Io24State.Source source, CommandSink sink) {
        super(context);
        this.source = source;
        this.sink = sink;
        setOrientation(VERTICAL);
        setPadding(0, Ui.dp(context, 8), 0, Ui.dp(context, 8));

        LinearLayout heading = Ui.row(context);
        heading.addView(Ui.label(context, source.label()), Ui.weight(1));
        assigned = Ui.toggle(context, "Assign");
        assigned.setContentDescription(source.label() + " bus assignment");
        assigned.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setMixerAssigned(source, bus, checked));
            }
        });
        heading.addView(assigned, Ui.weight(1));
        addView(heading, Ui.match());

        levelValue = Ui.caption(context, "0.0 dB");
        addView(levelValue, Ui.match());
        level = Ui.seek(context, 140);
        level.setContentDescription(source.label() + " level");
        level.setOnSeekBarChangeListener(listener(
                value -> levelValue.setText(Ui.db(value / 2.0f - 60.0f)),
                value -> sink.dispatch(Io24Command.setMixerSend(
                        source, bus, value / 2.0f - 60.0f))));
        addView(level, Ui.match());

        LinearLayout flags = Ui.row(context);
        mute = Ui.toggle(context, "Mute");
        mute.setContentDescription(source.label() + " mute in every mix");
        mute.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setMixerMute(source, checked));
            }
        });
        flags.addView(mute, Ui.weight(1));
        solo = Ui.toggle(context, "Solo");
        solo.setContentDescription(source.label() + " solo in " + bus.label());
        solo.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setMixerSolo(source, bus, checked));
            }
        });
        flags.addView(solo, Ui.weight(1));
        addView(flags, Ui.match());
    }

    void render(Io24State state, Io24State.Bus selectedBus, boolean enabled) {
        bus = selectedBus;
        rendering = true;
        Io24State.Send send = state.send(source, bus);
        level.setProgress(Math.round((send.db() + 60.0f) * 2.0f));
        levelValue.setText(Ui.db(send.db()));
        assigned.setChecked(send.assigned());
        mute.setChecked(send.muted());
        solo.setChecked(send.soloed());
        solo.setContentDescription(source.label() + " solo in " + bus.label());
        rendering = false;
        Ui.enabledTree(this, enabled);
    }

    private SeekBar.OnSeekBarChangeListener listener(
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

    private interface IntAction {
        void run(int value);
    }
}
