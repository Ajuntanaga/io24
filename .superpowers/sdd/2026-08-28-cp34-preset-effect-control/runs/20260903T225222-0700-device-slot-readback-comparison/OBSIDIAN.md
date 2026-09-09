# CP34 device-slot record comparison

Status: locally verified hardware-free evidence.

- The Linux-native host can prepare and send a complete `MemP/Stat` record.
- `compare_device_slot_records()` now distinguishes a decoded-record equality
  check from selected-slot state or a transport reply.
- `RECORD_EQUAL` requires the same slot plus a complete independently obtained
  decoded record. It does not prove source provenance, physical commit,
  front-panel recall, or audibility.
- No decoded device-slot readback has been obtained in this checkpoint.
- The complete local suite passed 190 tests with one expected skip.

Next live gate: exact scoped authority, current PRESTATE, a restoration plan,
and a provenance-bound record source. No USB, audio, preset/effect, Wine,
network, firmware, or other live action occurred here.
