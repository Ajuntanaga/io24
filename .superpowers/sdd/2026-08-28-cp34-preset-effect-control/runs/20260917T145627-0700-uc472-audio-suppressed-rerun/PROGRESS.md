# UC 4.7.2 VoiceFX capture and Host correction

Status: capture complete, device/host restored, Linux implementation corrected

## Authorized run

- Universal Control: `4.7.2.108537`
- io24: serial `AB7C22200355`, firmware `0128`
- Guest: isolated QEMU VM, no network adapter
- Windows audio services: stopped before USB attachment
- Excluded: playback, capture, listening, preset save, firmware update, reset,
  DFU and Wine

The first attachment attempt used the wrong tap environment-variable name. It
was stopped without a device change, USB was detached, Linux audio was
restored, and the guest shut down cleanly. This rerun used `IO24_USBLOG` and
captured the active control endpoint. Endpoint 3/83 remained at zero transfers;
endpoint 1/81 carried the control traffic.

## Capture result

UC rendered the exact six-unit VoiceFX rack:

- Transformer: Lows, Width, Dry/Wet
- De-Tuner
- Vocoder
- Ring Modulator
- Filters
- Delay: Time, Feedback, Dry/Wet

Every selected component has its own power control. There is no seventh/master
VoiceFX switch.

The bounded interaction selected VoG/Transformer, turned its component On,
moved Dry/Wet from 0.36 to 0.42 and back to 0.36, then turned it Off. The final
model was restored to Delay class
`{98A527BA-2D6E-4B35-BB26-251EC081A067}` with `on=0`,
`time=0.0350860022`, `feedback=1`, `mix=1`. The final encoded `Stat(0)` SHA-256
matched the initial state exactly:
`53976bd44fb5bfd8046065b0aee7187ba9d4b027fdd40f46b1a65980abb1b031`.

Exact block-201 sequence:

```text
line 39759  VoFx model 0
line 39761  Bqdf table/band 0
line 39763  Bqdf table/band 1
line 39765  MBdf table 0, size 0x1f4, count 4
line 39767  MBdf table 1, size 0x1f4, count 4
line 39769  godv on=0 lows=.82 width=.8 mix=.36
line 47229  godv on=1 only
...         godv Dry/Wet state-only edits
line 112251 godv on=0 only
line 276765 vech on=1 only
line 277019 vech on=0 only
```

The Transformer selection sequence spans 2.571 ms. UC sends no selector replay
and no artificial inter-frame delay. Delay selection is `VoFx + vech`; its
later On/Off operations are `vech` only.

The complete SetP inventory contains no separate VoiceFX activation tag.
`analyze_mprm_trace.py` proves the four `mprm` frames are ordinary mixer
snapshots. Main source 5 (`fxreturn/ch1`) is explicitly -96 dB, and VoiceFX
selection/On/WetDry/Off emits no mixer write. The reverb-return prelude is not
part of UC's VoiceFX transaction.

Capture:

- `uc-qemu-usbtap.txt`: 280,933 lines, 92,743,656 bytes
- SHA-256: `d4c1be6c9ecad6181f3addd6af3b4ede9c66fc9e4ea294406b06d9303394e1f6`
- Reproducible decoders: `analyze_setp_timeline.py`,
  `analyze_voicefx_trace.py`, `analyze_mprm_trace.py`

## Linux Host correction

- `io24_fx.py` now emits both Transformer `MBdf` tables for
  44.1/48/88.2/96 kHz and zero-fills unused entries.
- `Io24.set_fx()` materializes only when the model changes. Repeated model
  edits are state-only; Transformer Lows/sample-rate changes refresh the four
  filter payloads without replaying `VoFx`.
- The invented 20 ms delay is removed. `_exec()` remains the synchronous USB
  serialization boundary.
- GTK and preset VoiceFX paths no longer open or alter the block-202 reverb
  return. Reverb behavior is unchanged.
- The rack remains generated from `dsp_fx_params.xml`, with one independent On
  state and exact parameter-to-builder mapping per component.

Affected protocol, Host, preset, UI-contract and generated-inventory regression
result:

```text
239 passed, 1 warning, 76 subtests passed
```

This run did not test audibility because audio was explicitly suppressed. The
prior dry listening campaign used the superseded Linux transaction. The next
acceptance is one separately authorized Linux-Host VoiceFX on/off listen or
capture run. Device-preset storage is not a substitute: VoiceFX data can be
saved without becoming audible standalone, while Fat Channel state is audible
without the Host.

## Restoration

- USB detached from the guest
- Linux interfaces 0-4 rebound to `snd-usb-audio`; interfaces 5/6 unbound as
  before
- host audio restored
- guest shut down cleanly
- VM qcow2 check: zero errors
- no QEMU or watchdog process left running
- battery: 99 percent
