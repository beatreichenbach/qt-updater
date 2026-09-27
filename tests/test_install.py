import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest
from support import FakeDistribution, make_release

from qt_updater import InstallError
from qt_updater.core import Install, install

PACKAGE = 'demo'


def test_detect_missing_package(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_missing(name: str) -> FakeDistribution:
        raise PackageNotFoundError(name)

    monkeypatch.setattr(install.metadata, 'distribution', raise_missing)

    with pytest.raises(InstallError):
        install.detect_install(PACKAGE)


def test_detect_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution()
    )

    result = install.detect_install(PACKAGE)

    assert result.kind == install.Kind.REGISTRY
    assert result.manager == install.Manager.PIP


def test_detect_editable_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / 'demo'
    (root / '.git').mkdir(parents=True)
    direct = {'url': root.as_uri(), 'dir_info': {'editable': True}}
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution(direct)
    )

    result = install.detect_install(PACKAGE)

    assert result.kind == install.Kind.GIT
    assert result.root == root
    assert result.editable


def test_detect_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / 'demo'
    (root / '.git').mkdir(parents=True)
    direct = {'url': root.as_uri(), 'dir_info': {'editable': False}}
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution(direct)
    )

    assert install.detect_install(PACKAGE).kind == install.Kind.GIT


def test_detect_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / 'demo'
    root.mkdir()
    direct = {'url': root.as_uri(), 'dir_info': {'editable': False}}
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution(direct)
    )

    assert install.detect_install(PACKAGE).kind == install.Kind.SOURCE


def test_detect_vcs(monkeypatch: pytest.MonkeyPatch) -> None:
    direct = {
        'url': 'https://github.com/acme/app',
        'vcs_info': {'vcs': 'git', 'requested_revision': 'main', 'commit_id': 'abc'},
    }
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution(direct)
    )

    result = install.detect_install(PACKAGE)

    assert result.kind == install.Kind.VCS
    assert result.url == 'https://github.com/acme/app'


def test_detect_archive_falls_back_to_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    direct = {'url': 'https://ex.com/demo.whl', 'archive_info': {'hash': 'sha256=x'}}
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution(direct)
    )

    assert install.detect_install(PACKAGE).kind == install.Kind.REGISTRY


def test_detect_uv_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prefix = tmp_path / 'uv' / 'tools' / 'demo'
    prefix.mkdir(parents=True)
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution()
    )
    monkeypatch.setattr(install.sys, 'prefix', str(prefix))

    result = install.detect_install(PACKAGE)

    assert result.kind == install.Kind.REGISTRY
    assert result.manager == install.Manager.UV_TOOL


def test_detect_pipx_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prefix = tmp_path / 'pipx' / 'venvs' / 'demo'
    prefix.mkdir(parents=True)
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution()
    )
    monkeypatch.setattr(install.sys, 'prefix', str(prefix))

    result = install.detect_install(PACKAGE)

    assert result.manager == install.Manager.PIPX


def test_manager_from_installer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        install.metadata, 'distribution', lambda name: FakeDistribution(installer='uv')
    )

    assert install.detect_install(PACKAGE).manager == install.Manager.UV


def test_git_commands(tmp_path: Path) -> None:
    result = Install(kind=install.Kind.GIT, root=tmp_path, manager=install.Manager.PIP)
    commands = install.git_commands(result, make_release('2.0.0', tag='v2.0.0'))

    assert commands[0] == ['git', '-C', str(tmp_path), 'fetch', '--tags', '--force']
    assert commands[1] == ['git', '-C', str(tmp_path), 'checkout', 'tags/v2.0.0']


def test_git_commands_registry() -> None:
    result = Install(kind=install.Kind.REGISTRY, root=None, manager=install.Manager.PIP)
    assert install.git_commands(result, make_release()) == []


def test_manager_command_registry_pip() -> None:
    result = Install(kind=install.Kind.REGISTRY, root=None, manager=install.Manager.PIP)
    command = install.manager_command(result, PACKAGE, make_release())
    assert command == [sys.executable, '-m', 'pip', 'install', 'demo', '--upgrade']


def test_manager_command_registry_uv() -> None:
    result = Install(kind=install.Kind.REGISTRY, root=None, manager=install.Manager.UV)
    command = install.manager_command(result, PACKAGE, make_release())
    assert command == [
        'uv',
        'pip',
        'install',
        '--python',
        sys.executable,
        'demo',
        '--upgrade',
    ]


def test_manager_command_editable(tmp_path: Path) -> None:
    result = Install(
        kind=install.Kind.GIT,
        root=tmp_path,
        manager=install.Manager.PIP,
        editable=True,
    )
    command = install.manager_command(result, PACKAGE, make_release())
    assert command == [sys.executable, '-m', 'pip', 'install', '-e', str(tmp_path)]


def test_manager_command_vcs() -> None:
    result = Install(
        kind=install.Kind.VCS,
        root=None,
        manager=install.Manager.PIP,
        url='https://github.com/acme/app',
    )
    command = install.manager_command(result, PACKAGE, make_release(tag='v2.0.0'))
    assert 'demo @ git+https://github.com/acme/app@v2.0.0' in command
    assert command[-1] == '--upgrade'


def test_manager_command_tool() -> None:
    result = Install(
        kind=install.Kind.REGISTRY, root=None, manager=install.Manager.UV_TOOL
    )
    assert install.manager_command(result, PACKAGE, make_release()) == [
        'uv',
        'tool',
        'upgrade',
        'demo',
    ]

    result = Install(
        kind=install.Kind.REGISTRY, root=None, manager=install.Manager.PIPX
    )
    assert install.manager_command(result, PACKAGE, make_release())[:2] == [
        'pipx',
        'upgrade',
    ]
