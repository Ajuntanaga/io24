import hashlib
from pathlib import Path
import shutil
import subprocess
from unittest import mock
import zipfile

import pytest
import io24_eq_setup as setup


@pytest.fixture
def pinned(monkeypatch):
    data = b'test-only DLL fixture'
    monkeypatch.setattr(setup, 'DSP_SIZE', len(data))
    monkeypatch.setattr(setup, 'DSP_SHA256', hashlib.sha256(data).hexdigest())
    return data


def test_install_and_repeat(tmp_path, pinned):
    source = tmp_path / 'source.dll'
    source.write_bytes(pinned)
    target = tmp_path / 'cache' / 'dspusbdevice.dll'
    assert setup.install(source, target)
    assert target.read_bytes() == pinned
    assert not setup.install(source, target)


def test_wrong_hash_preserves_destination(tmp_path, pinned):
    source = tmp_path / 'source.dll'
    source.write_bytes(b'x' * len(pinned))
    target = tmp_path / 'existing.dll'
    target.write_bytes(b'keep me')
    with pytest.raises(ValueError, match='SHA-256'):
        setup.install(source, target)
    assert target.read_bytes() == b'keep me'


def test_conflicting_destination_preserved(tmp_path, pinned):
    source = tmp_path / 'source.dll'
    source.write_bytes(pinned)
    target = tmp_path / 'existing.dll'
    target.write_bytes(b'keep me')
    with pytest.raises(ValueError):
        setup.install(source, target)
    assert target.read_bytes() == b'keep me'


def test_actual_archive_extraction(tmp_path, pinned):
    if not (shutil.which('7z') or shutil.which('7zz')):
        pytest.skip('7-Zip unavailable')
    archive = tmp_path / 'installer fixture.zip'
    with zipfile.ZipFile(archive, 'w') as output:
        output.writestr('app/subdir/dspusbdevice.dll', pinned)
        output.writestr('app/other.txt', 'not needed')
    assert setup.obtain_data(archive) == pinned


def test_failed_extraction_does_not_install(tmp_path):
    source = tmp_path / 'installer.exe'
    source.write_bytes(b'invalid')
    with mock.patch.object(setup.shutil, 'which', return_value='/usr/bin/7z'), mock.patch.object(setup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 2)):
        with pytest.raises(ValueError, match='could not extract'):
            setup.install(source, tmp_path / 'cache.dll')
    assert not (tmp_path / 'cache.dll').exists()
