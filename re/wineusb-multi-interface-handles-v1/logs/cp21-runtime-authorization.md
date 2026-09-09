# CP21 live authorization and boundary

The user authorized connected-device testing, directed work through the next
three checkpoints, and required an immediate pause if battery reached 10%.
CP19 and CP20 remained hardware-free. CP21 used the authorization for one
bounded live-read after two complete preflights and one non-opening audit.

The first `driver-load` wrapper invocation failed before creating a systemd
unit because the outer shell lacked its user-bus environment. The missing unit,
empty journal, absent process, and unchanged device proved that no driver code
ran. After restoring only the user-bus environment, one USB-hidden candidate
driver-load ran. It did not expose a host USB node.

The only live-read ran as `io24-wine-live-read-464970.service`, invocation
`59fd56a3262a46d5b59922ce0600257b`. It exposed only io24 serial
`AB7C22200355` and was not retried. Battery was 63% and charging at its gate
and 64% and charging at immediate postflight.

Firmware, full Universal Control, Voice FX, the protected `.wine-io24` prefix,
kernel-driver detach, interface claim, alternate-setting change, and
configuration change remained outside this run. The observed PreSonus driver
made six clear-halt calls, but all six failed with `EBUSY`; no clear-halt USB
transaction completed.
