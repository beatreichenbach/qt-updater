import qt_themes
from PySide6 import QtWidgets

from qt_updater import App, UpdateDialog


def test_dialog() -> None:
    application = QtWidgets.QApplication()
    qt_themes.set_theme('one_dark_two')

    app = App.github(
        package='qt-updater',
        repository='beatreichenbach/qt-updater',
    )

    UpdateDialog(app).exec()

    application.exec()


if __name__ == '__main__':
    test_dialog()
