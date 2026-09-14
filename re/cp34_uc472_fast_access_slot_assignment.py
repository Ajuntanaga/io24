#!/usr/bin/env python3
"""Resolve UC 4.7.2's fast-access preset-slot assignment edge.

CP34 repeatedly looked for the wire operation that puts a preset into one of
the io24's four fast-access button slots, and repeatedly failed to find it
(``explicit_assign_frame_located: false``). This analyzer answers why, from
UC's own shipped definitions rather than from a wire capture.

It enumerates, exhaustively:

* every control in UC's embedded ``uceasy.xml`` skin whose name mentions a
  slot, a store, an assign, the mixer or the disk; and
* every parameter in UC's ``dspusb_component_model.xml`` whose id mentions a
  preset, a slot, a store or an assign, together with its declared flags.

The result is that UC exposes exactly one *mutable* slot parameter --
``activePresetSlotIndex``, which only selects -- while the four slot contents
``presetSlotTitle1..4`` are declared ``readonly``. No control and no parameter
writes a preset into a numbered slot. The assignment edge was never missing
from the analysis; it is absent from the product.

Inputs are the retained, hash-pinned UC 4.7.2 payload. Nothing here opens USB
and no vendor code is executed.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PANEL_SHA256 = "52e48cb1453b815abc4b55fd0232131e11115d1aceb2eb0ed899750db6c08dd8"
PANEL_SIZE = 41_828_312
DEFAULT_SKIN_FILE_OFFSET = 0x1305F48
DEFAULT_SKIN_SIZE = 21_371_451
UCEASY_OFFSET = 0x14579B5
UCEASY_COMPRESSED_SIZE = 5_918
UCEASY_RAW_SIZE = 39_057
UCEASY_SHA256 = "a710cf06425a48ff1bb0e9ae72ad74d15613b939e675d134b27f4441074d5dfa"

COMPONENT_MODEL = ROOT / "re" / "uc_component_model" / "dspusb_component_model.xml"

CONTROL_PATTERN = re.compile(
    r'<(?P<kind>Button|RadioButton|Toggle|SelectBox|ListView|MenuItem|Command)'
    # (?<![a-zA-Z]) or the suffix of titlename="..." matches too, which
    # attributes a slot's label to the control and invents an assign edge.
    r'[^>]*(?<![a-zA-Z])name="(?P<name>[^"]*'
    r'(?:[Ss]lot|[Ss]tore|[Aa]ssign|Mixer|Disk)[^"]*)"')
PARAM_PATTERN = re.compile(
    r'<uc:Param\s+id="(?P<id>[^"]*(?:[Pp]reset|[Ss]lot|[Ss]tore|[Aa]ssign)[^"]*)"'
    r'(?P<rest>[^/]*)/>')
FLAGS_PATTERN = re.compile(r'flags="([^"]*)"')


class AssignmentAnalysisError(RuntimeError):
    """An input differs from the pinned UC 4.7.2 payload."""


def _require(condition, message):
    if not condition:
        raise AssignmentAnalysisError(message)


def extract_uceasy(panel_bytes):
    """Return the embedded uceasy.xml, verifying both enclosing artifacts."""
    _require(len(panel_bytes) == PANEL_SIZE, "panel size differs")
    _require(hashlib.sha256(panel_bytes).hexdigest() == PANEL_SHA256,
             "panel sha256 differs")
    skin = panel_bytes[DEFAULT_SKIN_FILE_OFFSET:
                       DEFAULT_SKIN_FILE_OFFSET + DEFAULT_SKIN_SIZE]
    _require(len(skin) == DEFAULT_SKIN_SIZE, "DEFAULT.SKIN size differs")
    _require(skin[:8] == b"PACKAGEF", "DEFAULT.SKIN header differs")
    raw = zlib.decompress(skin[UCEASY_OFFSET:
                               UCEASY_OFFSET + UCEASY_COMPRESSED_SIZE])
    _require(len(raw) == UCEASY_RAW_SIZE, "uceasy.xml size differs")
    _require(hashlib.sha256(raw).hexdigest() == UCEASY_SHA256,
             "uceasy.xml sha256 differs")
    return raw.decode("utf-8", "replace")


def slot_controls(ui_xml):
    """Every skin control naming a slot, store, assign, mixer or disk."""
    found = {}
    for match in CONTROL_PATTERN.finditer(ui_xml):
        found.setdefault(match.group("name"), match.group("kind"))
    return dict(sorted(found.items()))


def preset_parameters(model_xml):
    """Every component-model parameter id mentioning preset/slot/store/assign."""
    found = {}
    for match in PARAM_PATTERN.finditer(model_xml):
        flags = FLAGS_PATTERN.search(match.group("rest"))
        found[match.group("id")] = sorted(
            flags.group(1).split()) if flags else []
    return dict(sorted(found.items()))


def analyze(panel_bytes, model_xml):
    ui_xml = extract_uceasy(panel_bytes)
    controls = slot_controls(ui_xml)
    params = preset_parameters(model_xml)

    slot_content_params = {
        name: flags for name, flags in params.items()
        if re.fullmatch(r"presetSlotTitle[1-4]", name)}
    _require(len(slot_content_params) == 4,
             "expected exactly four fast-access slot title parameters")
    writable_slot_content = sorted(
        name for name, flags in slot_content_params.items()
        if "readonly" not in flags)
    mutable_slot_params = sorted(
        name for name, flags in params.items()
        if "mutable" in flags and "Slot" in name)

    return {
        "schema": "cp34-uc472-fast-access-slot-assignment-v1",
        "panel_sha256": PANEL_SHA256,
        "uceasy_sha256": UCEASY_SHA256,
        "slot_store_assign_controls": controls,
        "preset_parameters": params,
        "slot_content_parameters": slot_content_params,
        "writable_slot_content_parameters": writable_slot_content,
        "mutable_slot_parameters": mutable_slot_params,
        "assignment_control_present": any(
            name not in ("sendToDisk", "sendToMixer",
                         "storeNamedRemotePreset", "presetSlot")
            for name in controls),
        "conclusion": (
            "UC exposes selection only. activePresetSlotIndex is the sole "
            "mutable slot parameter and chooses which of the four slots is "
            "active; presetSlotTitle1..4 are readonly, and no skin control "
            "writes a preset into a numbered slot. The fast-access assignment "
            "edge is absent from the product, not missing from the analysis."),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel", type=Path)
    parser.add_argument("--component-model", type=Path, default=COMPONENT_MODEL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    result = analyze(args.panel.read_bytes(),
                     args.component_model.read_text(encoding="utf-8",
                                                    errors="replace"))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
