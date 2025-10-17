"""Parser for oscilloscope channel data files"""
from typing import List, Tuple, Callable, Optional
import numpy as np
import struct
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
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
    def print_wave_header_info(file_buffer: bytes):
        """
        Print the binary file structure with offsets and byte values using file buffer.
        
        Args:
            file_buffer: Bytes buffer containing the binary file data
        """
        # Validate minimum size
        if len(file_buffer) < 10:
            print("⚠️  File too small to contain valid SPBXDS header")
            return
        
        # Read magic header
        magic = file_buffer[0:6]
        if magic != ChannelDataParser.MAGIC_HEADER:
            return
        
        # Read JSON length
        json_length_bytes = file_buffer[6:10]
        json_length = int.from_bytes(json_length_bytes, 'little')
        
        # Read JSON data
        if 10 + json_length > len(file_buffer):
            print("⚠️  Invalid JSON length - exceeds file size")
            return
        
        json_data_bytes = file_buffer[10:10 + json_length]
        json_text = json_data_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
        
        # Truncate JSON to first 150 characters
        json_truncated = json_text[:150]
        if len(json_text) > 150:
            json_truncated += "..."
        
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
                    ch_len_offset = wave_data_offset
                    
                    # Read 4 bytes for channel data length from buffer
                    if ch_len_offset + 4 <= len(file_buffer):
                        ch_len_bytes = file_buffer[ch_len_offset:ch_len_offset + 4]
                        ch_data_len = int.from_bytes(ch_len_bytes, 'little')
                        
                        # Format the channel length bytes
                        ch_len_hex = ' '.join(f'{b:02X}' for b in ch_len_bytes)
                        
                        # Get current offset for first data byte
                        current_offset = ch_len_offset + 4
                        
                        # Read first 10 bytes of wave data from buffer
                        wave_data_preview = file_buffer[current_offset:min(current_offset + 10, len(file_buffer))]
                        
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
                        
                        # Advance to next channel's data
                        wave_data_offset += 4 + ch_data_len
                except Exception as e:
                    print(f"    Wave Data: Error reading ({e})")
            
            print()
    
    @staticmethod
    def _process_single_channel(
        file_buffer: bytes,
        ch_idx: int,
        channel_config: dict,
        offset: int,
        num_channels: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        progress_lock: Optional[Lock] = None
    ) -> Tuple[str, np.ndarray]:
        """
        Process a single channel's data in parallel using vectorized NumPy operations.
        
        Args:
            file_buffer: Bytes buffer containing the binary file data
            ch_idx: Channel index
            channel_config: Channel configuration from JSON
            offset: Byte offset where this channel's data starts
            num_channels: Total number of channels (for progress calculation)
            progress_callback: Optional callback for progress updates
            progress_lock: Lock for thread-safe progress updates
            
        Returns:
            Tuple of (channel_name, NumPy array of voltage values)
        """
        # Skip channels that are not available
        if channel_config.get('Availability_Flag', '').upper() != 'TRUE':
            return channel_config.get('Index', f'CH{ch_idx}'), np.array([], dtype=np.float32)
        
        channel_name = channel_config.get('Index', f'CH{ch_idx}')
        
        # Read channel data length (4 bytes, little-endian)
        if offset + 4 > len(file_buffer):
            return channel_name, np.array([], dtype=np.float32)
        
        data_length = int.from_bytes(file_buffer[offset:offset+4], 'little')
        
        # Extract voltage conversion parameters
        voltage_rate_str = channel_config.get('Voltage_Rate', '0.781250mv')
        probe_mag_str = channel_config.get('Probe_Magnification', '1X')
        reference_zero = channel_config.get('Reference_Zero', 0)
        
        # Parse voltage rate (e.g., "0.781250mv" -> 0.781250)
        voltage_rate = float(voltage_rate_str.replace('mv', '').replace('mV', ''))
        
        # Parse probe magnification (e.g., "10X" -> 10)
        probe_mag = float(probe_mag_str.replace('X', '').replace('x', ''))
        
        # Calculate offset and scale (ONCE for this channel)
        try:
            ref_zero_int = int(reference_zero)
            offset_val = (ref_zero_int / 2) % 256
            scale_val = voltage_rate * 256
        except (ValueError, TypeError):
            offset_val = 128
            scale_val = voltage_rate * 256
        
        # Get channel data bytes
        data_start = offset + 4
        data_end = data_start + data_length
        if data_end > len(file_buffer):
            data_end = len(file_buffer)
        
        channel_bytes = file_buffer[data_start:data_end]
        
        # Vectorized approach: Convert all bytes to uint16 array at once (big-endian)
        if len(channel_bytes) < 2:
            return channel_name, np.array([], dtype=np.float32)
        
        raw_array = np.frombuffer(channel_bytes, dtype='>u2')
        
        # Vectorized transformation on entire array (all operations at once)
        voltage_array = ((raw_array - offset_val) * scale_val * probe_mag / 1000.0).astype(np.float32)
        
        # Report progress
        if progress_callback and progress_lock:
            with progress_lock:
                progress_callback(
                    PARSER_PROGRESS_DATA_START + int((ch_idx / num_channels) * (PARSER_PROGRESS_DATA_END - PARSER_PROGRESS_DATA_START)),
                    f"Parsing channel {channel_name}..."
                )
        
        return channel_name, voltage_array
    
    @staticmethod
    def parse_binary_streaming(file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None, use_parallel: bool = True) -> Tuple[DeviceInfo, List[ChannelInfo], TimeSeriesData]:
        """
        Parse channel data from OWON binary file with streaming and progress updates
        Supports both parallel and sequential processing.
        
        Args:
            file_path: Path to the binary file to parse
            progress_callback: Optional callback function(percent, message) for progress updates
            use_parallel: If True, process channels in parallel (default True)
            
        Returns:
            Tuple of (DeviceInfo, List of ChannelInfo objects, TimeSeriesData object)
        """
        file_size = os.path.getsize(file_path)
        
        if progress_callback:
            progress_callback(PARSER_PROGRESS_METADATA_START, "Reading binary file into memory...")
        
        # Read entire file into memory ONCE (more efficient for parallel processing)
        with open(file_path, 'rb') as f:
            file_buffer = f.read()
        
        if progress_callback:
            progress_callback(PARSER_PROGRESS_METADATA_START, "Reading binary header...")
        
        # Validate magic header
        if len(file_buffer) < 10:
            raise ValueError("File too small to be valid SPBXDS format")
        
        magic = file_buffer[0:6]
        if magic != ChannelDataParser.MAGIC_HEADER:
            raise ValueError("Invalid SPBXDS file format: incorrect magic header")
        
        # Read JSON length (4 bytes, little-endian)
        json_length_bytes = file_buffer[6:10]
        json_length = int.from_bytes(json_length_bytes, 'little')
        
        # Read and parse JSON
        if progress_callback:
            progress_callback(PARSER_PROGRESS_METADATA_DONE, "Parsing metadata...")
        
        if 10 + json_length > len(file_buffer):
            raise ValueError("Invalid JSON length in file header")
        
        json_data_bytes = file_buffer[10:10 + json_length]
        
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
        ChannelDataParser.print_wave_header_info(file_buffer)
        
        # Parse binary channel data
        if progress_callback:
            progress_callback(PARSER_PROGRESS_DATA_START, "Parsing channel data...")
        
        offset = 10 + json_length
        channel_data = {name: [] for name in channel_names}
        
        # Calculate offsets for all channels first
        channel_offsets = []
        temp_offset = offset
        for ch_config in channel_configs:
            channel_offsets.append(temp_offset)
            if ch_config.get('Availability_Flag', '').upper() == 'TRUE':
                # Read data length to advance offset
                if temp_offset + 4 <= len(file_buffer):
                    data_len = int.from_bytes(file_buffer[temp_offset:temp_offset+4], 'little')
                    temp_offset += 4 + data_len
            else:
                # Still need to advance even for unavailable channels
                if temp_offset + 4 <= len(file_buffer):
                    data_len = int.from_bytes(file_buffer[temp_offset:temp_offset+4], 'little')
                    temp_offset += 4 + data_len
        
        # Process channels either in parallel or sequentially
        if use_parallel and len(channel_configs) > 1:
            # Use parallel processing with ThreadPoolExecutor
            progress_lock = Lock()
            max_workers = min(4, len(channel_configs))  # Use up to 4 threads
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        ChannelDataParser._process_single_channel,
                        file_buffer,
                        ch_idx,
                        channel_configs[ch_idx],
                        channel_offsets[ch_idx],
                        len(channel_configs),
                        progress_callback,
                        progress_lock
                    ): ch_idx for ch_idx in range(len(channel_configs))
                }
                
                for future in as_completed(futures):
                    channel_name, data = future.result()
                    channel_data[channel_name] = data
        else:
            # Sequential processing (fallback for single channel or explicit request)
            for ch_idx, channel_config in enumerate(channel_configs):
                channel_name, data = ChannelDataParser._process_single_channel(
                    file_buffer,
                    ch_idx,
                    channel_config,
                    channel_offsets[ch_idx],
                    len(channel_configs),
                    progress_callback,
                    None
                )
                channel_data[channel_name] = data
        
        # Phase 3: Convert to numpy arrays
        if progress_callback:
            progress_callback(PARSER_PROGRESS_NUMPY_CONVERSION, "Converting to arrays...")
        
        # Create indices array from the longest channel
        max_length = max((len(data) for data in channel_data.values()), default=0)
        indices = np.arange(max_length, dtype=np.int32)
        
        # Ensure all channels have the same length and convert to numpy arrays if needed
        for channel_name in channel_names:
            data = channel_data[channel_name]
            # Data is already numpy array from _process_single_channel, but ensure correct length
            if len(data) < max_length:
                # Pad with NaN values
                padded = np.empty(max_length, dtype=np.float32)
                padded[:len(data)] = data
                padded[len(data):] = np.nan
                channel_data[channel_name] = padded
            elif not isinstance(data, np.ndarray):
                # Fallback in case of unexpected type
                channel_data[channel_name] = np.array(data, dtype=np.float32)
        
        time_series = TimeSeriesData(
            indices=indices,
            channel_data=channel_data,  # Already numpy arrays from threads!
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

