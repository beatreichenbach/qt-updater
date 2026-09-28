import pytest
from PySide6 import QtCore
from support import FakeProvider, make_release

from qt_updater import App, CheckResult, UpdateChecker


@pytest.fixture(scope='module', autouse=True)
def application() -> QtCore.QCoreApplication:
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def collect(checker: UpdateChecker, app: App) -> CheckResult:
    results: list[CheckResult] = []
    loop = QtCore.QEventLoop()

    def on_finished(result: CheckResult) -> None:
        results.append(result)
        loop.quit()

    checker.finished.connect(on_finished)
    QtCore.QTimer.singleShot(5000, loop.quit)
    checker.check(app)
    loop.exec()
    checker.finished.disconnect(on_finished)

    assert results
    return results[0]


def make_app(version: str, latest: str | None) -> App:
    provider = FakeProvider(make_release(latest) if latest is not None else None)
    return App(package='demo', provider=provider, version=version)


def test_reused_for_another_app() -> None:
    checker = UpdateChecker()

    assert collect(checker, make_app('1.0.0', '2.0.0')).available
    assert collect(checker, make_app('1.0.0', '1.0.0')).up_to_date
