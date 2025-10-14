"""Parser for oscilloscope channel data files"""
from typing import List, Tuple
import numpy as np
from models import ChannelInfo, TimeSeriesData


class ChannelDataParser:
    """Parses oscilloscope channel metadata from file content"""
    
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

