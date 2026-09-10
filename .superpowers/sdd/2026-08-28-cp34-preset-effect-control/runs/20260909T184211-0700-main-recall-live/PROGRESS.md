# MAIN live recall through the patched Host

Timestamp: 2026-09-09T18:42:11-07:00

Status: `MAIN_RECALLED_VOICEFX_GATE_OPENED_LISTENING_PENDING`

## Issue and action

Block 201 was not failing because of Detuner defaults, routing, or wet/dry
values. Its handler silently discards direct Voice FX writes until the native
`Stat` structured-state load opens its three internal gate flags. Device-slot
recall is the decoded Host action that runs that load.

The open Host was a stale pre-patch process: its `MAIN` and `B A S E` entries
were inert and it owned USB interface 5, which made a separate direct recall
attempt stop at `USBError: [Errno 16] Resource busy` before any write. The old
window was closed normally. The installed `io24-mixer` launcher, which points
at this worktree, then opened the patched Host. From its Presets page, the
`MAIN` / `Recall on device` action invoked Channel 1 global slot 0. The Effects
page subsequently exposed both of these live UI states:

```text
Opened
MAIN was recalled on Channel 1, so model and parameter edits reach the engine
```

The Host remains open on Effects. MAIN's stored Detuner body is loaded; human
listening is the remaining audibility observation.

## Scope

- Battery before the action: 37 percent.
- Connected USB identity: `194f:0422`.
- Exactly one requested device mutation: recall Channel 1 global slot 0.
- No device-slot body write; `MAIN` and `B A S E` contents were untouched.
- No Wine, firmware, DFU, reset, install, or network action.

## Verification

The interrupted save-path refactor left two stale test fixtures. They now
match the `Save only` / `Save and activate` controls and call the extracted
preset-adoption helper. The 748-row matrix was regenerated twice from the
current sources; both copies were byte-identical:

```text
e2294b839c7be884e10f8991d8a723954d86c49e2affd2a34fc1711f4f79c540
```

Focused suite:

```text
112 passed, 36 subtests passed, 0 failed
```

Full suite with `ResourceWarning` elevated to error:

```text
495 passed, 1 skipped, 124 subtests passed, 0 failed
```
