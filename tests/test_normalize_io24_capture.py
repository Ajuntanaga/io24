import importlib.util
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


_NORMALIZER_PATH = Path(__file__).with_name("normalize_io24_capture.py")
_DECODER_PATH = Path(__file__).with_name("usbmon_decode.py")


def load_normalizer():
    if not _NORMALIZER_PATH.exists():
        raise AssertionError("normalize_io24_capture.py is not implemented")
    spec = importlib.util.spec_from_file_location(
        "io24_capture_normalizer", _NORMALIZER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_decoder():
    spec = importlib.util.spec_from_file_location(
        "io24_capture_decoder_for_normalizer", _DECODER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CaptureNormalizerTests(unittest.TestCase):
    request = "2400010101000000507465536c7070410000000061726150100000000000000003000000"
    response = "2400018101000000796c70526c707041000000007453614a100000000000000000000000"

    def test_coherent_novel_command_survives_and_is_flagged(self):
        """Discovery must preserve an unknown command with a valid envelope."""
        normalizer = load_normalizer()
        decoder = load_decoder()
        novel = "1400010101000000646d43586c70704100000000"
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "C04.tsv"
            output = Path(directory) / "C04.jsonl"
            raw.write_text("100.0\t1\t7\t5\t0x01\t%s\n" % novel)

            self.assertEqual(
                normalizer.normalize(raw, output, "C04", "1:7"), 1)
            parsed = decoder.parse(output)
            self.assertEqual(decoder.decode_msg(parsed[0]["data"]),
                             [("XCmd", "Appl", 0, None, None, 0)])

            rendered = io.StringIO()
            with mock.patch.object(sys, "argv",
                                   ["usbmon_decode.py", str(output)]), \
                    contextlib.redirect_stdout(rendered):
                self.assertEqual(decoder.main(), 0)
            self.assertIn("NOT IN OUR SET", rendered.getvalue())
            self.assertIn("NEVER SENT BY THIS PROJECT", rendered.getvalue())

    def test_filters_interface_five_and_control_endpoints_deterministically(self):
        """Only complete io24 interface-5 payloads belong in normalized data."""
        normalizer = load_normalizer()
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "C02.tsv"
            output = Path(directory) / "C02.jsonl"
            raw.write_text("\n".join([
                "100.000000\t1\t7\t5\t0x01\t%s" % self.request,
                # Same interface/endpoints, different USB device: exclude it.
                "100.001000\t1\t8\t5\t0x01\t%s" % self.request,
                "100.002000\t1\t7\t4\t0x01\t%s" % self.request,
                "100.003000\t1\t7\t5\t0x02\t%s" % self.request,
                "100.004000\t1\t7\t5\t0x81\t%s" % ":".join(
                    self.response[i:i + 2]
                    for i in range(0, len(self.response), 2)),
            ]) + "\n")

            count = normalizer.normalize(raw, output, "C02", "1:7")

            self.assertEqual(count, 2)
            rows = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(rows, [
                {
                    "ts": "100.000000",
                    "action": "C02",
                    "bus": 1,
                    "device": 7,
                    "dir": "OUT",
                    "ep": 1,
                    "type": "S",
                    "data": self.request,
                },
                {
                    "ts": "100.004000",
                    "action": "C02",
                    "bus": 1,
                    "device": 7,
                    "dir": "IN",
                    "ep": 1,
                    "type": "C",
                    "data": self.response,
                },
            ])
            self.assertEqual(output.read_text(),
                             "".join(json.dumps(row, separators=(",", ":")) + "\n"
                                     for row in rows))

    def test_rejects_damaged_rows_and_incomplete_frames(self):
        """Normalization must never turn damaged evidence into a partial pass."""
        normalizer = load_normalizer()
        bad_rows = [
            "missing\tcolumns\n",
            "100.0\tone\t7\t5\t0x01\t%s\n" % self.request,
            "100.0\t1\tseven\t5\t0x01\t%s\n" % self.request,
            "100.0\t1\t7\tfive\t0x01\t%s\n" % self.request,
            "100.0\t1\t7\t5\t0x01\tnot-hex\n",
            "100.0\t1\t7\t5\t0x01\t0800010101000000\n",
            "100.0\t1\t7\t5\t0x01\t0c00010101000000646d4358\n",
            "100.0\t1\t7\t5\t0x01\t1c00010101000000507465536c70704100000000\n",
            "100.0\t1\t7\t5\t0x01\t1c00010101000000507465536c707041000000006172615010000000\n",
        ]
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "bad.tsv"
            output = Path(directory) / "bad.jsonl"
            for row in bad_rows:
                with self.subTest(row=row):
                    raw.write_text(row)
                    with self.assertRaises(ValueError):
                        normalizer.normalize(raw, output, "C02", "1:7")


if __name__ == "__main__":
    unittest.main()
