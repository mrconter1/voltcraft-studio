"""Decode results display dialog for Voltcraft Studio"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QColor
from typing import Dict, List


class DecodeResultsDialog(QDialog):
    """Dialog for displaying NMC9307 decode results"""
    
    def __init__(self, decode_results: Dict, channel_mapping: Dict[str, str], 
                 time_interval_str: str, parent=None, icon=None):
        super().__init__(parent)
        self.decode_results = decode_results
        self.channel_mapping = channel_mapping
        self.time_interval_str = time_interval_str
        
        self.setWindowTitle("NMC9307 Protocol Decode Results")
        if icon:
            self.setWindowIcon(icon)
        
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 10pt;
            }
            QTreeWidget {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444444;
                font-size: 10pt;
                font-family: Courier;
            }
            QTreeWidget::item {
                padding: 2px;
            }
            QTreeWidget::item:selected {
                background-color: #5a7fa8;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #e0e0e0;
                padding: 4px;
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
        """)
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create dialog widgets"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # Title
        title_label = QLabel("📊 NMC9307 SERIAL DATA DECODE RESULTS")
        title_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #FFD700;")
        main_layout.addWidget(title_label)
        
        # Protocol info
        protocol_info = QLabel(
            "NMC9307 16-bit Serial EEPROM (National Semiconductor)\n"
            "Format: 1 dummy bit + 1 start bit + 4-bit opcode + 4-bit address + optional 16-bit data\n"
            "Reference: National Memory Databook (1990), NMC9307 Serial EEPROM specification"
        )
        protocol_info.setStyleSheet("color: #a0a0a0; font-size: 9pt; padding: 8px; background-color: #252525; border-radius: 4px;")
        main_layout.addWidget(protocol_info)
        
        # Configuration summary
        config_text = f"Time Interval: {self.time_interval_str}  |  "
        config_text += " | ".join([f"{ch}→{st}" for ch, st in sorted(self.channel_mapping.items())])
        config_label = QLabel(config_text)
        config_label.setStyleSheet("color: #b0b0b0; font-size: 9pt;")
        main_layout.addWidget(config_label)
        
        # Tree widget for transactions
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Transaction"])
        self.tree.setColumnCount(1)
        
        # Populate tree with transactions
        transactions = self.decode_results["transactions"]
        for tx_idx, tx in enumerate(transactions, 1):
            # Transaction item
            tx_item = QTreeWidgetItem()
            
            start_time = tx["start_time"]
            end_time = tx["end_time"]
            
            if tx["instruction"] and tx["instruction"]["valid"]:
                instr = tx["instruction"]
                instr_name = instr["instruction_name"]
                addr = instr["address"]
                tx_text = f"📌 TX {tx_idx}: {instr_name} (Addr: {addr}) | CS: {start_time:.1f}→{end_time:.1f}μs"
            else:
                tx_text = f"⚠️  TX {tx_idx}: INVALID | CS: {start_time:.1f}→{end_time:.1f}μs"
            
            tx_item.setText(0, tx_text)
            tx_item.setForeground(0, QColor("#FFD700"))
            self.tree.addTopLevelItem(tx_item)
            
            # DI data
            if tx["di_bits"]:
                di_item = QTreeWidgetItem(tx_item)
                di_sequence = tx["di_bits"]
                di_formatted = " ".join([di_sequence[i:i+8] for i in range(0, len(di_sequence), 8)])
                di_text = f"📥 DI: {di_formatted} ({len(tx['di_bits'])} bits)"
                di_item.setText(0, di_text)
                di_item.setForeground(0, QColor("#64C8FF"))
            
            # DO data
            if tx["do_bits"]:
                do_item = QTreeWidgetItem(tx_item)
                do_sequence = tx["do_bits"]
                
                # For READ, skip dummy bit and convert to decimal
                if tx["instruction"] and tx["instruction"]["valid"]:
                    if tx["instruction"]["instruction_name"] == "READ":
                        do_data = do_sequence[1:17] if len(do_sequence) > 1 else ""
                        do_formatted = " ".join([do_data[i:i+8] for i in range(0, len(do_data), 8)])
                        
                        # Convert to decimal
                        try:
                            do_decimal = int(do_data, 2)
                            do_hex = hex(do_decimal).upper()
                            do_text = f"📤 DO: {do_formatted} ({len(do_data)} bits - D15→D0) = {do_decimal} (0x{do_hex[2:]})"
                        except ValueError:
                            do_text = f"📤 DO: {do_formatted} ({len(do_data)} bits - D15→D0)"
                    else:
                        do_formatted = " ".join([do_sequence[i:i+8] for i in range(0, len(do_sequence), 8)])
                        do_text = f"📤 DO: {do_formatted} ({len(do_sequence)} bits)"
                else:
                    do_formatted = " ".join([do_sequence[i:i+8] for i in range(0, len(do_sequence), 8)])
                    do_text = f"📤 DO: {do_formatted} ({len(do_sequence)} bits)"
                
                do_item.setText(0, do_text)
                do_item.setForeground(0, QColor("#FF7064"))
        
        self.tree.expandAll()
        main_layout.addWidget(self.tree, 1)
        
        # Summary stats
        summary_layout = QHBoxLayout()
        
        total_tx = len(transactions)
        total_di = sum(len(tx["di_bits"]) for tx in transactions)
        total_do = sum(len(tx["do_bits"][1:17]) if (tx["instruction"] and 
                       tx["instruction"]["instruction_name"] == "READ" and len(tx["do_bits"]) > 1) 
                       else len(tx["do_bits"]) for tx in transactions)
        
        summary_text = f"✅ Summary: {total_tx} transactions | {total_di} DI bits | {total_do} DO bits"
        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 11pt;")
        summary_layout.addWidget(summary_label)
        summary_layout.addStretch()
        
        main_layout.addLayout(summary_layout)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button)
