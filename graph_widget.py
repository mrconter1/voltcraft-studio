"""Graph widget for displaying time series data"""
import pyqtgraph as pg
import numpy as np
import re
from typing import List
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from models import TimeSeriesData, ChannelInfo


class CustomViewBox(pg.ViewBox):
    """Custom ViewBox with independent axis zoom control"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enable mouse interaction for both axes
        self.setMouseEnabled(x=True, y=True)
    
    def wheelEvent(self, ev, axis=None):
        """
        Handle mouse wheel events with modifier keys for independent axis zooming
        
        - Normal scroll: Zoom both axes
        - Ctrl + scroll: Zoom X-axis only
        - Shift + scroll: Zoom Y-axis only
        """
        # Get keyboard modifiers
        modifiers = ev.modifiers()
        
        # Determine which axis to zoom based on modifier keys
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            # Ctrl held - zoom X-axis only
            axis = 0  # X-axis
            mask = [True, False]
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            # Shift held - zoom Y-axis only
            axis = 1  # Y-axis
            mask = [False, True]
        else:
            # No modifier - zoom both axes (default behavior)
            mask = [True, True]
        
        # Temporarily set which axes respond to mouse
        self.setMouseEnabled(x=mask[0], y=mask[1])
        
        # Call parent wheelEvent to handle the actual zooming
        super().wheelEvent(ev, axis=axis)
        
        # Restore both axes to be mouse-enabled
        self.setMouseEnabled(x=True, y=True)
        
        # Accept the event
        ev.accept()


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
    
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create plot widget with dark theme and custom ViewBox
        pg.setConfigOptions(antialias=True)
        
        # Create custom ViewBox for independent axis control
        view_box = CustomViewBox()
        self.plot_widget = pg.PlotWidget(viewBox=view_box)
        
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
        self.plot_widget.getAxis('left').setPen(axis_color)
        self.plot_widget.getAxis('left').setTextPen(axis_color)
        self.plot_widget.getAxis('bottom').setPen(axis_color)
        self.plot_widget.getAxis('bottom').setTextPen(axis_color)
        
        # Labels with light color
        label_style = {'color': '#cccccc', 'font-size': '12pt'}
        self.plot_widget.setLabel('left', 'Voltage', units='mV', **label_style)
        self.plot_widget.setLabel('bottom', 'Time', **label_style)
        self.plot_widget.setTitle('Oscilloscope Waveform', color='#cccccc', size='14pt')
        
        # Enable auto-range and mouse interaction
        self.plot_widget.enableAutoRange()
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # Add legend with dark styling
        self.legend = self.plot_widget.addLegend(
            brush=(30, 30, 30, 180),
            pen={'color': '#666666', 'width': 1}
        )
        
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
                color: #cccccc;
                font-size: 10pt;
            }
            QProgressBar::chunk {
                background-color: #2196f3;
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
    
    def _parse_time_interval(self, time_interval_str: str) -> tuple:
        """
        Parse time interval string like '0.20000uS' to value and unit
        
        Returns:
            (value, unit, scale_factor_to_seconds)
        """
        # Match number and unit
        match = re.match(r'([\d.]+)\s*([a-zA-Z]+)', time_interval_str.strip())
        if not match:
            return 1.0, 'samples', 1.0
        
        value = float(match.group(1))
        unit = match.group(2)
        
        # Convert to standard units and get scale factor
        unit_map = {
            's': ('s', 1.0),
            'ms': ('ms', 1e-3),
            'us': ('µs', 1e-6),
            'uS': ('µs', 1e-6),
            'µs': ('µs', 1e-6),
            'ns': ('ns', 1e-9),
        }
        
        display_unit, scale = unit_map.get(unit, (unit, 1.0))
        return value, display_unit, scale
    
    def plot_data(self, time_series_data: TimeSeriesData, channels: List[ChannelInfo] = None):
        """
        Plot time series data with automatic downsampling
        
        Args:
            time_series_data: TimeSeriesData object containing the data to plot
            channels: List of ChannelInfo with metadata for proper axis scaling
        """
        self.time_series_data = time_series_data
        
        # Clear previous plots
        self.plot_widget.clear()
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
            # Get time interval from first channel
            time_interval_str = channels[0].time_interval
            interval_value, time_unit, scale = self._parse_time_interval(time_interval_str)
            
            # Calculate actual time array (index * time_interval)
            # Convert to appropriate unit for display
            time_values = time_series_data.indices * interval_value
            
            # Update X-axis label
            self.plot_widget.setLabel('bottom', f'Time ({time_unit})')
        else:
            # Fallback to sample indices
            time_values = time_series_data.indices
            self.plot_widget.setLabel('bottom', 'Sample Index')
        
        # Plot each channel with ALL data (PyQtGraph will handle downsampling)
        plot_items = []
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
                time_interval_str = channels[0].time_interval
                interval_value, unit, scale = self._parse_time_interval(time_interval_str)
                total_duration = num_samples * interval_value
                duration_str = f" | Duration: {total_duration:.3f} {unit}"
            
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
        
        # Auto-range to show all data
        self.plot_widget.autoRange()
        
        # Disable auto-ranging after initial display
        self.plot_widget.enableAutoRange(False)
    
    def clear(self):
        """Clear the plot"""
        self.plot_widget.clear()
        self.time_series_data = None
        self.info_label.setText("No data loaded")
    
    def set_loading_progress(self, value: int, message: str):
        """Update loading progress bar"""
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{message} - {value}%")
        if not self.progress_bar.isVisible():
            self.progress_bar.show()
    
    def hide_progress(self):
        """Hide the progress bar"""
        self.progress_bar.hide()

