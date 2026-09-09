# Progress

## Implemented

- Added RED then GREEN regressions proving default Host-file load and cached
  reapply no longer issue preset mode, slot, or enable calls, including the
  exact stale-Channel-1-selector/Channel-2-processing incident shape.
- Added explicit `include_device_preset_state=True` backend opt-in while
  retaining quarantined cache entries.
- Changed GTK reconnect accounting so selector-only cache state does not raise
  a misleading reapply banner.
- Renamed generic file actions to Host snapshots and disclosed quarantined
  selector counts after save, load, and cached reapply.
- Removed the live Channel-2 Delay/Slap Echo experiment actions and deferred
  custom-firmware/private-lane scaffolding from the production Effects page.
- Removed the dead private-reverb GTK helper after Claude identified that its
  removed widget dependencies would cause an AttributeError.
- Split the two HPF presentations: `Preamp HPF 80 Hz` on the Mixer page and one
  synchronized `Fat Channel HPF` surface with Off/40/80/160/Advanced modes.
- Updated GUIDE.md and README.md for the corrected domains.

## Verification

- Focused Host-state/Host-parameter/preset tests: 62 passed.
- Expanded affected Host suite: 121 passed, including release packaging, Host
  repairs, full parameter inventory, Standard high shelf, Host state, preset
  persistence, VoiceFX preset application, Host Hot Key, and Host delay.
- The 750-row parameter matrix regenerated three times (checked-in plus two
  `/tmp` outputs) and all bytes match at SHA-256
  `4fae0d3d338a00a9ce1892a20109a43381530131d28914f174cbeed851beedac`.
  The final regeneration reflects a documentation-only comment correction in
  `io24.py`; row count and parameter content remain unchanged.
- Dedicated Claude UUID `288f3639-1f23-4309-bd76-168255b7644e`; relevant
  peer turns completed with zero permission denials. Claude verified the
  quarantine and HPF UI, found the dead-helper defect that was corrected, and
  ultimately agreed Channel 1 is the only deterministic display-probe target.
- The last successful peer snapshot closed the executable quarantine/HPF review
  cleanly. Two later attempts to review the final comment-only `io24.py` digest
  and refreshed Task 5 checkpoint returned `Request timed out` with zero input/
  output tokens and zero permission denials. Those attempts are retained as
  unavailable transport results, not counted as peer approval.
- The historical five-entry Task 5 checkpoint was refreshed for the current
  README identity and verifies. Its release-package regression passes again.

## Open live gate

The user explicitly means the physical io24 screen. Static firmware-1.28
evidence classifies the preamp `input1/2HighPassFilter` parameters as booleans
and the digital `filter/hpf` as a separate component, but this does not disprove
the user's remembered physical display behavior.

The agreed decisive probe is human-paced, Channel-1-only, and strictly limited
to live `set_highpass_freq` values 40, 80, 160, and one non-basic value such as
55 Hz, with an exact 24 Hz bypass write in `finally`. It must refuse unless the
exact io24 identity, battery above 10 percent, MAIN slot 0 enabled, stereo link
off, and stable Channel-2 readable state all match. It must never save, select,
enable, or overwrite a device slot. This probe has not been run or authorized.
