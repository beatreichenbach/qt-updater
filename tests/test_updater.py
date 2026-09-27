import subprocess
import sys
from pathlib import Path

import pytest
from support import FakeProvider, make_release

from qt_updater import App, UpdaterError
from qt_updater.core import CheckResult, Install, Kind, Manager, runner, updater


def make_app() -> App:
    return App(package='demo', provider=FakeProvider())


def test_command_passes_arguments() -> None:
    release = make_release('2.0.0', tag='v2.0.0', source_url='https://ex.com/src.zip')
    command = runner.command('demo', release)

    assert command[0] == sys.executable
    assert command[1].endswith('updater.py')
    assert command[2:] == ['demo', 'v2.0.0', 'https://ex.com/src.zip']


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


def test_check_clean_tree_rejects_dirty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(command, 0, stdout=' M demo.py\n')

    monkeypatch.setattr(updater.subprocess, 'run', fake_run)
    install = Install(kind=Kind.GIT, root=tmp_path, manager=Manager.PIP)

    with pytest.raises(UpdaterError):
        updater.check_clean_tree(install)


def test_check_clean_tree_allows_clean(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(command, 0, stdout='')

    monkeypatch.setattr(updater.subprocess, 'run', fake_run)
    install = Install(kind=Kind.GIT, root=tmp_path, manager=Manager.PIP)

    updater.check_clean_tree(install)


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


def test_main_requires_arguments(caplog: pytest.LogCaptureFixture) -> None:
    assert updater.main(['demo']) == 2
    assert 'usage' in caplog.text


def test_main_reports_install_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def raise_error(package: str) -> Install:
        raise updater.InstallError('nope')

    monkeypatch.setattr(updater, 'detect_install', raise_error)

    assert updater.main(['demo', 'v2.0.0']) == 2
    assert 'nope' in caplog.text


def test_update_spawns_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, 'run', fake_run)

    assert runner.update(make_app(), make_release()) == 0
    assert commands[0][0] == sys.executable
    assert commands[0][1].endswith('updater.py')


def test_update_without_release(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(runner, 'check', lambda app: CheckResult())

    assert runner.update(make_app()) == 0
    assert 'No update available' in capsys.readouterr().out


def test_update_reports_check_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(runner, 'check', lambda app: CheckResult(error='boom'))

    assert runner.update(make_app()) == 0
    assert 'boom' in capsys.readouterr().out
