package dev.ajuntanaga.io24;

import android.content.Context;

/** Four-band EQ response graph. */
final class EqGraphView extends TraceView {
    EqGraphView(Context context) {
        super(context);
    }

    void setEq(float[] frequencies, float[] gainsDb) {
        setTrace(
                GraphMath.eqCurve(
                        frequencies, gainsDb,
                        Math.max(1, getWidth()), Ui.dp(getContext(), 120)),
                "Four band equalizer response");
    }
}
