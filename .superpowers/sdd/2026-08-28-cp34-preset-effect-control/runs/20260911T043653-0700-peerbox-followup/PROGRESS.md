# Peerbox follow-up — merge, shadow clear, Input 2 Doubler test

Authority: the user, 2026-09-11 ~04:35 PDT, "Proceed with all three" — the
merge of `io24-peerbox-20260911`, clearing the Host shadow, and Codex's
bounded Input 2 listening test (INBOX 2026-09-11 03:55, task 2).

## 1. Merge — done, no device action

Main-checkout `tests/test_io24_presets_page.py` was verified byte-identical to
`fa0d974` (`git diff fa0d974` empty), restored, then
`git merge --ff-only io24-peerbox-20260911`: `837da49..fa0d974`, 4 files.
Remaining dirt is the unrelated CP33 WinUSB files, untouched. Pre-merge full
suite on the branch worktree: 598 passed, 1 skipped, 125 subtests, exit 0.

## 2. Shadow clear — done, no device action

`io24.py shadow clear` opens USB only to reach `Io24.clear_shadow`, whose file
effect is `_store_shadow({})`. The file-only equivalent was run instead:
`python3 -c 'import io24; io24._store_shadow({})'`. No Host/io24 process was
running (the `host-view.pid` 2415188 is stale), so nothing could re-flush it.

| File | Bytes | SHA-256 |
|---|---|---|
| before, copied here as `shadow-before.json` | 9,593 | `45f3823be75ad7c9f04b60bc1aa0dc774343943ce1bc1fa77b2088f10cb14d45` |
| `~/.cache/io24/shadow.json` after (`{}`) | 2 | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` |

Recovery: copy `shadow-before.json` back to `~/.cache/io24/shadow.json`.
`~/.config/io24/` does not exist (no user presets, no last-session file).

## 3. Input 2 Doubler test — INCONCLUSIVE; block 2's reverb is inaudible

`re/io24_loopback_foundation.py` was not used: it has never run, and its
cleanup parks `line/ch2`, `fxreturn/ch1` and `return/ch1` off Main and leaves
Mix A holding only `line/ch2` (write-only, not restorable). The user chose a
hand-held patch cable instead: "I'll use a patch cable again. Static and pops
should work", listening to Channel 2 on Main/headphones.

`io24_input2_doubler_test.py` (here) opens `Io24(shadow=False)` and gates on
battery, serial `AB7C22200355` / firmware `0128`, link off, Input 2 phantom
off and Voice FX owned by Input 1. Exact output: `TEST-OUTPUT.txt`; starting
state: `before.json`. No audio was played or captured; no unit block,
routing or shared-reverb write.

1. `probe`: Channel 1 slot 0, Channel 2 slot 2, neither bypassed; link, mutes,
   phantom off; gains 30.0 / 24.288 dB; headphones 0.5, main 0.75; owner
   Input 1; battery 99 %.
2. `block 2`: recall slot 1 (MAIN + Doubler private reverb, canonical
   `175724d1…025d`); channel was processing, no enable asserted. `RESULT: OK`,
   every other readable value unchanged.
3. User, pops on Input 2: "Dry on Input 2". Positive control, pops on Input 1
   still on block 2: "Dry on Input 1 too".
4. `block 1`: recall slot 0. `RESULT: OK`; readable state equals `before.json`.

**Verdict.** Whether Input-1-owned Doubler processes Input 2 is `INCONCLUSIVE`:
the positive control failed, so a dry Input 2 proves nothing. New fact: a Host
recall of block 2 gives no audible tail even on the owner input, so slot 1
fails the audible acceptance left open in
`runs/20260911T003754-0700-presets-and-resume/PROGRESS.md`.

Not established: whether the unit's own Preset button behaves differently;
Channel 1's DSP amount (wire 4 is write-only; only "not bypassed" is known);
whether the Doubler's doubling, as distinct from its reverb, was present.
Offline lead from Codex's Task 4: `mix` (`model+0x350`) has no proven transfer
into the private core, and `width` (via `+0x358`) is the only proven core
input, so Wet/Dry 100 % may change nothing.

**Front-panel follow-up.** Stepping the blocks with the unit's own Preset
buttons, the user reported: "No tail on either channel or any block." The
front panel therefore behaves like the Host recall, closing the first
"not established" item above: no stored block engages audible Voice FX,
whichever path recalls it. This matches every earlier Voice FX listening
result on this unit (RESUME.md: 09-03 Channel 2 slot-3 recall edge "dry only";
09-06 Channel 2 materialization, no noticed change; 09-09 240 ms 100 %-wet
Delay inaudible while shared reverb worked). Shared reverb (block 202) remains
the only effect heard. Asked whether Voice FX was ever heard from a stored
block, the user said: "No, Ive never heard it from a stored block". The 09-09
directly-sent Detuner's pitch-drop confirmation is still recorded as pending.
Asked whether Voice FX was ever heard from the unit any other way, the user
said: "No, the host produces fx, just not the unit itself". Reading: effects
are heard while the Host drives the unit live, never from the unit on its own
(stored blocks, front panel). The Host's only computer-side processing is the
multiband compressor (`io24_mbc.py`, PipeWire filter-chain); it has no
software reverb or Voice FX, so a Host-driven effect is the unit's DSP under
live control (recorded example: shared reverb, block 202). Whether live Host
control has ever made block 201 Voice FX audible is not established here
(09-09: live 100 %-wet Delay inaudible; Detuner pitch drop still pending).
Tonight's test ran with no Host process. The user settled it: "thus far
reverb, but I havent checked since the other fx were apparently fixed". So the
only Host-driven effect heard is shared reverb; live Voice FX audibility is
unchecked since the 09-09 fixes.

## 4. Four-block layout — done on the user's go

The user: "Can you put both of those presets on both chanels and both
blocks", layout answer "MAIN 1, B A S E 2", then "Piano Accomany should be on
Channel 2 Block" / "block 2".

| | Block 1 | Block 2 |
|---|---|---|
| Channel 1 | MAIN, slot 0 (`f74cd983…`, not rewritten) | B A S E, slot 1 (`135a93f1…`) |
| Channel 2 | MAIN, slot 2 (`f74cd983…`) | Piano Accomany, slot 3 (`d58136ce…`) |

Piano Accomany is `Piano Accomany.scene` `line/ch2` (the scene's piano
channel, preamp 0 dB; identical to that scene's Channel 2 "Default" block),
built with the seven-section rule, which reproduced B A S E's `135a93f1…`
exactly as a check. It has no Voice FX section, like every Channel 2 body.
Preamp gain is not part of any block.

`io24_four_block_layout.py` (here), output `FOUR-BLOCK-OUTPUT.txt`; registry
before: `registry-before-four-block.json` (`ea66cab0…5d39`). Run 1 stopped
before any write: Channel 1 was on slot 1, left there by the user's
front-panel block test (the first `pgrep` gate had also self-matched and
was corrected). Run 2: recall Channel 1 block 1; write B A S E → 1; write
Piano → 3; recall Channel 2 block 2; write MAIN → 2; recall Channel 2 block 1.
Each write 1 fragment, 0 replies, `WRITE_SENT_UNVERIFIED`. After: slots
(0, 2), neither bypassed, link off, gains 30.0 / 24.288 dB, owner Input 1;
registry slots 0–3 carry the expected hashes. `RESULT: OK`. Slot bodies have
no readback; listening is the acceptance.
