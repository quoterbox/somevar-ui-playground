from __future__ import annotations

from dataclasses import dataclass
from math import cos, exp, sin
from typing import Final

from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QColorDialog,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from somevar_ui_playground.ui.playground_support import (
    country_names,
    MarkdownShowcaseWidget,
)
from somevar_ui.ui.kit.core import BaseWidget, hbox, vbox
from somevar_ui.ui.charts import (
    PYQTGRAPH_AVAILABLE,
    BarSeriesSpec,
    DonutSegmentSpec,
    BarChartWidget,
    DonutChartWidget,
    LineChartWidget,
    ScatterChartWidget,
    LineSeriesSpec,
    ScatterPointSpec,
    ScatterSeriesSpec,
)
from somevar_ui.ui.kit.containers import MessagePanel, ModalStack
from somevar_ui.ui.kit.dialogs import SettingsFormPanel
from somevar_ui.ui.kit.icons import AVAILABLE_ICONS, resolve_icon_name
from somevar_ui.ui.kit.tables import DataTableWidget, table_palette_for_theme
from somevar_ui.ui.kit.widgets import (
    ACCENT_BUTTON,
    SECONDARY_BUTTON,
    SURFACE_BUTTON,
    Button,
    CheckBox,
    CodeBlock,
    CollapsibleSection,
    ComboBox,
    DoubleSpinBox,
    FileDropZone,
    IconButton,
    IconWidget,
    LineEdit,
    ProgressBar,
    RadioButton,
    ROUTE_ACTION_LABEL_ROLE,
    ROUTE_AUTOSIZE_ROLE,
    ROUTE_BACKGROUND_ROLE,
    ROUTE_BORDER_ROLE,
    ROUTE_COORDS_LABEL_ROLE,
    ROUTE_ROLE_LABEL_ROLE,
    ROUTE_TEXT_ROLE,
    SearchableSelect,
    Slider,
    Switch,
    TILE_BACKGROUND_ROLE,
    TILE_BORDER_ROLE,
    TILE_META_ROLE,
    TILE_SUBTITLE_ROLE,
    TILE_TEXT_ROLE,
    TILE_TITLE_ROLE,
    DragListConfig,
    ReorderableListWidget,
    TileReorderableListWidget,
)
from somevar_ui.core import get_ui_runtime_state
from somevar_ui.ui.bootstrap import apply_theme
from somevar_ui.ui.shell import TitleBar, WindowFrameController, handle_windows_native_event
from somevar_ui.ui.theme import THEME

S = THEME.spacing
L = THEME.layout
C = THEME.colors
M = THEME.metrics


def _make_route_card_item(
    role: str,
    coords: str,
    action: str,
    *,
    background: str | None = None,
    border: str | None = None,
    text_color: str | None = None,
    height_units: int = 1,
    auto_height: bool = False,
) -> QListWidgetItem:
    item = QListWidgetItem()
    item.setData(ROUTE_ROLE_LABEL_ROLE, role)
    item.setData(ROUTE_COORDS_LABEL_ROLE, coords)
    item.setData(ROUTE_ACTION_LABEL_ROLE, action)
    if background is not None:
        item.setData(ROUTE_BACKGROUND_ROLE, background)
    if border is not None:
        item.setData(ROUTE_BORDER_ROLE, border)
    if text_color is not None:
        item.setData(ROUTE_TEXT_ROLE, text_color)
    if auto_height:
        item.setData(ROUTE_AUTOSIZE_ROLE, True)
    units = max(1, int(height_units))
    item.setSizeHint(QSize(0, (units * L.route_item_height) + (max(0, units - 1) * L.route_item_spacing)))
    return item


def _make_tile_item(
    title: str,
    subtitle: str,
    meta: str,
    *,
    background: str | None = None,
    border: str | None = None,
    text_color: str | None = None,
) -> QListWidgetItem:
    item = QListWidgetItem()
    item.setData(TILE_TITLE_ROLE, title)
    item.setData(TILE_SUBTITLE_ROLE, subtitle)
    item.setData(TILE_META_ROLE, meta)
    if background is not None:
        item.setData(TILE_BACKGROUND_ROLE, background)
    if border is not None:
        item.setData(TILE_BORDER_ROLE, border)
    if text_color is not None:
        item.setData(TILE_TEXT_ROLE, text_color)
    item.setSizeHint(QSize(L.tile_item_size, L.tile_item_size))
    return item


def _color_luminance(color: QColor) -> float:
    red, green, blue, _alpha = color.getRgb()
    return (0.299 * red) + (0.587 * green) + (0.114 * blue)


def _card_text_color(background: QColor) -> str:
    return '#102132' if _color_luminance(background) >= 158 else '#F4F8FF'


def _card_border_color(background: QColor) -> str:
    if _color_luminance(background) >= 158:
        return background.darker(135).name()
    return background.lighter(140).name()


def create_section(parent: QWidget, title: str, description: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame(parent)
    card.setObjectName('SectionCard')
    layout = vbox(card, spacing=S.lg)
    layout.setContentsMargins(
        L.section_padding_x,
        L.section_padding_top,
        L.section_padding_x,
        L.section_padding_bottom,
    )

    title_label = QLabel(title, card)
    title_label.setProperty('role', 'section')
    desc_label = QLabel(description, card)
    desc_label.setProperty('role', 'muted')
    desc_label.setWordWrap(True)

    layout.addWidget(title_label)
    layout.addWidget(desc_label)
    return card, layout


class _RawIconPreview(QWidget):
    def __init__(
        self,
        icon_name: str,
        *,
        size: int = 24,
        color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        box = max(40, size + 16)
        self.setFixedSize(box, box)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout = vbox(self, spacing=0)
        layout.setContentsMargins(0, 0, 0, 0)
        preview = IconWidget(icon_name, size=size, color=color, parent=self)
        layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignCenter)


class _IconCatalogTile(QFrame):
    def __init__(self, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('IconCatalogTile')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(156)
        self.refresh_theme()
        layout = vbox(self, spacing=S.xs)
        layout.setContentsMargins(S.md, S.md, S.md, S.md)

        preview = _RawIconPreview(icon_name, size=28, parent=self)
        title = QLabel(icon_name, self)
        title.setProperty('role', 'subsection')
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        resolved = QLabel(resolve_icon_name(icon_name), self)
        resolved.setProperty('role', 'muted')
        resolved.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(resolved)

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame#IconCatalogTile {{
                background: {C.field_background};
                border: 1px solid {C.section_border};
                border-radius: {M.card_radius}px;
            }}
            """
        )


class IconsCategoryPage(BaseWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)

        catalog_card, catalog_layout = create_section(
            self,
            'Vector icon catalog',
            'All registered icons rendered as raw vectors with larger previews.',
        )
        icon_grid = QGridLayout()
        icon_grid.setContentsMargins(0, 0, 0, 0)
        icon_grid.setHorizontalSpacing(S.md)
        icon_grid.setVerticalSpacing(S.md)
        columns = 4
        for index, icon_name in enumerate(AVAILABLE_ICONS):
            tile = _IconCatalogTile(icon_name, catalog_card)
            row = index // columns
            col = index % columns
            icon_grid.addWidget(tile, row, col)
        catalog_layout.addLayout(icon_grid)

        sizes_card, sizes_layout = create_section(
            self,
            'Icon sizes',
            'Compare how the same icon reads at compact and large sizes.',
        )
        sizes_row = hbox(spacing=S.xl)
        size_tokens = (
            ('XS', M.icon_size_xs),
            ('SM', M.icon_size_sm),
            ('MD', M.icon_size_md),
            ('LG', M.icon_size_lg),
            ('XL', M.icon_size_xl),
        )
        for token_name, size in size_tokens:
            sample = QWidget(sizes_card)
            sample_layout = vbox(sample, spacing=S.xs)
            sample_layout.setContentsMargins(0, 0, 0, 0)
            preview = _RawIconPreview('settings', size=size, parent=sample)
            caption = QLabel(f'{token_name} · {size}px', sample)
            caption.setProperty('role', 'caption')
            caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            sample_layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignHCenter)
            sample_layout.addWidget(caption)
            sizes_row.addWidget(sample)
        sizes_row.addStretch(1)
        sizes_layout.addLayout(sizes_row)

        buttons_card, buttons_layout = create_section(
            self,
            'Interactive icon buttons',
            'Real controls using the icon registry. Hover and press transitions come from the shared button animation system.',
        )

        buttons_row = hbox(spacing=S.lg)
        for icon_name in ('menu', 'search', 'info', 'settings', 'back', 'close', 'plus', 'check', 'trash', 'play'):
            sample = QWidget(buttons_card)
            sample_layout = vbox(sample, spacing=S.xs)
            sample_layout.setContentsMargins(0, 0, 0, 0)
            button = IconButton(icon_name, parent=sample)
            button.setFixedSize(42, 42)
            caption = QLabel(icon_name, sample)
            caption.setProperty('role', 'caption')
            caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            sample_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
            sample_layout.addWidget(caption)
            buttons_row.addWidget(sample)
        buttons_row.addStretch(1)

        palettes_row = hbox(spacing=S.lg)
        palette_specs = (
            ('Surface', SURFACE_BUTTON, 'folder'),
            ('Accent', ACCENT_BUTTON, 'play'),
            ('Secondary', SECONDARY_BUTTON, 'search'),
        )
        for label_text, palette, icon_name in palette_specs:
            sample = QWidget(buttons_card)
            sample_layout = vbox(sample, spacing=S.xs)
            sample_layout.setContentsMargins(0, 0, 0, 0)
            button = IconButton(icon_name, palette=palette, parent=sample)
            button.setFixedSize(46, 46)
            caption = QLabel(label_text, sample)
            caption.setProperty('role', 'caption')
            caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            sample_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
            sample_layout.addWidget(caption)
            palettes_row.addWidget(sample)
        ghost_sample = QWidget(buttons_card)
        ghost_layout = vbox(ghost_sample, spacing=S.xs)
        ghost_layout.setContentsMargins(0, 0, 0, 0)
        ghost_button = IconButton('back', parent=ghost_sample, ghost_idle=True)
        ghost_button.setFixedSize(46, 46)
        ghost_caption = QLabel('Ghost idle', ghost_sample)
        ghost_caption.setProperty('role', 'caption')
        ghost_caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ghost_layout.addWidget(ghost_button, 0, Qt.AlignmentFlag.AlignHCenter)
        ghost_layout.addWidget(ghost_caption)
        palettes_row.addWidget(ghost_sample)
        palettes_row.addStretch(1)

        alias_grid = QGridLayout()
        alias_grid.setContentsMargins(0, 0, 0, 0)
        alias_grid.setHorizontalSpacing(S.lg)
        alias_grid.setVerticalSpacing(S.sm)
        aliases = (
            ('back', 'chevron-left'),
            ('close', 'x'),
            ('minimize', 'minus'),
            ('maximize', 'square'),
            ('hamburger', 'menu'),
            ('add', 'plus'),
            ('confirm', 'check'),
            ('delete', 'trash'),
        )
        for index, (alias_name, resolved_name) in enumerate(aliases):
            left = QLabel(alias_name, buttons_card)
            left.setProperty('role', 'subsection')
            right = QLabel(resolved_name, buttons_card)
            right.setProperty('role', 'muted')
            alias_grid.addWidget(left, index, 0)
            alias_grid.addWidget(right, index, 1)

        buttons_layout.addLayout(buttons_row)
        buttons_layout.addWidget(self._caption('Button palettes and hover states'))
        buttons_layout.addLayout(palettes_row)
        buttons_layout.addWidget(self._caption('Semantic aliases'))
        buttons_layout.addLayout(alias_grid)

        layout.addWidget(catalog_card)
        layout.addWidget(sizes_card)
        layout.addWidget(buttons_card)
        layout.addStretch(1)

    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty('role', 'caption')
        return label


@dataclass(frozen=True, slots=True)
class PlaygroundCategory:
    category_id: str
    title: str
    description: str
    demo_count: int
    page: QWidget


class ModalCategoryPage(BaseWidget):
    open_simple_modal_requested = Signal()
    open_modal_stack_requested = Signal()
    open_settings_form_requested = Signal()
    open_detached_window_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)

        simple_card, simple_layout = create_section(
            self,
            'Simple modal window',
            'Minimal modal with one action button and clear content hierarchy.',
        )
        open_simple = Button('Open simple modal', ACCENT_BUTTON, simple_card)
        open_simple.clicked.connect(self.open_simple_modal_requested.emit)
        simple_layout.addWidget(open_simple)

        stack_card, stack_layout = create_section(
            self,
            'Modal chain (stack flow)',
            'Demonstrates forward/back transitions for a sequence of modal pages.',
        )
        open_stack = Button('Open modal chain', ACCENT_BUTTON, stack_card)
        open_stack.clicked.connect(self.open_modal_stack_requested.emit)
        stack_layout.addWidget(open_stack)

        settings_card, settings_layout = create_section(
            self,
            'Settings form modal',
            'Reusable framework panel for settings and form dialogs with sections, fields and footer actions.',
        )
        open_settings = Button('Open settings form', ACCENT_BUTTON, settings_card)
        open_settings.clicked.connect(self.open_settings_form_requested.emit)
        settings_layout.addWidget(open_settings)

        detached_card, detached_layout = create_section(
            self,
            'Standalone window',
            'Separate top-level demo window that uses the same UI kit controls and style.',
        )
        self.detached_mode_combo = ComboBox(detached_card)
        self.detached_mode_combo.addItem('Tool window (close only)', 'tool')
        self.detached_mode_combo.addItem('Full window (min/max/close)', 'full')
        detached_layout.addWidget(self._caption('Detached window mode'))
        detached_layout.addWidget(self.detached_mode_combo)

        open_detached = Button('Open standalone window', SECONDARY_BUTTON, detached_card)
        open_detached.clicked.connect(self._emit_detached_window_requested)
        detached_layout.addWidget(open_detached)

        layout.addWidget(simple_card)
        layout.addWidget(stack_card)
        layout.addWidget(settings_card)
        layout.addWidget(detached_card)
        layout.addStretch(1)

    def _emit_detached_window_requested(self) -> None:
        mode = str(self.detached_mode_combo.currentData() or 'tool')
        self.open_detached_window_requested.emit(mode)

    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty('role', 'caption')
        return label


class ControlsCategoryPage(BaseWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)

        form_card, form_layout = create_section(
            self,
            'Inputs and selectors',
            'Text fields, dropdowns and searchable select for form scenarios.',
        )
        self.name_input = LineEdit(form_card)
        self.name_input.setPlaceholderText('Type profile name')

        self.notes_input = QPlainTextEdit(form_card)
        self.notes_input.setPlaceholderText('Optional multiline note')
        self.notes_input.setFixedHeight(92)

        self.mode_combo = ComboBox(form_card)
        self.mode_combo.addItem('Algorithmic (stable)', 'algorithmic')
        self.mode_combo.addItem('Adaptive (experimental)', 'adaptive')
        self.mode_combo.addItem('Replay profile', 'profile')

        self.search_select = SearchableSelect(country_names(), form_card)

        form_layout.addWidget(self._caption('Profile name'))
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self._caption('Notes'))
        form_layout.addWidget(self.notes_input)
        form_layout.addWidget(self._caption('Movement engine'))
        form_layout.addWidget(self.mode_combo)
        form_layout.addWidget(self._caption('Searchable select (type at least 3 chars)'))
        form_layout.addWidget(self.search_select)

        toggle_card, toggle_layout = create_section(
            self,
            'Toggles and choice controls',
            'Checkboxes, radio buttons and compact switch variant.',
        )
        self.check_one = CheckBox('Enable hover transitions', toggle_card)
        self.check_two = CheckBox('Enable high precision mode', toggle_card)
        self.check_one.setChecked(True)

        radio_row = hbox(spacing=S.xl)
        self.radio_mouse = RadioButton('Mouse actions', toggle_card)
        self.radio_keyboard = RadioButton('Keyboard actions', toggle_card)
        self.interaction_group = QButtonGroup(toggle_card)
        self.interaction_group.setExclusive(True)
        self.interaction_group.addButton(self.radio_mouse)
        self.interaction_group.addButton(self.radio_keyboard)
        self.radio_mouse.setChecked(True)
        radio_row.addWidget(self.radio_mouse)
        radio_row.addWidget(self.radio_keyboard)
        radio_row.addStretch(1)

        switch_row = hbox(spacing=S.md)
        switch_label = QLabel('Use compact switch variant', toggle_card)
        switch_label.setProperty('role', 'subsection')
        self.mode_switch = Switch(toggle_card)
        self.mode_switch.setChecked(True)
        switch_row.addWidget(switch_label, 1)
        switch_row.addWidget(self.mode_switch, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        slider_row = hbox(spacing=S.md)
        self.intensity_slider = Slider(parent=toggle_card)
        self.intensity_slider.setRange(0, 100)
        self.intensity_slider.setValue(55)
        self.intensity_value = QLabel('55%', toggle_card)
        self.intensity_value.setProperty('role', 'subsection')
        self.intensity_value.setFixedWidth(L.percent_value_width)
        self.intensity_slider.valueChanged.connect(lambda value: self.intensity_value.setText(f'{value}%'))
        slider_row.addWidget(self.intensity_slider, 1)
        slider_row.addWidget(self.intensity_value)

        toggle_layout.addWidget(self.check_one)
        toggle_layout.addWidget(self.check_two)
        toggle_layout.addWidget(self._caption('Interaction mode'))
        toggle_layout.addLayout(radio_row)
        toggle_layout.addLayout(switch_row)
        toggle_layout.addWidget(self._caption('Intensity'))
        toggle_layout.addLayout(slider_row)

        layout.addWidget(form_card)
        layout.addWidget(toggle_card)
        layout.addStretch(1)

    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty('role', 'caption')
        return label


class ChartsCategoryPage(BaseWidget):
    _BAR_CATEGORIES: Final[tuple[str, ...]] = ('Idle', 'Gaming', 'Training', 'Render', 'Compile')
    _SCATTER_SERIES_COLORS: Final[tuple[str, ...]] = ('#5AA0D8', '#F2C168', '#7BD3B3', '#D98CDB', '#F48B6E')

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)

        self._resource_step = 0
        self._bar_phase = 0
        self._scatter_point_counter = 1
        self._scatter_color_map: dict[str, str] = {}
        self._resource_timer = QTimer(self)
        self._resource_timer.setInterval(700)
        self._resource_timer.timeout.connect(self._tick_resource_chart)

        function_card, function_layout = create_section(
            self,
            'Animated function plot',
            'Multiple curves can be toggled on and off. When visibility changes, the chart animates to the new visible data bounds instead of snapping abruptly.',
        )
        self._function_chart = LineChartWidget(function_card)
        self._function_chart.set_axis_labels('Input', 'Amplitude')
        self._function_chart.set_series(self._build_function_series(), animate_range=True)
        function_layout.addWidget(self._function_chart)

        resource_card, resource_layout = create_section(
            self,
            'Resource timeline',
            'Streaming CPU, GPU and NPU lines for the upcoming benchmark-style dashboards. This demo keeps the Y axis fixed to 0-100 while the data scrolls over time.',
        )
        resource_controls = hbox(spacing=S.md)
        self._resource_start_button = Button('Start stream', ACCENT_BUTTON, resource_card)
        self._resource_pause_button = Button('Pause', SECONDARY_BUTTON, resource_card)
        self._resource_reset_button = Button('Reset data', SURFACE_BUTTON, resource_card)
        self._resource_start_button.clicked.connect(self._start_resource_stream)
        self._resource_pause_button.clicked.connect(self._pause_resource_stream)
        self._resource_reset_button.clicked.connect(self._reset_resource_stream)
        resource_controls.addWidget(self._resource_start_button, 0)
        resource_controls.addWidget(self._resource_pause_button, 0)
        resource_controls.addWidget(self._resource_reset_button, 0)
        resource_controls.addStretch(1)
        resource_layout.addLayout(resource_controls)

        self._resource_chart = LineChartWidget(resource_card)
        self._resource_chart.set_axis_labels('Sample', 'Load %')
        self._resource_chart.set_fixed_y_range(0.0, 100.0)
        resource_layout.addWidget(self._resource_chart)
        self._seed_resource_chart()

        bars_card, bars_layout = create_section(
            self,
            'Workload comparison',
            'Grouped bars cover dashboards, benchmark comparisons and release reports. Series can be toggled just like line charts and the Y range rescales to the remaining data.',
        )
        bars_controls = hbox(spacing=S.md)
        cycle_button = Button('Cycle dataset', ACCENT_BUTTON, bars_card)
        cycle_button.clicked.connect(self._cycle_bar_dataset)
        bars_controls.addWidget(cycle_button, 0)
        bars_controls.addStretch(1)
        bars_layout.addLayout(bars_controls)

        self._bar_chart = BarChartWidget(bars_card)
        self._bar_chart.set_axis_labels('Workload', 'Relative throughput')
        self._bar_chart.set_data(categories=self._BAR_CATEGORIES, series_list=self._build_bar_series(phase=0), animate_range=True)
        bars_layout.addWidget(self._bar_chart)

        donut_card, donut_layout = create_section(
            self,
            'Donut dashboard widget',
            'QPainter-based dashboard charts stay fully themeable and do not depend on coordinate-plot mechanics. Hover a segment to highlight its share.',
        )
        self._donut_chart = DonutChartWidget(donut_card)
        self._donut_chart.set_segments(
            [
                DonutSegmentSpec.create(key='cpu', name='CPU', value=42, color='#5AA0D8'),
                DonutSegmentSpec.create(key='gpu', name='GPU', value=31, color='#F2C168'),
                DonutSegmentSpec.create(key='npu', name='NPU', value=18, color='#7BD3B3'),
                DonutSegmentSpec.create(key='io', name='I/O wait', value=9, color='#D98CDB'),
            ],
            title='Resource mix',
            center_label='100%',
            animate=True,
        )
        donut_layout.addWidget(self._donut_chart)

        scatter_card, scatter_layout = create_section(
            self,
            'Scatter + point annotations',
            'Add labeled points into any series, toggle those series like a legend and use the shared reset button to return to the default viewport.',
        )
        scatter_form = QGridLayout()
        scatter_form.setContentsMargins(0, 0, 0, 0)
        scatter_form.setHorizontalSpacing(S.lg)
        scatter_form.setVerticalSpacing(S.sm)

        self._scatter_series_input = LineEdit(scatter_card)
        self._scatter_series_input.setPlaceholderText('Series / legend label')
        self._scatter_series_input.setText('Candidate')
        self._scatter_label_input = LineEdit(scatter_card)
        self._scatter_label_input.setPlaceholderText('Point annotation')
        self._scatter_label_input.setText('P-01')
        self._scatter_x_input = DoubleSpinBox(scatter_card)
        self._scatter_x_input.setRange(-1000.0, 1000.0)
        self._scatter_x_input.setDecimals(2)
        self._scatter_x_input.setValue(5.2)
        self._scatter_y_input = DoubleSpinBox(scatter_card)
        self._scatter_y_input.setRange(-1000.0, 1000.0)
        self._scatter_y_input.setDecimals(2)
        self._scatter_y_input.setValue(8.4)

        scatter_form.addWidget(self._caption('Series'), 0, 0)
        scatter_form.addWidget(self._scatter_series_input, 0, 1)
        scatter_form.addWidget(self._caption('Point label'), 0, 2)
        scatter_form.addWidget(self._scatter_label_input, 0, 3)
        scatter_form.addWidget(self._caption('X'), 1, 0)
        scatter_form.addWidget(self._scatter_x_input, 1, 1)
        scatter_form.addWidget(self._caption('Y'), 1, 2)
        scatter_form.addWidget(self._scatter_y_input, 1, 3)
        scatter_layout.addLayout(scatter_form)

        scatter_actions = hbox(spacing=S.md)
        add_point_button = Button('Add point', ACCENT_BUTTON, scatter_card)
        reset_scatter_button = Button('Reset dataset', SURFACE_BUTTON, scatter_card)
        add_point_button.clicked.connect(self._add_scatter_point)
        reset_scatter_button.clicked.connect(self._reset_scatter_series)
        scatter_actions.addWidget(add_point_button, 0)
        scatter_actions.addWidget(reset_scatter_button, 0)
        scatter_actions.addStretch(1)
        scatter_layout.addLayout(scatter_actions)

        self._scatter_chart = ScatterChartWidget(scatter_card)
        self._scatter_chart.set_axis_labels('Latency', 'Throughput')
        scatter_layout.addWidget(self._scatter_chart)
        self._reset_scatter_series()

        layout.addWidget(function_card)
        layout.addWidget(resource_card)
        layout.addWidget(bars_card)
        layout.addWidget(donut_card)
        layout.addWidget(scatter_card)
        layout.addStretch(1)

        if PYQTGRAPH_AVAILABLE:
            self._resource_timer.start()
            self._resource_chart.set_live_streaming(True)

    def refresh_theme(self) -> None:
        self._function_chart.refresh_theme()
        self._resource_chart.refresh_theme()
        self._bar_chart.refresh_theme()
        self._donut_chart.refresh_theme()
        self._scatter_chart.refresh_theme()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if PYQTGRAPH_AVAILABLE and not self._resource_timer.isActive():
            self._resource_timer.start()
            self._resource_chart.set_live_streaming(True)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        super().hideEvent(event)
        self._resource_timer.stop()
        self._resource_chart.set_live_streaming(False)

    def _build_function_series(self) -> list[LineSeriesSpec]:
        x_values = [(-6.0 + (index * 0.2)) for index in range(61)]
        return [
            LineSeriesSpec.from_values(
                key='sine',
                name='sin(x)',
                x_values=x_values,
                y_values=[sin(value) for value in x_values],
                color='#5AA0D8',
                visible=True,
                show_points=False,
            ),
            LineSeriesSpec.from_values(
                key='cosine',
                name='0.65 * cos(0.6x)',
                x_values=x_values,
                y_values=[0.65 * cos(value * 0.6) for value in x_values],
                color='#7BD3B3',
                visible=True,
                show_points=True,
            ),
            LineSeriesSpec.from_values(
                key='response',
                name='e^(-0.18x²) * sin(2x)',
                x_values=x_values,
                y_values=[exp(-0.18 * (value * value)) * sin(value * 2.0) for value in x_values],
                color='#F2C168',
                visible=True,
                show_points=False,
                fill_level=0.0,
                fill_alpha=36,
            ),
        ]

    def _seed_resource_chart(self) -> None:
        x_values = [float(index) for index in range(36)]
        self._resource_step = len(x_values) - 1
        self._resource_chart.set_series(
            [
                LineSeriesSpec.from_values(
                    key='cpu',
                    name='CPU',
                    x_values=x_values,
                    y_values=[self._resource_value('cpu', index) for index in x_values],
                    color='#5AA0D8',
                ),
                LineSeriesSpec.from_values(
                    key='gpu',
                    name='GPU',
                    x_values=x_values,
                    y_values=[self._resource_value('gpu', index) for index in x_values],
                    color='#F2C168',
                ),
                LineSeriesSpec.from_values(
                    key='npu',
                    name='NPU',
                    x_values=x_values,
                    y_values=[self._resource_value('npu', index) for index in x_values],
                    color='#7BD3B3',
                ),
            ],
            animate_range=False,
        )

    def _resource_value(self, key: str, step: float) -> float:
        phase = float(step)
        if key == 'cpu':
            return max(6.0, min(96.0, 42.0 + (18.0 * sin(phase * 0.21)) + (11.0 * sin(phase * 0.47))))
        if key == 'gpu':
            return max(8.0, min(98.0, 58.0 + (24.0 * sin(phase * 0.17 + 0.9)) + (9.0 * cos(phase * 0.34))))
        return max(2.0, min(92.0, 18.0 + (12.0 * sin(phase * 0.13 + 1.8)) + (7.0 * cos(phase * 0.39))))

    def _tick_resource_chart(self) -> None:
        self._resource_step += 1
        sample = float(self._resource_step)
        self._resource_chart.append_sample(
            sample,
            {
                'cpu': self._resource_value('cpu', sample),
                'gpu': self._resource_value('gpu', sample),
                'npu': self._resource_value('npu', sample),
            },
            max_points=72,
        )
        self._resource_chart.set_fixed_x_range(max(0.0, sample - 71.0), max(12.0, sample + 1.0))

    def _start_resource_stream(self) -> None:
        if PYQTGRAPH_AVAILABLE:
            self._resource_timer.start()
            self._resource_chart.set_live_streaming(True)

    def _pause_resource_stream(self) -> None:
        self._resource_timer.stop()
        self._resource_chart.set_live_streaming(False)

    def _reset_resource_stream(self) -> None:
        self._resource_timer.stop()
        self._resource_chart.set_live_streaming(False)
        self._resource_chart.clear_fixed_x_range()
        self._seed_resource_chart()
        if PYQTGRAPH_AVAILABLE:
            self._resource_timer.start()
            self._resource_chart.set_live_streaming(True)

    def _build_bar_series(self, *, phase: int) -> list[BarSeriesSpec]:
        datasets = [
            (
                [36, 78, 54, 82, 41],
                [24, 96, 118, 72, 31],
                [12, 44, 86, 39, 18],
            ),
            (
                [42, 84, 59, 75, 53],
                [28, 103, 126, 88, 35],
                [15, 56, 94, 48, 22],
            ),
            (
                [31, 72, 49, 68, 45],
                [20, 91, 117, 70, 30],
                [10, 40, 79, 37, 19],
            ),
        ]
        cpu_values, gpu_values, npu_values = datasets[phase % len(datasets)]
        return [
            BarSeriesSpec.from_values(key='cpu', name='CPU', values=cpu_values, color='#5AA0D8'),
            BarSeriesSpec.from_values(key='gpu', name='GPU', values=gpu_values, color='#F2C168'),
            BarSeriesSpec.from_values(key='npu', name='NPU', values=npu_values, color='#7BD3B3'),
        ]

    def _cycle_bar_dataset(self) -> None:
        self._bar_phase = (self._bar_phase + 1) % 3
        self._bar_chart.set_data(categories=self._BAR_CATEGORIES, series_list=self._build_bar_series(phase=self._bar_phase), animate_range=True)

    def _build_scatter_series(self) -> list[ScatterSeriesSpec]:
        self._scatter_color_map = {
            'baseline': '#5AA0D8',
            'candidate': '#F2C168',
        }
        return [
            ScatterSeriesSpec.from_points(
                key='baseline',
                name='Baseline',
                color=self._scatter_color_map['baseline'],
                points=[
                    ScatterPointSpec.create(x=2.4, y=5.2, label='B-01'),
                    ScatterPointSpec.create(x=3.0, y=6.1, label='B-02'),
                    ScatterPointSpec.create(x=3.8, y=6.8, label='B-03'),
                ],
            ),
            ScatterSeriesSpec.from_points(
                key='candidate',
                name='Candidate',
                color=self._scatter_color_map['candidate'],
                points=[
                    ScatterPointSpec.create(x=4.4, y=7.4, label='C-01'),
                    ScatterPointSpec.create(x=5.2, y=8.4, label='C-02'),
                    ScatterPointSpec.create(x=6.1, y=8.9, label='C-03'),
                ],
            ),
        ]

    def _scatter_series_key(self, name: str) -> str:
        raw = ''.join(character.lower() if character.isalnum() else '_' for character in name.strip())
        return raw.strip('_') or 'custom_series'

    def _scatter_series_color(self, key: str) -> str:
        if key not in self._scatter_color_map:
            color = self._SCATTER_SERIES_COLORS[len(self._scatter_color_map) % len(self._SCATTER_SERIES_COLORS)]
            self._scatter_color_map[key] = color
        return self._scatter_color_map[key]

    def _add_scatter_point(self) -> None:
        series_name = self._scatter_series_input.text().strip() or 'Custom series'
        point_label = self._scatter_label_input.text().strip()
        series_key = self._scatter_series_key(series_name)
        self._scatter_chart.add_point(
            series_key=series_key,
            series_name=series_name,
            x=self._scatter_x_input.value(),
            y=self._scatter_y_input.value(),
            label=point_label,
            color=self._scatter_series_color(series_key),
            symbol_size=10.0,
        )
        self._scatter_point_counter += 1
        self._scatter_label_input.setText(f'P-{self._scatter_point_counter:02d}')

    def _reset_scatter_series(self) -> None:
        self._scatter_chart.set_series(self._build_scatter_series(), animate_range=False)
        self._scatter_point_counter = 1
        self._scatter_series_input.setText('Candidate')
        self._scatter_label_input.setText('P-01')
        self._scatter_x_input.setValue(5.2)
        self._scatter_y_input.setValue(8.4)

    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty('role', 'caption')
        return label


class ListsCategoryPage(BaseWidget):
    _TABLE_ROWS: Final[list[tuple[str, str, str, str]]] = [
        ('01', 'Button', 'Ready', 'now'),
        ('02', 'ComboBox', 'Ready', 'now'),
        ('03', 'CheckBox', 'Ready', 'now'),
        ('04', 'RadioButton', 'Ready', 'now'),
        ('05', 'ReorderableListWidget', 'Ready', 'now'),
        ('06', 'CollapsibleSection', 'Ready', 'now'),
        ('07', 'SearchableSelect', 'Ready', 'now'),
        ('08', 'ProgressBar', 'Ready', 'now'),
    ]
    _MULTI_ZONE_COLUMNS: Final[list[tuple[str, tuple[tuple[str, str, str], ...]]]] = [
        (
            'Inbox',
            (
                ('Landing page polish', 'Hero + CTA alignment', 'Priority high'),
                ('Settings cleanup', 'Resolve stale toggles', 'Needs product sign-off'),
                ('Team avatars', 'Add fallback states', 'Visual pass'),
                ('Changelog draft', 'Summarize release notes', 'Copy review'),
                ('Billing labels', 'Shorten summary strings', 'Localization ready'),
                ('Upload hints', 'Clarify retry state', 'UX tweak'),
            ),
        ),
        (
            'In progress',
            (
                ('DnD smoothing', 'Preview hysteresis', 'Animation tuning'),
                ('Table density', 'Tight row spacing', 'Needs QA'),
                ('Search popup', 'Keyboard focus polish', 'Regression pass'),
                ('Theme tokens', 'Audit neutral surfaces', 'Design system'),
                ('Build script', 'Portable mode checks', 'Tooling'),
            ),
        ),
        (
            'Review',
            (
                ('Card shadows', 'Trim hover intensity', 'Designer review'),
                ('Markdown lists', 'Nested spacing polish', 'Content QA'),
                ('Progress panel', 'Async reset state', 'Needs retest'),
                ('Tile metrics', 'Grid overflow pass', 'Performance check'),
                ('Top bar icons', 'Alias mapping', 'Ready for merge'),
            ),
        ),
        (
            'Done',
            (
                ('Theme switch', 'Persist mode choice', 'Merged'),
                ('Modal stack', 'Close sequencing', 'Merged'),
                ('Icon catalog', 'Large preview layout', 'Merged'),
                ('Upload zone', 'Animation cleanup', 'Merged'),
                ('Search select', 'Result highlight', 'Merged'),
            ),
        ),
    ]
    _DENSE_TILE_ITEMS: Final[tuple[tuple[str, str, str], ...]] = (
        ('Auth', 'Token rotation + sign-in states', 'API'),
        ('Billing', 'Invoices, plans and taxes', 'Finance'),
        ('Storage', 'Retention and archive rules', 'Infra'),
        ('Queue', 'Workers and retry budget', 'Infra'),
        ('Media', 'Thumbnails and codecs', 'Pipeline'),
        ('Editor', 'Selection model + shortcuts', 'App'),
        ('Profile', 'Account preferences and bio', 'App'),
        ('Search', 'Ranking and query suggestions', 'UX'),
        ('Maps', 'Waypoints + geodata overlays', 'Feature'),
        ('Logs', 'Tail view and filters', 'Tooling'),
        ('Deploy', 'Environment promotion flow', 'Ops'),
        ('Backup', 'Snapshot health checks', 'Ops'),
        ('Alerts', 'Escalation and silence rules', 'Ops'),
        ('SDK', 'Generated snippets and docs', 'Docs'),
        ('Charts', 'Hover states + legends', 'Data'),
        ('Themes', 'Semantic tokens and palettes', 'Design'),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)
        self._table_widgets: list[DataTableWidget] = []
        self._route_lists: list[ReorderableListWidget] = []
        self._tile_lists: list[TileReorderableListWidget] = []
        self._quick_card_counter = 1
        self._custom_card_counter = 1
        self._custom_card_color = QColor('#3A84F7')

        table_card, table_layout = create_section(
            self,
            'Tables',
            'Balanced table colors adapt to the active theme. The first table highlights rows, the second one highlights both rows and columns.',
        )
        table = DataTableWidget(
            ['ID', 'Component', 'State', 'Updated'],
            [list(row) for row in self._TABLE_ROWS],
            column_stretches=[1, 4, 2, 2],
            hover_rows=True,
            row_height=34,
            parent=table_card,
        )
        self._table_widgets.append(table)
        table_layout.addWidget(table)

        matrix_card, matrix_layout = create_section(
            self,
            'Cross-hover table',
            'Highlights the active row and the active column at the same time.',
        )
        matrix_table = DataTableWidget(
            ['Metric', 'CPU', 'GPU', 'NPU'],
            [
                ['Hash rate', '412 MH/s', '2.4 GH/s', '158 MH/s'],
                ['Matrix ops', '118 GFLOPS', '7.6 TFLOPS', '842 GFLOPS'],
                ['Latency', '18 ms', '11 ms', '7 ms'],
                ['Power draw', '84 W', '216 W', '32 W'],
            ],
            column_stretches=[2, 2, 2, 2],
            hover_rows=True,
            hover_columns=True,
            row_height=36,
            parent=matrix_card,
        )
        self._table_widgets.append(matrix_table)
        matrix_layout.addWidget(matrix_table)

        cards_card, cards_layout = create_section(
            self,
            'Drag-and-drop cards',
            'Row cards keep four visible items before scrolling starts. Reordering stays inside the list.',
        )
        cards = self._create_route_list(
            cards_card,
            max_visible_items=4,
            min_visible_items=4,
            empty_placeholder_text='Drop route cards here to build the sequence.',
        )
        sample = [
            ('Start point', 'X=145   Y=80', 'Left click'),
            ('Waypoint 1', 'X=320   Y=210', 'No action'),
            ('Waypoint 2', 'X=600   Y=340', 'Wheel +2'),
            ('End point', 'X=820   Y=460', 'Right click'),
        ]
        for role, coords, action in sample:
            cards.addItem(_make_route_card_item(role, coords, action))
        cards.setCurrentRow(0)
        cards_layout.addWidget(cards)

        transfer_card, transfer_layout = create_section(
            self,
            'Transfer between zones',
            'Each zone keeps four visible cards before scroll. Drop onto a zone to move cards between the two areas.',
        )
        transfer_row = hbox(spacing=S.xl)

        selected_column, selected_cards = self._create_route_column(
            transfer_card,
            'Selected build',
            (
                ('CPU', 'Ryzen 9 9950X3D', 'AM5 / 16 cores'),
                ('GPU', 'GeForce RTX 5090', '24 GB GDDR7'),
                ('RAM', 'Corsair Dominator 64 GB', 'DDR5-6400'),
                ('Board', 'ROG Crosshair X870E', 'X870E / ATX'),
            ),
            drag_group='hardware-build',
            max_visible_items=4,
            min_visible_items=4,
            empty_placeholder_text='Drop hardware cards here.',
        )
        parking_column, parking_cards = self._create_route_column(
            transfer_card,
            'Parking area',
            (
                ('SSD', 'Samsung 990 Pro 4 TB', 'PCIe 4.0 NVMe'),
                ('PSU', 'Seasonic Prime TX-1000', '80+ Titanium'),
                ('Cooler', 'Noctua NH-D15 G2', 'Dual tower'),
                ('Case', 'Fractal North XL', 'E-ATX airflow'),
            ),
            drag_group='hardware-build',
            max_visible_items=4,
            min_visible_items=4,
            empty_placeholder_text='Move cards here to clear the active build.',
        )
        selected_cards.setCurrentRow(0)

        transfer_row.addWidget(selected_column, 1)
        transfer_row.addWidget(parking_column, 1)
        transfer_layout.addLayout(transfer_row)

        tile_card, tile_layout = create_section(
            self,
            'Tile layout reorder',
            'Tiles use a two-column grid with two visible rows before scrolling starts. Reorder stays inside the grid and does not transfer to the card zones above.',
        )
        tile_list = self._create_tile_list(
            tile_card,
            max_visible_rows=2,
            min_visible_rows=2,
            grid_columns=2,
            empty_placeholder_text='Drop tiles here.',
            highlight_drop_target=False,
            compact_grid_width=True,
        )
        tile_shell = QWidget(tile_card)
        tile_shell_layout = hbox(tile_shell, spacing=S.md)
        tile_shell_layout.setContentsMargins(0, 0, 0, 0)
        tile_shell_layout.addWidget(tile_list, 0)
        tile_shell_layout.addStretch(1)
        for title, subtitle, meta in (
            ('CPU', 'Ryzen 9 9950X3D', '16 cores'),
            ('GPU', 'RTX 5090 Founders', '24 GB'),
            ('RAM', 'Dominator Titanium', '64 GB'),
            ('Board', 'ROG Crosshair X870E', 'ATX'),
            ('SSD', '990 Pro', '4 TB'),
            ('PSU', 'Prime TX-1000', '1000 W'),
            ('Cooler', 'Noctua NH-D15 G2', 'Air tower'),
            ('Case', 'Fractal North XL', 'E-ATX'),
        ):
            tile_list.addItem(_make_tile_item(title, subtitle, meta))
        tile_layout.addWidget(tile_shell)

        board_card, board_layout = create_section(
            self,
            'Multi-column board',
            'The same row-card engine can span more than two columns. Every lane below shares one drag group, so cards move freely across the full board.',
        )
        board_grid = QGridLayout()
        board_grid.setContentsMargins(0, 0, 0, 0)
        board_grid.setHorizontalSpacing(S.lg)
        board_grid.setVerticalSpacing(S.lg)
        for column_index, (title, items) in enumerate(self._MULTI_ZONE_COLUMNS):
            column, lane = self._create_route_column(
                board_card,
                title,
                items,
                drag_group='planning-board',
                max_visible_items=5,
                min_visible_items=5,
                empty_placeholder_text=f'Drop cards into {title.lower()}.',
            )
            lane.setCurrentRow(0)
            board_grid.addWidget(column, 0, column_index, Qt.AlignmentFlag.AlignTop)
            board_grid.setColumnStretch(column_index, 1)
        board_layout.addLayout(board_grid)

        dense_tile_card, dense_tile_layout = create_section(
            self,
            'Dense tile wall',
            'A wider four-column grid with more rows shows how the tile solver behaves when the board grows. Reordering stays smooth because widgets are reused and only their geometry is animated.',
        )
        dense_tile_list = self._create_tile_list(
            dense_tile_card,
            max_visible_rows=3,
            min_visible_rows=3,
            grid_columns=4,
            item_extent=142,
            empty_placeholder_text='Drop tiles into the wall.',
            highlight_drop_target=True,
            compact_grid_width=True,
        )
        dense_tile_shell = QWidget(dense_tile_card)
        dense_tile_shell_layout = hbox(dense_tile_shell, spacing=S.md)
        dense_tile_shell_layout.setContentsMargins(0, 0, 0, 0)
        dense_tile_shell_layout.addWidget(dense_tile_list, 0)
        dense_tile_shell_layout.addStretch(1)
        for title, subtitle, meta in self._DENSE_TILE_ITEMS:
            dense_tile_list.addItem(_make_tile_item(title, subtitle, meta))
        dense_tile_layout.addWidget(dense_tile_shell)

        adaptive_card, adaptive_layout = create_section(
            self,
            'Adaptive height cards',
            'Row cards can also grow vertically. The stack below mixes one-slot cards, explicit double-height cards and cards that expand naturally to fit longer text.',
        )
        adaptive_stack = self._create_route_list(
            adaptive_card,
            max_visible_items=4,
            min_visible_items=4,
            empty_placeholder_text='Drop adaptive cards here.',
        )
        adaptive_stack.addItem(
            _make_route_card_item(
                'Compact summary',
                'One-slot card',
                'Short footer',
            )
        )
        adaptive_stack.addItem(
            _make_route_card_item(
                'Double-height slot',
                'This card reserves the height of two regular slots, which is useful for denser notes or pinned summaries.',
                'Height units = 2',
                background='#365CBA',
                border='#8AAAF8',
                text_color='#F4F8FF',
                height_units=2,
            )
        )
        adaptive_stack.addItem(
            _make_route_card_item(
                'Auto-fit content',
                'This card does not declare an explicit span. Instead, the row widget measures the wrapped content and grows just enough to keep the footer visible without clipping.',
                'Natural height based on text',
                background='#2F9A7F',
                border='#8EE0C9',
                text_color='#F4F8FF',
                auto_height=True,
            )
        )
        adaptive_stack.addItem(
            _make_route_card_item(
                'Follow-up',
                'Drag these cards around together',
                'DnD stays height-aware',
            )
        )
        adaptive_stack.setCurrentRow(0)
        adaptive_layout.addWidget(adaptive_stack)

        quick_card, quick_layout = create_section(
            self,
            'Quick add and delete',
            'These controls append generated cards, remove the current selection and clear the stack without affecting drag behaviour.',
        )
        quick_controls = hbox(spacing=S.md)
        quick_add_button = Button('Add generated card', ACCENT_BUTTON, quick_card)
        quick_remove_button = Button('Remove selected', SECONDARY_BUTTON, quick_card)
        quick_clear_button = Button('Clear stack', SURFACE_BUTTON, quick_card)
        quick_add_button.clicked.connect(self._append_quick_card)
        quick_remove_button.clicked.connect(self._remove_selected_quick_card)
        quick_clear_button.clicked.connect(self._clear_quick_stack)
        quick_controls.addWidget(quick_add_button, 0)
        quick_controls.addWidget(quick_remove_button, 0)
        quick_controls.addWidget(quick_clear_button, 0)
        quick_controls.addStretch(1)
        quick_layout.addLayout(quick_controls)

        self._quick_stack = self._create_route_list(
            quick_card,
            max_visible_items=5,
            min_visible_items=5,
            empty_placeholder_text='Add cards to this stack.',
        )
        for role, coords, action in (
            ('Backlog', 'Queued polish tasks', 'Pick any card to remove'),
            ('Follow-up', 'QA notes from last pass', 'Try drag + delete together'),
            ('Docs', 'Update release summary', 'Clear stack if needed'),
        ):
            self._quick_stack.addItem(_make_route_card_item(role, coords, action))
        self._quick_stack.setCurrentRow(0)
        quick_layout.addWidget(self._quick_stack)

        builder_card, builder_layout = create_section(
            self,
            'Custom card builder',
            'Pick a color, type the card lines and add fully custom cards into a stack. This demo shows how easy it is to theme cards per item.',
        )
        builder_shell = QWidget(builder_card)
        builder_shell_layout = QGridLayout(builder_shell)
        builder_shell_layout.setContentsMargins(0, 0, 0, 0)
        builder_shell_layout.setHorizontalSpacing(S.xl)
        builder_shell_layout.setVerticalSpacing(S.md)

        builder_controls = QWidget(builder_shell)
        builder_controls.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        builder_controls_layout = vbox(builder_controls, spacing=S.md)
        builder_controls_layout.setContentsMargins(0, 0, 0, 0)

        form_grid = QGridLayout()
        form_grid.setContentsMargins(0, 0, 0, 0)
        form_grid.setHorizontalSpacing(S.md)
        form_grid.setVerticalSpacing(S.sm)

        title_caption = QLabel('Title', builder_controls)
        title_caption.setProperty('role', 'caption')
        self._custom_title_input = LineEdit(builder_controls)
        self._custom_title_input.setPlaceholderText('Card title')

        details_caption = QLabel('Details', builder_controls)
        details_caption.setProperty('role', 'caption')
        self._custom_details_input = QPlainTextEdit(builder_controls)
        self._custom_details_input.setPlaceholderText('Main text / supports longer content')
        self._custom_details_input.setFixedHeight(84)

        meta_caption = QLabel('Footer', builder_controls)
        meta_caption.setProperty('role', 'caption')
        self._custom_meta_input = LineEdit(builder_controls)
        self._custom_meta_input.setPlaceholderText('Third line / small meta label')

        color_caption = QLabel('Color', builder_controls)
        color_caption.setProperty('role', 'caption')
        color_row = QWidget(builder_controls)
        color_row_layout = hbox(color_row, spacing=S.sm)
        color_row_layout.setContentsMargins(0, 0, 0, 0)
        self._custom_color_preview = QFrame(color_row)
        self._custom_color_preview.setObjectName('CustomCardColorSwatch')
        self._custom_color_preview.setFixedSize(34, 34)
        self._custom_color_hex = QLabel(color_row)
        self._custom_color_hex.setProperty('role', 'caption')
        choose_color_button = Button('Choose color', SECONDARY_BUTTON, color_row)
        choose_color_button.clicked.connect(self._pick_custom_card_color)
        color_row_layout.addWidget(self._custom_color_preview, 0)
        color_row_layout.addWidget(self._custom_color_hex, 0)
        color_row_layout.addWidget(choose_color_button, 0)
        color_row_layout.addStretch(1)

        form_grid.addWidget(title_caption, 0, 0)
        form_grid.addWidget(self._custom_title_input, 0, 1)
        form_grid.addWidget(details_caption, 1, 0)
        form_grid.addWidget(self._custom_details_input, 1, 1)
        form_grid.addWidget(meta_caption, 2, 0)
        form_grid.addWidget(self._custom_meta_input, 2, 1)
        form_grid.addWidget(color_caption, 3, 0)
        form_grid.addWidget(color_row, 3, 1)
        form_grid.setColumnStretch(1, 1)
        builder_controls_layout.addLayout(form_grid)

        builder_actions = hbox(spacing=S.md)
        add_custom_button = Button('Add custom card', ACCENT_BUTTON, builder_controls)
        remove_custom_button = Button('Remove selected', SECONDARY_BUTTON, builder_controls)
        clear_custom_button = Button('Clear stack', SURFACE_BUTTON, builder_controls)
        add_custom_button.clicked.connect(self._add_custom_card)
        remove_custom_button.clicked.connect(self._remove_selected_custom_card)
        clear_custom_button.clicked.connect(self._clear_custom_stack)
        builder_actions.addWidget(add_custom_button, 0)
        builder_actions.addWidget(remove_custom_button, 0)
        builder_actions.addWidget(clear_custom_button, 0)
        builder_actions.addStretch(1)
        builder_controls_layout.addLayout(builder_actions)

        self._custom_stack = self._create_route_list(
            builder_shell,
            max_visible_items=5,
            min_visible_items=5,
            empty_placeholder_text='Custom cards will appear here.',
        )
        self._custom_stack.addItem(
            _make_route_card_item(
                'Ocean surface',
                'Custom background example',
                'Theme-aware contrast',
                background='#3168D8',
                border='#8BB3FF',
                text_color='#F4F8FF',
            )
        )
        self._custom_stack.addItem(
            _make_route_card_item(
                'Warm accent',
                'Lighter card preset',
                'Editable + removable',
                background='#F2C168',
                border='#B97B18',
                text_color='#1B2430',
            )
        )
        self._custom_stack.setCurrentRow(0)

        builder_shell_layout.addWidget(builder_controls, 0, 0)
        builder_shell_layout.addWidget(self._custom_stack, 0, 1)
        builder_shell_layout.setColumnStretch(1, 1)
        builder_shell_layout.setAlignment(builder_controls, Qt.AlignmentFlag.AlignTop)
        builder_layout.addWidget(builder_shell)

        layout.addWidget(table_card)
        layout.addWidget(matrix_card)
        layout.addWidget(cards_card)
        layout.addWidget(transfer_card)
        layout.addWidget(tile_card)
        layout.addWidget(board_card)
        layout.addWidget(dense_tile_card)
        layout.addWidget(adaptive_card)
        layout.addWidget(quick_card)
        layout.addWidget(builder_card)
        layout.addStretch(1)
        self._apply_table_palette()
        self._update_custom_color_preview()

    def refresh_theme(self) -> None:
        self._apply_table_palette()
        for widget in self._route_lists:
            widget.refresh_theme()
        for widget in self._tile_lists:
            widget.refresh_theme()
        self._update_custom_color_preview()

    def _create_route_list(
        self,
        parent: QWidget,
        *,
        max_visible_items: int,
        min_visible_items: int | None = None,
        external_drop_enabled: bool = False,
        empty_placeholder_text: str = '',
        drag_group: str | None = None,
    ) -> ReorderableListWidget:
        list_widget = ReorderableListWidget(parent)
        list_widget.setObjectName('PointsList')
        list_widget.apply_drag_config(
            DragListConfig.rows(
                max_visible_items=max_visible_items,
                min_visible_items=max_visible_items if min_visible_items is None else min_visible_items,
                row_height=L.route_item_height,
                external_drop_enabled=external_drop_enabled,
                viewport_padding=L.points_frame_padding,
                empty_placeholder_text=empty_placeholder_text,
                drag_group=drag_group,
            )
        )
        self._route_lists.append(list_widget)
        return list_widget

    def _create_route_column(
        self,
        parent: QWidget,
        title: str,
        items: tuple[tuple[str, str, str], ...],
        *,
        drag_group: str | None = None,
        max_visible_items: int = 4,
        min_visible_items: int | None = None,
        empty_placeholder_text: str = '',
    ) -> tuple[QWidget, ReorderableListWidget]:
        column = QWidget(parent)
        column.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        column_layout = vbox(column, spacing=S.sm)
        column_layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(title, column)
        caption.setProperty('role', 'caption')
        list_widget = self._create_route_list(
            column,
            max_visible_items=max_visible_items,
            min_visible_items=min_visible_items,
            external_drop_enabled=drag_group is not None,
            empty_placeholder_text=empty_placeholder_text,
            drag_group=drag_group,
        )
        for role, coords, action in items:
            list_widget.addItem(_make_route_card_item(role, coords, action))
        column_layout.addWidget(caption)
        column_layout.addWidget(list_widget)
        return column, list_widget

    def _create_tile_list(
        self,
        parent: QWidget,
        *,
        max_visible_rows: int,
        min_visible_rows: int | None = None,
        grid_columns: int,
        item_extent: int | None = None,
        empty_placeholder_text: str = '',
        highlight_drop_target: bool = True,
        compact_grid_width: bool = False,
    ) -> TileReorderableListWidget:
        tile_list = TileReorderableListWidget(parent)
        tile_list.setObjectName('PointsList')
        tile_list.apply_drag_config(
            DragListConfig.grid(
                max_visible_rows=max_visible_rows,
                min_visible_rows=max_visible_rows if min_visible_rows is None else min_visible_rows,
                item_extent=item_extent or L.tile_item_size,
                grid_columns=grid_columns,
                viewport_padding=L.points_frame_padding,
                empty_placeholder_text=empty_placeholder_text,
                highlight_drop_target=highlight_drop_target,
                compact_grid_width=compact_grid_width,
            )
        )
        self._tile_lists.append(tile_list)
        return tile_list

    def _append_quick_card(self) -> None:
        index = self._quick_card_counter
        self._quick_card_counter += 1
        self._quick_stack.addItem(
            _make_route_card_item(
                f'Generated card {index}',
                f'Queue slot #{index:02d}',
                'Added from demo button',
            )
        )
        self._quick_stack.setCurrentRow(self._quick_stack.count() - 1)

    def _remove_selected_quick_card(self) -> None:
        self._remove_selected_card(self._quick_stack)

    def _clear_quick_stack(self) -> None:
        self._clear_route_list(self._quick_stack)

    def _pick_custom_card_color(self) -> None:
        color = QColorDialog.getColor(self._custom_card_color, self, 'Choose card color')
        if not color.isValid():
            return
        self._custom_card_color = color
        self._update_custom_color_preview()

    def _update_custom_color_preview(self) -> None:
        if not hasattr(self, '_custom_color_preview'):
            return
        background = self._custom_card_color.name().upper()
        border = _card_border_color(self._custom_card_color)
        self._custom_color_preview.setStyleSheet(
            f"""
            QFrame#CustomCardColorSwatch {{
                background: {background};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            """
        )
        self._custom_color_hex.setText(background)

    def _add_custom_card(self) -> None:
        index = self._custom_card_counter
        self._custom_card_counter += 1
        title = self._custom_title_input.text().strip() or f'Custom card {index}'
        details = self._custom_details_input.toPlainText().strip() or 'Editable second line'
        meta = self._custom_meta_input.text().strip() or 'Added from the builder'
        background = self._custom_card_color.name()
        self._custom_stack.addItem(
            _make_route_card_item(
                title,
                details,
                meta,
                background=background,
                border=_card_border_color(self._custom_card_color),
                text_color=_card_text_color(self._custom_card_color),
                auto_height=True,
            )
        )
        self._custom_stack.setCurrentRow(self._custom_stack.count() - 1)
        self._custom_title_input.clear()
        self._custom_details_input.clear()
        self._custom_meta_input.clear()

    def _remove_selected_custom_card(self) -> None:
        self._remove_selected_card(self._custom_stack)

    def _clear_custom_stack(self) -> None:
        self._clear_route_list(self._custom_stack)

    def _remove_selected_card(self, list_widget: ReorderableListWidget) -> None:
        if list_widget.count() <= 0:
            return
        index = list_widget.currentRow()
        if index < 0:
            index = list_widget.count() - 1
        removed = list_widget.takeItem(index)
        if removed is None:
            return
        if list_widget.count() > 0:
            list_widget.setCurrentRow(min(index, list_widget.count() - 1))

    def _clear_route_list(self, list_widget: ReorderableListWidget) -> None:
        while list_widget.count() > 0:
            list_widget.takeItem(list_widget.count() - 1)
        list_widget.clearSelection()

    def _table_color(self, key: str) -> str:
        runtime = get_ui_runtime_state()
        return self._recommended_table_palette(runtime.theme_mode)[key]

    def _recommended_table_palette(self, mode: str) -> dict[str, str]:
        return dict(table_palette_for_theme(mode))

    def _apply_table_palette(self) -> None:
        palette_keys = tuple(table_palette_for_theme().keys())
        palette = {key: self._table_color(key) for key in palette_keys}
        for table in self._table_widgets:
            table.set_color_overrides(palette)


class MarkdownCategoryPage(BaseWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)

        self._markdown_showcase = '''
# H1 — Primary heading

Reference paragraph with **bold**, *italic*, ***bold italic***, ~~strikethrough~~ and `inline code`.

## H2 — Section heading

A second paragraph can contain practical guidance, short notes and emphasis without becoming visually noisy.

### H3 — Subsection heading

#### H4 — Component heading

##### H5 — Minor heading

---

## Lists

- Compact item A
- Compact item B
    - Nested item B.1
    - Nested item B.2
        - Nested item B.2.a
- Compact item C

1. Ordered step one
2. Ordered step two
3. Ordered step three

- [x] Completed task
- [ ] Pending task

## Quotes

> Hey, everyone! This is the example of the qoute blocks in markdown. It's available to make single quote blocks or nested qoute blocks if you need it.

> Markdown is a lightweight markup language used to format plain text using simple, readable syntax. Instead of complex HTML tags, it uses symbols like `#` for headings, `**` for bold text, `*` for italics, and `-` or `*` for lists. The idea is that the text remains easy to read in its raw form, while a parser can convert it into structured HTML or other formats for display. Markdown is widely used in documentation, README files, and note-taking apps because it balances simplicity with enough power to create well-structured content.

> I agree with that, because without proper contrast and harmony, even a well-designed interface can become confusing or hard to use, especially for people with visual impairments.
>> In app design, effective color combinations follow principles like contrast, harmony, and accessibility to ensure the interface is both visually appealing and easy to use.

---

## Table

| Component | Status | Notes |
| --- | --- | --- |
| Buttons | Ready | Hover + pressed states |
| Inputs | Ready | Theme-aware styling |
| Markdown | Enhanced | Better spacing and typography |
'''

        markdown_card, markdown_layout = create_section(
            self,
            'Markdown rendering',
            'Headings, paragraphs, nested lists, quotes and tables rendered with the same design system.',
        )
        self._markdown_preview = MarkdownShowcaseWidget(self._markdown_showcase, markdown_card)
        markdown_layout.addWidget(self._markdown_preview)

        source_card, source_layout = create_section(
            self,
            'Markdown source (raw)',
            'The exact markdown input used for the rendered preview above.',
        )
        self._source_view = QPlainTextEdit(source_card)
        self._source_view.setReadOnly(True)
        self._source_view.setPlainText(self._markdown_showcase.strip())
        self._source_view.setMinimumHeight(220)
        source_layout.addWidget(self._source_view)

        code_card, code_layout = create_section(
            self,
            'Native code blocks (UI kit widget)',
            'Fast syntax highlighting without markdown dependency. Unknown languages use fallback.',
        )

        fallback_row = hbox(spacing=S.md)
        fallback_caption = QLabel('Unknown language fallback', code_card)
        fallback_caption.setProperty('role', 'caption')
        self._fallback_combo = ComboBox(code_card)
        self._fallback_combo.addItem('YAML', 'yaml')
        self._fallback_combo.addItem('Bash', 'bash')
        fallback_row.addWidget(fallback_caption)
        fallback_row.addWidget(self._fallback_combo)
        fallback_row.addStretch(1)

        self._python_block = CodeBlock(
            """from dataclasses import dataclass\n\n@dataclass(slots=True)\nclass User:\n    name: str\n    score: int\n\n\ndef top_users(items: list[User]) -> list[User]:\n    return sorted(items, key=lambda item: item.score, reverse=True)[:5]\n""",
            language='python',
            title='Python example',
            parent=code_card,
        )

        self._php_block = CodeBlock(
            """<?php\n\nclass UserService {\n    public function topUsers(array $items): array {\n        usort($items, fn($a, $b) => $b['score'] <=> $a['score']);\n        return array_slice($items, 0, 5);\n    }\n}\n""",
            language='php',
            title='PHP example',
            parent=code_card,
        )

        self._unknown_block = CodeBlock(
            """app_name: somevar-ui\nrelease_channel: nightly\nflags:\n  - smooth_ui\n  - debug_overlay\n""",
            language='toml',
            fallback_language='yaml',
            title='Unknown language example (toml -> fallback)',
            parent=code_card,
        )

        self._fallback_combo.currentIndexChanged.connect(self._update_code_fallback)

        code_layout.addLayout(fallback_row)
        code_layout.addWidget(self._python_block)
        code_layout.addWidget(self._php_block)
        code_layout.addWidget(self._unknown_block)

        collapse_card, collapse_layout = create_section(
            self,
            'Expandable panels',
            'Bottom tongue toggles hidden content while preserving spacing rhythm.',
        )
        collapse = CollapsibleSection('Actions', collapse_card)
        details = vbox(spacing=S.sm)
        details.addWidget(QLabel('Left click / Right click / Middle click / Hold / Release / Wheel.'))
        details.addWidget(QLabel('Use this panel to validate animation smoothness and content clipping.'))
        collapse.setContentLayout(details)
        collapse_layout.addWidget(collapse)

        layout.addWidget(markdown_card)
        layout.addWidget(source_card)
        layout.addWidget(code_card)
        layout.addWidget(collapse_card)
        layout.addStretch(1)

    def _update_code_fallback(self, _index: int = 0) -> None:
        fallback = str(self._fallback_combo.currentData() or 'yaml')
        self._unknown_block.set_fallback_language(fallback)

    def refresh_theme(self) -> None:
        self._markdown_preview.refresh_theme()

class LoadingCategoryPage(BaseWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)

        self._request_running = False
        self._request_timer = QTimer(self)
        self._request_timer.setInterval(45)
        self._request_timer.timeout.connect(self._tick_request)
        self._upload_running = False
        self._upload_timer = QTimer(self)
        self._upload_timer.setInterval(50)
        self._upload_timer.timeout.connect(self._tick_upload)

        progress_card, progress_layout = create_section(
            self,
            'Progress and long operations',
            'Demo for determinate and indeterminate progress during long-running tasks.',
        )
        self.progress = ProgressBar(progress_card)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        progress_row = hbox(spacing=S.md)
        self.progress_value = QLabel('0%', progress_card)
        self.progress_value.setProperty('role', 'subsection')
        self.progress_value.setFixedWidth(L.percent_value_width)
        self.start_button = Button('Simulate API request', ACCENT_BUTTON, progress_card)
        self.reset_button = Button('Reset', SECONDARY_BUTTON, progress_card)
        self.start_button.clicked.connect(self.start_request)
        self.reset_button.clicked.connect(self.reset_request)
        progress_row.addWidget(self.start_button)
        progress_row.addWidget(self.reset_button)
        progress_row.addStretch(1)
        progress_row.addWidget(self.progress_value)

        self.auto_mode = CheckBox('Indeterminate mode', progress_card)
        self.auto_mode.toggled.connect(self._toggle_indeterminate)

        self.status = QLabel('Ready to run.', progress_card)
        self.status.setProperty('role', 'muted')
        self.status.setWordWrap(True)

        progress_layout.addWidget(self.progress)
        progress_layout.addLayout(progress_row)
        progress_layout.addWidget(self.auto_mode)
        progress_layout.addWidget(self.status)

        drop_card, drop_layout = create_section(
            self,
            'File drop zone',
            'Drop files to test drag-and-drop interactions and upload previews.',
        )
        self.drop_zone = FileDropZone(drop_card)
        self.drop_zone.filesChanged.connect(self._on_files_changed)
        self.drop_zone.filesDropped.connect(self._on_files_dropped)
        self.drop_progress = ProgressBar(drop_card)
        self.drop_progress.setRange(0, 100)
        self.drop_progress.setValue(0)
        drop_progress_row = hbox(spacing=S.md)
        self.drop_progress_value = QLabel('0%', drop_card)
        self.drop_progress_value.setProperty('role', 'subsection')
        self.drop_progress_value.setFixedWidth(L.percent_value_width)
        drop_progress_row.addWidget(self.drop_progress, 1)
        drop_progress_row.addWidget(self.drop_progress_value)

        self.drop_start_button = Button('Start upload simulation', ACCENT_BUTTON, drop_card)
        self.drop_reset_button = Button('Reset upload', SECONDARY_BUTTON, drop_card)
        self.drop_start_button.clicked.connect(self._start_upload_simulation)
        self.drop_reset_button.clicked.connect(self._reset_upload_simulation)
        drop_controls_row = hbox(spacing=S.md)
        drop_controls_row.addWidget(self.drop_start_button)
        drop_controls_row.addWidget(self.drop_reset_button)
        drop_controls_row.addStretch(1)

        self.drop_status = QLabel('Drop files to begin.', drop_card)
        self.drop_status.setProperty('role', 'muted')
        self.drop_status.setWordWrap(True)
        drop_layout.addWidget(self.drop_zone)
        drop_layout.addLayout(drop_progress_row)
        drop_layout.addLayout(drop_controls_row)
        drop_layout.addWidget(self.drop_status)
        self.drop_start_button.setEnabled(False)

        layout.addWidget(progress_card)
        layout.addWidget(drop_card)
        layout.addStretch(1)

    def _toggle_indeterminate(self, checked: bool) -> None:
        self.progress.setIndeterminate(checked)
        if checked:
            self.progress_value.setText('Auto')
            self.status.setText('Indeterminate mode enabled.')
            return
        self.progress_value.setText(f'{self.progress.value()}%')
        self.status.setText('Determinate mode enabled.')

    def _on_files_changed(self, files: list[str]) -> None:
        if not files:
            self._reset_upload_simulation()
            self.drop_start_button.setEnabled(False)
            self.drop_status.setText('Drop files to begin.')
            return
        noun = 'file' if len(files) == 1 else 'files'
        self.drop_status.setText(f'{len(files)} {noun} selected.')
        if not self._upload_running:
            self.drop_start_button.setEnabled(True)

    def _on_files_dropped(self, files: list[str]) -> None:
        if files:
            self.drop_status.setText(f'{len(files)} files dropped. Ready for upload simulation.')
            if not self._upload_running:
                self.drop_start_button.setEnabled(True)

    def start_request(self) -> None:
        if self._request_running:
            return
        self._request_running = True
        self.status.setText('Request in progress...')
        if not self.auto_mode.isChecked():
            self.progress.setValue(0)
            self.progress_value.setText('0%')
        self.start_button.setEnabled(False)
        self._request_timer.start()

    def reset_request(self) -> None:
        self._request_running = False
        self._request_timer.stop()
        self.progress.setIndeterminate(False)
        self.auto_mode.blockSignals(True)
        self.auto_mode.setChecked(False)
        self.auto_mode.blockSignals(False)
        self.progress.setValue(0)
        self.progress_value.setText('0%')
        self.status.setText('Ready to run.')
        self.start_button.setEnabled(True)

    def _tick_request(self) -> None:
        if self.auto_mode.isChecked():
            self.status.setText('Request in progress (indeterminate)...')
            return
        value = min(100, self.progress.value() + 5)
        self.progress.setValue(value)
        self.progress_value.setText(f'{value}%')
        if value < 100:
            return
        self._request_timer.stop()
        self._request_running = False
        self.start_button.setEnabled(True)
        self.status.setText('Request finished.')

    def _start_upload_simulation(self) -> None:
        if self._upload_running or not self.drop_zone.files():
            return
        self._upload_running = True
        self.drop_start_button.setEnabled(False)
        self.drop_progress.setIndeterminate(False)
        self.drop_progress.setValue(0)
        self.drop_progress_value.setText('0%')
        self.drop_status.setText('Uploading files...')
        self._upload_timer.start()

    def _reset_upload_simulation(self) -> None:
        self._upload_timer.stop()
        self._upload_running = False
        self.drop_progress.setIndeterminate(False)
        self.drop_progress.setValue(0)
        self.drop_progress_value.setText('0%')
        has_files = bool(self.drop_zone.files())
        self.drop_start_button.setEnabled(has_files)
        if has_files:
            self.drop_status.setText('Files selected. Ready for upload simulation.')
        else:
            self.drop_status.setText('Drop files to begin.')

    def _tick_upload(self) -> None:
        value = min(100, self.drop_progress.value() + 6)
        self.drop_progress.setValue(value)
        self.drop_progress_value.setText(f'{value}%')
        if value < 100:
            return
        self._upload_timer.stop()
        self._upload_running = False
        self.drop_status.setText('Upload simulation finished.')
        self.drop_start_button.setEnabled(bool(self.drop_zone.files()))


class StandaloneDemoWindow(QMainWindow):
    RESIZE_MARGIN = 4

    def __init__(self, parent: QWidget | None = None, *, window_mode: str = 'tool') -> None:
        super().__init__(parent)
        self._window_frame_controller: WindowFrameController | None = None
        self._window_mode = 'full' if str(window_mode).lower() == 'full' else 'tool'
        self.setWindowTitle('Standalone Playground Window')
        if self._window_mode == 'full':
            self.setWindowFlags(
                Qt.WindowType.Window
                | Qt.WindowType.WindowMinimizeButtonHint
                | Qt.WindowType.WindowMaximizeButtonHint
                | Qt.WindowType.WindowCloseButtonHint
            )
        else:
            self.setWindowFlags(
                Qt.WindowType.Window
                | Qt.WindowType.WindowCloseButtonHint
            )
        self.resize(620, 420)
        self.setMinimumSize(520, 340)

        root = QWidget(self)
        root.setObjectName('WindowRoot')
        root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._root_layout = QVBoxLayout(root)
        self._root_layout.setContentsMargins(
            L.window_frame_margin,
            L.window_frame_margin,
            L.window_frame_margin,
            L.window_frame_margin,
        )
        self._root_layout.setSpacing(0)

        self._surface = QFrame(root)
        self._surface.setObjectName('WindowSurface')
        surface_layout = QVBoxLayout(self._surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)

        self.title_bar = TitleBar('Standalone Playground Window', self._surface)
        self.title_bar.set_menu_button_visible(False)
        self.title_bar.set_window_controls(
            minimize=self._window_mode == 'full',
            maximize=self._window_mode == 'full',
            close=True,
        )

        body = QWidget(self._surface)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)
        body_layout.setSpacing(S.lg)

        hero = QLabel('Standalone window demo', body)
        hero.setProperty('role', 'hero')
        desc = QLabel(
            'Use this as a template when you need a separate top-level utility window '
            'that still shares the SomeVar UI Kit visual system.',
            body,
        )
        desc.setProperty('role', 'muted')
        desc.setWordWrap(True)

        close_row = QHBoxLayout()
        close_row.setContentsMargins(0, 0, 0, 0)
        close_row.setSpacing(S.md)
        close_row.addStretch(1)

        close_button = Button('Close window', ACCENT_BUTTON, body)
        close_button.clicked.connect(self.close)
        close_row.addWidget(close_button)

        body_layout.addWidget(hero)
        body_layout.addWidget(desc)
        body_layout.addStretch(1)
        body_layout.addLayout(close_row)

        surface_layout.addWidget(self.title_bar)
        surface_layout.addWidget(body, 1)
        self._root_layout.addWidget(self._surface, 1)
        self.setCentralWidget(root)
        self._window_frame_controller = WindowFrameController(
            self,
            self._root_layout,
            (root, self._surface, self.title_bar),
        )

        self.apply_runtime_theme()
        self._update_window_frame()

    def apply_runtime_theme(self, mode: str | None = None) -> None:
        apply_theme(self, theme_mode=mode)

    def _update_window_frame(self, *, force: bool = False) -> None:
        controller = getattr(self, '_window_frame_controller', None)
        if controller is not None:
            controller.update(force=force)

    def changeEvent(self, event) -> None:  # type: ignore[override]
        super().changeEvent(event)
        controller = getattr(self, '_window_frame_controller', None)
        if controller is not None:
            controller.handle_change_event(event)

    def moveEvent(self, event) -> None:  # type: ignore[override]
        super().moveEvent(event)
        self._update_window_frame()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_window_frame()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._update_window_frame(force=True)

    def nativeEvent(self, event_type, message):  # type: ignore[override]
        handled = handle_windows_native_event(self, message, resize_margin=self.RESIZE_MARGIN)
        if handled is not None:
            return handled
        return super().nativeEvent(event_type, message)


class _StackRootPage(BaseWidget):
    open_next_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        title = QLabel('Step 1', self)
        title.setProperty('role', 'section')
        body = QLabel('This is the first page in modal stack flow.', self)
        body.setProperty('role', 'muted')
        body.setWordWrap(True)
        next_button = Button('Go to step 2', ACCENT_BUTTON, self)
        next_button.clicked.connect(self.open_next_requested.emit)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addStretch(1)
        layout.addWidget(next_button, 0, Qt.AlignmentFlag.AlignRight)


class _StackDetailPage(BaseWidget):
    def __init__(self, title_text: str, body_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=S.xl)
        layout = self.root_layout
        title = QLabel(title_text, self)
        title.setProperty('role', 'section')
        body = QLabel(body_text, self)
        body.setProperty('role', 'muted')
        body.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addStretch(1)


class StackFlowPanel(BaseWidget):
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, spacing=0)
        self.setProperty('modalOwnHeaderControls', True)
        self.setProperty('modalPreferredWidth', L.settings_panel_preferred_width)
        self.setProperty('modalPreferredHeight', L.settings_panel_preferred_height)

        self.stack = ModalStack('Modal chain demo', self)
        self.stack.close_requested.connect(self.cancelled.emit)

        root_page = _StackRootPage(self)
        root_page.open_next_requested.connect(self._open_next)
        self.stack.set_root('Modal chain demo', root_page)

        self.root_layout.addWidget(self.stack, 1)

    def _open_next(self) -> None:
        page_two = _StackDetailPage(
            'Step 2',
            'Content slides smoothly. Use the back arrow to return to the previous modal page.',
            self,
        )
        self.stack.push_page('Step 2', page_two)


def create_simple_message_panel() -> MessagePanel:
    panel = MessagePanel(
        'Simple modal demo',
        (
            'This is the minimal modal layout. Use it for short confirmations and '
            'single-action informational messages.'
        ),
    )
    panel.setProperty('modalPreferredWidth', L.message_modal_width)
    return panel


def create_settings_form_panel() -> SettingsFormPanel:
    panel = SettingsFormPanel(
        'Settings form demo',
        subtitle='Reusable modal content from SomeVar UI Kit.',
        preferred_width=L.settings_panel_preferred_width,
        preferred_height=L.settings_panel_preferred_height,
    )

    profile = panel.add_section(
        'Profile',
        description='Common text fields and selectors arranged with the shared settings layout.',
    )
    name_input = LineEdit(profile)
    name_input.setPlaceholderText('Type profile name')
    profile.add_field('Profile name', name_input)

    language_combo = ComboBox(profile)
    for country in country_names()[:8]:
        language_combo.addItem(country, country)
    profile.add_field('Default region', language_combo)

    behavior = panel.add_section('Behavior')
    theme_combo = ComboBox(behavior)
    theme_combo.addItem('Dark', 'dark')
    theme_combo.addItem('Light', 'light')
    behavior.add_field('Theme', theme_combo)

    reduce_motion = Switch(behavior)
    reduce_motion.setChecked(False)
    behavior.add_toggle(
        'Reduce animation motion',
        reduce_motion,
        description='Useful for accessibility and long-running operational tools.',
    )

    return panel


def _wrap_page(parent: QWidget, page: QWidget) -> QScrollArea:
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(page)
    return scroll


def build_playground_categories(parent: QWidget) -> tuple[list[PlaygroundCategory], QStackedWidget]:
    stack = QStackedWidget(parent)

    modal_page = ModalCategoryPage(parent)
    controls_page = ControlsCategoryPage(parent)
    charts_page = ChartsCategoryPage(parent)
    icons_page = IconsCategoryPage(parent)
    data_page = ListsCategoryPage(parent)
    markdown_page = MarkdownCategoryPage(parent)
    loading_page = LoadingCategoryPage(parent)

    pages: list[PlaygroundCategory] = [
        PlaygroundCategory(
            category_id='modals',
            title='Modal windows',
            description='Simple modal, modal chain, settings form and standalone top-level window examples.',
            demo_count=4,
            page=modal_page,
        ),
        PlaygroundCategory(
            category_id='controls',
            title='Inputs and controls',
            description='Text fields, selectors, checkboxes, radios, switches and sliders.',
            demo_count=7,
            page=controls_page,
        ),
        PlaygroundCategory(
            category_id='charts',
            title='Charts and graphs',
            description='Animated plots, resource timelines and comparison diagrams.',
            demo_count=5,
            page=charts_page,
        ),
        PlaygroundCategory(
            category_id='icons',
            title='Icons',
            description='Vector icon catalog, semantic aliases and icon button examples.',
            demo_count=2,
            page=icons_page,
        ),
        PlaygroundCategory(
            category_id='data',
            title='Lists and tables',
            description='Interactive tables and drag-and-drop card lists.',
            demo_count=10,
            page=data_page,
        ),
        PlaygroundCategory(
            category_id='markdown',
            title='Markdown and panels',
            description='Formatted markdown, code blocks and expandable sections.',
            demo_count=2,
            page=markdown_page,
        ),
        PlaygroundCategory(
            category_id='loading',
            title='Loading and async states',
            description='Progress bars, long-task simulation and drag-and-drop upload zone.',
            demo_count=2,
            page=loading_page,
        ),
    ]

    for category in pages:
        stack.addWidget(_wrap_page(parent, category.page))

    return pages, stack


__all__ = [
    'PlaygroundCategory',
    'ModalCategoryPage',
    'StackFlowPanel',
    'StandaloneDemoWindow',
    'build_playground_categories',
    'create_settings_form_panel',
    'create_simple_message_panel',
]
