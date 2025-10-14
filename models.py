"""Data models for Voltcraft Studio"""
from dataclasses import dataclass


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

