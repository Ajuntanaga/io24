package dev.ajuntanaga.io24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.concurrent.Executor;

import org.junit.Test;

public final class Io24ControllerReducerTest {
    private static final Executor DIRECT = Runnable::run;

    private static final class QueuedExecutor implements Executor {
        private final Deque<Runnable> work = new ArrayDeque<>();

        @Override
        public void execute(Runnable command) {
            work.addLast(command);
        }

        void runNext() {
            work.removeFirst().run();
        }
    }

    @Test
    public void connectDispatchRefreshAndDisconnectPublishOrderedSnapshots() {
        SimulatedIo24Control.DeviceState device =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(device, false);
        Io24Controller controller = new Io24Controller(DIRECT, DIRECT);
        List<Io24State> snapshots = new ArrayList<>();
        controller.setListener(snapshots::add);

        controller.connect(() -> {
            control.connectAndRead();
            return control;
        });
        controller.dispatch(Io24Command.setGain(1, 17.0f));
        controller.refresh();
        controller.disconnect();

        assertEquals(Io24State.ConnectionStatus.CONNECTING,
                snapshots.get(0).connectionStatus());
        assertTrue(snapshots.get(0).busy());
        assertEquals(Io24State.ConnectionStatus.CONNECTED,
                snapshots.get(1).connectionStatus());
        assertFalse(snapshots.get(1).busy());
        assertEquals(17.0f, snapshots.get(3).input(1).gainDb(), 0.0f);
        assertEquals(Io24State.ConnectionStatus.DISCONNECTED,
                snapshots.get(snapshots.size() - 1).connectionStatus());
        assertFalse(controller.state().busy());
    }

    @Test
    public void commandFailureClosesUncertainSessionAndPreservesLastState() {
        SimulatedIo24Control.DeviceState device =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(device, true);
        Io24Controller controller = new Io24Controller(DIRECT, DIRECT);
        controller.connect(() -> {
            control.connectAndRead();
            return control;
        });

        controller.dispatch(Io24Command.setInputMute(2, true));

        assertEquals(Io24State.ConnectionStatus.ERROR,
                controller.state().connectionStatus());
        assertFalse(controller.state().input(2).muted());
        assertFalse(controller.state().busy());
        assertFalse(control.isConnected());
        assertTrue(controller.state().statusMessage()
                .contains("Simulated state readback failed"));
    }

    @Test
    public void sceneBatchPublishesOneBusyBoundaryAndFinalCombinedState() {
        SimulatedIo24Control control = new SimulatedIo24Control(
                new SimulatedIo24Control.DeviceState(false), false);
        Io24Controller controller = new Io24Controller(DIRECT, DIRECT);
        List<Io24State> snapshots = new ArrayList<>();
        controller.setListener(snapshots::add);
        controller.connect(() -> {
            control.connectAndRead();
            return control;
        });
        snapshots.clear();

        controller.dispatchAll(List.of(
                Io24Command.setGain(1, 12.0f),
                Io24Command.setGain(2, 18.0f),
                Io24Command.setVoiceFxModel(
                        Io24State.VoiceFxModel.FILTERS)), "Vocal scene");

        assertEquals(2, snapshots.size());
        assertTrue(snapshots.get(0).busy());
        assertFalse(snapshots.get(1).busy());
        assertEquals(12.0f, snapshots.get(1).input(1).gainDb(), 0.0f);
        assertEquals(18.0f, snapshots.get(1).input(2).gainDb(), 0.0f);
        assertEquals(Io24State.VoiceFxModel.FILTERS,
                snapshots.get(1).selectedVoiceFx());
    }

    @Test
    public void disconnectPublishesImmediatelyAndReleasesOffTheCallerThread() {
        QueuedExecutor worker = new QueuedExecutor();
        SimulatedIo24Control control = new SimulatedIo24Control(
                new SimulatedIo24Control.DeviceState(false), false);
        Io24Controller controller = new Io24Controller(worker, DIRECT);
        controller.connect(() -> {
            control.connectAndRead();
            return control;
        });
        worker.runNext();

        controller.disconnect();

        assertEquals(Io24State.ConnectionStatus.DISCONNECTED,
                controller.state().connectionStatus());
        assertTrue(control.isConnected());
        worker.runNext();
        assertFalse(control.isConnected());
    }

    @Test
    public void a_queued_write_is_discarded_after_disconnect() {
        QueuedExecutor worker = new QueuedExecutor();
        SimulatedIo24Control.DeviceState device =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(device, false);
        Io24Controller controller = new Io24Controller(worker, DIRECT);
        controller.connect(() -> {
            control.connectAndRead();
            return control;
        });
        worker.runNext();

        controller.dispatch(Io24Command.setGain(1, 24.0f));
        controller.disconnect();
        worker.runNext();
        worker.runNext();

        assertEquals(0.0f, device.snapshot().input(1).gainDb(), 0.0f);
        assertEquals(Io24State.ConnectionStatus.DISCONNECTED,
                controller.state().connectionStatus());
    }

    @Test
    public void a_partial_scene_reports_progress_and_uncertainty() {
        SimulatedIo24Control.DeviceState device =
                new SimulatedIo24Control.DeviceState(false);
        SimulatedIo24Control control = new SimulatedIo24Control(device, true);
        Io24Controller controller = new Io24Controller(DIRECT, DIRECT);
        controller.connect(() -> {
            control.connectAndRead();
            return control;
        });

        controller.dispatchAll(List.of(
                Io24Command.setFxMix(1, 0.25f),
                Io24Command.setInputMute(2, true)), "Partial scene");

        assertEquals(Io24State.ConnectionStatus.ERROR,
                controller.state().connectionStatus());
        assertTrue(controller.state().statusMessage().contains("after 1 of 2"));
        assertTrue(controller.state().statusMessage()
                .contains("may be partially changed"));
        assertFalse(control.isConnected());
    }
}
