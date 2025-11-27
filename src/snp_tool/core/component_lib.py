"""
E-Series Component Libraries (Task 2.1.1).

Provides standard component value series (E12, E24, E96) for capacitors and inductors.
Implements snap-to-standard functionality for optimization in standard values mode.
"""

from enum import Enum
from typing import List, Tuple
import numpy as np


class ESeries(Enum):
    """Standard E-series for resistors, capacitors, and inductors."""
    E12 = "E12"
    E24 = "E24"
    E96 = "E96"


# E-series base values (multiplied by decades)
E12_VALUES = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]

E24_VALUES = [
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1
]

E96_VALUES = [
    1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30,
    1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62, 1.65, 1.69, 1.74,
    1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15, 2.21, 2.26, 2.32,
    2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09,
    3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
    4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49,
    5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32,
    7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76
]


def generate_e_series(
    series: ESeries,
    min_value: float,
    max_value: float,
    unit: str = 'F'
) -> List[float]:
    """
    Generate E-series values within specified range.
    
    Args:
        series: E-series type (E12, E24, E96)
        min_value: Minimum value in SI units (e.g., 1e-12 for 1pF)
        max_value: Maximum value in SI units
        unit: Unit type ('F' for Farad, 'H' for Henry)
        
    Returns:
        List of standard values in SI units within range
        
    Example:
        >>> generate_e_series(ESeries.E24, 1e-12, 100e-12, 'F')  # 1pF to 100pF
        [1.0e-12, 1.1e-12, 1.2e-12, ..., 82e-12, 91e-12]
    """
    if series == ESeries.E12:
        base_values = E12_VALUES
    elif series == ESeries.E24:
        base_values = E24_VALUES
    elif series == ESeries.E96:
        base_values = E96_VALUES
    else:
        raise ValueError(f"Unknown E-series: {series}")
    
    # Generate values across decades
    values = []
    
    # Determine decade range
    min_decade = np.floor(np.log10(min_value))
    max_decade = np.ceil(np.log10(max_value))
    
    for decade_exp in range(int(min_decade), int(max_decade) + 1):
        decade = 10 ** decade_exp
        for base in base_values:
            value = base * decade
            if min_value <= value <= max_value:
                values.append(value)
    
    return sorted(values)


def get_standard_values(
    series: ESeries,
    component_type: str = 'capacitor',
    decade_range: Tuple[str, str] = None
) -> List[float]:
    """
    Get standard component values for specified E-series.
    
    Args:
        series: E-series type (E12, E24, E96)
        component_type: 'capacitor' or 'inductor'
        decade_range: Optional (min_unit, max_unit) e.g., ('pF', 'µF') or ('nH', 'mH')
                     If None, uses sensible defaults
        
    Returns:
        List of standard values in SI units
        
    Example:
        >>> values = get_standard_values(ESeries.E24, 'capacitor', ('pF', 'µF'))
        >>> len(values) > 100  # Many values across wide range
        True
    """
    if component_type == 'capacitor':
        if decade_range is None:
            min_val, max_val = 1e-12, 100e-6  # 1pF to 100µF
        else:
            min_val = _parse_unit_to_si(decade_range[0], 'F')
            max_val = _parse_unit_to_si(decade_range[1], 'F')
        unit = 'F'
    elif component_type == 'inductor':
        if decade_range is None:
            min_val, max_val = 1e-9, 100e-3  # 1nH to 100mH
        else:
            min_val = _parse_unit_to_si(decade_range[0], 'H')
            max_val = _parse_unit_to_si(decade_range[1], 'H')
        unit = 'H'
    else:
        raise ValueError(f"Unknown component type: {component_type}")
    
    return generate_e_series(series, min_val, max_val, unit)


def snap_to_standard(
    value: float,
    series: ESeries,
    component_type: str = 'capacitor'
) -> float:
    """
    Snap a value to the nearest standard E-series value.
    
    Args:
        value: Component value in SI units (e.g., 12.7e-12 for 12.7pF)
        series: E-series type to snap to
        component_type: 'capacitor' or 'inductor'
        
    Returns:
        Nearest standard value in SI units
        
    Example:
        >>> snap_to_standard(12.7e-12, ESeries.E24, 'capacitor')
        1.2e-11  # 12pF (nearest E24 value)
    """
    # Get all standard values for this component type
    standard_values = get_standard_values(series, component_type)
    
    # Find nearest value
    distances = np.abs(np.array(standard_values) - value)
    nearest_idx = np.argmin(distances)
    
    return standard_values[nearest_idx]


def _parse_unit_to_si(unit_str: str, base_unit: str) -> float:
    """
    Parse engineering unit string to SI value.
    
    Args:
        unit_str: Unit string like 'pF', 'nH', 'µF', 'mH'
        base_unit: Base unit ('F' or 'H')
        
    Returns:
        Multiplier for SI units
    """
    unit_str = unit_str.strip()
    
    multipliers = {
        'f': 1e-15,
        'p': 1e-12,
        'n': 1e-9,
        'u': 1e-6,
        'µ': 1e-6,
        'm': 1e-3,
        '': 1.0,
    }
    
    # Extract prefix
    if unit_str.endswith(base_unit):
        prefix = unit_str[:-1]
    else:
        prefix = unit_str
    
    prefix_lower = prefix.lower()
    
    if prefix_lower in multipliers:
        return multipliers[prefix_lower]
    else:
        raise ValueError(f"Unknown unit prefix: {prefix}")


# Testing utilities
def validate_e_series_properties(series: ESeries) -> bool:
    """
    Validate that E-series values meet expected properties.
    
    Properties checked:
    - Values are monotonically increasing
    - Ratios between consecutive values are approximately constant
    - Decade coverage (1.0 to ~10.0)
    
    Args:
        series: E-series to validate
        
    Returns:
        True if valid, raises AssertionError if invalid
    """
    if series == ESeries.E12:
        values = E12_VALUES
        expected_ratio = 10 ** (1/12)  # 12th root of 10
    elif series == ESeries.E24:
        values = E24_VALUES
        expected_ratio = 10 ** (1/24)
    elif series == ESeries.E96:
        values = E96_VALUES
        expected_ratio = 10 ** (1/96)
    else:
        raise ValueError(f"Unknown series: {series}")
    
    # Check monotonic increasing
    for i in range(len(values) - 1):
        assert values[i] < values[i+1], f"Values not monotonic at index {i}"
    
    # Check ratios are approximately constant
    ratios = [values[i+1] / values[i] for i in range(len(values) - 1)]
    avg_ratio = np.mean(ratios)
    
    # Allow 10% tolerance
    for i, ratio in enumerate(ratios):
        assert abs(ratio - expected_ratio) / expected_ratio < 0.10, \
            f"Ratio at index {i} deviates too much: {ratio} vs expected {expected_ratio}"
    
    # Check decade coverage
    assert values[0] >= 0.9 and values[0] <= 1.1, "First value should be ~1.0"
    assert values[-1] >= 8.0 and values[-1] <= 10.0, "Last value should cover decade"
    
    return True
