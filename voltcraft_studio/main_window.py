"""Main window for Voltcraft Studio"""
from typing import List, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QToolBar,
    QTabWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from .models import ChannelInfo, TimeSeriesData
from .icons import IconFactory
from .graph_widget import TimeSeriesGraphWidget
from .loader import FileLoaderThread
from .constants import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    TOOLBAR_ICON_SIZE, CHANNEL_PARAMETERS,
    FILE_DIALOG_TITLE, FILE_DIALOG_FILTER,
    HELP_DIALOG_TEXT
)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, initial_file: str = None):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Set window icon
        self.setWindowIcon(IconFactory.create_window_icon())
        
        # Create toolbar
        self._create_toolbar()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11pt;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
        """)
        
        # Tab 1: Waveform view (graph only - full screen)
        self.graph_widget = TimeSeriesGraphWidget()
        self.tab_widget.addTab(self.graph_widget, "📈 Waveform")
        
        # Tab 2: Channel info (metadata table)
        channel_info_widget = QWidget()
        channel_info_layout = QVBoxLayout(channel_info_widget)
        channel_info_layout.setContentsMargins(10, 10, 10, 10)
        
        self.channel_table = QTableWidget()
        self.channel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.channel_table.verticalHeader().setVisible(True)
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.channel_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.channel_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                color: #e0e0e0;
                font-size: 11pt;
                gridline-color: #444444;
                border: 1px solid #444444;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #404040;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #e0e0e0;
                padding: 10px;
                border: 1px solid #444444;
                font-weight: bold;
                font-size: 11pt;
            }
            QTableView QTableCornerButton::section {
                background-color: #1e1e1e;
                border: 1px solid #444444;
            }
        """)
        channel_info_layout.addWidget(self.channel_table)
        
        self.tab_widget.addTab(channel_info_widget, "📊 Channel Info")
        
        layout.addWidget(self.tab_widget)
        
        # Initialize loader thread
        self.loader_thread = None
        self.current_file_path = None
        
        # Tool state
        self.current_tool = "move"  # Default tool is move
        
        # Load initial file if provided
        if initial_file:
            self.current_file_path = initial_file
            self._load_file_with_progress(initial_file)
    
    def _create_toolbar(self):
        """Create and configure the main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(TOOLBAR_ICON_SIZE)
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #2d2d2d, stop:1 #1e1e1e);
                border-bottom: 1px solid #444444;
                spacing: 6px;
                padding: 4px;
            }
            QToolButton {
                background: #3d3d3d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
                color: #e0e0e0;
            }
            QToolButton:hover {
                background: #4d4d4d;
                border: 1px solid #6d6d6d;
            }
            QToolButton:pressed {
                background: #2d2d2d;
            }
            QToolButton:checked {
                background: transparent;
                border: 2px solid #5da3e8;
                color: #ffffff;
                font-weight: bold;
            }
            QToolButton:checked:hover {
                background: rgba(90, 160, 233, 0.2);
                border: 2px solid #6db3f8;
            }
        """)
        self.addToolBar(toolbar)
        
        # Create open action
        open_action = QAction(IconFactory.create_folder_icon(), "Open File", self)
        open_action.setToolTip("Open oscilloscope data file")
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        # Add separator
        toolbar.addSeparator()
        
        # Create move tool action
        self.move_action = QAction(IconFactory.create_move_icon(), "Move Tool", self)
        self.move_action.setToolTip("Pan and zoom the graph (default) [Shortcut: 1]")
        self.move_action.setCheckable(True)
        self.move_action.setChecked(True)  # Default tool
        self.move_action.setShortcut("1")
        self.move_action.triggered.connect(self.select_move_tool)
        toolbar.addAction(self.move_action)
        
        # Create tape measure tool action
        self.tape_action = QAction(IconFactory.create_tape_measure_icon(), "Tape Measure", self)
        self.tape_action.setToolTip("Measure time and voltage difference between two points [Shortcut: 2]")
        self.tape_action.setCheckable(True)
        self.tape_action.setShortcut("2")
        self.tape_action.triggered.connect(self.select_tape_tool)
        toolbar.addAction(self.tape_action)
        
        # Add separator
        toolbar.addSeparator()
        
        # Create help action
        help_action = QAction(IconFactory.create_help_icon(), "Help", self)
        help_action.setToolTip("Show controls and keyboard shortcuts")
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
    
    def display_channel_info(self, channels: List[ChannelInfo]):
        """Display channel information in table"""
        if not channels:
            return
        
        # Set table dimensions
        self.channel_table.setRowCount(len(CHANNEL_PARAMETERS))
        self.channel_table.setColumnCount(len(channels))
        
        # Set column headers (channel names)
        self.channel_table.setHorizontalHeaderLabels([ch.name for ch in channels])
        
        # Set row headers (parameter names)
        self.channel_table.setVerticalHeaderLabels([p[0] for p in CHANNEL_PARAMETERS])
        
        # Fill table with data
        for row, (label, attr) in enumerate(CHANNEL_PARAMETERS):
            for col, channel in enumerate(channels):
                value = getattr(channel, attr)
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.channel_table.setItem(row, col, item)
        
        # Resize to fit content
        self.channel_table.resizeColumnsToContents()
        self.channel_table.resizeRowsToContents()
    
    def open_file(self):
        """Open and parse an oscilloscope data file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            FILE_DIALOG_TITLE,
            "",
            FILE_DIALOG_FILTER
        )
        
        if file_path:
            self.current_file_path = file_path
            self._load_file_with_progress(file_path)
    
    def select_move_tool(self):
        """Select the move/pan tool"""
        self.current_tool = "move"
        self.move_action.setChecked(True)
        self.tape_action.setChecked(False)
        self.graph_widget.set_tool("move")
    
    def select_tape_tool(self):
        """Select the tape measure tool"""
        self.current_tool = "tape"
        self.move_action.setChecked(False)
        self.tape_action.setChecked(True)
        self.graph_widget.set_tool("tape")
    
    def show_help(self):
        """Show help dialog with controls and keyboard shortcuts"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Voltcraft Studio - Help")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(HELP_DIALOG_TEXT)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def _load_file_with_progress(self, file_path: str):
        """Load file in background with progress display"""
        # Show progress in graph widget
        self.graph_widget.set_loading_progress(0, "Starting...")
        
        # Create and start loader thread
        self.loader_thread = FileLoaderThread(file_path)
        self.loader_thread.progress.connect(self._update_progress)
        self.loader_thread.finished.connect(self._on_file_loaded)
        self.loader_thread.error.connect(self._on_load_error)
        self.loader_thread.start()
    
    def _update_progress(self, value: int, message: str):
        """Update progress display"""
        self.graph_widget.set_loading_progress(value, message)
    
    def _on_file_loaded(self, channels: List[ChannelInfo], time_series: TimeSeriesData):
        """Handle successful file load"""
        # Display channel info in table
        self.display_channel_info(channels)
        
        # Display time series in graph with metadata for proper axis scaling
        self.graph_widget.plot_data(time_series, channels)
        
        self.setWindowTitle(f"{WINDOW_TITLE} - {self.current_file_path}")
        
        # Hide progress bar
        self.graph_widget.hide_progress()
        
        # Clean up thread
        if self.loader_thread:
            self.loader_thread.deleteLater()
            self.loader_thread = None
    
    def _on_load_error(self, error_message: str):
        """Handle file load error"""
        # Hide progress bar and show error
        self.graph_widget.hide_progress()
        
        # Show error message box
        QMessageBox.critical(
            self,
            "Error Loading File",
            f"Failed to load file:\n\n{error_message}",
            QMessageBox.StandardButton.Ok
        )
        
        # Clean up thread
        if self.loader_thread:
            self.loader_thread.deleteLater()
            self.loader_thread = None

