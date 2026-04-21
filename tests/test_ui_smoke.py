import os


def test_playground_window_smoke_offscreen() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from PySide6.QtWidgets import QApplication

    from somevar_ui_playground.registration import create_app_registration

    app = QApplication.instance() or QApplication([])
    registration = create_app_registration()
    window = registration.create_window()

    try:
        assert window.windowTitle() == 'SomeVar UI Playground'
        assert window.minimumWidth() > 0
    finally:
        window.close()
        window.deleteLater()


def test_detached_window_follows_theme_changes() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from PySide6.QtWidgets import QApplication

    from somevar_ui_playground.registration import create_app_registration

    app = QApplication.instance() or QApplication([])
    registration = create_app_registration()
    window = registration.create_window()

    try:
        window._open_detached_window('tool')
        detached = window._detached_windows[-1]

        window._apply_theme('light')

        assert '#f4f7fb' in detached.styleSheet()
    finally:
        for detached in list(window._detached_windows):
            detached.close()
            detached.deleteLater()
        window.close()
        window.deleteLater()
