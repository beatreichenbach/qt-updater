import pytest
from packaging.version import InvalidVersion
from support import FakeProvider, make_release

from qt_updater import App, check
from qt_updater.core import current_version, has_update


def test_has_update() -> None:
    assert has_update('1.0.0', '2.0.0')
    assert not has_update('2.0.0', '2.0.0')
    assert not has_update('3.0.0', '2.0.0')


def test_has_update_rejects_invalid_version() -> None:
    with pytest.raises(InvalidVersion):
        has_update('1.0.0', 'not-a-version')


def test_version_override() -> None:
    app = App(package='demo', provider=FakeProvider(), version='1.2.3')
    assert app.version == '1.2.3'


def test_version_fallback() -> None:
    app = App(package='definitely_not_installed_pkg', provider=FakeProvider())
    assert app.version == '0'


def test_current_version_missing_package() -> None:
    assert current_version('definitely_not_installed_pkg') == '0'


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
