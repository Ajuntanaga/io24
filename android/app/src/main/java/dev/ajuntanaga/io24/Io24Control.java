package dev.ajuntanaga.io24;

/** Narrow control session shared by the physical and emulator transports. */
interface Io24Control extends AutoCloseable {
    boolean isConnected();

    Io24State currentState();

    Io24State refresh() throws Io24UsbProbe.ProbeException;

    CommandResult execute(Io24Command command)
            throws Io24UsbProbe.ProbeException;

    default boolean setInput2Mute(boolean muted)
            throws Io24UsbProbe.ProbeException {
        return execute(Io24Command.setInputMute(2, muted))
                .state().input(2).muted();
    }

    @Override
    void close();
}
