# Candidate: UC 4.7.2 offline guest ready

Status: staged locally; not promoted

## Done

Universal Control 4.7.2.108537 was installed in the isolated Windows guest and
the guest was shut down cleanly.

## Verified

The installed executable reports `4.7.2.108537`; `VERSION_MATCH=1`,
`VERIFY_EXIT=0`, and the final qcow2 check reports zero errors.

## Unverified

The Revelator io24 rack and live Voice FX transaction remain unobserved because
no USB device was attached.

## Decisions

Keep UC 5.0 excluded, networking disabled, and USB passthrough separately
gated. Do not save presets or accept firmware updates during the capture.

## Evidence

- `PROGRESS.md`
- `UC472-VERIFY.png`
- `.vm/io24-windows/README.md`

## Next

After exact USB/device authorization, attach only serial `AB7C22200355` and
capture the smallest Voice FX enable/disable transaction.
