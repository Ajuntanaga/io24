# Block 201 is inert; block 202 is audible on the same return

Status: `BLOCK201_INERT_BY_EAR_ON_A_PROVEN_LIVE_RETURN`

Decided by ear on serial `AB7C22200355`, firmware `0128`, 2026-09-15, with the
user listening on headphones. This is the first block-201 null taken on the bus
the block actually feeds, with an in-run positive control that fired.

## Rig

An instrument cable in Input 1 with the user's finger on the far end as the
source. No playback stream: audio played to Main never enters Channel 1, and an
earlier attempt that played beeps could not have reached the FX at all.

    Input 1 -> channel 1 DSP -> FX send ('Para' wire 4, 1.000)
            -> block 201 -> fxreturn/ch1 -> Main (+6.79 dB) -> headphones

The Host was **closed**, which is the point that wasted two runs: the send and
return are established by the Host, so with it shut nothing had opened them and
arming a model was arming it into a return routed nowhere. The scripts now
perform that transaction themselves through `Io24.establish_effects_return`.

## Result

| engine | state | heard |
|---|---|---|
| block 202 reverb | on, size 0.96, fully wet | **yes** — "reverb is on", and again on cue at the end of two runs |
| block 201 delay | 450 ms, feedback 0.55, 100 % wet, reverb held off, 3 on/off phases | no — "dry signal" |
| block 201, all six models | each fully wet in turn, reverb held off | no — "signal is dry" |

Transcripts: `delay-ab-transcript.txt`, `sweep-transcript.txt`. The sweep armed
delay, transformer, detuner, ringmod, vocoder and filters in sequence, 8 s on
and 3 s off each, then turned the reverb on for 8 s; the user reported dry
throughout and "now theres reverb again" at the control.

So the shared effects return into Main demonstrably carries block 202, and
block 201 on that identical path, with 202 silenced, renders nothing on any of
its six models.

## What this settles, and what it corrects

**The send/return repair is real and necessary.** The reverb only became audible
once the transaction was performed; that is the defect fixed in
`Io24.establish_effects_return` and its callers. Block 201 needs the same path.

**But the wrong bus was not the whole story, and I said it was.** The earlier
claim that CP34's nulls were "the expected reading of the wrong bus" is half
right: the bus was wrong, and fixing it does not make block 201 audible. The
CP34 measurements reached the correct conclusion for block 201 by an unsound
route; the conclusion stands.

**The 2026-07-28 "Delay ear-verified" claim does not survive.** That record has
Delay, De-Tuner and Transformer heard on this unit and this firmware. It also
records, about the first delay test, that it "only appeared to work because the
reverb's routing was still open from the previous test" — and block 202 shares
the very return block 201 feeds, so the same confound applies to the
verification that followed it. A reverb with pre-delay and stereo
decorrelation is a fair description of "a panning echo thing". Today's runs
silenced 202 explicitly and swept all six models; nothing was heard. Treat the
2026-07-28 audibility claim as the reverb heard through the shared return.

## Remaining hypothesis

One route is untested and cannot be reached from the host: the device applies
its stored preset at power-on, so a cold boot with a stored Voice-FX-on slot and
no host attached is the last place block 201 could render. Everything
host-reachable is now closed by ear. That test needs a power cycle and separate
authorization.

## Boundary

Writes were the channel processing scalar, `fxreturn/ch1 -> Main` level and
assignment, block 201 and block 202 — every one Host-known in the shadow and
resent exactly at the end of each run. Readable state matched before and after
the bracketed A/B run. No preset slot, `processingChannel`, gain, phantom or
link was touched. Battery 60 → 59 %.

## Third confirmation, with a guitar

The two runs above used an instrument cable with a finger on the far end — a
weak, broadband source, which left open the worry that a subtle effect was
simply inaudible in it. With a **guitar** plugged into Input 1, the reverb held
off, and the delay left armed at 250 ms / feedback 1.00 / 100 % wet through
`fxreturn/ch1 -> Main` at +6.79 dB, the user reports: "I hear dry, I dont hear
any fx". A strong sustained harmonically rich source changes nothing.

An intermediate report of "some kind of vibrato or something with the reverb" is
accounted for: the Host-known reverb state carries `fs=96000.0` while the device
is running 48 kHz, and reverb coefficients built for the wrong rate produce
exactly that wobble. A six-pair A/B of block 201 alone, with the reverb left
exactly as it was, did not track it.

Block 201 is therefore inert on the live host path by three independent ear
tests, against a positive control that fired in every one of them. Battery fell
60 % -> 14 % across the session; live work stopped there, above the 10 % floor.

The native stored-record route remains untested and is now prepared:
`re/io24_native_delay_recall.py` writes the firmware's **own** Channel-1 default
slot record — which already ships component 201 with `selected_model 5` — with
only the delay's four state words armed, then recalls it. The leaf format is
proven byte-for-byte against those firmware records, not inferred:
`io24_native_stat.encode_native_delay_state` reproduces the firmware's
`000000000000003fcdcccc3d5c8f423e` exactly, and the live `vech` payload after
its 12-byte header IS that leaf.
