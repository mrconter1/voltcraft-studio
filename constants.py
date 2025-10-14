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

