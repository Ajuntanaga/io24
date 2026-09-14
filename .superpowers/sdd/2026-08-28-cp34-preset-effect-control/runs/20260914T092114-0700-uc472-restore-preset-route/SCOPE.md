# What UC 4.7.2 actually does on RestorePreset — scope

Objective: the `MemP/Stat`-plus-selector route is closed negative on hardware,
with a positive control proving the meter was not blind. That leaves the
question the nulls could not answer — if that route is not how a preset is
recalled, what is? Answer it from the exact vendor binary rather than the wire.

Method: static analysis of the retained UC 4.7.2 `dspusbdevice.dll`
(4,979,672 bytes, SHA-256 `de685e89...`). Pin the high-level request
receiver's message vocabulary, both `RestorePreset` branches, the channel
applier, and the module's parameter-frame builder to exact instruction bytes;
then test, over the module's own direct call graph, whether the applier can
reach any function that materialises a `MemP`, `Stat`, or `PrsM` tag.

Boundary: no device, USB, audio, Host, Wine, network, or firmware action. No
vendor code is loaded or executed. `NEXT.md`'s standing instruction against a
speculative `PrsM` write is respected — nothing was written anywhere.
