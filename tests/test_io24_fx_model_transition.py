#!/usr/bin/env python3
"""Hardware-free ordering contracts for block-201 model replacement."""

import unittest

import io24
import io24_fx


class VoiceFxModelTransitionTests(unittest.TestCase):
    def _device(self):
        device = object.__new__(io24.Io24)
        device.sent = []
        device._exec = device.sent.append
        return device

    def test_two_frame_model_replays_selector_after_bypass_transition(self):
        device = self._device()
        waits = []
        frames = io24_fx.set_fx_delay(
            on=True, time_s=0.25, feedback=1.0, mix=1.0)

        logical = device.send_fx(frames, sleep_fn=waits.append)

        self.assertEqual(logical, 2)
        self.assertEqual(device.sent,
                         [frames[0][8:], frames[0][8:], frames[1][8:]])
        self.assertEqual(waits, [io24.FX_MODEL_REBUILD_SETTLE_S,
                                 io24.FX_FRAME_INTERVAL_S])

    def test_transformer_preserves_blob_order_after_selector_replay(self):
        device = self._device()
        waits = []
        frames = io24_fx.set_fx_transformer(
            on=True, lows=0.5, width=0.5, mix=1.0, fs=96000.0)

        logical = device.send_fx(frames, sleep_fn=waits.append)

        self.assertEqual(logical, 4)
        self.assertEqual(device.sent,
                         [frames[0][8:], frames[0][8:], frames[1][8:],
                          frames[2][8:], frames[3][8:]])

    def test_non_selector_payloads_keep_ordinary_interframe_sequence(self):
        device = self._device()
        waits = []
        frame = io24_fx.setp(
            201, io24_fx.fx_delay(True, 0.125, 0.5, 0.5))

        logical = device.send_fx([frame], sleep_fn=waits.append)

        self.assertEqual(logical, 1)
        self.assertEqual(device.sent, [frame[8:]])
        self.assertEqual(waits, [io24.FX_FRAME_INTERVAL_S])


if __name__ == "__main__":
    unittest.main()
