from __future__ import annotations

import os

from somevar_ui.app import run


def main() -> int:
    os.environ.setdefault('SOMEVAR_UI_APP_ID', 'playground')
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
