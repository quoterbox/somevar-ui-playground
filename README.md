# SomeVar UI Playground

<p align="center">
  <a href="https://github.com/quoterbox/somevar-ui-playground/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/quoterbox/somevar-ui-playground/actions/workflows/ci.yml/badge.svg?branch=master">
  </a>
  <a href="LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-2f81f7.svg">
  </a>
  <a href="https://github.com/quoterbox/somevar-ui">
    <img alt="Framework: SomeVar UI Kit" src="https://img.shields.io/badge/framework-SomeVar%20UI%20Kit-2f81f7.svg">
  </a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB.svg">
</p>

SomeVar UI Playground is a demo and QA application for SomeVar UI Kit. It shows the framework controls, charts, modal flows, drag-and-drop lists, shell chrome, and rich-content widgets in one runnable desktop app.

The playground is intentionally separate from the framework package. It depends on [`somevar-ui`](https://github.com/quoterbox/somevar-ui) and registers a `playground` application through the `somevar_ui.apps` entry-point group.

## Preview

<p align="center">
  <img src="docs/assets/screenshots/charts-lines.png" alt="Animated SomeVar UI Kit chart examples" width="900">
</p>

<p align="center">
  <img src="docs/assets/screenshots/drag-and-drop-cards.png" alt="SomeVar UI Kit drag and drop card demos" width="900">
</p>

## Screenshots

| Charts and dashboards | Tables and cards |
| --- | --- |
| <img src="docs/assets/screenshots/charts-dashboard.png" alt="Dashboard widgets and donut charts" width="420"> | <img src="docs/assets/screenshots/tables.png" alt="Tables and list demos" width="420"> |

| Inputs and icons | Modals and windows |
| --- | --- |
| <img src="docs/assets/screenshots/inputs.png" alt="Inputs and controls" width="420"> | <img src="docs/assets/screenshots/simple-modal.png" alt="Modal window demo" width="420"> |
| <img src="docs/assets/screenshots/icons.png" alt="Icon catalog" width="420"> | <img src="docs/assets/screenshots/standalone-window.png" alt="Standalone window demo" width="420"> |

| Rich content | Progress states |
| --- | --- |
| <img src="docs/assets/screenshots/markdown-render.png" alt="Markdown rendering demo" width="420"> | <img src="docs/assets/screenshots/progress-bars.png" alt="Progress bar demos" width="420"> |
| <img src="docs/assets/screenshots/syntax-highlighting.png" alt="Syntax highlighting demo" width="420"> | <img src="docs/assets/screenshots/drag-and-drop-cards.png" alt="Drag and drop card layout" width="420"> |

## Run

```shell
uv sync --extra dev
uv run somevar-ui run
```

The app is configured through `somevar-ui.toml`:

```toml
[app]
id = "playground"
title = "SomeVar UI Playground"
entry = "somevar_ui_playground.main:main"
```

## Development

```shell
uv run python -m pytest
uv run somevar-ui doctor
uv run somevar-ui build --mode onedir
```

Use the playground as a visual regression surface for framework changes. Reusable code belongs in `somevar-ui`; playground-specific pages and demo data belong in this package.

## License

SomeVar UI Playground is released under the [MIT License](LICENSE).

## Author

Created by [JQ / quoterbox](https://github.com/quoterbox).
