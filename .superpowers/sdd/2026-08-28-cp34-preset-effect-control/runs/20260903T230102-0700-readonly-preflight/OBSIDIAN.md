# CP34 read-only io24 preflight

`PASS` at 2026-09-03T23:04:39-07:00.

- io24 serial: `AB7C22200355`; firmware descriptor: `1.28`.
- Host battery: 84%.
- Interface 5 / alternate 1 accepted two identical read-only JaSt replies.
- Readable state: channel 1 slot 0 enabled; channel 2 slot 2 enabled.
- The device shows preset-block icons only, not names; compression is present
  across all currently onboard presets.

This does not expose slot titles or stored records, and does not prove preset
commit, recall, or audible Voice FX. The live scope ended after these reads.
