"""Parser for oscilloscope channel data files"""
from typing import List, Tuple, Callable, Optional
import numpy as np
from .models import ChannelInfo, TimeSeriesData
from .constants import (
    PARSER_BATCH_SIZE,
    PARSER_PROGRESS_METADATA_START,
    PARSER_PROGRESS_METADATA_DONE,
    PARSER_PROGRESS_DATA_START,
    PARSER_PROGRESS_DATA_END,
    PARSER_PROGRESS_NUMPY_CONVERSION
)


class ChannelDataParser:
    """Parses oscilloscope channel metadata from file content"""
    
    @staticmethod
    def parse_streaming(file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[List[ChannelInfo], TimeSeriesData]:
        """
        Parse channel data from file with streaming and progress updates
        
        Args:
            file_path: Path to the file to parse
            progress_callback: Optional callback function(percent, message) for progress updates
            
        Returns:
            Tuple of (List of ChannelInfo objects, TimeSeriesData object)
        """
        import os
        
        # Get file size for progress estimation
        file_size = os.path.getsize(file_path)
        
        if progress_callback:
            progress_callback(PARSER_PROGRESS_METADATA_START, "Reading metadata...")
        
        # Phase 1: Read metadata (first ~20-30 lines)
        metadata_lines = []
        data_start_line = 0
        metadata_bytes = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                metadata_lines.append(line)
                metadata_bytes += len(line.encode('utf-8'))
                if line.startswith('index'):
                    data_start_line = i + 1
                    break
        
        # Parse metadata
        if progress_callback:
            progress_callback(PARSER_PROGRESS_METADATA_DONE, "Parsing metadata...")
        
        first_line = metadata_lines[0]
        channel_names = [ch.strip() for ch in first_line.split(':')[1].split('\t') if ch.strip()]
        
        # Initialize channel data storage
        channel_data_dict = {name: {} for name in channel_names}
        
        # Parse each metadata line
        for line in metadata_lines[1:]:
            if line.startswith('index'):
                break
            
            if ':' in line:
                parts = line.split(':')
                param_name = parts[0].strip()
                values = [v.strip() for v in parts[1].split('\t') if v.strip()]
                
                # Assign values to each channel
                for j, channel_name in enumerate(channel_names):
                    if j < len(values):
                        channel_data_dict[channel_name][param_name] = values[j]
        
        # Create ChannelInfo objects
        channels = []
        for channel_name in channel_names:
            data = channel_data_dict[channel_name]
            channel = ChannelInfo(
                name=channel_name,
                frequency=data.get('Frequency', '?'),
                period=data.get('Period', '?'),
                pk_pk=data.get('PK-PK', '?'),
                average=data.get('Average', '?'),
                vertical_pos=data.get('Vertical pos', '?'),
                probe_attenuation=data.get('Probe attenuation', '?'),
                voltage_per_adc=data.get('Voltage per ADC value', '?'),
                time_interval=data.get('Time interval', '?')
            )
            channels.append(channel)
        
        # Phase 2: Parse time series data in batches using file size for progress
        if progress_callback:
            progress_callback(PARSER_PROGRESS_DATA_START, "Parsing data...")
        
        indices = []
        channel_data = {name: [] for name in channel_names}
        
        parse_errors = 0
        bytes_processed = metadata_bytes
        skip_header = True
        last_progress = PARSER_PROGRESS_DATA_START
        
        with open(file_path, 'r', encoding='utf-8') as f:
            # Skip to data section
            for _ in range(data_start_line):
                next(f)
            
            batch_lines = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Skip header line
                if skip_header and 'Voltage' in line:
                    skip_header = False
                    continue
                
                batch_lines.append(line)
                
                # Process batch when full
                if len(batch_lines) >= PARSER_BATCH_SIZE:
                    # Parse batch
                    for batch_line in batch_lines:
                        parts = [p.strip() for p in batch_line.split('\t') if p.strip()]
                        
                        if len(parts) < len(channel_names) + 1:
                            continue
                        
                        try:
                            index = int(parts[0])
                            indices.append(index)
                            
                            for i, channel_name in enumerate(channel_names):
                                voltage = float(parts[i + 1])
                                channel_data[channel_name].append(voltage)
                        except (ValueError, IndexError):
                            parse_errors += 1
                        
                        # Track bytes for progress estimation
                        bytes_processed += len(batch_line.encode('utf-8'))
                    
                    batch_lines = []
                    
                    # Update progress based on bytes read (DATA_START to DATA_END range)
                    if progress_callback and file_size > 0:
                        progress_range = PARSER_PROGRESS_DATA_END - PARSER_PROGRESS_DATA_START
                        percent = PARSER_PROGRESS_DATA_START + int((bytes_processed / file_size) * progress_range)
                        percent = min(PARSER_PROGRESS_DATA_END, percent)
                        
                        # Only update if percentage changed
                        if percent != last_progress:
                            progress_callback(percent, "Parsing data...")
                            last_progress = percent
            
            # Process remaining lines
            if batch_lines:
                for batch_line in batch_lines:
                    parts = [p.strip() for p in batch_line.split('\t') if p.strip()]
                    
                    if len(parts) < len(channel_names) + 1:
                        continue
                    
                    try:
                        index = int(parts[0])
                        indices.append(index)
                        
                        for i, channel_name in enumerate(channel_names):
                            voltage = float(parts[i + 1])
                            channel_data[channel_name].append(voltage)
                    except (ValueError, IndexError):
                        parse_errors += 1
        
        # Phase 3: Convert to numpy arrays
        if progress_callback:
            progress_callback(PARSER_PROGRESS_NUMPY_CONVERSION, "Converting to arrays...")
        
        time_series = TimeSeriesData(
            indices=np.array(indices, dtype=np.int32),
            channel_data={name: np.array(data, dtype=np.float32) for name, data in channel_data.items()},
            channel_names=channel_names
        )
        
        if parse_errors > 0:
            print(f"Warning: {parse_errors} lines had parse errors during data import")
        
        return channels, time_series

