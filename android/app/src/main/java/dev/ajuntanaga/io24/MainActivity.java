package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ApplicationInfo;
import android.graphics.Insets;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.EnumMap;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Direct, offline Android controller for the Revelator io24. */
public final class MainActivity extends Activity {
    private static final String ACTION_USB_PERMISSION =
            "dev.ajuntanaga.io24.USB_PERMISSION";
    private static final String EXTRA_SIMULATED_IO24 =
            "dev.ajuntanaga.io24.SIMULATED_IO24";
    private static final String EXTRA_SIMULATED_READBACK_FAILURE =
            "dev.ajuntanaga.io24.SIMULATED_READBACK_FAILURE";
    private static final String EXTRA_SIMULATED_DELAY_96 =
            "dev.ajuntanaga.io24.SIMULATED_DELAY_96";
    private static final int REQUEST_IMPORT_SCENE = 31;
    private static final int REQUEST_EXPORT_SCENE = 32;
    private static final int MAX_IMPORT_BYTES = 1_000_000;

    private enum Destination {
        MIXER("Mixer"),
        FAT_CHANNEL("Fat"),
        EFFECTS("Effects"),
        PRESETS("Presets"),
        DEVICE("Device");

        final String label;

        Destination(String label) {
            this.label = label;
        }
    }

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final SimulatedIo24Control.DeviceState simulatedDeviceState =
            new SimulatedIo24Control.DeviceState(false);
    private final EnumMap<Destination, ControllerView> screens =
            new EnumMap<>(Destination.class);
    private final EnumMap<Destination, Button> navigation =
            new EnumMap<>(Destination.class);
    private UsbManager usbManager;
    private Io24Controller controller;
    private PresetStore presetStore;
    private PresetsView presetsView;
    private FrameLayout viewport;
    private TextView connectionStatus;
    private TextView connectionDetail;
    private Button connect;
    private Button refresh;
    private Button disconnect;
    private Destination destination = Destination.MIXER;
    private Io24State visibleState = Io24State.defaults();
    private String pendingExportJson;

    private final BroadcastReceiver usbReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            UsbDevice device = usbDeviceExtra(intent);
            if (ACTION_USB_PERMISSION.equals(intent.getAction())) {
                boolean granted = intent.getBooleanExtra(
                        UsbManager.EXTRA_PERMISSION_GRANTED, false);
                // Some Android builds omit or lose the filled-in permission
                // boolean on this mutable system broadcast.  The manager is
                // authoritative after the user answers the dialog.
                if (Io24UsbProbe.matches(device)
                        && (granted || usbManager.hasPermission(device))) {
                    connectPhysical(device);
                } else {
                    render(visibleState.buildUpon()
                            .setConnection(
                                    Io24State.ConnectionStatus.ERROR,
                                    getString(R.string.status_permission_denied),
                                    false)
                            .build());
                }
            } else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(intent.getAction())
                    && Io24UsbProbe.matches(device)) {
                controller.disconnect();
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        usbManager = (UsbManager) getSystemService(Context.USB_SERVICE);
        presetStore = new PresetStore(this);
        controller = new Io24Controller(worker, this::runOnUiThread);
        controller.setListener(this::render);
        if (savedInstanceState != null) {
            String savedDestination = savedInstanceState.getString("destination");
            if (savedDestination != null) {
                destination = Destination.valueOf(savedDestination);
            }
        }
        if (isSimulationEnabled()
                && getIntent().getBooleanExtra(EXTRA_SIMULATED_DELAY_96, false)) {
            simulatedDeviceState.apply(Io24Command.setSampleRate(96_000));
            // This is semantic scene intent. The native model remains forbidden.
            simulatedDeviceState.apply(Io24Command.setVoiceFxModel(
                    Io24State.VoiceFxModel.DELAY));
        }
        setContentView(buildShell());
        registerUsbReceiver();
        Io24State initial = Io24State.defaults().buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.DISCONNECTED,
                        initialStatus(),
                        isSimulationEnabled())
                .build();
        showDestination(destination);
        render(initial);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        outState.putString("destination", destination.name());
        super.onSaveInstanceState(outState);
    }

    @Override
    protected void onDestroy() {
        unregisterReceiver(usbReceiver);
        controller.close();
        // Let the controller's queued USB release drain without blocking the
        // main thread or cancelling interface cleanup.
        worker.shutdown();
        super.onDestroy();
    }

    private View buildShell() {
        LinearLayout root = Ui.column(this);
        root.setBackgroundColor(getColor(R.color.surface_0));
        root.setOnApplyWindowInsetsListener((view, windowInsets) -> {
            int left;
            int top;
            int right;
            int bottom;
            if (Build.VERSION.SDK_INT >= 30) {
                Insets insets = windowInsets.getInsets(
                        WindowInsets.Type.systemBars()
                                | WindowInsets.Type.displayCutout());
                left = insets.left;
                top = insets.top;
                right = insets.right;
                bottom = insets.bottom;
            } else {
                left = windowInsets.getSystemWindowInsetLeft();
                top = windowInsets.getSystemWindowInsetTop();
                right = windowInsets.getSystemWindowInsetRight();
                bottom = windowInsets.getSystemWindowInsetBottom();
            }
            view.setPadding(left, top, right, bottom);
            return windowInsets;
        });

        LinearLayout banner = Ui.column(this);
        banner.setPadding(Ui.dp(this, 16), Ui.dp(this, 12),
                Ui.dp(this, 16), Ui.dp(this, 12));
        banner.setBackgroundColor(getColor(R.color.surface_1));
        LinearLayout heading = Ui.row(this);
        heading.addView(Ui.title(this, getString(R.string.app_name)), Ui.weight(2));
        connectionStatus = Ui.caption(this, getString(R.string.status_connect_device));
        connectionStatus.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        connectionStatus.setGravity(android.view.Gravity.END);
        heading.addView(connectionStatus, Ui.weight(1));
        banner.addView(heading, Ui.match());

        connectionDetail = Ui.caption(
                this, getString(R.string.status_connect_device));
        connectionDetail.setAccessibilityLiveRegion(
                View.ACCESSIBILITY_LIVE_REGION_POLITE);
        banner.addView(connectionDetail, Ui.spaced(this));

        LinearLayout actions = Ui.row(this);
        connect = Ui.button(this, "Connect");
        connect.setContentDescription("Connect to io24 control");
        connect.setOnClickListener(view -> inspect());
        actions.addView(connect, Ui.weight(1));
        refresh = Ui.button(this, "Refresh");
        refresh.setOnClickListener(view -> controller.refresh());
        LinearLayout.LayoutParams refreshParams = Ui.weight(1);
        refreshParams.leftMargin = Ui.dp(this, 8);
        actions.addView(refresh, refreshParams);
        disconnect = Ui.button(this, "Disconnect");
        disconnect.setOnClickListener(view -> controller.disconnect());
        LinearLayout.LayoutParams disconnectParams = Ui.weight(1);
        disconnectParams.leftMargin = Ui.dp(this, 8);
        actions.addView(disconnect, disconnectParams);
        banner.addView(actions, Ui.spaced(this));
        root.addView(banner, Ui.match());

        CommandSink sink = command -> controller.dispatch(command);
        screens.put(Destination.MIXER, new MixerView(this, sink));
        screens.put(Destination.FAT_CHANNEL, new FatChannelView(this, sink));
        screens.put(Destination.EFFECTS, new EffectsView(this, sink));
        presetsView = new PresetsView(
                this,
                presetStore,
                sink,
                new PresetsView.SceneActions() {
                    @Override
                    public void apply(PresetCodec.Decoded scene) {
                        applyScene(scene);
                    }

                    @Override
                    public void export(PresetCodec.Decoded scene) {
                        exportScene(scene);
                    }

                    @Override
                    public void importScene() {
                        requestSceneImport();
                    }
                });
        screens.put(Destination.PRESETS, presetsView);
        screens.put(Destination.DEVICE,
                new DeviceView(this, sink, () -> controller.refresh()));

        viewport = new FrameLayout(this);
        LinearLayout.LayoutParams viewportParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1.0f);
        root.addView(viewport, viewportParams);

        LinearLayout nav = Ui.row(this);
        nav.setPadding(Ui.dp(this, 4), Ui.dp(this, 4),
                Ui.dp(this, 4), Ui.dp(this, 4));
        nav.setBackgroundColor(getColor(R.color.surface_1));
        for (Destination item : Destination.values()) {
            Button button = Ui.button(this, item.label);
            button.setContentDescription("Open " + item.label);
            button.setOnClickListener(view -> showDestination(item));
            navigation.put(item, button);
            LinearLayout.LayoutParams params = Ui.weight(1);
            if (item != Destination.MIXER) {
                params.leftMargin = Ui.dp(this, 4);
            }
            nav.addView(button, params);
        }
        root.addView(nav, Ui.match());
        return root;
    }

    private void inspect() {
        if (isSimulationEnabled()) {
            controller.connect(() -> {
                SimulatedIo24Control simulated = new SimulatedIo24Control(
                        simulatedDeviceState,
                        getIntent().getBooleanExtra(
                                EXTRA_SIMULATED_READBACK_FAILURE, false));
                simulated.connectAndRead();
                return simulated;
            });
            return;
        }
        UsbDevice device = Io24UsbProbe.findDevice(usbManager);
        if (device == null) {
            render(visibleState.buildUpon()
                    .setConnection(
                            Io24State.ConnectionStatus.ERROR,
                            getString(R.string.status_device_missing),
                            false)
                    .build());
            return;
        }
        if (usbManager.hasPermission(device)) {
            connectPhysical(device);
            return;
        }
        render(visibleState.buildUpon()
                .setConnection(
                        Io24State.ConnectionStatus.CONNECTING,
                        getString(R.string.status_waiting_permission),
                        false)
                .setBusy(true)
                .build());
        int permissionFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            permissionFlags |= PendingIntent.FLAG_MUTABLE;
        }
        PendingIntent permissionIntent = PendingIntent.getBroadcast(
                this,
                0,
                new Intent(ACTION_USB_PERMISSION).setPackage(getPackageName()),
                permissionFlags);
        usbManager.requestPermission(device, permissionIntent);
    }

    private void connectPhysical(UsbDevice device) {
        controller.connect(() -> {
            Io24UsbProbe physical = new Io24UsbProbe(usbManager);
            physical.connectAndRead(device);
            return physical;
        });
    }

    private void render(Io24State state) {
        visibleState = state;
        connectionStatus.setText(connectionLabel(state));
        connectionStatus.setTextColor(getColor(connectionColor(state)));
        boolean showDetail = state.connectionStatus()
                != Io24State.ConnectionStatus.CONNECTED;
        connectionDetail.setText(state.statusMessage());
        connectionDetail.setTextColor(getColor(
                state.connectionStatus() == Io24State.ConnectionStatus.ERROR
                        ? R.color.danger
                        : R.color.text_secondary));
        connectionDetail.setVisibility(showDetail ? View.VISIBLE : View.GONE);
        boolean connected = state.connectionStatus()
                == Io24State.ConnectionStatus.CONNECTED;
        connect.setEnabled(!connected && !state.busy());
        refresh.setEnabled(connected && !state.busy());
        disconnect.setEnabled(connected || state.busy());
        for (ControllerView screen : screens.values()) {
            screen.render(state);
        }
    }

    private void showDestination(Destination next) {
        destination = next;
        viewport.removeAllViews();
        viewport.addView(
                screens.get(next).view(),
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT));
        for (Destination item : Destination.values()) {
            Button button = navigation.get(item);
            button.setBackground(Ui.panel(
                    this,
                    item == next ? R.color.accent_dark : R.color.surface_2,
                    10));
            button.setTextColor(getColor(
                    item == next ? R.color.accent : R.color.text_primary));
            button.setSelected(item == next);
        }
    }

    private void applyScene(PresetCodec.Decoded scene) {
        if (visibleState.connectionStatus()
                != Io24State.ConnectionStatus.CONNECTED) {
            render(scene.state().buildUpon()
                    .setConnection(
                            Io24State.ConnectionStatus.DISCONNECTED,
                            "Loaded " + scene.name() + " locally; connect to apply it",
                            false)
                    .build());
            return;
        }
        List<Io24Command> commands = Io24ScenePlanner.commands(scene.state());
        controller.dispatchAll(commands, scene.name());
    }

    private void exportScene(PresetCodec.Decoded scene) {
        pendingExportJson = PresetCodec.encode(scene.name(), scene.state());
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/json")
                .putExtra(Intent.EXTRA_TITLE, safeFileName(scene.name()) + ".json");
        startActivityForResult(intent, REQUEST_EXPORT_SCENE);
    }

    private void requestSceneImport() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/json");
        startActivityForResult(intent, REQUEST_IMPORT_SCENE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;
        }
        Uri uri = data.getData();
        try {
            if (requestCode == REQUEST_EXPORT_SCENE && pendingExportJson != null) {
                try (OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
                    if (output == null) {
                        throw new IOException("Android could not open the export file");
                    }
                    output.write(pendingExportJson.getBytes(StandardCharsets.UTF_8));
                }
                pendingExportJson = null;
            } else if (requestCode == REQUEST_IMPORT_SCENE) {
                PresetCodec.Decoded decoded = presetStore.importJson(readDocument(uri));
                presetsView.imported(decoded);
            }
        } catch (IllegalArgumentException | IOException error) {
            render(visibleState.buildUpon()
                    .setConnection(
                            visibleState.connectionStatus(),
                            error.getMessage(),
                            visibleState.simulated())
                    .build());
        }
    }

    private String readDocument(Uri uri) throws IOException {
        try (InputStream input = getContentResolver().openInputStream(uri)) {
            if (input == null) {
                throw new IOException("Android could not open the selected file");
            }
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            byte[] buffer = new byte[8_192];
            int count;
            while ((count = input.read(buffer)) >= 0) {
                if (output.size() + count > MAX_IMPORT_BYTES) {
                    throw new IOException("Scene file is larger than 1 MB");
                }
                output.write(buffer, 0, count);
            }
            return output.toString(StandardCharsets.UTF_8.name());
        }
    }

    private String initialStatus() {
        if (isSimulationEnabled()) {
            return getString(R.string.status_simulated_ready);
        }
        return Io24UsbProbe.findDevice(usbManager) == null
                ? getString(R.string.status_connect_device)
                : getString(R.string.status_device_ready);
    }

    private boolean isSimulationEnabled() {
        return (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0
                && getIntent().getBooleanExtra(EXTRA_SIMULATED_IO24, false);
    }

    @SuppressLint("UnspecifiedRegisterReceiverFlag")
    private void registerUsbReceiver() {
        IntentFilter filter = new IntentFilter(ACTION_USB_PERMISSION);
        filter.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(usbReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(usbReceiver, filter);
        }
    }

    private static UsbDevice usbDeviceExtra(Intent intent) {
        if (intent == null) {
            return null;
        }
        if (Build.VERSION.SDK_INT >= 33) {
            return intent.getParcelableExtra(UsbManager.EXTRA_DEVICE, UsbDevice.class);
        }
        @SuppressWarnings("deprecation")
        UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
        return device;
    }

    private static String connectionLabel(Io24State state) {
        switch (state.connectionStatus()) {
            case CONNECTED:
                return state.busy() ? "Working" : "Connected";
            case CONNECTING:
                return "Connecting";
            case ERROR:
                return "Needs attention";
            default:
                return "Disconnected";
        }
    }

    private static int connectionColor(Io24State state) {
        switch (state.connectionStatus()) {
            case CONNECTED:
                return R.color.accent;
            case CONNECTING:
                return R.color.warning;
            case ERROR:
                return R.color.danger;
            default:
                return R.color.text_secondary;
        }
    }

    private static String safeFileName(String value) {
        String cleaned = value.replaceAll("[^A-Za-z0-9._-]+", "-");
        return cleaned.isEmpty() ? "io24-scene" : cleaned;
    }
}
