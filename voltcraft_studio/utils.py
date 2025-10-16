"""Utility functions for Voltcraft Studio"""
import re
from pathlib import Path
from pint import UnitRegistry

# Initialize Pint unit registry
ureg = UnitRegistry()


def get_version() -> str:
    """
    Get the application version from version.txt.
    
    Returns:
        str: Version string (e.g., "1.3.0") or "unknown" if not found
    """
    try:
        # Look for version.txt in the project root (parent of voltcraft_studio package)
        version_file = Path(__file__).parent.parent / "version.txt"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception:
        pass
    
    return "unknown"


def parse_time_interval(time_interval_str: str) -> tuple:
    """
    Parse time interval string like '0.20000uS' to Pint Quantity
    
    Args:
        time_interval_str: Time string like '0.20000uS', '1.5ms', etc.
    
    Returns:
        tuple: (value, unit_str, pint_quantity)
               - value: float value
               - unit_str: original unit string (for display)
               - pint_quantity: Pint Quantity object in seconds
    """
    # Match number and unit
    match = re.match(r'([\d.]+)\s*([a-zA-Z]+)', time_interval_str.strip())
    if not match:
        return 1.0, 'samples', 1.0 * ureg.dimensionless
    
    value = float(match.group(1))
    unit = match.group(2)
    
    # Map common oscilloscope units to Pint units
    unit_map = {
        's': 'second',
        'ms': 'millisecond',
        'us': 'microsecond',
        'uS': 'microsecond',
        'µs': 'microsecond',
        'ns': 'nanosecond',
    }
    
    pint_unit = unit_map.get(unit, 'dimensionless')
    
    # Create Pint quantity
    quantity = value * getattr(ureg, pint_unit)
    
    return value, unit, quantity


def format_time_auto(time_quantity, precision=4) -> str:
    """
    Automatically format time with appropriate unit for readability.
    
    Uses Pint's compact formatting to select the most readable unit.
    For example:
        - 0.000001 s -> "1.0 µs"
        - 2500000 µs -> "2.5 s"
        - 0.0025 s -> "2.5 ms"
    
    Args:
        time_quantity: Pint Quantity in time units, or float (assumed seconds)
        precision: Number of significant figures (default: 4)
    
    Returns:
        str: Formatted time string like "2.543 ms" or "15.2 µs"
    """
    # Convert to Pint quantity if needed
    if not isinstance(time_quantity, ureg.Quantity):
        time_quantity = time_quantity * ureg.second
    
    # Convert to seconds first
    time_in_seconds = time_quantity.to(ureg.second).magnitude
    
    # Determine best unit based on magnitude
    if abs(time_in_seconds) < 1e-6:
        # Use nanoseconds for very small values
        formatted = time_quantity.to(ureg.nanosecond)
        return f"{formatted.magnitude:.{precision}g} ns"
    elif abs(time_in_seconds) < 1e-3:
        # Use microseconds
        formatted = time_quantity.to(ureg.microsecond)
        return f"{formatted.magnitude:.{precision}g} µs"
    elif abs(time_in_seconds) < 1:
        # Use milliseconds
        formatted = time_quantity.to(ureg.millisecond)
        return f"{formatted.magnitude:.{precision}g} ms"
    else:
        # Use seconds
        formatted = time_quantity.to(ureg.second)
        return f"{formatted.magnitude:.{precision}g} s"


def get_best_time_unit_for_range(max_value_seconds) -> str:
    """
    Get the best time unit for a given time range.
    
    Useful for axis labels where you want consistent units.
    
    Args:
        max_value_seconds: Maximum time value in seconds
    
    Returns:
        str: Unit name ('ns', 'µs', 'ms', or 's')
    """
    if max_value_seconds < 1e-6:
        return 'ns'
    elif max_value_seconds < 1e-3:
        return 'µs'
    elif max_value_seconds < 1:
        return 'ms'
    else:
        return 's'


def convert_time_to_unit(time_quantity, target_unit: str):
    """
    Convert time quantity to specific unit and return magnitude.
    
    Args:
        time_quantity: Pint Quantity or float (assumed seconds)
        target_unit: Target unit ('ns', 'µs', 'ms', 's')
    
    Returns:
        float: Magnitude in target unit
    """
    # Convert to Pint quantity if needed
    if not isinstance(time_quantity, ureg.Quantity):
        time_quantity = time_quantity * ureg.second
    
    # Map short names to Pint units
    unit_map = {
        'ns': ureg.nanosecond,
        'µs': ureg.microsecond,
        'us': ureg.microsecond,
        'ms': ureg.millisecond,
        's': ureg.second,
    }
    
    pint_unit = unit_map.get(target_unit, ureg.second)
    return time_quantity.to(pint_unit).magnitude

