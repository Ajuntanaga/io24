# Contributing

io24 controls real audio hardware. Ordinary pull-request checks must be fully
hardware-free: no USB claim, device write, firmware operation, audio routing, or
assumption that an attached interface is available.

## Development setup

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest -q tests/test_publication_docs.py tests/test_io24_release_package.py
```

Run the focused hardware-free tests for the code you changed as well; the full
release-suite command is maintained in [PUBLICATION.md](PUBLICATION.md). Tests
that compare against lawfully retained vendor evidence skip explicitly when
that local evidence is absent. Live tests
belong in an explicitly authorized local campaign and must report the exact
device, route, stimulus, restoration, and proof boundary; they are never a CI
requirement.

Keep user documentation honest about evidence. A successful USB reply proves a
write was sent, not cold-boot persistence, stored-body readback, or audibility.
Host snapshots, UC Device Presets, and the front-panel `Stat` blocks are distinct
workflows. VoiceFX is one shared block with one selected model and a separate
stored **On** field for every model component.

Do not add Universal Control installers, vendor DLLs or firmware, recovered
factory data, device serials, local absolute paths, captures, VMs, or agent work
records. See [PUBLICATION.md](PUBLICATION.md) for the public-source boundary.
