# DSO6084F Oscilloscope Binary File Format

## Overview

The Voltcraft DSO6084F oscilloscope uses a proprietary binary format to store waveform data. This document describes the complete file structure, decoding procedures, and mathematical formulas required to interpret the raw binary data into voltage measurements.

**Device Model:** DSO6084F  
**Magic Header:** `SPBXDS` (0x53 0x50 0x42 0x58 0x44 0x53)

---

## Binary Structure Overview

```
SPBXDS Binary File Format
│
├─ Header (10 bytes total)
│  ├─ Magic Header: "SPBXDS" (6 bytes at offset 0x0000)
│  └─ JSON Length: uint32 LE (4 bytes at offset 0x0006)
│
├─ JSON Metadata (varies in size, starts at 0x000A)
│  └─ Single JSON object
│     ├─ MODEL
│     ├─ IDN
│     └─ channel[] (array of channel configurations)
│
└─ Channel Data (starts after JSON, varies in size)
   ├─ Channel 1
   │  ├─ Data Length: uint32 LE (4 bytes)
   │  └─ Samples: uint16 BE (N × 2 bytes)
   ├─ Channel 2
   │  ├─ Data Length: uint32 LE (4 bytes)
   │  └─ Samples: uint16 BE (N × 2 bytes)
   ├─ Channel 3
   │  ├─ Data Length: uint32 LE (4 bytes)
   │  └─ Samples: uint16 BE (N × 2 bytes)
   └─ Channel 4
      ├─ Data Length: uint32 LE (4 bytes)
      └─ Samples: uint16 BE (N × 2 bytes)
```

---

## File Structure

### 1. Header Section (10 bytes)

| Offset | Size | Field | Format | Description |
|--------|------|-------|--------|-------------|
| 0x0000 | 6    | Magic | ASCII | Fixed string: `SPBXDS` (0x53 0x50 0x42 0x58 0x44 0x53) |
| 0x0006 | 4    | JSON Length | uint32 LE | Length of JSON metadata in bytes |

**Example:**
```
0x0000: 53 50 42 58 44 53           → "SPBXDS"
0x0006: F7 09 00 00                 → 2551 bytes (0x09F7 in little-endian)
```

### 2. JSON Metadata Section

**Offset:** 0x000A  
**Size:** Variable (specified in header)

Contains device information and channel configuration in JSON format:

```json
{
  "MODEL": "307400101",
  "IDN": ",DSO6084F,1912044,V2.2.0",
  "channel": [
    {
      "Index": "CH1",
      "Availability_Flag": "TRUE",
      "Display_Switch": "OFF",
      "Reference_Zero": -181,
      "Voltage_Rate": 0.781250,
      "Wave_Character": "CH1"
    },
    {
      "Index": "CH2",
      "Availability_Flag": "TRUE",
      "Display_Switch": "ON",
      "Reference_Zero": 49,
      "Voltage_Rate": 0.781250,
      "Wave_Character": "CH2"
    },
    {
      "Index": "CH3",
      "Availability_Flag": "TRUE",
      "Display_Switch": "ON",
      "Reference_Zero": 115,
      "Voltage_Rate": 0.312500,
      "Wave_Character": "CH3"
    },
    {
      "Index": "CH4",
      "Availability_Flag": "TRUE",
      "Display_Switch": "OFF",
      "Reference_Zero": -53,
      "Voltage_Rate": 0.781250,
      "Wave_Character": "CH4"
    }
  ]
}
```

**Key Fields:**
- `Reference_Zero`: Integer offset value used in voltage calculations
- `Voltage_Rate`: Voltage scale in millivolts per unit

### 3. Channel Data Section

**Offset:** Immediately after JSON (0x000A + JSON_LENGTH)

Each channel contains sequential wave data. For a 4-channel device, the layout is:

```
[CH1 Data] [CH2 Data] [CH3 Data] [CH4 Data]
```

---

## Channel Data Format

### Channel Structure

| Offset | Size | Field | Format | Description |
|--------|------|-------|--------|-------------|
| +0     | 4    | Length | uint32 LE | Number of bytes in waveform data |
| +4     | N    | Data  | uint16 BE | Waveform samples (2 bytes each) |

**Note:** Channel offsets are calculated cumulatively; each channel's data begins after the previous one.

### Example Channel Layout

For 4 channels with 20,000,000 bytes each (0x01312D00 LE):

```
CH1: offset 0x0A0A (10250 decimal)
     Length: 0x01312D00 → 20,000,000 bytes
     Data:   20,000,000 samples
     End:    offset 0x1313709

CH2: offset 0x1313709 (20,002,569 decimal)
     Length: 0x01312D00 → 20,000,000 bytes
     Data:   20,000,000 samples
     End:    offset 0x2626407

CH3: offset 0x2626407 (40,002,567 decimal)
     Length: 0x01312D00 → 20,000,000 bytes
     Data:   20,000,000 samples
     End:    offset 0x393910B

CH4: offset 0x393910B (60,002,571 decimal)
     Length: 0x01312D00 → 20,000,000 bytes
     Data:   20,000,000 samples
```

---

## Voltage Conversion Formula

Raw ADC values must be converted to voltage using the formula:

```
voltage_mV = (raw_sample - offset) × scale

where:
  offset = (Reference_Zero / 2) mod 256
  scale  = Voltage_Rate × 256
```

### Detailed Calculation Steps

1. **Calculate Offset:**
   ```
   offset = (Reference_Zero / 2) % 256
   ```
   Uses modulo arithmetic to ensure offset is in range [0, 256)

2. **Calculate Scale:**
   ```
   scale = Voltage_Rate × 256
   ```
   Converts voltage rate to per-unit scaling factor

3. **Convert Sample:**
   ```
   voltage_mV = (raw_sample - offset) × scale
   ```
   Applies linear transformation to raw ADC value

---

## Example: Complete Decoding Walkthrough

### Channel 1 (CH1)

**JSON Configuration:**
```json
{
  "Index": "CH1",
  "Reference_Zero": -181,
  "Voltage_Rate": 0.781250
}
```

**Calculations:**
```
offset = (-181 / 2) % 256
       = (-90.5) % 256
       = 165.5

scale = 0.781250 × 256
      = 200.0
```

**Raw Data at offset 0x0A05 (binary):**
```
0x0A05: 00 A5  →  raw_sample = 0x00A5 = 165 (decimal)
```

**Voltage Conversion:**
```
voltage = (165 - 165.5) × 200.0 = -0.5 × 200.0 = -100.0 mV
```

### Channel 3 (CH3)

**JSON Configuration:**
```json
{
  "Index": "CH3",
  "Reference_Zero": 115,
  "Voltage_Rate": 0.312500
}
```

**Calculations:**
```
offset = (115 / 2) % 256
       = 57.5 % 256
       = 57.5

scale = 0.312500 × 256
      = 80.0
```

**Raw Data at offset 0x262640D (binary):**
```
0x262640D: 00 76  →  raw_sample = 0x0076 = 118
0x262640F: 00 77  →  raw_sample = 0x0077 = 119
```

**Voltage Conversion:**
```
voltage_1 = (118 - 57.5) × 80.0 = 60.5 × 80.0 = 4840.0 mV
voltage_2 = (119 - 57.5) × 80.0 = 61.5 × 80.0 = 4920.0 mV
```

---

## Byte Order Reference

| Data Type | Byte Order | Example |
|-----------|-----------|---------|
| Magic Header | ASCII | 0x53 0x50 0x42 0x58 0x44 0x53 |
| Length Fields | Little-Endian (LE) | 0xF7 0x09 0x00 0x00 = 0x000009F7 |
| Samples | Big-Endian (BE) | 0x00 0xA5 = 0x00A5 |
