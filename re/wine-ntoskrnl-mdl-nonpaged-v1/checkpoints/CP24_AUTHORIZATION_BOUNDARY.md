# CP24 authorization boundary

The pre-existing explicit authorization covered one bounded, non-mutating
CP24 diagnostic against the freshly verified disposable clone. That single
`live-read` ran as `io24-wine-live-read-197499.service`, invocation
`8f9790c96bc84b8a9d331c11949d15e4`, and exited 1. The authorization is
consumed. It does not authorize a retry.

The run did not authorize and did not perform firmware access, Voice FX,
class-OUT, interface claim/release, kernel-driver detach, automatic detach,
alternate-setting changes, configuration changes, protected-prefix access,
or full Universal Control operation. Device presence or reconnection does not
renew the consumed authorization.

The next permitted work is offline and test-first. Any future device-visible
action requires new explicit authorization and a new full preflight. Pause at
10% battery or lower remains mandatory.
