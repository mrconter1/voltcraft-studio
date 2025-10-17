"""
Voltcraft Studio - Oscilloscope Data Viewer

A GUI application for viewing and analyzing oscilloscope channel data.
"""
import sys
import argparse
import statistics
import time
from PyQt6.QtWidgets import QApplication
from voltcraft_studio.main_window import MainWindow
from voltcraft_studio.parser import ChannelDataParser


def benchmark_load(file_path: str, runs: int = 10):
    """
    Benchmark file loading performance by running it multiple times.
    
    Args:
        file_path: Path to the file to benchmark
        runs: Number of times to load the file
    """
    print(f"\n{'='*70}")
    print(f"🔬 BENCHMARK MODE - Loading '{file_path}' {runs} times")
    print(f"{'='*70}\n")
    
    times = []
    
    try:
        # Detect file format
        is_binary = ChannelDataParser.is_binary_format(file_path)
        
        for run in range(1, runs + 1):
            print(f"Run {run}/{runs}: ", end="", flush=True)
            
            start_time = time.time()
            
            if is_binary:
                # Read file once
                with open(file_path, 'rb') as f:
                    file_buffer = f.read()
                
                # Parse metadata
                device_info, channels = ChannelDataParser.parse_binary_metadata_only(file_path, file_buffer)
                
                # Parse full data
                device_info, channels, time_series = ChannelDataParser.parse_binary_streaming(
                    file_path,
                    progress_callback=None,
                    use_parallel=True,
                    file_buffer=file_buffer
                )
            else:
                # Text file parsing
                device_info, channels = ChannelDataParser.parse_metadata_only(file_path)
                device_info, channels, time_series = ChannelDataParser.parse_streaming(
                    file_path,
                    progress_callback=None
                )
            
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            times.append(elapsed)
            print(f"{elapsed:.2f} ms ✓")
    
    except Exception as e:
        print(f"\n❌ Error during benchmarking: {e}")
        return
    
    # Calculate statistics
    print(f"\n{'='*70}")
    print("📊 BENCHMARK RESULTS")
    print(f"{'='*70}")
    print(f"  Runs:            {runs}")
    print(f"  File Format:     {'Binary (SPBXDS)' if is_binary else 'Text (CSV)'}")
    print(f"\n⏱️  Timing Statistics (ms):")
    print(f"  Min:             {min(times):.2f} ms")
    print(f"  Max:             {max(times):.2f} ms")
    print(f"  Average:         {statistics.mean(times):.2f} ms")
    if len(times) > 1:
        print(f"  Std Dev:         {statistics.stdev(times):.2f} ms")
    print(f"  ─────────────────────")
    print(f"  Total:           {sum(times):.2f} ms")
    print(f"{'='*70}\n")


def main():
    """Application entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Voltcraft Studio - Oscilloscope Data Viewer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Launch GUI normally
  python main.py file.bin                           # Load file on startup
  python main.py file.bin --benchmark_load 10       # Benchmark load 10 times
  python main.py file.bin --enable_debug            # Enable debug output
        """
    )
    parser.add_argument(
        'file',
        nargs='?',
        help='Path to oscilloscope data file to load on startup'
    )
    parser.add_argument(
        '--benchmark_load',
        type=int,
        metavar='RUNS',
        help='Benchmark mode: load file N times and report statistics (no GUI)'
    )
    parser.add_argument(
        '--enable_debug',
        action='store_true',
        help='Enable debug output'
    )
    
    args = parser.parse_args()
    
    # Handle benchmark mode
    if args.benchmark_load:
        if not args.file:
            print("❌ Error: File path required for benchmarking")
            sys.exit(1)
        benchmark_load(args.file, args.benchmark_load)
        sys.exit(0)
    
    # Normal GUI mode
    app = QApplication(sys.argv)
    window = MainWindow(initial_file=args.file)
    window.showMaximized()  # Start maximized for better data visualization
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
