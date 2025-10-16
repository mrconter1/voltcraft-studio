"""Decode processor for detecting signal patterns in oscilloscope data"""
from typing import Dict, List, Tuple, Optional
import numpy as np


# NMC9307 Instruction Set
OPCODE_MAP = {
    0b0001: "WRITE",      # Write register
    0b0010: "READ",       # Read register
    0b0011: "ERASE",      # Erase register
    0b0100: "ERAL",       # Erase all
    0b0101: "WRAL",       # Write all
    0b1000: "EWDS",       # Erase/Write disable
    0b1001: "EWEN",       # Erase/Write enable
}


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
    def parse_nmc9307_instruction(bits_str: str) -> Dict[str, any]:
        """
        Parse NMC9307 instruction from bits.
        Format: 1 dummy bit (0) + 1 start bit (1) + 4-bit opcode + 4-bit address = 10 bits
        Then optional 16-bit data for WRITE/WRAL instructions
        
        Args:
            bits_str: Binary string with at least 10 bits
        
        Returns:
            Dictionary with instruction details
        """
        if len(bits_str) < 10:
            return None
        
        # Extract components (10-bit format: dummy + start + opcode + address)
        dummy_bit = bits_str[0]
        start_bit = bits_str[1]
        opcode_bits = bits_str[2:6]
        address_bits = bits_str[6:10]
        
        opcode = int(opcode_bits, 2)
        address = int(address_bits, 2)
        
        return {
            "dummy_bit": dummy_bit,
            "start_bit": start_bit,
            "opcode": opcode,
            "opcode_bits": opcode_bits,
            "address": address,
            "address_bits": address_bits,
            "instruction_name": DecodeProcessor._get_instruction_name(opcode),
            "valid": start_bit == "1" and dummy_bit == "0"
        }
    
    @staticmethod
    def _get_instruction_name(opcode: int) -> str:
        """
        Get instruction name from 4-bit opcode.
        
        Args:
            opcode: 4-bit opcode value
        
        Returns:
            Instruction name string
        """
        # Check upper 2 bits for main opcode
        upper_bits = (opcode >> 2) & 0b11
        
        if upper_bits == 0b10:  # 10xx
            return "READ"
        elif upper_bits == 0b01:  # 01xx
            return "WRITE"
        elif upper_bits == 0b11:  # 11xx
            return "ERASE"
        elif opcode == 0b0011:
            return "EWEN"
        elif opcode == 0b0000:
            return "EWDS"
        elif opcode == 0b0010:
            return "ERAL"
        elif opcode == 0b0001:
            return "WRAL"
        else:
            return "UNKNOWN"
    
    @staticmethod
    def get_instruction_expected_length(opcode: int) -> Tuple[int, int]:
        """
        Get expected DI and DO lengths for an instruction.
        
        Args:
            opcode: 4-bit opcode value
        
        Returns:
            Tuple (di_bits, do_bits) expected lengths
        """
        upper_bits = (opcode >> 2) & 0b11
        
        if upper_bits == 0b01:  # 01xx = WRITE
            return (26, 0)  # 10-bit instruction + 16-bit data
        elif upper_bits == 0b10:  # 10xx = READ
            return (10, 17)  # 10-bit instruction, then 1 dummy bit + 16-bit data output
        elif upper_bits == 0b11:  # 11xx = ERASE
            return (10, 0)
        elif opcode == 0b0001:  # WRAL
            return (26, 0)  # 10-bit instruction + 16-bit data
        elif opcode == 0b0010:  # ERAL
            return (10, 0)
        elif opcode == 0b0011:  # EWEN
            return (10, 0)
        elif opcode == 0b0000:  # EWDS
            return (10, 0)
        else:
            return (10, 0)  # Default: instruction only
    
    @staticmethod
    def process_decode_binary(
        sk_data: np.ndarray,
        cs_data: np.ndarray,
        di_data: Optional[np.ndarray],
        do_data: Optional[np.ndarray],
        time_interval_str: str,
        sample_count: int
    ) -> Dict[str, any]:
        """
        Decode binary data using SK as clock signal, grouped by CS transactions.
        On each SK rising edge while CS is HIGH, sample DI and DO.
        Automatically parses NMC9307 instructions and separates data.
        
        Args:
            sk_data: SK (clock) channel samples
            cs_data: CS (chip select) channel samples
            di_data: DI (data input) channel samples or None
            do_data: DO (data output) channel samples or None
            time_interval_str: Time interval as string (e.g., "0.400000us")
            sample_count: Total number of samples
        
        Returns:
            Dictionary with transaction data grouped by CS activation
        """
        # Parse time interval
        time_interval_us = DecodeProcessor._parse_time_interval(time_interval_str)
        
        # Binarize all signals ONCE at the start
        sk_binary = DecodeProcessor.binarize_signal(sk_data)
        cs_binary = DecodeProcessor.binarize_signal(cs_data)
        
        # Binarize DI and DO if provided
        di_binary = DecodeProcessor.binarize_signal(di_data) if di_data is not None else None
        do_binary = DecodeProcessor.binarize_signal(do_data) if do_data is not None else None
        
        # Detect rising edges on SK
        sk_rising = DecodeProcessor.detect_rising_edge(sk_binary)
        
        # Detect CS transitions (HIGH to LOW for end of transaction, LOW to HIGH for start)
        cs_transitions = np.diff(cs_binary)  # -1 for HIGH->LOW, 1 for LOW->HIGH
        cs_transitions = np.insert(cs_transitions, 0, 0)
        
        # Group bits by CS transactions
        transactions = []
        current_transaction = None
        
        for i in range(len(sk_binary)):
            # Start of new transaction (CS LOW to HIGH transition)
            if cs_transitions[i] == 1:  # LOW to HIGH
                if current_transaction is not None:
                    transactions.append(current_transaction)
                current_transaction = {
                    "start_sample": i,
                    "start_time": i * time_interval_us,
                    "raw_di_bits": [],
                    "raw_do_bits": [],
                    "instruction": None,
                    "di_bits": [],
                    "do_bits": [],
                    "end_sample": i,
                    "end_time": i * time_interval_us
                }
            
            # Collect bits on SK rising edge while CS is HIGH
            if sk_rising[i] == 1 and cs_binary[i] == 1 and current_transaction is not None:
                current_transaction["end_sample"] = i
                current_transaction["end_time"] = i * time_interval_us
                
                if di_binary is not None:
                    bit_value = di_binary[i]
                    current_transaction["raw_di_bits"].append(str(bit_value))
                
                if do_binary is not None:
                    bit_value = do_binary[i]
                    current_transaction["raw_do_bits"].append(str(bit_value))
            
            # End of transaction (CS HIGH to LOW transition)
            if cs_transitions[i] == -1:  # HIGH to LOW
                if current_transaction is not None:
                    # Parse instruction and separate DI/DO
                    DecodeProcessor._parse_transaction(current_transaction)
                    transactions.append(current_transaction)
                    current_transaction = None
        
        # Don't forget the last transaction if CS is still active at the end
        if current_transaction is not None:
            DecodeProcessor._parse_transaction(current_transaction)
            transactions.append(current_transaction)
        
        return {
            "transactions": transactions,
            "time_interval_us": time_interval_us,
            "di_enabled": di_data is not None,
            "do_enabled": do_data is not None
        }
    
    @staticmethod
    def _parse_transaction(transaction: Dict[str, any]):
        """
        Parse instruction and separate DI/DO bits in a transaction.
        Instruction format: 1 dummy bit + 1 start bit + 4-bit opcode + 4-bit address = 10 bits
        
        Args:
            transaction: Transaction dictionary to parse in-place
        """
        di_bits_str = "".join(transaction["raw_di_bits"])
        do_bits_str = "".join(transaction["raw_do_bits"])
        
        # Parse instruction from first 10 DI bits
        if len(di_bits_str) >= 10:
            instruction = DecodeProcessor.parse_nmc9307_instruction(di_bits_str[:10])
            transaction["instruction"] = instruction
            
            if instruction and instruction["valid"]:
                opcode = instruction["opcode"]
                expected_di, expected_do = DecodeProcessor.get_instruction_expected_length(opcode)
                
                # Separate bits based on expected lengths
                transaction["di_bits"] = di_bits_str[:expected_di]
                transaction["do_bits"] = do_bits_str[:expected_do]
            else:
                # Invalid instruction (start bit != 1 or dummy bit != 0)
                transaction["di_bits"] = di_bits_str[:10]  # Show at least the instruction part
                transaction["do_bits"] = ""
        else:
            transaction["di_bits"] = di_bits_str
            transaction["do_bits"] = ""
    
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
        decode_results: Dict[str, any],
        channel_mapping: Dict[str, str],
        time_interval_str: str
    ):
        """
        Print binary decode results grouped by CS transactions with instruction parsing.
        
        Args:
            decode_results: Dictionary with transaction data from process_decode_binary
            channel_mapping: Mapping of channels to signal types
            time_interval_str: Time interval for display
        """
        transactions = decode_results["transactions"]
        di_enabled = decode_results["di_enabled"]
        do_enabled = decode_results["do_enabled"]
        
        print("\n" + "=" * 110)
        print("SERIAL DATA DECODE - NMC9307 PROTOCOL (GROUPED BY CS TRANSACTIONS)")
        print("=" * 110)
        
        # Print configuration
        print("\n📋 Configuration:")
        print(f"  Time Interval        : {time_interval_str}")
        print(f"  Decode Method        : SK rising edge (clock), sample on CS HIGH")
        print(f"  Channel Mapping:")
        for channel, signal_type in sorted(channel_mapping.items()):
            print(f"    {channel:<15} → {signal_type}")
        
        # Print transactions
        if transactions:
            print(f"\n📊 TRANSACTIONS (Total: {len(transactions)}):")
            print()
            
            total_di_bits = 0
            total_do_bits = 0
            
            for tx_idx, tx in enumerate(transactions, 1):
                start_time = tx["start_time"]
                end_time = tx["end_time"]
                
                print(f"  Transaction {tx_idx}: (CS Active: {start_time:.1f}μs → {end_time:.1f}μs)")
                
                # Print instruction if available
                if tx["instruction"]:
                    instr = tx["instruction"]
                    if instr["valid"]:
                        print(f"    📌 Instruction: {instr['instruction_name']} (Dummy: {instr['dummy_bit']}, Start: {instr['start_bit']}, Opcode: {instr['opcode_bits']}, Address: {instr['address_bits']} = {instr['address']})")
                    else:
                        print(f"    ⚠️  Invalid instruction (Dummy: {instr['dummy_bit']}, Start: {instr['start_bit']} - expected Dummy=0, Start=1)")
                
                # Print DI bits
                if di_enabled and tx["di_bits"]:
                    di_sequence = tx["di_bits"]
                    di_bits_with_spaces = " ".join([di_sequence[i:i+8] for i in range(0, len(di_sequence), 8)])
                    print(f"    📥 DI: {di_bits_with_spaces} ({len(tx['di_bits'])} bits)")
                    total_di_bits += len(tx["di_bits"])
                
                # Print DO bits
                if do_enabled and tx["do_bits"]:
                    do_sequence = tx["do_bits"]
                    
                    # For READ instructions, skip the first dummy bit
                    if tx["instruction"] and tx["instruction"]["valid"]:
                        instr_name = tx["instruction"]["instruction_name"]
                        if instr_name == "READ":
                            # Skip first dummy bit, take only 16 data bits
                            do_data = do_sequence[1:17] if len(do_sequence) > 1 else ""
                            do_bits_with_spaces = " ".join([do_data[i:i+8] for i in range(0, len(do_data), 8)])
                            print(f"    📤 DO: {do_bits_with_spaces} ({len(do_data)} bits - D15→D0)")
                            total_do_bits += len(do_data)
                        else:
                            do_bits_with_spaces = " ".join([do_sequence[i:i+8] for i in range(0, len(do_sequence), 8)])
                            print(f"    📤 DO: {do_bits_with_spaces} ({len(do_sequence)} bits)")
                            total_do_bits += len(do_sequence)
                    else:
                        do_bits_with_spaces = " ".join([do_sequence[i:i+8] for i in range(0, len(do_sequence), 8)])
                        print(f"    📤 DO: {do_bits_with_spaces} ({len(do_sequence)} bits)")
                        total_do_bits += len(do_sequence)
                
                print()
        else:
            print("\n  ⚠️  No transactions detected. Check channel mapping and signal levels.")
        
        # Summary
        print("=" * 110)
        if transactions:
            print(f"✅ Summary:")
            print(f"  Total Transactions: {len(transactions)}")
            if di_enabled:
                print(f"  DI Total Bits: {total_di_bits} across {len([tx for tx in transactions if tx['di_bits']])} transaction(s)")
            if do_enabled:
                print(f"  DO Total Bits: {total_do_bits} across {len([tx for tx in transactions if tx['do_bits']])} transaction(s)")
        else:
            print("⚠️  No bits decoded. Check channel mapping and signal levels.")
        print("=" * 110 + "\n")
    
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
