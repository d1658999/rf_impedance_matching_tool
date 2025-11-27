"""RF metrics calculation module.

Per contracts/grid_optimizer.md: Compute reflection coefficient, VSWR, return loss.
"""

from __future__ import annotations
import numpy as np
from numpy.typing import NDArray


def reflection_coefficient(
    impedance: complex | NDArray[np.complex128], reference_impedance: float = 50.0
) -> float | NDArray[np.float64]:
    """Calculate reflection coefficient magnitude from impedance.

    Γ = (Z - Z0) / (Z + Z0)
    Returns |Γ|

    Args:
        impedance: Complex impedance (single value or array)
        reference_impedance: Reference impedance Z0 (default 50Ω)

    Returns:
        Magnitude of reflection coefficient (0 to 1)
    """
    z0 = reference_impedance
    gamma = (impedance - z0) / (impedance + z0)
    return np.abs(gamma)


def vswr(
    impedance: complex | NDArray[np.complex128], reference_impedance: float = 50.0
) -> float | NDArray[np.float64]:
    """Calculate VSWR from impedance.

    VSWR = (1 + |Γ|) / (1 - |Γ|)

    Args:
        impedance: Complex impedance (single value or array)
        reference_impedance: Reference impedance Z0 (default 50Ω)

    Returns:
        VSWR value (≥ 1.0)
    """
    gamma = reflection_coefficient(impedance, reference_impedance)

    # Avoid division by zero
    denom = 1 - gamma
    if isinstance(denom, np.ndarray):
        denom = np.where(np.abs(denom) < 1e-10, 1e-10, denom)
    elif abs(denom) < 1e-10:
        return float("inf")

    return (1 + gamma) / denom


def return_loss_db(
    impedance: complex | NDArray[np.complex128], reference_impedance: float = 50.0
) -> float | NDArray[np.float64]:
    """Calculate return loss in dB from impedance.

    Return Loss = -20 * log10(|Γ|)

    Args:
        impedance: Complex impedance (single value or array)
        reference_impedance: Reference impedance Z0 (default 50Ω)

    Returns:
        Return loss in dB (positive value, higher is better)
    """
    gamma = reflection_coefficient(impedance, reference_impedance)

    # Avoid log(0)
    if isinstance(gamma, np.ndarray):
        gamma = np.where(gamma < 1e-10, 1e-10, gamma)
    elif gamma < 1e-10:
        return 100.0  # Cap at 100 dB

    return -20 * np.log10(gamma)


def reflection_coefficient_from_s11(s11: complex | NDArray[np.complex128]) -> float | NDArray[np.float64]:
    """Get reflection coefficient magnitude directly from S11.

    |Γ| = |S11|

    Args:
        s11: S11 parameter (complex)

    Returns:
        Magnitude of S11
    """
    return np.abs(s11)


def vswr_from_s11(s11: complex | NDArray[np.complex128]) -> float | NDArray[np.float64]:
    """Calculate VSWR from S11.

    VSWR = (1 + |S11|) / (1 - |S11|)

    Args:
        s11: S11 parameter (complex)

    Returns:
        VSWR value
    """
    gamma = np.abs(s11)
    denom = 1 - gamma

    if isinstance(denom, np.ndarray):
        denom = np.where(np.abs(denom) < 1e-10, 1e-10, denom)
    elif abs(denom) < 1e-10:
        return float("inf")

    return (1 + gamma) / denom


def return_loss_from_s11(s11: complex | NDArray[np.complex128]) -> float | NDArray[np.float64]:
    """Calculate return loss in dB from S11.

    Return Loss = -20 * log10(|S11|)

    Args:
        s11: S11 parameter (complex)

    Returns:
        Return loss in dB
    """
    gamma = np.abs(s11)

    if isinstance(gamma, np.ndarray):
        gamma = np.where(gamma < 1e-10, 1e-10, gamma)
    elif gamma < 1e-10:
        return 100.0

    return -20 * np.log10(gamma)


def impedance_from_s11(
    s11: complex | NDArray[np.complex128], reference_impedance: float = 50.0
) -> complex | NDArray[np.complex128]:
    """Calculate impedance from S11.

    Z = Z0 * (1 + S11) / (1 - S11)

    Args:
        s11: S11 parameter (complex)
        reference_impedance: Reference impedance Z0 (default 50Ω)

    Returns:
        Complex impedance
    """
    z0 = reference_impedance
    denom = 1 - s11

    if isinstance(denom, np.ndarray):
        denom = np.where(np.abs(denom) < 1e-10, 1e-10, denom)
    elif abs(denom) < 1e-10:
        return complex(float("inf"), 0)

    return z0 * (1 + s11) / denom


def mismatch_loss_db(
    impedance: complex | NDArray[np.complex128], reference_impedance: float = 50.0
) -> float | NDArray[np.float64]:
    """Calculate mismatch loss in dB.

    Mismatch Loss = -10 * log10(1 - |Γ|²)

    Args:
        impedance: Complex impedance
        reference_impedance: Reference impedance Z0 (default 50Ω)

    Returns:
        Mismatch loss in dB (positive value)
    """
    gamma = reflection_coefficient(impedance, reference_impedance)
    gamma_sq = gamma**2

    # Avoid log(0)
    if isinstance(gamma_sq, np.ndarray):
        arg = np.where(gamma_sq >= 1, 1e-10, 1 - gamma_sq)
    else:
        arg = max(1e-10, 1 - gamma_sq)

    return -10 * np.log10(arg)


def impedance_distance_to_target(
    impedance: complex, target_impedance: float = 50.0
) -> float:
    """Calculate the distance from impedance to target.

    Args:
        impedance: Complex impedance
        target_impedance: Target impedance (default 50Ω, real)

    Returns:
        Absolute distance |Z - Z_target|
    """
    return abs(impedance - target_impedance)


def is_matched(
    impedance: complex,
    target_impedance: float = 50.0,
    tolerance: float = 10.0,
    vswr_threshold: float = 2.0,
) -> bool:
    """Check if impedance is considered matched.

    Matched if either:
    - |Z - Z_target| ≤ tolerance
    - VSWR ≤ vswr_threshold

    Args:
        impedance: Complex impedance
        target_impedance: Target impedance (default 50Ω)
        tolerance: Impedance tolerance (default ±10Ω)
        vswr_threshold: VSWR threshold (default 2.0)

    Returns:
        True if matched, False otherwise
    """
    z_error = abs(impedance - target_impedance)
    v = vswr(impedance, target_impedance)

    return z_error <= tolerance or v <= vswr_threshold


def calculate_vswr(s11_magnitude: float) -> float:
    """Calculate VSWR from |S11| magnitude.

    VSWR = (1 + |S11|) / (1 - |S11|)

    Args:
        s11_magnitude: Magnitude of S11 (0 to 1)

    Returns:
        VSWR value (≥ 1.0)
    """
    # Clamp to valid range
    gamma = min(max(s11_magnitude, 0.0), 0.9999)

    denom = 1 - gamma
    if abs(denom) < 1e-10:
        return float("inf")

    return (1 + gamma) / denom
