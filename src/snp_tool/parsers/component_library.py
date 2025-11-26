"""Component library parser for vendor S2P files.

Per contracts/component_library.md: Parse folder of vendor component files
and build searchable index.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import numpy as np
from numpy.typing import NDArray

try:
    import skrf as rf
except ImportError:
    rf = None  # type: ignore

from ..models.component import ComponentModel, ComponentType
from ..models.component_library import ComponentLibrary
from ..utils.exceptions import TouchstoneFormatError, FrequencyGapError
from ..utils.logging import get_logger


def parse_folder(folder_path: str, recursive: bool = True) -> ComponentLibrary:
    """Parse a folder of vendor .s2p component files.

    Args:
        folder_path: Path to folder containing .s2p files
        recursive: Whether to search subdirectories

    Returns:
        ComponentLibrary with all parsed components
    """
    if rf is None:
        raise ImportError("scikit-rf is required: pip install scikit-rf")

    logger = get_logger()
    path = Path(folder_path)

    if not path.exists():
        raise FileNotFoundError(f"Component library folder not found: {folder_path}")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    # Find all .s2p files
    pattern = "**/*.s2p" if recursive else "*.s2p"
    s2p_files = list(path.glob(pattern))

    # Also find .s1p files (single-port components)
    s1p_files = list(path.glob("**/*.s1p" if recursive else "*.s1p"))

    all_files = s2p_files + s1p_files
    logger.info(f"Found {len(all_files)} component files in {folder_path}")

    components = []
    failed = []

    for file_path in all_files:
        try:
            component = parse_component_file(str(file_path))
            components.append(component)
        except Exception as e:
            logger.warning(f"Failed to parse {file_path.name}: {str(e)}")
            failed.append((str(file_path), str(e)))

    logger.info(
        f"Loaded {len(components)} components successfully",
        failed=len(failed),
        capacitors=sum(1 for c in components if c.component_type == ComponentType.CAPACITOR),
        inductors=sum(1 for c in components if c.component_type == ComponentType.INDUCTOR),
    )

    return ComponentLibrary(
        library_path=str(path.absolute()),
        components=components,
    )


def parse_component_file(file_path: str) -> ComponentModel:
    """Parse a single component S-parameter file.

    Args:
        file_path: Path to .s2p or .s1p file

    Returns:
        ComponentModel with parsed data and inferred metadata
    """
    if rf is None:
        raise ImportError("scikit-rf is required: pip install scikit-rf")

    path = Path(file_path)

    try:
        network = rf.Network(str(path))
    except Exception as e:
        raise TouchstoneFormatError(
            f"Failed to parse component file: {str(e)}", file_path=file_path
        )

    # Extract S-parameters
    frequency = network.f
    z0 = float(network.z0[0, 0].real)

    s_parameters = {"s11": network.s[:, 0, 0]}
    if network.number_of_ports >= 2:
        s_parameters["s12"] = network.s[:, 0, 1]
        s_parameters["s21"] = network.s[:, 1, 0]
        s_parameters["s22"] = network.s[:, 1, 1]

    # Extract metadata from filename and path
    manufacturer, part_number, component_type, value = extract_metadata_from_path(path)

    # If type couldn't be determined from filename, infer from S-parameters
    if component_type == ComponentType.UNKNOWN:
        component_type = infer_component_type(s_parameters["s11"], frequency, z0)

    # If value couldn't be determined, try to infer
    if value is None:
        value = infer_component_value(s_parameters["s11"], frequency, z0, component_type)

    return ComponentModel(
        s2p_file_path=str(path.absolute()),
        manufacturer=manufacturer,
        part_number=part_number,
        component_type=component_type,
        frequency=frequency,
        s_parameters=s_parameters,
        value=value,
        value_nominal=parse_value_to_si(value) if value else None,
        reference_impedance=z0,
        metadata={"original_filename": path.name},
    )


def extract_metadata_from_path(path: Path) -> Tuple[str, str, ComponentType, Optional[str]]:
    """Extract component metadata from file path and name.

    Tries to extract:
    - Manufacturer from parent directory name
    - Part number from filename
    - Component type from keywords (CAP, IND, C, L)
    - Value from filename patterns (10pF, 1nH, etc.)

    Args:
        path: Path to component file

    Returns:
        Tuple of (manufacturer, part_number, component_type, value)
    """
    filename = path.stem  # Filename without extension
    parent_name = path.parent.name if path.parent.name != "." else ""

    # Try to extract manufacturer
    manufacturer = "Unknown"
    known_manufacturers = ["murata", "tdk", "samsung", "vishay", "kemet", "avx", "yageo"]

    # Check parent directory
    for mfr in known_manufacturers:
        if mfr.lower() in parent_name.lower():
            manufacturer = mfr.capitalize()
            break

    # Check filename
    if manufacturer == "Unknown":
        for mfr in known_manufacturers:
            if mfr.lower() in filename.lower():
                manufacturer = mfr.capitalize()
                break

    # Extract part number (usually the filename without common prefixes)
    part_number = filename
    prefixes = ["cap_", "ind_", "c_", "l_", "capacitor_", "inductor_"]
    for prefix in prefixes:
        if part_number.lower().startswith(prefix):
            part_number = part_number[len(prefix) :]
            break

    # Determine component type
    component_type = ComponentType.UNKNOWN

    type_indicators_cap = ["cap", "capacitor", "_c_", "c_", "_c-"]
    type_indicators_ind = ["ind", "inductor", "_l_", "l_", "_l-"]

    filename_lower = filename.lower()
    for indicator in type_indicators_cap:
        if indicator in filename_lower:
            component_type = ComponentType.CAPACITOR
            break

    if component_type == ComponentType.UNKNOWN:
        for indicator in type_indicators_ind:
            if indicator in filename_lower:
                component_type = ComponentType.INDUCTOR
                break

    # Extract value from filename
    value = extract_value_from_string(filename)

    return manufacturer, part_number, component_type, value


def extract_value_from_string(s: str) -> Optional[str]:
    """Extract component value from a string.

    Recognizes patterns like:
    - 10pF, 100pf, 1.5pF
    - 1nH, 10nH, 1.2nh
    - 10uF, 100nF
    - 1_0pF (underscore as decimal point)
    """
    # Pattern for capacitance values
    cap_pattern = r"(\d+[._]?\d*)\s*(p|n|u|µ)?\s*[fF]"
    # Pattern for inductance values
    ind_pattern = r"(\d+[._]?\d*)\s*(p|n|u|µ)?\s*[hH]"

    # Try capacitance first
    match = re.search(cap_pattern, s, re.IGNORECASE)
    if match:
        num = match.group(1).replace("_", ".")
        prefix = match.group(2) or ""
        return f"{num}{prefix}F"

    # Try inductance
    match = re.search(ind_pattern, s, re.IGNORECASE)
    if match:
        num = match.group(1).replace("_", ".")
        prefix = match.group(2) or ""
        return f"{num}{prefix}H"

    return None


def parse_value_to_si(value: str) -> Optional[float]:
    """Parse component value string to SI units (Farads or Henries).

    Args:
        value: Value string like '10pF', '1nH'

    Returns:
        Value in SI units (Farads or Henries), or None if unparseable
    """
    if not value:
        return None

    prefixes = {
        "p": 1e-12,
        "n": 1e-9,
        "u": 1e-6,
        "µ": 1e-6,
        "m": 1e-3,
        "": 1,
    }

    # Pattern: number + optional prefix + unit
    pattern = r"(\d+\.?\d*)\s*([pnuµm]?)\s*([fFhH])"
    match = re.match(pattern, value.strip())

    if not match:
        return None

    number = float(match.group(1))
    prefix = match.group(2).lower()
    multiplier = prefixes.get(prefix, 1)

    return number * multiplier


def infer_component_type(
    s11: NDArray[np.complex128], frequency: NDArray[np.float64], z0: float
) -> ComponentType:
    """Infer component type from S-parameter behavior.

    Capacitor: Impedance magnitude decreases with frequency (capacitive reactance)
    Inductor: Impedance magnitude increases with frequency (inductive reactance)
    """
    if len(frequency) < 2:
        return ComponentType.UNKNOWN

    # Calculate impedance at low and high frequencies
    z_low = z0 * (1 + s11[0]) / (1 - s11[0])
    z_high = z0 * (1 + s11[-1]) / (1 - s11[-1])

    # Compare imaginary parts (reactance)
    x_low = z_low.imag
    x_high = z_high.imag

    # Capacitor: negative reactance, magnitude decreases with freq
    # Inductor: positive reactance, magnitude increases with freq
    if x_low < -1 and x_high < -1:
        if abs(x_low) > abs(x_high):
            return ComponentType.CAPACITOR
    elif x_low > 1 and x_high > 1:
        if x_high > x_low:
            return ComponentType.INDUCTOR

    # Fallback: check center frequency reactance sign
    center_idx = len(frequency) // 2
    z_center = z0 * (1 + s11[center_idx]) / (1 - s11[center_idx])

    if z_center.imag < -5:
        return ComponentType.CAPACITOR
    elif z_center.imag > 5:
        return ComponentType.INDUCTOR

    return ComponentType.UNKNOWN


def infer_component_value(
    s11: NDArray[np.complex128],
    frequency: NDArray[np.float64],
    z0: float,
    component_type: ComponentType,
) -> Optional[str]:
    """Infer component nominal value from S-parameters.

    For capacitors: C = 1 / (2πf * |Xc|)
    For inductors: L = |Xl| / (2πf)
    """
    if component_type == ComponentType.UNKNOWN:
        return None

    # Use center frequency for calculation
    center_idx = len(frequency) // 2
    f = frequency[center_idx]
    z = z0 * (1 + s11[center_idx]) / (1 - s11[center_idx])
    x = z.imag

    if abs(x) < 1e-6:
        return None

    try:
        if component_type == ComponentType.CAPACITOR:
            # C = 1 / (2πf * |Xc|)
            c = 1 / (2 * np.pi * f * abs(x))
            return format_si_value(c, "F")
        elif component_type == ComponentType.INDUCTOR:
            # L = |Xl| / (2πf)
            l = abs(x) / (2 * np.pi * f)
            return format_si_value(l, "H")
    except Exception:
        pass

    return None


def format_si_value(value: float, unit: str) -> str:
    """Format a value with appropriate SI prefix.

    Args:
        value: Value in base units (Farads or Henries)
        unit: Unit string ('F' or 'H')

    Returns:
        Formatted string like '10pF' or '1.5nH'
    """
    prefixes = [
        (1e-15, "f"),
        (1e-12, "p"),
        (1e-9, "n"),
        (1e-6, "µ"),
        (1e-3, "m"),
        (1, ""),
    ]

    for threshold, prefix in prefixes:
        if value < threshold * 1000:
            scaled = value / threshold
            if scaled >= 100:
                return f"{scaled:.0f}{prefix}{unit}"
            elif scaled >= 10:
                return f"{scaled:.1f}{prefix}{unit}"
            else:
                return f"{scaled:.2f}{prefix}{unit}"

    return f"{value}{unit}"
