from __future__ import annotations

import html
import re
import textwrap
from dataclasses import dataclass, field
from typing import Final

from PySide6.QtCore import QPointF, QRectF, QLocale, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from somevar_ui.ui.base import BaseWidget, hbox, vbox
from somevar_ui.ui.kit.widgets import CheckBox, CodeBlock
from somevar_ui.ui.theme import THEME, get_theme_mode

C = THEME.colors
M = THEME.metrics
S = THEME.spacing

try:
    import markdown as _markdown_module
except ImportError:
    _markdown_module = None

try:
    import pygments as _pygments_module  # noqa: F401
except ImportError:
    _pygments_module = None

_BASE_MARKDOWN_EXTENSIONS: Final[list[str]] = [
    'fenced_code',
    'tables',
    'sane_lists',
    'md_in_html',
    'admonition',
]
_CODE_HILITE_EXTENSION: Final[str] = 'codehilite'
_MARKDOWN_EXTENSION_CONFIGS: Final[dict[str, dict[str, object]]] = {
    _CODE_HILITE_EXTENSION: {
        'guess_lang': False,
        'linenums': False,
        'css_class': 'codehilite',
        'noclasses': False,
    }
}

_KEYWORDS: Final[dict[str, tuple[str, ...]]] = {
    'python': (
        'def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'in', 'import', 'from', 'as',
        'try', 'except', 'finally', 'with', 'lambda', 'yield', 'pass', 'break', 'continue', 'True', 'False', 'None',
    ),
    'javascript': (
        'const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 'switch', 'case',
        'break', 'continue', 'new', 'class', 'extends', 'import', 'from', 'export', 'async', 'await', 'true', 'false', 'null',
    ),
    'typescript': (
        'type', 'interface', 'const', 'let', 'function', 'return', 'if', 'else', 'for', 'while', 'class',
        'extends', 'implements', 'import', 'from', 'export', 'async', 'await', 'true', 'false', 'null',
    ),
    'cpp': (
        'int', 'float', 'double', 'char', 'bool', 'void', 'class', 'struct', 'namespace', 'return', 'if',
        'else', 'for', 'while', 'include', 'using', 'public', 'private', 'protected', 'const', 'auto', 'new', 'delete',
    ),
    'bash': (
        'if', 'then', 'else', 'fi', 'for', 'in', 'do', 'done', 'case', 'esac', 'function',
        'export', 'local', 'echo', 'cd', 'pwd', 'grep', 'awk', 'sed', 'python', 'pip',
    ),
    'sql': (
        'select', 'from', 'where', 'group', 'by', 'order', 'insert', 'into', 'update', 'delete',
        'join', 'left', 'right', 'inner', 'outer', 'as', 'and', 'or', 'not', 'null', 'avg', 'count',
    ),
    'json': (),
}

_STRING_PATTERN: Final[re.Pattern[str]] = re.compile(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')', re.MULTILINE)
_NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(r'\b\d+(?:\.\d+)?\b')


def _markdown_extensions() -> list[str]:
    extensions = list(_BASE_MARKDOWN_EXTENSIONS)
    if _pygments_module is not None:
        extensions.append(_CODE_HILITE_EXTENSION)
    return extensions


def country_names() -> list[str]:
    names: set[str] = set()

    language_any = getattr(QLocale.Language, 'AnyLanguage', None)
    script_any = getattr(QLocale.Script, 'AnyScript', None)
    territory_enum = getattr(QLocale, 'Territory', None)
    territory_any = getattr(territory_enum, 'AnyTerritory', None)

    if language_any is not None and script_any is not None and territory_any is not None:
        locales = QLocale.matchingLocales(language_any, script_any, territory_any)
        for locale in locales:
            territory_getter = getattr(locale, 'territory', None)
            territory_to_string = getattr(locale, 'territoryToString', None)
            if callable(territory_getter) and callable(territory_to_string):
                territory = territory_getter()
                name = territory_to_string(territory)
                normalized = name.strip() if name else ''
                if normalized and normalized.lower() not in {'any territory', 'anyterritory', 'lastterritory'}:
                    names.add(normalized)
        if names:
            return sorted(names, key=str.casefold)

    for country in QLocale.Country:
        name = QLocale.countryToString(country)
        if not name:
            continue
        normalized = name.strip()
        if not normalized or normalized.lower() in {'any country', 'anycountry', 'lastcountry'}:
            continue
        names.add(normalized)
    return sorted(names, key=str.casefold)


def apply_markdown_style(browser: QTextBrowser) -> None:
    browser.setOpenExternalLinks(False)
    browser.setStyleSheet(
        f"QTextBrowser {{ background: {C.field_background}; border: 1px solid {C.dropdown_surface_border}; border-radius: {max(4, M.card_radius)}px; padding: 10px; }}"
    )
    browser.document().setDefaultStyleSheet(
        f"""
        * {{
            font-family: 'Segoe UI', 'Noto Sans', sans-serif;
        }}

        body {{
            color: {C.text_primary};
            font-size: 10.25pt;
            line-height: 1.58;
            margin: 0;
            padding: 0;
            background: transparent;
        }}

        h1, h2, h3, h4, h5 {{
            color: {C.text_hero};
            font-weight: 650;
            margin: 18px 0 10px;
            line-height: 1.24;
        }}

        h1 {{
            font-size: 1.9em;
            margin-top: 0;
            padding-bottom: 8px;
            border-bottom: 1px solid {C.dropdown_surface_border};
        }}

        h2 {{
            font-size: 1.5em;
            padding-bottom: 6px;
            border-bottom: 1px solid {C.dropdown_surface_border};
        }}

        h3 {{ font-size: 1.28em; }}
        h4 {{ font-size: 1.08em; }}
        h5 {{ font-size: 0.96em; color: {C.text_subsection}; }}

        p {{ margin: 0 0 10px 0; }}

        ul, ol {{
            margin: 0 0 10px 0;
            padding: 0 0 0 18px;
            list-style-position: outside;
            -qt-list-indent: 1;
        }}

        ul ul, ul ol, ol ul, ol ol {{
            margin: 2px 0 2px 0;
            padding-left: 14px;
        }}

        li {{ margin: 0 0 2px 0; padding: 0; }}
        li p {{ margin: 0; }}
        li.task-item {{ list-style: none; margin-left: -14px; }}

        hr {{
            border: 0;
            border-top: 1px solid {C.dropdown_surface_border};
            margin: 14px 0;
        }}

        blockquote {{
            margin: 0 0 12px 0;
            padding: 0;
            border: none;
            color: {C.text_primary};
            background: transparent;
        }}

        blockquote p {{ margin: 0 0 8px 0; }}
        blockquote p + p {{ margin-top: 6px; }}

        table {{
            border-collapse: collapse;
            border-spacing: 0;
            margin: 0 0 12px 0;
            width: 100%;
            background: {C.field_background};
            border: 1px solid {C.field_border};
        }}

        th, td {{
            border: 1px solid {C.field_border};
            padding: 7px 10px;
            text-align: left;
            vertical-align: top;
        }}

        th {{
            background: {C.section_background};
            color: {C.text_hero};
            font-weight: 650;
        }}

        tbody tr:nth-child(2n) {{
            background: {C.section_background};
        }}

        a {{ color: {C.button_accent_base}; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        code {{
            color: {C.text_hero};
            font-family: Consolas, 'Courier New', monospace;
            font-size: 0.92em;
            background: {C.section_background};
            border: 1px solid {C.dropdown_surface_border};
            border-radius: 4px;
            padding: 2px 5px;
        }}

        pre {{ margin: 0; padding: 0; border: none; background: transparent; }}

        .codehilite, .highlight {{
            margin: 0 0 12px 0;
            border: 1px solid {C.dropdown_surface_border};
            border-radius: 8px;
            background: {C.field_background};
            overflow: hidden;
        }}

        .codehilite pre, .highlight pre {{
            margin: 0;
            padding: 12px 14px;
            border: none;
            border-radius: 0;
            background: transparent;
            line-height: 1.45;
            white-space: pre;
            overflow-x: auto;
        }}

        .codehilite code, .highlight code {{
            border: none;
            border-radius: 0;
            background: transparent;
            padding: 0;
            color: {C.text_hero};
        }}

        .tok-keyword {{ color: #c792ea; font-weight: 600; }}
        .tok-string {{ color: #ecc48d; }}
        .tok-number {{ color: #f78c6c; }}
        .tok-comment {{ color: #7f8fa3; font-style: italic; }}
        .tok-func {{ color: #82aaff; }}
        .tok-type {{ color: #4fc1ff; }}

        .codehilite .k,
        .codehilite .kd,
        .codehilite .kn,
        .codehilite .kr,
        .codehilite .kt,
        .highlight .k,
        .highlight .kd,
        .highlight .kn,
        .highlight .kr,
        .highlight .kt {{ color: #c792ea; font-weight: 600; }}

        .codehilite .s,
        .codehilite .sa,
        .codehilite .sb,
        .codehilite .sc,
        .codehilite .sd,
        .codehilite .s1,
        .codehilite .s2,
        .codehilite .se,
        .codehilite .sh,
        .codehilite .si,
        .codehilite .sx,
        .highlight .s,
        .highlight .sa,
        .highlight .sb,
        .highlight .sc,
        .highlight .sd,
        .highlight .s1,
        .highlight .s2,
        .highlight .se,
        .highlight .sh,
        .highlight .si,
        .highlight .sx {{ color: #ecc48d; }}

        .codehilite .m,
        .codehilite .mb,
        .codehilite .mf,
        .codehilite .mh,
        .codehilite .mi,
        .codehilite .mo,
        .highlight .m,
        .highlight .mb,
        .highlight .mf,
        .highlight .mh,
        .highlight .mi,
        .highlight .mo {{ color: #f78c6c; }}

        .codehilite .c,
        .codehilite .c1,
        .codehilite .cm,
        .codehilite .cp,
        .codehilite .cs,
        .highlight .c,
        .highlight .c1,
        .highlight .cm,
        .highlight .cp,
        .highlight .cs {{ color: #7f8fa3; font-style: italic; }}

        .codehilite .nf,
        .codehilite .fm,
        .highlight .nf,
        .highlight .fm {{ color: #82aaff; }}

        .codehilite .nc,
        .codehilite .nn,
        .codehilite .nt,
        .highlight .nc,
        .highlight .nn,
        .highlight .nt {{ color: #4fc1ff; }}

        .codehilite .o,
        .codehilite .ow,
        .highlight .o,
        .highlight .ow {{ color: #89ddff; }}

        .codehilite .p,
        .highlight .p {{ color: {C.text_primary}; }}

        .codehilite .nb,
        .codehilite .bp,
        .highlight .nb,
        .highlight .bp {{ color: #82aaff; }}
        """
    )


@dataclass(slots=True)
class _MarkdownListItem:
    text: str
    checked: bool | None = None
    children: list['_MarkdownListItem'] = field(default_factory=list)


@dataclass(slots=True)
class _MarkdownQuoteItem:
    text: str
    children: list['_MarkdownQuoteItem'] = field(default_factory=list)


class DataTableWidget(QFrame):
    def __init__(
        self,
        headers: list[str],
        rows: list[list[str]],
        *,
        column_stretches: list[int] | None = None,
        hover_rows: bool = False,
        hover_columns: bool = False,
        row_height: int = 40,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._headers = list(headers)
        self._rows = [list(row) for row in rows]
        self._column_stretches = list(column_stretches or ([1] * len(headers)))
        self._hover_rows = hover_rows
        self._hover_columns = hover_columns
        self._row_height = row_height
        self._hovered_row: int | None = None
        self._hovered_col: int | None = None
        self._color_overrides: dict[str, str] = {}

        self.setObjectName('DataTableShell')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(hover_rows or hover_columns)
        self._build()

    def refresh_theme(self) -> None:
        self.update()

    def set_color_override(self, key: str, value: str | QColor | None) -> None:
        if value is None:
            self._color_overrides.pop(key, None)
        else:
            self._color_overrides[key] = QColor(value).name()
        self.update()

    def set_color_overrides(self, overrides: dict[str, str | QColor]) -> None:
        self._color_overrides = {key: QColor(value).name() for key, value in overrides.items()}
        self.update()

    def clear_color_overrides(self) -> None:
        self._color_overrides.clear()
        self.update()

    def _build(self) -> None:
        total_rows = len(self._rows) + (1 if self._headers else 0)
        self.setFixedHeight(total_rows * self._row_height)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if not self._hover_rows and not self._hover_columns:
            super().mouseMoveEvent(event)
            return
        point = event.position().toPoint()
        hovered_row = self._row_index_at(point.y()) if self._hover_rows else None
        hovered_col = self._column_index_at(point.x()) if self._hover_columns else None
        if hovered_row != self._hovered_row or hovered_col != self._hovered_col:
            self._hovered_row = hovered_row
            self._hovered_col = hovered_col
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        if self._hovered_row is not None or self._hovered_col is not None:
            self._hovered_row = None
            self._hovered_col = None
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        if not self._headers and not self._rows:
            return

        radius = float(max(4, M.card_radius))
        outer_rect = self.rect().adjusted(0, 0, -1, -1)
        outer = QRectF(outer_rect)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        clip_path = QPainterPath()
        clip_path.addRoundedRect(outer, radius, radius)

        painter.fillPath(clip_path, QColor(C.scrollable_surface_background))
        painter.save()
        painter.setClipPath(clip_path)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        widths = self._column_widths(float(outer_rect.width() + 1))
        x_positions = [outer_rect.left()]
        current_x = outer_rect.left()
        for width in widths:
            current_x += int(round(width))
            x_positions.append(current_x)
        x_positions[-1] = outer_rect.right() + 1

        header_height = self._row_height if self._headers else 0

        if self._headers:
            for col_index in range(len(self._headers)):
                left = x_positions[col_index]
                width = x_positions[col_index + 1] - left
                painter.fillRect(
                    left,
                    outer_rect.top(),
                    width,
                    header_height,
                    self._header_fill(col_index),
                )

        for row_index, row_values in enumerate(self._rows):
            visual_row = row_index + (1 if self._headers else 0)
            top = outer_rect.top() + visual_row * self._row_height
            for col_index in range(len(self._headers)):
                left = x_positions[col_index]
                width = x_positions[col_index + 1] - left
                fill = self._cell_fill(row_index, col_index)
                painter.fillRect(left, top, width, self._row_height, fill)

        if self._headers and self._rows:
            y = outer_rect.top() + header_height
            for col_index in range(len(self._headers)):
                left = x_positions[col_index]
                width = x_positions[col_index + 1] - left
                divider = self._divider_color(
                    self._header_fill(col_index),
                    self._cell_fill(0, col_index),
                )
                painter.setPen(QPen(divider, 1))
                painter.drawLine(left, y, left + width, y)

        for row_index in range(len(self._rows) - 1):
            y = outer_rect.top() + header_height + (row_index + 1) * self._row_height
            for col_index in range(len(self._headers)):
                left = x_positions[col_index]
                width = x_positions[col_index + 1] - left
                divider = self._divider_color(
                    self._cell_fill(row_index, col_index),
                    self._cell_fill(row_index + 1, col_index),
                )
                painter.setPen(QPen(divider, 1))
                painter.drawLine(left, y, left + width, y)

        for boundary in range(1, len(x_positions) - 1):
            x = x_positions[boundary]
            if self._headers:
                header_divider = self._divider_color(
                    self._header_fill(boundary - 1),
                    self._header_fill(boundary),
                )
                painter.setPen(QPen(header_divider, 1))
                painter.drawLine(x, outer_rect.top(), x, outer_rect.top() + header_height)
            for row_index in range(len(self._rows)):
                visual_row = row_index + (1 if self._headers else 0)
                top = outer_rect.top() + visual_row * self._row_height
                divider = self._divider_color(
                    self._cell_fill(row_index, boundary - 1),
                    self._cell_fill(row_index, boundary),
                )
                painter.setPen(QPen(divider, 1))
                painter.drawLine(x, top, x, top + self._row_height)

        header_font = QFont('Segoe UI', 9)
        header_font.setWeight(QFont.Weight.DemiBold)
        body_font = QFont('Segoe UI', 10)
        header_metrics = QFontMetrics(header_font)
        body_metrics = QFontMetrics(body_font)
        horizontal_padding = 12.0

        if self._headers:
            painter.setFont(header_font)
            painter.setPen(self._color('header_text', C.text_subsection))
            self._draw_row_text(
                painter,
                self._headers,
                widths,
                x_positions,
                float(outer_rect.top()),
                header_metrics,
                horizontal_padding,
            )

        painter.setFont(body_font)
        for row_index, row_values in enumerate(self._rows):
            painter.setPen(self._color('row_hover_text', C.text_section) if row_index == self._hovered_row else self._color('body_text', C.text_primary))
            top = float(outer_rect.top() + (row_index + (1 if self._headers else 0)) * self._row_height)
            self._draw_row_text(
                painter,
                row_values,
                widths,
                x_positions,
                top,
                body_metrics,
                horizontal_padding,
            )

        painter.restore()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self._color('grid', C.scrollable_surface_border), 1))
        painter.drawPath(clip_path)

    def _row_index_at(self, y: int) -> int | None:
        body_start = self._row_height if self._headers else 0
        if y < body_start:
            return None
        row = (y - body_start) // self._row_height
        if 0 <= row < len(self._rows):
            return int(row)
        return None

    def _column_widths(self, total_width: float) -> list[float]:
        if not self._headers:
            return []
        stretches = self._column_stretches[:len(self._headers)]
        if len(stretches) < len(self._headers):
            stretches += [1] * (len(self._headers) - len(stretches))
        total = sum(stretches) or len(self._headers)
        widths: list[float] = []
        used = 0.0
        for index, stretch in enumerate(stretches):
            if index == len(stretches) - 1:
                width = total_width - used
            else:
                width = float(int(total_width * stretch / total))
                used += width
            widths.append(width)
        return widths

    def _column_index_at(self, x: int) -> int | None:
        widths = self._column_widths(float(self.rect().width()))
        current_x = 0
        for index, width in enumerate(widths):
            current_x += int(round(width))
            if x < current_x:
                return index
        return len(widths) - 1 if widths else None

    def _row_base_fill(self, row_index: int) -> QColor:
        if row_index % 2 == 1:
            return self._color('row_odd', C.project_item_hover)
        return self._color('row_even', C.scrollable_surface_background)

    def _row_fill(self, row_index: int) -> QColor:
        base = self._row_base_fill(row_index)
        if self._hover_rows and row_index == self._hovered_row:
            return self._mix_colors(base, self._color('row_hover', C.project_item_selected), 0.74)
        return base

    def _cell_fill(self, row_index: int, col_index: int) -> QColor:
        base = self._row_fill(row_index)
        row_hovered = self._hover_rows and row_index == self._hovered_row
        col_hovered = self._hover_columns and col_index == self._hovered_col

        if row_hovered and col_hovered:
            return self._mix_colors(base, self._color('cross_hover', C.project_item_selected), 0.82)
        if col_hovered:
            return self._mix_colors(base, self._color('column_hover', C.badge_background), 0.42)
        return base

    def _header_fill(self, col_index: int) -> QColor:
        base = self._color('header_bg', C.route_card_selected)
        if self._hover_columns and col_index == self._hovered_col:
            return self._mix_colors(base, self._color('cross_hover', C.project_item_selected), 0.56)
        return base

    def _divider_color(self, left_fill: QColor, right_fill: QColor) -> QColor:
        average_fill = QColor(
            round((left_fill.red() + right_fill.red()) / 2),
            round((left_fill.green() + right_fill.green()) / 2),
            round((left_fill.blue() + right_fill.blue()) / 2),
        )
        return self._mix_colors(self._color('grid', C.scrollable_surface_border), average_fill, 0.52)

    def _color(self, key: str, fallback: str) -> QColor:
        default_palette = table_palette_for_theme()
        value = self._color_overrides.get(key, default_palette.get(key, fallback))
        return QColor(value)

    @staticmethod
    def _mix_colors(base: QColor, overlay: QColor, amount: float) -> QColor:
        ratio = max(0.0, min(1.0, amount))
        return QColor(
            round(base.red() + (overlay.red() - base.red()) * ratio),
            round(base.green() + (overlay.green() - base.green()) * ratio),
            round(base.blue() + (overlay.blue() - base.blue()) * ratio),
        )

    def _draw_row_text(
        self,
        painter: QPainter,
        values: list[str],
        widths: list[float],
        x_positions: list[float],
        top: float,
        metrics: QFontMetrics,
        horizontal_padding: float,
    ) -> None:
        baseline_offset = (self._row_height - metrics.height()) / 2
        for index, value in enumerate(values):
            left = x_positions[index]
            width = widths[index]
            text_rect = QRectF(left + horizontal_padding, top + baseline_offset, max(1.0, width - horizontal_padding * 2), metrics.height())
            elided = metrics.elidedText(value, Qt.TextElideMode.ElideRight, int(text_rect.width()))
            painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), elided)


def _inline_rich_text(text: str) -> str:
    value = html.escape(text)
    value = re.sub(
        r'`([^`]+)`',
        lambda m: (
            f'<span style="font-family:Consolas, \'Courier New\', monospace; '
            f'background:{C.section_background}; '
            f'border:1px solid {C.dropdown_surface_border}; '
            f'border-radius:4px; padding:1px 4px; color:{C.text_hero};">'
            f'{html.escape(m.group(1))}</span>'
        ),
        value,
    )
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:' + C.button_accent_base + r'; text-decoration:none;">\1</a>', value)
    value = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<strong><em>\1</em></strong>', value)
    value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    value = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', value)
    value = re.sub(r'~~([^~]+)~~', r'<span style="text-decoration: line-through;">\1</span>', value)
    return value


def _parse_unordered_items(block_lines: list[str]) -> list[_MarkdownListItem]:
    items: list[_MarkdownListItem] = []
    stack: list[tuple[int, list[_MarkdownListItem]]] = [(-1, items)]

    for raw in block_lines:
        parsed = _parse_unordered_line(raw)
        if parsed is None:
            continue
        indent, content = parsed
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        task_match = re.match(r'^\[( |x|X)\]\s+(.*)$', content)
        if task_match:
            node = _MarkdownListItem(
                text=task_match.group(2),
                checked=task_match.group(1).lower() == 'x',
            )
        else:
            node = _MarkdownListItem(text=content)

        stack[-1][1].append(node)
        stack.append((indent, node.children))

    return items


def _parse_quote_line(text: str) -> tuple[int, str] | None:
    stripped = text.lstrip()
    if not stripped.startswith('>'):
        return None

    level = 0
    index = 0
    while index < len(stripped) and stripped[index] == '>':
        level += 1
        index += 1
        while index < len(stripped) and stripped[index] == ' ':
            index += 1

    content = stripped[index:].strip()
    return level, content


def _parse_quote_items(block_lines: list[str]) -> list[_MarkdownQuoteItem]:
    items: list[_MarkdownQuoteItem] = []
    stack: list[tuple[int, list[_MarkdownQuoteItem]]] = [(0, items)]

    for raw in block_lines:
        parsed = _parse_quote_line(raw)
        if parsed is None:
            continue
        level, content = parsed
        while len(stack) > 1 and level <= stack[-1][0]:
            stack.pop()

        node = _MarkdownQuoteItem(text=content)
        stack[-1][1].append(node)
        stack.append((level, node.children))

    return items


class MarkdownShowcaseWidget(BaseWidget):
    def __init__(self, markdown_text: str = '', parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.lg)
        self.setObjectName('ScrollableSurface')
        self.root_layout.setContentsMargins(S.lg, S.lg, S.lg, S.lg)
        self._markdown_text = ''
        if markdown_text:
            self.set_markdown(markdown_text)

    def set_markdown(self, markdown_text: str) -> None:
        self._markdown_text = textwrap.dedent(markdown_text).strip('\n')
        self._clear_layout()
        self._build_from_markdown(self._markdown_text)

    def refresh_theme(self) -> None:
        if self._markdown_text:
            self.set_markdown(self._markdown_text)

    def _clear_layout(self) -> None:
        while self.root_layout.count():
            item = self.root_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_child_layout(child_layout)

    def _clear_child_layout(self, layout: QVBoxLayout | QHBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            nested = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif nested is not None:
                self._clear_child_layout(nested)  # type: ignore[arg-type]

    def _build_from_markdown(self, markdown_text: str) -> None:
        lines = markdown_text.splitlines()
        i = 0

        while i < len(lines):
            raw = lines[i].rstrip('\n')
            stripped = raw.strip()

            if not stripped:
                i += 1
                continue

            if stripped.startswith('```'):
                language = stripped[3:].strip().lower() or 'text'
                code_lines: list[str] = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i].rstrip('\n'))
                    i += 1
                if i < len(lines):
                    i += 1
                self.root_layout.addWidget(
                    CodeBlock(
                        '\n'.join(code_lines),
                        language=language,
                        title=f'{language.title()} code',
                        parent=self,
                    )
                )
                continue

            if stripped.startswith('#'):
                level = min(5, len(stripped) - len(stripped.lstrip('#')))
                content = stripped[level:].strip()
                self.root_layout.addWidget(self._heading_label(content, level))
                i += 1
                continue

            if stripped in {'---', '***', '___'}:
                self.root_layout.addWidget(self._separator())
                i += 1
                continue

            if stripped.startswith('>'):
                quote_lines: list[str] = []
                while i < len(lines) and lines[i].strip().startswith('>'):
                    quote_lines.append(lines[i].rstrip('\n'))
                    i += 1
                self.root_layout.addWidget(self._quote_group_widget(_parse_quote_items(quote_lines)))
                continue

            if stripped.startswith('|') and i + 1 < len(lines) and self._is_table_separator(lines[i + 1]):
                header_cells = [cell.strip() for cell in stripped.strip('|').split('|')]
                i += 2
                rows: list[list[str]] = []
                while i < len(lines):
                    row_line = lines[i].strip()
                    if not row_line.startswith('|'):
                        break
                    rows.append([cell.strip() for cell in row_line.strip('|').split('|')])
                    i += 1
                self.root_layout.addWidget(self._table_widget(header_cells, rows))
                continue

            if _parse_unordered_line(raw) is not None:
                list_lines: list[str] = []
                while i < len(lines) and _parse_unordered_line(lines[i]) is not None:
                    list_lines.append(lines[i].rstrip('\n'))
                    i += 1
                self.root_layout.addWidget(self._unordered_list_widget(_parse_unordered_items(list_lines)))
                continue

            if re.match(r'^\d+\.\s+', stripped):
                ordered: list[str] = []
                while i < len(lines):
                    probe = lines[i].strip()
                    if not re.match(r'^\d+\.\s+', probe):
                        break
                    ordered.append(re.sub(r'^\d+\.\s+', '', probe))
                    i += 1
                self.root_layout.addWidget(self._ordered_list_widget(ordered))
                continue

            para_lines: list[str] = [stripped]
            i += 1
            while i < len(lines):
                probe = lines[i].strip()
                if not probe:
                    break
                if (
                    probe.startswith('```')
                    or probe.startswith('#')
                    or probe in {'---', '***', '___'}
                    or probe.startswith('>')
                    or probe.startswith('|')
                    or _parse_unordered_line(lines[i]) is not None
                    or re.match(r'^\d+\.\s+', probe)
                ):
                    break
                para_lines.append(probe)
                i += 1
            self.root_layout.addWidget(self._paragraph_label(' '.join(para_lines)))

        self.root_layout.addStretch(1)

    @staticmethod
    def _is_table_separator(value: str) -> bool:
        v = value.strip()
        if '|' not in v:
            return False
        compact = v.replace('|', '').replace(':', '').replace('-', '').replace(' ', '')
        return compact == '' and '-' in v

    def _heading_label(self, text: str, level: int) -> QWidget:
        wrapper = QWidget(self)
        layout = vbox(wrapper, spacing=0)

        sizes = {1: 31, 2: 24, 3: 20, 4: 17, 5: 14}
        top_margins = {1: 4, 2: 10, 3: 8, 4: 6, 5: 4}
        color = C.text_hero if level <= 3 else C.text_subsection

        layout.setContentsMargins(0, top_margins[level], 0, 0)

        label = QLabel(text, wrapper)
        label.setWordWrap(True)
        label.setIndent(0)
        label.setMargin(0)
        label.setContentsMargins(0, 0, 0, 0)

        label.setStyleSheet(
            f'color: {color}; font-weight: 700; font-size: {sizes[level]}px; margin: 0; padding: 0;'
        )

        layout.addWidget(label)
        return wrapper

    def _paragraph_label(self, text: str) -> QLabel:
        label = QLabel(self)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setText(_inline_rich_text(text))
        label.setStyleSheet(f"color: {C.text_primary}; font-size: 14px; line-height: 1.55;")
        return label

    def _separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background: {C.dropdown_surface_border}; min-height: 1px; max-height: 1px; border: none;")
        return line

    def _unordered_list_widget(self, items: list[_MarkdownListItem]) -> QWidget:
        wrapper = QWidget(self)
        layout = vbox(wrapper, spacing=6)
        self._append_unordered_items(layout, items, 0)
        return wrapper

    def _append_unordered_items(self, layout: QVBoxLayout, items: list[_MarkdownListItem], depth: int) -> None:
        for item in items:
            layout.addWidget(self._list_row(item.text, depth, checked=item.checked))
            if item.children:
                self._append_unordered_items(layout, item.children, depth + 1)

    def _ordered_list_widget(self, items: list[str]) -> QWidget:
        wrapper = QWidget(self)
        layout = vbox(wrapper, spacing=6)
        for index, text in enumerate(items, start=1):
            layout.addWidget(self._list_row(text, 0, prefix=f'{index}.'))
        return wrapper

    def _list_row(self, text: str, depth: int, *, prefix: str | None = None, checked: bool | None = None) -> QWidget:
        row = QWidget(self)
        row_layout = hbox(row, spacing=10)
        row_layout.setContentsMargins(depth * 18, 0, 0, 0)

        if checked is not None:
            marker = CheckBox(text, row)
            marker.setChecked(checked)
            marker.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            marker.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            row_layout.addSpacing(2)
            row_layout.addWidget(marker, 1)
            return row

        marker = QLabel(row)
        marker.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        marker.setFixedWidth(22)
        marker.setStyleSheet(f"color: {C.text_subsection}; font-size: 14px;")
        marker.setText(prefix or '•')

        content = QLabel(row)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setWordWrap(True)
        content.setText(_inline_rich_text(text))
        content.setStyleSheet(f"color: {C.text_primary}; font-size: 14px; line-height: 1.45;")

        row_layout.addWidget(marker, 0, Qt.AlignmentFlag.AlignTop)
        row_layout.addWidget(content, 1)
        return row

    def _quote_group_widget(self, items: list[_MarkdownQuoteItem]) -> QWidget:
        wrapper = QWidget(self)
        layout = vbox(wrapper, spacing=10)
        for item in items:
            layout.addWidget(self._quote_widget(item, 0))
        return wrapper

    def _quote_widget(self, item: _MarkdownQuoteItem, depth: int) -> QWidget:
        accent_color = C.button_accent_base if depth == 0 else C.route_card_border_selected
        content_background = C.scrollable_surface_background if depth == 0 else C.field_background_hover
        radius = max(4, M.card_radius - min(depth, 2))

        shell = QFrame(self)
        shell.setObjectName('MarkdownQuoteShell')
        shell.setStyleSheet(
            f"""
            QFrame#MarkdownQuoteShell {{
                background: {content_background};
                border: none;
                border-radius: {radius}px;
            }}
            QFrame#MarkdownQuoteAccent {{
                background: {accent_color};
                border: none;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 2px;
                border-bottom-right-radius: 2px;
            }}
            """
        )
        shell_layout = hbox(shell, spacing=0)
        shell_layout.setContentsMargins(0, 0, 0, 0)

        accent_host = QWidget(shell)
        accent_host.setFixedWidth(8)
        accent_host_layout = vbox(accent_host, spacing=0)
        accent_host_layout.setContentsMargins(0, 8, 0, 8)

        accent = QFrame(accent_host)
        accent.setObjectName('MarkdownQuoteAccent')
        accent.setFixedWidth(4)
        accent.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        accent_host_layout.addWidget(accent)

        content_body = QWidget(shell)
        content_layout = vbox(content_body, spacing=S.sm)
        content_layout.setContentsMargins(10, 12, 14, 12)

        text = QLabel(content_body)
        text.setWordWrap(True)
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setText(_inline_rich_text(item.text))
        text.setStyleSheet(f"color: {C.text_primary}; font-size: 14px; line-height: 1.5;")
        content_layout.addWidget(text)

        for child in item.children:
            child_container = QWidget(content_body)
            child_layout = hbox(child_container, spacing=0)
            child_layout.setContentsMargins(0, 8, 0, 0)
            child_layout.addWidget(self._quote_widget(child, depth + 1))
            content_layout.addWidget(child_container)

        shell_layout.addWidget(accent_host, 0)
        shell_layout.addWidget(content_body, 1)

        return shell

    def _table_widget(self, headers: list[str], rows: list[list[str]]) -> QWidget:
        stretches = [2, 2, 7] if len(headers) == 3 else [1] * len(headers)
        return DataTableWidget(
            headers,
            rows,
            column_stretches=stretches,
            hover_rows=False,
            row_height=40,
            parent=self,
        )


def table_palette_for_theme(mode: str | None = None) -> dict[str, str]:
    normalized = str(mode or get_theme_mode()).strip().lower()
    if normalized == 'light':
        return {
            'header_bg': '#DCE8F4',
            'header_text': '#23384A',
            'row_even': '#FCFDFF',
            'row_odd': '#E2ECF6',
            'row_hover': '#F0D2B8',
            'column_hover': '#F6E4D4',
            'cross_hover': '#E6A46F',
            'grid': '#BCD0E0',
            'body_text': '#1F3347',
            'row_hover_text': '#182A3A',
        }
    return {
        'header_bg': '#2B4359',
        'header_text': '#EEF5FB',
        'row_even': '#15212B',
        'row_odd': '#273A4A',
        'row_hover': '#A66A3B',
        'column_hover': '#744B34',
        'cross_hover': '#D28E56',
        'grid': '#355068',
        'body_text': '#E7F0F9',
        'row_hover_text': '#F9FBFE',
    }


def _inline_format(text: str) -> str:
    value = html.escape(text)
    value = value.replace('&lt;u&gt;', '<u>').replace('&lt;/u&gt;', '</u>')
    value = re.sub(r'`([^`]+)`', lambda m: f'<code>{html.escape(m.group(1))}</code>', value)
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', value)
    value = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<strong><em>\1</em></strong>', value)
    value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    value = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', value)
    value = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', value)
    return value


def _comment_patterns(lang: str) -> list[re.Pattern[str]]:
    if lang in {'python', 'bash'}:
        return [re.compile(r'#[^\n]*')]
    if lang in {'javascript', 'typescript', 'cpp'}:
        return [re.compile(r'//[^\n]*'), re.compile(r'/\*[\s\S]*?\*/')]
    if lang == 'sql':
        return [re.compile(r'--[^\n]*')]
    return []


def _highlight_code_fallback(code: str, language: str) -> str:
    text = code
    placeholders: dict[str, str] = {}
    token_counter = 0

    def stash(match: re.Match[str], css_class: str) -> str:
        nonlocal token_counter
        key = f'__TOK_{token_counter}__'
        token_counter += 1
        placeholders[key] = f'<span class="{css_class}">{html.escape(match.group(0))}</span>'
        return key

    for comment_pattern in _comment_patterns(language):
        text = comment_pattern.sub(lambda m: stash(m, 'tok-comment'), text)

    text = _STRING_PATTERN.sub(lambda m: stash(m, 'tok-string'), text)

    escaped = html.escape(text)

    escaped = _NUMBER_PATTERN.sub(r'<span class="tok-number">\g<0></span>', escaped)

    keywords = _KEYWORDS.get(language, ())
    if keywords:
        keyword_pattern = re.compile(r'\b(' + '|'.join(re.escape(item) for item in keywords) + r')\b', re.IGNORECASE if language == 'sql' else 0)
        escaped = keyword_pattern.sub(r'<span class="tok-keyword">\g<1></span>', escaped)

    for key, rendered in placeholders.items():
        escaped = escaped.replace(key, rendered)

    return escaped




def _leading_spaces_width(text: str) -> int:
    width = 0
    for ch in text:
        if ch == ' ':
            width += 1
        elif ch == '\t':
            width += 4
        else:
            break
    return width


def _parse_unordered_line(text: str) -> tuple[int, str] | None:
    match = re.match(r'^(\s*)[-*]\s+(.*)$', text)
    if match is None:
        return None
    indent = _leading_spaces_width(match.group(1))
    content = match.group(2).strip()
    return indent, content


def _render_unordered_list(block_lines: list[str]) -> str:
    items: list[dict[str, object]] = []
    stack: list[tuple[int, list[dict[str, object]]]] = [(-1, items)]

    for raw in block_lines:
        parsed = _parse_unordered_line(raw)
        if parsed is None:
            continue
        indent, content = parsed

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        node = {'text': content, 'children': []}
        stack[-1][1].append(node)
        stack.append((indent, node['children']))

    def render(nodes: list[dict[str, object]]) -> str:
        if not nodes:
            return ''
        parts = ['<ul>']
        for node in nodes:
            text = str(node['text'])
            task_match = re.match(r'^\[( |x|X)\]\s+(.*)$', text)
            if task_match:
                mark = '&#x2611;' if task_match.group(1).lower() == 'x' else '&#x2610;'
                parts.append(f'<li class="task-item">{mark} {_inline_format(task_match.group(2))}')
            else:
                parts.append(f'<li>{_inline_format(text)}')
            children = render(node['children'])
            if children:
                parts.append(children)
            parts.append('</li>')
        parts.append('</ul>')
        return ''.join(parts)

    return render(items)

def _render_markdown_fallback(markdown_text: str) -> str:
    lines = markdown_text.strip().splitlines()
    html_parts: list[str] = []
    i = 0

    def is_table_separator(value: str) -> bool:
        v = value.strip()
        if '|' not in v:
            return False
        compact = v.replace('|', '').replace(':', '').replace('-', '').replace(' ', '')
        return compact == '' and '-' in v

    while i < len(lines):
        line = lines[i].rstrip('\n')
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith('```'):
            language = stripped[3:].strip().lower()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i].rstrip('\n'))
                i += 1
            if i < len(lines):
                i += 1
            code_text = '\n'.join(code_lines)
            highlighted = _highlight_code_fallback(code_text, language)
            html_parts.append(f'<div class="codehilite"><pre><code>{highlighted}</code></pre></div>')
            continue

        if stripped.startswith('#'):
            level = min(6, len(stripped) - len(stripped.lstrip('#')))
            content = stripped[level:].strip()
            html_parts.append(f'<h{level}>{_inline_format(content)}</h{level}>')
            i += 1
            continue

        if stripped in {'---', '***', '___'}:
            html_parts.append('<hr/>')
            i += 1
            continue

        if stripped.startswith('>'):
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            html_parts.append('<blockquote>' + '<br/>'.join(_inline_format(item) for item in quote_lines) + '</blockquote>')
            continue

        if stripped.startswith('|') and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            header_cells = [cell.strip() for cell in stripped.strip('|').split('|')]
            i += 2
            rows: list[list[str]] = []
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line.startswith('|'):
                    break
                rows.append([cell.strip() for cell in row_line.strip('|').split('|')])
                i += 1

            header_html = ''.join(f'<th>{_inline_format(cell)}</th>' for cell in header_cells)
            body_html = ''.join(
                '<tr>' + ''.join(f'<td>{_inline_format(cell)}</td>' for cell in row) + '</tr>'
                for row in rows
            )
            html_parts.append(f'<table><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>')
            continue

        if _parse_unordered_line(line) is not None:
            block_lines: list[str] = []
            while i < len(lines) and _parse_unordered_line(lines[i]) is not None:
                block_lines.append(lines[i].rstrip('\n'))
                i += 1
            html_parts.append(_render_unordered_list(block_lines))
            continue

        if re.match(r'^\d+\.\s+', stripped):
            list_items = []
            while i < len(lines):
                li = lines[i].strip()
                if not re.match(r'^\d+\.\s+', li):
                    break
                text = re.sub(r'^\d+\.\s+', '', li)
                list_items.append(f'<li>{_inline_format(text)}</li>')
                i += 1
            html_parts.append('<ol>' + ''.join(list_items) + '</ol>')
            continue

        para_lines: list[str] = [stripped]
        i += 1
        while i < len(lines):
            probe = lines[i].strip()
            if not probe:
                break
            if (
                probe.startswith('```')
                or probe.startswith('#')
                or probe in {'---', '***', '___'}
                or probe.startswith('>')
                or probe.startswith('|')
                or _parse_unordered_line(lines[i]) is not None
                or re.match(r'^\d+\.\s+', probe)
            ):
                break
            para_lines.append(probe)
            i += 1
        html_parts.append('<p>' + _inline_format(' '.join(para_lines)) + '</p>')

    return '<body>' + ''.join(html_parts) + '</body>'


def _postprocess_html_codeblocks(html_content: str) -> str:
    pattern = re.compile(r'<pre><code(?: class="([^"]*)")?>(.*?)</code></pre>', re.DOTALL)

    def repl(match: re.Match[str]) -> str:
        class_attr = (match.group(1) or '').strip()
        code_payload = html.unescape(match.group(2) or '')
        language = ''
        for token in class_attr.split():
            token_norm = token.strip().lower()
            if token_norm.startswith('language-'):
                language = token_norm.removeprefix('language-')
                break
            if token_norm in _KEYWORDS:
                language = token_norm
                break

        highlighted = _highlight_code_fallback(code_payload, language)
        return f'<div class="codehilite"><pre><code>{highlighted}</code></pre></div>'

    return pattern.sub(repl, html_content)


def _inject_inline_style(html_content: str, tag_name: str, style: str) -> str:
    pattern = re.compile(rf'<{tag_name}\b([^>]*)>', re.IGNORECASE)

    def repl(match: re.Match[str]) -> str:
        attrs = match.group(1) or ''
        lower_attrs = attrs.lower()
        if 'style=' in lower_attrs:
            return f'<{tag_name}{attrs}>'
        if tag_name.lower() == 'table' and 'dk-quote-table' in lower_attrs:
            return f'<{tag_name}{attrs}>'
        return f'<{tag_name}{attrs} style="{style}">'

    return pattern.sub(repl, html_content)


def _apply_list_depth_styles(html_content: str) -> str:
    token_pattern = re.compile(r'(<(/?)(ul|ol|li)\b[^>]*>)', re.IGNORECASE)
    depth = 0
    parts: list[str] = []
    last = 0

    for match in token_pattern.finditer(html_content):
        parts.append(html_content[last:match.start()])
        token = match.group(1)
        closing = match.group(2) == '/'
        tag = match.group(3).lower()
        replacement = token

        if tag in {'ul', 'ol'}:
            if closing:
                depth = max(0, depth - 1)
            else:
                depth += 1
                if 'style=' not in token.lower():
                    if depth == 1:
                        list_style = 'margin:0 0 10px 0; padding:0 0 0 18px;'
                    else:
                        list_style = 'margin:2px 0 4px 0; padding:0 0 0 16px;'
                    replacement = token[:-1] + f' style="{list_style}">'
        elif tag == 'li' and not closing and 'style=' not in token.lower():
            replacement = token[:-1] + ' style="margin:0 0 2px 0; padding:0;">'

        parts.append(replacement)
        last = match.end()

    parts.append(html_content[last:])
    return ''.join(parts)


def _postprocess_html_markdown_blocks(html_content: str) -> str:
    quote_pattern = re.compile(r'<blockquote>(.*?)</blockquote>', re.DOTALL | re.IGNORECASE)

    quote_table_style = (
        f'width:100%; border-collapse:separate; border-spacing:0; margin:0 0 12px 0; '
        f'border:1px solid {C.dropdown_surface_border}; border-radius:8px; '
        f'background:{C.scrollable_surface_background};'
    )
    quote_icon_style = (
        f'width:24px; padding:8px 4px 8px 12px; border:none; '
        f'color:{C.button_accent_base}; font-size:18px; font-weight:700; '
        f'vertical-align:top;'
    )
    quote_cell_style = (
        f'padding:8px 12px 8px 4px; color:{C.text_primary}; '
        f'vertical-align:top; border:none; background:transparent;'
    )
    table_style = (
        f'width:100%; border-collapse:collapse; border-spacing:0; margin:0 0 12px 0; '
        f'border:1px solid {C.field_border}; background:{C.field_background};'
    )
    th_style = (
        f'border:1px solid {C.field_border}; padding:7px 10px; text-align:left; '
        f'vertical-align:top; background:{C.section_background}; color:{C.text_hero}; font-weight:650;'
    )
    td_style = (
        f'border:1px solid {C.field_border}; padding:7px 10px; text-align:left; '
        f'vertical-align:top; color:{C.text_primary};'
    )

    html_content = quote_pattern.sub(
        lambda m: (
            f'<table class="dk-quote-table" bgcolor="{C.scrollable_surface_background}" style="{quote_table_style}" border="0" cellspacing="0" cellpadding="0"><tr>'
            f'<td style="{quote_icon_style}">❝</td>'
            f'<td style="{quote_cell_style}">{m.group(1).strip()}</td>'
            f'</tr></table>'
        ),
        html_content,
    )

    html_content = _apply_list_depth_styles(html_content)
    html_content = _inject_inline_style(html_content, 'table', table_style)
    html_content = _inject_inline_style(html_content, 'th', th_style)
    html_content = _inject_inline_style(html_content, 'td', td_style)
    return html_content
def set_markdown_content(browser: QTextBrowser, markdown_text: str) -> None:
    normalized_markdown = textwrap.dedent(markdown_text).strip('\n')

    if _markdown_module is not None:
        html_content = _markdown_module.markdown(
            normalized_markdown,
            extensions=_markdown_extensions(),
            extension_configs=_MARKDOWN_EXTENSION_CONFIGS,
        )
        if _pygments_module is None:
            html_content = _postprocess_html_codeblocks(html_content)
    else:
        html_content = _render_markdown_fallback(normalized_markdown)

    html_content = _postprocess_html_markdown_blocks(html_content)
    browser.setHtml(f'<body><div class="markdown-body">{html_content}</div></body>')
__all__ = [
    'DataTableWidget',
    'MarkdownShowcaseWidget',
    'apply_markdown_style',
    'country_names',
    'set_markdown_content',
    'table_palette_for_theme',
]





















