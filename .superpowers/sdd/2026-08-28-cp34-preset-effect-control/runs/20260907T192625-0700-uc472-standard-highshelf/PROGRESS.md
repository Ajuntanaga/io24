# UC 4.7.2 Standard high-shelf recovery progress

Final status: `UC472_STANDARD_HIGHSHELF_SOURCE_BOUND`

- The exact DLL's `eqtype4` record is at `0x1800ede48`; the task brief's
  `0x1800ef2e8` is stale for this retained binary and is explicitly rejected as
  the descriptor identity.
- Standard UI enum `2` reaches mapper table `[3, 8, 9, 6]` and therefore
  designer selector `9`.
- The Standard band route enters double full recompute `0x18000f8b0`, selector
  branch `0x18001039d`, and the matching incremental branch `0x1800175cd`.
- Inputs are three binary32 values widened to binary64.  Source-ordered
  binary64 operations produce object fields `[b0, -a1, b1, -a2, b2]`, each
  independently narrowed to binary32 at `0x180014396`.
- The retained Bright Vocal tuple produces exact little-endian bytes
  `ac5ce03f98b18e3ff79b16c08c69b6be1c88573f`; full and incremental
  transcriptions agree.
- The bounded analyzer, production helper, GTK reuse contract, validation,
  boundary vectors, matrix scoping, and focused 121-test regression set are
  GREEN.  The deterministic matrix remains 750 rows and regenerates
  byte-identically.

The analysis remains static and source-bound; no runtime or hardware claim is
made.
