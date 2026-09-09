# MAIN/B A S E restoration and Host repair progress

Status: `LIVE_EFFECTS_REPAIR_GREEN`

The shared-reverb transaction now establishes its feed and Main return before
arming the engine. Plate was written live to Channel 1 at 35 percent processing
mix with a 0 dB Main return, then the control connection closed. Fresh audible
confirmation is not inferred.

Multiband now selects its ready PipeWire sink as the system output and restores
the physical io24 output when disabled or on Host shutdown. A bounded live
start/select/restore/stop round trip passed. The physical output was unmuted at
its existing 40 percent volume; no playback streams were active.

The patched Host is open. The affected suite passes 142/142, and the 748-row
matrix SHA-256 is
`aa9e26fd432110d6ea3d96aafe3a353a8fa43d2070efc60d80881a2d5a675643`.
No review was requested or performed. Block-201 Voice FX activation remains a
separate unresolved device gate.

The two user-requested complete records were sent to the exact Channel-1 device
blocks and recorded in the identity-bound Host registry. MAIN is active. The
device does not expose stored-body readback, so transport completion is not
mislabelled as a decoded device read.

Host source fixes now expose both user presets, require the real multiband node
before showing On, and establish the visible Channel-1/Main shared-reverb path
when its engine is enabled.

The bus strip is now meters only: all Main/Mix A/Mix B pan knobs and their
runtime and snapshot state are removed. Mix A/B remain fixed-unity passive
stereo sources. Old `host_features.pan` data is discarded and cannot be
re-saved.

Preset block dots now use faster, deeper opacity-only breathing (1.8 s for
Block 1, 0.9 s for Block 2) with a fixed animated radius. Section descriptions
were removed from the Host; the explanatory copy remains in README.md and
GUIDE.md.

Final verification after those refinements: focused Host 63/63; affected
source, persistence, inventory, and hot-key suite 140/140 with
`ResourceWarning` elevated to error; release-package 1/1 without installation.
Two fresh 748-row matrices match the checked-in artifact at SHA-256
`94c1d5af78ee652b22c98893d7dd619edc84af84b379f079e3e1c0832978b23e`.

The project launcher executes this working tree directly. The stale multiband
child was stopped and the repaired Host was launched without installing or
replacing a package.
