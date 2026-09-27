import zipfile
from pathlib import Path

import pytest

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


def test_extract_and_check_source(tmp_path: Path) -> None:
    archive = make_archive(tmp_path)
    staging = tmp_path / 'staging'
    staging.mkdir()

    source = updater.extract(archive, staging)

    assert source.name == 'source'
    updater.check_source(source, 'demo')


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


def test_check_source_invalid(tmp_path: Path) -> None:
    with pytest.raises(UpdaterError):
        updater.check_source(tmp_path, 'demo')


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


def test_apply_source_requires_url(tmp_path: Path) -> None:
    root = make_install(tmp_path)
    install = Install(kind=Kind.SOURCE, root=root, manager=Manager.PIP)

    with pytest.raises(UpdaterError):
        updater.apply_source_archive(install, 'demo', '')
