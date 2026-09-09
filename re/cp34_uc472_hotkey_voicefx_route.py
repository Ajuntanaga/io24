#!/usr/bin/env python3
"""Source-bind UC 4.7.2 Hot Key to its VoiceFX model-selection route.

This exact-version analyzer reads retained vendor files without loading them.
It proves that ``presetHotKey`` is a full-channel snapshot override, that the
selected VoiceFX algorithm is host component state (``fxmodel`` /
``voicefx.__classid``), and that selecting a model emits ``VoFx`` before the
selected mutable child receives its own state.

It does not execute Universal Control, access Wine, touch USB/audio hardware,
or prove runtime event propagation, device storage, recall, activation, or
audibility.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ElementTree


RE_DIR = Path(__file__).resolve().parent
if str(RE_DIR) not in sys.path:
    sys.path.insert(0, str(RE_DIR))

import cp34_uc5_serializer_comparison as pe_helpers  # noqa: E402
import cp34_uc472_save_assign_ui_route as ui_helpers  # noqa: E402


class AnalysisError(ValueError):
    """An input differs from the pinned UC 4.7.2 source or expected route."""


SOURCES = {
    "DSP": {
        "size": 4_979_672,
        "sha256": "de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28",
    },
    "panel": {
        "size": 41_828_312,
        "sha256": "52e48cb1453b815abc4b55fd0232131e11115d1aceb2eb0ed899750db6c08dd8",
    },
    "component model": {
        "size": 20_450,
        "sha256": "55388fd3fdcf6d5b466991db886d50a2d8c787afe50390cde554e46d74ff2bfc",
    },
    "FX params": {
        "size": 13_925,
        "sha256": "3f5f99bd6efdfd54b65adf15c82d8b9da36116b25b11e3c88a4ad441b9decd89",
    },
}

IMAGE_BASE = 0x180000000
PARAM_CHANGE = 0x180041160
PARAM_DISPATCH_TABLE = 0x1800414B8
PARAM_DISPATCH_MAP = 0x1800414DC
HOTKEY_HANDLER = 0x1800412B0
PROCESSING_CHANNEL_HANDLER = 0x18004145E
VOICEFX_OWNERSHIP_SWITCH = 0x18003E6C0
HOTKEY_CHANNEL_LOAD = 0x1800424B0
HOTKEY_CHANNEL_SAVE = 0x180042680
STATE_SERIALIZER = 0x18002E270
STATE_DESERIALIZER = 0x18002E690
STORE_PRESET_SERIALIZER_CALL = 0x18003B5B3
FXMODEL_HANDLER = 0x1800491F0
FXMODEL_FACTORY = 0x180049260
VOICEFX_DESERIALIZER = 0x180049870
MODEL_TABLE = 0x1800EF430

MODEL_CLASS_IDS = {
    0: "{66A10093-D461-4CAC-A80C-91F6A1BB37E5}",
    1: "{509018B0-0DE1-4D26-9DDF-D782476D3C98}",
    2: "{981F8B8F-D1D8-4634-BB04-2148AF2123E3}",
    3: "{4B4CAD90-7709-451F-A7DD-AF6F0E954F57}",
    4: "{491FED97-6761-4FF6-91E1-E155891291AA}",
    5: "{98A527BA-2D6E-4B35-BB26-251EC081A067}",
}

EXACT_BYTES = {
    # Parameter descriptors 109..151 dispatch through a byte map and a
    # relative-address table. Parameter 151 is map index 42.
    0x180041188: "488b4218448b48044183c1934183f92a",
    0x1800411B4: "4963c10fb68402dc1404008b8c82b81404004803caff",

    # Hot Key on selects complete-channel +0x180 (rdi is complete-channel +8).
    # Off resolves parameter 150 and selects active slot * 0x38 at +0x2d8.
    0x1800412B0: "498b06498bceff90800000000f57c9",
    0x1800412C4: "488d9f78010000eb6c",
    0x1800412CD: "488d4f30ba96000000e8c5d10100",
    0x18004131A: "3b99e00200007d104863c3486bd838480399d8020000eb07",
    # Selected snapshot enters the generic deserializer, then channel vtable
    # +0x130 performs the class-specific post-apply operation.
    0x18004133E: "4533c0488d4ff8488bd3e843d3feff488b47f8488d4ff8488bd3ff9030010000",

    # Per-channel VoiceFX ownership is selected by processingChannel == 0.
    # Initial channel setup reads parameter 149, turns equality with zero into
    # a boolean, and calls the VoiceFX ownership switch.
    0x180040729: "ba95000000488d4b38e869dd0100488b08488b9180000000488bc8ffd2f30f2cc085c00f94c2488bcbe869dfffff",
    # The switch resolves voicefxopt, marks its fxmodel parameter active only
    # on the owning channel, and either selects parameter 450's current model
    # or installs the host no-model sentinel -1.
    0x18003E6CC: "488d1585723f00ff50204885c0747d488b08ba5378464948895c24304c8b01488bc841ffd0",
    0x18003E6F9: "488b88e0000000488b114c8b4240400fb6d741ffd04084ff7433",
    0x18003E713: "488d4b38bac2010000e87ffd0100488b08488b9180000000488bc8ffd2f30f2cd0488bcb488b5c24304883c4205fe91aab0000",
    0x18003E746: "baffffffff488bcbe80dab0000",
    # Parameter 149's dispatcher marks the channel for a later routing
    # refresh. The refresh again evaluates value == 0 and calls the same
    # ownership switch; voicefx.on is not this channel-selection predicate.
    0x18004145E: "c687b501000001eb0c",
    0x18004193F: "ba95000000e857cb0100488b084c8b4138488bc841ffd084c07445488d8fe0feffffba95000000e835cb0100488b08488b9180000000488bc8ffd2f30f2cc085c0751db201eb1b",
    0x18004199F: "32d2488d8fa8feffffe813cdffff",

    # Channel load recognizes hotkey, owns a snapshot at +0x180, resolves title
    # ID 152 and active toggle ID 151, and captures active state with the same
    # serializer used by StorePreset.
    0x180042509: "488d3da43f3f00",
    0x180042582: "498dbe800100004533c0488b0733",
    0x1800425B2: "498d4e38ba98000000e8e0be0100",
    0x1800425E6: "ba97000000498d4e38e8acbe0100",
    0x18004261A: "498bd6498d8e80010000e847bcfeff",

    # Channel save explicitly creates and closes a nested hotkey record.
    0x1800426C3: "4533c94c8d05e73d3f0033d241ff",
    0x180042830: "4533c0488d157a3c3f00ff108b4d",
    0x18004288B: "488b014533c0488d151c3c3f00ff",

    # fxmodel parameter 450 invokes the model factory.
    0x180049208: "4183f8027526488b4218817804c20100007519488b",
    0x180049227: "f30f2cd0488d4ef8e82c000000",
    # model+1 <= 6 admits exactly -1 and 0..5.
    0x1800492BE: "418d450183f8060f87fb040000",

    # The model is installed as the mutable voicefx child. -1 skips VoFx;
    # otherwise block 201 / index 0 / VoFx / size 16 carries the model number.
    0x18004970B: "4c8bcf4c8bc3488d1550c23e00498bcee860e9ffff",
    0x180049720: "4183fdff0f849c000000",
    0x180049752: "48c7442470c9000000c744242078466f5648c74424241000000044896c242c",
    0x18004979E: "488b03488bcbff503084c0751b488b8f900200004885c9740f4c8d442470488d542420e85a9c0000",

    # Serialized state lookup: voicefx, then __classid, then mapping table.
    0x1800498A7: "4c896424704c8d25b5c03e00c644242200",
    0x180049940: "488b3e488d154e0d3f00488d7608488b4f48e80b9c08",
    0x1800499C7: "498b8fe0000000488d1d5b5a0a00488b01ff9080000000f30f",
    0x1800499E2: "488d059ff13e00",
    0x180049A39: "498b4e28488b9c24900000004885c97415488b014533c94d8bc4ba706d6f43ff500884c0741a498b8fe000000041b001660f6ecf0f5bc9488b01ff90a8000000",
}


def _require(condition, message):
    if not condition:
        raise AnalysisError(message)


def _identity(label, data):
    expected = SOURCES[label]
    _require(len(data) == expected["size"], "%s size differs" % label)
    digest = hashlib.sha256(data).hexdigest()
    _require(digest == expected["sha256"], "%s SHA-256 differs" % label)
    return {"size": len(data), "sha256": digest}


def _parse_pe(data):
    try:
        image_base, sections = pe_helpers._parse_pe(data)
    except pe_helpers.PeAnalysisError as error:
        raise AnalysisError(str(error)) from error
    _require(image_base == IMAGE_BASE, "DSP image base differs")
    return image_base, sections


def _section_bytes(image_base, sections, address, size):
    try:
        return pe_helpers._section_bytes(image_base, sections, address, size)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _require_bytes(image_base, sections, address, expected_hex):
    expected = bytes.fromhex(expected_hex)
    actual = _section_bytes(image_base, sections, address, len(expected))
    _require(actual == expected, "instruction bytes differ at %#x" % address)


def _require_direct_target(image_base, sections, address, target):
    try:
        pe_helpers._require_direct_target(image_base, sections, address, target)
    except pe_helpers.AnalysisError as error:
        raise AnalysisError(str(error)) from error


def _ascii(image_base, sections, address, expected):
    actual = _section_bytes(image_base, sections, address, len(expected) + 1)
    _require(actual == expected.encode("ascii") + b"\0",
             "ASCII literal differs at %#x" % address)


def _component_models(data):
    start_tag = b"<uc:ComponentModel"
    end_tag = b"</uc:ComponentModel>"
    roots = []
    cursor = 0
    while True:
        start = data.find(start_tag, cursor)
        if start < 0:
            break
        end = data.find(end_tag, start)
        _require(end >= 0, "component-model XML document is unterminated")
        try:
            roots.append(ElementTree.fromstring(data[start:end + len(end_tag)]))
        except ElementTree.ParseError as error:
            raise AnalysisError("component-model XML is invalid") from error
        cursor = end + len(end_tag)
    _require(roots, "component-model XML document is absent")
    return roots


def _first_component_model(data):
    return _component_models(data)[0]


def _parameter_ids(root):
    namespace = {"uc": "http://www.presonus.com/xml/uc"}
    lists = {
        node.attrib["id"]: node
        for node in root.findall(".//uc:ParamList", namespace)
    }
    analog = lists.get("AnalogInputChannel")
    selector = lists.get("InsertFXSelector")
    _require(analog is not None and selector is not None,
             "required component parameter lists are absent")

    analog_start = int(analog.attrib["starttag"])
    analog_ids = {
        node.attrib["id"]: analog_start + index
        for index, node in enumerate(analog.findall("uc:Param", namespace))
    }
    selector_start = int(selector.attrib["starttag"])
    selector_ids = {
        node.attrib["id"]: selector_start + index
        for index, node in enumerate(selector.findall("uc:Param", namespace))
    }
    expected = {
        "processingChannel": 149,
        "activePresetSlotIndex": 150,
        "presetHotKey": 151,
        "presetHotKeyTitle": 152,
    }
    _require({name: analog_ids.get(name) for name in expected} == expected,
             "AnalogInputChannel Hot Key parameter IDs differ")
    _require(selector_ids.get("fxmodel") == 450,
             "InsertFXSelector fxmodel parameter ID differs")

    template = root.find(".//uc:Template[@id='MicInputDSP']", namespace)
    _require(template is not None, "MicInputDSP template is absent")
    children = {node.attrib["id"]: node for node in template.findall("uc:Component", namespace)}
    _require(children.get("voicefxopt") is not None and
             children["voicefxopt"].attrib.get("paramlist") == "InsertFXSelector",
             "voicefxopt selector component differs")
    _require(children.get("voicefx") is not None and
             "mutable" in children["voicefx"].attrib.get("flags", "").split(),
             "voicefx mutable child differs")

    return {
        **expected,
        "fxmodel": selector_ids["fxmodel"],
        "voicefx_child_mutable": True,
        "voicefx_selector_component": "voicefxopt",
    }


def _validate_enable_parameter(data):
    namespace = {"uc": "http://www.presonus.com/xml/uc"}
    matches = [
        root.findall(".//uc:ParamList[@id='VoiceOfGod']/uc:Param", namespace)
        for root in _component_models(data)
    ]
    matches = [params for params in matches if params]
    _require(len(matches) == 1, "VoiceOfGod parameter list identity differs")
    params = matches[0]
    fields = [node.attrib["id"] for node in params]
    _require(fields == ["on", "lows", "width", "mix"],
             "VoiceOfGod parameter fields differ")
    on = params[0]
    _require(on.attrib.get("type") == "toggle" and
             "storable" in on.attrib.get("flags", "").split(),
             "voicefx.on storage semantics differ")


def _embedded_ui(panel):
    try:
        _, sections = ui_helpers._parse_pe("panel", panel)
        leaves = ui_helpers._resource_leaves(panel, sections)
        skin = [leaf for leaf in leaves
                if leaf["path"] == (10, "DEFAULT.SKIN", 0x409)]
        _require(len(skin) == 1, "DEFAULT.SKIN resource identity differs")
        _, xml = ui_helpers._parse_package(skin[0]["data"])
        root = ElementTree.fromstring(xml)
    except (ui_helpers.AnalysisError, ElementTree.ParseError) as error:
        raise AnalysisError(str(error)) from error

    toggles = [node for node in root.iter("Toggle")
               if node.attrib.get("name") == "presetHotKey"]
    _require(len(toggles) == 1, "presetHotKey UI toggle differs")
    options = toggles[0].attrib.get("options", "").split()
    _require(options == ["momentary", "transparent"],
             "presetHotKey UI options differ")

    slots = [int(node.attrib["value"])
             for node in root.iter("RadioButton")
             if node.attrib.get("name") == "presetSlot"]
    _require(sorted(set(slots)) == [1, 2, 3, 4] and len(slots) == 8,
             "normal preset-slot UI bindings differ")
    selectors = [node.attrib.get("style") for node in root.iter("SelectBox")
                 if node.attrib.get("name") == "presets/preset"]
    _require("BigKnobSelectBox.HotKey" in selectors,
             "Hot Key preset selector style is absent")
    knobs = [node for node in root.iter("Knob")
             if node.attrib.get("name") == "presets/preset"]
    _require(knobs and all("endless" in node.attrib.get("options", "").split()
                           for node in knobs),
             "preset selector knob binding differs")
    return {
        "hotkey_control": "presetHotKey",
        "hotkey_options": options,
        "normal_slot_values": sorted(set(slots)),
        "preset_select_path": "presets/preset",
        "hotkey_selector_style": "BigKnobSelectBox.HotKey",
        "same_endless_knob_path": True,
    }


def _model_class_ids(image_base, sections):
    raw = _section_bytes(image_base, sections, MODEL_TABLE, 6 * 16)
    result = {}
    for index in range(6):
        string_address, model, reserved = struct.unpack_from("<QII", raw, index * 16)
        _require(model == index and reserved == 0,
                 "VoiceFX class-id table entry %d differs" % index)
        text = _section_bytes(image_base, sections, string_address, 39)
        _require(text[-1:] == b"\0", "VoiceFX class-id string is unterminated")
        class_id = text[:-1].decode("ascii")
        _require(class_id == MODEL_CLASS_IDS[index],
                 "VoiceFX class-id %d differs" % index)
        result[str(index)] = class_id
    return result


def analyze(dsp, panel, component_model, fx_params):
    """Return the exact, hardware-free Hot Key and VoiceFX state report."""
    sources = {
        "dsp": _identity("DSP", dsp),
        "panel": _identity("panel", panel),
        "component_model": _identity("component model", component_model),
        "fx_params": _identity("FX params", fx_params),
    }
    image_base, sections = _parse_pe(dsp)
    for address, expected in EXACT_BYTES.items():
        _require_bytes(image_base, sections, address, expected)

    dispatch_map = _section_bytes(image_base, sections, PARAM_DISPATCH_MAP, 43)
    expected_map = bytes.fromhex(
        "0008010808080808080808080808080808080808080808080808080808080802"
        "0808080308080404050607"
    )
    _require(dispatch_map == expected_map, "parameter dispatch map differs")
    dispatch_index = 151 - 109
    dispatch_case = dispatch_map[dispatch_index]
    table = struct.unpack(
        "<9i", _section_bytes(image_base, sections, PARAM_DISPATCH_TABLE, 36))
    handler = image_base + table[dispatch_case]
    _require(dispatch_index == 42 and dispatch_case == 7 and handler == HOTKEY_HANDLER,
             "presetHotKey dispatch target differs")
    processing_dispatch_index = 149 - 109
    processing_dispatch_case = dispatch_map[processing_dispatch_index]
    processing_handler = image_base + table[processing_dispatch_case]
    _require(
        processing_dispatch_index == 40
        and processing_dispatch_case == 5
        and processing_handler == PROCESSING_CHANNEL_HANDLER,
        "processingChannel dispatch target differs",
    )

    _require_direct_target(image_base, sections, 0x180041348, STATE_DESERIALIZER)
    _require_direct_target(image_base, sections, 0x180042624, STATE_SERIALIZER)
    _require_direct_target(
        image_base, sections, STORE_PRESET_SERIALIZER_CALL, STATE_SERIALIZER)
    _require_direct_target(image_base, sections, 0x18004922F, FXMODEL_FACTORY)
    _require_direct_target(image_base, sections, 0x1800497C1, 0x180053420)
    _require_direct_target(
        image_base, sections, 0x180040752, VOICEFX_OWNERSHIP_SWITCH)
    _require_direct_target(
        image_base, sections, 0x1800419A8, VOICEFX_OWNERSHIP_SWITCH)
    _require_direct_target(image_base, sections, 0x18003E74E, FXMODEL_FACTORY)

    _ascii(image_base, sections, 0x1804364B4, "hotkey")
    _ascii(image_base, sections, 0x1804364C8, "Hotkey Default.settings")
    _ascii(image_base, sections, 0x180435968, "voicefx")
    _ascii(image_base, sections, 0x180435958, "voicefxopt")
    _ascii(image_base, sections, 0x18043A698, "__classid")

    component_root = _first_component_model(component_model)
    component_parameters = _parameter_ids(component_root)
    _validate_enable_parameter(fx_params)
    ui = _embedded_ui(panel)
    class_ids = _model_class_ids(image_base, sections)

    return {
        "status": (
            "UC472_HOTKEY_FULL_CHANNEL_OVERRIDE_AND_VOICEFX_SELECTION_"
            "ROUTE_SOURCE_BOUND"
        ),
        "boundary": (
            "STATIC_HOST_STATE_ROUTE_SOURCE_BOUND_RUNTIME_EVENT_PROPAGATION_"
            "DEVICE_STORAGE_RECALL_GATE_AND_AUDIBILITY_UNOBSERVED"
        ),
        "sources": sources,
        "component_model": component_parameters,
        "embedded_ui": ui,
        "hotkey_toggle": {
            "parameter_change_dispatch": hex(PARAM_CHANGE),
            "parameter_id": 151,
            "dispatch_index": dispatch_index,
            "dispatch_case": dispatch_case,
            "handler": hex(handler),
            "on_source": "complete channel object +0x180 Hot Key snapshot",
            "off_source": "active normal slot selected by parameter 150",
            "deserializer_apply": "0x180041348 -> 0x18002e690",
            "post_apply": "channel vtable +0x130",
        },
        "hotkey_persistence": {
            "channel_load": hex(HOTKEY_CHANNEL_LOAD),
            "channel_save": hex(HOTKEY_CHANNEL_SAVE),
            "record_key": "hotkey",
            "snapshot_offset": "complete channel object +0x180",
            "active_capture": "0x180042624 -> 0x18002e270",
            "store_preset_capture": "0x18003b5b3 -> 0x18002e270",
            "same_serializer": True,
        },
        "voicefx_selection": {
            "serialized_parent": "voicefx",
            "serialized_selector": "__classid",
            "deserialize_function": hex(VOICEFX_DESERIALIZER),
            "selector_parameter": "voicefxopt/fxmodel",
            "selector_parameter_id": 450,
            "parameter_handler": hex(FXMODEL_HANDLER),
            "model_factory": hex(FXMODEL_FACTORY),
            "valid_values": [-1, 0, 1, 2, 3, 4, 5],
            "no_model_value": -1,
            "model_zero_is_off": False,
            "model_zero": "Transformer/Doubler",
            "wire_selector": {
                "block": 201,
                "block_index": 0,
                "tag": "VoFx",
                "size": 16,
                "send": "0x1800497c1 -> 0x180053420",
            },
            "enable_is_separate": "voicefx.on",
            "save_source": "host component state, not a readable DSP register",
        },
        "voicefx_channel_ownership": {
            "selector_parameter": "processingChannel",
            "selector_parameter_id": 149,
            "parameter_change_handler": hex(processing_handler),
            "ownership_switch": hex(VOICEFX_OWNERSHIP_SWITCH),
            "owning_predicate": "processingChannel == 0",
            "owning_channel_action": (
                "activate voicefxopt/fxmodel and select its current model"
            ),
            "nonowning_channel_action": (
                "deactivate voicefxopt/fxmodel and select host model -1"
            ),
            "initial_apply": "0x180040729 -> 0x18003e6c0",
            "change_refresh": "0x18004193f -> 0x18003e6c0",
            "voicefx_on_role": (
                "separate storable enable inside the selected model state"
            ),
            "stock_instance_count": 1,
        },
        "model_class_ids": class_ids,
        "linux_host_implication": {
            "save": (
                "persist model/class id, voicefx.on, and only the selected "
                "model state"
            ),
            "apply": (
                "instantiate/select the model before applying its state; "
                "preserve the full-channel Hot Key/normal-slot transition"
            ),
            "unknown_attached_state": (
                "cannot be recovered from block 201 readback; explicitly "
                "select a model or consume a complete known snapshot"
            ),
            "prior_channel2_trial_gap": "direct VoiceFX parameter write was omitted",
        },
    }


def _arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsp", required=True, type=Path)
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--component-model", required=True, type=Path)
    parser.add_argument("--fx-params", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv=None):
    arguments = _arguments(argv)
    report = analyze(
        dsp=arguments.dsp.read_bytes(),
        panel=arguments.panel.read_bytes(),
        component_model=arguments.component_model.read_bytes(),
        fx_params=arguments.fx_params.read_bytes(),
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
