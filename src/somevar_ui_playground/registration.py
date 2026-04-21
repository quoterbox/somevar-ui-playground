from __future__ import annotations

from pathlib import Path

from somevar_ui.apps.registry import AppRegistration


def _create_window():
    from somevar_ui_playground import create_playground_window

    return create_playground_window()


def _data_dir() -> Path:
    from somevar_ui_playground.storage import default_data_dir

    return default_data_dir()


def create_app_registration() -> AppRegistration:
    return AppRegistration(
        app_id='playground',
        title='SomeVar UI Playground',
        create_window=_create_window,
        data_dir_provider=_data_dir,
        package_name='somevar_ui_playground',
    )
