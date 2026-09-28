from support import FakeProvider

from qt_updater import App
from qt_updater.core import has_update


def test_has_update() -> None:
    assert has_update('1.0.0', '2.0.0')
    assert not has_update('2.0.0', '2.0.0')
    assert not has_update('3.0.0', '2.0.0')


def test_version_fallback() -> None:
    app = App(package='definitely_not_installed_pkg', provider=FakeProvider())
    assert app.version == '0'
