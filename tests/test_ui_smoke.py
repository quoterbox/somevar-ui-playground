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


def test_modal_overlay_tracks_root_geometry() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from PySide6.QtWidgets import QApplication

    from somevar_ui_playground.registration import create_app_registration

    app = QApplication.instance() or QApplication([])
    registration = create_app_registration()
    window = registration.create_window()

    try:
        window._open_simple_modal()
        overlay = window._modal_overlay

        assert overlay is not None
        assert overlay.parentWidget() is window.centralWidget()
        assert overlay.geometry() == overlay.parentWidget().rect()

        window.resize(window.width() + 120, window.height() + 80)
        app.processEvents()

        assert overlay.geometry() == overlay.parentWidget().rect()
    finally:
        if window._modal_overlay is not None:
            window._modal_overlay.close_modal()
            app.processEvents()
        window.close()
        window.deleteLater()


def test_snapped_window_frame_uses_zero_root_margins(monkeypatch) -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from PySide6.QtWidgets import QApplication

    from somevar_ui_playground.registration import create_app_registration
    from somevar_ui_playground.ui import window as playground_window

    app = QApplication.instance() or QApplication([])
    registration = create_app_registration()
    window = registration.create_window()

    try:
        monkeypatch.setattr(
            playground_window.win_platform,
            'resolve_window_shell_state',
            lambda widget: playground_window.win_platform.WindowShellState.SNAPPED,
        )
        window._window_frame_state = playground_window.win_platform.WindowShellState.NORMAL
        window._update_window_frame()

        margins = window._root_layout.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (0, 0, 0, 0)
        assert window._window_frame_state is playground_window.win_platform.WindowShellState.SNAPPED
        assert window.centralWidget().property('shellState') == 'snapped'
        assert window.centralWidget().property('maximized') is False
    finally:
        window.close()
        window.deleteLater()


def test_maximized_window_frame_keeps_native_root_inset(monkeypatch) -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from PySide6.QtWidgets import QApplication

    from somevar_ui_playground.registration import create_app_registration
    from somevar_ui_playground.ui import window as playground_window

    app = QApplication.instance() or QApplication([])
    registration = create_app_registration()
    window = registration.create_window()

    try:
        monkeypatch.setattr(
            playground_window.win_platform,
            'resolve_window_shell_state',
            lambda widget: playground_window.win_platform.WindowShellState.MAXIMIZED,
        )
        monkeypatch.setattr(playground_window.win_platform, 'native_frame_margin', lambda default=8: 8)
        window._window_frame_state = playground_window.win_platform.WindowShellState.NORMAL
        window._update_window_frame()

        margins = window._root_layout.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (8, 8, 8, 8)
        assert window._window_frame_state is playground_window.win_platform.WindowShellState.MAXIMIZED
        assert window.centralWidget().property('shellState') == 'maximized'
        assert window.centralWidget().property('attached') is True
    finally:
        window.close()
        window.deleteLater()
