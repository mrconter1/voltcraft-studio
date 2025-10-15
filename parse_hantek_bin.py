#!/usr/bin/env python3
"""
Hantek SPBX Format Parser
Extracts JSON metadata and waveform data from Hantek .bin files
"""

import sys
import json
import struct
from pathlib import Path


def parse_spbx_file(filepath):
    """Parse Hantek SPBX binary file format"""
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"\n{'='*70}")
    print(f"Parsing: {Path(filepath).name}")
    print(f"Total size: {len(data):,} bytes")
    print(f"{'='*70}\n")
    
    # Check magic number
    magic = data[0:4]
    if magic != b'SPBX':
        print(f"Warning: Expected 'SPBX' magic, got {magic}")
        return None
    
    print(f"✓ Magic number: {magic.decode('ascii')}")
    
    # Next 2 bytes
    subtype = data[4:6]
    print(f"✓ Subtype: {subtype.decode('ascii', errors='replace')}")
    
    # Parse length field (little-endian 32-bit int at offset 6)
    json_length = struct.unpack('<I', data[6:10])[0]
    print(f"✓ JSON length: {json_length} bytes (0x{json_length:04x})")
    
    # Extract JSON
    json_start = 10
    json_end = json_start + json_length
    
    if json_end > len(data):
        print(f"Error: JSON length extends beyond file size")
        return None
    
    json_bytes = data[json_start:json_end]
    
    # Parse JSON (strip null bytes and whitespace)
    json_text = json_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
    
    # Fix common JSON issues from Hantek firmware
    # 1. Remove trailing commas before ] or } (invalid JSON but common firmware bug)
    import re
    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
    
    try:
        config = json.loads(json_text)
        print(f"✓ JSON parsed successfully\n")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        # Debug: show the problematic area
        print(f"\nDebug info:")
        print(f"  Last 100 chars of JSON: {json_text[-100:]}")
        print(f"  Character at error position: {repr(json_text[2549:2560])}")
        
        # Try to find the actual JSON end
        try:
            # Find the last '}' which should be the end of JSON
            last_brace = json_text.rfind('}')
            if last_brace != -1:
                json_text_trimmed = json_text[:last_brace + 1]
                # Apply fix again
                json_text_trimmed = re.sub(r',(\s*[}\]])', r'\1', json_text_trimmed)
                config = json.loads(json_text_trimmed)
                print(f"\n✓ JSON parsed successfully after trimming (actual length: {len(json_text_trimmed)} bytes)\n")
            else:
                return None
        except Exception as e2:
            print(f"Failed to recover: {e2}")
            # Save problematic JSON for debugging
            with open('debug_json.txt', 'w') as f:
                f.write(json_text)
            print(f"Saved problematic JSON to debug_json.txt for inspection")
            return None
    
    # Display configuration
    print(f"{'='*70}")
    print("OSCILLOSCOPE CONFIGURATION:")
    print(f"{'='*70}\n")
    
    print(f"Model: {config.get('MODEL', 'Unknown')}")
    print(f"IDN: {config.get('IDN', 'Unknown')}")
    
    # Parse channels
    channels = config.get('channel', [])
    print(f"\nChannels: {len(channels)}")
    
    for ch in channels:
        index = ch.get('Index', '?')
        display = ch.get('Display_Switch', 'OFF')
        vscale = ch.get('Vscale', '?')
        hscale = ch.get('Hscale', '?')
        sample_rate = ch.get('Sample_Rate', '?')
        depth = ch.get('Storage_Depth', '?')
        data_len = ch.get('Data_Length', '?')
        probe = ch.get('Probe_Magnification', '?')
        voltage_rate = ch.get('Voltage_Rate', '?')
        
        print(f"\n  {index}:")
        print(f"    Display: {display}")
        print(f"    Vertical: {vscale} (Probe: {probe})")
        print(f"    Horizontal: {hscale}")
        print(f"    Sample Rate: {sample_rate}")
        print(f"    Storage Depth: {depth}")
        print(f"    Data Length: {data_len} samples")
        print(f"    Voltage Rate: {voltage_rate} per ADC unit")
        
        if 'Freq' in ch:
            print(f"    Measured Freq: {ch['Freq']}")
        if 'Cyc' in ch:
            print(f"    Measured Period: {ch['Cyc']}")
    
    # Analyze binary data section
    binary_start = json_end
    binary_data = data[binary_start:]
    binary_size = len(binary_data)
    
    print(f"\n{'='*70}")
    print("WAVEFORM DATA:")
    print(f"{'='*70}\n")
    
    print(f"Binary data starts at offset: 0x{binary_start:08x} ({binary_start:,} bytes)")
    print(f"Binary data size: {binary_size:,} bytes")
    
    # Calculate expected size
    enabled_channels = [ch for ch in channels if ch.get('Display_Switch') == 'ON']
    total_channels = len(channels)
    
    # Try to determine sample format
    try:
        first_channel_samples = int(channels[0].get('Data_Length', '0'))
        bytes_per_sample = binary_size / (total_channels * first_channel_samples) if first_channel_samples > 0 else 0
        
        print(f"\nEstimated samples per channel: {first_channel_samples:,}")
        print(f"Total channels in file: {total_channels}")
        print(f"Estimated bytes per sample: {bytes_per_sample:.2f}")
        
        if 0.9 <= bytes_per_sample <= 1.1:
            print(f"→ Likely 8-bit samples (1 byte each)")
            sample_format = 'B'  # unsigned char
            bytes_per_sample = 1
        elif 1.9 <= bytes_per_sample <= 2.1:
            print(f"→ Likely 16-bit samples (2 bytes each)")
            sample_format = 'H'  # unsigned short
            bytes_per_sample = 2
        else:
            print(f"→ Unknown sample format")
            sample_format = 'B'
            bytes_per_sample = 1
        
        # Show sample data layout
        print(f"\n{'='*70}")
        print("SAMPLE DATA PREVIEW:")
        print(f"{'='*70}\n")
        
        # Show first few samples from start of binary section
        print("First 32 bytes of waveform data:")
        hex_preview = ' '.join(f'{b:02x}' for b in binary_data[:32])
        print(f"  {hex_preview}")
        
        # Try to extract first few samples for each channel
        if bytes_per_sample in [1, 2]:
            print(f"\nFirst 10 samples (assuming {bytes_per_sample}-byte format):")
            
            for i, ch in enumerate(channels):
                ch_index = ch.get('Index', f'CH{i+1}')
                offset = i * first_channel_samples * bytes_per_sample
                
                if offset + 10 * bytes_per_sample <= len(binary_data):
                    if bytes_per_sample == 1:
                        samples = struct.unpack(f'{10}B', binary_data[offset:offset+10])
                    else:
                        samples = struct.unpack(f'<{10}H', binary_data[offset:offset+20])
                    
                    print(f"  {ch_index}: {samples}")
        
    except Exception as e:
        print(f"Error analyzing waveform data: {e}")
    
    # Return parsed data
    return {
        'config': config,
        'binary_data': binary_data,
        'binary_start': binary_start,
        'channels': channels
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python parse_hantek_bin.py <path_to_bin_file>")
        print("Example: python parse_hantek_bin.py C:\\Users\\rasmu\\Downloads\\20251015_173959b.bin")
        sys.exit(1)
    
    bin_file = sys.argv[1]
    
    if not Path(bin_file).exists():
        print(f"Error: File not found: {bin_file}")
        sys.exit(1)
    
    result = parse_spbx_file(bin_file)
    
    if result:
        print(f"\n{'='*70}")
        print("SUCCESS - File parsed successfully!")
        print(f"{'='*70}\n")
        
        # Optionally save JSON to separate file
        output_json = Path(bin_file).with_suffix('.json')
        with open(output_json, 'w') as f:
            json.dump(result['config'], f, indent=2)
        print(f"✓ Configuration saved to: {output_json}")


if __name__ == "__main__":
    main()

