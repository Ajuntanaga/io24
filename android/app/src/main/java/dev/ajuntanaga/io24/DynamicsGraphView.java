package dev.ajuntanaga.io24;

import android.content.Context;

/** Compressor transfer curve. */
final class DynamicsGraphView extends TraceView {
    DynamicsGraphView(Context context) {
        super(context);
    }

    void setDynamics(float thresholdDb, float ratio, float makeupDb) {
        setTrace(
                GraphMath.dynamicsCurve(
                        thresholdDb, ratio, makeupDb,
                        Math.max(1, getWidth()), Ui.dp(getContext(), 120)),
                "Compressor curve, threshold " + Ui.db(thresholdDb)
                        + ", ratio " + ratio + " to one, makeup " + Ui.db(makeupDb));
    }
}
