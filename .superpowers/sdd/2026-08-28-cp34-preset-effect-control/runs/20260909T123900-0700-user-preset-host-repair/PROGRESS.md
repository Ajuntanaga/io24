# MAIN/B A S E restoration and Host repair progress

Status: `LIVE_WRITES_SENT_HOST_REPAIR_GREEN`

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
