# Result

The live routing trial completed and restored safely, but the audible Voice FX
question remains **unproved because the capture had no listening-level source**.

- Serial `AB7C22200355` matched.  Battery was 94 percent at execution and 93
  percent at the final independent read.
- The device confirmed Channel 2 `3 -> 2`, stereo link on, Channel 2 `2 -> 3`,
  then stereo link off.  The final flags were again `0x1a1`; Channel 1 remained
  disabled on slot 0 and its readable gain/processing/slot/enable guard was
  unchanged.  Channel 2 finished enabled on slot 3.
- The 14-second, six-channel capture completed without error at SHA-256
  `e587d9a7cbf78312eabcb4b2b4ee5e2f806d88335d3c812dd4d7372b1120aa14`.
- During the linked slot-3 window, capture channels 3-6 each followed Input 2
  with correlation `0.99999668` and direct coefficient `0.70797731` (-3 dB).
  A joint fit found a 150 ms coefficient of only `0.00000642`; no delayed
  component is present in the captured noise.
- Input 2 nevertheless peaked at only -83.66 dBFS (RMS -97.15 dBFS), 36.16 dB
  below the exact factory Slap Echo gate threshold of -47.5 dBFS.  The open
  cable therefore supplied no signal that the preset was required to pass or
  echo.  This is `NO_150MS_COMPONENT_IN_CAPTURED_NOISE`, not proof that a safe
  line-level transient would be dry.

No follow-on hardware action is justified while the operator rests.  The next
discriminating trial still requires a known safe source physically feeding
Input 2 (or separately authorized and restorable gain/gate changes).
