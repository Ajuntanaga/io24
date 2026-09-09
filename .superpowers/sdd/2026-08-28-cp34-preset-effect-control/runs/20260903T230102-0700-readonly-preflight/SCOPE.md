# CP34 authorized read-only device preflight

## Exact authorization

Target: Revelator io24 serial `AB7C22200355`.

Permitted: read identity and host battery, claim USB interface 5 / alternate
setting 1, and issue only `GetP | Appl(0) | JaSt` state reads.

Prohibited: `SetP`, audio, preset/effect writes, Wine or its prefix, firmware,
USB detach, and network access. Stop at or below 10 percent battery.

## Objective

Record current read-only identity and selected-slot/enable PRESTATE without
promoting it to a stored-record readback or a device-content match.

## Completion rule

Complete only after the battery is safely above the floor, the exact serial
matches before interface claim, two valid `Rply`-tagged JaSt results are
recorded, the interface is released, and every result is explicitly limited to
readable state. Otherwise stop without an interface claim or write.
