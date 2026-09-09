"""Shared validation for normalized io24 bulk-control evidence."""


REQUEST_TAGS = {b"PteG", b"PteS"}  # GetP / SetP in wire byte order
RESPONSE_TAG = b"ylpR"              # Rply in wire byte order


def validate_bulk_frame(payload, direction, transfer_type, endpoint):
    """Return bytes for one coherent, complete normalized paesdk frame."""
    if direction == "OUT":
        expected_type = "S"
        expected_code = 0x01
    elif direction == "IN":
        expected_type = "C"
        expected_code = 0x81
    else:
        raise ValueError("dir must be OUT or IN")
    if transfer_type != expected_type:
        raise ValueError("%s payload must use transfer type %s"
                         % (direction, expected_type))
    if isinstance(endpoint, bool) or endpoint != 1:
        raise ValueError("normalized io24 control endpoint must be 1")
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    payload = bytes(payload)
    if len(payload) < 20:
        raise ValueError(
            "payload is shorter than a decodable paesdk command envelope")

    declared = int.from_bytes(payload[:2], "little")
    if declared != len(payload):
        raise ValueError("declared paesdk length %d does not match %d bytes"
                         % (declared, len(payload)))
    if payload[2] != 0x01:
        raise ValueError("unsupported paesdk protocol code 0x%02x" % payload[2])
    if payload[3] != expected_code:
        raise ValueError("paesdk message code contradicts %s direction"
                         % direction)
    if payload[4] == 0:
        raise ValueError("paesdk unique id must be nonzero")

    command = payload[8:12]
    if direction == "OUT" and command == RESPONSE_TAG:
        raise ValueError("Rply command contradicts OUT direction")
    if direction == "IN" and command in REQUEST_TAGS:
        raise ValueError("GetP/SetP command contradicts IN direction")

    # Unknown command bodies are the discovery target. Preserve any coherent
    # generic envelope; only apply the known inner-TLV contract to the commands
    # whose structure has already been established.
    known_tlv = ((direction == "OUT" and command in REQUEST_TAGS) or
                 (direction == "IN" and command == RESPONSE_TAG))
    if not known_tlv:
        return payload
    if len(payload) < 28:
        raise ValueError("known command is shorter than a complete TLV frame")

    body = payload[8:]
    blob_size = int.from_bytes(body[16:20], "little")
    if blob_size < 8:
        raise ValueError("inner blob is shorter than its header")
    if 12 + blob_size != len(body):
        raise ValueError("declared inner blob length %d does not match %d bytes"
                         % (blob_size, len(body) - 12))
    return payload
