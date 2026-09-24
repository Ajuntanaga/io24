package dev.ajuntanaga.io24;

import android.annotation.SuppressLint;
import android.app.AlertDialog;
import android.content.Context;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/** Whole-setup phone scenes and distinct front-panel preset-block controls. */
@SuppressLint("SetTextI18n")
final class PresetsView implements ControllerView {
    private static final String BLOCK_STATUS =
            "Block writes are reported as sent, not read back or power-cycle verified.";

    interface SceneActions {
        void apply(PresetCodec.Decoded scene);

        void export(PresetCodec.Decoded scene);

        void importScene();
    }

    private final View root;
    private final PresetStore store;
    private final CommandSink sink;
    private final SceneActions actions;
    private final EditText name;
    private final Spinner saved;
    private final ArrayAdapter<String> savedAdapter;
    private final TextView status;
    private final Spinner slotInput;
    private final Spinner slot;
    private final Switch slotEnabled;
    private final Button loadSlot;
    private final Button saveBlock;
    private final TextView deviceStatus;
    private Io24State state = Io24State.defaults();
    private boolean rendering;

    PresetsView(
            Context context,
            PresetStore store,
            CommandSink sink,
            SceneActions actions) {
        this.store = store;
        this.sink = sink;
        this.actions = actions;
        LinearLayout content = Ui.column(context);
        content.setPadding(Ui.dp(context, 16), Ui.dp(context, 12),
                Ui.dp(context, 16), Ui.dp(context, 24));
        content.addView(Ui.title(context, "Presets & setups"), Ui.match());
        content.addView(Ui.caption(context,
                "A scene is the whole setup saved on this phone. A device preset block is one input sound recalled by the io24's Preset button."),
                Ui.spaced(context));

        LinearLayout local = Ui.panel(context);
        local.addView(Ui.section(context, "Whole-setup scenes"), Ui.match());
        name = new EditText(context);
        name.setHint("Scene name");
        name.setSingleLine(true);
        name.setMaxLines(1);
        name.setTextColor(context.getColor(R.color.text_primary));
        name.setHintTextColor(context.getColor(R.color.text_secondary));
        name.setMinimumHeight(Ui.dp(context, 48));
        local.addView(name, Ui.match());
        Button saveButton = Ui.button(context, "Save current scene");
        saveButton.setOnClickListener(view -> save());
        local.addView(saveButton, Ui.spaced(context));
        saved = new Spinner(context);
        saved.setMinimumHeight(Ui.dp(context, 48));
        saved.setContentDescription("Saved phone scenes");
        savedAdapter = new ArrayAdapter<>(
                context,
                android.R.layout.simple_spinner_item,
                new ArrayList<>());
        savedAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        saved.setAdapter(savedAdapter);
        saved.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                if (position >= 0) {
                    name.setText(savedAdapter.getItem(position));
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        local.addView(saved, Ui.spaced(context));
        LinearLayout firstActions = Ui.row(context);
        Button load = Ui.button(context, "Load");
        load.setOnClickListener(view -> load());
        firstActions.addView(load, Ui.weight(1));
        Button rename = Ui.button(context, "Rename");
        rename.setOnClickListener(view -> rename());
        LinearLayout.LayoutParams renameParams = Ui.weight(1);
        renameParams.leftMargin = Ui.dp(context, 8);
        firstActions.addView(rename, renameParams);
        Button delete = Ui.button(context, "Delete");
        delete.setOnClickListener(view -> delete());
        LinearLayout.LayoutParams deleteParams = Ui.weight(1);
        deleteParams.leftMargin = Ui.dp(context, 8);
        firstActions.addView(delete, deleteParams);
        local.addView(firstActions, Ui.spaced(context));

        LinearLayout fileActions = Ui.row(context);
        Button export = Ui.button(context, "Export JSON");
        export.setOnClickListener(view -> export());
        fileActions.addView(export, Ui.weight(1));
        Button importButton = Ui.button(context, "Import JSON");
        importButton.setOnClickListener(view -> actions.importScene());
        LinearLayout.LayoutParams importParams = Ui.weight(1);
        importParams.leftMargin = Ui.dp(context, 8);
        fileActions.addView(importButton, importParams);
        local.addView(fileActions, Ui.spaced(context));
        status = Ui.caption(context, "Stored privately on this phone");
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        local.addView(status, Ui.spaced(context));
        content.addView(local, Ui.spaced(context));

        LinearLayout device = Ui.panel(context);
        device.addView(Ui.section(context, "Front-panel preset blocks"), Ui.match());
        device.addView(Ui.caption(context,
                "Each input has Block 1 and Block 2. Select changes the front-panel choice; firmware does not reapply that block's stored body. Save replaces the exact block you choose."),
                Ui.match());
        slotInput = spinner(context, new String[] {"Input 1", "Input 2"});
        slotInput.setContentDescription("Device preset input");
        slotInput.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                render(state);
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        device.addView(slotInput, Ui.spaced(context));
        slot = spinner(context, new String[] {"Block 1", "Block 2"});
        slot.setContentDescription("Front-panel preset block");
        device.addView(slot, Ui.spaced(context));
        loadSlot = Ui.button(context, "Select block for front-panel use");
        loadSlot.setOnClickListener(view -> sink.dispatch(Io24Command.setPresetSlot(
                slotInput.getSelectedItemPosition() + 1,
                deviceSlotIndex(
                        slotInput.getSelectedItemPosition() + 1,
                        slot.getSelectedItemPosition()))));
        device.addView(loadSlot, Ui.spaced(context));
        saveBlock = Ui.button(context, "Save current input to this block");
        saveBlock.setOnClickListener(view -> saveDeviceBlock(context));
        device.addView(saveBlock, Ui.spaced(context));
        slotEnabled = Ui.toggle(context, "Preset processing enabled");
        slotEnabled.setOnCheckedChangeListener((button, checked) -> {
            if (!rendering) {
                sink.dispatch(Io24Command.setPresetEnabled(
                        slotInput.getSelectedItemPosition() + 1,
                        checked));
            }
        });
        device.addView(slotEnabled, Ui.spaced(context));
        deviceStatus = Ui.caption(context,
                BLOCK_STATUS);
        deviceStatus.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        device.addView(deviceStatus, Ui.spaced(context));
        slot.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id) {
                if (!rendering) {
                    deviceStatus.setText(BLOCK_STATUS);
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
        content.addView(device, Ui.spaced(context));
        root = Ui.scroll(context, content);
        refreshNames();
    }

    @Override
    public View view() {
        return root;
    }

    @Override
    public void render(Io24State state) {
        this.state = state;
        boolean enabled = state.connectionStatus()
                == Io24State.ConnectionStatus.CONNECTED && !state.busy();
        int channel = slotInput.getSelectedItemPosition() + 1;
        rendering = true;
        slot.setSelection(relativeBlockIndex(
                channel, state.input(channel).presetSlot()), false);
        slotEnabled.setChecked(
                value(state, channel, "preset_enabled", 1.0f) >= 0.5f);
        rendering = false;
        slotInput.setEnabled(enabled);
        slot.setEnabled(enabled);
        loadSlot.setEnabled(enabled);
        saveBlock.setEnabled(enabled);
        slotEnabled.setEnabled(enabled);
        if (state.lastProof().startsWith("WRITE_SENT_UNVERIFIED")) {
            deviceStatus.setText(state.lastProof());
        }
    }

    void imported(PresetCodec.Decoded decoded) {
        status.setText("Imported " + decoded.name());
        refreshNames();
    }

    private void save() {
        String sceneName = name.getText().toString().trim();
        try {
            store.save(sceneName, state);
            status.setText("Saved " + sceneName + " privately on this phone");
            refreshNames();
            select(sceneName);
        } catch (IllegalArgumentException | IOException error) {
            status.setText(error.getMessage());
        }
    }

    private void load() {
        String selected = selectedName();
        if (selected == null) {
            status.setText("Save or select a phone scene first");
            return;
        }
        try {
            PresetCodec.Decoded decoded = store.load(selected);
            actions.apply(decoded);
            status.setText("Loaded " + decoded.name());
        } catch (IllegalArgumentException | IOException error) {
            status.setText(error.getMessage());
        }
    }

    private void rename() {
        String selected = selectedName();
        String next = name.getText().toString().trim();
        if (selected == null) {
            status.setText("Select a scene to rename");
            return;
        }
        try {
            store.rename(selected, next);
            status.setText("Renamed scene to " + next);
            refreshNames();
            select(next);
        } catch (IllegalArgumentException | IOException error) {
            status.setText(error.getMessage());
        }
    }

    private void delete() {
        String selected = selectedName();
        if (selected == null) {
            status.setText("Select a scene to delete");
            return;
        }
        try {
            store.delete(selected);
            status.setText("Deleted " + selected);
            name.setText("");
            refreshNames();
        } catch (IOException error) {
            status.setText(error.getMessage());
        }
    }

    private void saveDeviceBlock(Context context) {
        int channel = slotInput.getSelectedItemPosition() + 1;
        int block = slot.getSelectedItemPosition();
        int absoluteSlot = deviceSlotIndex(channel, block);
        if (state.input(channel).presetSlot() == absoluteSlot) {
            deviceStatus.setText(
                    "That block is playing now. Choose the other block before replacing it.");
            return;
        }
        Io24State.VoiceFxModel model = state.selectedVoiceFx();
        Io24State.VoiceFxState effect = state.voiceFx(model);
        if (state.voiceFxInput() == channel && effect.on()
                && model != Io24State.VoiceFxModel.TRANSFORMER
                && model != Io24State.VoiceFxModel.DELAY) {
            deviceStatus.setText(model.label()
                    + " has no decoded front-panel block body yet. Turn it off or save a phone scene instead.");
            return;
        }
        if (state.voiceFxInput() == channel && effect.on()
                && model == Io24State.VoiceFxModel.DELAY) {
            deviceStatus.setText(
                    "Delay cannot be stored active in a device block. Save a phone scene so the current rate can choose safe placement.");
            return;
        }
        String destination = "Input " + channel + " · Block " + (block + 1);
        new AlertDialog.Builder(context, R.style.Io24DialogTheme)
                .setTitle("Replace " + destination + "?")
                .setMessage(
                        "This writes the Fat Channel currently shown on this phone. The io24 cannot return the stored body, so success is WRITE_SENT_UNVERIFIED.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Replace block", (dialog, which) -> {
                    deviceStatus.setText("Sending " + destination + "…");
                    sink.dispatch(Io24Command.saveDeviceBlock(channel, block));
                })
                .show();
    }

    private void export() {
        String selected = selectedName();
        try {
            PresetCodec.Decoded decoded = selected == null
                    ? PresetCodec.decode(PresetCodec.encode(
                            name.getText().toString().trim(), state))
                    : store.load(selected);
            actions.export(decoded);
        } catch (IllegalArgumentException | IOException error) {
            status.setText(error.getMessage());
        }
    }

    private void refreshNames() {
        try {
            List<String> names = store.names();
            savedAdapter.clear();
            savedAdapter.addAll(names);
            savedAdapter.notifyDataSetChanged();
        } catch (IOException error) {
            status.setText(error.getMessage());
        }
    }

    private String selectedName() {
        Object selected = saved.getSelectedItem();
        return selected == null ? null : selected.toString();
    }

    private void select(String value) {
        int position = savedAdapter.getPosition(value);
        if (position >= 0) {
            saved.setSelection(position);
        }
    }

    private static Spinner spinner(Context context, String[] labels) {
        Spinner spinner = new Spinner(context);
        spinner.setMinimumHeight(Ui.dp(context, 48));
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
                context, android.R.layout.simple_spinner_item, labels);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(adapter);
        return spinner;
    }

    static int deviceSlotIndex(int channel, int block) {
        if (channel < 1 || channel > 2) {
            throw new IllegalArgumentException("Preset input must be 1 or 2");
        }
        if (block < 0 || block > 1) {
            throw new IllegalArgumentException("Preset block must be 0 or 1");
        }
        return (channel - 1) * 2 + block;
    }

    static int relativeBlockIndex(int channel, int deviceSlot) {
        int relative = deviceSlot - (channel - 1) * 2;
        return Math.max(0, Math.min(1, relative));
    }

    private static float value(
            Io24State state,
            int channel,
            String key,
            float fallback) {
        Float value = state.processing(channel).get(key);
        return value == null ? fallback : value;
    }
}
