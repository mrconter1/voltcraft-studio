"""Main window for Voltcraft Studio"""
from typing import List, Tuple, Optional, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QToolBar,
    QTabWidget, QMessageBox, QLabel, QApplication, QDialog, QTextEdit, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut

from .models import ChannelInfo, TimeSeriesData, DeviceInfo
from .icons import IconFactory
from .graph_widget import TimeSeriesGraphWidget
from .loader import FileLoaderThread
from .decode_dialog import DecodeDialog
from .decode_processor import DecodeProcessor
from .decode_results_dialog import DecodeResultsDialog
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
        # Disable text selection in tabs
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tab_bar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # Tab 1: Waveform view (graph only - full screen)
        self.graph_widget = TimeSeriesGraphWidget()
        self.tab_widget.addTab(self.graph_widget, "📈 Waveform")
        
        # Tab 2: Channel info (metadata table)
        channel_info_widget = QWidget()
        channel_info_layout = QVBoxLayout(channel_info_widget)
        channel_info_layout.setContentsMargins(10, 10, 10, 10)
        
        self.channel_table = QTableWidget()
        # Completely disable all editing triggers
        self.channel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Prevent items from getting focus (prevents text selection within cells)
        self.channel_table.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        self.channel_table.verticalHeader().setVisible(True)
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.channel_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Enable cell selection (can select multiple cells)
        self.channel_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.channel_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        
        # Allow selecting rows/columns by clicking headers
        self.channel_table.horizontalHeader().setSectionsClickable(True)
        self.channel_table.verticalHeader().setSectionsClickable(True)
        self.channel_table.horizontalHeader().setHighlightSections(True)
        self.channel_table.verticalHeader().setHighlightSections(True)
        
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
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #5a7fa8;
                outline: none;
            }
            QTableWidget::item:selected:focus {
                background-color: #5a7fa8;
                outline: none;
                border: none;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #e0e0e0;
                padding: 10px;
                border: 1px solid #444444;
                font-weight: bold;
                font-size: 11pt;
            }
            QHeaderView::section:hover {
                background-color: #3d3d3d;
                cursor: pointer;
            }
            QHeaderView::section:checked {
                background-color: #4a5f7f;
            }
            QTableView QTableCornerButton::section {
                background-color: #1e1e1e;
                border: 1px solid #444444;
            }
        """)
        
        # Add keyboard shortcut for copying
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self.channel_table)
        copy_shortcut.activated.connect(self._copy_table_selection)
        
        channel_info_layout.addWidget(self.channel_table)
        
        # Status label to show copy confirmation
        self.copy_status_label = QLabel("")
        self.copy_status_label.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                background-color: #2d2d2d;
                color: #4CAF50;
                font-size: 10pt;
                font-weight: bold;
                border-top: 1px solid #444444;
            }
        """)
        self.copy_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.copy_status_label.hide()
        channel_info_layout.addWidget(self.copy_status_label)
        
        self.tab_widget.addTab(channel_info_widget, "📊 Data Info")
        
        # Connect to tab change event to clear selection
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(self.tab_widget)
        
        # Initialize loader thread
        self.loader_thread = None
        self.current_file_path = None
        self.device_info = None  # Store device info from bin files
        self.current_channels = None  # Store current loaded channels
        
        # Tool state
        self.current_tool = "move"  # Default tool is move
        
        # Disable tape measure and binarize until data is loaded
        self.tape_action.setEnabled(False)
        self.binarize_action.setEnabled(False)
        self.decode_action.setEnabled(False)
        
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
            QToolBar::separator {
                background: white;
                width: 1px;
                margin: 4px 8px;
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
        self.tape_action.setToolTip("Measure time and voltage difference between two points\nClick to place points, or click & hold to dynamically adjust [Shortcut: 2]")
        self.tape_action.setCheckable(True)
        self.tape_action.setShortcut("2")
        self.tape_action.triggered.connect(self.select_tape_tool)
        toolbar.addAction(self.tape_action)
        
        # Add separator
        toolbar.addSeparator()
        
        # Create binarize toggle action
        self.binarize_action = QAction(IconFactory.create_binarize_icon(), "Binarize Signal", self)
        self.binarize_action.setToolTip("Toggle signal binarization (converts to binary square wave) [Shortcut: 3]")
        self.binarize_action.setCheckable(True)
        self.binarize_action.setShortcut("3")
        self.binarize_action.triggered.connect(self.toggle_binarize)
        toolbar.addAction(self.binarize_action)

        # Create decode action
        self.decode_action = QAction(IconFactory.create_decode_icon(), "Decode Signal", self)
        self.decode_action.setToolTip("Decode signal using a predefined dictionary (e.g., ASCII, HEX, etc.)")
        self.decode_action.triggered.connect(self.show_decode_dialog)
        toolbar.addAction(self.decode_action)
        
        # Add separator
        toolbar.addSeparator()
        
        # Create help action
        help_action = QAction(IconFactory.create_help_icon(), "Help", self)
        help_action.setToolTip("Show controls and keyboard shortcuts")
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
    
    def _on_tab_changed(self, index):
        """Handle tab change event"""
        # Check if we switched to the Data Info tab (index 1)
        if index == 1:  # Data Info tab
            # Clear selection when entering the tab
            self.channel_table.clearSelection()
            # Also hide any copy status message
            self.copy_status_label.hide()
    
    def _format_metadata_value(self, value) -> str:
        """Format a metadata value for display"""
        if value is None:
            return "N/A"
        return str(value)
    
    def display_bin_metadata(self, device_info: Optional[DeviceInfo], channels: List[ChannelInfo]):
        """Display bin file metadata in a hierarchical table format"""
        if not channels or not any(ch.raw_metadata for ch in channels):
            return
        
        # Build a list of all keys that appear in any channel
        all_keys = set()
        for channel in channels:
            if channel.raw_metadata:
                all_keys.update(channel.raw_metadata.keys())
        
        # Sort keys for consistent display
        sorted_keys = sorted(all_keys)
        
        # Calculate table dimensions
        # Rows: device info (2) + separator + channels * keys
        num_device_rows = 0
        if device_info and (device_info.model or device_info.idn):
            num_device_rows = 2
        
        num_data_rows = num_device_rows + len(sorted_keys)
        num_cols = len(channels)
        
        # Set table dimensions
        self.channel_table.setRowCount(num_data_rows)
        self.channel_table.setColumnCount(num_cols)
        
        # Set column headers (channel names)
        self.channel_table.setHorizontalHeaderLabels([ch.name for ch in channels])
        
        # Set row headers
        row_labels = []
        if device_info and (device_info.model or device_info.idn):
            row_labels.append("MODEL")
            row_labels.append("IDN")
        row_labels.extend(sorted_keys)
        self.channel_table.setVerticalHeaderLabels(row_labels)
        
        # Fill device info rows
        current_row = 0
        if device_info and (device_info.model or device_info.idn):
            # MODEL row
            for col in range(num_cols):
                item = QTableWidgetItem(self._format_metadata_value(device_info.model))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.channel_table.setItem(current_row, col, item)
            current_row += 1
            
            # IDN row
            for col in range(num_cols):
                item = QTableWidgetItem(self._format_metadata_value(device_info.idn))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.channel_table.setItem(current_row, col, item)
            current_row += 1
        
        # Fill channel metadata rows
        for key in sorted_keys:
            for col, channel in enumerate(channels):
                value = ""
                if channel.raw_metadata and key in channel.raw_metadata:
                    value = self._format_metadata_value(channel.raw_metadata[key])
                
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.channel_table.setItem(current_row, col, item)
            current_row += 1
        
        # Resize to fit content
        self.channel_table.resizeColumnsToContents()
        self.channel_table.resizeRowsToContents()
    
    def _copy_table_selection(self):
        """Copy selected cells from channel table to clipboard, including headers if selected"""
        # Get selected ranges
        selected_ranges = self.channel_table.selectedRanges()
        
        if not selected_ranges:
            # Nothing selected
            return
        
        # Build a 2D array of selected cells
        # We need to handle potentially non-contiguous selections
        rows_data = {}
        min_row = float('inf')
        max_row = float('-inf')
        min_col = float('inf')
        max_col = float('-inf')
        
        for selected_range in selected_ranges:
            for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                if row not in rows_data:
                    rows_data[row] = {}
                for col in range(selected_range.leftColumn(), selected_range.rightColumn() + 1):
                    item = self.channel_table.item(row, col)
                    rows_data[row][col] = item.text() if item else ""
                    # Track the bounds
                    min_row = min(min_row, row)
                    max_row = max(max_row, row)
                    min_col = min(min_col, col)
                    max_col = max(max_col, col)
        
        if not rows_data:
            return
        
        # Check if entire rows or columns are selected
        total_rows = self.channel_table.rowCount()
        total_cols = self.channel_table.columnCount()
        
        # Determine if we should include headers
        include_row_headers = False
        include_col_headers = False
        
        # Check if entire rows are selected (all columns in those rows)
        for row in rows_data:
            if len(rows_data[row]) == total_cols:
                include_row_headers = True
                break
        
        # Check if entire columns are selected (all rows in those columns)
        cols_with_all_rows = set()
        for row in rows_data:
            for col in rows_data[row]:
                cols_with_all_rows.add(col)
        
        # A column has all rows if it appears in all selected rows
        if len(rows_data) == total_rows:
            include_col_headers = True
        
        # Build the output
        lines = []
        
        # Add column headers if needed
        if include_col_headers:
            header_line = []
            if include_row_headers:
                header_line.append("")  # Empty cell for top-left corner
            
            for col in range(min_col, max_col + 1):
                # Check if this column has any selected cells
                has_data = any(col in rows_data.get(row, {}) for row in rows_data)
                if has_data:
                    header_text = self.channel_table.horizontalHeaderItem(col)
                    header_line.append(header_text.text() if header_text else f"Col{col}")
            
            if header_line and (not include_row_headers or len(header_line) > 1):
                lines.append("\t".join(header_line))
        
        # Add data rows
        for row in sorted(rows_data.keys()):
            cols_in_row = rows_data[row]
            if not cols_in_row:
                continue
            
            line_data = []
            
            # Add row header if needed
            if include_row_headers:
                header_text = self.channel_table.verticalHeaderItem(row)
                line_data.append(header_text.text() if header_text else f"Row{row}")
            
            # Add cell data
            row_min_col = min(cols_in_row.keys())
            row_max_col = max(cols_in_row.keys())
            for col in range(row_min_col, row_max_col + 1):
                line_data.append(cols_in_row.get(col, ""))
            
            lines.append("\t".join(line_data))
        
        # Copy to clipboard
        clipboard_text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text)
        
        # Show confirmation message
        num_cells = sum(len(cols) for cols in rows_data.values())
        header_info = ""
        if include_col_headers or include_row_headers:
            header_info = " with headers"
        self.copy_status_label.setText(f"✓ Copied {num_cells} cell(s){header_info} to clipboard")
        self.copy_status_label.show()
        
        # Hide message after 2 seconds
        QTimer.singleShot(2000, self.copy_status_label.hide)
    
    def display_channel_info(self, channels: List[ChannelInfo]):
        """Display channel information in table (txt format with predefined parameters)"""
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
                # Make item selectable but not editable (prevents text selection within cells)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
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
    
    def toggle_binarize(self):
        """Toggle signal binarization on/off"""
        is_binarized = self.binarize_action.isChecked()
        self.graph_widget.set_binarize(is_binarized)
    
    def show_decode_dialog(self):
        """Show the decode signal dialog and process the decode"""
        if self.current_channels is None or len(self.current_channels) == 0:
            QMessageBox.warning(
                self,
                "No Data Loaded",
                "No time series data is currently loaded. Please load a file first.",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # Extract channel names from channel info objects
        channel_names = [ch.name for ch in self.current_channels]
        
        # Create and show decode dialog with app icon
        self.decode_dialog = DecodeDialog(channel_names, self, IconFactory.create_window_icon())
        
        # Show dialog and wait for result
        if self.decode_dialog.exec():
            # User clicked "Decode & Analyze"
            mapping = self.decode_dialog.get_mapping()
            
            # Process decode with actual data
            self._process_decode(mapping)
    
    def _process_decode(self, mapping: Dict[str, str]):
        """
        Process the decode with the given channel mapping.
        
        Args:
            mapping: Dictionary mapping channel names to signal types (SK, CS, DI, DO)
        """
        if not self.graph_widget.time_series_data:
            QMessageBox.warning(self, "Error", "No time series data available.")
            return
        
        # Get time interval from channel metadata
        time_interval_str = self._get_time_interval()
        if not time_interval_str:
            QMessageBox.warning(
                self,
                "Error",
                "Could not determine time interval from file metadata.",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # Extract data for SK and CS channels (required)
        ts_data = self.graph_widget.time_series_data
        channel_data = ts_data.channel_data
        
        # Find which channels correspond to SK, CS, DI, DO
        reverse_mapping = {v: k for k, v in mapping.items()}  # signal_type -> channel_name
        
        try:
            sk_channel = reverse_mapping.get("SK")
            cs_channel = reverse_mapping.get("CS")
            di_channel = reverse_mapping.get("DI")
            do_channel = reverse_mapping.get("DO")
            
            # SK and CS are required
            if not sk_channel or not cs_channel:
                QMessageBox.warning(
                    self, 
                    "Missing Required Channels", 
                    "Please assign SK and CS to channels.\n\nBoth are required for decoding."
                )
                return
            
            # Get data for required channels
            sk_data = channel_data[sk_channel]
            cs_data = channel_data[cs_channel]
            
            # Get optional DI and DO data
            di_data = channel_data[di_channel] if di_channel else None
            do_data = channel_data[do_channel] if do_channel else None
            
            # Check that at least one of DI or DO is mapped
            if di_data is None and do_data is None:
                QMessageBox.warning(
                    self, 
                    "No Data Channels", 
                    "Please assign at least one of DI (Data Input) or DO (Data Output) to decode."
                )
                return
            
            # Process binary decode
            results = DecodeProcessor.process_decode_binary(
                sk_data, cs_data, di_data, do_data,
                time_interval_str,
                len(sk_data)
            )
            
            # Show results in a dialog
            self.decode_results_dialog = DecodeResultsDialog(results, mapping, time_interval_str, 
                                                              self, IconFactory.create_window_icon())
            self.decode_results_dialog.exec()
            
        except KeyError as e:
            QMessageBox.critical(self, "Error", f"Channel data not found: {e}")
    
    def _get_time_interval(self) -> str:
        """
        Get time interval from channel metadata.
        Looks for 'Adc_Data_Time' in raw metadata or similar fields.
        
        Returns:
            Time interval string (e.g., "0.400000us") or None if not found
        """
        if not self.current_channels or len(self.current_channels) == 0:
            return None
        
        # Try to get from first channel's raw metadata
        for channel in self.current_channels:
            if channel.raw_metadata:
                # Look for Adc_Data_Time field
                if "Adc_Data_Time" in channel.raw_metadata:
                    return str(channel.raw_metadata["Adc_Data_Time"])
            
            # Fallback: try time_interval attribute if it exists
            if hasattr(channel, "time_interval") and channel.time_interval:
                return channel.time_interval
        
        return None
    
    def show_help(self):
        """Show help dialog with controls and keyboard shortcuts"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Voltcraft Studio - Help")

        # Create Tab Widget
        tab_widget = QTabWidget(help_dialog)

        # Add tabs
        tools_tab = QTextEdit()
        tools_tab.setReadOnly(True)
        tools_tab.setHtml("""
        <h3>Tools</h3>
        <p style='margin-left: 20px;'>
        <b>Move Tool</b> - Pan and zoom the graph (default)<br>
        <b>Tape Measure</b> - Measure time and voltage difference between two points<br>
        <b>Binarize Signal</b> - Convert signal to binary square wave (HIGH/LOW states only)
        </p>
        """)
        tab_widget.addTab(tools_tab, "Tools")

        mouse_controls_tab = QTextEdit()
        mouse_controls_tab.setReadOnly(True)
        mouse_controls_tab.setHtml("""
        <h3>Mouse Controls</h3>
        <p style='margin-left: 20px;'>
        <b>Left Drag</b> - Pan the graph (Move tool)<br>
        <b>Left Click</b> - Place measurement points (Tape tool)<br>
        <b>Click & Hold</b> - Dynamic second point while dragging (Tape tool)<br>
        <b>Right Drag</b> - Box zoom selection<br>
        <b>Mouse Wheel</b> - Zoom both axes
        </p>
        """)
        tab_widget.addTab(mouse_controls_tab, "Mouse Controls")

        shortcuts_tab = QTextEdit()
        shortcuts_tab.setReadOnly(True)
        shortcuts_tab.setHtml("""
        <h3>Keyboard Shortcuts</h3>
        <p style='margin-left: 20px;'>
        <b>1</b> - Switch to Move tool<br>
        <b>2</b> - Switch to Tape Measure tool<br>
        <b>3</b> - Toggle signal binarization<br>
        <b>Ctrl + C</b> - Copy selected cells (Data Info tab)<br>
        <b>Ctrl + Scroll</b> - Zoom X-axis only (time)<br>
        <b>Shift + Scroll</b> - Zoom Y-axis only (voltage)
        </p>
        """)
        tab_widget.addTab(shortcuts_tab, "Shortcuts")

        # Layout
        layout = QVBoxLayout(help_dialog)
        layout.addWidget(tab_widget)

        help_dialog.setLayout(layout)
        help_dialog.exec()
    
    def _load_file_with_progress(self, file_path: str):
        """Load file in background with progress display"""
        # Disable tape measure and binarize while loading
        self.tape_action.setEnabled(False)
        self.binarize_action.setEnabled(False)
        self.binarize_action.setChecked(False)
        if self.current_tool == "tape":
            self.select_move_tool()
        
        # Show progress in graph widget
        self.graph_widget.set_loading_progress(0, "Starting...")
        
        # Create and start loader thread
        self.loader_thread = FileLoaderThread(file_path)
        self.loader_thread.metadata_loaded.connect(self._on_metadata_loaded)
        self.loader_thread.progress.connect(self._update_progress)
        self.loader_thread.finished.connect(self._on_file_loaded)
        self.loader_thread.error.connect(self._on_load_error)
        self.loader_thread.start()
    
    def _update_progress(self, value: int, message: str):
        """Update progress display"""
        self.graph_widget.set_loading_progress(value, message)
    
    def _on_metadata_loaded(self, device_info: Optional[DeviceInfo], channels: List[ChannelInfo]):
        """Handle metadata loaded (before full data)"""
        # Store device info
        self.device_info = device_info
        self.current_channels = channels # Store channels for decode dialog
        
        # Display channel info in table immediately
        # Use appropriate display method based on whether we have bin metadata
        if device_info or (channels and channels[0].raw_metadata):
            # Bin file format with rich metadata
            self.display_bin_metadata(device_info, channels)
        else:
            # Text file format with predefined parameters
            self.display_channel_info(channels)
        
        # Update window title
        self.setWindowTitle(f"{WINDOW_TITLE} - {self.current_file_path}")
    
    def _on_file_loaded(self, device_info: Optional[DeviceInfo], channels: List[ChannelInfo], time_series: TimeSeriesData):
        """Handle successful file load (full data ready)"""
        # Channel info already displayed from metadata_loaded signal
        # Now just plot the time series data
        self.graph_widget.plot_data(time_series, channels)
        
        # Enable tape measure and binarize tools now that we have data
        self.tape_action.setEnabled(True)
        self.binarize_action.setEnabled(True)
        self.decode_action.setEnabled(True) # Enable decode action
        
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

