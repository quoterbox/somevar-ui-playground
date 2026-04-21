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
