from support import FakeProvider

from qt_updater import App


def test_version_fallback() -> None:
    app = App(package='definitely_not_installed_pkg', provider=FakeProvider())
    assert app.version == '0'
