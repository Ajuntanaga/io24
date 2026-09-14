#!/usr/bin/env python3
"""Hardware-free contracts for the UC 4.7.2 module graph.

This tool exists because a linear x86 sweep produced a false negative in this
project. Its own correctness therefore matters more than usual: it must build
functions only from .pdata, and it must never report a reachability result it
cannot support. Nothing here opens USB.
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
    "cp34_uc472_module_graph", RE_DIR / "cp34_uc472_module_graph.py")
GRAPH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GRAPH)

MODULE_PATH = (ROOT / ".superpowers/sdd/2026-08-28-cp34-preset-effect-control"
               / "runs/20260906T001130-0700-uc472-official-reacquisition"
               / "extracted/hwaccess/dspusbdevice.dll")
UC472_SHA256 = ("de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917"
                "f611fd28")


class ReachabilityTests(unittest.TestCase):
    def test_reverse_reachability_walks_transitively(self):
        callers = {0xC: {0xB}, 0xB: {0xA}}
        depth = GRAPH.reaches(callers, 0xC)
        self.assertEqual(depth, {0xB: 1, 0xA: 2})

    def test_the_target_is_not_its_own_caller(self):
        self.assertEqual(GRAPH.reaches({0xC: {0xC}}, 0xC), {})

    def test_an_unreached_target_yields_nothing(self):
        self.assertEqual(GRAPH.reaches({}, 0xC), {})


class OwnerTests(unittest.TestCase):
    FUNCS = [(0x100, 0x200), (0x200, 0x280), (0x400, 0x410)]

    def test_an_address_resolves_to_its_containing_function(self):
        self.assertEqual(GRAPH.owner_of(self.FUNCS, 0x1FF), (0x100, 0x200))
        self.assertEqual(GRAPH.owner_of(self.FUNCS, 0x200), (0x200, 0x280))

    def test_an_address_in_a_gap_resolves_to_nothing(self):
        self.assertIsNone(GRAPH.owner_of(self.FUNCS, 0x300))
        self.assertIsNone(GRAPH.owner_of(self.FUNCS, 0x0))


class RejectionTests(unittest.TestCase):
    def test_a_non_pe_input_is_refused(self):
        with self.assertRaises(GRAPH.ModuleGraphError):
            GRAPH.Module(b"not a pe image at all")


class SectionMappingTests(unittest.TestCase):
    """A section's virtual span can exceed its raw data, so file-offset
    containment must use the RAW extent or neighbouring sections overlap in
    file space and an offset is attributed to the wrong section."""

    @classmethod
    def setUpClass(cls):
        if not MODULE_PATH.exists():
            raise unittest.SkipTest("retained UC 4.7.2 dsp module not present")
        cls.module = GRAPH.Module(MODULE_PATH.read_bytes())

    def test_data_and_pdata_overlap_in_file_space(self):
        spans = {name: (ra, rsz) for name, _va, _sz, ra, rsz
                 in self.module.sections}
        data_start, data_raw = spans[".data"]
        pdata_start, _pdata_raw = spans[".pdata"]
        virtual_end = data_start + dict(
            (n, sz) for n, _v, sz, _r, _rs in self.module.sections)[".data"]
        # .pdata begins before .data's virtual span would end in file terms.
        self.assertLess(pdata_start, virtual_end)
        self.assertLess(data_start + data_raw, virtual_end)

    def test_a_pdata_file_offset_maps_to_pdata_not_data(self):
        pdata = [s for s in self.module.sections if s[0] == ".pdata"][0]
        _n, va, _sz, ra, _rsz = pdata
        address = self.module.address_of_offset(ra + 12)
        self.assertIsNotNone(address)
        self.assertEqual(self.module.section_of(address), ".pdata")
        self.assertEqual(address, self.module.base + va + 12)

    def test_pointer_search_does_not_report_pdata_as_data(self):
        # The VoFx dispatch slot is a real .rdata pointer; nothing else.
        slots = self.module.vtable_slots(0x1800491F0)
        self.assertEqual([hex(s) for s in slots], ["0x180437bf8"])
        for slot in slots:
            self.assertEqual(self.module.section_of(slot), ".rdata")


class RetainedModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODULE_PATH.exists():
            raise unittest.SkipTest("retained UC 4.7.2 dsp module not present")
        cls.module = GRAPH.Module(MODULE_PATH.read_bytes())
        cls.functions = cls.module.functions()

    def test_the_pinned_module_is_the_4_7_2_build(self):
        self.assertEqual(self.module.sha256, UC472_SHA256)
        self.assertEqual(self.module.base, 0x180000000)

    def test_pdata_yields_exact_function_bounds(self):
        self.assertEqual(len(self.functions), 3452)
        for begin, end in self.functions:
            self.assertLess(begin, end)

    def test_the_block201_emit_site_resolves_to_one_function(self):
        # 0x180049752 stores block 0xc9; 0x18004976c stores the model number.
        owner = GRAPH.owner_of(self.functions, 0x180049752)
        self.assertEqual(owner, (0x180049260, 0x180049870))
        self.assertEqual(GRAPH.owner_of(self.functions, 0x18004976C), owner)

    def test_the_block201_emitter_is_only_reached_by_virtual_dispatch(self):
        callers, _callees = self.module.call_graph(self.functions)
        direct = sorted(callers.get(0x180049260, ()))
        self.assertEqual([hex(c) for c in direct],
                         ["0x18003e6e3", "0x18003e746", "0x1800491f0"])
        # None of the three has a direct caller of its own, so nothing above
        # them is visible without resolving vtables.
        for caller in direct:
            self.assertEqual(callers.get(caller, set()), set())
        # Exactly one of them is dispatched from a vtable slot.
        self.assertEqual([hex(s) for s in self.module.vtable_slots(0x1800491F0)],
                         ["0x180437bf8"])
