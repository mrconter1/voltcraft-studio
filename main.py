import sys
from dataclasses import dataclass
from typing import List, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, 
    QPushButton, QVBoxLayout, QWidget, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QToolBar
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QAction, QPainterPath, QLinearGradient


@dataclass
class ChannelInfo:
    """Stores metadata for a single channel"""
    name: str
    frequency: str
    period: str
    pk_pk: str
    average: str
    vertical_pos: str
    probe_attenuation: str
    voltage_per_adc: str
    time_interval: str


class TextViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voltcraft Studio")
        self.setGeometry(100, 100, 800, 600)
        
        # Create and set a cute icon
        self.setWindowIcon(self.create_icon())
        
        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
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
        
        # Create open action with custom icon
        open_action = QAction(self.create_folder_icon(), "Open File", self)
        open_action.setToolTip("Open oscilloscope data file")
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create table widget for channel info
        self.channel_table = QTableWidget()
        self.channel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.channel_table)
    
    def create_icon(self):
        # Create a black circle with golden border and lightning bolt
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw black circle background
        painter.setBrush(QColor(0, 0, 0))  # Black
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        
        # Draw golden border
        pen = QPen(QColor(255, 215, 0), 4)  # Gold color, 4px width
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, 60, 60)
        
        # Draw lightning bolt emoji in the middle
        font = QFont("Segoe UI Emoji", 36)
        painter.setFont(font)
        painter.setPen(QColor(255, 215, 0))  # Gold color for bolt
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "⚡")
        
        painter.end()
        return QIcon(pixmap)
    
    def create_folder_icon(self):
        """Create a modern folder open icon"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw folder body
        folder_path = QPainterPath()
        folder_path.moveTo(12, 24)
        folder_path.lineTo(12, 52)
        folder_path.lineTo(52, 52)
        folder_path.lineTo(52, 24)
        folder_path.lineTo(12, 24)
        
        # Draw folder tab
        tab_path = QPainterPath()
        tab_path.moveTo(12, 24)
        tab_path.lineTo(12, 18)
        tab_path.lineTo(30, 18)
        tab_path.lineTo(32, 24)
        tab_path.lineTo(12, 24)
        
        # Fill folder with gradient
        gradient = QLinearGradient(0, 18, 0, 52)
        gradient.setColorAt(0, QColor(255, 215, 0))  # Gold
        gradient.setColorAt(1, QColor(218, 165, 32))  # Darker gold
        
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(180, 130, 0), 2))
        painter.drawPath(tab_path)
        painter.drawPath(folder_path)
        
        # Draw document lines inside
        painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
        painter.drawLine(20, 32, 44, 32)
        painter.drawLine(20, 38, 44, 38)
        painter.drawLine(20, 44, 36, 44)
        
        painter.end()
        return QIcon(pixmap)
    
    def parse_channel_info(self, content: str) -> List[ChannelInfo]:
        """Parse channel metadata from file content"""
        lines = content.split('\n')
        channels = []
        
        # Find channel names from first line
        first_line = lines[0]
        channel_names = [ch.strip() for ch in first_line.split(':')[1].split('\t') if ch.strip()]
        
        # Initialize channel data storage
        channel_data = {name: {} for name in channel_names}
        
        # Parse each metadata line
        for line in lines[1:]:
            if line.startswith('index'):
                break  # Stop at data section
            
            if ':' in line:
                parts = line.split(':')
                param_name = parts[0].strip()
                values = [v.strip() for v in parts[1].split('\t') if v.strip()]
                
                # Assign values to each channel
                for i, channel_name in enumerate(channel_names):
                    if i < len(values):
                        channel_data[channel_name][param_name] = values[i]
        
        # Create ChannelInfo objects
        for channel_name in channel_names:
            data = channel_data[channel_name]
            channel = ChannelInfo(
                name=channel_name,
                frequency=data.get('Frequency', '?'),
                period=data.get('Period', '?'),
                pk_pk=data.get('PK-PK', '?'),
                average=data.get('Average', '?'),
                vertical_pos=data.get('Vertical pos', '?'),
                probe_attenuation=data.get('Probe attenuation', '?'),
                voltage_per_adc=data.get('Voltage per ADC value', '?'),
                time_interval=data.get('Time interval', '?')
            )
            channels.append(channel)
        
        return channels
    
    def display_channel_info(self, channels: List[ChannelInfo]):
        """Display channel information in table"""
        if not channels:
            return
        
        # Define parameter labels
        params = [
            ('Frequency', 'frequency'),
            ('Period', 'period'),
            ('PK-PK', 'pk_pk'),
            ('Average', 'average'),
            ('Vertical pos', 'vertical_pos'),
            ('Probe attenuation', 'probe_attenuation'),
            ('Voltage per ADC value', 'voltage_per_adc'),
            ('Time interval', 'time_interval')
        ]
        
        # Set table dimensions
        self.channel_table.setRowCount(len(params))
        self.channel_table.setColumnCount(len(channels))
        
        # Set column headers (channel names)
        self.channel_table.setHorizontalHeaderLabels([ch.name for ch in channels])
        
        # Set row headers (parameter names)
        self.channel_table.setVerticalHeaderLabels([p[0] for p in params])
        
        # Fill table with data
        for row, (label, attr) in enumerate(params):
            for col, channel in enumerate(channels):
                value = getattr(channel, attr)
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.channel_table.setItem(row, col, item)
        
        # Adjust column widths
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    def open_file(self):
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Text File",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    channels = self.parse_channel_info(content)
                    self.display_channel_info(channels)
                    self.setWindowTitle(f"Voltcraft Studio - {file_path}")
            except Exception as e:
                # Show error in table
                self.channel_table.setRowCount(1)
                self.channel_table.setColumnCount(1)
                self.channel_table.setHorizontalHeaderLabels(['Error'])
                item = QTableWidgetItem(f"Error opening file: {str(e)}")
                self.channel_table.setItem(0, 0, item)


def main():
    app = QApplication(sys.argv)
    viewer = TextViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

