from pathlib import Path

from somevar_ui_playground.registration import create_app_registration


def test_playground_registration_factory() -> None:
    registration = create_app_registration()

    assert registration.app_id == 'playground'
    assert registration.title == 'SomeVar UI Playground'
    assert registration.package_name == 'somevar_ui_playground'
    assert isinstance(registration.data_dir_provider(), Path)
