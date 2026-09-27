import contextlib
from functools import partial

from PySide6 import QtCore

from ..core import App, CheckResult, check


class UpdateChecker(QtCore.QObject):
    finished: QtCore.Signal = QtCore.Signal(CheckResult)

    def check(self, app: App) -> None:
        """Check an app for updates in the background."""

        QtCore.QThreadPool.globalInstance().start(partial(self._check, app))

    def _check(self, app: App) -> None:
        result = check(app)
        # Handle garbage deleted QObject:
        with contextlib.suppress(RuntimeError):
            self.finished.emit(result)
