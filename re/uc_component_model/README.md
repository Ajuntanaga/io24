# Universal Control's own component model (recovered)

PreSonus ships its device model as XML embedded in
`Plugins/studiolivepanel.dll`. It is not a resource and not a file on disk —
it sits as plain text inside the binary, and it is the authoritative source
for parameter names, ranges, defaults, curves and flags.

Recovered 2026-08-11 by scanning the DLL for printable runs containing
`uc:ComponentModel`: 12 documents, 372 KB. The two kept here are the ones
that describe this device.

| file | what it is |
|---|---|
| `dsp_fx_params.xml` | the Voice FX and reverb parameter lists, plus the Voice FX class-ID template table |
| `dspusb_component_model.xml` | the DSP-USB channel model: `MicLineInputDSP` / `StereoLineInputDSP` templates and the `starttag` numbering |

## Why it matters

**It confirms this project's decode.** Every Voice FX parameter this driver
sends matches PreSonus's definition — `fx_detuner(detune=…)` really is a
0..8 list index, `fx_filters` really does take `pitch`/`regeneration`, and
the volume parameters on vocoder/ringmod/filters are real. The decode was
done from disassembly without this file; the file agrees with it.

**It settles the naming.** `<!-- Doubler -->` sits directly above
`<uc:ParamList id="VoiceOfGod">`, so the manual's "Doubler" and UC's
"Transformer" are the same processor under a third internal name again.
Filters' controls are officially **Pitch** and **Regeneration**.

**It answers the detuner range for good.** `TuneList` is nine entries,
`-8 … 0`, default index 4. The detuner only ever pitches **down**.

**It shows two things the device has that no UI exposes**: the vocoder's
`avoiced` readonly "Voiced" output, and the `VocoderMode` (cheapo / rms
follow) and `VocDetectorMode` (off / Voiced-Unvoiced) string lists, which are
declared but referenced by no parameter in the shipped model.

## Relationship to the wire capture

The XML describes presentation and component state, not USB framing. The
2026-09-17 UC 4.7.2 capture supplies that missing half and confirms the XML's
structure: `voicefxopt/fxmodel` becomes the one `VoFx` selection, and each
component's own first `on` parameter is encoded in its model-state tag. There
is no container-level/master VoiceFX enable. After materialization, UC sends
only the selected component's state for On/Off and ordinary edits.
