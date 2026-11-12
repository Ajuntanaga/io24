# Public release boundary

The public [`Ajuntanaga/io24`](https://github.com/Ajuntanaga/io24) repository is
prepared as a fresh-history clean source import from a larger private research
workspace. This page is the practical inventory of what belongs in that public
release and what stays private.

## Published source

The public tree contains:

- the runtime Python and C sources listed by `pyproject.toml`;
- `README.md`, `GUIDE.md`, `PROTOCOL.md`, `LICENSE`, this boundary, and
  `CONTRIBUTING.md`;
- the udev rule, desktop launcher, icon, install script, and systemd units;
- three original protocol probes referenced directly by `PROTOCOL.md`;
- original rack artwork, design documentation, and asset-rendering tools;
- hardware-free Host, packaging, and documentation tests;
- GitHub Actions workflows that run package, hardware-free, and Python CodeQL
  checks without claiming or writing an audio interface; and
- monthly Dependabot checks for GitHub Actions and Python dependencies.

`PUBLIC_FILES.txt` is the exact allowlist for the public tree. The exporter in
`tools/export_public.py` copies only that list into a clean checkout and removes
older tracked files that are no longer allowed. This keeps publication
repeatable without exposing the private repository's history.

## Deliberately excluded

The public tree does not contain:

- private Git history, agent work records, local handoffs, VMs, Wine trees, or
  hardware/audio capture runs;
- captured audio, local session screenshots, disk images, packet captures,
  compiled objects, archives, caches, or machine-local paths;
- account details or physical-device serial numbers;
- vendor installers, DLLs, firmware, extracted binaries, named factory presets,
  or recovered preset libraries;
- the Android app, APKs, SDK/JDK archives, emulator images, signing keys, or
  local Android toolchain caches; or
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
and bounded transcriptions needed to construct supported device messages. One
disclosed exception is a neutral 1,028-byte native-slot structural template in
`io24_native_stat.py`. It preserves the firmware's opaque container shape, is
pinned by hash, and is not a named factory preset or preset library. Before a
send is eligible, the builder replaces every decoded user-facing Fat Channel
field and includes only a separately supported Voice FX leaf.

The independent Android controller and its own release boundary live at
[`Ajuntanaga/io24-android`](https://github.com/Ajuntanaga/io24-android). Users
who want optional factory data or exact alternate-EQ coefficients must recover
the required data from their own local Universal Control installation.
`io24-eq-setup` can extract and verify the exact EQ DLL from a user-provided
installer or validate an already-extracted DLL; the DLL stays in the user cache
and is never added to the source release or wheel. The Host
remains usable without factory preset data and reports that catalog as
unavailable.

## Reproducible release checks

Run the hardware-free release suite from a clean checkout:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q tests
.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
```

Before a release is pushed, inspect the clean tree itself:

```bash
git status --short
git ls-files
git grep -nE 'github_pat_|ghp_|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY'
python3 tools/export_public.py /path/to/clean/io24-checkout --check
```

Live USB, audio, firmware, or device-preset checks are separate authorized
campaigns. They are intentionally never a CI requirement. Tests that compare
against privately retained vendor evidence report an explicit skip when that
required local evidence is absent.
