"""Constants for Voltcraft Studio"""
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor


# Window settings
WINDOW_TITLE = "Voltcraft Studio"
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# Toolbar settings
TOOLBAR_ICON_SIZE = QSize(24, 24)
TOOLBAR_PADDING = 4
TOOLBAR_SPACING = 6

# Colors
COLOR_GOLD = QColor(255, 215, 0)
COLOR_DARK_GOLD = QColor(218, 165, 32)
COLOR_DARKER_GOLD = QColor(180, 130, 0)
COLOR_BLACK = QColor(0, 0, 0)
COLOR_WHITE = QColor(255, 255, 255)

# Icon sizes
WINDOW_ICON_SIZE = 64
FOLDER_ICON_SIZE = 64

# Channel parameter mappings (display label, attribute name)
CHANNEL_PARAMETERS = [
    ('Frequency', 'frequency'),
    ('Period', 'period'),
    ('PK-PK', 'pk_pk'),
    ('Average', 'average'),
    ('Vertical pos', 'vertical_pos'),
    ('Probe attenuation', 'probe_attenuation'),
    ('Voltage per ADC value', 'voltage_per_adc'),
    ('Time interval', 'time_interval')
]

# File dialog settings
FILE_DIALOG_TITLE = "Open Text File"
FILE_DIALOG_FILTER = "Text Files (*.txt);;All Files (*.*)"

# Parser settings
PARSER_BATCH_SIZE = 100000  # Number of lines to process in each batch
PARSER_PROGRESS_METADATA_START = 5  # Progress % when starting metadata read
PARSER_PROGRESS_METADATA_DONE = 10  # Progress % when metadata parsing complete
PARSER_PROGRESS_DATA_START = 15  # Progress % when starting data parsing
PARSER_PROGRESS_DATA_END = 90  # Progress % when data parsing complete
PARSER_PROGRESS_NUMPY_CONVERSION = 95  # Progress % during numpy conversion

# Help dialog text
HELP_DIALOG_TEXT = """
<h3>Tools</h3>
<p style='margin-left: 20px;'>
<b>Move Tool</b> - Pan and zoom the graph (default)<br>
<b>Tape Measure</b> - Measure time and voltage difference between two points
</p>

<h3>Mouse Controls</h3>
<p style='margin-left: 20px;'>
<b>Left Drag</b> - Pan the graph (Move tool)<br>
<b>Left Click</b> - Place measurement points (Tape tool)<br>
<b>Click & Hold</b> - Dynamic second point while dragging (Tape tool)<br>
<b>Right Drag</b> - Box zoom selection<br>
<b>Mouse Wheel</b> - Zoom both axes
</p>

<h3>Keyboard Shortcuts</h3>
<p style='margin-left: 20px;'>
<b>1</b> - Switch to Move tool<br>
<b>2</b> - Switch to Tape Measure tool<br>
<b>Ctrl + C</b> - Copy selected cells (Channel Info tab)<br>
<b>Ctrl + Scroll</b> - Zoom X-axis only (time)<br>
<b>Shift + Scroll</b> - Zoom Y-axis only (voltage)
</p>

<h3>Tape Measure Usage</h3>
<p style='margin-left: 20px;'>
1. Click to place first point<br>
2. Click to place second point OR click & hold to dynamically adjust<br>
3. Release to finalize measurement<br>
4. Click again to clear and start over
</p>

<h3>Tabs</h3>
<p style='margin-left: 20px;'>
<b>Waveform</b> - Interactive oscilloscope graph view<br>
<b>Channel Info</b> - Detailed metadata for all channels
</p>

<h3>Channel Info Table</h3>
<p style='margin-left: 20px;'>
• Click cells to select data<br>
• Click column headers to select entire columns<br>
• Click row headers to select entire rows<br>
• Press Ctrl+C to copy (includes headers when rows/columns selected)<br>
• Paste into Excel, Google Sheets, or any text editor
</p>
"""

