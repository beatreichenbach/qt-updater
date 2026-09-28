import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from support import make_release

from qt_updater import UpdaterError
from qt_updater.core import Install, Kind, Manager, updater


def make_archive(tmp_path: Path, package: str = 'demo', version: str = '2.0.0') -> Path:
    source = tmp_path / 'source'
    (source / package).mkdir(parents=True)
    (source / package / '__init__.py').write_text(f"__version__ = '{version}'")
    (source / 'pyproject.toml').write_text(f'version = "{version}"')

    archive = tmp_path / f'archive-{version}.zip'
    with zipfile.ZipFile(archive, 'w') as file:
        for path in source.rglob('*'):
            file.write(path, path.relative_to(tmp_path))
    return archive


def make_install(tmp_path: Path, package: str = 'demo') -> Path:
    root = tmp_path / 'install'
    (root / package).mkdir(parents=True)
    (root / package / '__init__.py').write_text("__version__ = '1.0.0'")
    (root / 'pyproject.toml').write_text('version = "1.0.0"')
    (root / '.venv').mkdir()
    (root / '.venv' / 'marker').write_text('keep')
    (root / 'custom').mkdir()
    (root / 'custom' / 'data').write_text('keep')
    return root


def test_run_executes_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(updater.subprocess, 'run', fake_run)
    install = Install(kind=Kind.REGISTRY, root=None, manager=Manager.PIP)

    assert updater.run(install, 'demo', make_release()) == 0
    assert calls == [[sys.executable, '-m', 'pip', 'install', 'demo', '--upgrade']]


def test_run_stops_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess:
        calls.append(command)
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(updater.subprocess, 'run', fake_run)
    install = Install(kind=Kind.REGISTRY, root=None, manager=Manager.PIP)

    assert updater.run(install, 'demo', make_release()) == 1
    assert len(calls) == 1


def test_main_runs_update(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        updater,
        'detect_install',
        lambda package: Install(kind=Kind.REGISTRY, root=None, manager=Manager.PIP),
    )
    monkeypatch.setattr(updater.subprocess, 'run', fake_run)

    assert updater.main(['demo', 'v2.0.0', 'https://ex.com/src.zip']) == 0
    assert calls == [[sys.executable, '-m', 'pip', 'install', 'demo', '--upgrade']]


def test_extract_and_check_source(tmp_path: Path) -> None:
    archive = make_archive(tmp_path)
    staging = tmp_path / 'staging'
    staging.mkdir()

    source = updater.extract(archive, staging)

    assert source.name == 'source'
    updater.check_source(source, 'demo')

    with pytest.raises(UpdaterError):
        updater.check_source(tmp_path, 'demo')


def test_extract_flat_archive(tmp_path: Path) -> None:
    source = tmp_path / 'flat'
    (source / 'demo').mkdir(parents=True)
    (source / 'demo' / '__init__.py').write_text('')
    (source / 'pyproject.toml').write_text('version = "2.0.0"')
    archive = tmp_path / 'flat.zip'
    with zipfile.ZipFile(archive, 'w') as file:
        for path in source.rglob('*'):
            file.write(path, path.relative_to(source))

    staging = tmp_path / 'flat-staging'
    staging.mkdir()

    extracted = updater.extract(archive, staging)

    assert extracted == staging
    updater.check_source(extracted, 'demo')


def test_apply_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = make_archive(tmp_path)
    root = make_install(tmp_path)
    install = Install(kind=Kind.SOURCE, root=root, manager=Manager.PIP)

    monkeypatch.setattr(updater, 'download', lambda url: archive)

    updater.apply_source_archive(install, 'demo', 'https://example.com/source.zip')

    assert '2.0.0' in (root / 'demo' / '__init__.py').read_text()
    assert '2.0.0' in (root / 'pyproject.toml').read_text()
    assert (root / '.venv' / 'marker').read_text() == 'keep'
    assert (root / 'custom' / 'data').read_text() == 'keep'
    assert not (root / '.demo-backup').exists()
