import hashlib
import json
import struct
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
PACKAGE = ANDROID / "app/src/main/java/dev/ajuntanaga/io24"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


def _vector():
    return json.loads(
        (ANDROID / "protocol/io24-read-state-v1.json").read_text()
    )


def _build_reference_state_read(vector):
    state = vector["state_read"]
    blob_size = state["blob_size"]
    blob = struct.pack(
        "<IIII",
        int(state["blob_tag"], 16),
        blob_size,
        0,
        0,
    ) + bytes(blob_size - 16)
    payload = struct.pack(
        "<III",
        int(state["command_tag"], 16),
        int(state["block_tag"], 16),
        0,
    ) + blob
    return (
        struct.pack("<H", len(payload) + 8)
        + bytes((1, 1, state["uid"], 0, 0, 0))
        + payload
    )


def _build_reference_input2_mute(vector, uid, muted):
    write = vector["input2_mute_write"]
    blob = struct.pack(
        "<IIIIi",
        int(write["blob_tag"], 16),
        write["blob_size"],
        write["channel_index"],
        write["parameter_id"],
        int(muted),
    )
    payload = struct.pack(
        "<III",
        int(write["command_tag"], 16),
        int(write["block_tag"], 16),
        write["block_index"],
    ) + blob
    return (
        struct.pack("<H", len(payload) + 8)
        + bytes((1, 1, uid, 0, 0, 0))
        + payload
    )


def test_state_read_vector_matches_the_proven_linux_wire_contract():
    vector = _vector()
    frame = _build_reference_state_read(vector)

    assert vector["device"] == {"vendor_id": "194f", "product_id": "0422"}
    assert vector["control_interface"] == {
        "number": 5,
        "alternate_setting": 1,
        "endpoint_out": "01",
        "endpoint_in": "81",
    }
    assert len(frame) == 2048
    assert frame[:36].hex() == (
        "0008010101000000507465476c70704100000000"
        "7453614aec0700000000000000000000"
    )
    assert hashlib.sha256(frame).hexdigest() == (
        "0cc107bdd645d9df161d4ede8355226c3c6f56166f9359a331d9e077a0230bb2"
    )


def test_input2_mute_vector_is_fixed_to_the_proven_parameter():
    vector = _vector()
    muted = _build_reference_input2_mute(vector, 17, True)
    unmuted = _build_reference_input2_mute(vector, 18, False)

    assert muted.hex() == (
        "2800010111000000"
        "507465536c70704100000000"
        "6972615014000000010000000700000001000000"
    )
    assert unmuted.hex() == (
        "2800010112000000"
        "507465536c70704100000000"
        "6972615014000000010000000700000000000000"
    )


def test_android_protocol_core_exposes_bounded_native_framing():
    frame = (PACKAGE / "PaeFrame.java").read_text()
    protocol = (PACKAGE / "Io24Protocol.java").read_text()
    commands = (PACKAGE / "Io24Command.java").read_text()

    assert "buildStateRead" in frame
    assert "parseStateReply" in frame
    assert "buildBlockWrite" in frame
    assert "parseSetReply" in frame
    assert "encodeTransaction" in protocol
    assert "VOICE_FX_REPLACE_SETTLE_MS = 60" in protocol
    assert "enum Kind" in commands
    assert "Map<String, Range> PROCESSING" in commands
    for source in (frame, protocol, commands):
        assert "FRst" not in source


def test_manifest_has_usb_host_support_without_network_permission():
    manifest = ElementTree.parse(
        ANDROID / "app/src/main/AndroidManifest.xml"
    ).getroot()

    permissions = {
        item.attrib[ANDROID_NS + "name"]
        for item in manifest.findall("uses-permission")
    }
    features = {
        item.attrib[ANDROID_NS + "name"]
        for item in manifest.findall("uses-feature")
    }
    assert "android.permission.INTERNET" not in permissions
    assert features == {"android.hardware.usb.host"}


def test_usb_transport_claims_only_the_unforced_control_interface():
    source = (PACKAGE / "Io24UsbProbe.java").read_text()

    assert "VENDOR_ID = 0x194f" in source
    assert "PRODUCT_ID = 0x0422" in source
    assert "CONTROL_INTERFACE = 5" in source
    assert "CONTROL_ALTERNATE = 1" in source
    assert "ENDPOINT_OUT = 0x01" in source
    assert "ENDPOINT_IN = 0x81" in source
    assert "claimInterface(controlInterface, false)" in source
    assert "setInterface(controlInterface)" in source
    assert "setInput2Mute" in source
    assert "MUTE_SETTLE_MS = 350" in source
    assert "Io24Protocol.encodeTransaction" in source
    for forbidden in ("claimInterface(controlInterface, true)", "FRst"):
        assert forbidden not in source


def test_each_native_write_drains_its_reply_before_fresh_state():
    source = (PACKAGE / "Io24UsbProbe.java").read_text()
    method = source.split(
        "public synchronized CommandResult execute", 1
    )[1].split("public synchronized boolean setInput2Mute", 1)[0]

    drain = method.index("readOptionalSetpReply")
    state_read = method.index("readFreshState")
    assert drain < state_read
    assert "PaeFrame.parseSetReply" in source


def test_usb_access_has_no_automatic_attach_entrypoint():
    manifest = ElementTree.parse(
        ANDROID / "app/src/main/AndroidManifest.xml"
    ).getroot()
    activity = manifest.find("application/activity")

    assert activity is not None
    actions = {
        action.attrib[ANDROID_NS + "name"]
        for action in activity.findall("intent-filter/action")
    }
    metadata = {
        item.attrib[ANDROID_NS + "name"]
        for item in activity.findall("meta-data")
    }
    assert "android.hardware.usb.action.USB_DEVICE_ATTACHED" not in actions
    assert "android.hardware.usb.action.USB_DEVICE_ATTACHED" not in metadata
    assert not (ANDROID / "app/src/main/res/xml/device_filter.xml").exists()
    assert "ACTION_USB_DEVICE_ATTACHED" not in (
        PACKAGE / "MainActivity.java"
    ).read_text()


def test_legacy_receiver_branch_has_a_narrow_lint_suppression():
    source = (PACKAGE / "MainActivity.java").read_text()

    assert 'import android.annotation.SuppressLint;' in source
    assert (
        '@SuppressLint("UnspecifiedRegisterReceiverFlag")\n'
        "    private void registerUsbReceiver()"
    ) in source


def test_front_facing_android_metadata_is_resource_backed():
    manifest = ElementTree.parse(
        ANDROID / "app/src/main/AndroidManifest.xml"
    ).getroot()
    application = manifest.find("application")
    strings = ElementTree.parse(
        ANDROID / "app/src/main/res/values/strings.xml"
    ).getroot()
    names = {item.attrib["name"] for item in strings.findall("string")}

    assert application is not None
    assert application.attrib[ANDROID_NS + "label"] == "@string/app_name"
    assert application.attrib[ANDROID_NS + "icon"] == "@drawable/ic_io24"
    assert application.attrib[ANDROID_NS + "roundIcon"] == "@drawable/ic_io24"
    assert application.attrib[ANDROID_NS + "dataExtractionRules"] == (
        "@xml/data_extraction_rules"
    )
    assert application.attrib[ANDROID_NS + "fullBackupContent"] == "false"
    assert {
        "app_name",
        "status_connect_device",
        "status_device_ready",
        "status_device_missing",
        "status_permission_denied",
        "status_waiting_permission",
        "status_simulated_ready",
    } <= names


def test_five_screen_shell_has_no_browser_or_network_runtime():
    activity = (PACKAGE / "MainActivity.java").read_text()

    for label in ("MIXER", "FAT_CHANNEL", "EFFECTS", "PRESETS", "DEVICE"):
        assert label in activity
    assert "WindowInsets.Type.systemBars()" in activity
    assert "connectionDetail.setText(state.statusMessage())" in activity
    assert "WebView" not in activity
    assert "http://" not in activity
    assert "https://" not in activity


def test_native_dsp_surface_is_allowlisted_and_rate_guarded():
    dsp = (PACKAGE / "NativeDsp.java").read_text()
    protocol = (PACKAGE / "Io24Protocol.java").read_text()
    command = (PACKAGE / "Io24Command.java").read_text()
    effects = (PACKAGE / "EffectRackView.java").read_text()

    for tag in (
        "TAG_VOFX", "TAG_GODV", "TAG_MAY4", "TAG_BOTA", "TAG_BOTB",
        "TAG_BOTC", "TAG_VECH", "TAG_VRVB", "TAG_CPXT", "TAG_GATE",
    ):
        assert tag in dsp
    assert "twoAudioQuantaMillis" in protocol
    assert "canRunNatively" in protocol
    assert "sampleRateConfirmed" in command
    assert "enabling it disables other Voice FX models" in effects
    assert 'addWetDry(context)' in effects


def test_android_preset_ui_maps_two_blocks_per_input_and_names_scene_scope():
    presets = (PACKAGE / "PresetsView.java").read_text()
    native = (PACKAGE / "NativePreset.java").read_text()

    assert '"Whole-setup scenes"' in presets
    assert '"Front-panel preset blocks"' in presets
    assert 'new String[] {"Block 1", "Block 2"}' in presets
    assert "deviceSlotIndex(" in presets
    assert '"Save current input to this block"' in presets
    assert "Io24Command.saveDeviceBlock(channel, block)" in presets
    assert "WRITE_SENT_UNVERIFIED" in presets
    assert "Native preset body is too large" in native
    assert "Delay cannot be stored active in a device block" in native
    assert '"Select block for front-panel use"' in presets
    assert '"Load selected block"' not in presets
    assert '"Slot 3"' not in presets
    assert '"Slot 4"' not in presets


def test_emulator_transport_is_debug_only_and_requires_an_explicit_extra():
    activity = (PACKAGE / "MainActivity.java").read_text()
    simulator = (PACKAGE / "SimulatedIo24Control.java").read_text()

    assert "ApplicationInfo.FLAG_DEBUGGABLE" in activity
    assert "EXTRA_SIMULATED_IO24" in activity
    assert "getBooleanExtra(EXTRA_SIMULATED_IO24, false)" in activity
    assert "SimulatedIo24Control" in activity
    assert "android.hardware.usb" not in simulator
    assert "DeviceState" in simulator


def test_emulator_helper_targets_only_the_named_local_avd():
    helper = (ANDROID / "emulator.sh").read_text()

    assert "io24_blu_api35" in helper
    assert "emulator-5556" in helper
    assert "SIMULATED_IO24" in helper
    assert "SIMULATED_READBACK_FAILURE" in helper
    assert "SIMULATED_DELAY_96" in helper
    assert "delay96" in helper
    for forbidden in (
        'adb devices',
        '"$ADB" -d',
        '"$ADB" -e',
        'USB_DEVICE_ATTACHED',
    ):
        assert forbidden not in helper


def test_voice_fx_input_assignment_uses_the_uc_owner_object():
    protocol = (PACKAGE / "Io24Protocol.java").read_text()

    assert "scalarNative(\n                        0, 12, command.channel() - 1" in protocol
    assert "scalarNative(\n                        command.channel() - 1, 12" not in protocol


def test_rate_confirmation_and_usb_permission_fail_safe():
    state = (PACKAGE / "Io24State.java").read_text()
    device = (PACKAGE / "DeviceView.java").read_text()
    activity = (PACKAGE / "MainActivity.java").read_text()
    manifest = ElementTree.parse(
        ANDROID / "app/src/main/AndroidManifest.xml"
    ).getroot()
    android_activity = manifest.find("application/activity")

    assert "sampleRateConfirmed" in state
    assert '"Confirm current audio rate…"' in device
    assert "PendingIntent.FLAG_MUTABLE" in activity
    assert "usbManager.hasPermission(device)" in activity
    assert android_activity is not None
    config_changes = set(android_activity.attrib[
        ANDROID_NS + "configChanges"].split("|"))
    assert {
        "density", "keyboardHidden", "orientation", "screenLayout",
        "screenSize", "smallestScreenSize", "uiMode",
    } <= config_changes


def test_scene_planner_keeps_rate_and_front_panel_blocks_out_of_scene_apply():
    planner = (PACKAGE / "Io24ScenePlanner.java").read_text()

    assert "Io24Command.setSampleRate" not in planner
    assert "Io24Command.setPresetSlot" not in planner
