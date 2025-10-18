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


def parse_csv_txt_file(file_path):
    """Parse oscilloscope CSV or TXT export file - supports multiple channels"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Detect delimiter (comma for CSV, tab for TXT)
    delimiter = '\t' if '\t' in lines[0] else ','
    
    # Parse metadata header
    metadata_by_channel = {}
    channel_names = []
    data_start_idx = 0
    
    for i, line in enumerate(lines):
        line = line.rstrip()
        if not line:
            continue
        
        # Check if this is the data header line
        if line.startswith('index'):
            parts = [p.strip() for p in line.split(delimiter) if p.strip()]
            # Extract channel names from column headers like "CH1_Voltage(mV)"
            # Reset channel_names to avoid duplicates
            detected_channels = []
            for part in parts[1:]:  # Skip 'index' column
                if '_Voltage' in part:
                    ch_name = part.split('_')[0]
                    detected_channels.append(ch_name)
            
            # Use detected channels if we found any, otherwise keep the ones from metadata
            if detected_channels:
                channel_names = detected_channels
            
            data_start_idx = i + 1
            break
        
        # Parse metadata line
        if ':' in line:
            parts = line.split(':')
            if len(parts) >= 2:
                key = parts[0].strip()
                # Split values by delimiter
                values = [v.strip() for v in parts[1].split(delimiter) if v.strip()]
                
                # First time we see "Channel" key, initialize channel list
                if not channel_names and 'Channel' in key:
                    channel_names = values
                    for ch_name in channel_names:
                        metadata_by_channel[ch_name] = {}
                elif channel_names:
                    # Assign metadata values to each channel
                    for j, value in enumerate(values):
                        if j < len(channel_names):
                            ch_name = channel_names[j]
                            if ch_name not in metadata_by_channel:
                                metadata_by_channel[ch_name] = {}
                            metadata_by_channel[ch_name][key] = value
    
    # Parse voltage data for all channels
    voltages_by_channel = {ch: [] for ch in channel_names}
    
    lines_processed = 0
    lines_skipped = 0
    
    for line in lines[data_start_idx:]:
        line = line.strip()
        if not line:
            continue
        
        parts = [p.strip() for p in line.split(delimiter) if p.strip()]
        
        # Debug: check what we're getting
        if len(parts) < len(channel_names) + 1:
            lines_skipped += 1
            continue
        
        try:
            index = int(parts[0])
            for j, ch_name in enumerate(channel_names):
                if j + 1 < len(parts):
                    voltage = float(parts[j + 1])
                    voltages_by_channel[ch_name].append((index, voltage))
            lines_processed += 1
        except (ValueError, IndexError) as e:
            lines_skipped += 1
            continue
    
    # Debug output
    if lines_processed == 0 and lines_skipped > 0:
        print(f"Warning: No voltage data parsed. Skipped {lines_skipped} lines. Data starts at line {data_start_idx}")
        print(f"Channel names detected: {channel_names}")
        print(f"Delimiter: {'TAB' if delimiter == chr(9) else 'COMMA'}")
        if data_start_idx < len(lines):
            print(f"First data line: {repr(lines[data_start_idx][:100])}")
    
    return channel_names, metadata_by_channel, voltages_by_channel


def parse_binary_file(bin_path):
    """Parse oscilloscope binary file - supports multiple channels"""
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
    
    # Get all channels
    channels = json_data.get('channel', [])
    if not channels:
        raise ValueError("No channels found in binary file")
    
    # Read wave data for all channels
    wave_data_offset = 10 + json_length
    channel_data = {}
    
    for channel_config in channels:
        channel_name = channel_config.get('Index', '?')
        availability = channel_config.get('Availability_Flag', '').upper()
        
        if availability != 'TRUE':
            # Skip unavailable channels, but still advance offset if data exists
            if wave_data_offset + 4 <= len(file_buffer):
                data_length = int.from_bytes(file_buffer[wave_data_offset:wave_data_offset+4], 'little')
                wave_data_offset += 4 + data_length
            continue
        
        # Read channel data length
        if wave_data_offset + 4 > len(file_buffer):
            break
        
        data_length = int.from_bytes(file_buffer[wave_data_offset:wave_data_offset+4], 'little')
        
        data_start = wave_data_offset + 4
        data_end = data_start + data_length
        if data_end > len(file_buffer):
            data_end = len(file_buffer)
        
        channel_bytes = file_buffer[data_start:data_end]
        
        # Parse as 16-bit big-endian values
        byte_pairs = []
        for i in range(0, len(channel_bytes), 2):
            if i + 1 < len(channel_bytes):
                byte1 = channel_bytes[i]
                byte2 = channel_bytes[i + 1]
                raw_16bit = (byte1 << 8) | byte2
                byte_pairs.append((byte1, byte2, raw_16bit))
        
        channel_data[channel_name] = {
            'metadata': channel_config,
            'byte_pairs': byte_pairs
        }
        
        # Advance offset for next channel
        wave_data_offset = data_end
    
    return channel_data


def create_mapping_table(csv_path, bin_path, output_path):
    """Create mapping table comparing binary and CSV values for all channels"""
    
    print(f"Reading CSV/TXT file: {csv_path}")
    csv_channel_names, csv_metadata_by_channel, csv_voltages_by_channel = parse_csv_txt_file(csv_path)
    
    print(f"Reading binary file: {bin_path}")
    bin_channel_data = parse_binary_file(bin_path)
    
    print(f"Found {len(csv_channel_names)} channels in CSV/TXT file")
    print(f"Found {len(bin_channel_data)} channels in binary file")
    
    # Write output file
    with open(output_path, 'w', encoding='utf-8') as f:
        
        # Process each channel
        for channel_name in csv_channel_names:
            if channel_name not in bin_channel_data:
                print(f"Warning: Channel {channel_name} not found in binary file, skipping")
                continue
            
            if channel_name not in csv_voltages_by_channel:
                print(f"Warning: Channel {channel_name} not found in CSV file, skipping")
                continue
            
            bin_metadata = bin_channel_data[channel_name]['metadata']
            byte_pairs = bin_channel_data[channel_name]['byte_pairs']
            csv_voltages = csv_voltages_by_channel[channel_name]
            csv_metadata = csv_metadata_by_channel.get(channel_name, {})
            
            # Extract key parameters
            reference_zero = bin_metadata.get('Reference_Zero', '?')
            voltage_rate = bin_metadata.get('Voltage_Rate', '?')
            probe_mag = bin_metadata.get('Probe_Magnification', '?')
            
            print(f"\nProcessing {channel_name}:")
            print(f"  Reference_Zero: {reference_zero}")
            print(f"  Voltage_Rate: {voltage_rate}")
            print(f"  Binary samples: {len(byte_pairs)}")
            print(f"  CSV samples: {len(csv_voltages)}")
            
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
            
            # Write channel header
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
            
            # Write each unique mapping (as integers)
            for (byte1, byte2, raw_16bit), csv_values in sorted_mapping:
                upper_byte = byte1
                lower_byte = byte2
                
                # Calculate average CSV voltage and round to integer
                avg_csv_voltage = sum(csv_values) / len(csv_values)
                voltage_int = int(round(avg_csv_voltage))
                
                f.write(f"{upper_byte:02X},{lower_byte:02X},{voltage_int}\n")
            
            print(f"  Unique byte pairs: {len(mapping)}")
            
            # Add spacing between channels
            f.write(f"\n")
    
    print(f"\nMapping table written to: {output_path}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python debug_byte_mapping.py <csv_or_txt_file> <bin_file>")
        print("\nExample:")
        print("  python debug_byte_mapping.py data.csv data.bin")
        print("  python debug_byte_mapping.py data.txt data.bin")
        print("\nSupports both CSV and TXT oscilloscope export formats.")
        print("This will create a file 'byte_mapping_comparison.txt' with the mapping table.")
        print("For multi-channel files, all channels will be processed and included in the output.")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    bin_path = sys.argv[2]
    
    # Validate files exist
    if not Path(csv_path).exists():
        print(f"Error: File not found: {csv_path}")
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

