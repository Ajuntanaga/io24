#!/usr/bin/env python3
"""The bus sources must match the card profile the io24 is actually in.

2026-09-14: the io24's PipeWire nodes were `...analog-surround-21`, which
exposes three capture channels (FL, FR, LFE). The bus sources assumed six and
read indices 2-5, so "io24 Host Mix A" carried the LFE channel plus a channel
that does not exist and Mix B carried two that do not. Both still published,
and a live smoke run recorded them `ready`. Silence wearing the name of a mix
is worse than an absent source, so a profile that cannot supply a bus now says
so. A node's index i is device capture channel i+1 in every profile.

Nothing here opens USB, audio, PipeWire or a display.
"""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

import io24_mbc
import io24gtk

SURROUND_21 = ("FL", "FR", "LFE")
SURROUND_41 = ("FL", "FR", "RL", "RR")
PRO_AUDIO = tuple("AUX%d" % index for index in range(6))


class BusChannelMapTests(unittest.TestCase):
    def test_six_channels_carry_both_buses(self):
        for positions in (io24_mbc.CAPTURE_POSITIONS, PRO_AUDIO):
            with self.subTest(positions=positions[0]):
                self.assertEqual(
                    io24_mbc.bus_source_indices("mixa", positions), (2, 3))
                self.assertEqual(
                    io24_mbc.bus_source_indices("mixb", positions), (4, 5))

    def test_a_three_channel_profile_carries_neither(self):
        for bus in io24_mbc.BUS_SOURCE_KEYS:
            self.assertIsNone(io24_mbc.bus_source_indices(bus, SURROUND_21))

    def test_a_four_channel_profile_carries_only_mix_a(self):
        self.assertEqual(
            io24_mbc.bus_source_indices("mixa", SURROUND_41), (2, 3))
        self.assertIsNone(io24_mbc.bus_source_indices("mixb", SURROUND_41))

    def test_a_graph_is_refused_rather_than_fed_absent_channels(self):
        with self.assertRaisesRegex(ValueError, "Mix A"):
            io24_mbc.build_bus_source_graph("mixa", SURROUND_21)

    def test_the_config_declares_the_channels_the_node_has(self):
        conf = io24_mbc.build_bus_source_conf(
            "mixa", "alsa_input.io24", SURROUND_41)
        args = json.loads(conf[conf.index("args = ") + len("args = "):
                               conf.rindex("\n  }")])
        self.assertEqual(args["capture.props"]["audio.channels"], 4)
        self.assertEqual(args["capture.props"]["audio.position"],
                         list(SURROUND_41))


class _Chain:
    def __init__(self):
        self.starts, self.stops, self._running = [], 0, False

    @property
    def running(self):
        return self._running

    def start(self, capture_target=None, positions=None):
        self.starts.append((capture_target, positions))
        self._running = True
        return True

    def stop(self):
        self.stops += 1
        self._running = False

    def node_id(self):
        return "42" if self._running else None


class ReconcileTests(unittest.TestCase):
    def _manager(self):
        chains = {bus: _Chain() for bus in io24_mbc.BUS_SOURCE_KEYS}
        return io24_mbc.BusSourceManager(chains), chains

    def test_a_profile_without_the_channels_publishes_nothing(self):
        manager, chains = self._manager()
        statuses = manager.reconcile("alsa_input.io24", positions=SURROUND_21)
        self.assertEqual(statuses, {"mixa": "profile", "mixb": "profile"})
        for chain in chains.values():
            self.assertEqual(chain.starts, [])

    def test_six_channels_start_both_and_pass_the_map_down(self):
        manager, chains = self._manager()
        statuses = manager.reconcile("alsa_input.io24", positions=PRO_AUDIO)
        self.assertEqual(statuses, {"mixa": "ready", "mixb": "ready"})
        self.assertEqual(chains["mixa"].starts, [("alsa_input.io24", PRO_AUDIO)])

    def test_only_the_bus_the_profile_has_is_published(self):
        manager, chains = self._manager()
        statuses = manager.reconcile("alsa_input.io24", positions=SURROUND_41)
        self.assertEqual(statuses["mixa"], "ready")
        self.assertEqual(statuses["mixb"], "profile")
        self.assertEqual(chains["mixb"].starts, [])

    def test_a_running_source_is_stopped_when_the_profile_loses_it(self):
        manager, chains = self._manager()
        manager.reconcile("alsa_input.io24", positions=PRO_AUDIO)
        manager.reconcile("alsa_input.io24", positions=SURROUND_21)
        self.assertEqual(manager.statuses["mixa"], "profile")
        self.assertGreaterEqual(chains["mixa"].stops, 1)


class CapturePositionsTests(unittest.TestCase):
    def setUp(self):
        io24_mbc._POSITION_CACHE.clear()
        self.addCleanup(io24_mbc._POSITION_CACHE.clear)

    def _dump(self, props):
        return json.dumps([{"info": {"props": props}}])

    def test_a_position_list_is_read(self):
        dump = self._dump({"node.name": "n", "audio.position": list(PRO_AUDIO)})
        with mock.patch.object(io24_mbc.subprocess, "run",
                               return_value=SimpleNamespace(stdout=dump)):
            self.assertEqual(io24_mbc.capture_positions("n"), PRO_AUDIO)

    def test_a_bracketed_string_is_read_and_then_cached(self):
        dump = self._dump({"node.name": "n",
                           "audio.position": "[ FL, FR, LFE ]"})
        with mock.patch.object(io24_mbc.subprocess, "run",
                               return_value=SimpleNamespace(stdout=dump)) as run:
            self.assertEqual(io24_mbc.capture_positions("n"), SURROUND_21)
            self.assertEqual(io24_mbc.capture_positions("n"), SURROUND_21)
            self.assertEqual(run.call_count, 1)

    def test_an_unreadable_graph_is_not_a_guess(self):
        with mock.patch.object(io24_mbc.subprocess, "run",
                               side_effect=OSError("no pw-dump")):
            self.assertEqual(io24_mbc.capture_positions("n"), ())
        self.assertEqual(io24_mbc.capture_positions(None), ())


class InsertProfileTests(unittest.TestCase):
    def test_the_insert_needs_only_the_two_inputs(self):
        graph = io24_mbc.build_insert_graph(
            {1: io24_mbc.default_snapshot()}, False, SURROUND_21)
        self.assertEqual(len(graph["inputs"]), 3)

    def test_a_single_channel_profile_cannot_carry_it(self):
        with self.assertRaisesRegex(ValueError, "both inputs"):
            io24_mbc.build_insert_graph(
                {1: io24_mbc.default_snapshot()}, False, ("FL",))


class HostNoticeTests(unittest.TestCase):
    def test_the_profile_case_is_reported_and_is_not_called_a_failure(self):
        said = []
        host = SimpleNamespace(_bus_source_status={"mixa": "ready"},
                               say=said.append)
        io24gtk.Win._set_bus_source_status(host, "mixa", "profile", notify=True)
        self.assertEqual(len(said), 1)
        self.assertIn("Pro Audio", said[0])
        self.assertNotIn("failed", said[0])
        io24gtk.Win._set_bus_source_status(host, "mixa", "profile", notify=True)
        self.assertEqual(len(said), 1)          # said once, not every tick
