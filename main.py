"""
Voltcraft Studio - Oscilloscope Data Viewer

A GUI application for viewing and analyzing oscilloscope channel data.
"""
import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
