# Voltcraft Studio

A GUI application built with PyQt6 to open and display oscilloscope channel data files.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Click the "Open File" button to browse and select a data file to display.

## Features

- Clean and modern interface with custom icon
- Parses oscilloscope channel metadata (1-4 channels)
- Displays channel information in a structured table format
- Supports multiple channels (CH1, CH2, CH3, CH4)
- Shows parameters: Frequency, Period, PK-PK, Average, Vertical pos, Probe attenuation, etc.
- Error handling for file operations

## Sample Data

A sample data file (`sample_data.txt`) is included for testing.

