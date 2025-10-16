"""Decode tool dialog for channel mapping in Voltcraft Studio"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QWidget, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from typing import Dict, Optional


class DecodeDialog(QDialog):
    """Dialog for mapping channels to signal types (SK, CS, DI, DO)"""
    
    SIGNAL_TYPES = ["None", "SK", "CS", "DI", "DO"]
    
    def __init__(self, channels: list, parent=None, icon: Optional[QIcon] = None):
        super().__init__(parent)
        self.channels = channels
        self.mapping: Dict[str, str] = {}
        
        self.setWindowTitle("Channel Decoder - Signal Type Mapping")
        if icon:
            self.setWindowIcon(icon)
        
        self.setGeometry(100, 100, 500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 11pt;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px;
                font-size: 11pt;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #3d3d3d;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #5a7fa8;
                border: 1px solid #444444;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11pt;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
                border: 1px solid #6d6d6d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
            QPushButton#decodeButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #FFD700, stop:1 #DAA520);
                color: #000000;
                border: 1px solid #B8860B;
            }
            QPushButton#decodeButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #FFE44D, stop:1 #FFD700);
            }
            QPushButton#decodeButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #DAA520, stop:1 #B8860B);
            }
        """)
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create and layout the dialog widgets"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # Title label
        title_label = QLabel("Map Channels to Signal Types")
        title_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #FFD700;")
        main_layout.addWidget(title_label)
        
        # Info label
        info_label = QLabel("Select the signal type for each channel:")
        info_label.setStyleSheet("color: #b0b0b0; font-size: 10pt; margin-bottom: 8px;")
        main_layout.addWidget(info_label)
        
        # Scroll area for channel mappings
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: 1px solid #444444;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6d6d6d;
            }
        """)
        scroll_area.setWidgetResizable(True)
        
        # Create container for channel mappings
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e1e;")
        grid_layout = QGridLayout(container)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(8, 8, 8, 8)
        
        # Create dropdown for each channel
        self.combo_boxes: Dict[str, QComboBox] = {}
        for idx, channel in enumerate(self.channels):
            # Channel name label
            channel_label = QLabel(f"{channel}:")
            channel_label.setStyleSheet("font-weight: bold; color: #FFD700;")
            grid_layout.addWidget(channel_label, idx, 0, alignment=Qt.AlignmentFlag.AlignRight)
            
            # Dropdown for signal type
            combo = QComboBox()
            combo.addItems(self.SIGNAL_TYPES)
            combo.setCurrentIndex(0)  # Default to "None"
            self.combo_boxes[channel] = combo
            grid_layout.addWidget(combo, idx, 1)
        
        # Add vertical stretch to push widgets to top
        grid_layout.setRowStretch(len(self.channels), 1)
        
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area, 1)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # Decode button
        decode_button = QPushButton("Decode")
        decode_button.setObjectName("decodeButton")
        decode_button.clicked.connect(self._on_decode)
        button_layout.addWidget(decode_button)
        
        main_layout.addLayout(button_layout)
    
    def _on_decode(self):
        """Handle decode button click"""
        # Build mapping from current dropdown values
        self.mapping = {}
        for channel, combo in self.combo_boxes.items():
            signal_type = combo.currentText()
            if signal_type != "None":
                self.mapping[channel] = signal_type
        
        # Print to terminal
        self._print_mapping_to_terminal()
        
        # Close dialog
        self.accept()
    
    def _print_mapping_to_terminal(self):
        """Print the channel mapping to terminal/console"""
        print("\n" + "="*60)
        print("CHANNEL DECODER - SIGNAL TYPE MAPPING")
        print("="*60)
        
        if not self.mapping:
            print("No channels mapped. All channels set to 'None'.")
        else:
            for channel, signal_type in sorted(self.mapping.items()):
                print(f"  {channel:<15} → {signal_type}")
        
        # Print summary
        signal_counts = {}
        for signal_type in self.mapping.values():
            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
        
        if signal_counts:
            print("\nSignal Type Summary:")
            for signal_type in sorted(signal_counts.keys()):
                count = signal_counts[signal_type]
                print(f"  {signal_type}: {count} channel(s)")
        
        print("="*60 + "\n")
    
    def get_mapping(self) -> Dict[str, str]:
        """Get the channel mapping"""
        return self.mapping
