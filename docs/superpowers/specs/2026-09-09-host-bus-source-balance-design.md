# Host bus source and balance design

Date: 2026-09-09
Status: Approved direction; implementation pending
Scope: Offline Linux Host implementation only

## Purpose

Replace the current Host-only physical-input pan monitor with truthful controls
for the io24 buses that the computer can actually capture. The Mixer will keep
one aligned control beneath each `Main`, `Mix A`, and `Mix B` meter column, but
it will publish only the two buses supported by retained topology evidence:
Mix A on USB capture channels 3-4 and Mix B on channels 5-6.

The complete Main mix is not present on the six-channel USB capture stream.
Capture channels 1-2 are physical Inputs 1-2. A monitor of the io24 playback
sink would contain only computer playback and would omit device inputs and
internal returns, so it must not be presented as Main.

## User-visible outcome

- `Main` keeps a centered balance knob for column alignment, but the knob is
  disabled. Its accessible description and tooltip say that the Main bus is
  not exposed by USB capture.
- `Mix A` and `Mix B` each receive an always-present stereo balance knob beneath
  the corresponding stereo meter.
- The Host publishes two independently routable PipeWire sources named
  `io24 Host Mix A` and `io24 Host Mix B`.
- There is no activation button, persistent status paragraph, per-input pan
  knob, routine-move toast, or automatic route to io24 playback.
- The sources disappear when the Host closes and stop when the io24 capture
  node disappears.

## Evidence boundary

The design relies on the retained six-channel mapping:

| USB capture channels | Signal |
|---|---|
| 1-2 | Physical Inputs 1-2 |
| 3-4 | Mix A left/right |
| 5-6 | Mix B left/right |

This mapping supports source-bound implementation and hardware-free tests. It
does not prove that the live PipeWire profile will negotiate six channels, that
the endpoints will appear on this workstation, or that their sound and latency
are acceptable. Those remain separately authorized live acceptance gates.

## Architecture

### Snapshot model

Replace the meaning of `host_features.pan` with a version 2 bus-balance schema.
The new object has exactly these fields:

```json
{
  "version": 2,
  "balances": {
    "mixa": 0.5,
    "mixb": 0.5
  }
}
```

Each balance is a finite number from 0.0 through 1.0. No `enabled` field is
stored because the endpoints are passive Host infrastructure rather than an
audible route that the user turns on. Main has no persisted value because its
control cannot affect a truthful source.

The loader accepts version 1 only as an explicit migration case. Channel 1/2
pan positions have no valid mapping onto Mix A/B, so migration returns centered
bus balances and reports during the discrete file load that legacy input pan
was not applied. Saving emits only version 2. A snapshot containing a malformed
version 1 or version 2 object still fails before any device setter runs,
preserving the existing atomic Host-file validation boundary.

### PipeWire graph

`io24_mbc.py` will replace `PanChain` with a bus-source abstraction:

- `build_bus_source_graph(pair, balance)` selects one exact stereo pair from a
  six-channel input graph. It never mixes capture channels 1-2 into a bus.
- `build_bus_source_conf(bus, capture_target, state)` targets the io24 capture
  node as a passive six-channel `Stream/Input/Audio` and publishes one passive
  two-channel `Audio/Source` from `playback.props`, mirroring the existing
  public-sink/real-target filter-chain direction.
- Mix A uses source indices 2-3; Mix B uses indices 4-5. The public labels remain
  one-based channels 3-4 and 5-6.
- `BusSourceChain` owns one child PipeWire process and one unique node name.
  `BusSourceManager` owns two independent chain instances so either endpoint
  can remain available if the other fails.

Both `capture.props` and `playback.props` set `stream.dont-remix` to true. The
USB channel labels use surround-style names, so allowing PipeWire's default
remixer could reinterpret FC/LFE/RL/RR and corrupt the exact pair selection.

The graph does not crossfeed left and right. At center both legs remain at
unity. Moving toward an edge progressively attenuates only the opposite leg;
hard left is `(1, 0)` and hard right is `(0, 1)`. This is stereo balance, not
mono-to-stereo panning, and avoids the center-level loss in the retired input
pan law.

The two source endpoints are passive. They carry audio only when another
PipeWire client connects to them, and neither endpoint targets an io24 playback
sink. A source consumer chooses routing explicitly outside this feature.

### Lifecycle

The Host performs a low-frequency reconciliation rather than querying
PipeWire in the 30 fps paint path:

1. On Host construction, locate the io24 PipeWire capture node without coupling
   endpoint availability to the separate USB control connection.
2. While the node is unavailable, retry discovery on a bounded slow timer.
3. When it appears, start Mix A and Mix B independently with their saved
   balances.
4. Keep a successfully started endpoint if the other endpoint fails.
5. Treat an endpoint as ready only after its child remains alive and its unique
   PipeWire source node is observed; spawning a process alone is not success.
6. On capture-node loss or Host shutdown, stop both child processes and remove
   their private configuration directories.
7. On reconnection, recreate the endpoints from the retained in-memory balance
   state.

Repeated starts with an identical target and configuration are idempotent.
Changing one balance uses `pw-cli set-param` only for that endpoint; it does not
restart either process or touch the other bus.

### Mixer UI

The Buses grid remains three fixed-width columns aligned with the existing
meters and labels.

- Main: disabled centered knob, disabled value label, accessible description
  `Main is not exposed by USB capture`, and the same text as its tooltip.
- Mix A: enabled only while its source endpoint is running.
- Mix B: enabled only while its source endpoint is running.
- Each live value reads `L100` through `C` to `R100`.

Unavailable endpoints communicate state by disabling the affected knob. There
is no permanent status paragraph. A genuine endpoint launch failure may use
the existing fault notification once per failed launch transition; discovery
absence and routine balance movement do not notify.

The old Channel 1/2 pan rows, `Host input pan` toggle, monitor description,
status label, and capture-to-playback warning are removed because that graph no
longer exists.

## Failure behavior

- Invalid saved state: reject the Host file before any device state is applied.
- Missing io24 capture node: keep all bus controls insensitive and retry
  discovery slowly without a toast loop.
- One endpoint fails: keep the other operational, disable only the failed bus,
  and issue one fault notification for that transition.
- Live parameter update fails: retain the intended balance in Host state,
  disable that endpoint, stop its chain, and report one fault. Reconciliation
  may recreate it later.
- Shutdown or disconnect: stop processes and clean private files even if a
  child loses the normal termination race.

No failure path may write device DSP, change Monitoring Blend, create an
automatic playback route, or label Inputs 1-2 as Main.

## Files and ownership

Expected production and regression files:

- `io24_mbc.py`: schemas, balance law, graphs, endpoint chains, manager.
- `io24gtk.py`: Mixer controls, lifecycle reconciliation, Host snapshot
  adoption, and fault presentation.
- `io24.py`: strict `host_features.pan` validation and legacy migration.
- `tests/test_io24_host_parameter_repairs.py`: state, graph, UI, lifecycle, and
  migration regressions.
- `README.md` and `GUIDE.md`: truthful endpoint and persistence documentation.
- Task-local `PROGRESS.md`, `RESUME.md`, and checksum records after verification.

No device-slot, Voice FX, firmware, Wine, installer, or publication file is in
this implementation boundary.

## Test design

Implementation begins test-first with hardware-free failures for:

1. Exact current schema validation and rejection of extra, missing, Boolean,
   non-finite, and out-of-range values.
2. Legacy input-pan migration to centered Mix A/B balances without semantic
   reuse of the old positions.
3. Exact six-input selection for Mix A and Mix B, including a regression that
   capture 1-2 never appear in either graph.
4. Center-unity stereo balance, hard-edge muting, monotonic attenuation, and no
   left/right crossfeed.
5. Two distinct passive `Audio/Source` configurations with no playback target
   or `Audio/Sink` identity.
6. Independent endpoint start, update, failure, restart, idempotence, shutdown,
   and temporary-directory cleanup.
7. GTK structure: three aligned knobs, permanently unavailable Main, removal of
   per-input controls/toggle/status, and no routine-move toast.
8. Host-file save/load round trip for version 2 `pan`, validation before device
   setters, and a visible legacy-migration message only on discrete load.
9. Existing affected Host/package/matrix regressions to ensure this change does
   not reopen Task 5 outside the intended files.

The fake-device GTK paint run and screenshots require a separate exact Host
launch authorization even with the interface unplugged. Live PipeWire endpoint
discovery, routing, sound, latency, and shutdown acceptance require their own
later authorization and cannot be inferred from unit tests.

## Offline acceptance criteria

The implementation is ready for user review only when:

- all new focused tests pass after demonstrating the intended RED failures;
- the affected hardware-free Host suite passes with `ResourceWarning` elevated
  to an error;
- the release-package regression and deterministic parameter matrix still pass;
- current docs contain no claim that Main is captured or that the endpoints
  route automatically to playback;
- the approved peer snapshot boundary is refreshed only under exact renewed
  disclosure authority; and
- task-local progress, recovery text, and checksums describe offline evidence
  without promoting it to live operation.

## Peer coordination

Codex and the dedicated Claude peer make independent technical judgments and
exchange them through the append-only peer inbox/outbox. One decision-focused
review is required before implementation and one closure review after the
verified implementation. Agreement advances the work immediately. A follow-up
turn is warranted only for a concrete defect or a material disagreement; clean
reviews are not repeated for ceremony. The peer snapshot remains bound to its
exact authorized 53-file disclosure unless the user separately approves an
expansion.

## Deferred gates

This design does not resolve:

- a complete capturable Main bus;
- live PipeWire six-channel negotiation or source visibility;
- routing, audible balance behavior, or latency;
- visual acceptance in the real GTK Host;
- private Voice FX activation, device-slot recall, or power-cycle persistence;
- installation or publication.

Those remain separately scoped and separately authorized.
