# CP34 device-slot decoded-record comparison

## Objective

Make the host-intended `MemP/Stat` record comparable with a later, independently
obtained decoded device-slot record. The result must distinguish an exact record
comparison from selected-slot state, a transport reply, physical commit,
front-panel recall, and audible Voice FX.

## Permitted work

- Pure local record normalization, comparison, and hardware-free regression
  tests.
- Task-local scope, progress, and checksum evidence.
- Inspection of existing local CP34 sources and retained host artifacts.

## Explicit limits

- Do not infer a decoded device record from a host cache, selected-slot value,
  protocol reply, UI toast, or preset title.
- `RECORD_EQUAL` may establish equality between two supplied complete decoded
  records only. It does not prove the observed record came from the device,
  nonvolatile commit, front-panel recall, or audible Voice FX.
- Do not open USB, claim an interface, access audio, change a preset/effect,
  start Wine, access `/home/ajuntanaga/.wine-io24`, use the network, or emit or
  operate on firmware.

## Completion rule

Close only as a hardware-free comparison checkpoint after focused and complete
regression evidence passes. A later live run must have its own exact authority,
PRESTATE, restoration plan, capture/source provenance, and physical observation.
