package dev.ajuntanaga.io24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class Io24CommandTest {
    @Test
    public void safeScalarFactoriesValidateChannelsAndRanges() {
        Io24Command gain = Io24Command.setGain(2, 42.5f);

        assertEquals(Io24Command.Kind.SET_GAIN, gain.kind());
        assertEquals(2, gain.channel());
        assertEquals(42.5f, gain.value(), 0.0f);
        assertEquals(Io24Command.Proof.READBACK, gain.proof());

        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.setGain(3, 10.0f));
        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.setGain(1, -0.1f));
        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.setMonitorBlend(1.01f));
    }

    @Test
    public void mixerFactoriesRequireKnownSourceAndBus() {
        Io24Command send = Io24Command.setMixerSend(
                Io24State.Source.PLAYBACK_1_2,
                Io24State.Bus.MAIN,
                -6.0f);

        assertEquals(Io24Command.Kind.SET_MIXER_SEND, send.kind());
        assertEquals(Io24State.Source.PLAYBACK_1_2, send.source());
        assertEquals(Io24State.Bus.MAIN, send.bus());
        assertEquals(Io24Command.Proof.SENT, send.proof());

        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.setMixerSend(
                        Io24State.Source.INPUT_1,
                        Io24State.Bus.MIX_A,
                        10.1f));
    }

    @Test
    public void delayNativePlacementRequiresAConfirmedRateAtOrBelow48k() {
        Io24Command delay = Io24Command.setVoiceFxModel(
                Io24State.VoiceFxModel.DELAY);
        Io24Command transformer = Io24Command.setVoiceFxModel(
                Io24State.VoiceFxModel.TRANSFORMER);
        Io24State unknown = Io24State.defaults();
        Io24State at44 = unknown.buildUpon().setSampleRateHz(44_100).build();
        Io24State at48 = unknown.buildUpon().setSampleRateHz(48_000).build();
        Io24State at882 = unknown.buildUpon().setSampleRateHz(88_200).build();
        Io24State at96 = unknown.buildUpon().setSampleRateHz(96_000).build();

        assertFalse(delay.canRunNatively(unknown));
        assertTrue(delay.canRunNatively(at44));
        assertTrue(delay.canRunNatively(at48));
        assertFalse(delay.canRunNatively(at882));
        assertFalse(delay.canRunNatively(at96));
        assertTrue(transformer.canRunNatively(unknown));
    }

    @Test
    public void voiceFxParametersFollowExactModelCatalog() {
        Io24Command wetDry = Io24Command.setVoiceFxParameter(
                Io24State.VoiceFxModel.FILTERS, "mix", 0.4f);
        assertEquals("mix", wetDry.parameter());
        assertEquals(0.4f, wetDry.value(), 0.0f);

        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.setVoiceFxParameter(
                        Io24State.VoiceFxModel.VOCODER, "voiced", 0.5f));
        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.setVoiceFxParameter(
                        Io24State.VoiceFxModel.DETUNER, "detune", 9.0f));
    }

    @Test
    public void fatChannelParametersAreTypedAndAndroidExposesStandardModels() {
        assertEquals(7.5f, Io24Command.setProcessingParameter(
                1, "compressor_ratio", 7.5f).value(), 0.0f);
        assertThrows(IllegalArgumentException.class, () ->
                Io24Command.setProcessingParameter(1, "unknown", 1));
        assertThrows(IllegalArgumentException.class, () ->
                Io24Command.setProcessingParameter(
                        1, "compressor_model", 1));
        assertThrows(IllegalArgumentException.class, () ->
                Io24Command.setProcessingParameter(1, "eq_model", 2));
    }

    @Test
    public void deviceBlockSaveRequiresAnExactInputAndOneOfTwoBlocks() {
        Io24Command save = Io24Command.saveDeviceBlock(2, 1);

        assertEquals(Io24Command.Kind.SAVE_DEVICE_BLOCK, save.kind());
        assertEquals(Io24Command.Proof.SENT, save.proof());
        assertEquals(2, save.channel());
        assertEquals(1.0f, save.value(), 0.0f);
        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.saveDeviceBlock(1, 2));
        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.setPresetSlot(1, 2));
        assertThrows(IllegalArgumentException.class,
                () -> Io24Command.setPresetSlot(2, 1));
    }
}
