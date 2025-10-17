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
   │  └─ Samples: uint16 BE (S × 2 bytes)
   ├─ Channel 2
   │  ├─ Data Length: uint32 LE (4 bytes)
   │  └─ Samples: uint16 BE (S × 2 bytes)
   └─ Channel N
      ├─ Data Length: uint32 LE (4 bytes)
      └─ Samples: uint16 BE (S × 2 bytes)
```

**Note:** The number of channels (N) varies by device. The DSO6084F supports 4 channels. Each channel contains S (number of samples) 2-byte waveform samples.

---

## File Structure Details

### Header Section
**Offset:** 0x0000 | **Size:** 10 bytes

Contains the magic header and JSON length:
```
0x0000: 53 50 42 58 44 53           → "SPBXDS"
0x0006: F7 09 00 00                 → 2551 bytes (0x09F7 in little-endian)
```

### JSON Metadata Section
**Offset:** 0x000A | **Size:** Variable (specified in header)

Device information and channel configuration:

```json
{
  "MODEL": "307400101",
  "IDN": ",DSO6084F,1912044,V2.2.0",
  "channel": [
    {
      "Index": "CH1",
      "Reference_Zero": -181,
      "Voltage_Rate": 0.781250
    },
    {
      "Index": "CH2",
      "Reference_Zero": 49,
      "Voltage_Rate": 0.781250
    },
    ...
  ]
}
```

**Key Fields:**
- `Reference_Zero`: Integer offset value used in voltage calculations
- `Voltage_Rate`: Voltage scale in millivolts per unit

### Channel Data Section
**Offset:** 0x000A + JSON_LENGTH | **Size:** Varies

Sequential channel blocks, each with:
- **Data Length** (4 bytes, uint32 LE) - number of bytes in waveform
- **Samples** (S × 2 bytes, uint16 BE) - raw waveform data

**Example layout for 4 channels with 20MB each:**
```
CH1: 0x0A0A → 20,000,000 bytes
CH2: 0x1313709 → 20,000,000 bytes
...
CHN: offset calculated cumulatively
```

---

## Voltage Conversion Formula

Raw ADC values must be converted to voltage using:

```
voltage_mV = (raw_sample - offset) × scale

where:
  offset = (Reference_Zero / 2) mod 256
  scale  = Voltage_Rate × 256
```

**Calculation steps:**

1. **offset** = (Reference_Zero / 2) % 256
2. **scale** = Voltage_Rate × 256
3. **voltage_mV** = (raw_sample - offset) × scale

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

### Channel 2 (CH2)

**JSON Configuration:**
```json
{
  "Index": "CH2",
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

**Raw Data at offset 0x2626409 (binary):**
```
0x2626409: 00 76  →  raw_sample = 0x0076 = 118
0x262640B: 00 77  →  raw_sample = 0x0077 = 119
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
