# Native Universal Control capture manifest

Status: prepared offline; not authorized for execution

## Purpose

Capture the smallest genuine Universal Control sequence that distinguishes:

1. ordinary synchronization;
2. working reverb control;
3. audible Voice FX control;
4. saving a user preset;
5. assigning it to a hardware slot; and
6. recalling it without the editor driving the state.

This route uses a supported native Universal Control host. It does not depend on
Wine or the frozen CP33 task.

## Separate live authorization required

Before execution, obtain exact authorization for the named device, the capture
host, Universal Control, the specific preset/effect operations below, and the
final restore. Without that authorization, this file is planning only.

Do not update firmware, enter DFU, factory-reset, install or stage a driver,
probe unknown controls, detach an interface, or use any action not listed here.
Stop at or below 10 percent battery.

## Preserve before changing anything

Record in `PRESTATE.md`:

- device model, serial, and firmware as displayed by the supported host;
- current sample rate;
- current preset mode and selected slot for each channel;
- active reverb values and routing;
- active Voice FX model, values, and channel selection;
- the complete user-preset library, confirming the unique test name is absent;
- the exact user slot chosen for the bounded test; and
- how the original state will be restored.

Export a Universal Control scene if the supported host already offers that
operation. Do not overwrite an existing scene or preset. Use the unique test
name `IO24-CAPTURE-20260828` unless a later checkpoint replaces it.

## Capture matrix

Use a fresh capture file for every row. Wait for traffic to settle before and
after the one listed action, and record wall-clock times in `ACTIONS.tsv`.

| ID | One action | Expected role |
|---|---|---|
| C00 | Open Universal Control and allow normal synchronization; change nothing | baseline vocabulary and polling |
| C01 | Change only reverb wet mix from 31 percent to 37 percent, then back to 31 percent | known-working positive control |
| C02 | Select only one known-audible Voice FX model; leave wet/dry and every other value unchanged | model-selection/activation transaction |
| C03 | With that model unchanged, change only Voice FX wet/dry from 41 percent to 47 percent, then back | Voice FX parameter transaction |
| C04 | Save current state as the new user preset `IO24-CAPTURE-20260828`; do not assign it yet | user-preset store transaction |
| C05 | Assign only that user preset to the predeclared test slot | library-to-slot assignment transaction |
| C06 | Close the editor path as declared in the authorization, then recall only the test slot from the hardware control | standalone recall evidence |
| C07 | Reopen the editor if required; restore every PRESTATE value and original slot assignment; delete `IO24-CAPTURE-20260828`; verify the library matches PRESTATE | bounded restoration and test-artifact removal |

If any UI label, available value, or state differs from the manifest, stop and
record the discrepancy. Do not improvise a substitute operation.

## Required artifacts

```text
io24-native-capture-YYYYMMDDTHHMMSS/
  PRESTATE.md
  ACTIONS.tsv
  TOOLING.txt
  C00-sync.<native-capture-extension>
  C01-reverb.<native-capture-extension>
  C02-voice-model.<native-capture-extension>
  C03-voice-mix.<native-capture-extension>
  C04-user-save.<native-capture-extension>
  C05-slot-assign.<native-capture-extension>
  C06-hardware-recall.<native-capture-extension>
  C07-restore-delete.<native-capture-extension>
  exports/
    C00-sync.tsv
    C01-reverb.tsv
    C02-voice-model.tsv
    C03-voice-mix.tsv
    C04-user-save.tsv
    C05-slot-assign.tsv
    C06-hardware-recall.tsv
    C07-restore-delete.tsv
    C00-sync-control.tsv
    C01-reverb-control.tsv
    C02-voice-model-control.tsv
    C03-voice-mix-control.tsv
    C04-user-save-control.tsv
    C05-slot-assign-control.tsv
    C06-hardware-recall-control.tsv
    C07-restore-delete-control.tsv
  normalized/
    C00-sync.jsonl
    C01-reverb.jsonl
    C02-voice-model.jsonl
    C03-voice-mix.jsonl
    C04-user-save.jsonl
    C05-slot-assign.jsonl
    C06-hardware-recall.jsonl
    C07-restore-delete.jsonl
  SHA256SUMS
```

Keep the native captures immutable. Normalize into new files; never edit the
original capture to make the decoder accept it.

Record the exact target USB bus and device address, the native capture tool
name/version, and the SHA-256 of
`tests/normalize_io24_capture.py` in `TOOLING.txt`. If the six export fields or
the exact interface/endpoint filter below are unavailable on the capture host,
stop and preserve the native capture; do not improvise a lossy conversion.

## Deterministic export and normalization

For each native USBPcap/pcapng file, export exactly these six headerless TSV
columns in this order:

```text
frame.time_epoch<TAB>usb.bus_id<TAB>usb.device_address<TAB>usb.interface_number<TAB>usb.endpoint_address<TAB>usb.capdata
```

The example bus/address below are placeholders. Replace them once with the exact
target recorded in `PRESTATE.md` and `TOOLING.txt`; never infer them from endpoint
traffic. This C03 example is the template for every matrix row:

```bash
IO24_CAPTURE_BUS=1
IO24_CAPTURE_ADDRESS=7

tshark -r C03-voice-mix.pcapng \
  -Y "usb.bus_id == ${IO24_CAPTURE_BUS} && usb.device_address == ${IO24_CAPTURE_ADDRESS} && usb.interface_number == 5 && (usb.endpoint_address == 0x01 || usb.endpoint_address == 0x81) && usb.capdata" \
  -T fields -E separator=/t -E quote=n -E occurrence=f \
  -e frame.time_epoch -e usb.bus_id -e usb.device_address \
  -e usb.interface_number \
  -e usb.endpoint_address -e usb.capdata \
  > exports/C03-voice-mix.tsv

python3 tests/normalize_io24_capture.py \
  --action C03 \
  --device "${IO24_CAPTURE_BUS}:${IO24_CAPTURE_ADDRESS}" \
  exports/C03-voice-mix.tsv \
  normalized/C03-voice-mix.jsonl

python3 tests/usbmon_decode.py normalized/C03-voice-mix.jsonl
```

The normalizer independently requires the declared bus/device, enforces
interface 5, accepts only endpoints 0x01 and 0x81, maps them to OUT/S and IN/C,
requires coherent outer and inner paesdk framing, and writes compact JSONL in
source timestamp order. A malformed matching row or an export with no matching
payload is a hard failure. Rows from every other device, interface, or endpoint
are excluded deterministically.

Endpoint-zero control transfers are a separate evidence stream; do not fold them
into bulk JSONL. Export them deterministically from each same native capture:

```bash
tshark -r C03-voice-mix.pcapng \
  -Y "usb.bus_id == ${IO24_CAPTURE_BUS} && usb.device_address == ${IO24_CAPTURE_ADDRESS} && (usb.endpoint_address == 0x00 || usb.endpoint_address == 0x80)" \
  -T fields -E separator=/t -E quote=n -E occurrence=f \
  -e frame.time_epoch -e usb.bus_id -e usb.device_address -e usb.urb_type \
  -e usb.setup.bmRequestType -e usb.setup.bRequest \
  -e usb.setup.wValue -e usb.setup.wIndex -e usb.setup.wLength \
  -e usb.capdata \
  > exports/C03-voice-mix-control.tsv
```

An empty control TSV is valid negative evidence; hash it unchanged. Compare
control TSVs by chronology and setup tuple. Do not treat them as paesdk frames.

## Normalized payload format

Each JSONL row represents one bulk payload after the capture tool has reassembled
it. Use an OUT submission for host-to-device data and an IN completion for
device-to-host data. `ep` is the numeric endpoint without the direction bit;
`data` is the complete paesdk frame as hexadecimal.

```json
{"ts":"12.345678","action":"C03","bus":1,"device":7,"dir":"OUT","ep":1,"type":"S","data":"2400010101000000507465536c7070410000000061726150100000000000000003000000"}
{"ts":"12.346912","action":"C03","bus":1,"device":7,"dir":"IN","ep":1,"type":"C","data":"2400018101000000796c70526c707041000000007453614a100000000000000000000000"}
```

The decoder ignores optional `ts`, `action`, `bus`, and `device` fields. It
strictly validates direction/type/endpoint coherence plus outer and inner frame
length, then accepts the normalized files directly:

```bash
python3 tests/usbmon_decode.py normalized/C03-voice-mix.jsonl
```

## Offline adjudication

Compare each action capture to C00 and to the existing project vocabulary.
Prioritize:

- a new command, block, or blob tag;
- a known tag with a new ordering or prerequisite;
- a control transfer before the familiar bulk messages;
- a model-selection transaction that appears in C02 but not C03;
- a parameter transaction that appears in C03 without another model selection;
- a save transaction that appears in C04 but not C05;
- an assignment transaction that appears in C05 but not C04; and
- a recall sequence in C06 that reproduces state without a contemporaneous host
  push.

Do not infer success from a UI toast or a capture exit code. The effect must be
audible for C02/C03, the reverb delta must be observable for C01, the new preset
must survive the declared recall boundary for C06, and C07 must restore PRESTATE
and remove the uniquely named test preset.
