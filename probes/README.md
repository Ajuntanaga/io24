# probes/

The investigation trail. These are the scripts that established each finding in
[PROTOCOL.md](../PROTOCOL.md) — kept because a claim in the protocol document is
only as good as the experiment behind it, and several of the findings here were
corrections of earlier, confidently-wrong conclusions.

They are not part of the driver. Run them from the repo root:

```bash
python3 probes/probe_getp.py
```

| script | what it established |
|---|---|
| `probe_iface5.py` | interface 5 alt 1 is the control interface; endpoints 0x01/0x81 |
| `probe_handshake*.py` | the vendor control queries (protocol, maxCmd, maxRsp) |
| `probe_bulkcmd*.py` | the 8-byte paesdk header, and that the protocol is strictly synchronous |
| `probe_control*.py`, `probe_enable.py` | UCNET-over-USB does not work — the payload is native |
| `probe_sweep*.py`, `probe_batch.py` | which FourCC blocks answer, and which are silent |
| `probe_getp.py` | `'GetP'`/`'Appl'`/`'JaSt'` — the readable state blob |
| `probe_setp.py`, `probe_write.py` | `'SetP'` with `'Para'`/`'Pari'`, and the wire paramId space |
| `probe_optest.py` | the six per-channel DSP blocks and their dispatch |
| `probe_limiter.py` | the limiter blob, and reduction metering via `'Redu'` |
| `probe_listen.py` | whether the device ever sends unsolicited traffic (it does not) |
| `probe_final_safe.py` | the read-only sweep used before any write-shaped probing |
| `oracle.py` | a value oracle for checking recovered coefficient maths |
