# CP34 UC 4.7.2 host-source retention audit - progress

Timestamp: 2026-09-05T18:37:25-07:00
Status: locally checkpointed availability result; exact serializer analysis is
blocked on source reacquisition and separate network authority

## Result

The exact UC 4.7.2 host artifacts used by the 2026-08-30 static analysis are
no longer present at their recorded temporary paths and were not found by the
bounded exact-name/exact-size local searches. The controlling result is:

`UC472_HOST_SERIALIZER_SOURCE_UNAVAILABLE_IN_BOUNDED_LOCAL_ROOTS`

This is an artifact-availability result, not a protocol conclusion. The exact
leading bytes supplied by UC 4.7.2 for a valid live `Stat` record remain
unresolved. In particular, this audit does not justify prepending integer `2`
to the Linux record, changing the writer, or replaying a device operation.

## Exact missing sources

The independently reviewed historical report records these temporary sources:

- installer: 186,792,552 bytes, SHA-256
  `1b5ddd6fd3ad4b93529caf8e5933bcd52b13194bdfa62652292b46ddcd980b95`;
- `Universal Control.exe`: 22,172,120 bytes, SHA-256
  `27f9fe550b466c9d783e3432d6663bb02af9aa001b23165985a56c96005e1a96`;
- `cclgui.dll`: 7,053,272 bytes, SHA-256
  `04cd73f8f6e65cd025c61b586b87c32093d75f3289e2d73e9e5ccf9b4506bd16`;
- UC 4.7.2 `hwaccess/dspusbdevice.dll`: 4,979,672 bytes, SHA-256
  `de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.

Running the historical `SHA256SUMS` check reports all four `/tmp` artifacts as
missing. Its six durable/current rows still verify: the installed comparison
DLL, analyzer, analyzer tests, both JSON inventories, and the historical
report.

## Bounded search

No exact-name or exact-size match was found in:

- `/tmp`, maximum depth 4;
- `Downloads`, `Desktop`, and `Documents`, maximum depth 4;
- `Archive`, maximum depth 5, explicitly pruning `Windows.old`;
- `.cache`, `Development`, `Projects`, `Research`, `recovered`, and
  `Ventoy-backup`, maximum depth 6.

The searches used idle I/O priority and timeouts where the roots could be
large. Permission-denied diagnostics from system-owned private `/tmp`
directories do not establish their contents; the conclusion is deliberately
limited to the accessible bounded roots. Neither `.wine-io24` nor any Wine
prefix was accessed.

## Non-substitute current artifacts

The installed comparison artifacts currently hash as:

- `hwaccess/dspusbdevice.dll`: 4,984,704 bytes, SHA-256
  `567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b`;
- `Universal Control.exe`: 37,248,392 bytes, SHA-256
  `0e5744435f98c86cabd0e9d13bd30392627405229138b3697a2260a6d184014d`.

They are not the missing UC 4.7.2 sources. The installed DLL still contains
the pinned firmware recovery package used for in-memory firmware analysis;
that does not make its host serializer UC 4.7.2.

## Preserved evidence and boundary

The old report and JSON inventories remain durable and bind their conclusions
to the exact UC 4.7.2 hashes. They preserve queue/caller topology and the
high-level save route, but do not preserve the byte-level serializer slice
needed to resolve the new four-byte prefix question.

The preceding firmware result remains valid within its own boundary: live
dispatcher `0x420bc` consumes caller-supplied `Stat` bytes from cursor zero and
structured-state method `0x531e0` requires native word `2`. The bridge from a
valid host- or recall-generated record to those leading bytes is still
unresolved. The missing artifact must be reacquired at its exact hash before
claiming a UC 4.7.2 source-bound answer.

## Safety

No network, Wine, protected-prefix, USB/device, ALSA, preset/effect, reset,
DFU, install, staging, firmware-image, or REAPER action occurred. Battery was
97 percent and charging at the end of the audit.

## Next exact action

With separate explicit network authorization, reacquire the exact installer
hash above into temporary storage, extract without loading vendor code, verify
the UC 4.7.2 module hash, and then trace the serializer. Without that authority,
stop here; an installed-UC-5.0 comparison may be analyzed only as a separately
named comparison and cannot close the UC 4.7.2 question.
