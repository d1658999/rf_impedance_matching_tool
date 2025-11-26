"""Component Model entity representing a vendor passive component.

Per data-model.md: Represents a single vendor passive component (capacitor or inductor)
with S-parameters.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import numpy as np
from numpy.typing import NDArray


class ComponentType(Enum):
    """Type of passive component."""

    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    UNKNOWN = "unknown"


@dataclass
class ComponentModel:
    """Vendor component model with S-parameters.

    Attributes:
        s2p_file_path: Path to the vendor .s2p file
        manufacturer: Manufacturer name (e.g., 'Murata', 'TDK')
        part_number: Component part number
        component_type: Type of component (capacitor/inductor)
        value: Component value as string (e.g., '10pF', '1nH')
        value_nominal: Nominal value in SI units (Farads or Henries)
        frequency: Array of frequency points in Hz
        s_parameters: Dict mapping S-param names to complex arrays
        reference_impedance: Reference impedance in Ohms (default 50.0)
        metadata: Optional additional metadata
    """

    s2p_file_path: str
    manufacturer: str
    part_number: str
    component_type: ComponentType
    frequency: NDArray[np.float64]
    s_parameters: Dict[str, NDArray[np.complex128]]
    value: Optional[str] = None
    value_nominal: Optional[float] = None
    reference_impedance: float = 50.0
    metadata: Dict = field(default_factory=dict)

    @property
    def frequency_grid(self) -> List[float]:
        """Get sorted list of frequency points."""
        return sorted(self.frequency.tolist())

    @property
    def frequency_range(self) -> tuple:
        """Return (min_freq, max_freq) in Hz."""
        return float(self.frequency.min()), float(self.frequency.max())

    @property
    def s11(self) -> NDArray[np.complex128]:
        """Get S11 parameter."""
        return self.s_parameters.get("s11", np.array([], dtype=np.complex128))

    @property
    def s21(self) -> NDArray[np.complex128]:
        """Get S21 parameter (insertion)."""
        return self.s_parameters.get("s21", np.array([], dtype=np.complex128))

    def impedance_at_frequency(self, freq: float) -> complex:
        """Calculate component impedance at a specific frequency.

        Uses formula: Z = Z0 * (1 + S11) / (1 - S11)

        Args:
            freq: Frequency in Hz

        Returns:
            Complex impedance in Ohms

        Raises:
            ValueError: If frequency is outside the data range
        """
        if freq < self.frequency.min() or freq > self.frequency.max():
            raise ValueError(
                f"Frequency {freq/1e9:.3f} GHz outside component range "
                f"[{self.frequency.min()/1e9:.3f}, {self.frequency.max()/1e9:.3f}] GHz"
            )

        # Find nearest frequency index
        idx = np.argmin(np.abs(self.frequency - freq))
        s11 = self.s11[idx]

        # Calculate impedance from S11
        z0 = self.reference_impedance
        if np.abs(1 - s11) < 1e-10:
            return complex(float("inf"), 0)

        return z0 * (1 + s11) / (1 - s11)

    def validate_frequency_coverage(
        self, device_frequency_grid: NDArray[np.float64], tolerance: float = 1e-6
    ) -> tuple:
        """Validate that component covers all device frequencies.

        Per Q4 clarification: Reject components with frequency gaps.

        Args:
            device_frequency_grid: Array of device frequency points
            tolerance: Relative tolerance for frequency matching

        Returns:
            Tuple of (is_valid, missing_frequencies)
        """
        component_freqs = set(self.frequency)
        missing_freqs = []

        for device_freq in device_frequency_grid:
            # Check if component has data at this frequency (within tolerance)
            found = False
            for comp_freq in component_freqs:
                if abs(comp_freq - device_freq) / device_freq < tolerance:
                    found = True
                    break
            if not found:
                missing_freqs.append(device_freq)

        return len(missing_freqs) == 0, missing_freqs

    def get_insertion_loss_db(self) -> NDArray[np.float64]:
        """Get insertion loss in dB at all frequencies.

        Insertion Loss = -20 * log10(|S21|)
        """
        s21 = self.s21
        if len(s21) == 0:
            return np.array([])

        magnitude = np.abs(s21)
        magnitude = np.where(magnitude < 1e-10, 1e-10, magnitude)
        return -20 * np.log10(magnitude)

    def infer_component_type(self) -> ComponentType:
        """Infer component type from S-parameter behavior.

        Capacitor: Impedance magnitude decreases with frequency
        Inductor: Impedance magnitude increases with frequency
        """
        if len(self.frequency) < 2:
            return ComponentType.UNKNOWN

        # Calculate impedance at low and high frequencies
        z0 = self.reference_impedance
        s11_low = self.s11[0]
        s11_high = self.s11[-1]

        z_low = z0 * (1 + s11_low) / (1 - s11_low)
        z_high = z0 * (1 + s11_high) / (1 - s11_high)

        # Compare imaginary parts (reactance)
        x_low = z_low.imag
        x_high = z_high.imag

        # Capacitor: negative reactance (decreasing magnitude)
        # Inductor: positive reactance (increasing magnitude)
        if x_low < 0 and x_high < 0:
            # Both negative (capacitive)
            if abs(x_low) > abs(x_high):
                return ComponentType.CAPACITOR
        elif x_low > 0 and x_high > 0:
            # Both positive (inductive)
            if x_high > x_low:
                return ComponentType.INDUCTOR

        # Fallback: check sign of reactance at center frequency
        center_idx = len(self.frequency) // 2
        s11_center = self.s11[center_idx]
        z_center = z0 * (1 + s11_center) / (1 - s11_center)

        if z_center.imag < 0:
            return ComponentType.CAPACITOR
        elif z_center.imag > 0:
            return ComponentType.INDUCTOR

        return ComponentType.UNKNOWN

    def __repr__(self) -> str:
        type_str = self.component_type.value if self.component_type else "unknown"
        value_str = self.value or "N/A"
        return (
            f"ComponentModel("
            f"{self.manufacturer} {self.part_number}, "
            f"type={type_str}, "
            f"value={value_str}, "
            f"freq=[{self.frequency.min()/1e9:.3f}, {self.frequency.max()/1e9:.3f}] GHz)"
        )
