import enum
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from ..core import App, CheckResult, Release, command, format_command
from .checker import UpdateChecker
from .qt_material_icons import MaterialIcon


class Stage(enum.Enum):
    CHECKING = enum.auto()
    PROMPT = enum.auto()
    UPDATING = enum.auto()
    DONE = enum.auto()


class UpdateDialog(QtWidgets.QDialog):
    """
    Dialog to check, prompt, and apply an update.

    It emits ``restart_requested`` once an update is successfully installed.
    """

    restart_requested: QtCore.Signal = QtCore.Signal()

    def __init__(
        self,
        app: App,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._app = app
        self._release: Release | None = None
        self._stage = Stage.CHECKING
        self._checked = False

        self._init_ui()
        self._init_process()
        self._apply_stage()

        self._checker = UpdateChecker(self)
        self._checker.finished.connect(self._on_checked)

    def _init_ui(self) -> None:
        self.setWindowTitle('Update')
        self.resize(480, 120)

        layout = QtWidgets.QVBoxLayout(self)

        # Header
        header = QtWidgets.QHBoxLayout()

        self.status_icon_label = QtWidgets.QLabel()
        self.status_icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        header.addWidget(self.status_icon_label)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        header.addWidget(self.status_label)
        header.addStretch()

        layout.addLayout(header)

        # Terminal
        self.terminal_text = QtWidgets.QPlainTextEdit()
        self.terminal_text.setReadOnly(True)
        self.terminal_text.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        self.terminal_text.setFont(font)
        layout.addWidget(self.terminal_text, 1)

        # Buttons
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()

        self.primary_button = QtWidgets.QPushButton()
        self.primary_button.clicked.connect(self._on_primary)
        buttons.addWidget(self.primary_button)

        self.secondary_button = QtWidgets.QPushButton()
        self.secondary_button.clicked.connect(self._on_secondary)
        buttons.addWidget(self.secondary_button)

        layout.addLayout(buttons)

        # Icons
        self._pixmap_pending = MaterialIcon('pending').pixmap()
        self._pixmap_check = MaterialIcon('check').pixmap()
        self._pixmap_update = MaterialIcon('system_update_alt').pixmap()
        self._pixmap_error = MaterialIcon('error').pixmap()

    def _init_process(self) -> None:
        channel_mode = QtCore.QProcess.ProcessChannelMode.MergedChannels
        self._process = QtCore.QProcess(self)
        self._process.setProcessChannelMode(channel_mode)
        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._process.state() == QtCore.QProcess.ProcessState.Running:
            self._process.kill()
            self._process.waitForFinished()
        if self._stage is Stage.CHECKING:
            self._checker.finished.disconnect(self._on_checked)
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """Start the check the first time the dialog is shown."""

        super().showEvent(event)

        if not self._checked:
            self._checked = True
            self._checker.check(self._app)

    def _apply_stage(self) -> None:
        """Render the status, terminal and buttons for the current stage."""

        if self._stage is Stage.CHECKING:
            self.status_label.setText(f'Checking {self._app.package} for updates...')
            self.status_icon_label.setPixmap(self._pixmap_pending)
            self.terminal_text.setVisible(False)

            self.primary_button.setText('Cancel')
            self.primary_button.setEnabled(True)
            self.secondary_button.setVisible(False)
            return

        if self._stage is Stage.PROMPT:
            release = self._release
            if release is not None:
                self.status_label.setText(
                    f'Version {release.version} is available. '
                    f'You are running {self._app.version}.'
                )
            self.status_icon_label.setPixmap(self._pixmap_update)
            self.terminal_text.setVisible(False)

            self.primary_button.setText('Update')
            self.secondary_button.setText('Later')
            self.secondary_button.setVisible(True)
            return

        if self._stage is Stage.UPDATING:
            self.resize(720, 480)

            self.status_label.setText('Updating...')
            self.status_icon_label.setPixmap(self._pixmap_pending)
            self.terminal_text.setVisible(True)

            self.primary_button.setEnabled(False)
            self.secondary_button.setText('Stop')
            self.secondary_button.setVisible(True)
            return

        if self._stage is Stage.DONE:
            self.terminal_text.setVisible(bool(self.terminal_text.toPlainText()))

            self.primary_button.setText('Close')
            self.primary_button.setEnabled(True)
            self.secondary_button.setVisible(False)
            return

    def _start_update(self) -> None:
        """Launch the updater subprocess and stream it into the terminal."""

        if self._release is None:
            return

        self._stage = Stage.UPDATING
        self.terminal_text.clear()
        self._apply_stage()

        args = command(self._app.package, self._release)
        self.terminal_text.appendPlainText(format_command(args))
        self.terminal_text.appendPlainText('\n\n')
        self._process.start(args[0], args[1:])

    def _read_output(self) -> None:
        output = bytes(self._process.readAllStandardOutput().data())
        if not output:
            return

        self.terminal_text.insertPlainText(output.decode('utf-8', errors='replace'))
        scrollbar = self.terminal_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _cancel(self) -> None:
        self._checker.finished.disconnect(self._on_checked)
        self.reject()

    def _on_primary(self) -> None:
        if self._stage is Stage.CHECKING:
            self._cancel()
        elif self._stage is Stage.PROMPT:
            self._start_update()
        else:
            self.reject()

    def _on_secondary(self) -> None:
        if self._stage is Stage.PROMPT:
            self.reject()
        else:
            self._process.kill()

    def _on_checked(self, result: CheckResult) -> None:
        """
        Move to the prompt or a terminal stage from a check result.

        A result that arrives after leaving the checking stage is dropped.
        """

        if self._stage is not Stage.CHECKING:
            return

        if result.release is not None:
            self._release = result.release
            self._stage = Stage.PROMPT
        elif result.error:
            self.status_label.setText(result.error)
            self.status_icon_label.setPixmap(self._pixmap_error)
            self._stage = Stage.DONE
        else:
            self.status_label.setText('You are running the latest version.')
            self.status_icon_label.setPixmap(self._pixmap_check)
            self._stage = Stage.DONE
        self._apply_stage()

    def _on_finished(self, exit_code: int, _status: object = None) -> None:
        self._read_output()
        self._stage = Stage.DONE
        self._apply_stage()

        if exit_code == 0:
            self.status_label.setText('Update complete. Restart to finish.')
            self.status_icon_label.setPixmap(self._pixmap_check)
            self.restart_requested.emit()
        else:
            self.status_label.setText(f'Update failed with exit code {exit_code}.')
            self.status_icon_label.setPixmap(self._pixmap_error)

    def _on_error(self, error: QtCore.QProcess.ProcessError) -> None:
        if error == QtCore.QProcess.ProcessError.FailedToStart:
            self.terminal_text.appendPlainText(
                f'error: could not start {sys.executable}'
            )
            self._on_finished(-1)


def show_update_dialog(app: App, parent: QtWidgets.QWidget | None = None) -> int:
    """Show the update dialog and return its result code."""

    dialog = UpdateDialog(app, parent)
    return dialog.exec()
