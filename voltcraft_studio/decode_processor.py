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
    def process_decode_binary(
        sk_data: np.ndarray,
        cs_data: np.ndarray,
        di_data: Optional[np.ndarray],
        do_data: Optional[np.ndarray],
        time_interval_str: str,
        sample_count: int
    ) -> Dict[str, List[Tuple[int, float, str, str]]]:
        """
        Decode binary data using SK as clock signal.
        On each SK rising edge while CS is HIGH, sample DI and DO.
        
        Args:
            sk_data: SK (clock) channel samples
            cs_data: CS (chip select) channel samples
            di_data: DI (data input) channel samples or None
            do_data: DO (data output) channel samples or None
            time_interval_str: Time interval as string (e.g., "0.400000us")
            sample_count: Total number of samples
        
        Returns:
            Dictionary with keys "DI" and/or "DO", each containing list of 
            (sample_index, time_us, bit_value, description)
        """
        # Parse time interval
        time_interval_us = DecodeProcessor._parse_time_interval(time_interval_str)
        
        # Binarize all signals
        sk_binary = DecodeProcessor.binarize_signal(sk_data)
        cs_binary = DecodeProcessor.binarize_signal(cs_data)
        
        # Detect rising edges on SK
        sk_rising = DecodeProcessor.detect_rising_edge(sk_binary)
        
        results = {}
        
        # Decode DI if provided
        if di_data is not None:
            di_binary = DecodeProcessor.binarize_signal(di_data)
            di_bits = []
            
            for i in range(len(sk_binary)):
                # On SK rising edge AND CS is HIGH
                if sk_rising[i] == 1 and cs_binary[i] == 1:
                    bit_value = di_binary[i]
                    time_us = i * time_interval_us
                    desc = f"DI={bit_value} (bit received)"
                    di_bits.append((i, time_us, str(bit_value), desc))
            
            results["DI"] = di_bits
        
        # Decode DO if provided
        if do_data is not None:
            do_binary = DecodeProcessor.binarize_signal(do_data)
            do_bits = []
            
            for i in range(len(sk_binary)):
                # On SK rising edge AND CS is HIGH
                if sk_rising[i] == 1 and cs_binary[i] == 1:
                    bit_value = do_binary[i]
                    time_us = i * time_interval_us
                    desc = f"DO={bit_value} (bit transmitted)"
                    do_bits.append((i, time_us, str(bit_value), desc))
            
            results["DO"] = do_bits
        
        return results
    
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
    def print_decode_results_binary(
        results: Dict[str, List[Tuple[int, float, str, str]]],
        channel_mapping: Dict[str, str],
        time_interval_str: str
    ):
        """
        Print binary decode results to terminal in a formatted way.
        
        Args:
            results: Dictionary with "DI" and/or "DO" keys containing bit events
            channel_mapping: Mapping of channels to signal types
            time_interval_str: Time interval for display
        """
        print("\n" + "=" * 90)
        print("SERIAL DATA DECODE - BINARY DECODING")
        print("=" * 90)
        
        # Print configuration
        print("\n📋 Configuration:")
        print(f"  Time Interval        : {time_interval_str}")
        print(f"  Decode Method        : SK rising edge (clock), sample on CS HIGH")
        print(f"  Channel Mapping:")
        for channel, signal_type in sorted(channel_mapping.items()):
            print(f"    {channel:<15} → {signal_type}")
        
        # Print DI bits
        if "DI" in results and results["DI"]:
            di_bits = results["DI"]
            di_sequence = "".join([bit[2] for bit in di_bits])
            print(f"\n📥 Data Input (DI) - {len(di_bits)} bits:")
            print(f"  Binary Sequence: {di_sequence}")
            print(f"  Hex (8-bit):     {DecodeProcessor._bits_to_hex(di_sequence)}")
            print(f"\n  Bit Details:")
            print("  Bit # | Sample #    | Time (μs)     | Value | Description")
            print("  " + "-" * 75)
            for bit_idx, (sample_idx, time_us, bit_val, desc) in enumerate(di_bits):
                print(f"  {bit_idx:<5} | {sample_idx:<11} | {time_us:>13.4f} | {bit_val:>5} | {desc}")
        else:
            print(f"\n📥 Data Input (DI): No data (not mapped)")
        
        # Print DO bits
        if "DO" in results and results["DO"]:
            do_bits = results["DO"]
            do_sequence = "".join([bit[2] for bit in do_bits])
            print(f"\n📤 Data Output (DO) - {len(do_bits)} bits:")
            print(f"  Binary Sequence: {do_sequence}")
            print(f"  Hex (8-bit):     {DecodeProcessor._bits_to_hex(do_sequence)}")
            print(f"\n  Bit Details:")
            print("  Bit # | Sample #    | Time (μs)     | Value | Description")
            print("  " + "-" * 75)
            for bit_idx, (sample_idx, time_us, bit_val, desc) in enumerate(do_bits):
                print(f"  {bit_idx:<5} | {sample_idx:<11} | {time_us:>13.4f} | {bit_val:>5} | {desc}")
        else:
            print(f"\n📤 Data Output (DO): No data (not mapped)")
        
        # Summary
        print("\n" + "=" * 90)
        total_bits = 0
        if "DI" in results:
            total_bits += len(results["DI"])
        if "DO" in results:
            total_bits += len(results["DO"])
        
        if total_bits > 0:
            print(f"✅ Total Bits Decoded: {total_bits}")
        else:
            print("⚠️  No bits decoded. Check channel mapping and signal levels.")
        print("=" * 90 + "\n")
    
    @staticmethod
    def _bits_to_hex(bit_string: str) -> str:
        """
        Convert binary string to hexadecimal representation.
        Pads with zeros if not multiple of 8.
        
        Args:
            bit_string: String of '0' and '1' characters
        
        Returns:
            Hex representation (e.g., "0xA5")
        """
        if not bit_string:
            return "N/A"
        
        # Pad to multiple of 8 bits
        while len(bit_string) % 8 != 0:
            bit_string = "0" + bit_string
        
        # Convert to hex
        hex_values = []
        for i in range(0, len(bit_string), 8):
            byte = bit_string[i:i+8]
            hex_val = hex(int(byte, 2))
            hex_values.append(hex_val.upper())
        
        return " ".join(hex_values)
