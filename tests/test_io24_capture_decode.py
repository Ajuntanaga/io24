import contextlib
import importlib.util
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import io24


_DECODER_PATH = Path(__file__).with_name("usbmon_decode.py")
_SPEC = importlib.util.spec_from_file_location("io24_capture_decoder", _DECODER_PATH)
decoder = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(decoder)


class CaptureDecodeTests(unittest.TestCase):
    @staticmethod
    def _request_frame(command):
        return struct.pack("<HBBBBH", len(command) + 8, 1, 1, 1, 0, 0) + command

    def test_preset_metadata_is_bounded_without_claiming_an_operation(self):
        command = io24._build_captured_memp_frames(16, b"record")[0]
        preset = decoder.decode_preset_metadata(self._request_frame(command))

        self.assertEqual(preset, {
            "record": "PrsM",
            "index": 16,
            "meaning": "cache-refresh-envelope",
            "operation": None,
        })

        slot_command = bytearray(command)
        struct.pack_into("<II", slot_command, 20, io24.fourcc("Stat"), 3)
        slot = decoder.decode_preset_metadata(
            self._request_frame(bytes(slot_command)))
        self.assertEqual(slot, {
            "record": "Stat",
            "index": 3,
            "meaning": "enumeration-metadata",
            "operation": None,
        })

        for tag, index in (("PrsM", 15), ("PrsM", 28),
                           ("Stat", -1), ("Stat", 4)):
            with self.subTest(tag=tag, index=index):
                bad = bytearray(command)
                struct.pack_into("<II", bad, 20, io24.fourcc(tag),
                                 index & 0xffffffff)
                with self.assertRaises(ValueError):
                    decoder.decode_preset_metadata(
                        self._request_frame(bytes(bad)))

    def test_decoder_output_marks_memp_as_metadata_not_device_save(self):
        command = io24._build_captured_memp_frames(16, b"record")[0]
        frame = self._request_frame(command)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "C04.jsonl"
            path.write_text(json.dumps({
                "dir": "OUT", "ep": 1, "type": "S",
                "data": frame.hex(),
            }) + "\n")
            output = io.StringIO()
            with mock.patch.object(decoder.sys, "argv",
                                   ["usbmon_decode.py", str(path)]), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(decoder.main(), 0)

        self.assertIn("PrsM index 16: cache-refresh-envelope; "
                      "no inferred operation", output.getvalue())

    def test_normalized_jsonl_capture_is_accepted(self):
        """Supported-host exports must decode without a Linux usbmon capture."""
        records = [
            {"dir": "OUT", "ep": 1, "type": "S",
             "data": "2400010101000000507465536c7070410000000061726150100000000000000003000000"},
            {"dir": "IN", "ep": 1, "type": "C",
             "data": "2400018101000000796c70526c707041000000007453614a100000000000000000000000"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "uc-effects.jsonl"
            path.write_text("".join(json.dumps(record) + "\n"
                                    for record in records))

            self.assertEqual(decoder.parse(path), [
                {"dir": "OUT", "ep": 1, "type": "S",
                 "data": bytes.fromhex(
                     "2400010101000000507465536c7070410000000061726150100000000000000003000000")},
                {"dir": "IN", "ep": 1, "type": "C",
                 "data": bytes.fromhex(
                     "2400018101000000796c70526c707041000000007453614a100000000000000000000000")},
            ])
            parsed = decoder.parse(path)
            self.assertEqual(decoder.decode_msg(parsed[0]["data"]),
                             [("SetP", "Appl", 0, "Para", 16, 16)])
            self.assertEqual(decoder.decode_msg(parsed[1]["data"]),
                             [("Rply", "Appl", 0, "JaSt", 16, 16)])

    def test_normalized_jsonl_rejects_invalid_or_truncated_rows(self):
        """A damaged normalized capture must fail instead of losing rows."""
        bad_rows = [
            "{not-json}\n",
            json.dumps({"dir": "OUT", "ep": 1, "type": "S",
                        "data": "0800010101000000"}) + "\n",
            # Command-only envelope cannot be surfaced by the decoder.
            json.dumps({"dir": "OUT", "ep": 1, "type": "S",
                        "data": "0c00010101000000646d4358"}) + "\n",
            json.dumps({"dir": "SIDE", "ep": 1, "type": "S",
                        "data": "2400010101000000507465536c7070410000000061726150100000000000000003000000"}) + "\n",
            json.dumps({"dir": "OUT", "ep": 1, "type": "S",
                        "data": "1c00010101000000507465536c70704100000000"}) + "\n",
            # Outer frame is complete, but blobSize=16 has only 8 bytes.
            json.dumps({"dir": "OUT", "ep": 1, "type": "S",
                        "data": "1c00010101000000507465536c707041000000006172615010000000"}) + "\n",
            # Wrong endpoint with otherwise coherent request metadata.
            json.dumps({"dir": "OUT", "ep": 7, "type": "S",
                        "data": "2400010101000000507465536c7070410000000061726150100000000000000003000000"}) + "\n",
            # Wrong transfer type with otherwise coherent request metadata.
            json.dumps({"dir": "OUT", "ep": 1, "type": "C",
                        "data": "2400010101000000507465536c7070410000000061726150100000000000000003000000"}) + "\n",
            # Response message code contradicts the declared OUT direction.
            json.dumps({"dir": "OUT", "ep": 1, "type": "S",
                        "data": "2400018101000000796c70526c707041000000007453614a100000000000000000000000"}) + "\n",
            # Unsupported protocol byte with all other request fields coherent.
            json.dumps({"dir": "OUT", "ep": 1, "type": "S",
                        "data": "2400020101000000507465536c7070410000000061726150100000000000000003000000"}) + "\n",
            # Multiple contradictions must also fail rather than be normalized.
            json.dumps({"dir": "OUT", "ep": 7, "type": "C",
                        "data": "2400018101000000796c70526c707041000000007453614a100000000000000000000000"}) + "\n",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            for row in bad_rows:
                with self.subTest(row=row):
                    path.write_text(row)
                    with self.assertRaises(ValueError):
                        decoder.parse(path)


if __name__ == "__main__":
    unittest.main()
