"""Parser for oscilloscope channel data files"""
from typing import List
from models import ChannelInfo


class ChannelDataParser:
    """Parses oscilloscope channel metadata from file content"""
    
    @staticmethod
    def parse(content: str) -> List[ChannelInfo]:
        """
        Parse channel metadata from file content
        
        Args:
            content: The complete file content as string
            
        Returns:
            List of ChannelInfo objects, one per channel
        """
        lines = content.split('\n')
        channels = []
        
        # Find channel names from first line
        first_line = lines[0]
        channel_names = [ch.strip() for ch in first_line.split(':')[1].split('\t') if ch.strip()]
        
        # Initialize channel data storage
        channel_data = {name: {} for name in channel_names}
        
        # Parse each metadata line
        for line in lines[1:]:
            if line.startswith('index'):
                break  # Stop at data section
            
            if ':' in line:
                parts = line.split(':')
                param_name = parts[0].strip()
                values = [v.strip() for v in parts[1].split('\t') if v.strip()]
                
                # Assign values to each channel
                for i, channel_name in enumerate(channel_names):
                    if i < len(values):
                        channel_data[channel_name][param_name] = values[i]
        
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
        
        return channels

