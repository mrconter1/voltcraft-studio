"""Background file loader thread for Voltcraft Studio"""
from PyQt6.QtCore import QThread, pyqtSignal
from .parser import ChannelDataParser


class FileLoaderThread(QThread):
    """Background thread for loading and parsing files"""
    metadata_loaded = pyqtSignal(list)  # Emits channel info early
    finished = pyqtSignal(list, object)  # Emits (list of ChannelInfo, TimeSeriesData)
    error = pyqtSignal(str)  # Emits error message
    progress = pyqtSignal(int, str)  # Emits (progress percentage, status message)
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        """Load and parse the file in background with streaming"""
        try:
            import os
            
            self.progress.emit(0, "Opening file...")
            
            # Parse metadata first and emit it immediately
            self.progress.emit(5, "Reading metadata...")
            channels = ChannelDataParser.parse_metadata_only(self.file_path)
            self.metadata_loaded.emit(channels)
            
            # Now parse the full data with progress callback
            def progress_callback(percent: int, message: str):
                self.progress.emit(percent, message)
            
            channels, time_series = ChannelDataParser.parse_streaming(
                self.file_path, 
                progress_callback
            )
            
            self.progress.emit(100, "Complete!")
            self.finished.emit(channels, time_series)
        except Exception as e:
            self.error.emit(str(e))

