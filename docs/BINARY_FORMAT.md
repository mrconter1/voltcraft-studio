# DSO6084F Oscilloscope Binary File Format

## Overview

The Voltcraft DSO6084F oscilloscope uses a proprietary binary format to store waveform data. This document describes the complete file structure, decoding procedures, and mathematical formulas required to interpret the raw binary data into voltage measurements.

**Device Model:** DSO6084F  
**Magic Header:** `SPBXDS` (0x53 0x50 0x42 0x58 0x44 0x53)

### Format Source & Verification

This binary format was **reverse engineered** with help of the [OwonBinfileReader](https://github.com/RobThree/OwonBinfileReader) project. While that source provided foundational insights, it does not completely explain this format. This documentation is tailored specifically to the **Voltcraft DSO6084F** oscilloscope model and may not apply to other models or variants.

The decoding process has been verified by comparing waveform data extracted from binary files against CSV exports from the oscilloscope, ensuring accuracy of the conversion formulas and byte interpretations.

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

The oscilloscope uses **8-bit ADC samples** stored in **16-bit containers**. Raw samples must be extracted and converted to voltage using:

```python
lower_byte = (raw_16bit_BE >> 0) & 0xFF
scale = Voltage_Rate × 256

if Reference_Zero == 0:
    # Signed 8-bit interpretation
    raw = lower_byte if lower_byte < 128 else lower_byte - 256
    voltage_mV = raw × scale
else:
    # Unsigned 8-bit with offset
    raw = lower_byte
    offset = (Reference_Zero / 2) % 256
    voltage_mV = (raw - offset) × scale
```

**Key Points:**

- Each sample is stored as a 16-bit big-endian value, but only the **lower byte** contains the actual 8-bit ADC reading
- The upper byte is unused (typically 0x00)
- `Reference_Zero` determines the interpretation mode:
  - **= 0**: Signed 8-bit mode (range -128 to +127)
  - **≠ 0**: Unsigned 8-bit mode with offset (range 0 to 255)
- The scale factor of 256 converts the JSON's `Voltage_Rate` (voltage per internal unit) into voltage per raw sample value

**Calculation steps:**

1. Extract **lower_byte** from 16-bit big-endian value
2. Calculate **scale** = Voltage_Rate × 256
3. Apply interpretation based on **Reference_Zero**:
   - If 0: Apply signed conversion, then multiply by scale
   - Otherwise: Calculate offset, subtract from raw, then multiply by scale

---

## Example: Complete Decoding Walkthrough

### Channel 1 (CH1) - Unsigned Mode with Offset

**JSON Configuration:**
```json
{
  "Index": "CH1",
  "Reference_Zero": -181,
  "Voltage_Rate": 0.781250
}
```

**Step 1: Calculate scale**
```
scale = 0.781250 × 256 = 200.0
```

**Step 2: Determine interpretation mode**
```
Reference_Zero = -181 (≠ 0, so use unsigned mode with offset)
offset = (-181 / 2) % 256 = (-90.5) % 256 = 165.5
```

**Step 3: Extract lower byte from raw data**
```
Raw Data at offset 0x0A05 (binary): 00 A5
raw_16bit_BE = 0x00A5 = 165 (decimal)
lower_byte = 165 & 0xFF = 165
```

**Step 4: Calculate voltage**
```
voltage_mV = (165 - 165.5) × 200.0 = -0.5 × 200.0 = -100.0 mV
```

### Channel 2 (CH2) - Unsigned Mode with Offset

**JSON Configuration:**
```json
{
  "Index": "CH2",
  "Reference_Zero": 115,
  "Voltage_Rate": 0.312500
}
```

**Step 1: Calculate scale**
```
scale = 0.312500 × 256 = 80.0
```

**Step 2: Determine interpretation mode**
```
Reference_Zero = 115 (≠ 0, so use unsigned mode with offset)
offset = (115 / 2) % 256 = 57.5 % 256 = 57.5
```

**Step 3: Extract lower bytes from raw data**
```
Raw Data at offset 0x2626409 (binary): 00 76
raw_16bit_BE = 0x0076 = 118 (decimal)
lower_byte_1 = 118 & 0xFF = 118

Raw Data at offset 0x262640B (binary): 00 77
raw_16bit_BE = 0x0077 = 119 (decimal)
lower_byte_2 = 119 & 0xFF = 119
```

**Step 4: Calculate voltages**
```
voltage_1 = (118 - 57.5) × 80.0 = 60.5 × 80.0 = 4840.0 mV
voltage_2 = (119 - 57.5) × 80.0 = 61.5 × 80.0 = 4920.0 mV
```

### Example: Signed Mode (Reference_Zero = 0)

**JSON Configuration:**
```json
{
  "Index": "CH3",
  "Reference_Zero": 0,
  "Voltage_Rate": 1.000000
}
```

**Step 1: Calculate scale**
```
scale = 1.000000 × 256 = 256.0
```

**Step 2: Determine interpretation mode**
```
Reference_Zero = 0 (use signed 8-bit mode)
```

**Step 3: Extract lower bytes and apply signed interpretation**
```
Raw Data: 00 50  →  lower_byte = 80  →  raw = 80 (< 128, stays positive)
voltage_mV = 80 × 256.0 = 20480.0 mV

Raw Data: 00 FF  →  lower_byte = 255  →  raw = 255 - 256 = -1 (≥ 128, becomes negative)
voltage_mV = -1 × 256.0 = -256.0 mV

Raw Data: 00 80  →  lower_byte = 128  →  raw = 128 - 256 = -128
voltage_mV = -128 × 256.0 = -32768.0 mV
```
