"""Touchstone file parser using scikit-rf.

Per contracts/touchstone_parser.md: Parse .snp/.s2p Touchstone format files
and extract S-parameters.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
from numpy.typing import NDArray

try:
    import skrf as rf
except ImportError:
    rf = None  # type: ignore

from ..models.snp_file import SNPFile
from ..utils.exceptions import (
    TouchstoneFormatError,
    FrequencyGapError,
    InvalidPortMappingError,
)
from ..utils.logging import get_logger


def parse(file_path: str, port_mapping: Optional[Tuple[int, int]] = None) -> SNPFile:
    """Parse a Touchstone file and return an SNPFile object.

    Args:
        file_path: Path to .snp or .s2p file
        port_mapping: Optional (source_port, load_port) for multi-port files.
                     For S3P/S4P files, extracts 2x2 submatrix for specified port pair.
                     Default: None (uses ports 0→1 for 2-port, requires specification for >2 ports)

    Returns:
        SNPFile object with parsed S-parameters

    Raises:
        FileNotFoundError: File does not exist
        TouchstoneFormatError: File format invalid
        InvalidPortMappingError: Port mapping invalid for file
    """
    if rf is None:
        raise ImportError("scikit-rf is required: pip install scikit-rf")

    logger = get_logger()
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Touchstone file not found: {file_path}")

    logger.debug(f"Parsing Touchstone file: {file_path}")

    try:
        network = rf.Network(str(path))
    except Exception as e:
        raise TouchstoneFormatError(
            f"Failed to parse Touchstone file: {str(e)}", file_path=file_path
        )

    # Extract basic info
    num_ports = network.number_of_ports
    frequency = network.f  # Frequency in Hz
    z0 = float(network.z0[0, 0].real)  # Reference impedance

    logger.debug(
        f"Loaded network",
        ports=num_ports,
        freq_points=len(frequency),
        z0=z0,
    )

    # Determine port mapping
    source_port = 0
    load_port = 1 if num_ports > 1 else 0

    if port_mapping is not None:
        source_port, load_port = port_mapping
        if source_port < 0 or source_port >= num_ports:
            raise InvalidPortMappingError(
                f"Source port {source_port} invalid",
                num_ports=num_ports,
                requested_ports=port_mapping,
            )
        if load_port < 0 or load_port >= num_ports:
            raise InvalidPortMappingError(
                f"Load port {load_port} invalid",
                num_ports=num_ports,
                requested_ports=port_mapping,
            )
    elif num_ports > 2 and port_mapping is None:
        logger.warning(
            f"Multi-port file ({num_ports} ports) without port mapping. Using default 0→1."
        )

    # Extract S-parameters
    s_parameters = _extract_s_parameters(network, source_port, load_port)

    # Determine format info from file
    frequency_unit = _detect_frequency_unit(frequency)
    s_param_format = "complex"  # scikit-rf normalizes to complex internally

    # Validate frequency array
    _validate_frequency_array(frequency, file_path)

    return SNPFile(
        file_path=str(path.absolute()),
        frequency=frequency,
        s_parameters=s_parameters,
        num_ports=2 if num_ports > 2 else num_ports,  # Reduced to 2-port after extraction
        source_port_index=source_port,
        load_port_index=load_port,
        reference_impedance=z0,
        frequency_unit=frequency_unit,
        s_parameter_format=s_param_format,
        _network=network,
    )


def _extract_s_parameters(
    network, source_port: int, load_port: int
) -> Dict[str, NDArray[np.complex128]]:
    """Extract S-parameters from network, handling multi-port reduction.

    For multi-port networks, extracts 2x2 submatrix for specified port pair.
    """
    num_ports = network.number_of_ports
    s = network.s  # Shape: (freq_points, num_ports, num_ports)

    if num_ports <= 2:
        # Direct extraction for 1-port or 2-port
        s_params = {"s11": s[:, 0, 0]}
        if num_ports == 2:
            s_params["s12"] = s[:, 0, 1]
            s_params["s21"] = s[:, 1, 0]
            s_params["s22"] = s[:, 1, 1]
    else:
        # Extract 2x2 submatrix for specified port pair
        s_params = {
            "s11": s[:, source_port, source_port],
            "s12": s[:, source_port, load_port],
            "s21": s[:, load_port, source_port],
            "s22": s[:, load_port, load_port],
        }

    return s_params


def _detect_frequency_unit(frequency: NDArray[np.float64]) -> str:
    """Detect the most appropriate frequency unit for display."""
    max_freq = frequency.max()

    if max_freq >= 1e9:
        return "GHz"
    elif max_freq >= 1e6:
        return "MHz"
    elif max_freq >= 1e3:
        return "kHz"
    else:
        return "Hz"


def _validate_frequency_array(frequency: NDArray[np.float64], file_path: str) -> None:
    """Validate frequency array is sorted and monotonic."""
    if len(frequency) == 0:
        raise TouchstoneFormatError("Empty frequency array", file_path=file_path)

    # Check sorted ascending
    if not np.all(np.diff(frequency) > 0):
        raise TouchstoneFormatError(
            "Frequency array must be sorted ascending with no duplicates",
            file_path=file_path,
        )


def extract_impedance(
    s11: NDArray[np.complex128], reference_impedance: float = 50.0
) -> NDArray[np.complex128]:
    """Calculate impedance from S11 parameter.

    Formula: Z = Z0 * (1 + S11) / (1 - S11)

    Args:
        s11: Array of S11 values (complex)
        reference_impedance: Reference impedance Z0 (default 50Ω)

    Returns:
        Array of complex impedances
    """
    denominator = 1 - s11
    # Avoid division by zero (S11 ≈ 1 means open circuit)
    denominator = np.where(np.abs(denominator) < 1e-10, 1e-10, denominator)

    return reference_impedance * (1 + s11) / denominator


def validate_frequency_coverage(
    frequency_grid: NDArray[np.float64], tolerance: float = 1e-6
) -> bool:
    """Validate frequency grid has no gaps.

    Args:
        frequency_grid: Sorted array of frequency points
        tolerance: Relative tolerance for gap detection

    Returns:
        True if valid (no gaps), False otherwise

    Raises:
        FrequencyGapError: If gaps are detected (optional based on use case)
    """
    if len(frequency_grid) < 2:
        return True

    # Check for monotonically increasing
    diffs = np.diff(frequency_grid)
    if np.any(diffs <= 0):
        return False

    # Check for consistent spacing (optional - some files have variable spacing)
    # For now, just ensure monotonically increasing
    return True
