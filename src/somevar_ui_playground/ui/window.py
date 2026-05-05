from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from somevar_ui_playground.ui.pages import (
    ModalCategoryPage,
    PlaygroundCategory,
    StackFlowPanel,
    StandaloneDemoWindow,
    build_playground_categories,
    create_simple_message_panel,
)
from somevar_ui.ui.bootstrap import apply_theme, refresh_theme_tree
from somevar_ui.ui.kit.containers import CenteredModalOverlay, MessagePanel, PageHeader
from somevar_ui.ui.kit.widgets import (
    ComboBox,
    PROJECT_COUNT_ROLE,
    PROJECT_TITLE_ROLE,
    ProjectItemDelegate,
    install_capsule_scrollbars,
)
from somevar_ui.ui.platform import windows as win_platform
from somevar_ui.ui.shell import TitleBar
from somevar_ui.ui.theme import THEME

S = THEME.spacing
L = THEME.layout


class PlaygroundWindow(QMainWindow):
    RESIZE_MARGIN = 4

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('SomeVar UI Playground')
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(max(L.window_default_width, 1180), max(L.window_default_height, 760))
        self.setMinimumSize(980, 700)

        self._window_frame_state: win_platform.WindowShellState | None = None
        self._modal_overlay: CenteredModalOverlay | None = None
        self._detached_windows: list[StandaloneDemoWindow] = []
        self._active_shell_menu: QMenu | None = None
        self._top_menu_visible = True
        self._sidebar_visible = True

        self._categories: list[PlaygroundCategory] = []
        self._category_stack = None
        self._modal_page: ModalCategoryPage | None = None

        self._build_ui()
        self._apply_theme('dark')
        self._update_window_frame()

    def _build_ui(self) -> None:
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

        self.title_bar = TitleBar('SomeVar UI Playground', self._surface)
        self.title_bar.set_menu_button_visible(True)
        self.title_bar.menu_requested.connect(self._open_shell_menu)
        self.top_menu_bar = self._build_top_menu_bar()

        body = QWidget(self._surface)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar_panel = self._build_sidebar(body)
        self.content_panel = self._build_content_panel(body)
        body_layout.addWidget(self.sidebar_panel, 0)
        body_layout.addWidget(self.content_panel, 1)

        surface_layout.addWidget(self.title_bar)
        surface_layout.addWidget(self.top_menu_bar)
        surface_layout.addWidget(body, 1)
        self._root_layout.addWidget(self._surface, 1)
        self.setCentralWidget(root)
        self._apply_shell_layout()

    def _build_sidebar(self, parent: QWidget) -> QWidget:
        sidebar = QFrame(parent)
        sidebar.setObjectName('SidebarPanel')
        sidebar.setFixedWidth(L.sidebar_width)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(
            L.sidebar_padding_x,
            L.sidebar_padding_top,
            L.sidebar_padding_x,
            L.sidebar_padding_bottom,
        )
        layout.setSpacing(S.xxl)

        title = QLabel('Playground', sidebar)
        title.setProperty('role', 'hero')
        subtitle = QLabel('Choose a category and interact with focused UI demos.', sidebar)
        subtitle.setProperty('role', 'muted')
        subtitle.setWordWrap(True)

        self.category_list = QListWidget(sidebar)
        self.category_list.setObjectName('ProjectList')
        self.category_list.setItemDelegate(ProjectItemDelegate(self.category_list))
        self.category_list.currentRowChanged.connect(self._on_category_changed)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.category_list, 1)

        return sidebar

    def _build_content_panel(self, parent: QWidget) -> QWidget:
        panel = QFrame(parent)
        panel.setObjectName('EditorPanel')

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            L.editor_content_padding_x,
            L.editor_content_padding_top,
            L.editor_content_padding_x,
            L.editor_content_padding_bottom,
        )
        layout.setSpacing(S.xl)

        self.page_header = PageHeader('UI Playground', badge_text='0 demos', parent=panel)

        theme_label = QLabel('Theme', panel)
        theme_label.setProperty('role', 'caption')
        self.theme_combo = ComboBox(panel)
        self.theme_combo.addItem('Dark', 'dark')
        self.theme_combo.addItem('Light', 'light')
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        self.theme_combo.setFixedWidth(150)

        theme_controls = QWidget(panel)
        theme_controls_layout = QHBoxLayout(theme_controls)
        theme_controls_layout.setContentsMargins(0, 0, 0, 0)
        theme_controls_layout.setSpacing(S.md)
        theme_controls_layout.addWidget(theme_label, 0, Qt.AlignmentFlag.AlignVCenter)
        theme_controls_layout.addWidget(self.theme_combo, 0, Qt.AlignmentFlag.AlignVCenter)
        self.page_header.set_action_widgets([theme_controls])

        self._categories, self._category_stack = build_playground_categories(panel)
        self._modal_page = self._find_modal_page()
        if self._modal_page is not None:
            self._modal_page.open_simple_modal_requested.connect(self._open_simple_modal)
            self._modal_page.open_modal_stack_requested.connect(self._open_stack_modal)
            self._modal_page.open_detached_window_requested.connect(self._open_detached_window)

        self._populate_category_list()

        layout.addWidget(self.page_header)
        layout.addWidget(self._category_stack, 1)
        return panel

    def _build_top_menu_bar(self) -> QWidget:
        bar = QFrame(self._surface)
        bar.setObjectName('TopMenuBar')
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(L.editor_content_padding_x, S.sm, L.editor_content_padding_x, S.sm)
        layout.setSpacing(S.sm)

        self.file_menu_button = QPushButton('File', bar)
        self.view_menu_button = QPushButton('View', bar)
        self.about_menu_button = QPushButton('About', bar)
        for button in (self.file_menu_button, self.view_menu_button, self.about_menu_button):
            button.setObjectName('TopMenuTrigger')
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.file_menu_button.clicked.connect(lambda: self._open_top_menu(self.file_menu_button, 'file'))
        self.view_menu_button.clicked.connect(lambda: self._open_top_menu(self.view_menu_button, 'view'))
        self.about_menu_button.clicked.connect(lambda: self._open_top_menu(self.about_menu_button, 'about'))

        layout.addWidget(self.file_menu_button)
        layout.addWidget(self.view_menu_button)
        layout.addWidget(self.about_menu_button)
        layout.addStretch(1)
        return bar

    def _prepare_top_popup_menu(self, menu: QMenu) -> None:
        menu.setObjectName('TopPopupMenu')
        menu.setGraphicsEffect(None)
        menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
        menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

    def _clear_active_shell_menu(self) -> None:
        self._active_shell_menu = None

    def _set_sidebar_visible(self, visible: bool) -> None:
        next_visible = bool(visible)
        if self._sidebar_visible == next_visible:
            return
        self._sidebar_visible = next_visible
        self._apply_shell_layout()

    def _set_top_menu_visible(self, visible: bool) -> None:
        next_visible = bool(visible)
        if self._top_menu_visible == next_visible:
            return
        self._top_menu_visible = next_visible
        self._apply_shell_layout()

    def _apply_shell_layout(self) -> None:
        self.top_menu_bar.setVisible(self._top_menu_visible)
        self.sidebar_panel.setVisible(self._sidebar_visible)
        layout = self._surface.layout()
        if layout is not None:
            layout.invalidate()
            layout.activate()

    def _open_top_menu(self, anchor: QPushButton, kind: str) -> None:
        menu = QMenu(self)
        self._prepare_top_popup_menu(menu)
        if kind == 'file':
            open_modal_action = menu.addAction('Open simple modal')
            open_modal_action.triggered.connect(self._open_simple_modal)
            menu.addSeparator()
            close_action = menu.addAction('Exit')
            close_action.triggered.connect(self.close)
        elif kind == 'view':
            sidebar_action = QAction('Show sidebar', menu)
            sidebar_action.setCheckable(True)
            sidebar_action.setChecked(self._sidebar_visible)
            sidebar_action.triggered.connect(lambda checked=False: self._set_sidebar_visible(bool(checked)))
            menu.addAction(sidebar_action)

            top_menu_action = QAction('Show top menu', menu)
            top_menu_action.setCheckable(True)
            top_menu_action.setChecked(self._top_menu_visible)
            top_menu_action.triggered.connect(lambda checked=False: self._set_top_menu_visible(bool(checked)))
            menu.addAction(top_menu_action)
        else:
            about_action = menu.addAction('About Playground')
            about_action.triggered.connect(self._show_about_panel)
            docs_action = menu.addAction('Open docs modal')
            docs_action.triggered.connect(self._open_simple_modal)

        self._active_shell_menu = menu
        menu.aboutToHide.connect(self._clear_active_shell_menu)
        menu.popup(anchor.mapToGlobal(QPoint(0, anchor.height() + 4)))

    def _open_shell_menu(self) -> None:
        menu = QMenu(self)
        self._prepare_top_popup_menu(menu)

        sidebar_action = QAction('Show sidebar', menu)
        sidebar_action.setCheckable(True)
        sidebar_action.setChecked(self._sidebar_visible)
        sidebar_action.triggered.connect(lambda checked=False: self._set_sidebar_visible(bool(checked)))
        menu.addAction(sidebar_action)

        top_menu_action = QAction('Show top menu', menu)
        top_menu_action.setCheckable(True)
        top_menu_action.setChecked(self._top_menu_visible)
        top_menu_action.triggered.connect(lambda checked=False: self._set_top_menu_visible(bool(checked)))
        menu.addAction(top_menu_action)

        menu.addSeparator()
        about_action = menu.addAction('About Playground')
        about_action.triggered.connect(self._show_about_panel)

        self._active_shell_menu = menu
        menu.aboutToHide.connect(self._clear_active_shell_menu)
        menu_button = self.title_bar.menu_button
        menu.popup(menu_button.mapToGlobal(QPoint(0, menu_button.height() + 4)))

    def _show_about_panel(self) -> None:
        if self._modal_overlay is not None:
            return
        overlay_parent = self.centralWidget() or self._surface
        panel = MessagePanel(
            'About SomeVar UI Playground',
            'Playground demonstrates reusable SomeVar UI Kit controls, modal stacks and shell toggles.',
            overlay_parent,
        )
        panel.dismissed.connect(self._close_active_modal)
        self._show_modal(panel, L.message_modal_width)

    def _find_modal_page(self) -> ModalCategoryPage | None:
        for category in self._categories:
            if isinstance(category.page, ModalCategoryPage):
                return category.page
        return None

    def _populate_category_list(self) -> None:
        self.category_list.clear()
        for category in self._categories:
            item = QListWidgetItem()
            item.setData(PROJECT_TITLE_ROLE, category.title)
            item.setData(PROJECT_COUNT_ROLE, str(category.demo_count))
            item.setSizeHint(QSize(0, L.project_item_height))
            self.category_list.addItem(item)
        if self._categories:
            self.category_list.setCurrentRow(0)

    def _on_category_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._categories):
            return
        category = self._categories[row]
        self._category_stack.setCurrentIndex(row)
        refresh_theme_tree(category.page)
        self.page_header.set_title(category.title)
        demos_word = 'demo' if category.demo_count == 1 else 'demos'
        self.page_header.set_badge_text(f'{category.demo_count} {demos_word}')
        self.page_header.set_subtitle(category.description)

    def _theme_changed(self) -> None:
        mode = str(self.theme_combo.currentData() or 'dark')
        self._apply_theme(mode)

    def _apply_theme(self, mode: str) -> None:
        normalized = apply_theme(self, theme_mode=mode)
        for detached_window in list(self._detached_windows):
            detached_window.apply_runtime_theme(normalized.theme_mode)

        index = self.theme_combo.findData(normalized.theme_mode)
        if index >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(index)
            self.theme_combo.blockSignals(False)

    def _open_simple_modal(self) -> None:
        panel = create_simple_message_panel()
        panel.dismissed.connect(self._close_active_modal)
        self._show_modal(panel, L.message_modal_width)

    def _open_stack_modal(self) -> None:
        overlay_parent = self.centralWidget() or self._surface
        panel = StackFlowPanel(overlay_parent)
        panel.cancelled.connect(self._close_active_modal)
        self._show_modal(panel, L.settings_modal_width)

    def _open_detached_window(self, mode: str = 'tool') -> None:
        window = StandaloneDemoWindow(window_mode=str(mode or 'tool'))
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._detached_windows.append(window)

        def _cleanup(*_args) -> None:
            self._detached_windows = [item for item in self._detached_windows if item is not window]

        window.destroyed.connect(_cleanup)
        window.show()
        window.raise_()
        window.activateWindow()

    def _show_modal(self, content: QWidget, preferred_width: int) -> None:
        if self._modal_overlay is not None:
            return
        overlay_parent = self.centralWidget() or self._surface
        overlay = CenteredModalOverlay(overlay_parent, content, preferred_width=preferred_width)
        install_capsule_scrollbars(content)
        install_capsule_scrollbars(overlay)
        overlay.closed.connect(self._active_modal_closed)
        self._modal_overlay = overlay
        overlay.open()

    def _close_active_modal(self) -> None:
        if self._modal_overlay is not None:
            self._modal_overlay.close_modal()

    def _active_modal_closed(self) -> None:
        self._modal_overlay = None

    def _refresh_widget_style(self, widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _apply_native_window_corners(self) -> None:
        win_platform.apply_window_corners(int(self.winId()), win_platform.resolve_window_shell_state(self))

    def _update_window_frame(self) -> None:
        shell_state = win_platform.resolve_window_shell_state(self)
        if self._window_frame_state == shell_state:
            return
        self._window_frame_state = shell_state

        margin = win_platform.frame_margin_for_shell_state(
            shell_state,
            normal=L.window_frame_margin,
            maximized=L.window_frame_margin_maximized,
        )
        self._root_layout.setContentsMargins(margin, margin, margin, margin)

        root = self.centralWidget()
        for widget in (root, self._surface, self.title_bar):
            if widget is None:
                continue
            win_platform.set_window_shell_state_properties(widget, shell_state)
            self._refresh_widget_style(widget)

        self._apply_native_window_corners()

    def changeEvent(self, event) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_window_frame()

    def moveEvent(self, event) -> None:  # type: ignore[override]
        super().moveEvent(event)
        self._update_window_frame()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_window_frame()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._update_window_frame()
        self._apply_native_window_corners()

    def nativeEvent(self, event_type, message):  # type: ignore[override]
        if not win_platform.IS_WIN32:
            return super().nativeEvent(event_type, message)

        msg = win_platform.native_message_from_pointer(message)
        if win_platform.is_nccalcsize_message(msg):
            return True, 0

        if msg is None or msg.message != win_platform.WM_NCHITTEST:
            return super().nativeEvent(event_type, message)

        if not win_platform.should_use_custom_resize_hit(self):
            return super().nativeEvent(event_type, message)

        hit = win_platform.resolve_resize_hit(self, self.cursor().pos(), self.RESIZE_MARGIN)
        if hit is not None:
            return True, hit
        return super().nativeEvent(event_type, message)
