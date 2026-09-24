package dev.ajuntanaga.io24;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;

import java.util.Locale;

/** Small platform-view design system shared by every app destination. */
final class Ui {
    private Ui() {
    }

    static int dp(Context context, int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }

    static LinearLayout column(Context context) {
        LinearLayout result = new LinearLayout(context);
        result.setOrientation(LinearLayout.VERTICAL);
        return result;
    }

    static LinearLayout row(Context context) {
        LinearLayout result = new LinearLayout(context);
        result.setOrientation(LinearLayout.HORIZONTAL);
        result.setGravity(Gravity.CENTER_VERTICAL);
        return result;
    }

    static ScrollView scroll(Context context, View content) {
        ScrollView result = new ScrollView(context);
        result.setFillViewport(true);
        result.setClipToPadding(false);
        result.setSmoothScrollingEnabled(true);
        result.addView(content, match());
        return result;
    }

    static TextView title(Context context, CharSequence text) {
        TextView view = text(context, text, 26, true);
        if (Build.VERSION.SDK_INT >= 28) {
            view.setAccessibilityHeading(true);
        }
        return view;
    }

    static TextView section(Context context, CharSequence text) {
        TextView view = text(context, text, 18, true);
        view.setPadding(0, dp(context, 8), 0, dp(context, 8));
        if (Build.VERSION.SDK_INT >= 28) {
            view.setAccessibilityHeading(true);
        }
        return view;
    }

    static TextView label(Context context, CharSequence text) {
        return text(context, text, 14, false);
    }

    static TextView caption(Context context, CharSequence text) {
        TextView view = text(context, text, 12, false);
        view.setTextColor(context.getColor(R.color.text_secondary));
        return view;
    }

    static TextView text(
            Context context,
            CharSequence text,
            int sizeSp,
            boolean strong) {
        TextView view = new TextView(context);
        view.setText(text);
        view.setTextSize(sizeSp);
        view.setTextColor(context.getColor(R.color.text_primary));
        view.setLineSpacing(0, 1.1f);
        if (strong) {
            view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        }
        return view;
    }

    static Button button(Context context, CharSequence text) {
        Button button = new Button(context);
        button.setText(text);
        button.setTextSize(12);
        button.setTextColor(context.getColor(R.color.text_primary));
        button.setMinHeight(dp(context, 48));
        button.setMinWidth(dp(context, 48));
        button.setAllCaps(false);
        button.setBackground(panel(context, R.color.surface_2, 10));
        return button;
    }

    @SuppressWarnings("deprecation")
    static Switch toggle(Context context, CharSequence text) {
        Switch toggle = new Switch(context);
        toggle.setText(text);
        toggle.setTextSize(14);
        toggle.setTextColor(context.getColor(R.color.text_primary));
        toggle.setMinHeight(dp(context, 48));
        ColorStateList tint = new ColorStateList(
                new int[][] {
                        new int[] {android.R.attr.state_checked},
                        new int[] {}
                },
                new int[] {
                        context.getColor(R.color.accent),
                        context.getColor(R.color.line)
                });
        toggle.setThumbTintList(tint);
        toggle.setTrackTintList(new ColorStateList(
                new int[][] {
                        new int[] {android.R.attr.state_checked},
                        new int[] {}
                },
                new int[] {
                        context.getColor(R.color.accent_dark),
                        context.getColor(R.color.surface_2)
                }));
        return toggle;
    }

    static SeekBar seek(Context context, int max) {
        SeekBar seek = new SeekBar(context);
        seek.setMax(max);
        seek.setMinimumHeight(dp(context, 48));
        seek.setProgressTintList(ColorStateList.valueOf(
                context.getColor(R.color.accent)));
        seek.setThumbTintList(ColorStateList.valueOf(
                context.getColor(R.color.accent)));
        return seek;
    }

    static LinearLayout panel(Context context) {
        LinearLayout panel = column(context);
        panel.setPadding(
                dp(context, 12),
                dp(context, 12),
                dp(context, 12),
                dp(context, 12));
        panel.setBackground(panel(context, R.color.surface_1, 12));
        return panel;
    }

    static GradientDrawable panel(Context context, int color, int radiusDp) {
        GradientDrawable background = new GradientDrawable();
        background.setColor(context.getColor(color));
        background.setCornerRadius(dp(context, radiusDp));
        return background;
    }

    static LinearLayout.LayoutParams match() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    static LinearLayout.LayoutParams weight(float value) {
        return new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, value);
    }

    static LinearLayout.LayoutParams spaced(Context context) {
        LinearLayout.LayoutParams params = match();
        params.topMargin = dp(context, 8);
        return params;
    }

    static String db(float value) {
        return String.format(Locale.US, "%+.1f dB", value);
    }

    static String percent(float value) {
        return String.format(Locale.US, "%d%%", Math.round(value * 100.0f));
    }

    static String hz(float value) {
        if (value >= 1000.0f) {
            return String.format(Locale.US, "%.1f kHz", value / 1000.0f);
        }
        return String.format(Locale.US, "%d Hz", Math.round(value));
    }

    static void enabledTree(View view, boolean enabled) {
        view.setEnabled(enabled);
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int index = 0; index < group.getChildCount(); index++) {
                enabledTree(group.getChildAt(index), enabled);
            }
        }
    }
}
