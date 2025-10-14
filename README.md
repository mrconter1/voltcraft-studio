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

Click the folder icon in the toolbar to browse and select a data file to display.

## Features

- Clean and modern interface with custom icon
- Compact toolbar with intuitive controls
- **Background file loading with progress dialog** - handles large files (millions of rows) smoothly
- Non-blocking UI - application stays responsive during file loading
- Parses oscilloscope channel metadata (1-4 channels)
- Displays channel information in a structured table format
- Supports multiple channels (CH1, CH2, CH3, CH4)
- Shows parameters: Frequency, Period, PK-PK, Average, Vertical pos, Probe attenuation, etc.
- Error handling for file operations
- Cancellable file loading

## Project Structure

- `main.py` - Application entry point
- `main_window.py` - Main window GUI class
- `models.py` - Data models (ChannelInfo)
- `parser.py` - Channel data parser
- `icons.py` - Icon factory for UI icons
- `constants.py` - Application constants and configuration

