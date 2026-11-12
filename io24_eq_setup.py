"""Install optional exact-EQ data from a local DLL or Windows installer."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from io24_uc472_vintage_eq import DSP_SHA256, DSP_SIZE, DEFAULT_DLL


def verified_bytes(path):
    path = Path(path)
    if path.stat().st_size != DSP_SIZE:
        raise ValueError("DLL size does not match the required Universal Control 4.7.2 build")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != DSP_SHA256:
        raise ValueError("DLL SHA-256 does not match the required Universal Control 4.7.2 build")
    return data


def obtain_data(source):
    source = Path(source).expanduser().resolve(strict=True)
    if source.suffix.lower() == '.dll':
        return verified_bytes(source)
    extractor = shutil.which('7z') or shutil.which('7zz')
    if not extractor:
        raise ValueError("Install 7-Zip (Debian/Ubuntu: sudo apt install p7zip-full), or supply an extracted dspusbdevice.dll")
    with tempfile.TemporaryDirectory(prefix='io24-eq-extract-') as temporary:
        # Flat extraction selects only this filename; no installer code is run.
        completed = subprocess.run(
            [extractor, 'e', '-y', '-r', '-aoa', '-o' + temporary,
             str(source), 'dspusbdevice.dll'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=180, check=False)
        candidate = Path(temporary) / 'dspusbdevice.dll'
        if completed.returncode != 0 or not candidate.is_file():
            raise ValueError("7-Zip could not extract dspusbdevice.dll from this installer. Supply the DLL from your own extracted Universal Control 4.7.2 installation instead.")
        return verified_bytes(candidate)


def install(source, destination):
    data = obtain_data(source)
    destination = Path(destination).expanduser()
    if destination.exists():
        if verified_bytes(destination) == data:
            return False
        raise ValueError("Existing destination differs; preserve it and choose another --destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Publish only complete validated data; never overwrite a pre-existing file.
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.io24-eq-', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            os.link(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Local UC 4.7.2 Windows installer or dspusbdevice.dll')
    parser.add_argument('--destination', type=Path, default=DEFAULT_DLL,
                        help='Cache path (defaults to Host path, including environment override)')
    args = parser.parse_args(argv)
    try:
        changed = install(args.source, args.destination)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, 'EQ setup failed: %s\n' % error)
    print(('Installed' if changed else 'Already installed') + ': ' + str(args.destination))
    print('Exact Passive/Vintage EQ data verified. Restart the Host if it is open.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
