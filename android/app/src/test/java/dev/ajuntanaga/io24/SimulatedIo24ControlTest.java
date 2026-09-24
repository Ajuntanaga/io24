package dev.ajuntanaga.io24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class SimulatedIo24ControlTest {
    @Test
    public void verifiedSessionMatchesThePhysicalReadShape() throws Exception {
        SimulatedIo24Control.DeviceState state =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(state, false);

        ProbeResult initial = control.connectAndRead();
        assertEquals(1, initial.protocolVersion());
        assertEquals(2048, initial.maxCommandLength());
        assertEquals(2048, initial.maxResponseLength());
        assertEquals(2048, initial.responseLength());
        assertEquals(503, initial.stateSlotCount());
        assertFalse(initial.input2Muted());

        assertTrue(control.setInput2Mute(true));
        assertTrue(state.input2Muted());
        assertTrue(control.isConnected());

        CommandResult gain = control.execute(Io24Command.setGain(1, 24.0f));
        assertEquals(Io24Command.Proof.READBACK, gain.proof());
        assertEquals(24.0f, gain.state().input(1).gainDb(), 0.0f);

        CommandResult send = control.execute(Io24Command.setMixerSend(
                Io24State.Source.INPUT_1,
                Io24State.Bus.MIX_A,
                -9.0f));
        assertEquals(Io24Command.Proof.SENT, send.proof());
        assertEquals(-9.0f,
                send.state().send(
                        Io24State.Source.INPUT_1,
                        Io24State.Bus.MIX_A).db(), 0.0f);

        control.execute(Io24Command.setVoiceFxOn(
                Io24State.VoiceFxModel.TRANSFORMER, true));
        CommandResult wet = control.execute(Io24Command.setVoiceFxParameter(
                Io24State.VoiceFxModel.TRANSFORMER, "mix", 0.8f));
        assertTrue(wet.state().voiceFx(
                Io24State.VoiceFxModel.TRANSFORMER).on());
        assertEquals(0.8f, wet.state().voiceFx(
                Io24State.VoiceFxModel.TRANSFORMER).parameter("mix"), 0.0f);

        control.close();
        assertFalse(control.isConnected());
    }

    @Test
    public void failedReadbackRetainsTheSimulatedDeviceWrite() throws Exception {
        SimulatedIo24Control.DeviceState state =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(state, true);
        control.connectAndRead();

        Io24UsbProbe.ProbeException error = assertThrows(
                Io24UsbProbe.ProbeException.class,
                () -> control.setInput2Mute(true));

        assertEquals("Simulated state readback failed", error.getMessage());
        assertTrue(state.input2Muted());

        SimulatedIo24Control fresh = new SimulatedIo24Control(state, false);
        assertTrue(fresh.connectAndRead().input2Muted());
    }

    @Test
    public void delayAtNinetySixKilohertzIsRetainedButNotPlacedNatively()
            throws Exception {
        SimulatedIo24Control.DeviceState device =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(device, false);
        control.connectAndRead();
        control.execute(Io24Command.setSampleRate(96_000));

        CommandResult result = control.execute(Io24Command.setVoiceFxModel(
                Io24State.VoiceFxModel.DELAY));

        assertEquals(Io24State.VoiceFxModel.DELAY,
                control.currentState().selectedVoiceFx());
        assertTrue(result.message().contains("phone"));
    }

    @Test
    public void semanticDelayIntentCanBeDisplayedAtNinetySixKilohertz() {
        SimulatedIo24Control.DeviceState device =
                new SimulatedIo24Control.DeviceState(false);
        device.apply(Io24Command.setSampleRate(96_000));
        device.apply(Io24Command.setVoiceFxModel(
                Io24State.VoiceFxModel.DELAY));

        Io24State state = device.snapshot();
        assertEquals(96_000, state.sampleRateHz());
        assertEquals(Io24State.VoiceFxModel.DELAY, state.selectedVoiceFx());
    }

    @Test
    public void confirmingSafeRateLeavesSelectedDelayExplicitlyOff()
            throws Exception {
        SimulatedIo24Control.DeviceState device =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(device, false);
        control.connectAndRead();
        control.execute(Io24Command.setVoiceFxModel(
                Io24State.VoiceFxModel.DELAY));
        control.execute(Io24Command.setVoiceFxOn(
                Io24State.VoiceFxModel.DELAY, true));

        CommandResult result = control.execute(
                Io24Command.setSampleRate(48_000));

        assertFalse(result.state().voiceFx(
                Io24State.VoiceFxModel.DELAY).on());
        assertEquals(
                "Rate confirmed; device Delay is off until explicitly enabled",
                result.message());
    }

    @Test
    public void deviceBlockWriteUsesTheSameUnverifiedStatusAsHardware()
            throws Exception {
        SimulatedIo24Control.DeviceState device =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(device, false);
        control.connectAndRead();

        CommandResult result = control.execute(
                Io24Command.saveDeviceBlock(1, 1));

        assertEquals(Io24Command.Proof.SENT, result.proof());
        assertEquals(
                "WRITE_SENT_UNVERIFIED: the io24 cannot read the stored block body back",
                result.message());
        assertEquals(result.message(), result.state().lastProof());
    }
}
