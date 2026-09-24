package dev.ajuntanaga.io24;

/** Debug-build transport for deterministic emulator UI and lifecycle checks. */
final class SimulatedIo24Control implements Io24Control {
    static final class DeviceState {
        private Io24State state;

        DeviceState(boolean input2Muted) {
            state = Io24State.defaults().buildUpon()
                    .setInputMute(2, input2Muted)
                    .build();
        }

        synchronized boolean input2Muted() {
            return state.input(2).muted();
        }

        synchronized void setInput2Muted(boolean muted) {
            state = state.buildUpon().setInputMute(2, muted).build();
        }

        synchronized Io24State snapshot() {
            return state;
        }

        synchronized void apply(Io24Command command) {
            state = Io24StateReducer.apply(state, command);
        }
    }

    private final DeviceState deviceState;
    private final boolean failWriteReadback;
    private boolean connected;
    private Io24State currentState = Io24State.defaults();

    SimulatedIo24Control(
            DeviceState deviceState,
            boolean failWriteReadback) {
        if (deviceState == null) {
            throw new IllegalArgumentException("Device state is required");
        }
        this.deviceState = deviceState;
        this.failWriteReadback = failWriteReadback;
    }

    ProbeResult connectAndRead() {
        connected = true;
        currentState = deviceState.snapshot().buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.CONNECTED,
                        "Connected to emulator test device",
                        true)
                .setProtocolInfo(1, 2_048, 2_048, 503)
                .setLastProof("Read from emulator test device")
                .build();
        return result();
    }

    @Override
    public boolean isConnected() {
        return connected;
    }

    @Override
    public Io24State currentState() {
        return currentState;
    }

    @Override
    public Io24State refresh() throws Io24UsbProbe.ProbeException {
        if (!connected) {
            throw new Io24UsbProbe.ProbeException(
                    "The simulated io24 is not connected");
        }
        currentState = deviceState.snapshot().buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.CONNECTED,
                        "Connected to emulator test device",
                        true)
                .setProtocolInfo(1, 2_048, 2_048, 503)
                .setLastProof("Read from emulator test device")
                .build();
        return currentState;
    }

    @Override
    public CommandResult execute(Io24Command command)
            throws Io24UsbProbe.ProbeException {
        if (!connected) {
            throw new Io24UsbProbe.ProbeException(
                    "The simulated io24 is not connected");
        }
        boolean retainedDelay = command.model() == Io24State.VoiceFxModel.DELAY
                && !command.canRunNatively(currentState);
        boolean inactiveEffect = (command.kind() == Io24Command.Kind.SET_VOICE_FX_ON
                || command.kind() == Io24Command.Kind.SET_VOICE_FX_PARAMETER)
                && (command.model() != currentState.selectedVoiceFx()
                || retainedDelay);
        deviceState.apply(command);
        if (failWriteReadback
                && command.proof() == Io24Command.Proof.READBACK) {
            throw new Io24UsbProbe.ProbeException(
                    "Simulated state readback failed");
        }
        String proofLabel;
        if (command.kind() == Io24Command.Kind.SAVE_DEVICE_BLOCK) {
            proofLabel = "WRITE_SENT_UNVERIFIED: the io24 cannot read the stored block body back";
        } else if (inactiveEffect) {
            proofLabel = "Stored on this phone until the model is selected";
        } else if (retainedDelay) {
            proofLabel = "Delay kept on this phone; device Voice FX is safely off";
        } else if (command.kind() == Io24Command.Kind.SET_SAMPLE_RATE) {
            proofLabel = "Rate confirmed; device Delay is off until explicitly enabled";
        } else {
            proofLabel = Io24StateReducer.proofLabel(command.proof());
        }
        currentState = deviceState.snapshot().buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.CONNECTED,
                        "Connected to emulator test device",
                        true)
                .setProtocolInfo(1, 2_048, 2_048, 503)
                .setLastProof(proofLabel)
                .build();
        return new CommandResult(
                currentState,
                inactiveEffect ? Io24Command.Proof.LOCAL : command.proof(),
                currentState.lastProof());
    }

    @Override
    public void close() {
        connected = false;
        currentState = currentState.buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.DISCONNECTED,
                        "Control released",
                        true)
                .build();
    }

    private ProbeResult result() {
        return new ProbeResult(
                1,
                2_048,
                2_048,
                2_048,
                503,
                    currentState.input(2).muted());
    }
}
