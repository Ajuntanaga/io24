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


def test_android_protocol_core_exposes_read_and_only_the_bounded_write():
    source = (PACKAGE / "PaeFrame.java").read_text()

    assert "buildStateRead" in source
    assert "parseStateReply" in source
    assert "0x47657450" in source  # GetP
    assert "0x4170706c" in source  # Appl
    assert "0x4a615374" in source  # JaSt
    assert "0x52706c79" in source  # Rply
    assert "buildInput2MuteWrite" in source
    assert "0x53657450" in source  # SetP
    assert "0x50617269" in source  # Pari
    for forbidden in ("FRst", "setParam", "parameterId", "channelIndex"):
        assert forbidden not in source


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
    for forbidden in ("claimInterface(controlInterface, true)", "FRst"):
        assert forbidden not in source


def test_device_filter_matches_only_the_normal_io24_identity():
    root = ElementTree.parse(
        ANDROID / "app/src/main/res/xml/device_filter.xml"
    ).getroot()
    devices = root.findall("usb-device")

    assert len(devices) == 1
    assert devices[0].attrib == {
        "vendor-id": "0x194f",
        "product-id": "0x0422",
    }


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
    activity = (PACKAGE / "MainActivity.java").read_text()

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
        "app_description",
        "action_inspect",
        "action_disconnect",
        "action_mute_input2",
        "action_unmute_input2",
        "status_connected",
        "status_input2_mute_writing",
        "status_input2_mute_unverified",
        "status_probe_failed",
    } <= names
    assert '.setText("' not in activity


def test_input2_mute_is_an_explicit_disabled_until_connected_action():
    activity = (PACKAGE / "MainActivity.java").read_text()

    assert "input2MuteButton" in activity
    assert "setInput2Mute" in activity
    assert "input2MuteButton.setEnabled(false)" in activity
