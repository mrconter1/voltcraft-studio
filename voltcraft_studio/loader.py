"""Background file loader thread for Voltcraft Studio"""
from PyQt6.QtCore import QThread, pyqtSignal
from .parser import ChannelDataParser


class FileLoaderThread(QThread):
    """Background thread for loading and parsing files"""
    metadata_loaded = pyqtSignal(object, list)  # Emits (device_info, list of channel info)
    finished = pyqtSignal(object, list, object)  # Emits (device_info, list of ChannelInfo, TimeSeriesData)
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
            
            # Detect file format (binary or text)
            is_binary = ChannelDataParser.is_binary_format(self.file_path)
            
            # Parse metadata first and emit it immediately
            self.progress.emit(5, "Reading metadata...")
            if is_binary:
                device_info, channels = ChannelDataParser.parse_binary_metadata_only(self.file_path)
            else:
                device_info, channels = ChannelDataParser.parse_metadata_only(self.file_path)
            self.metadata_loaded.emit(device_info, channels)
            
            # Now parse the full data with progress callback
            def progress_callback(percent: int, message: str):
                self.progress.emit(percent, message)
            
            if is_binary:
                device_info, channels, time_series = ChannelDataParser.parse_binary_streaming(
                    self.file_path, 
                    progress_callback
                )
            else:
                device_info, channels, time_series = ChannelDataParser.parse_streaming(
                    self.file_path, 
                    progress_callback
                )
            
            self.progress.emit(100, "Complete!")
            self.finished.emit(device_info, channels, time_series)
        except Exception as e:
            self.error.emit(str(e))

