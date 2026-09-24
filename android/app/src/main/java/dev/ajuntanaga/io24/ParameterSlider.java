package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.content.Context;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.TextView;

/** Labelled float slider with linear or logarithmic mapping and stop commits. */
@SuppressLint({"ViewConstructor", "SetTextI18n"})
final class ParameterSlider extends LinearLayout {
    enum Scale {
        LINEAR,
        LOG
    }

    interface Formatter {
        String format(float value);
    }

    interface Listener {
        void changed(float value, boolean committed);
    }

    private final String name;
    private final float min;
    private final float max;
    private final Scale scale;
    private final Formatter formatter;
    private final TextView valueLabel;
    private final SeekBar seek;
    private Listener listener;
    private boolean rendering;

    ParameterSlider(
            Context context,
            String name,
            float min,
            float max,
            int steps,
            Scale scale,
            Formatter formatter) {
        super(context);
        if (!(max > min) || steps < 1) {
            throw new IllegalArgumentException("Slider requires an increasing range");
        }
        this.name = name;
        this.min = min;
        this.max = max;
        this.scale = scale;
        this.formatter = formatter;
        setOrientation(VERTICAL);
        valueLabel = Ui.label(context, name + " " + formatter.format(min));
        addView(valueLabel, Ui.match());
        seek = Ui.seek(context, steps);
        seek.setContentDescription(name);
        seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(
                    SeekBar seekBar,
                    int progress,
                    boolean fromUser) {
                float value = valueFromProgress(progress);
                valueLabel.setText(name + " " + formatter.format(value));
                if (fromUser && listener != null) {
                    listener.changed(value, false);
                }
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {
            }

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {
                if (!rendering && listener != null) {
                    listener.changed(value(), true);
                }
            }
        });
        addView(seek, Ui.match());
    }

    void setListener(Listener value) {
        listener = value;
    }

    void setValue(float value) {
        rendering = true;
        seek.setProgress(progressFromValue(value));
        valueLabel.setText(name + " " + formatter.format(value()));
        rendering = false;
    }

    float value() {
        return valueFromProgress(seek.getProgress());
    }

    private float valueFromProgress(int progress) {
        float normalized = progress / (float) seek.getMax();
        if (scale == Scale.LOG) {
            double low = Math.log(min);
            return (float) Math.exp(low + normalized * (Math.log(max) - low));
        }
        return min + normalized * (max - min);
    }

    private int progressFromValue(float value) {
        float clamped = Math.max(min, Math.min(max, value));
        double normalized;
        if (scale == Scale.LOG) {
            normalized = (Math.log(clamped) - Math.log(min))
                    / (Math.log(max) - Math.log(min));
        } else {
            normalized = (clamped - min) / (max - min);
        }
        return (int) Math.round(normalized * seek.getMax());
    }
}
