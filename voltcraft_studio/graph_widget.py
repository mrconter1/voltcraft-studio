"""Graph widget for displaying time series data"""
import pyqtgraph as pg
import numpy as np
from typing import List
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor, QCursor, QMouseEvent

from .models import TimeSeriesData, ChannelInfo
from .utils import parse_time_interval, format_time_auto, ureg, get_best_time_unit_for_range, convert_time_to_unit


class DynamicVoltageAxisItem(pg.AxisItem):
    """Axis that dynamically adjusts voltage units based on visible range"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_plot_widget = None
        
    def set_parent_plot_widget(self, plot_widget):
        """Set reference to parent plot widget to access view range"""
        self.parent_plot_widget = plot_widget
    
    def tickStrings(self, values, scale, spacing):
        """Override tick string formatting with dynamic voltage unit selection"""
        if self.parent_plot_widget is None or len(values) == 0:
            return super().tickStrings(values, scale, spacing)
        
        # Get the absolute values to determine unit
        abs_values = [abs(v) for v in values if v != 0]
        if not abs_values:
            abs_values = [abs(v) for v in values]
        
        if not abs_values:
            return super().tickStrings(values, scale, spacing)
        
        # Find typical magnitude
        max_val = max(abs_values)
        min_val = min(abs_values) if min(abs_values) > 0 else max_val
        avg_magnitude = (max_val + min_val) / 2
        
        # Determine best unit (µV, mV, or V)
        if avg_magnitude < 1:
            best_unit = 'µV'
            scale_factor = 1000  # mV to µV
        elif avg_magnitude < 1000:
            best_unit = 'mV'
            scale_factor = 1
        else:
            best_unit = 'V'
            scale_factor = 0.001  # mV to V
        
        # Calculate tick spacing to determine precision
        if len(values) >= 2:
            spacing_magnitude = abs(values[1] - values[0]) * scale_factor
            
            if spacing_magnitude < 0.0001:
                decimal_places = 5
            elif spacing_magnitude < 0.001:
                decimal_places = 4
            elif spacing_magnitude < 0.01:
                decimal_places = 3
            elif spacing_magnitude < 0.1:
                decimal_places = 2
            elif spacing_magnitude < 1:
                decimal_places = 2
            elif spacing_magnitude < 10:
                decimal_places = 1
            else:
                decimal_places = 0
        else:
            decimal_places = 2
        
        # Format all tick values with unit suffix
        strings = []
        for value in values:
            try:
                magnitude = value * scale_factor
                strings.append(f"{magnitude:.{decimal_places}f} {best_unit}")
            except Exception:
                strings.append(f"{value:.3g}")
        
        return strings


class DynamicTimeAxisItem(pg.AxisItem):
    """Axis that dynamically adjusts time units based on visible range"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interval_quantity = 1.0 * ureg.dimensionless
        self.is_time_axis = False
        self.parent_plot_widget = None
        self.current_unit = 's'
        
    def set_time_interval(self, interval_quantity):
        """Set the time interval for this axis"""
        self.interval_quantity = interval_quantity
        self.is_time_axis = True
    
    def set_parent_plot_widget(self, plot_widget):
        """Set reference to parent plot widget to access view range"""
        self.parent_plot_widget = plot_widget
    
    def disable_time_formatting(self):
        """Disable time formatting (for sample indices)"""
        self.is_time_axis = False
    
    def tickStrings(self, values, scale, spacing):
        """Override tick string formatting with dynamic unit selection"""
        if not self.is_time_axis or self.parent_plot_widget is None or len(values) == 0:
            # Use default formatting for non-time axes
            return super().tickStrings(values, scale, spacing)
        
        # Convert all tick values to seconds to find the best unit
        time_values_seconds = []
        for value in values:
            try:
                time_quantity = value * self.interval_quantity
                time_seconds = time_quantity.to(ureg.second).magnitude
                time_values_seconds.append(abs(time_seconds))
            except Exception:
                pass
        
        if not time_values_seconds:
            return super().tickStrings(values, scale, spacing)
        
        # Find the range of values being displayed
        max_time = max(time_values_seconds)
        min_time = min(time_values_seconds) if min(time_values_seconds) > 0 else max_time
        
        # Determine best unit based on the typical magnitude of values
        # We want numbers to be in the range 0.1 - 999 for readability
        avg_magnitude = (max_time + min_time) / 2
        best_unit = get_best_time_unit_for_range(avg_magnitude)
        self.current_unit = best_unit
        
        # Calculate tick spacing in the chosen unit to determine precision
        if len(values) >= 2:
            # Convert first two values to get spacing
            val1_qty = values[0] * self.interval_quantity
            val2_qty = values[1] * self.interval_quantity
            spacing_magnitude = abs(convert_time_to_unit(val2_qty - val1_qty, best_unit))
            
            # Determine decimal places needed to show the spacing
            if spacing_magnitude < 0.0001:
                decimal_places = 5
            elif spacing_magnitude < 0.001:
                decimal_places = 4
            elif spacing_magnitude < 0.01:
                decimal_places = 3
            elif spacing_magnitude < 0.1:
                decimal_places = 2
            elif spacing_magnitude < 1:
                decimal_places = 2
            elif spacing_magnitude < 10:
                decimal_places = 1
            else:
                decimal_places = 0
        else:
            decimal_places = 2
        
        # Format all tick values in the chosen unit with unit suffix
        strings = []
        for value in values:
            try:
                # Convert value to time quantity
                time_quantity = value * self.interval_quantity
                # Convert to the chosen unit
                magnitude = convert_time_to_unit(time_quantity, best_unit)
                # Format with calculated precision and unit suffix
                strings.append(f"{magnitude:.{decimal_places}f} {best_unit}")
            except Exception:
                # Fallback to default if formatting fails
                strings.append(f"{value:.3g}")
        
        return strings


class CustomViewBox(pg.ViewBox):
    """Custom ViewBox with independent axis zoom control"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enable mouse interaction for both axes
        self.setMouseEnabled(x=True, y=True)
        self.tape_measure_mode = False  # Flag for tape measure mode
        self.is_dragging = False  # Track drag state for cursor changes
        # Set default cursor to open hand for move tool
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def wheelEvent(self, ev, axis=None):
        """
        Handle mouse wheel events with modifier keys for independent axis zooming
        
        - Normal scroll: Zoom both axes
        - Ctrl + scroll: Zoom X-axis only
        - Shift + scroll: Zoom Y-axis only
        """
        # Block wheel events in tape measure mode
        if self.tape_measure_mode:
            ev.ignore()
            return
        
        # Get keyboard modifiers
        modifiers = ev.modifiers()

        # Temporary store the original cursor state
        original_cursor = self.cursor()
        
        # Determine which axis to zoom based on modifier keys
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            # Ctrl held - zoom X-axis only
            axis = 0  # X-axis
            mask = [True, False]
            self.setCursor(Qt.CursorShape.SizeHorCursor)  # Change cursor to horizontal resize
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            # Shift held - zoom Y-axis only
            axis = 1  # Y-axis
            mask = [False, True]
            self.setCursor(Qt.CursorShape.SizeVerCursor)  # Change cursor to vertical resize
        else:
            # No modifier - zoom both axes (default behavior)
            mask = [True, True]

        # Temporarily set which axes respond to mouse
        self.setMouseEnabled(x=mask[0], y=mask[1])

        # Call parent wheelEvent to handle the actual zooming
        super().wheelEvent(ev, axis=axis)

        # Restore both axes to be mouse-enabled
        self.setMouseEnabled(x=True, y=True)
        
        # Restore original cursor
        self.setCursor(original_cursor)

        # Accept the event
        ev.accept()
    
    def mouseDragEvent(self, ev, axis=None):
        """Block drag events in tape measure mode, handle cursor changes for move tool"""
        if self.tape_measure_mode:
            ev.ignore()
            return
        
        # Change cursor to closed hand when dragging starts
        if ev.isStart():
            self.is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif ev.isFinish():
            self.is_dragging = False
            # Restore to open hand cursor
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        
        super().mouseDragEvent(ev, axis=axis)
    
    def mouseClickEvent(self, ev):
        """Block click events in tape measure mode"""
        if self.tape_measure_mode:
            ev.ignore()
            return
        super().mouseClickEvent(ev)

    def keyPressEvent(self, ev):
        """Handle key press events to change cursor based on modifier keys"""
        if ev.key() == Qt.Key.Key_Control:
            # Change cursor to horizontal resize when Control is pressed
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif ev.key() == Qt.Key.Key_Shift:
            # Change cursor to vertical resize when Shift is pressed
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            # Call parent method if no relevant key is pressed
            super().keyPressEvent(ev)

    def keyReleaseEvent(self, ev):
        """Handle key release events to reset cursor to open hand"""
        if ev.key() in (Qt.Key.Key_Control, Qt.Key.Key_Shift):
            # Reset cursor to open hand
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            super().keyReleaseEvent(ev)


class TimeSeriesGraphWidget(QWidget):
    """Widget for displaying time series oscilloscope data"""
    
    # Colors for different channels (brighter for dark background)
    CHANNEL_COLORS = [
        (255, 215, 0),    # Gold (CH1)
        (100, 200, 255),  # Light blue (CH2)
        (255, 120, 100),  # Light red (CH3)
        (100, 255, 150),  # Light green (CH4)
    ]
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.time_series_data = None
        self.current_tool = "move"
        
        # Tape measure state
        self.tape_point1 = None  # First click point (x, y)
        self.tape_point2 = None  # Second click point (x, y)
        self.tape_line = None    # Visual line between points
        self.tape_markers = []   # Visual markers at click points
        self.tape_text_item = None  # Text box showing measurement
        self.tape_coords_item = None  # Text box showing current coordinates
        self.is_dragging_tape = False  # Track if we're dragging to set point 2
        self.mouse_is_pressed = False  # Track if mouse button is currently held down
        
        # Time interval info for calculations
        self.time_unit = 'samples'
        self.interval_quantity = 1.0 * ureg.dimensionless  # Pint quantity
        
        # Binarize state
        self.binarize_enabled = False
        self.original_data = None  # Store original data for toggling
        self.channels_info = None  # Store channel info for re-plotting
        
        # Channel info overlays
        self.channel_info_boxes = []  # List of TextItem widgets for channel info
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create plot widget with dark theme and custom ViewBox
        pg.setConfigOptions(antialias=True)
        
        # Create custom axes with dynamic unit scaling
        self.time_axis = DynamicTimeAxisItem(orientation='bottom')
        self.voltage_axis = DynamicVoltageAxisItem(orientation='left')
        
        # Create custom ViewBox for independent axis control
        view_box = CustomViewBox()
        
        # Create plot widget with custom axes and viewbox
        self.plot_widget = pg.PlotWidget(
            viewBox=view_box,
            axisItems={'bottom': self.time_axis, 'left': self.voltage_axis}
        )
        
        # Set reference to plot widget in axes for range detection
        self.time_axis.set_parent_plot_widget(self.plot_widget)
        self.voltage_axis.set_parent_plot_widget(self.plot_widget)
        
        # Enable OpenGL for GPU acceleration (much faster for large datasets)
        try:
            self.plot_widget.useOpenGL(True)
            print("OpenGL acceleration enabled")
        except Exception as e:
            print(f"OpenGL not available: {e}")
        
        # Dark mode styling
        self.plot_widget.setBackground('#1e1e1e')  # Dark background
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        
        # Set axis colors for dark mode
        axis_color = '#cccccc'
        # Custom axes styling
        self.voltage_axis.setPen(axis_color)
        self.voltage_axis.setTextPen(axis_color)
        self.time_axis.setPen(axis_color)
        self.time_axis.setTextPen(axis_color)
        
        # Labels with light color (just axis names, units shown on ticks)
        label_style = {'color': '#cccccc', 'font-size': '12pt'}
        self.plot_widget.setLabel('left', 'Voltage', **label_style)
        self.plot_widget.setLabel('bottom', 'Time', **label_style)
        self.plot_widget.setTitle('Oscilloscope Waveform', color='#cccccc', size='14pt')
        
        # Enable auto-range and mouse interaction
        self.plot_widget.enableAutoRange()
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # Connect mouse events to the plot widget's scene
        self.plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)
        
        # Connect to mouse press and move events for dynamic tape measure
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
        # Install event filter to catch mouse press/release for tape measure
        self.plot_widget.viewport().installEventFilter(self)
        
        # Connect view range change signal to update channel info box positions
        self.plot_widget.getViewBox().sigRangeChanged.connect(self._on_view_range_changed)
        
        # Legend will be created when data is loaded
        self.legend = None
        
        layout.addWidget(self.plot_widget)
        
        # Progress bar for loading (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximumHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-top: 1px solid #444444;
                text-align: center;
                background-color: #2d2d2d;
                color: white;
                font-size: 10pt;
            }
            QProgressBar::chunk {
                background-color: #1e88e5;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Info label with dark styling
        self.info_label = QLabel("No data loaded")
        self.info_label.setStyleSheet(
            "padding: 6px; "
            "background-color: #2d2d2d; "
            "color: #cccccc; "
            "border-top: 1px solid #444444;"
        )
        layout.addWidget(self.info_label)
    
    
    def plot_data(self, time_series_data: TimeSeriesData, channels: List[ChannelInfo] = None, preserve_view: bool = False):
        """
        Plot time series data with automatic downsampling
        
        Args:
            time_series_data: TimeSeriesData object containing the data to plot
            channels: List of ChannelInfo with metadata for proper axis scaling
            preserve_view: If True, preserve the current zoom/pan state
        """
        # Save current view range and channel visibility if we need to preserve them
        saved_view_range = None
        saved_auto_range_state = None
        saved_channel_visibility = {}
        
        if preserve_view and self.time_series_data is not None:
            view_box = self.plot_widget.getViewBox()
            if view_box is not None:
                # Get the current view range (returns [[xmin, xmax], [ymin, ymax]])
                saved_view_range = view_box.viewRange()
                # Also save auto-range state
                saved_auto_range_state = view_box.autoRangeEnabled()
                print(f"  💾 Saving view: X=[{saved_view_range[0][0]:.2f}, {saved_view_range[0][1]:.2f}], Y=[{saved_view_range[1][0]:.2f}, {saved_view_range[1][1]:.2f}]")
            
            # Save which channels are currently visible
            if self.legend is not None:
                print(f"  🔍 Checking visibility of {len(self.legend.items)} channel(s)...")
                for item in self.legend.items:
                    # item is a tuple of (PlotDataItem, LabelItem)
                    plot_item = item[0]
                    label_item = item[1]
                    channel_name = label_item.text
                    # Check if the plot item is visible
                    is_visible = plot_item.isVisible()
                    saved_channel_visibility[channel_name] = is_visible
                    print(f"  💾 Saving {channel_name} visibility = {is_visible}")
        
        # Store original data for binarize toggle
        self.original_data = time_series_data
        self.channels_info = channels
        
        # Apply binarization if enabled
        if self.binarize_enabled:
            time_series_data = self._apply_binarize(time_series_data)
        
        self.time_series_data = time_series_data
        
        # Clear previous plots - this removes all plot items but may affect the legend
        self.plot_widget.clear()
        
        # Remove the old legend if it exists (clear() should remove it, but be explicit)
        if self.legend is not None:
            try:
                self.plot_widget.plotItem.legend = None
                self.legend = None
            except:
                pass
        
        # Create a fresh legend
        self.legend = self.plot_widget.addLegend(
            brush=(30, 30, 30, 180),
            pen={'color': '#666666', 'width': 1}
        )
        
        if not time_series_data or len(time_series_data.indices) == 0:
            self.info_label.setText("No data to display")
            return
        
        total_points = len(time_series_data.indices)
        
        # Calculate actual time values from time interval
        time_values = None
        time_unit = 'samples'
        if channels and len(channels) > 0:
            # Get time interval from first channel using Pint
            time_interval_str = channels[0].time_interval
            interval_value, time_unit, interval_quantity = parse_time_interval(time_interval_str)
            
            # Store Pint quantity for calculations
            self.time_unit = time_unit
            self.interval_quantity = interval_quantity
            
            # Configure the time axis for dynamic unit scaling
            self.time_axis.set_time_interval(interval_quantity)
            
            # Use raw indices for the x-axis; the DynamicTimeAxisItem will handle the conversion to time
            time_values = time_series_data.indices
            
            # Set X-axis label (just "Time" - units shown on tick values)
            self.plot_widget.setLabel('bottom', 'Time')
        else:
            # Fallback to sample indices
            time_values = time_series_data.indices
            self.time_unit = 'samples'
            self.interval_quantity = 1.0 * ureg.dimensionless
            
            # Disable dynamic time formatting for sample indices
            self.time_axis.disable_time_formatting()
            self.plot_widget.setLabel('bottom', 'Sample Index')
        
        # Plot each channel with ALL data (PyQtGraph will handle downsampling)
        plot_items = []
        plot_items_by_name = {}  # Map channel name to plot item for visibility restoration
        
        for i, channel_name in enumerate(time_series_data.channel_names):
            if channel_name in time_series_data.channel_data:
                voltage_data = time_series_data.channel_data[channel_name]
                
                # Skip empty channels
                if len(voltage_data) == 0:
                    continue
                
                color = self.CHANNEL_COLORS[i % len(self.CHANNEL_COLORS)]
                
                # Create pen with channel color and increased width for visibility
                pen = pg.mkPen(color=color, width=2)
                
                # Plot ALL data with actual time values - let PyQtGraph handle downsampling
                plot_item = self.plot_widget.plot(
                    time_values,
                    voltage_data,
                    pen=pen,
                    name=channel_name
                )
                
                # Enable automatic downsampling with 'peak' method for best quality
                # ds=500 means downsample by factor of 500 when zoomed out (10M -> 20k points)
                # method='peak' preserves min/max, ensuring spikes/glitches are never missed
                # Perfect for oscilloscope data with GPU acceleration
                plot_item.setDownsampling(ds=500, auto=True, method='peak')
                
                # Only render data that's visible in the viewport
                plot_item.setClipToView(True)
                
                plot_items.append(plot_item)
                plot_items_by_name[channel_name] = plot_item
        
        # Update info label
        num_samples = len(time_series_data.indices)
        num_channels = len(time_series_data.channel_names)
        
        # Get voltage range for all data
        all_voltages = []
        for channel_name in time_series_data.channel_names:
            if channel_name in time_series_data.channel_data:
                data = time_series_data.channel_data[channel_name]
                if len(data) > 0:
                    all_voltages.append(data.min())
                    all_voltages.append(data.max())
        
        if all_voltages:
            min_v = min(all_voltages)
            max_v = max(all_voltages)
            
            # Calculate total time duration if we have time info
            duration_str = ""
            if channels and len(channels) > 0:
                # Calculate total duration using Pint
                total_duration_quantity = num_samples * self.interval_quantity
                # Format with auto-scaling
                duration_formatted = format_time_auto(total_duration_quantity, precision=4)
                duration_str = f" | Duration: {duration_formatted}"
            
            self.info_label.setText(
                f"Loaded {num_samples:,} samples across {num_channels} channel(s){duration_str} | "
                f"Voltage range: {min_v:.2f} to {max_v:.2f} mV | "
                f"GPU-accelerated with peak downsampling | Scroll: zoom both | Ctrl+Scroll: zoom X | Shift+Scroll: zoom Y"
            )
        else:
            self.info_label.setText(
                f"Loaded {num_samples:,} samples across {num_channels} channel(s) | "
                f"Scroll: zoom both | Ctrl+Scroll: zoom X | Shift+Scroll: zoom Y"
            )
        
        # Restore channel visibility if preserved
        if saved_channel_visibility:
            print(f"  🔍 Restoring visibility for {len(saved_channel_visibility)} channel(s)...")
            for channel_name, is_visible in saved_channel_visibility.items():
                if channel_name in plot_items_by_name:
                    plot_items_by_name[channel_name].setVisible(is_visible)
                    print(f"  ✓ Set {channel_name} visibility = {is_visible}")
                else:
                    print(f"  ⚠ Could not find {channel_name} in plot items!")
        
        # Restore view range if preserved, otherwise auto-range
        if saved_view_range is not None:
            # Disable auto-range first to prevent it from interfering
            self.plot_widget.enableAutoRange(False)
            
            view_box = self.plot_widget.getViewBox()
            if view_box is not None:
                # Disable auto-range on the ViewBox itself
                view_box.enableAutoRange(enable=False)
                # Set the exact range we saved
                view_box.setRange(xRange=saved_view_range[0], yRange=saved_view_range[1], padding=0, update=True)
                print(f"  ✓ Restored view: X=[{saved_view_range[0][0]:.2f}, {saved_view_range[0][1]:.2f}], Y=[{saved_view_range[1][0]:.2f}, {saved_view_range[1][1]:.2f}]")
        else:
            # Auto-range to show all data
            self.plot_widget.autoRange()
            # Disable auto-ranging after initial display
            self.plot_widget.enableAutoRange(False)
        
        # Create channel info overlays if channels provided
        if channels:
            self._create_channel_info_overlays(channels)
    
    def _create_channel_info_overlays(self, channels: List[ChannelInfo]):
        """Create floating info boxes for each channel on the graph"""
        # Clear any existing info boxes
        for box in self.channel_info_boxes:
            self.plot_widget.removeItem(box)
        self.channel_info_boxes.clear()
        
        if not channels:
            return
        
        # Position boxes vertically stacked in top-right corner
        for i, channel in enumerate(channels):
            # Get channel color
            color = self.CHANNEL_COLORS[i % len(self.CHANNEL_COLORS)]
            
            # Create concise info text with key parameters
            info_lines = [
                f"<b>{channel.name}</b>",
                f"Freq: {channel.frequency}",
                f"PK-PK: {channel.pk_pk}",
                f"Avg: {channel.average}",
            ]
            info_text = "<br/>".join(info_lines)
            
            # Create text item with HTML formatting
            text_box = pg.TextItem(
                html=f'<div style="text-align: left;">{info_text}</div>',
                color=color,
                fill=(30, 30, 30, 180),  # Semi-transparent dark background
                border=pg.mkPen(color=color, width=2),
                anchor=(1.0, 0.0)  # Top-right anchor
            )
            
            self.channel_info_boxes.append(text_box)
        
        # Add all boxes to the plot at once
        for box in self.channel_info_boxes:
            self.plot_widget.addItem(box, ignoreBounds=True)
        
        # Position the boxes - will be updated when view changes
        self._update_channel_info_positions()
    
    def _update_channel_info_positions(self):
        """Update positions of channel info boxes based on current view"""
        if not self.channel_info_boxes:
            return
        
        view_box = self.plot_widget.getViewBox()
        if view_box is None:
            return
        
        # Get current view range
        view_range = view_box.viewRange()
        x_max = view_range[0][1]
        y_max = view_range[1][1]
        y_range = view_range[1][1] - view_range[1][0]
        
        # Stack boxes vertically from top
        box_spacing = y_range * 0.15  # 15% of view height between boxes
        
        for i, box in enumerate(self.channel_info_boxes):
            # Position in top-right corner, stacked vertically
            y_pos = y_max - (i * box_spacing)
            box.setPos(x_max, y_pos)
    
    def _on_view_range_changed(self):
        """Handle view range changes to update channel info box positions"""
        self._update_channel_info_positions()
    
    def clear(self):
        """Clear the plot"""
        self.plot_widget.clear()
        self.time_series_data = None
        self.info_label.setText("No data loaded")
        
        # Clear channel info overlays
        for box in self.channel_info_boxes:
            try:
                self.plot_widget.removeItem(box)
            except:
                pass
        self.channel_info_boxes.clear()
    
    def set_loading_progress(self, value: int, message: str):
        """Update loading progress bar"""
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{message} {value}%")
        if not self.progress_bar.isVisible():
            self.progress_bar.show()
    
    def hide_progress(self):
        """Hide the progress bar"""
        self.progress_bar.hide()
    
    def eventFilter(self, obj, event):
        """Event filter to catch mouse press/release for tape measure"""
        if self.current_tool == "tape" and obj == self.plot_widget.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._on_mouse_press(event)
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._on_mouse_release(event)
        
        # Always pass the event to the parent
        return super().eventFilter(obj, event)
    
    def _on_mouse_press(self, event):
        """Handle mouse button press for tape measure"""
        if self.current_tool != "tape":
            return
        
        # Mark that mouse is pressed
        self.mouse_is_pressed = True
        
        # If we already have first point but no second point, start dragging
        if self.tape_point1 is not None and self.tape_point2 is None:
            self.is_dragging_tape = True
    
    def _on_mouse_release(self, event):
        """Handle mouse button release for tape measure"""
        if self.current_tool != "tape":
            return
        
        # Mark that mouse is released
        self.mouse_is_pressed = False
        
        # If we were dragging, stop dragging (finalize second point)
        if self.is_dragging_tape:
            self.is_dragging_tape = False
    
    def set_tool(self, tool: str):
        """Set the current tool (move or tape)"""
        self.current_tool = tool
        
        view_box = self.plot_widget.getViewBox()
        
        if tool == "move":
            # Enable mouse panning/zooming
            if view_box:
                view_box.tape_measure_mode = False
                view_box.setMouseEnabled(x=True, y=True)
                view_box.setMouseMode(pg.ViewBox.PanMode)
                # Set open hand cursor for move tool
                view_box.setCursor(Qt.CursorShape.OpenHandCursor)
            # Set cursor on plot widget as well
            self.plot_widget.setCursor(Qt.CursorShape.OpenHandCursor)
            # Clear any existing tape measure and reset dragging state
            self._clear_tape_measure()
        elif tool == "tape":
            # Enable tape measure mode to block ViewBox events
            if view_box:
                view_box.tape_measure_mode = True
                view_box.rbScaleBox.hide()  # Hide the scale box if visible
                # Set crosshair cursor for tape measure tool
                view_box.setCursor(Qt.CursorShape.CrossCursor)
            # Set cursor on plot widget as well
            self.plot_widget.setCursor(Qt.CursorShape.CrossCursor)
            # Make sure dragging state is reset when switching to tape tool
            self.is_dragging_tape = False
            self.mouse_is_pressed = False
    
    def _on_mouse_clicked(self, event):
        """Handle mouse click events for tape measure tool"""
        if self.current_tool != "tape":
            return
        
        # Accept and consume the event to prevent it from propagating to ViewBox
        event.accept()
        
        # Only handle left clicks
        if event.button() != Qt.MouseButton.LeftButton:
            return
        
        # Get the scene position
        scene_pos = event.scenePos()
        
        # Map scene position to data coordinates
        view_box = self.plot_widget.getViewBox()
        if view_box is None:
            return
        
        # Convert scene coordinates to data coordinates
        data_pos = view_box.mapSceneToView(scene_pos)
        x_pos = data_pos.x()
        y_pos = data_pos.y()
        
        # Handle mouse click (button up)
        if event.double():
            # Double click - ignore for now
            return
        
        # Single click - determine what to do based on current state
        if self.tape_point1 is None:
            # First click - set first point, but don't start dragging yet
            # Dragging will start on the next mouse press
            self.tape_point1 = (x_pos, y_pos)
            self._draw_tape_marker(x_pos, y_pos, is_first=True)
        elif self.tape_point1 is not None and self.tape_point2 is None and not self.is_dragging_tape:
            # Second click without drag - place second point immediately
            self.tape_point2 = (x_pos, y_pos)
            self._draw_tape_marker(x_pos, y_pos, is_first=False)
            self._draw_tape_measurement()
        elif self.tape_point2 is not None and not self.is_dragging_tape:
            # Already have both fixed points - this is third click, clear and start over
            self._clear_tape_measure()
            self.tape_point1 = (x_pos, y_pos)
            self._draw_tape_marker(x_pos, y_pos, is_first=True)
    
    def _on_mouse_moved(self, pos):
        """Handle mouse move events for dynamic tape measure and coordinate display"""
        if self.current_tool != "tape":
            return
        
        # Get the scene position
        scene_pos = pos
        
        # Map scene position to data coordinates
        view_box = self.plot_widget.getViewBox()
        if view_box is None:
            return
        
        # Convert scene coordinates to data coordinates
        data_pos = view_box.mapSceneToView(scene_pos)
        x_pos = data_pos.x()
        y_pos = data_pos.y()
        
        # Always update coordinate display
        self._update_coordinate_display(x_pos, y_pos)
        
        # Only update measurement if we're actively dragging (button pressed and dragging mode)
        if self.is_dragging_tape and self.mouse_is_pressed and self.tape_point1 is not None:
            # Update second point dynamically
            self.tape_point2 = (x_pos, y_pos)
            
            # Clear previous second marker, line, and text (but keep first marker)
            if len(self.tape_markers) > 1:
                self.plot_widget.removeItem(self.tape_markers[1])
                self.tape_markers.pop()
            
            if self.tape_line is not None:
                self.plot_widget.removeItem(self.tape_line)
                self.tape_line = None
            
            if self.tape_text_item is not None:
                self.plot_widget.removeItem(self.tape_text_item)
                self.tape_text_item = None
            
            # Draw new marker and measurement
            self._draw_tape_marker(x_pos, y_pos, is_first=False)
            self._draw_tape_measurement()
    
    def _update_coordinate_display(self, x: float, y: float):
        """Update the floating coordinate display at cursor position"""
        # Convert x (time) to formatted string
        time_quantity = x * self.interval_quantity
        time_formatted = format_time_auto(time_quantity, precision=4)
        
        # Format voltage with appropriate precision
        voltage_abs = abs(y)
        if voltage_abs < 0.001 or voltage_abs > 10000:
            voltage_str = f"{y:.3e} mV"
        elif voltage_abs < 1:
            voltage_str = f"{y:.4f} mV"
        elif voltage_abs < 10:
            voltage_str = f"{y:.3f} mV"
        elif voltage_abs < 100:
            voltage_str = f"{y:.2f} mV"
        else:
            voltage_str = f"{y:.1f} mV"
        
        # Create coordinate text
        coords_text = f"t = {time_formatted}\nV = {voltage_str}"
        
        # Remove old coordinate item if exists
        if self.tape_coords_item is not None:
            self.plot_widget.removeItem(self.tape_coords_item)
            self.tape_coords_item = None
        
        # Create new coordinate text item
        self.tape_coords_item = pg.TextItem(
            text=coords_text,
            color=(150, 200, 255),  # Light blue color
            fill=(30, 30, 30, 220),  # Slightly more opaque than measurement box
            border=(150, 200, 255),
            anchor=(0.0, 1.0)  # Bottom-left anchor, so it appears above and to the right of cursor
        )
        
        # Get view range to determine offset
        view_box = self.plot_widget.getViewBox()
        if view_box is not None:
            view_range = view_box.viewRange()
            x_range = view_range[0][1] - view_range[0][0]
            y_range = view_range[1][1] - view_range[1][0]
            
            # Position slightly offset from cursor (2% of view range)
            offset_x = x_range * 0.02
            offset_y = y_range * 0.02
            self.tape_coords_item.setPos(x + offset_x, y + offset_y)
        else:
            # Fallback: no offset
            self.tape_coords_item.setPos(x, y)
        
        self.plot_widget.addItem(self.tape_coords_item)
    
    def _draw_tape_marker(self, x: float, y: float, is_first: bool):
        """Draw a marker at the clicked point"""
        # Create a scatter plot item for the marker
        color = (255, 100, 100) if is_first else (100, 255, 100)
        marker = pg.ScatterPlotItem(
            [x], [y],
            size=15,
            pen=pg.mkPen(color=color, width=2),
            brush=pg.mkBrush(color + (150,)),
            symbol='o'
        )
        self.plot_widget.addItem(marker)
        self.tape_markers.append(marker)
    
    def _draw_tape_measurement(self):
        """Draw line and measurement text between two points"""
        if self.tape_point1 is None or self.tape_point2 is None:
            return
        
        x1, y1 = self.tape_point1
        x2, y2 = self.tape_point2
        
        # Draw line between points
        self.tape_line = pg.PlotDataItem(
            [x1, x2], [y1, y2],
            pen=pg.mkPen(color=(255, 215, 0), width=2, style=Qt.PenStyle.DashLine)
        )
        self.plot_widget.addItem(self.tape_line)
        
        # Calculate time difference
        time_diff = abs(x2 - x1)
        
        # Convert to Pint quantity and format with auto-scaling
        time_diff_quantity = time_diff * self.interval_quantity
        time_formatted = format_time_auto(time_diff_quantity, precision=4)
        
        # Calculate voltage difference
        voltage_diff = y2 - y1  # Keep sign to show direction
        voltage_abs = abs(voltage_diff)
        
        # Format voltage with appropriate precision
        # Use scientific notation for very small/large values
        if voltage_abs < 0.001 or voltage_abs > 10000:
            voltage_str = f"{voltage_diff:.3e} mV"
        elif voltage_abs < 1:
            voltage_str = f"{voltage_diff:.4f} mV"
        elif voltage_abs < 10:
            voltage_str = f"{voltage_diff:.3f} mV"
        elif voltage_abs < 100:
            voltage_str = f"{voltage_diff:.2f} mV"
        else:
            voltage_str = f"{voltage_diff:.1f} mV"
        
        # Format the measurement text with both time and voltage
        measurement_text = f"Δt = {time_formatted}\nΔV = {voltage_str}"
        
        # Create text item for measurement box
        self.tape_text_item = pg.TextItem(
            text=measurement_text,
            color=(255, 215, 0),
            fill=(30, 30, 30, 200),
            border=(255, 215, 0),
            anchor=(0.5, 1.0)  # Center bottom of text
        )
        
        # Position text at midpoint above the line
        mid_x = (x1 + x2) / 2
        mid_y = max(y1, y2) + abs(y2 - y1) * 0.1  # Slightly above the higher point
        self.tape_text_item.setPos(mid_x, mid_y)
        
        self.plot_widget.addItem(self.tape_text_item)
    
    def _clear_tape_measure(self):
        """Clear all tape measure visual elements"""
        # Remove markers
        for marker in self.tape_markers:
            self.plot_widget.removeItem(marker)
        self.tape_markers.clear()
        
        # Remove line
        if self.tape_line is not None:
            self.plot_widget.removeItem(self.tape_line)
            self.tape_line = None
        
        # Remove measurement text
        if self.tape_text_item is not None:
            self.plot_widget.removeItem(self.tape_text_item)
            self.tape_text_item = None
        
        # Remove coordinate display
        if self.tape_coords_item is not None:
            self.plot_widget.removeItem(self.tape_coords_item)
            self.tape_coords_item = None
        
        # Reset points and dragging state
        self.tape_point1 = None
        self.tape_point2 = None
        self.is_dragging_tape = False
        self.mouse_is_pressed = False
    
    def set_binarize(self, enabled: bool):
        """Enable or disable signal binarization"""
        self.binarize_enabled = enabled
        
        if enabled:
            print("\n🔧 Binarize ENABLED - Converting to binary square wave representation")
        else:
            print("\n🔧 Binarize DISABLED - Showing original signal")
        
        # Re-plot with binarization applied/removed, preserving current zoom/pan
        if self.original_data is not None:
            self.plot_data(self.original_data, self.channels_info, preserve_view=True)
    
    def _apply_binarize(self, time_series_data: TimeSeriesData) -> TimeSeriesData:
        """
        Apply binarization to the signal by extracting only low-to-high and high-to-low transitions.
        
        This creates a binary square wave representation of the signal showing only state changes.
        
        Args:
            time_series_data: Original time series data
            
        Returns:
            Binarized time series data with only transitions
        """
        print("\n" + "="*60)
        print("APPLYING SIGNAL BINARIZATION")
        print("="*60)
        print(f"Processing {len(time_series_data.channel_names)} channel(s)...")
        print(f"Total samples per channel: {len(time_series_data.indices):,}")
        
        binarized_channel_data = {}
        
        for channel_idx, channel_name in enumerate(time_series_data.channel_names, 1):
            if channel_name not in time_series_data.channel_data:
                continue
            
            original_voltage = time_series_data.channel_data[channel_name]
            
            print(f"\n[{channel_idx}/{len(time_series_data.channel_names)}] Processing {channel_name}...")
            
            if len(original_voltage) == 0:
                print(f"  ⚠ Empty channel - skipping")
                binarized_channel_data[channel_name] = original_voltage
                continue
            
            # Calculate threshold as the midpoint between min and max
            v_min = np.min(original_voltage)
            v_max = np.max(original_voltage)
            threshold = (v_min + v_max) / 2
            
            print(f"  Voltage range: {v_min:.4f} mV to {v_max:.4f} mV")
            print(f"  Threshold: {threshold:.4f} mV")
            
            # Create binary signal (0 = low, 1 = high)
            binary_signal = (original_voltage > threshold).astype(int)
            
            # Find transitions (where binary signal changes)
            transitions = np.diff(binary_signal, prepend=binary_signal[0])
            transition_indices = np.where(transitions != 0)[0]
            
            # Count low-to-high and high-to-low transitions
            low_to_high = 0
            high_to_low = 0
            for trans_idx in transition_indices:
                if binary_signal[trans_idx] == 1:
                    low_to_high += 1
                else:
                    high_to_low += 1
            
            print(f"  Transitions detected: {len(transition_indices):,}")
            print(f"    • Low-to-high: {low_to_high:,}")
            print(f"    • High-to-low: {high_to_low:,}")
            
            # If no transitions found, keep original signal
            if len(transition_indices) == 0:
                print(f"  ⚠ No transitions found - keeping original signal")
                binarized_channel_data[channel_name] = original_voltage
                continue
            
            # Build binarized signal with only transitions
            # We'll create a new array with transition points
            binarized_indices = [0]  # Start at beginning
            binarized_voltages = [v_min if binary_signal[0] == 0 else v_max]
            
            for trans_idx in transition_indices:
                # Add point just before transition (to create vertical edge)
                binarized_indices.append(trans_idx)
                current_state = binary_signal[trans_idx - 1] if trans_idx > 0 else binary_signal[0]
                binarized_voltages.append(v_min if current_state == 0 else v_max)
                
                # Add point at transition (creates the vertical line)
                binarized_indices.append(trans_idx)
                new_state = binary_signal[trans_idx]
                binarized_voltages.append(v_min if new_state == 0 else v_max)
            
            # Add final point at the end
            binarized_indices.append(len(original_voltage) - 1)
            final_state = binary_signal[-1]
            binarized_voltages.append(v_min if final_state == 0 else v_max)
            
            # Create the binarized voltage array using vectorized operations (FAST!)
            total_points = len(time_series_data.indices)
            print(f"  Creating binary square wave from {total_points:,} datapoints...")
            
            # Use NumPy's searchsorted for ultra-fast lookup (O(n log m) instead of O(n*m))
            # This finds which transition segment each point belongs to
            binarized_indices_array = np.array(binarized_indices)
            binarized_voltages_array = np.array(binarized_voltages)
            
            # searchsorted tells us which transition index each point should use
            # 'right' means if a point equals a transition index, use the next segment
            indices_positions = np.searchsorted(binarized_indices_array, np.arange(total_points), side='right') - 1
            
            # Clamp to valid range [0, len-1]
            indices_positions = np.clip(indices_positions, 0, len(binarized_voltages_array) - 1)
            
            # Now just index into the voltages array - vectorized operation!
            full_binarized = binarized_voltages_array[indices_positions]
            
            print(f"  ✓ Binary square wave created instantly using vectorized NumPy operations")
            
            binarized_channel_data[channel_name] = full_binarized
            
            # Calculate compression ratio
            original_unique_points = len(np.unique(original_voltage))
            binarized_unique_points = len(np.unique(full_binarized))
            compression_ratio = (1 - binarized_unique_points / original_unique_points) * 100 if original_unique_points > 0 else 0
            
            print(f"  Binary signal statistics:")
            print(f"    • Original unique values: {original_unique_points:,}")
            print(f"    • Binarized unique values: {binarized_unique_points:,}")
            print(f"    • Simplification: {compression_ratio:.1f}%")
            print(f"  ✓ {channel_name} binarization complete")
        
        print("\n" + "="*60)
        print("BINARIZATION COMPLETE")
        print("="*60 + "\n")
        
        # Create new TimeSeriesData with binarized signals
        return TimeSeriesData(
            indices=time_series_data.indices,
            channel_data=binarized_channel_data,
            channel_names=time_series_data.channel_names
        )

