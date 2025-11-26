"""S-parameter cascade using ABCD matrices.

Per contracts/grid_optimizer.md: Cascade S-parameter matrices using ABCD
transmission line parameters.
"""

from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
from numpy.typing import NDArray

try:
    import skrf as rf
except ImportError:
    rf = None  # type: ignore


def interpolate_s_params(
    s_params: Dict[str, NDArray[np.complex128]],
    source_freq: NDArray[np.float64],
    target_freq: NDArray[np.float64],
) -> Dict[str, NDArray[np.complex128]]:
    """Interpolate S-parameters to a new frequency grid.

    Args:
        s_params: Original S-parameters
        source_freq: Original frequency points
        target_freq: Target frequency points

    Returns:
        Interpolated S-parameters at target frequencies
    """
    result = {}
    for key, values in s_params.items():
        # Interpolate real and imaginary parts separately
        real_interp = np.interp(target_freq, source_freq, values.real)
        imag_interp = np.interp(target_freq, source_freq, values.imag)
        result[key] = real_interp + 1j * imag_interp
    return result


def cascade_networks(
    s_param_list: List[Dict[str, NDArray[np.complex128]]],
    frequency: NDArray[np.float64],
    reference_impedance: float = 50.0,
) -> Dict[str, NDArray[np.complex128]]:
    """Cascade multiple 2-port networks using ABCD matrices.

    Args:
        s_param_list: List of S-parameter dicts (each with s11, s12, s21, s22)
        frequency: Frequency points (must be same for all networks)
        reference_impedance: Reference impedance Z0 (default 50Ω)

    Returns:
        Dict with cascaded S-parameters (s11, s12, s21, s22)
    """
    if not s_param_list:
        raise ValueError("No networks to cascade")

    if len(s_param_list) == 1:
        return s_param_list[0].copy()

    num_freqs = len(frequency)
    z0 = reference_impedance

    # Start with identity ABCD matrix at each frequency
    # ABCD = [[A, B], [C, D]] = [[1, 0], [0, 1]]
    abcd_result = np.zeros((num_freqs, 2, 2), dtype=np.complex128)
    abcd_result[:, 0, 0] = 1.0
    abcd_result[:, 1, 1] = 1.0

    # Cascade each network
    for s_params in s_param_list:
        abcd = s_to_abcd(s_params, z0)
        abcd_result = _matrix_multiply(abcd_result, abcd)

    # Convert back to S-parameters
    return abcd_to_s(abcd_result, z0)


def s_to_abcd(
    s_params: Dict[str, NDArray[np.complex128]], z0: float = 50.0
) -> NDArray[np.complex128]:
    """Convert S-parameters to ABCD matrix.

    Args:
        s_params: Dict with s11, s12, s21, s22 arrays
        z0: Reference impedance

    Returns:
        ABCD matrix array of shape (num_freqs, 2, 2)
    """
    s11 = s_params["s11"]
    s12 = s_params.get("s12", s_params.get("s11"))  # Fallback for 1-port
    s21 = s_params.get("s21", s_params.get("s11"))
    s22 = s_params.get("s22", s_params.get("s11"))

    num_freqs = len(s11)
    abcd = np.zeros((num_freqs, 2, 2), dtype=np.complex128)

    # Conversion formulas from S to ABCD
    # Reference: Pozar, Microwave Engineering
    denom = 2 * s21

    # Handle near-zero S21 (high isolation)
    denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)

    # A = ((1 + S11) * (1 - S22) + S12 * S21) / (2 * S21)
    abcd[:, 0, 0] = ((1 + s11) * (1 - s22) + s12 * s21) / denom

    # B = Z0 * ((1 + S11) * (1 + S22) - S12 * S21) / (2 * S21)
    abcd[:, 0, 1] = z0 * ((1 + s11) * (1 + s22) - s12 * s21) / denom

    # C = (1/Z0) * ((1 - S11) * (1 - S22) - S12 * S21) / (2 * S21)
    abcd[:, 1, 0] = (1 / z0) * ((1 - s11) * (1 - s22) - s12 * s21) / denom

    # D = ((1 - S11) * (1 + S22) + S12 * S21) / (2 * S21)
    abcd[:, 1, 1] = ((1 - s11) * (1 + s22) + s12 * s21) / denom

    return abcd


def abcd_to_s(
    abcd: NDArray[np.complex128], z0: float = 50.0
) -> Dict[str, NDArray[np.complex128]]:
    """Convert ABCD matrix to S-parameters.

    Args:
        abcd: ABCD matrix array of shape (num_freqs, 2, 2)
        z0: Reference impedance

    Returns:
        Dict with s11, s12, s21, s22 arrays
    """
    A = abcd[:, 0, 0]
    B = abcd[:, 0, 1]
    C = abcd[:, 1, 0]
    D = abcd[:, 1, 1]

    # Conversion formulas from ABCD to S
    denom = A + B / z0 + C * z0 + D

    # Handle near-zero denominator
    denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)

    s11 = (A + B / z0 - C * z0 - D) / denom
    s12 = 2 * (A * D - B * C) / denom
    s21 = 2 / denom
    s22 = (-A + B / z0 - C * z0 + D) / denom

    return {"s11": s11, "s12": s12, "s21": s21, "s22": s22}


def _matrix_multiply(
    a: NDArray[np.complex128], b: NDArray[np.complex128]
) -> NDArray[np.complex128]:
    """Multiply arrays of 2x2 matrices element-wise over frequency.

    Args:
        a: Array of shape (num_freqs, 2, 2)
        b: Array of shape (num_freqs, 2, 2)

    Returns:
        Array of shape (num_freqs, 2, 2) with matrix products
    """
    # Use einsum for efficient batched matrix multiplication
    return np.einsum("nij,njk->nik", a, b)


def cascade_with_topology(
    device_s_params: Dict[str, NDArray[np.complex128]],
    component_s_params_list: List[Dict[str, NDArray[np.complex128]]],
    component_order: List[str],  # ['series', 'shunt']
    frequency: NDArray[np.float64],
    reference_impedance: float = 50.0,
    component_frequencies: List[NDArray[np.float64]] = None,
) -> Dict[str, NDArray[np.complex128]]:
    """Cascade device with components according to topology.

    For series components: Direct cascade
    For shunt components: Connect in parallel (transform to shunt network first)

    Args:
        device_s_params: Main device S-parameters
        component_s_params_list: List of component S-parameters
        component_order: Connection type for each component
        frequency: Frequency points (device frequency grid)
        reference_impedance: Reference impedance
        component_frequencies: Optional list of component frequency grids for interpolation

    Returns:
        Cascaded S-parameters
    """
    z0 = reference_impedance
    num_freqs = len(frequency)

    # Interpolate device S-params if needed
    device_s = device_s_params
    if len(device_s_params["s11"]) != num_freqs:
        # Assume device frequency matches target
        pass

    # Start with device ABCD
    abcd_result = s_to_abcd(device_s, z0)

    for i, (s_params, order) in enumerate(zip(component_s_params_list, component_order)):
        # Interpolate component S-params to device frequency grid if needed
        comp_s = s_params
        comp_len = len(s_params["s11"])
        if comp_len != num_freqs:
            # Need to interpolate
            if component_frequencies and i < len(component_frequencies):
                comp_freq = component_frequencies[i]
            else:
                # Assume uniform frequency grid
                comp_freq = np.linspace(frequency[0], frequency[-1], comp_len)
            comp_s = interpolate_s_params(s_params, comp_freq, frequency)

        if order == "series":
            # Series connection: direct cascade
            abcd_comp = s_to_abcd(comp_s, z0)
        else:
            # Shunt connection: transform to shunt ABCD representation
            abcd_comp = _component_to_shunt_abcd(comp_s, frequency, z0)

        abcd_result = _matrix_multiply(abcd_result, abcd_comp)

    return abcd_to_s(abcd_result, z0)


def _component_to_shunt_abcd(
    s_params: Dict[str, NDArray[np.complex128]],
    frequency: NDArray[np.float64],
    z0: float,
) -> NDArray[np.complex128]:
    """Convert component S-parameters to shunt connection ABCD matrix.

    For a shunt element with impedance Z:
    ABCD = [[1, 0], [1/Z, 1]]

    Args:
        s_params: Component S-parameters
        frequency: Frequency points
        z0: Reference impedance

    Returns:
        ABCD matrix for shunt connection
    """
    num_freqs = len(frequency)
    s11 = s_params["s11"]

    # Calculate impedance from S11
    # Z = Z0 * (1 + S11) / (1 - S11)
    denom = 1 - s11
    denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)
    z = z0 * (1 + s11) / denom

    # For shunt connection: ABCD = [[1, 0], [Y, 1]] where Y = 1/Z
    y = 1 / np.where(np.abs(z) < 1e-12, 1e-12, z)

    abcd = np.zeros((num_freqs, 2, 2), dtype=np.complex128)
    abcd[:, 0, 0] = 1.0
    abcd[:, 0, 1] = 0.0
    abcd[:, 1, 0] = y
    abcd[:, 1, 1] = 1.0

    return abcd
