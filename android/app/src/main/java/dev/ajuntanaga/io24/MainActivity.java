package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.os.Build;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** One-screen io24 controller with one explicit, readback-verified write. */
public final class MainActivity extends Activity {
    private static final String ACTION_USB_PERMISSION =
            "dev.ajuntanaga.io24.USB_PERMISSION";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private UsbManager usbManager;
    private Io24UsbProbe probe;
    private TextView status;
    private Button inspectButton;
    private Button input2MuteButton;
    private Button disconnectButton;
    private boolean input2Muted;
    private ProbeResult lastResult;

    private final BroadcastReceiver usbReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            UsbDevice device = usbDeviceExtra(intent);
            if (ACTION_USB_PERMISSION.equals(intent.getAction())) {
                boolean granted = intent.getBooleanExtra(
                        UsbManager.EXTRA_PERMISSION_GRANTED, false);
                if (granted && Io24UsbProbe.matches(device)) {
                    startProbe(device);
                } else {
                    showIdle(getString(R.string.status_permission_denied));
                }
            } else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(intent.getAction())
                    && Io24UsbProbe.matches(device)) {
                disconnect(getString(R.string.status_device_detached));
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        usbManager = (UsbManager) getSystemService(Context.USB_SERVICE);
        setContentView(buildContent());
        registerUsbReceiver();
        showIdle(initialStatus(getIntent()));
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(intent.getAction())
                && Io24UsbProbe.matches(usbDeviceExtra(intent))) {
            showIdle(getString(R.string.status_device_ready));
        }
    }

    @Override
    protected void onDestroy() {
        unregisterReceiver(usbReceiver);
        executor.shutdownNow();
        if (probe != null) {
            probe.close();
            probe = null;
        }
        super.onDestroy();
    }

    private View buildContent() {
        int spacing = dp(24);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(spacing, spacing, spacing, spacing);

        TextView title = new TextView(this);
        title.setText(R.string.app_name);
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 26);
        if (Build.VERSION.SDK_INT >= 28) {
            title.setAccessibilityHeading(true);
        }
        content.addView(title, matchWidth());

        TextView description = new TextView(this);
        description.setText(R.string.app_description);
        description.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        LinearLayout.LayoutParams descriptionLayout = matchWidth();
        descriptionLayout.topMargin = dp(12);
        content.addView(description, descriptionLayout);

        status = new TextView(this);
        status.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        LinearLayout.LayoutParams statusLayout = matchWidth();
        statusLayout.topMargin = spacing;
        statusLayout.bottomMargin = spacing;
        content.addView(status, statusLayout);

        inspectButton = new Button(this);
        inspectButton.setText(R.string.action_inspect);
        inspectButton.setOnClickListener(view -> inspect());
        content.addView(inspectButton, matchWidth());

        input2MuteButton = new Button(this);
        input2MuteButton.setText(R.string.action_mute_input2);
        input2MuteButton.setEnabled(false);
        input2MuteButton.setOnClickListener(view -> writeInput2Mute());
        LinearLayout.LayoutParams muteLayout = matchWidth();
        muteLayout.topMargin = dp(8);
        content.addView(input2MuteButton, muteLayout);

        disconnectButton = new Button(this);
        disconnectButton.setText(R.string.action_disconnect);
        disconnectButton.setOnClickListener(
                view -> disconnect(getString(R.string.status_control_released)));
        LinearLayout.LayoutParams disconnectLayout = matchWidth();
        disconnectLayout.topMargin = dp(8);
        content.addView(disconnectButton, disconnectLayout);
        return content;
    }

    private void inspect() {
        UsbDevice device = Io24UsbProbe.findDevice(usbManager);
        if (device == null) {
            showIdle(getString(R.string.status_device_missing));
            return;
        }
        if (usbManager.hasPermission(device)) {
            startProbe(device);
            return;
        }
        status.setText(R.string.status_waiting_permission);
        inspectButton.setEnabled(false);
        PendingIntent permissionIntent = PendingIntent.getBroadcast(
                this,
                0,
                new Intent(ACTION_USB_PERMISSION).setPackage(getPackageName()),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        usbManager.requestPermission(device, permissionIntent);
    }

    private void startProbe(UsbDevice device) {
        status.setText(R.string.status_reading);
        inspectButton.setEnabled(false);
        disconnectButton.setEnabled(false);
        executor.execute(() -> {
            Io24UsbProbe candidate = new Io24UsbProbe(usbManager);
            try {
                ProbeResult result = candidate.connectAndRead(device);
                runOnUiThread(() -> {
                    if (isFinishing() || isDestroyed()) {
                        candidate.close();
                        return;
                    }
                    if (probe != null) {
                        probe.close();
                    }
                    probe = candidate;
                    showConnected(result);
                });
            } catch (Io24UsbProbe.ProbeException error) {
                candidate.close();
                runOnUiThread(() -> showIdle(getString(
                        R.string.status_probe_failed, error.getMessage())));
            }
        });
    }

    private void writeInput2Mute() {
        Io24UsbProbe activeProbe = probe;
        if (activeProbe == null || !activeProbe.isConnected()) {
            showIdle(getString(R.string.status_control_released));
            return;
        }

        boolean requestedMute = !input2Muted;
        status.setText(R.string.status_input2_mute_writing);
        input2MuteButton.setEnabled(false);
        disconnectButton.setEnabled(false);
        executor.execute(() -> {
            try {
                boolean verifiedMute = activeProbe.setInput2Mute(requestedMute);
                runOnUiThread(() -> {
                    if (probe != activeProbe || lastResult == null) {
                        return;
                    }
                    input2Muted = verifiedMute;
                    showConnected(new ProbeResult(
                            lastResult.protocolVersion(),
                            lastResult.maxCommandLength(),
                            lastResult.maxResponseLength(),
                            lastResult.responseLength(),
                            lastResult.stateSlotCount(),
                            verifiedMute));
                });
            } catch (Io24UsbProbe.ProbeException error) {
                activeProbe.close();
                runOnUiThread(() -> {
                    if (probe == activeProbe) {
                        probe = null;
                    }
                    showIdle(getString(
                            R.string.status_input2_mute_unverified,
                            error.getMessage()));
                });
            }
        });
    }

    private void showConnected(ProbeResult result) {
        lastResult = result;
        input2Muted = result.input2Muted();
        status.setText(getString(
                R.string.status_connected,
                result.protocolVersion(),
                result.maxCommandLength(),
                result.maxResponseLength(),
                result.responseLength(),
                result.stateSlotCount(),
                getString(input2Muted ? R.string.state_on : R.string.state_off)));
        input2MuteButton.setText(input2Muted
                ? R.string.action_unmute_input2
                : R.string.action_mute_input2);
        inspectButton.setEnabled(false);
        input2MuteButton.setEnabled(true);
        disconnectButton.setEnabled(true);
    }

    private void disconnect(String message) {
        if (probe != null) {
            probe.close();
            probe = null;
        }
        lastResult = null;
        showIdle(message);
    }

    private void showIdle(String message) {
        status.setText(message);
        inspectButton.setEnabled(true);
        input2MuteButton.setEnabled(false);
        disconnectButton.setEnabled(false);
    }

    private String initialStatus(Intent intent) {
        if (intent != null
                && UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(intent.getAction())
                && Io24UsbProbe.matches(usbDeviceExtra(intent))) {
            return getString(R.string.status_device_ready);
        }
        return Io24UsbProbe.findDevice(usbManager) == null
                ? getString(R.string.status_connect_device)
                : getString(R.string.status_device_ready);
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

    private LinearLayout.LayoutParams matchWidth() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
