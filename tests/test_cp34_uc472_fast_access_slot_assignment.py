#!/usr/bin/env python3
"""Hardware-free contracts for the fast-access slot assignment analyzer.

The analyzer's whole value is a negative -- that UC has no assign edge -- so
its scanners must not be able to manufacture one, and must not miss one that
is really there. Nothing here opens USB.
"""

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RE_DIR = ROOT / "re"
for path in (str(ROOT), str(RE_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

SPEC = importlib.util.spec_from_file_location(
    "cp34_uc472_fast_access_slot_assignment",
    RE_DIR / "cp34_uc472_fast_access_slot_assignment.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ControlScanTests(unittest.TestCase):
    def test_a_title_attribute_is_not_mistaken_for_a_control_name(self):
        # titlename="..." ends in name="...". Matching it attributed a slot's
        # label to the control and produced a false assign edge.
        xml = ('<RadioButton name="presetSlot" titlename="presetSlotTitle1" '
               'value="1"/>')
        self.assertEqual(MODULE.slot_controls(xml),
                         {"presetSlot": "RadioButton"})

    def test_a_real_assign_control_would_be_found(self):
        xml = '<Button name="assignPresetToSlot" title="Assign"/>'
        self.assertEqual(MODULE.slot_controls(xml),
                         {"assignPresetToSlot": "Button"})

    def test_controls_without_the_keywords_are_ignored(self):
        xml = '<Button name="cancel"/><Toggle name="gate/on"/>'
        self.assertEqual(MODULE.slot_controls(xml), {})


class ParameterScanTests(unittest.TestCase):
    def test_flags_are_captured_per_parameter(self):
        xml = ('<uc:Param id="activePresetSlotIndex" type="int" '
               'flags="mutable" />\n'
               '<uc:Param id="presetSlotTitle1" type="string" '
               'flags="readonly" />')
        self.assertEqual(MODULE.preset_parameters(xml), {
            "activePresetSlotIndex": ["mutable"],
            "presetSlotTitle1": ["readonly"]})

    def test_a_parameter_without_flags_reports_an_empty_list(self):
        xml = '<uc:Param id="presetHotKey" type="toggle" />'
        self.assertEqual(MODULE.preset_parameters(xml), {"presetHotKey": []})


class ConclusionTests(unittest.TestCase):
    """The analyzer must refuse to conclude 'no assign edge' on a payload
    that does not actually match UC 4.7.2."""

    def test_a_wrong_sized_panel_is_refused(self):
        with self.assertRaises(MODULE.AssignmentAnalysisError):
            MODULE.extract_uceasy(b"\x00" * 16)

    def test_it_requires_four_slot_title_parameters(self):
        panel = (ROOT / ".superpowers/sdd/2026-08-28-cp34-preset-effect-control"
                 / "runs/20260906T010449-0700-uc472-save-assign-ui-route"
                 / "extracted/Plugins/studiolivepanel.dll")
        if not panel.exists():
            self.skipTest("retained UC 4.7.2 panel is not present")
        # A model that declares only one slot title must not be allowed to
        # produce the "no assign edge" conclusion.
        thin = '<uc:Param id="presetSlotTitle1" flags="readonly" />'
        with self.assertRaises(MODULE.AssignmentAnalysisError):
            MODULE.analyze(panel.read_bytes(), thin)


class RetainedPayloadTests(unittest.TestCase):
    PANEL = (ROOT / ".superpowers/sdd/2026-08-28-cp34-preset-effect-control"
             / "runs/20260906T010449-0700-uc472-save-assign-ui-route"
             / "extracted/Plugins/studiolivepanel.dll")

    def setUp(self):
        if not self.PANEL.exists():
            self.skipTest("retained UC 4.7.2 panel is not present")

    def test_the_pinned_payload_yields_the_recorded_negative(self):
        model = MODULE.COMPONENT_MODEL.read_text(encoding="utf-8",
                                                 errors="replace")
        result = MODULE.analyze(self.PANEL.read_bytes(), model)
        self.assertEqual(sorted(result["slot_store_assign_controls"]),
                         ["presetSlot", "sendToDisk", "sendToMixer",
                          "storeNamedRemotePreset"])
        self.assertEqual(result["mutable_slot_parameters"],
                         ["activePresetSlotIndex"])
        self.assertEqual(result["writable_slot_content_parameters"], [])
        self.assertFalse(result["assignment_control_present"])
        for slot in range(1, 5):
            self.assertEqual(
                result["slot_content_parameters"]["presetSlotTitle%d" % slot],
                ["readonly"])


if __name__ == "__main__":
    unittest.main()
