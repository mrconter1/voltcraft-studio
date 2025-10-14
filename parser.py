"""Parser for oscilloscope channel data files"""
from typing import List, Tuple, Callable, Optional
import numpy as np
from models import ChannelInfo, TimeSeriesData


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
        
        if progress_callback:
            progress_callback(5, "Reading metadata...")
        
        # Phase 1: Read metadata (first ~20-30 lines)
        metadata_lines = []
        data_start_line = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                metadata_lines.append(line)
                if line.startswith('index'):
                    data_start_line = i + 1
                    break
        
        # Parse metadata
        if progress_callback:
            progress_callback(10, "Parsing metadata...")
        
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
        
        # Phase 2: Count total lines for progress calculation
        if progress_callback:
            progress_callback(15, "Counting data lines...")
        
        total_lines = sum(1 for _ in open(file_path, 'r', encoding='utf-8'))
        data_lines_count = total_lines - data_start_line - 1  # -1 for header
        
        # Phase 3: Parse time series data in batches
        if progress_callback:
            progress_callback(20, "Parsing data...")
        
        indices = []
        channel_data = {name: [] for name in channel_names}
        
        BATCH_SIZE = 100000  # Process 100k lines at a time
        parse_errors = 0
        lines_processed = 0
        skip_header = True
        
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
                if len(batch_lines) >= BATCH_SIZE:
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
                    
                    lines_processed += len(batch_lines)
                    batch_lines = []
                    
                    # Update progress (20-90% for parsing)
                    if progress_callback and data_lines_count > 0:
                        percent = 20 + int((lines_processed / data_lines_count) * 70)
                        percent = min(90, percent)
                        progress_callback(percent, f"Parsing data... {lines_processed:,} lines")
            
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
        
        # Phase 4: Convert to numpy arrays
        if progress_callback:
            progress_callback(95, "Converting to arrays...")
        
        time_series = TimeSeriesData(
            indices=np.array(indices, dtype=np.int32),
            channel_data={name: np.array(data, dtype=np.float32) for name, data in channel_data.items()},
            channel_names=channel_names
        )
        
        if parse_errors > 0:
            print(f"Warning: {parse_errors} lines had parse errors during data import")
        
        return channels, time_series
    
    @staticmethod
    def parse(content: str) -> Tuple[List[ChannelInfo], TimeSeriesData]:
        """
        Parse channel metadata and time series data from file content
        
        Args:
            content: The complete file content as string
            
        Returns:
            Tuple of (List of ChannelInfo objects, TimeSeriesData object)
        """
        lines = content.split('\n')
        channels = []
        data_start_index = 0
        
        # Find channel names from first line
        first_line = lines[0]
        channel_names = [ch.strip() for ch in first_line.split(':')[1].split('\t') if ch.strip()]
        
        # Initialize channel data storage
        channel_data = {name: {} for name in channel_names}
        
        # Parse each metadata line
        for i, line in enumerate(lines[1:], start=1):
            if line.startswith('index'):
                data_start_index = i + 1  # Data starts after the index line
                break
            
            if ':' in line:
                parts = line.split(':')
                param_name = parts[0].strip()
                values = [v.strip() for v in parts[1].split('\t') if v.strip()]
                
                # Assign values to each channel
                for j, channel_name in enumerate(channel_names):
                    if j < len(values):
                        channel_data[channel_name][param_name] = values[j]
        
        # Create ChannelInfo objects
        for channel_name in channel_names:
            data = channel_data[channel_name]
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
        
        # Parse time series data
        time_series = ChannelDataParser._parse_time_series(lines[data_start_index:], channel_names)
        
        return channels, time_series
    
    @staticmethod
    def _parse_time_series(data_lines: List[str], channel_names: List[str]) -> TimeSeriesData:
        """
        Parse time series data section
        
        Args:
            data_lines: Lines containing the time series data
            channel_names: List of channel names
            
        Returns:
            TimeSeriesData object with parsed data
        """
        indices = []
        channel_data = {name: [] for name in channel_names}
        
        # Skip header line if present (e.g., "index  CH1_Voltage(mV)  CH2_Voltage(mV)")
        start_line = 0
        if data_lines and 'Voltage' in data_lines[0]:
            start_line = 1
        
        parse_errors = 0
        for line_num, line in enumerate(data_lines[start_line:], start=start_line):
            line = line.strip()
            if not line:
                continue
            
            # Split by tabs and filter out empty strings
            parts = [p.strip() for p in line.split('\t') if p.strip()]
            
            if len(parts) < len(channel_names) + 1:
                continue
                
            try:
                # First column is index
                index = int(parts[0])
                indices.append(index)
                
                # Remaining columns are channel voltages
                for i, channel_name in enumerate(channel_names):
                    voltage = float(parts[i + 1])
                    channel_data[channel_name].append(voltage)
            except (ValueError, IndexError):
                parse_errors += 1
                continue
        
        # Convert to numpy arrays for efficient plotting
        time_series = TimeSeriesData(
            indices=np.array(indices, dtype=np.int32),
            channel_data={name: np.array(data, dtype=np.float32) for name, data in channel_data.items()},
            channel_names=channel_names
        )
        
        # Optional: Log parsing summary
        if parse_errors > 0:
            print(f"Warning: {parse_errors} lines had parse errors during data import")
        
        return time_series

