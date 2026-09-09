# Claude/Codex handoff — io24 CP34 Host

Updated: 2026-09-08

## Start here

The authoritative recovery record is `RESUME.md` in this directory. Continue
the active CP34 Host lane only. The task outcomes remain device-resident preset
save/assign/recall and audible Voice FX. The sealed host-persistence work is an
immutable predecessor; CP33/Wine and older transport trees are historical and
must not be revived during an ordinary continuation.

Current implementation ledger:

- `../../FULL-PARAMETER-VERIFICATION-PLAN/progress.md`
- `../../FULL-PARAMETER-VERIFICATION-PLAN/task-1-report.md`
- `../../FULL-PARAMETER-VERIFICATION-PLAN/task-2-report.md`
- `../../FULL-PARAMETER-VERIFICATION-PLAN/task-3-brief.md`

There is no Git repository. Task-local checkpoints, exact SHA-256 inventories,
focused tests, and deterministic artifact regeneration are the recovery and
review mechanism. Do not assume a clean baseline from timestamps alone.

## Pre-Codex Claude evidence

Claude's original project records are retained at:

- `/home/ajuntanaga/.claude/projects/-home-ajuntanaga-Development-Experiments-PreSonus-Revelator---UniCont/memory/MEMORY.md`
- `/home/ajuntanaga/.claude/projects/-home-ajuntanaga-Development-Experiments-PreSonus-Revelator---UniCont/memory/io24-preset-model-solved.md`
- `/home/ajuntanaga/.claude/projects/-home-ajuntanaga-Development-Experiments-PreSonus-Revelator---UniCont/memory/io24-where-we-left-off.md`
- `/home/ajuntanaga/.claude/projects/-home-ajuntanaga-Development-Experiments-PreSonus-Revelator---UniCont/ca785e36-dad8-467f-a189-06fa83de894c.jsonl`
- `/home/ajuntanaga/.claude/projects/-home-ajuntanaga-Development-Experiments-PreSonus-Revelator---UniCont/68415eac-d655-4e97-abf9-7d350e007f55.jsonl`

Those records establish that the Host UI and preset workflow existed and worked
before the Claude-to-Codex handoff. In particular, the 2026-08-10/11 state had
the Host UI, four global preset blocks paired by channel, factory/scene preset
application, and the recovered preset/effect model. Treat later CP34 task-local
evidence as authoritative where it narrows or corrects an older claim. Do not
reuse the old live/Wine instructions: current project rules expressly forbid
Wine and require a separate exact authorization for every device/live action.

## Current verified Host state

Tasks 1 and 2 are complete and independently re-reviewed:

- Reconciled the P1 Host repairs, including headphones source shadow/UI state,
  atomic compressor preflight, exact Standard compressor class dispatch,
  correct Standard outer-shelf toggle, and fail-closed Passive/Vintage replay.
- Implemented the source-bound Host Hot Key as a per-channel, momentary Host
  snapshot transition with exact normal-state restoration and no invented wire
  command.
- Final focused evidence is 97 required tests plus a deterministic 750-row
  parameter matrix and a valid 7-entry campaign checkpoint. Exact hashes are in
  the two task reports.

Task 3 is complete: the retained-DLL route proves selector 9, production and GTK
share the source-order implementation, the exact golden bytes are pinned, 121
affected tests pass, and both task/campaign checkpoints passed at closure. It is
static/source-bound evidence only. Passive/Vintage remain fail-closed pending
their exact builders.

Task 4 is complete. The offline P2 audit corrections pass 77 focused and 162
broader affected tests; the deterministic 750-row matrix and both checkpoints
are GREEN. Across two serialized turns, the Claude peer independently closed
Tasks 3 and 4 with no open finding. Its report-provenance finding was corrected:
the pre-edit hash for `tests/test_io24_loopback_foundation.py` was not captured
and is no longer represented as unchanged.

Task 5 is complete: the wheel ships all 15 runtime modules and seven console
entry points, including `io24-scene`; isolated wheel imports and the hardware-
free module invocation are executable regressions. Later Host work quarantined
device-slot selectors from ordinary Host snapshots, removed Channel-2
experiment controls from the production Effects page, and split the fixed
80 Hz preamp HPF from the adjustable Fat Channel HPF. The expanded affected
suite passes 121/121 and the current 750-row matrix is deterministic. The
physical io24 display behavior remains an unrun, separately authorized live
gate; consult `RESUME.md` for the exact current state and probe boundary.

## Collaboration protocol

The durable peer is one serialized unattended Claude `-p` session, invoked by
`./claude-io24-peer-turn` at every task boundary. It uses a distinct UUID in
`.context/claude-peer-session-id`; consult session `ac576547-...` is retired and
must never be resumed. The optional interactive terminal is not the canonical
channel and must not run concurrently with an unattended turn.

For asynchronous coordination, the canonical independent-peer channel is the
isolated `.claude-peer/` workspace at the project root:

1. Codex writes `.claude-peer/INBOX.md`. Claude's `-p` response is appended
   verbatim to `.claude-peer/OUTBOX.md` by the fixed wrapper; Codex does not
   summarize or filter it.
2. Claude analyzes the copied evidence under `.claude-peer/evidence/` and binds
   every finding to `.claude-peer/EVIDENCE.sha256`; it does not see or edit the
   live project tree.
3. Drafts remain in `.claude-peer/` until an explicit import/recovery boundary
   exists. Never claim a snapshot result is confirmed-current without refresh.
4. The initial task-local ledgers remain historical records of the consult
   setup; they are not used as a security boundary.
5. Never revert another agent's edits. Record exact identities and verification
   evidence for any later production import.
6. Every peer turn first runs `refresh-claude-peer-evidence`, verifies the
   sorted manifest, and stamps `SNAPSHOT.md`. Calls are locked so the peer UUID
   cannot fork into concurrent histories.

## Non-negotiable boundary

No USB/device access, interface claims, transfers, firmware action, preset or
effect operations, audio actions, Host launch, Wine/protected-prefix access,
network reacquisition, install, staging, user-cache mutation, or Obsidian
mutation without separate exact authorization. A connected device is state, not
authority. Stop live work at or below 10% battery. Static local source reading,
bounded disassembly of retained artifacts, code edits, and hardware-free tests
are the present lane.
