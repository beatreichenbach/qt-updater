import subprocess
import sys

import pytest
from support import FakeProvider, make_release

from qt_updater import App, check
from qt_updater.core import CheckResult, runner


def make_app() -> App:
    return App(package='demo', provider=FakeProvider())


def test_check_returns_newer_release() -> None:
    app = App(package='demo', provider=FakeProvider(make_release()), version='1.0.0')
    assert check(app).available


def test_check_up_to_date() -> None:
    app = App(
        package='demo',
        provider=FakeProvider(make_release('1.0.0')),
        version='1.0.0',
    )
    assert check(app).up_to_date


def test_check_failed_provider() -> None:
    app = App(package='demo', provider=FakeProvider(None), version='1.0.0')
    assert check(app).failed


def test_check_reports_invalid_version() -> None:
    app = App(
        package='demo',
        provider=FakeProvider(make_release('not-a-version')),
        version='1.0.0',
    )
    assert check(app).failed


def test_update_spawns_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, 'run', fake_run)
    release = make_release('2.0.0', tag='v2.0.0', source_url='https://ex.com/src.zip')

    assert runner.update(make_app(), release) == 0
    assert commands[0][0] == sys.executable
    assert commands[0][1].endswith('updater.py')
    assert commands[0][2:] == ['demo', 'v2.0.0', 'https://ex.com/src.zip']


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
