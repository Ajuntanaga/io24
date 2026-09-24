package dev.ajuntanaga.io24;

import android.content.Context;

import java.util.Map;

/** Model-specific Voice FX graph driven by the complete model state. */
final class EffectGraphView extends TraceView {
    EffectGraphView(Context context) {
        super(context);
    }

    void setEffect(
            Io24State.VoiceFxModel model,
            Io24State.VoiceFxState state) {
        setTrace(
                GraphMath.effectTrace(
                        model,
                        state.parameters(),
                        Math.max(1, getWidth()),
                        Ui.dp(getContext(), 120)),
                model.label() + " response using all current parameters");
    }

    void setEffect(
            Io24State.VoiceFxModel model,
            Map<String, Float> parameters) {
        setTrace(
                GraphMath.effectTrace(
                        model,
                        parameters,
                        Math.max(1, getWidth()),
                        Ui.dp(getContext(), 120)),
                model.label() + " response using all current parameters");
    }
}
