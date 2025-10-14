"""
Voltcraft Studio - Oscilloscope Data Viewer

A GUI application for viewing and analyzing oscilloscope channel data.
"""
import sys
import argparse
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow


def main():
    """Application entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Voltcraft Studio - Oscilloscope Data Viewer',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'file',
        nargs='?',
        help='Path to oscilloscope data file to load on startup'
    )
    args = parser.parse_args()
    
    # Create application
    app = QApplication(sys.argv)
    window = MainWindow(initial_file=args.file)
    window.showMaximized()  # Start maximized for better data visualization
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
