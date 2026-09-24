package dev.ajuntanaga.io24;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.List;

import org.junit.Test;

public final class Io24ScenePlannerTest {
    @Test
    public void scenesDoNotChangeTheCurrentAudioRateOrFrontPanelBlock() {
        Io24State target = Io24State.defaults().buildUpon()
                .setRememberedSampleRateHz(96_000)
                .setInputPresetSlot(1, 1)
                .setInputPresetSlot(2, 3)
                .build();

        List<Io24Command> commands = Io24ScenePlanner.commands(target);

        assertFalse(has(commands, Io24Command.Kind.SET_SAMPLE_RATE));
        assertFalse(has(commands, Io24Command.Kind.SET_PRESET_SLOT));
    }

    @Test
    public void aDelaySceneAlwaysCarriesSemanticModelIntent() {
        Io24State target = Io24State.defaults().buildUpon()
                .setRememberedSampleRateHz(96_000)
                .setSelectedVoiceFx(Io24State.VoiceFxModel.DELAY)
                .build();

        List<Io24Command> commands = Io24ScenePlanner.commands(target);

        assertTrue(commands.stream().anyMatch(command ->
                command.kind() == Io24Command.Kind.SET_VOICE_FX_MODEL
                        && command.model() == Io24State.VoiceFxModel.DELAY));
    }

    private static boolean has(
            List<Io24Command> commands,
            Io24Command.Kind kind) {
        return commands.stream().anyMatch(command -> command.kind() == kind);
    }
}
