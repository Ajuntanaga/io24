package dev.ajuntanaga.io24;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Executor;

/** Serial lifecycle and command owner between Android UI and one io24 session. */
public final class Io24Controller implements AutoCloseable {
    public interface Listener {
        void onState(Io24State state);
    }

    public interface SessionFactory {
        Io24Control open() throws Io24UsbProbe.ProbeException;
    }

    private final Executor worker;
    private final Executor callbacks;
    private volatile Io24State state = Io24State.defaults();
    private volatile Listener listener;
    private Io24Control control;
    private long sessionEpoch;

    public Io24Controller(Executor worker, Executor callbacks) {
        if (worker == null || callbacks == null) {
            throw new IllegalArgumentException("Worker and callback executors are required");
        }
        this.worker = worker;
        this.callbacks = callbacks;
    }

    public void setListener(Listener value) {
        listener = value;
    }

    public Io24State state() {
        return state;
    }

    public void connect(SessionFactory factory) {
        if (factory == null) {
            throw new IllegalArgumentException("Session factory is required");
        }
        final long requestedEpoch;
        synchronized (this) {
            requestedEpoch = ++sessionEpoch;
        }
        Io24State pending = state.buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.CONNECTING,
                        "Connecting to io24…",
                        state.simulated())
                .setBusy(true)
                .build();
        publish(pending);
        worker.execute(() -> {
            if (!isCurrentEpoch(requestedEpoch)) {
                return;
            }
            try {
                Io24Control opened = factory.open();
                Io24Control previous;
                synchronized (this) {
                    if (sessionEpoch != requestedEpoch) {
                        opened.close();
                        return;
                    }
                    previous = control;
                    control = opened;
                }
                if (previous != null) {
                    previous.close();
                }
                publish(opened.currentState().buildUpon()
                        .setBusy(false)
                        .build());
            } catch (Io24UsbProbe.ProbeException error) {
                if (isCurrentEpoch(requestedEpoch)) {
                    publishError(state, error);
                }
            }
        });
    }

    public void dispatch(Io24Command command) {
        if (command == null) {
            throw new IllegalArgumentException("Command is required");
        }
        Io24Control active;
        long operationEpoch;
        synchronized (this) {
            active = control;
            operationEpoch = sessionEpoch;
        }
        if (active == null || !active.isConnected()) {
            publish(state.buildUpon()
                    .setConnection(
                            Io24State.ConnectionStatus.ERROR,
                            "Connect the io24 before changing a control",
                            state.simulated())
                    .setBusy(false)
                    .build());
            return;
        }
        Io24State confirmedBefore = state;
        publish(state.buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.CONNECTED,
                        "Applying " + friendly(command.kind()) + "…",
                        state.simulated())
                .setBusy(true)
                .build());
        worker.execute(() -> {
            if (!isCurrent(active, operationEpoch)) {
                return;
            }
            try {
                CommandResult result = active.execute(command);
                if (!isCurrent(active, operationEpoch)) {
                    return;
                }
                publish(result.state().buildUpon()
                        .setBusy(false)
                        .build());
            } catch (Io24UsbProbe.ProbeException error) {
                if (clearIfCurrent(active, operationEpoch)) {
                    active.close();
                    publishError(confirmedBefore, error);
                }
            }
        });
    }

    /** Applies an ordered scene as one serialized operation and one busy state. */
    public void dispatchAll(List<Io24Command> commands, String label) {
        if (commands == null || commands.isEmpty()) {
            return;
        }
        List<Io24Command> ordered = new ArrayList<>(commands);
        for (Io24Command command : ordered) {
            if (command == null) {
                throw new IllegalArgumentException("Scene command is required");
            }
        }
        Io24Control active;
        long operationEpoch;
        synchronized (this) {
            active = control;
            operationEpoch = sessionEpoch;
        }
        if (active == null || !active.isConnected()) {
            publish(state.buildUpon()
                    .setConnection(
                            Io24State.ConnectionStatus.ERROR,
                            "Connect the io24 before loading a scene",
                            state.simulated())
                    .setBusy(false)
                    .build());
            return;
        }
        Io24State confirmedBefore = state;
        publish(state.buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.CONNECTED,
                        "Applying " + (label == null ? "scene" : label) + "…",
                        state.simulated())
                .setBusy(true)
                .build());
        worker.execute(() -> {
            if (!isCurrent(active, operationEpoch)) {
                return;
            }
            int completed = 0;
            try {
                CommandResult result = null;
                for (Io24Command command : ordered) {
                    if (!isCurrent(active, operationEpoch)) {
                        return;
                    }
                    result = active.execute(command);
                    completed++;
                }
                if (!isCurrent(active, operationEpoch)) {
                    return;
                }
                Io24State finalState = result == null
                        ? active.currentState()
                        : result.state();
                publish(finalState.buildUpon().setBusy(false).build());
            } catch (Io24UsbProbe.ProbeException error) {
                if (clearIfCurrent(active, operationEpoch)) {
                    active.close();
                    String scene = label == null ? "Scene" : label;
                    publishError(confirmedBefore, new Io24UsbProbe.ProbeException(
                            scene + " stopped after " + completed + " of "
                                    + ordered.size()
                                    + " confirmed controls; the device may be "
                                    + "partially changed. Reconnect and refresh "
                                    + "before continuing. " + error.getMessage(),
                            error));
                }
            }
        });
    }

    public void refresh() {
        Io24Control active;
        long operationEpoch;
        synchronized (this) {
            active = control;
            operationEpoch = sessionEpoch;
        }
        if (active == null || !active.isConnected()) {
            return;
        }
        Io24State confirmedBefore = state;
        publish(state.buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.CONNECTED,
                        "Refreshing io24 state…",
                        state.simulated())
                .setBusy(true)
                .build());
        worker.execute(() -> {
            if (!isCurrent(active, operationEpoch)) {
                return;
            }
            try {
                Io24State refreshed = active.refresh();
                if (isCurrent(active, operationEpoch)) {
                    publish(refreshed.buildUpon().setBusy(false).build());
                }
            } catch (Io24UsbProbe.ProbeException error) {
                if (clearIfCurrent(active, operationEpoch)) {
                    active.close();
                    publishError(confirmedBefore, error);
                }
            }
        });
    }

    public void disconnect() {
        Io24Control active;
        synchronized (this) {
            sessionEpoch++;
            active = control;
            control = null;
        }
        publish(state.buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.DISCONNECTED,
                        "Control released",
                        state.simulated())
                .setBusy(false)
                .build());
        if (active != null) {
            worker.execute(active::close);
        }
    }

    @Override
    public void close() {
        disconnect();
        listener = null;
    }

    private void publishError(
            Io24State lastConfirmed,
            Exception error) {
        publish(lastConfirmed.buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.ERROR,
                        error.getMessage(),
                        lastConfirmed.simulated())
                .setBusy(false)
                .build());
    }

    private void publish(Io24State next) {
        state = next;
        Listener current = listener;
        if (current != null) {
            callbacks.execute(() -> current.onState(next));
        }
    }

    private synchronized boolean isCurrentEpoch(long epoch) {
        return sessionEpoch == epoch;
    }

    private synchronized boolean isCurrent(
            Io24Control expected,
            long epoch) {
        return control == expected && sessionEpoch == epoch;
    }

    private synchronized boolean clearIfCurrent(
            Io24Control expected,
            long epoch) {
        if (control != expected || sessionEpoch != epoch) {
            return false;
        }
        control = null;
        sessionEpoch++;
        return true;
    }

    private static String friendly(Io24Command.Kind kind) {
        return kind.name().toLowerCase(Locale.ROOT).replace('_', ' ');
    }
}
