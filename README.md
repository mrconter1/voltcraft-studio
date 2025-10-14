# Voltcraft Studio

A GPU-accelerated oscilloscope data viewer with advanced visualization features.

## 🚀 Quick Start

### Option 1: Download Portable Executable (Windows)
Download the latest `VoltcraftStudio.exe` from the [Releases page](https://github.com/mrconter1/voltcraft-studio/releases) - no installation required!

```bash
# Run directly
VoltcraftStudio.exe

# Or load a file on startup
VoltcraftStudio.exe "path\to\your\data.txt"
```

### Option 2: Run from Source
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Or load a file on startup
python main.py "path\to\your\data.txt"
```

**Note:** For optimal performance with large datasets (millions of points), the application uses OpenGL GPU acceleration. If you experience issues, OpenGL will be automatically disabled and fallback to CPU rendering.

## Features

- Clean and modern interface with custom icon
- Compact toolbar with intuitive controls
- **Tabbed interface** for optimal workflow
  - **Waveform tab** - Full-screen graph for maximum visualization space
  - **Channel Info tab** - Clean, dark-mode metadata table
- **Interactive time series graph** - visualize voltage data across all channels
  - **Accurate time axis** - displays actual time values (µs, ms, s) from metadata, not just sample indices
  - **Full screen graph** - 100% of available space dedicated to waveform when viewing
  - Displays ALL data points (even 10M+ samples) with intelligent downsampling
  - Zoom with mouse wheel to see fine details
  - Pan by dragging to browse through data
  - **Dynamic Level-of-Detail** - automatically downsamples when zoomed out, shows actual data when zoomed in
  - OpenGL GPU acceleration for smooth rendering
  - Auto-scaling and legend
  - Handles millions of data points smoothly
- **Background file loading with progress dialog** - handles large files (millions of rows) smoothly
- Non-blocking UI - application stays responsive during file loading
- Parses oscilloscope channel metadata (1-4 channels)
- Displays channel information in a structured table format
- Supports multiple channels (CH1, CH2, CH3, CH4)
- Shows parameters: Frequency, Period, PK-PK, Average, Vertical pos, Probe attenuation, etc.
- Resizable split view between metadata table and graph
- Error handling for file operations
- Cancellable file loading

## Project Structure

- `main.py` - Application entry point
- `main_window.py` - Main window GUI class
- `graph_widget.py` - Time series graph widget with custom controls
- `loader.py` - Background file loading thread
- `parser.py` - Streaming data parser with progress tracking
- `models.py` - Data models (ChannelInfo, TimeSeriesData)
- `icons.py` - Icon factory for UI icons
- `constants.py` - Application constants and configuration
- `build.spec` - PyInstaller configuration for building .exe

## Dependencies

- PyQt6 - GUI framework
- pyqtgraph - High-performance plotting library
- numpy - Numerical array processing
- PyOpenGL - GPU acceleration (optional)

## Building

To create a portable .exe or set up automated builds, see [BUILD.md](BUILD.md)

**Quick build:**
```bash
python generate_icon.py
pyinstaller --clean --noconfirm build.spec
```

The executable will be in `dist/VoltcraftStudio.exe`

