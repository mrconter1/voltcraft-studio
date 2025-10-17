"""Parser for oscilloscope channel data files"""
from typing import List, Tuple, Callable, Optional
import numpy as np
import struct
import json
import os
import re
from .models import ChannelInfo, TimeSeriesData, DeviceInfo
from .constants import (
    PARSER_BATCH_SIZE,
    PARSER_PROGRESS_METADATA_START,
    PARSER_PROGRESS_METADATA_DONE,
    PARSER_PROGRESS_DATA_START,
    PARSER_PROGRESS_DATA_END,
    PARSER_PROGRESS_NUMPY_CONVERSION
)


class ChannelDataParser:
    """Parses oscilloscope channel metadata from file content"""
    
    MAGIC_HEADER = b'SPBXDS'
    
    @staticmethod
    def is_binary_format(file_path: str) -> bool:
        """
        Check if file is in OWON SPBXDS binary format
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file has SPBXDS magic header, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(6)
                return header == ChannelDataParser.MAGIC_HEADER
        except:
            return False
    
    @staticmethod
    def parse_binary_metadata_only(file_path: str) -> Tuple[DeviceInfo, List[ChannelInfo]]:
        """
        Parse only the channel metadata from OWON binary file (fast)
        
        Args:
            file_path: Path to the binary file to parse
            
        Returns:
            Tuple of (DeviceInfo, List of ChannelInfo objects)
        """
        with open(file_path, 'rb') as f:
            # Read and validate magic header
            magic = f.read(6)
            if magic != ChannelDataParser.MAGIC_HEADER:
                raise ValueError("Invalid SPBXDS file format")
            
            # Read JSON length (4 bytes, little-endian)
            json_length_bytes = f.read(4)
            json_length = int.from_bytes(json_length_bytes, 'little')
            
            # Read and parse JSON
            json_data_bytes = f.read(json_length)
        
        # Decode JSON with error handling
        json_text = json_data_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
        
        # Fix common JSON issues from Hantek firmware
        # 1. Remove trailing commas before ] or } (invalid JSON but common firmware bug)
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        # 2. Try to find and trim to the last valid JSON close brace
        try:
            json_data = json.loads(json_text)
        except json.JSONDecodeError:
            # Find the last '}' which should be the end of JSON
            last_brace = json_text.rfind('}')
            if last_brace != -1:
                json_text = json_text[:last_brace + 1]
                json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                json_data = json.loads(json_text)
            else:
                raise ValueError("Could not parse JSON metadata from binary file")
        
        # Extract device info
        device_info = DeviceInfo(
            model=json_data.get('MODEL'),
            idn=json_data.get('IDN')
        )
        
        # Create ChannelInfo objects from JSON channel data
        channels = []
        for channel_info in json_data.get('channel', []):
            channel = ChannelInfo.create_from_bin_data(channel_info)
            channels.append(channel)
        
        return device_info, channels
    
    @staticmethod
    def print_wave_header_info(file_path: str):
        """
        Print the binary file structure with offsets and byte values.
        
        Args:
            file_path: Path to the binary file
        """
        with open(file_path, 'rb') as f:
            # Read magic header
            magic = f.read(6)
            if magic != ChannelDataParser.MAGIC_HEADER:
                return
            
            # Read JSON length
            json_length_bytes = f.read(4)
            json_length = int.from_bytes(json_length_bytes, 'little')
            
            # Read JSON data
            json_data_bytes = f.read(json_length)
            json_text = json_data_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
            
            # Truncate JSON to first 150 characters
            json_truncated = json_text[:150]
            if len(json_text) > 150:
                json_truncated += "..."
            
            # Calculate wave header offset
            wave_header_offset = 10 + json_length
            
            # Read first 20 bytes after JSON
            wave_header = f.read(20)
            
            if len(wave_header) < 20:
                print("⚠️  Less than 20 bytes available after JSON")
                return
            
            # Format magic header bytes
            magic_hex = ' '.join(f'{b:02X}' for b in magic)
            json_len_hex = ' '.join(f'{b:02X}' for b in json_length_bytes)
            
            # Display binary file structure information
            print("\n📋 BINARY FILE STRUCTURE:")
            print(f"  0x0000, 6 bytes: {magic_hex} = '{magic.decode('utf-8')}' (Magic Header)")
            print(f"  0x0006, 4 bytes: {json_len_hex} = {json_length} bytes (JSON Length)")
            print(f"  0x000A, {json_length} bytes: JSON data (truncated): {json_truncated}")
            
            # Parse JSON to extract channel information
            json_text_full = json_data_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
            json_text_full = re.sub(r',(\s*[}\]])', r'\1', json_text_full)
            try:
                json_data = json.loads(json_text_full)
            except json.JSONDecodeError:
                last_brace = json_text_full.rfind('}')
                if last_brace != -1:
                    json_text_full = json_text_full[:last_brace + 1]
                    json_text_full = re.sub(r',(\s*[}\]])', r'\1', json_text_full)
                    json_data = json.loads(json_text_full)
                else:
                    json_data = {}
            
            # Display channel information
            channels = json_data.get('channel', [])
            print(f"\n📊 CHANNELS FROM JSON ({len(channels)} total):")
            print(f"  Formulas:")
            print(f"    offset = (reference_zero / 2) % 256")
            print(f"    scale = voltage_rate × 256")
            print(f"    voltage_mV = (raw_value - offset) × scale")
            print(f"  Wave Length Data (4 bytes): little-endian uint32")
            print(f"  Wave Samples (2 bytes each): big-endian uint16")
            print()
            
            # Track wave data offset for reading channel-specific wave data
            wave_data_offset = 10 + json_length
            f.seek(wave_data_offset)
            
            for ch_idx, ch in enumerate(channels):
                ch_name = ch.get('Index', '?')
                ch_ref_zero = ch.get('Reference_Zero', '?')
                ch_voltage_rate_str = ch.get('Voltage_Rate', '?')
                availability = ch.get('Availability_Flag', '').upper()
                
                print(f"  {ch_name}:")
                print(f"    Reference_Zero: {ch_ref_zero}")
                print(f"    Voltage_Rate: {ch_voltage_rate_str}")
                
                # Calculate offset and scale if we have valid values
                offset_val = None
                scale_val = None
                try:
                    ref_zero_int = int(ch_ref_zero)
                    # Extract numeric value from voltage rate (e.g., "0.781250mv" -> 0.781250)
                    voltage_rate_str = str(ch_voltage_rate_str).replace('mv', '').replace('mV', '')
                    voltage_rate = float(voltage_rate_str)
                    
                    # Calculate offset and scale
                    offset_val = (ref_zero_int / 2) % 256
                    scale_val = voltage_rate * 256
                    
                    print(f"    Calculations:")
                    print(f"      offset = ({ref_zero_int} / 2) % 256 = {offset_val}")
                    print(f"      scale = {voltage_rate} × 256 = {scale_val}")
                except (ValueError, TypeError):
                    print(f"    Calculations: Unable to calculate (invalid values)")
                
                # Read wave data if channel is available
                if availability == 'TRUE':
                    try:
                        # Get offset of channel length bytes
                        ch_len_offset = f.tell()
                        
                        # Read 4 bytes for channel data length
                        ch_len_bytes = f.read(4)
                        if len(ch_len_bytes) == 4:
                            ch_data_len = int.from_bytes(ch_len_bytes, 'little')
                            
                            # Format the channel length bytes
                            ch_len_hex = ' '.join(f'{b:02X}' for b in ch_len_bytes)
                            
                            # Get current offset for first data byte
                            current_offset = f.tell()
                            
                            # Read first 10 bytes of wave data
                            wave_data_preview = f.read(min(10, ch_data_len))
                            
                            print(f"    Wave Data:")
                            print(f"      0x{ch_len_offset:04X}, 4 bytes: {ch_len_hex} = {ch_data_len} bytes (Channel Data Length)")
                            print(f"      First 10 bytes (at offset 0x{current_offset:04X} / {current_offset}):")
                            
                            # Format the preview bytes in 2-byte pairs
                            for i in range(0, len(wave_data_preview), 2):
                                byte1 = wave_data_preview[i]
                                byte2 = wave_data_preview[i + 1] if i + 1 < len(wave_data_preview) else 0
                                byte_offset = current_offset + i
                                byte_hex = f'{byte1:02X} {byte2:02X}'
                                
                                # Interpret as 16-bit unsigned integer (big-endian)
                                raw_value = (byte1 << 8) | byte2
                                
                                # Calculate voltage if we have valid offset and scale
                                if offset_val is not None and scale_val is not None:
                                    voltage_mV = (raw_value - offset_val) * scale_val
                                    print(f"        0x{byte_offset:04X}, 2 bytes: {byte_hex} = {raw_value} → voltage_mV = ({raw_value} - {offset_val}) × {scale_val} = {voltage_mV}")
                                else:
                                    print(f"        0x{byte_offset:04X}, 2 bytes: {byte_hex} = {raw_value}")
                            
                            # Seek to next channel's data
                            wave_data_offset += 4 + ch_data_len
                            f.seek(wave_data_offset)
                    except Exception as e:
                        print(f"    Wave Data: Error reading ({e})")
                
                print()
    
    @staticmethod
    def parse_binary_streaming(file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[DeviceInfo, List[ChannelInfo], TimeSeriesData]:
        """
        Parse channel data from OWON binary file with streaming and progress updates
        
        Args:
            file_path: Path to the binary file to parse
            progress_callback: Optional callback function(percent, message) for progress updates
            
        Returns:
            Tuple of (DeviceInfo, List of ChannelInfo objects, TimeSeriesData object)
        """
        file_size = os.path.getsize(file_path)
        
        if progress_callback:
            progress_callback(PARSER_PROGRESS_METADATA_START, "Reading binary header...")
        
        with open(file_path, 'rb') as f:
            # Read and validate magic header
            magic = f.read(6)
            if magic != ChannelDataParser.MAGIC_HEADER:
                raise ValueError("Invalid SPBXDS file format: incorrect magic header")
            
            # Read JSON length (4 bytes, little-endian)
            json_length_bytes = f.read(4)
            json_length = int.from_bytes(json_length_bytes, 'little')
            
            # Read and parse JSON
            if progress_callback:
                progress_callback(PARSER_PROGRESS_METADATA_DONE, "Parsing metadata...")
            
            json_data_bytes = f.read(json_length)
            
            # Decode JSON with error handling
            json_text = json_data_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
            
            # Fix common JSON issues from Hantek firmware
            # 1. Remove trailing commas before ] or } (invalid JSON but common firmware bug)
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            
            # 2. Try to find and trim to the last valid JSON close brace
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError:
                # Find the last '}' which should be the end of JSON
                last_brace = json_text.rfind('}')
                if last_brace != -1:
                    json_text = json_text[:last_brace + 1]
                    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                    json_data = json.loads(json_text)
                else:
                    raise ValueError("Could not parse JSON metadata from binary file")
            
            # Extract device info
            device_info = DeviceInfo(
                model=json_data.get('MODEL'),
                idn=json_data.get('IDN')
            )
            
            # Extract channel information
            channel_configs = json_data.get('channel', [])
            channel_names = [ch.get('Index', f'CH{i}') for i, ch in enumerate(channel_configs)]
            
            # Create ChannelInfo objects
            channels = []
            for channel_info in channel_configs:
                channel = ChannelInfo.create_from_bin_data(channel_info)
                channels.append(channel)
            
            # Print wave header info
            ChannelDataParser.print_wave_header_info(file_path)
            
            # Parse binary channel data
            if progress_callback:
                progress_callback(PARSER_PROGRESS_DATA_START, "Parsing channel data...")
            
            offset = 10 + json_length
            channel_data = {name: [] for name in channel_names}
            
            last_progress = PARSER_PROGRESS_DATA_START
            
            for ch_idx, channel_config in enumerate(channel_configs):
                # Skip channels that are not available
                if channel_config.get('Availability_Flag', '').upper() != 'TRUE':
                    continue
                
                # Read channel data length (4 bytes, little-endian)
                if offset + 4 > file_size:
                    break
                
                f.seek(offset)
                data_length_bytes = f.read(4)
                if len(data_length_bytes) < 4:
                    break
                
                data_length = int.from_bytes(data_length_bytes, 'little')
                offset += 4
                
                # Extract voltage conversion parameters
                voltage_rate_str = channel_config.get('Voltage_Rate', '0.781250mv')
                probe_mag_str = channel_config.get('Probe_Magnification', '1X')
                reference_zero = channel_config.get('Reference_Zero', 0)
                
                # Parse voltage rate (e.g., "0.781250mv" -> 0.781250)
                voltage_rate = float(voltage_rate_str.replace('mv', '').replace('mV', ''))
                
                # Parse probe magnification (e.g., "10X" -> 10)
                probe_mag = float(probe_mag_str.replace('X', '').replace('x', ''))
                
                # Calculate offset and scale using the same formula as print_wave_header_info
                try:
                    ref_zero_int = int(reference_zero)
                    offset_val = (ref_zero_int / 2) % 256
                    scale_val = voltage_rate * 256
                except (ValueError, TypeError):
                    # Fallback to basic calculation if parsing fails
                    offset_val = 128
                    scale_val = voltage_rate * 256
                
                # Read and convert samples
                channel_name = channel_config.get('Index', f'CH{ch_idx}')
                sample_count = data_length // 2
                
                for i in range(sample_count):
                    f.seek(offset + i * 2)
                    sample_bytes = f.read(2)
                    if len(sample_bytes) < 2:
                        break
                    
                    # Unpack as 16-bit unsigned integer (big-endian) - matches binary format
                    byte1 = sample_bytes[0]
                    byte2 = sample_bytes[1]
                    raw_value = (byte1 << 8) | byte2
                    
                    # Convert to voltage using offset/scale formula
                    # voltage is in millivolts, apply probe magnification
                    voltage_mv = (raw_value - offset_val) * scale_val
                    voltage = voltage_mv * probe_mag / 1000.0  # Convert mV to V
                    channel_data[channel_name].append(voltage)
                
                offset += data_length
                
                # Update progress
                if progress_callback and file_size > 0:
                    progress_range = PARSER_PROGRESS_DATA_END - PARSER_PROGRESS_DATA_START
                    percent = PARSER_PROGRESS_DATA_START + int((ch_idx / len(channel_configs)) * progress_range)
                    percent = min(PARSER_PROGRESS_DATA_END, percent)
                    
                    if percent != last_progress:
                        progress_callback(percent, f"Parsing channel {channel_name}...")
                        last_progress = percent
        
        # Phase 3: Convert to numpy arrays
        if progress_callback:
            progress_callback(PARSER_PROGRESS_NUMPY_CONVERSION, "Converting to arrays...")
        
        # Create indices array from the longest channel
        max_length = max((len(data) for data in channel_data.values()), default=0)
        indices = np.arange(max_length, dtype=np.int32)
        
        # Ensure all channels have the same length
        for channel_name in channel_names:
            if len(channel_data[channel_name]) < max_length:
                channel_data[channel_name].extend([np.nan] * (max_length - len(channel_data[channel_name])))
        
        time_series = TimeSeriesData(
            indices=indices,
            channel_data={name: np.array(data, dtype=np.float32) for name, data in channel_data.items()},
            channel_names=channel_names
        )
        
        return device_info, channels, time_series
    
    @staticmethod
    def parse_metadata_only(file_path: str) -> Tuple[Optional[DeviceInfo], List[ChannelInfo]]:
        """
        Parse only the channel metadata from file (fast)
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Tuple of (DeviceInfo or None for txt files, List of ChannelInfo objects)
        """
        # Read metadata (first ~20-30 lines until 'index')
        metadata_lines = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                metadata_lines.append(line)
                if line.startswith('index'):
                    break
        
        # Parse channel names from first line
        first_line = metadata_lines[0]
        channel_names = [ch.strip() for ch in first_line.split(':')[1].split('\t') if ch.strip()]
        
        # Initialize channel data storage
        channel_data_dict = {name: {} for name in channel_names}
        
        # Parse each metadata line
        for line in metadata_lines[1:]:
            if line.startswith('index'):
                break
            
            if ':' in line:
                parts = line.split(':')
                param_name = parts[0].strip()
                values = [v.strip() for v in parts[1].split('\t') if v.strip()]
                
                # Assign values to each channel
                for j, channel_name in enumerate(channel_names):
                    if j < len(values):
                        channel_data_dict[channel_name][param_name] = values[j]
        
        # Create ChannelInfo objects
        channels = []
        for channel_name in channel_names:
            data = channel_data_dict[channel_name]
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
        
        return None, channels
    
    @staticmethod
    def parse_streaming(file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[Optional[DeviceInfo], List[ChannelInfo], TimeSeriesData]:
        """
        Parse channel data from file with streaming and progress updates
        
        Args:
            file_path: Path to the file to parse
            progress_callback: Optional callback function(percent, message) for progress updates
            
        Returns:
            Tuple of (DeviceInfo or None for txt files, List of ChannelInfo objects, TimeSeriesData object)
        """
        import os
        
        # Get file size for progress estimation
        file_size = os.path.getsize(file_path)
        
        if progress_callback:
            progress_callback(PARSER_PROGRESS_METADATA_START, "Reading metadata...")
        
        # Phase 1: Read metadata (first ~20-30 lines)
        metadata_lines = []
        data_start_line = 0
        metadata_bytes = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                metadata_lines.append(line)
                metadata_bytes += len(line.encode('utf-8'))
                if line.startswith('index'):
                    data_start_line = i + 1
                    break
        
        # Parse metadata
        if progress_callback:
            progress_callback(PARSER_PROGRESS_METADATA_DONE, "Parsing metadata...")
        
        first_line = metadata_lines[0]
        channel_names = [ch.strip() for ch in first_line.split(':')[1].split('\t') if ch.strip()]
        
        # Initialize channel data storage
        channel_data_dict = {name: {} for name in channel_names}
        
        # Parse each metadata line
        for line in metadata_lines[1:]:
            if line.startswith('index'):
                break
            
            if ':' in line:
                parts = line.split(':')
                param_name = parts[0].strip()
                values = [v.strip() for v in parts[1].split('\t') if v.strip()]
                
                # Assign values to each channel
                for j, channel_name in enumerate(channel_names):
                    if j < len(values):
                        channel_data_dict[channel_name][param_name] = values[j]
        
        # Create ChannelInfo objects
        channels = []
        for channel_name in channel_names:
            data = channel_data_dict[channel_name]
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
        
        # Phase 2: Parse time series data in batches using file size for progress
        if progress_callback:
            progress_callback(PARSER_PROGRESS_DATA_START, "Parsing data...")
        
        indices = []
        channel_data = {name: [] for name in channel_names}
        
        parse_errors = 0
        bytes_processed = metadata_bytes
        skip_header = True
        last_progress = PARSER_PROGRESS_DATA_START
        
        with open(file_path, 'r', encoding='utf-8') as f:
            # Skip to data section
            for _ in range(data_start_line):
                next(f)
            
            batch_lines = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Skip header line
                if skip_header and 'Voltage' in line:
                    skip_header = False
                    continue
                
                batch_lines.append(line)
                
                # Process batch when full
                if len(batch_lines) >= PARSER_BATCH_SIZE:
                    # Parse batch
                    for batch_line in batch_lines:
                        parts = [p.strip() for p in batch_line.split('\t') if p.strip()]
                        
                        if len(parts) < len(channel_names) + 1:
                            continue
                        
                        try:
                            index = int(parts[0])
                            indices.append(index)
                            
                            for i, channel_name in enumerate(channel_names):
                                voltage = float(parts[i + 1])
                                channel_data[channel_name].append(voltage)
                        except (ValueError, IndexError):
                            parse_errors += 1
                        
                        # Track bytes for progress estimation
                        bytes_processed += len(batch_line.encode('utf-8'))
                    
                    batch_lines = []
                    
                    # Update progress based on bytes read (DATA_START to DATA_END range)
                    if progress_callback and file_size > 0:
                        progress_range = PARSER_PROGRESS_DATA_END - PARSER_PROGRESS_DATA_START
                        percent = PARSER_PROGRESS_DATA_START + int((bytes_processed / file_size) * progress_range)
                        percent = min(PARSER_PROGRESS_DATA_END, percent)
                        
                        # Only update if percentage changed
                        if percent != last_progress:
                            progress_callback(percent, "Parsing data...")
                            last_progress = percent
            
            # Process remaining lines
            if batch_lines:
                for batch_line in batch_lines:
                    parts = [p.strip() for p in batch_line.split('\t') if p.strip()]
                    
                    if len(parts) < len(channel_names) + 1:
                        continue
                    
                    try:
                        index = int(parts[0])
                        indices.append(index)
                        
                        for i, channel_name in enumerate(channel_names):
                            voltage = float(parts[i + 1])
                            channel_data[channel_name].append(voltage)
                    except (ValueError, IndexError):
                        parse_errors += 1
        
        # Phase 3: Convert to numpy arrays
        if progress_callback:
            progress_callback(PARSER_PROGRESS_NUMPY_CONVERSION, "Converting to arrays...")
        
        time_series = TimeSeriesData(
            indices=np.array(indices, dtype=np.int32),
            channel_data={name: np.array(data, dtype=np.float32) for name, data in channel_data.items()},
            channel_names=channel_names
        )
        
        if parse_errors > 0:
            print(f"Warning: {parse_errors} lines had parse errors during data import")
        
        return None, channels, time_series

