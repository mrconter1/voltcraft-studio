"""Decode processor for detecting signal patterns in oscilloscope data"""
from typing import Dict, List, Tuple, Optional
import numpy as np


class DecodeProcessor:
    """Process decoded signal patterns with binarization"""
    
    @staticmethod
    def binarize_signal(data: np.ndarray) -> np.ndarray:
        """
        Binarize a signal using threshold at midpoint.
        Values above midpoint become 1, below become 0.
        """
        if len(data) == 0:
            return data
        
        min_val = np.min(data)
        max_val = np.max(data)
        threshold = (min_val + max_val) / 2
        return (data > threshold).astype(int)
    
    @staticmethod
    def detect_rising_edge(binary_signal: np.ndarray) -> np.ndarray:
        """
        Detect rising edges in a binary signal.
        Returns array where 1 indicates a rising edge (0->1 transition).
        """
        if len(binary_signal) < 2:
            return np.zeros(len(binary_signal), dtype=int)
        
        edges = np.diff(binary_signal)
        # Rising edge is when diff == 1 (previous was 0, current is 1)
        rising_edges = (edges == 1).astype(int)
        # Prepend 0 to maintain same length
        rising_edges = np.insert(rising_edges, 0, 0)
        return rising_edges
    
    @staticmethod
    def process_decode(
        sk_data: np.ndarray,
        cs_data: np.ndarray,
        di_data: np.ndarray,
        time_interval_str: str,
        sample_count: int
    ) -> List[Tuple[int, float, str]]:
        """
        Process decode: detect when SK HIGH + CS HIGH + DI rising edge.
        
        Args:
            sk_data: SK channel samples
            cs_data: CS channel samples
            di_data: DI channel samples
            time_interval_str: Time interval as string (e.g., "0.400000us")
            sample_count: Total number of samples
        
        Returns:
            List of tuples: (sample_index, time_us, description)
        """
        # Parse time interval (e.g., "0.400000us" -> 0.4)
        time_interval_us = DecodeProcessor._parse_time_interval(time_interval_str)
        
        # Binarize all signals
        sk_binary = DecodeProcessor.binarize_signal(sk_data)
        cs_binary = DecodeProcessor.binarize_signal(cs_data)
        di_binary = DecodeProcessor.binarize_signal(di_data)
        
        # Detect rising edges on DI
        di_rising = DecodeProcessor.detect_rising_edge(di_binary)
        
        # Find events where: SK HIGH + CS HIGH + DI rising edge
        events = []
        
        for i in range(len(sk_binary)):
            # Check all three conditions
            sk_high = sk_binary[i] == 1
            cs_high = cs_binary[i] == 1
            di_edge = di_rising[i] == 1
            
            if sk_high and cs_high and di_edge:
                time_us = i * time_interval_us
                event_desc = f"SK=HIGH, CS=HIGH, DI=↑ (rising edge)"
                events.append((i, time_us, event_desc))
        
        return events
    
    @staticmethod
    def _parse_time_interval(interval_str: str) -> float:
        """
        Parse time interval string like "0.400000us" to float (microseconds).
        
        Args:
            interval_str: String like "0.400000us"
        
        Returns:
            Float value in microseconds
        """
        # Remove whitespace and convert to lowercase
        interval_str = interval_str.strip().lower()
        
        # Remove unit suffix
        if interval_str.endswith('us'):
            interval_str = interval_str[:-2]
        elif interval_str.endswith('ms'):
            interval_str = interval_str[:-2]
        elif interval_str.endswith('ns'):
            interval_str = interval_str[:-2]
        
        try:
            return float(interval_str)
        except ValueError:
            # Default to 1us if parsing fails
            return 1.0
    
    @staticmethod
    def print_decode_results(
        events: List[Tuple[int, float, str]],
        channel_mapping: Dict[str, str],
        time_interval_str: str
    ):
        """
        Print decode results to terminal in a formatted way.
        
        Args:
            events: List of detected events
            channel_mapping: Mapping of channels to signal types
            time_interval_str: Time interval for display
        """
        print("\n" + "=" * 80)
        print("SIGNAL DECODE RESULTS - PATTERN: SK HIGH + CS HIGH + DI ↑ (RISING EDGE)")
        print("=" * 80)
        
        # Print configuration
        print("\n📋 Configuration:")
        print(f"  Time Interval        : {time_interval_str}")
        print(f"  Channel Mapping:")
        for channel, signal_type in sorted(channel_mapping.items()):
            print(f"    {channel:<15} → {signal_type}")
        
        # Print events
        print(f"\n📊 Events Detected: {len(events)}")
        if events:
            print("\n  Sample #    | Time (μs)     | Event Description")
            print("  " + "-" * 70)
            for sample_idx, time_us, description in events:
                print(f"  {sample_idx:<11} | {time_us:>13.4f} | {description}")
        else:
            print("  ❌ No events detected matching the pattern.")
        
        # Summary
        print("\n" + "=" * 80)
        if events:
            print(f"✅ Total Events: {len(events)}")
        else:
            print("⚠️  No events found. Check channel mapping and signal levels.")
        print("=" * 80 + "\n")
