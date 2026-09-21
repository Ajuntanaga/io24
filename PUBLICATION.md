# Public release boundary

The public [`Ajuntanaga/io24`](https://github.com/Ajuntanaga/io24) repository is
prepared as a fresh-history clean source import from a larger private research
workspace. This page is the practical inventory of what belongs in that public
release and what stays private. It is not a legal conclusion.

## Published source

The public tree contains:

- the runtime Python and C sources listed by `pyproject.toml`;
- `README.md`, `GUIDE.md`, `PROTOCOL.md`, `LICENSE`, this boundary, and
  `CONTRIBUTING.md`;
- the udev rule, desktop launcher, icon, install script, and systemd units;
- three original protocol probes referenced directly by `PROTOCOL.md`;
- hardware-free functional, packaging, and documentation tests; and
- a GitHub Actions workflow that runs those checks without claiming or writing
  an audio interface.

## Deliberately excluded

The public tree does not contain:

- private Git history, agent work records, local handoffs, VMs, Wine trees, or
  hardware/audio capture runs;
- captured audio, screenshots, disk images, packet captures, compiled objects,
  archives, caches, or machine-local paths;
- account details or physical-device serial numbers;
- vendor installers, DLLs, firmware, extracted binaries, or recovered factory
  preset bodies; or
- decompiler output and component-model XML extracted from Universal Control.

These exclusions are why releases are built as clean source imports rather than
by deleting files from the private history: deleting a tracked file in a later
commit would not remove it from earlier commits.

## Vendor-derived research artifacts

The private research workspace retains material such as
`re/param_consumers.txt`, `re/uc_factory_presets.json`, and recovered Universal
Control component-model XML. None of it is included in the public repository or
Python wheel, and this project's GPL does not relicense it.

The published runtime contains this project's original interoperability code
and bounded transcriptions needed to construct supported device messages. Users
who want optional factory data or exact alternate-EQ coefficients must recover
the required data from their own lawful Universal Control copy. The Host remains
usable without factory preset data and reports that catalog as unavailable.

## Reproducible release checks

Run the hardware-free release suite from a clean checkout:

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest -q \
  tests/test_io24_host_parameter_repairs.py \
  tests/test_io24_host_state_repair.py \
  tests/test_io24_global_fx.py \
  tests/test_io24_scene.py \
  tests/test_io24_uc_parity_closure.py \
  tests/test_io24_standard_eq_ui.py \
  tests/test_io24_vintage_eq_view.py \
  tests/test_io24_spring.py \
  tests/test_io24_multiband_insert.py \
  tests/test_publication_docs.py \
  tests/test_io24_release_package.py
python3 -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
```

Before a release is pushed, inspect the clean tree itself:

```bash
git status --short
git ls-files
git grep -nE 'github_pat_|ghp_|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY'
```

Live USB, audio, firmware, or device-preset checks are separate authorized
campaigns. They are intentionally never a CI requirement. Tests that compare
against privately retained vendor evidence report an explicit skip when that
lawful local evidence is absent.
