package dev.ajuntanaga.io24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class Io24StateTest {
    @Test
    public void builderProducesIndependentImmutableSnapshots() {
        Io24State first = Io24State.defaults();
        Io24State second = first.buildUpon()
                .setInputGain(1, 18.0f)
                .setInputMute(2, true)
                .build();

        assertNotSame(first, second);
        assertEquals(0.0f, first.input(1).gainDb(), 0.0f);
        assertFalse(first.input(2).muted());
        assertEquals(18.0f, second.input(1).gainDb(), 0.0f);
        assertTrue(second.input(2).muted());
    }

    @Test
    public void audioRateStartsUnknownAndOnlyCurrentSessionConfirmationSetsIt() {
        Io24State unknown = Io24State.defaults();
        Io24State confirmed = unknown.buildUpon()
                .setSampleRateHz(48_000)
                .build();
        Io24State remembered = confirmed.buildUpon()
                .setRememberedSampleRateHz(96_000)
                .build();

        assertFalse(unknown.sampleRateConfirmed());
        assertTrue(confirmed.sampleRateConfirmed());
        assertEquals(48_000, confirmed.sampleRateHz());
        assertFalse(remembered.sampleRateConfirmed());
        assertEquals(96_000, remembered.sampleRateHz());
    }

    @Test
    public void enablingOneVoiceFxTurnsTheOthersOffButKeepsTheirSettings() {
        Io24State state = Io24State.defaults().buildUpon()
                .setVoiceFxOn(Io24State.VoiceFxModel.TRANSFORMER, true)
                .setVoiceFxParameter(
                        Io24State.VoiceFxModel.TRANSFORMER, "mix", 0.75f)
                .setVoiceFxParameter(
                        Io24State.VoiceFxModel.DELAY, "mix", 0.2f)
                .setVoiceFxOn(Io24State.VoiceFxModel.DELAY, true)
                .build();

        assertFalse(state.voiceFx(Io24State.VoiceFxModel.TRANSFORMER).on());
        assertTrue(state.voiceFx(Io24State.VoiceFxModel.DELAY).on());
        assertEquals(0.75f,
                state.voiceFx(Io24State.VoiceFxModel.TRANSFORMER)
                        .parameter("mix"), 0.0f);
        assertEquals(0.2f,
                state.voiceFx(Io24State.VoiceFxModel.DELAY)
                        .parameter("mix"), 0.0f);
    }

    @Test
    public void confirmingARateLeavesDelayOffUntilTheUserEnablesIt() {
        Io24State before = Io24State.defaults().buildUpon()
                .setSelectedVoiceFx(Io24State.VoiceFxModel.DELAY)
                .setVoiceFxOn(Io24State.VoiceFxModel.DELAY, true)
                .setSampleRateHz(96_000)
                .build();

        Io24State after = Io24StateReducer.apply(
                before, Io24Command.setSampleRate(48_000));

        assertEquals(48_000, after.sampleRateHz());
        assertFalse(after.voiceFx(Io24State.VoiceFxModel.DELAY).on());
    }

    @Test
    public void mixerStateIsIndexedBySourceAndBus() {
        Io24State state = Io24State.defaults().buildUpon()
                .setMixerSend(
                        Io24State.Source.INPUT_2,
                        Io24State.Bus.MIX_B,
                        -12.5f,
                        true,
                        0.7f)
                .build();

        Io24State.Send send = state.send(
                Io24State.Source.INPUT_2, Io24State.Bus.MIX_B);
        assertEquals(-12.5f, send.db(), 0.0f);
        assertTrue(send.assigned());
        assertEquals(0.7f, send.pan(), 0.0f);
    }
}
