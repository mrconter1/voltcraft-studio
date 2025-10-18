"""
Debug script to compare binary byte pairs with CSV voltage values.
This creates a mapping table showing raw binary values and their corresponding
voltages from the oscilloscope's CSV export for verification.
"""

import sys
import struct
import json
import re
from pathlib import Path


def parse_csv_file(csv_path):
    """Parse oscilloscope CSV export file"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Parse metadata
    metadata = {}
    data_start_idx = 0
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('index,'):
            data_start_idx = i + 1
            break
        
        if ':' in line:
            parts = line.split(':,')
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                metadata[key] = value
    
    # Parse voltage data
    voltages = []
    for line in lines[data_start_idx:]:
        line = line.strip()
        if not line:
            continue
        
        parts = line.split(',')
        if len(parts) >= 2:
            try:
                index = int(parts[0])
                voltage = float(parts[1])
                voltages.append((index, voltage))
            except ValueError:
                continue
    
    return metadata, voltages


def parse_binary_file(bin_path):
    """Parse oscilloscope binary file"""
    with open(bin_path, 'rb') as f:
        file_buffer = f.read()
    
    # Validate magic header
    magic = file_buffer[0:6]
    if magic != b'SPBXDS':
        raise ValueError("Invalid SPBXDS file format")
    
    # Read JSON length
    json_length = int.from_bytes(file_buffer[6:10], 'little')
    
    # Parse JSON metadata
    json_data_bytes = file_buffer[10:10 + json_length]
    json_text = json_data_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
    
    try:
        json_data = json.loads(json_text)
    except json.JSONDecodeError:
        last_brace = json_text.rfind('}')
        if last_brace != -1:
            json_text = json_text[:last_brace + 1]
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            json_data = json.loads(json_text)
        else:
            raise ValueError("Could not parse JSON metadata")
    
    # Get first available channel
    channels = json_data.get('channel', [])
    if not channels:
        raise ValueError("No channels found in binary file")
    
    channel_metadata = channels[0]
    
    # Read wave data for first channel
    wave_data_offset = 10 + json_length
    data_length = int.from_bytes(file_buffer[wave_data_offset:wave_data_offset+4], 'little')
    
    data_start = wave_data_offset + 4
    data_end = data_start + data_length
    channel_bytes = file_buffer[data_start:data_end]
    
    # Parse as 16-bit big-endian values
    byte_pairs = []
    for i in range(0, len(channel_bytes), 2):
        if i + 1 < len(channel_bytes):
            byte1 = channel_bytes[i]
            byte2 = channel_bytes[i + 1]
            raw_16bit = (byte1 << 8) | byte2
            byte_pairs.append((byte1, byte2, raw_16bit))
    
    return channel_metadata, byte_pairs


def create_mapping_table(csv_path, bin_path, output_path):
    """Create mapping table comparing binary and CSV values"""
    
    print(f"Reading CSV file: {csv_path}")
    csv_metadata, csv_voltages = parse_csv_file(csv_path)
    
    print(f"Reading binary file: {bin_path}")
    bin_metadata, byte_pairs = parse_binary_file(bin_path)
    
    # Extract key parameters
    reference_zero = bin_metadata.get('Reference_Zero', '?')
    voltage_rate = bin_metadata.get('Voltage_Rate', '?')
    probe_mag = bin_metadata.get('Probe_Magnification', '?')
    channel_name = bin_metadata.get('Index', '?')
    
    print(f"Channel: {channel_name}")
    print(f"Reference_Zero: {reference_zero}")
    print(f"Voltage_Rate: {voltage_rate}")
    print(f"Binary samples: {len(byte_pairs)}")
    print(f"CSV samples: {len(csv_voltages)}")
    
    # Create mapping with unique values
    mapping = {}
    
    for i, (byte1, byte2, raw_16bit) in enumerate(byte_pairs):
        if i < len(csv_voltages):
            csv_index, csv_voltage = csv_voltages[i]
            
            # Store unique byte pairs
            key = (byte1, byte2, raw_16bit)
            if key not in mapping:
                mapping[key] = []
            mapping[key].append(csv_voltage)
    
    # Write output file
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write channel info
        f.write(f"Channel: {channel_name}\n")
        f.write(f"Reference_Zero: {reference_zero}\n")
        f.write(f"Voltage_Rate: {voltage_rate}\n")
        f.write(f"Probe_Magnification: {probe_mag}\n")
        f.write(f"\n")
        
        # CSV metadata
        f.write(f"CSV Metadata:\n")
        for key, value in csv_metadata.items():
            f.write(f"  {key}: {value}\n")
        f.write(f"\n")
        
        # Write simple CSV header
        f.write(f"UpperByte,LowerByte,Voltage_mV\n")
        
        # Sort by raw value for easier reading
        sorted_mapping = sorted(mapping.items(), key=lambda x: x[0][2])
        
        # Write each unique mapping
        for (byte1, byte2, raw_16bit), csv_values in sorted_mapping:
            upper_byte = byte1
            lower_byte = byte2
            
            # Calculate average CSV voltage for this byte pair
            avg_csv_voltage = sum(csv_values) / len(csv_values)
            
            f.write(f"{upper_byte:02X},{lower_byte:02X},{avg_csv_voltage}\n")
    
    print(f"\nMapping table written to: {output_path}")
    print(f"Unique byte pairs found: {len(mapping)}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python debug_byte_mapping.py <csv_file> <bin_file>")
        print("\nExample:")
        print("  python debug_byte_mapping.py data.csv data.bin")
        print("\nThis will create a file 'byte_mapping_comparison.txt' with the mapping table.")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    bin_path = sys.argv[2]
    
    # Validate files exist
    if not Path(csv_path).exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    if not Path(bin_path).exists():
        print(f"Error: Binary file not found: {bin_path}")
        sys.exit(1)
    
    # Create output filename based on input files
    output_path = "byte_mapping_comparison.txt"
    
    try:
        create_mapping_table(csv_path, bin_path, output_path)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

