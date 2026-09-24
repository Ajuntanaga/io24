package dev.ajuntanaga.io24;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.view.View;

/** Compact accessible input/output level meter. */
final class LevelMeterView extends View {
    private final Paint track = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private float level;

    LevelMeterView(Context context) {
        super(context);
        track.setColor(context.getColor(R.color.line));
        fill.setColor(context.getColor(R.color.accent));
        setMinimumHeight(Ui.dp(context, 12));
        setContentDescription("Signal level 0 percent");
    }

    void setLevel(float value) {
        level = Math.max(0.0f, Math.min(1.0f, value));
        setContentDescription("Signal level " + Math.round(level * 100) + " percent");
        invalidate();
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        int height = resolveSize(Ui.dp(getContext(), 12), heightMeasureSpec);
        setMeasuredDimension(MeasureSpec.getSize(widthMeasureSpec), height);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float radius = getHeight() / 2.0f;
        canvas.drawRoundRect(0, 0, getWidth(), getHeight(), radius, radius, track);
        canvas.drawRoundRect(0, 0, getWidth() * level, getHeight(), radius, radius, fill);
    }
}
