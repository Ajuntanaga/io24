# CP34 read-only preflight command record

At `2026-09-03T23:04:39-07:00`, the exact authorized command was:

```text
PYTHONDONTWRITEBYTECODE=1 python3 re/cp34_readonly_preflight.py \
  --serial AB7C22200355
```

The dedicated client checked the host battery before USB enumeration, verified
the exact serial before claiming interface 5, selected alternate setting 1, and
sent exactly two `GetP | Appl(0) | JaSt` requests. It returned `PASS`; the two
2040-byte `Rply` payload hashes were identical. The client has no `SetP`, audio,
Wine, firmware, detach, network, endpoint-clear, or vendor-control-query path.

The run ends here. No subsequent USB request, preset/effect operation, audio
operation, or device mutation is authorized by this record.
