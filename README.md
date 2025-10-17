# Voltcraft Studio

Interactive oscilloscope waveform viewer with measurement tools and GPU acceleration.

## Hardware Compatibility

**Tested and Verified:**
- Voltcraft DSO-6084F Digital Storage Oscilloscope

Compatible with oscilloscope text data files containing channel metadata and time-series voltage measurements.

## 📖 Documentation

For detailed information about the DSO6084F binary file format, including file structure, decoding procedures, and voltage conversion formulas, see **[BINARY_FORMAT.md](docs/BINARY_FORMAT.md)**.

This includes:
- Complete file structure breakdown
- Magic header and JSON metadata parsing
- Channel data format specifications
- Voltage conversion formulas with examples
- Byte order reference and implementation checklist

## 🚀 Quick Start

### Download (Windows)
Download `VoltcraftStudio.exe` from [Releases](https://github.com/mrconter1/voltcraft-studio/releases) - no installation required!

```bash
VoltcraftStudio.exe                    # Run directly
VoltcraftStudio.exe "data.txt"         # Load file on startup
```

### Run from Source
```bash
pip install -r requirements.txt
python main.py "data.txt"              # Optional: Load file on startup
```

## Key Features

### Interactive Visualization
- **GPU-accelerated rendering** - handles millions of data points smoothly
- **Dynamic zoom/pan** - mouse wheel zoom, drag to pan, box zoom selection
- **Independent axis control** - Ctrl+Scroll (X-axis), Shift+Scroll (Y-axis)
- **Smart downsampling** - peak detection preserves spikes and glitches
- **Accurate time axis** - displays µs/ms/s based on actual metadata

### Measurement Tools
- **Tape Measure** - click two points to measure Δt and ΔV
- **Move Tool** - standard pan and zoom navigation
- Multi-channel support (CH1-CH4) with color-coded traces

### Interface
- **Tabbed layout** - Waveform view and Channel Info metadata table
- **Background loading** - responsive UI with progress tracking
- Dark theme optimized for extended viewing

## Building

See [BUILD.md](BUILD.md) for detailed build instructions and automated release setup.

**Quick build:**
```bash
python generate_icon.py
pyinstaller --clean --noconfirm build.spec
```

Output: `dist/VoltcraftStudio.exe`

## Dependencies

- PyQt6 - GUI framework
- pyqtgraph - High-performance plotting
- numpy - Numerical processing
- PyOpenGL - GPU acceleration (optional, auto-fallback to CPU)

