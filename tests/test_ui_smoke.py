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


def test_modal_size_policy_examples_are_distinct() -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from PySide6.QtWidgets import QApplication

    from somevar_ui.ui.kit.containers import ModalSizePolicy
    from somevar_ui_playground.ui.pages import (
        build_playground_categories,
        create_compact_fixed_modal_panel,
        create_elastic_modal_panel,
    )

    app = QApplication.instance() or QApplication([])
    compact = create_compact_fixed_modal_panel()
    elastic = create_elastic_modal_panel()
    categories, stack = build_playground_categories(None)

    try:
        compact_policy = compact.property('modalSizePolicy')
        elastic_policy = elastic.property('modalSizePolicy')

        assert isinstance(compact_policy, ModalSizePolicy)
        assert isinstance(elastic_policy, ModalSizePolicy)
        assert compact_policy.elastic_width is False
        assert compact_policy.max_width == 340
        assert elastic_policy.elastic_width is True
        assert elastic_policy.elastic_height is True
        assert elastic_policy.parent_width_ratio == 0.72
        assert categories[0].demo_count == 6
        assert categories[4].demo_count == 11
        assert len(categories[4].page._table_widgets) == 3
        assert categories[4].page._resizable_table.resizable_columns() is True
        assert categories[-1].demo_count == 3
    finally:
        compact.deleteLater()
        elastic.deleteLater()
        stack.deleteLater()


def test_qthread_transfer_demo_worker_moves_demo_file(tmp_path) -> None:
    from pathlib import Path

    from somevar_ui.ui.kit.tasks import TaskContext
    from somevar_ui_playground.ui.pages import _TRANSFER_DEMO_FILE_PREFIX, _run_throttled_file_transfer

    source = tmp_path / 'source'
    destination = tmp_path / 'destination'

    result = _run_throttled_file_transfer(
        TaskContext(),
        source_dir=str(source),
        destination_dir=str(destination),
        size_mb=0.1,
        speed_mb_s=64.0,
    )

    moved_file = Path(str(result['destination']))
    assert moved_file.exists()
    assert moved_file.name.startswith(_TRANSFER_DEMO_FILE_PREFIX)
    assert moved_file.stat().st_size == result['bytes']
    assert not any(source.iterdir())


def test_snapped_window_frame_uses_zero_root_margins(monkeypatch) -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from PySide6.QtWidgets import QApplication

    from somevar_ui_playground.registration import create_app_registration
    from somevar_ui.ui.platform import windows as win_platform

    app = QApplication.instance() or QApplication([])
    registration = create_app_registration()
    window = registration.create_window()

    try:
        monkeypatch.setattr(
            win_platform,
            'resolve_window_shell_state',
            lambda widget: win_platform.WindowShellState.SNAPPED,
        )
        window._update_window_frame()

        margins = window._root_layout.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (0, 0, 0, 0)
        assert window._window_frame_controller.state is win_platform.WindowShellState.SNAPPED
        assert window.centralWidget().property('shellState') == 'snapped'
        assert window.centralWidget().property('maximized') is False
    finally:
        window.close()
        window.deleteLater()


def test_maximized_window_frame_keeps_native_root_inset(monkeypatch) -> None:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    from PySide6.QtWidgets import QApplication

    from somevar_ui_playground.registration import create_app_registration
    from somevar_ui.ui.platform import windows as win_platform

    app = QApplication.instance() or QApplication([])
    registration = create_app_registration()
    window = registration.create_window()

    try:
        monkeypatch.setattr(
            win_platform,
            'resolve_window_shell_state',
            lambda widget: win_platform.WindowShellState.MAXIMIZED,
        )
        monkeypatch.setattr(win_platform, 'native_frame_margin', lambda default=8: 8)
        window._update_window_frame()

        margins = window._root_layout.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (8, 8, 8, 8)
        assert window._window_frame_controller.state is win_platform.WindowShellState.MAXIMIZED
        assert window.centralWidget().property('shellState') == 'maximized'
        assert window.centralWidget().property('attached') is True
    finally:
        window.close()
        window.deleteLater()
