"""Main window for Voltcraft Studio"""
from typing import List
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QToolBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from models import ChannelInfo
from parser import ChannelDataParser
from icons import IconFactory
from constants import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    TOOLBAR_ICON_SIZE, CHANNEL_PARAMETERS,
    FILE_DIALOG_TITLE, FILE_DIALOG_FILTER
)


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
        
        # Create table widget for channel info
        self.channel_table = QTableWidget()
        self.channel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.channel_table)
    
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
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    channels = ChannelDataParser.parse(content)
                    self.display_channel_info(channels)
                    self.setWindowTitle(f"{WINDOW_TITLE} - {file_path}")
            except Exception as e:
                # Show error in table
                self.channel_table.setRowCount(1)
                self.channel_table.setColumnCount(1)
                self.channel_table.setHorizontalHeaderLabels(['Error'])
                item = QTableWidgetItem(f"Error opening file: {str(e)}")
                self.channel_table.setItem(0, 0, item)

