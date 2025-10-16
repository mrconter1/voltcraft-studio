"""Data models for Voltcraft Studio"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import numpy as np


@dataclass
class ChannelInfo:
    """Stores metadata for a single channel"""
    name: str
    frequency: str
    period: str
    pk_pk: str
    average: str
    vertical_pos: str
    probe_attenuation: str
    voltage_per_adc: str
    time_interval: str
    raw_metadata: Optional[Dict[str, Any]] = None  # Raw bin file metadata
    
    @staticmethod
    def create_from_bin_data(channel_data: Dict[str, Any]) -> 'ChannelInfo':
        """Create ChannelInfo from bin file channel data"""
        return ChannelInfo(
            name=channel_data.get('Index', '?'),
            frequency=channel_data.get('Freq', '?'),
            period=channel_data.get('Cyc', '?'),
            pk_pk='?',
            average='?',
            vertical_pos=channel_data.get('Reference_Zero', '?'),
            probe_attenuation=channel_data.get('Probe_Magnification', '?'),
            voltage_per_adc=channel_data.get('Voltage_Rate', '?'),
            time_interval=channel_data.get('Adc_Data_Time', '?'),
            raw_metadata=channel_data
        )


@dataclass
class DeviceInfo:
    """Stores device-level metadata from bin files"""
    model: Optional[str] = None
    idn: Optional[str] = None
    

@dataclass
class TimeSeriesData:
    """Stores time series data for all channels"""
    indices: np.ndarray  # Array of index values
    channel_data: Dict[str, np.ndarray]  # Channel name -> voltage array
    channel_names: List[str]  # List of channel names in order

