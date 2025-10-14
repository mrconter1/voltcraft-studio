"""Main window for Voltcraft Studio"""
from typing import List, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QToolBar,
    QProgressDialog, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from models import ChannelInfo, TimeSeriesData
from parser import ChannelDataParser
from icons import IconFactory
from graph_widget import TimeSeriesGraphWidget
from constants import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    TOOLBAR_ICON_SIZE, CHANNEL_PARAMETERS,
    FILE_DIALOG_TITLE, FILE_DIALOG_FILTER
)


class FileLoaderThread(QThread):
    """Background thread for loading and parsing files"""
    finished = pyqtSignal(list, object)  # Emits (list of ChannelInfo, TimeSeriesData)
    error = pyqtSignal(str)  # Emits error message
    progress = pyqtSignal(int)  # Emits progress percentage
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        """Load and parse the file in background"""
        try:
            # Read file
            self.progress.emit(10)
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse content
            self.progress.emit(50)
            channels, time_series = ChannelDataParser.parse(content)
            
            self.progress.emit(100)
            self.finished.emit(channels, time_series)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
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
        
        # Create splitter to divide table and graph
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create table widget for channel info
        self.channel_table = QTableWidget()
        self.channel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        splitter.addWidget(self.channel_table)
        
        # Create graph widget for time series
        self.graph_widget = TimeSeriesGraphWidget()
        splitter.addWidget(self.graph_widget)
        
        # Set initial splitter sizes (30% table, 70% graph)
        splitter.setSizes([200, 400])
        
        layout.addWidget(splitter)
        
        # Initialize loader thread and progress dialog
        self.loader_thread = None
        self.progress_dialog = None
        self.current_file_path = None
    
    def _create_toolbar(self):
        """Create and configure the main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(TOOLBAR_ICON_SIZE)
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #f5f5f5, stop:1 #e0e0e0);
                border-bottom: 1px solid #cccccc;
                spacing: 6px;
                padding: 4px;
            }
            QToolButton {
                background: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background: #e3f2fd;
                border: 1px solid #2196f3;
            }
            QToolButton:pressed {
                background: #bbdefb;
            }
        """)
        self.addToolBar(toolbar)
        
        # Create open action
        open_action = QAction(IconFactory.create_folder_icon(), "Open File", self)
        open_action.setToolTip("Open oscilloscope data file")
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
    
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
        
        # Adjust column widths
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
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
    
    def _load_file_with_progress(self, file_path: str):
        """Load file in background with progress dialog"""
        # Create progress dialog
        self.progress_dialog = QProgressDialog(
            "Loading file...", 
            "Cancel", 
            0, 
            100, 
            self
        )
        self.progress_dialog.setWindowTitle("Opening File")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)  # Show immediately
        self.progress_dialog.canceled.connect(self._cancel_loading)
        
        # Create and start loader thread
        self.loader_thread = FileLoaderThread(file_path)
        self.loader_thread.progress.connect(self._update_progress)
        self.loader_thread.finished.connect(self._on_file_loaded)
        self.loader_thread.error.connect(self._on_load_error)
        self.loader_thread.start()
    
    def _update_progress(self, value: int):
        """Update progress dialog value"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
    
    def _on_file_loaded(self, channels: List[ChannelInfo], time_series: TimeSeriesData):
        """Handle successful file load"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # Display channel info in table
        self.display_channel_info(channels)
        
        # Display time series in graph
        self.graph_widget.plot_data(time_series)
        
        self.setWindowTitle(f"{WINDOW_TITLE} - {self.current_file_path}")
        
        # Clean up thread
        if self.loader_thread:
            self.loader_thread.deleteLater()
            self.loader_thread = None
    
    def _on_load_error(self, error_message: str):
        """Handle file load error"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # Show error in table
        self.channel_table.setRowCount(1)
        self.channel_table.setColumnCount(1)
        self.channel_table.setHorizontalHeaderLabels(['Error'])
        item = QTableWidgetItem(f"Error opening file: {error_message}")
        self.channel_table.setItem(0, 0, item)
        
        # Clean up thread
        if self.loader_thread:
            self.loader_thread.deleteLater()
            self.loader_thread = None
    
    def _cancel_loading(self):
        """Handle cancel button in progress dialog"""
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.terminate()
            self.loader_thread.wait()
            self.loader_thread.deleteLater()
            self.loader_thread = None

