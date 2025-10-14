"""Data models for Voltcraft Studio"""
from dataclasses import dataclass
from typing import Dict, List
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


@dataclass
class TimeSeriesData:
    """Stores time series data for all channels"""
    indices: np.ndarray  # Array of index values
    channel_data: Dict[str, np.ndarray]  # Channel name -> voltage array
    channel_names: List[str]  # List of channel names in order

