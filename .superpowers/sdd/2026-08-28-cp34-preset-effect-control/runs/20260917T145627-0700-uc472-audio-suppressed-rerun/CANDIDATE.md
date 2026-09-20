# Candidate: UC-captured VoiceFX transaction

Decision: implement

UC 4.7.2 proves the Linux Host had three protocol differences:

1. It reselected and rebuilt the model on every edit; UC performs state-only
   edits after one model materialization.
2. It omitted Transformer's two `MBdf` sample-rate tables.
3. It inserted 20 ms between frames and opened the reverb return; UC does
   neither.

The corrected implementation and regression tests are in the working tree.
The protocol behavior is complete. Audible acceptance is the one remaining
hardware check and was outside this audio-suppressed capture authorization.
