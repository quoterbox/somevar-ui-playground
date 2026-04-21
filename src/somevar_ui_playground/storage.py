from __future__ import annotations

import os
from pathlib import Path


def default_data_dir() -> Path:
    app_data = os.getenv('APPDATA')
    if app_data:
        return Path(app_data) / 'SomeVar' / 'UI Playground'
    return Path.home() / '.somevar-ui-playground'
