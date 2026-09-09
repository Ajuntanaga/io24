import importlib.util
import os
import struct
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RE_DIR = os.path.join(ROOT, "re")
if RE_DIR not in sys.path:
    sys.path.insert(0, RE_DIR)
SCRIPT = os.path.join(RE_DIR, "cp34_restore_input_mutes.py")
SPEC = importlib.util.spec_from_file_location("cp34_restore_input_mutes", SCRIPT)
RESTORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESTORE)


class InputEndpoint:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def read(self, _size, timeout):
        if not self.chunks:
            raise AssertionError("unexpected read")
        return self.chunks.pop(0)


class RestoreInputMutesTests(unittest.TestCase):
    def test_mute_frame_is_exact_pari_7_for_requested_channel(self):
        frame = RESTORE._set_mute_frame(9, 2, False)
        self.assertEqual(struct.unpack_from("<H", frame, 0)[0], len(frame))
        self.assertEqual(frame[4], 9)
        self.assertEqual(struct.unpack_from("<III", frame, 8),
                         (RESTORE.readonly.SETP, RESTORE.readonly.APPL, 0))
        self.assertEqual(struct.unpack_from("<IIIIi", frame, 20),
                         (RESTORE.PARI, 0x14, 1, RESTORE.MUTE_WIRE_ID, 0))

    def test_fragmented_jast_reply_is_reassembled(self):
        payload = bytearray(RESTORE.readonly.DATA_START + 51 * 4)
        struct.pack_into("<I", payload, 0, RESTORE.readonly.RPLY)
        frame = (struct.pack("<H", len(payload) + 8) +
                 b"\x01\x01\x01\0\0\0" + bytes(payload))
        endpoint = InputEndpoint((frame[:71], frame[71:173], frame[173:]))

        result = RESTORE._read_complete_reply(endpoint)

        self.assertEqual(result, bytes(payload))
        self.assertEqual(endpoint.chunks, [])

    def test_truncated_fragmented_reply_fails_closed(self):
        frame = struct.pack("<H", 200) + b"\x01\x01\x01\0\0\0" + b"short"
        endpoint = InputEndpoint((frame,))
        with self.assertRaises(Exception):
            RESTORE._read_complete_reply(endpoint)


if __name__ == "__main__":
    unittest.main()
