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
            import time
            
            # Start timing
            start_time = time.time()
            self.progress.emit(0, "Opening file...")
            
            # Read file once into buffer
            read_start = time.time()
            with open(self.file_path, 'rb') as f:
                file_buffer = f.read()
            read_time = time.time() - read_start
            
            # Detect file format (binary or text) - reuse buffer for binary detection
            is_binary = ChannelDataParser.is_binary_format(self.file_path, file_buffer)
            
            # Parse metadata first and emit it immediately - reuse buffer
            self.progress.emit(5, "Reading metadata...")
            metadata_start = time.time()
            if is_binary:
                device_info, channels = ChannelDataParser.parse_binary_metadata_only(self.file_path, file_buffer)
            else:
                device_info, channels = ChannelDataParser.parse_metadata_only(self.file_path)
            metadata_time = time.time() - metadata_start
            self.metadata_loaded.emit(device_info, channels)
            
            # Now parse the full data with progress callback - reuse buffer for binary
            def progress_callback(percent: int, message: str):
                self.progress.emit(percent, message)
            
            parse_start = time.time()
            if is_binary:
                device_info, channels, time_series = ChannelDataParser.parse_binary_streaming(
                    self.file_path,
                    progress_callback,
                    use_parallel=True,
                    file_buffer=file_buffer
                )
            else:
                device_info, channels, time_series = ChannelDataParser.parse_streaming(
                    self.file_path, 
                    progress_callback
                )
            parse_time = time.time() - parse_start
            
            total_time = time.time() - start_time
            file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
            
            # Get CPU info
            cpu_count = os.cpu_count() or 1
            # Actual threads used is min(cpu_count, num_channels) for binary files
            channels_count = len(channels) if is_binary else len(time_series.channel_names)
            threads_used = min(cpu_count, channels_count) if is_binary else 1
            
            # Print timing statistics
            print("\n" + "="*70)
            print("📊 FILE LOAD TIMING STATISTICS")
            print("="*70)
            print(f"  File: {os.path.basename(self.file_path)}")
            print(f"  Size: {file_size_mb:.2f} MB")
            print(f"  Format: {'Binary (SPBXDS)' if is_binary else 'Text (CSV)'}")
            print(f"  CPU Cores: {cpu_count} available, {threads_used} threads used for parsing")
            print(f"  Channels: {channels_count}")
            print(f"\n⏱️  Stage Times:")
            print(f"  File Read:      {read_time*1000:.2f} ms")
            print(f"  Metadata Parse: {metadata_time*1000:.2f} ms")
            print(f"  Data Parse:     {parse_time*1000:.2f} ms")
            print(f"  ─────────────────────")
            print(f"  TOTAL:          {total_time*1000:.2f} ms ({total_time:.2f}s)")
            if file_size_mb > 0:
                throughput = file_size_mb / total_time
                print(f"  Throughput:     {throughput:.2f} MB/s")
            print("="*70 + "\n")
            
            self.progress.emit(100, "Complete!")
            self.finished.emit(device_info, channels, time_series)
        except Exception as e:
            self.error.emit(str(e))

