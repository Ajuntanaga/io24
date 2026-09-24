package dev.ajuntanaga.io24;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

/** Shared restrained rack-display renderer. */
abstract class TraceView extends View {
    private final Paint background = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint grid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tracePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path path = new Path();
    private float[] trace = new float[0];

    TraceView(Context context) {
        super(context);
        background.setColor(context.getColor(R.color.surface_0));
        grid.setColor(context.getColor(R.color.line));
        grid.setStrokeWidth(Ui.dp(context, 1));
        tracePaint.setColor(context.getColor(R.color.accent));
        tracePaint.setStrokeWidth(Ui.dp(context, 2));
        tracePaint.setStyle(Paint.Style.STROKE);
        setMinimumHeight(Ui.dp(context, 120));
    }

    final void setTrace(float[] value, String description) {
        trace = value == null ? new float[0] : value.clone();
        setContentDescription(description);
        invalidate();
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        int desired = Ui.dp(getContext(), 120);
        setMeasuredDimension(
                MeasureSpec.getSize(widthMeasureSpec),
                resolveSize(desired, heightMeasureSpec));
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        canvas.drawRoundRect(
                0, 0, getWidth(), getHeight(),
                Ui.dp(getContext(), 8), Ui.dp(getContext(), 8), background);
        for (int division = 1; division < 4; division++) {
            float x = getWidth() * division / 4.0f;
            float y = getHeight() * division / 4.0f;
            canvas.drawLine(x, 0, x, getHeight(), grid);
            canvas.drawLine(0, y, getWidth(), y, grid);
        }
        if (trace.length < 2) {
            return;
        }
        path.reset();
        for (int index = 0; index < trace.length; index++) {
            float x = getWidth() * index / (trace.length - 1.0f);
            float y = Math.max(0.0f, Math.min(getHeight(), trace[index]));
            if (index == 0) {
                path.moveTo(x, y);
            } else {
                path.lineTo(x, y);
            }
        }
        canvas.drawPath(path, tracePaint);
    }
}
