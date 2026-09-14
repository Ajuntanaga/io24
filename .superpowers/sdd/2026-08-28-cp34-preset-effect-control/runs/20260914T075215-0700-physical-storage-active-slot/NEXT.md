# Next writer boundary after the active-slot null

The existing UC 4.7.2 source analysis already resolves `PrsM`: it is the
twelve-record Device Presets/library namespace at indexes 16..27. It uses the
same `MemP` fragmenter and firmware storage writer as `Stat`. It is distinct
from the four fast-access button slots, and no separate low-level Assign frame
has been located.

A direct `PrsM` write is therefore not the next live discriminator. It would
overwrite an unreadable library entry without proving button assignment or
recall, and the current authorization named only global `Stat` slot 3.

The next useful acquisition is one known UC 4.7.2 `sendToMixer` plus button-
assignment sequence captured at the native-control boundary, or a source-bound
continuation through the panel's `ZStr`/UCNet transfer into the exact operation
that changes the four fast-access assignments. Only after that edge is known
should a specific `PrsM` index and restoration plan be proposed for hardware.

Until then, the Linux Host's working host-side presets plus direct DSP setters
are the supported equivalent while connected. Device-resident custom save and
standalone recall remain the one missing UC capability; firmware flashing is
not implicated or authorized.
