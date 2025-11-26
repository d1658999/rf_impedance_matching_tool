"""SNP File entity representing S-parameters of a device.

Per data-model.md: Represents S-parameters of a device (main device being matched)
at discrete frequency points.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np
from numpy.typing import NDArray


@dataclass
class SNPFile:
    """S-parameter file representation for RF devices.

    Attributes:
        file_path: Path to the original .snp file
        frequency: Array of frequency points in Hz
        s_parameters: Dict mapping S-param names ('s11', 's21', etc.) to complex arrays
        num_ports: Number of ports (1, 2, 3, or 4)
        source_port_index: 0-indexed source port (default 0)
        load_port_index: 0-indexed load port (default 1 for 2-port)
        reference_impedance: Reference impedance in Ohms (default 50.0)
        frequency_unit: Original frequency unit from file
        s_parameter_format: Original S-param format from file
    """

    file_path: str
    frequency: NDArray[np.float64]
    s_parameters: Dict[str, NDArray[np.complex128]]
    num_ports: int
    source_port_index: int = 0
    load_port_index: int = 1
    reference_impedance: float = 50.0
    frequency_unit: str = "Hz"
    s_parameter_format: str = "dB/angle"
    _network: Optional[object] = field(default=None, repr=False)  # scikit-rf Network object

    def __post_init__(self) -> None:
        """Validate data after initialization."""
        # Validate frequency array
        if len(self.frequency) == 0:
            raise ValueError("Frequency array cannot be empty")

        # Check monotonically increasing
        if not np.all(np.diff(self.frequency) > 0):
            raise ValueError("Frequency array must be sorted and monotonically increasing")

        # Validate port indices
        if not (0 <= self.source_port_index < self.num_ports):
            raise ValueError(
                f"Source port index {self.source_port_index} invalid for {self.num_ports}-port network"
            )
        if not (0 <= self.load_port_index < self.num_ports):
            raise ValueError(
                f"Load port index {self.load_port_index} invalid for {self.num_ports}-port network"
            )

        # Validate S-parameter array lengths
        for name, values in self.s_parameters.items():
            if len(values) != len(self.frequency):
                raise ValueError(
                    f"S-parameter '{name}' length ({len(values)}) doesn't match frequency length ({len(self.frequency)})"
                )

    @property
    def center_frequency(self) -> float:
        """Return the center frequency in Hz."""
        return float(np.mean(self.frequency))

    @property
    def frequency_range(self) -> Tuple[float, float]:
        """Return (min_freq, max_freq) in Hz."""
        return float(self.frequency[0]), float(self.frequency[-1])

    @property
    def num_frequency_points(self) -> int:
        """Return number of frequency points."""
        return len(self.frequency)

    @property
    def s11(self) -> NDArray[np.complex128]:
        """Get S11 (reflection at port 1)."""
        return self.s_parameters.get("s11", np.array([], dtype=np.complex128))

    def impedance_at_frequency(self, freq: float) -> complex:
        """Calculate impedance at a specific frequency from S11.

        Uses formula: Z = Z0 * (1 + S11) / (1 - S11)

        Args:
            freq: Frequency in Hz

        Returns:
            Complex impedance in Ohms

        Raises:
            ValueError: If frequency is outside the data range
        """
        if freq < self.frequency[0] or freq > self.frequency[-1]:
            raise ValueError(
                f"Frequency {freq/1e9:.3f} GHz outside range "
                f"[{self.frequency[0]/1e9:.3f}, {self.frequency[-1]/1e9:.3f}] GHz"
            )

        # Find nearest frequency index
        idx = np.argmin(np.abs(self.frequency - freq))
        s11 = self.s11[idx]

        # Calculate impedance from S11
        z0 = self.reference_impedance
        # Handle edge case where S11 ≈ 1 (open circuit)
        if np.abs(1 - s11) < 1e-10:
            return complex(float("inf"), 0)

        impedance = z0 * (1 + s11) / (1 - s11)
        return complex(impedance)

    def get_impedance_trajectory(self) -> NDArray[np.complex128]:
        """Get impedance values at all frequency points.

        Returns:
            Array of complex impedances
        """
        z0 = self.reference_impedance
        s11 = self.s11

        # Vectorized calculation
        # Avoid division by zero
        denominator = 1 - s11
        denominator = np.where(np.abs(denominator) < 1e-10, 1e-10, denominator)

        return z0 * (1 + s11) / denominator

    def get_reflection_coefficient(self) -> NDArray[np.float64]:
        """Get magnitude of reflection coefficient |S11| at all frequencies."""
        return np.abs(self.s11)

    def get_vswr(self) -> NDArray[np.float64]:
        """Get VSWR at all frequencies.

        VSWR = (1 + |S11|) / (1 - |S11|)
        """
        gamma = np.abs(self.s11)
        # Avoid division by zero
        denominator = 1 - gamma
        denominator = np.where(np.abs(denominator) < 1e-10, 1e-10, denominator)
        return (1 + gamma) / denominator

    def get_return_loss_db(self) -> NDArray[np.float64]:
        """Get return loss in dB at all frequencies.

        Return Loss = -20 * log10(|S11|)
        """
        gamma = np.abs(self.s11)
        # Avoid log(0)
        gamma = np.where(gamma < 1e-10, 1e-10, gamma)
        return -20 * np.log10(gamma)

    def __repr__(self) -> str:
        return (
            f"SNPFile(file={self.file_path}, "
            f"ports={self.num_ports}, "
            f"freq_range=[{self.frequency[0]/1e9:.3f}, {self.frequency[-1]/1e9:.3f}] GHz, "
            f"points={len(self.frequency)})"
        )
