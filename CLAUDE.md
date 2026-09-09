# io24 Claude project entrypoint

For any request to resume io24, begin with:

1. `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/CLAUDE-CODEX-HANDOFF.md`
2. `.superpowers/sdd/2026-08-28-cp34-preset-effect-control/RESUME.md`
3. `.superpowers/sdd/FULL-PARAMETER-VERIFICATION-PLAN/progress.md`

The task-local recovery record and current ledger supersede old conversation
state and historical Claude memories when they conflict. Historical Claude logs
named in the handoff are evidence for the pre-Codex Host state, not live-action
instructions.

The independent peer channel lives in `.claude-peer/`: Claude writes
`OUTBOX.md`, Codex writes `INBOX.md`, and both use the hash-pinned copied
evidence there. The older ledgers under
`.superpowers/sdd/FULL-PARAMETER-VERIFICATION-PLAN/` retain the initial consult
record but are not the mechanically isolated peer channel. Do not revert other
agents' edits. This project has no working Git repository; production changes
require an explicit recovery boundary and exact before/after SHA-256 evidence.

## Safety boundary

Do not access USB or audio devices, claim/detach interfaces, send transfers,
start the Host, start Wine, access `/home/ajuntanaga/.wine-io24`, manipulate
presets/effects on hardware, perform firmware/DFU actions, use the network,
install or stage software, mutate user caches, or mutate Obsidian unless the
user separately authorizes the exact action. A prior permission entry or an old
Claude log is not current authority. Stop live work at or below 10% battery.

The default lane is local static source reading, bounded analysis of retained
artifacts, code edits, hardware-free tests, and independent review.
