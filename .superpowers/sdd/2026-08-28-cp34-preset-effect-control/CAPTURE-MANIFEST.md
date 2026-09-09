# CP34 native preset and Voice FX capture

Status: superseded before execution

The user confirmed that Windows and macOS are not available for this project.
This supported-host matrix was never executed and is retained only to preserve
the earlier design. The active route is `LINUX-MANIFEST.md`.

This is the only live matrix for CP34. It uses the supported Universal Control
host and the capture tooling already present there. It does not require or
permit installation, firmware changes, reset, driver staging, interface
detach, Wine, network access, blind writes, or controls outside the rows below.

## Required record before C00

Fill `PRESTATE.md` from the actual supported host before starting:

- device model and exact serial;
- Windows or macOS version and host identifier;
- Universal Control version and executable hash;
- native USB-capture tool/version and audio-capture tool/version;
- current preset mode, enabled state, selected slot for each channel, complete
  user-library listing, and the slot chosen for the test;
- current Voice FX model/on/wet-dry/processing-channel values visible in the
  editor;
- monitor and input levels used for the audible A/B; and
- capture filters that isolate only the declared io24.

Do not infer the target from traffic. If the actual serial, host, tool, or a
restorable PRESTATE value is unavailable, record that fact and do not start
C00. Stop at or below 10 percent battery.

## Matrix

| Row | One permitted change | Required observation |
| --- | --- | --- |
| C00 | Open Universal Control and allow its normal synchronization; change nothing | Baseline native traffic, visible state, and dry audio reference |
| C01 | Change only reverb wet mix from 31 percent to 37 percent, then restore 31 percent | Known-working control delta and audible positive control |
| C02 | Select one known Voice FX model; change no other visible value | Model-selection/activation delta plus wet-vs-dry audio A/B |
| C03 | Keep that model selected; change only Voice FX wet/dry from 41 percent to 47 percent, then restore 41 percent | Parameter-only delta and corresponding audio change |
| C04 | Save current state as user preset `IO24-CAPTURE-20260828`; do not assign it | User-library store delta, or evidence that the action is host-library-only |
| C05 | Assign only `IO24-CAPTURE-20260828` to the predeclared test slot | Assignment delta distinct from C04, or evidence that no such device action exists |
| C06 | Close the editor path recorded in PRESTATE and recall only the test slot from the front panel | Editor-independent state and audible recall |
| C07 | Restore every PRESTATE value and original slot assignment, delete `IO24-CAPTURE-20260828`, and compare the library to PRESTATE | Complete restoration and removal of the test artifact |

Run rows in order. Start and stop a distinct native capture for every row. Do
not combine controls, use an unknown UI element, substitute a direct-driver
packet, or continue after a restoration mismatch.

## Evidence layout

Create one new run directory only after the required record is complete:

```text
CP34-CAPTURE-<UTC>/
  PRESTATE.md
  TOOLING.txt
  C00-baseline.<native-extension>
  C01-reverb.<native-extension>
  C02-voice-model.<native-extension>
  C03-voice-wetdry.<native-extension>
  C04-user-save.<native-extension>
  C05-slot-assign.<native-extension>
  C06-hardware-recall.<native-extension>
  C07-restore-delete.<native-extension>
  audio/
  normalized/
  SHA256SUMS
```

Keep native captures immutable. Export and normalize copies with the existing
`tests/normalize_io24_capture.py` tooling. Compare each row with C00 and its
single adjacent control change; a coherent frame or successful reply is not by
itself semantic proof.

## Completion gates

Device-resident preset saving passes only if C04 and C05 produce distinct
native operations and C06 recalls the saved content without the editor driving
the state. Audible Voice FX passes only if C02/C03 produce a repeatable audio
change while C01 proves the observation path works. CP34 remains active unless
both pass and C07 proves full restoration.
