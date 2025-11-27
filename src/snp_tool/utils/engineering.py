"""Engineering notation parsing and formatting utilities.

Per research.md Section 8: Parse and format engineering notation (10pF, 2.2nH, 100uH, 1.5MHz).
"""

import re
from typing import Union


# Engineering notation multipliers
MULTIPLIERS = {
    'p': 1e-12,  # pico
    'n': 1e-9,   # nano
    'u': 1e-6,   # micro (μ)
    'µ': 1e-6,   # micro (alternative)
    'm': 1e-3,   # milli
    'k': 1e3,    # kilo
    'M': 1e6,    # mega
    'G': 1e9,    # giga
}

# Unit suffixes for validation
CAPACITANCE_UNITS = ['F', 'f']  # Farad
INDUCTANCE_UNITS = ['H', 'h']   # Henry
FREQUENCY_UNITS = ['Hz', 'hz']  # Hertz


def parse_engineering_notation(value_str: str, expected_unit: str = None) -> float:
    """Parse engineering notation string to numeric value.
    
    Args:
        value_str: String like "10pF", "2.2nH", "1.5GHz"
        expected_unit: Optional unit validation ('F', 'H', 'Hz')
    
    Returns:
        Numeric value in base units (Farads, Henrys, Hz)
    
    Raises:
        ValueError: if parsing fails or unit mismatch
    
    Examples:
        >>> parse_engineering_notation("10pF")
        1e-11  # 10 * 1e-12
        >>> parse_engineering_notation("2.2nH")
        2.2e-9
        >>> parse_engineering_notation("100uH")
        1e-4  # 100 * 1e-6
        >>> parse_engineering_notation("1.5GHz")
        1.5e9
    """
    # Pattern: number + optional multiplier + unit
    pattern = r'^(\d+\.?\d*)\s*([pnuµmkMG]?)([A-Za-z]+)?$'
    match = re.match(pattern, value_str.strip())
    
    if not match:
        raise ValueError(f"Invalid engineering notation: '{value_str}'")
    
    number_str, multiplier, unit = match.groups()
    
    # Parse number
    try:
        number = float(number_str)
    except ValueError:
        raise ValueError(f"Invalid number in '{value_str}'")
    
    # Apply multiplier
    if multiplier:
        if multiplier not in MULTIPLIERS:
            raise ValueError(f"Unknown multiplier '{multiplier}' in '{value_str}'")
        number *= MULTIPLIERS[multiplier]
    
    # Validate unit if expected
    if expected_unit:
        if not unit:
            raise ValueError(f"Missing unit in '{value_str}' (expected {expected_unit})")
        if unit.upper() != expected_unit.upper():
            raise ValueError(f"Unit mismatch: expected {expected_unit}, got {unit}")
    
    return number


def format_engineering_notation(value: float, unit: str = '', precision: int = 2) -> str:
    """Format numeric value as engineering notation string.
    
    Args:
        value: Numeric value in base units
        unit: Unit suffix ('F', 'H', 'Hz')
        precision: Decimal places
    
    Returns:
        Engineering notation string
    
    Examples:
        >>> format_engineering_notation(1e-11, 'F')
        '10.00pF'
        >>> format_engineering_notation(2.2e-9, 'H')
        '2.20nH'
    """
    # Handle zero
    if abs(value) < 1e-15:
        return f"0{unit}"
    
    # Find appropriate multiplier
    for prefix, multiplier in sorted(MULTIPLIERS.items(), key=lambda x: -x[1]):
        if abs(value) >= multiplier:
            scaled = value / multiplier
            return f"{scaled:.{precision}f}{prefix}{unit}"
    
    # No multiplier needed
    return f"{value:.{precision}f}{unit}"
