"""Matching Network entity representing an optimized impedance matching solution.

Per data-model.md: Represents the optimized 2-stage matching network (solution)
connecting main device to 50Ω load.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import numpy as np
from numpy.typing import NDArray

from .component import ComponentModel


class Topology(Enum):
    """Matching network topology options.

    Per Q3 clarification: Engineer chooses from preset topologies.
    """

    L_SECTION = "L-section"  # series-then-shunt
    PI_SECTION = "Pi-section"  # shunt-then-series
    T_SECTION = "T-section"  # series-shunt-series
    CUSTOM = "custom"


@dataclass
class MatchingNetwork:
    """Optimized matching network solution.

    Attributes:
        components: List of components in order (1-3 components)
        topology: Network topology (L-section, Pi-section, T-section)
        component_order: Connection order for each component (['series', 'shunt'])
        cascaded_s_parameters: Combined S-parameters after cascading
        frequency: Frequency points for cascaded S-params
        reference_impedance: Reference impedance (default 50Ω)
    """

    components: List[ComponentModel]
    topology: Topology
    component_order: List[str]  # ['series', 'shunt'] or ['shunt', 'series', 'shunt']
    frequency: NDArray[np.float64]
    cascaded_s_parameters: Dict[str, NDArray[np.complex128]] = field(default_factory=dict)
    reference_impedance: float = 50.0

    def __post_init__(self) -> None:
        """Validate network configuration."""
        if len(self.components) < 1 or len(self.components) > 3:
            raise ValueError(f"Network must have 1-3 components, got {len(self.components)}")

        if len(self.component_order) != len(self.components):
            raise ValueError(
                f"Component order length ({len(self.component_order)}) "
                f"must match components ({len(self.components)})"
            )

        for order in self.component_order:
            if order not in ("series", "shunt"):
                raise ValueError(f"Invalid component order: {order}")

    @property
    def s11(self) -> NDArray[np.complex128]:
        """Get S11 of cascaded network."""
        return self.cascaded_s_parameters.get("s11", np.array([], dtype=np.complex128))

    @property
    def num_components(self) -> int:
        """Get number of components in network."""
        return len(self.components)

    def reflection_coefficient_at_frequency(self, freq: float) -> float:
        """Get |S11| at specified frequency.

        Args:
            freq: Frequency in Hz

        Returns:
            Magnitude of reflection coefficient (0-1)
        """
        if len(self.s11) == 0:
            raise ValueError("No cascaded S-parameters available")

        idx = np.argmin(np.abs(self.frequency - freq))
        return float(np.abs(self.s11[idx]))

    def vswr_at_frequency(self, freq: float) -> float:
        """Get VSWR at specified frequency.

        VSWR = (1 + |S11|) / (1 - |S11|)

        Args:
            freq: Frequency in Hz

        Returns:
            VSWR value (≥ 1.0)
        """
        gamma = self.reflection_coefficient_at_frequency(freq)
        if gamma >= 1.0:
            return float("inf")
        return (1 + gamma) / (1 - gamma)

    def return_loss_db_at_frequency(self, freq: float) -> float:
        """Get return loss in dB at specified frequency.

        Return Loss = -20 * log10(|S11|)

        Args:
            freq: Frequency in Hz

        Returns:
            Return loss in dB (positive value, higher is better)
        """
        gamma = self.reflection_coefficient_at_frequency(freq)
        if gamma < 1e-10:
            return 100.0  # Cap at 100 dB for numerical stability
        return -20 * np.log10(gamma)

    def impedance_at_frequency(self, freq: float) -> complex:
        """Get input impedance at specified frequency.

        Z = Z0 * (1 + S11) / (1 - S11)
        """
        if len(self.s11) == 0:
            raise ValueError("No cascaded S-parameters available")

        idx = np.argmin(np.abs(self.frequency - freq))
        s11 = self.s11[idx]

        if np.abs(1 - s11) < 1e-10:
            return complex(float("inf"), 0)

        return self.reference_impedance * (1 + s11) / (1 - s11)

    def get_reflection_coefficient(self) -> NDArray[np.float64]:
        """Get |S11| at all frequencies."""
        return np.abs(self.s11)

    def get_vswr(self) -> NDArray[np.float64]:
        """Get VSWR at all frequencies."""
        gamma = np.abs(self.s11)
        denominator = 1 - gamma
        denominator = np.where(np.abs(denominator) < 1e-10, 1e-10, denominator)
        return (1 + gamma) / denominator

    def get_return_loss_db(self) -> NDArray[np.float64]:
        """Get return loss in dB at all frequencies."""
        gamma = np.abs(self.s11)
        gamma = np.where(gamma < 1e-10, 1e-10, gamma)
        return -20 * np.log10(gamma)

    def get_max_vswr_in_band(self) -> tuple:
        """Get maximum VSWR in the frequency band.

        Returns:
            Tuple of (max_vswr, frequency_at_max)
        """
        vswr = self.get_vswr()
        max_idx = np.argmax(vswr)
        return float(vswr[max_idx]), float(self.frequency[max_idx])

    def get_min_vswr_in_band(self) -> tuple:
        """Get minimum VSWR in the frequency band.

        Returns:
            Tuple of (min_vswr, frequency_at_min)
        """
        vswr = self.get_vswr()
        min_idx = np.argmin(vswr)
        return float(vswr[min_idx]), float(self.frequency[min_idx])

    def get_schematic_text(self) -> str:
        """Generate ASCII schematic representation."""
        parts = ["Source"]

        for i, (comp, order) in enumerate(zip(self.components, self.component_order)):
            type_str = comp.component_type.value[0].upper()  # 'C' or 'L'
            value_str = comp.value or "?"

            if order == "series":
                parts.append(f"──[{type_str}: {value_str}]──")
            else:  # shunt
                parts.append(f"┬─[{type_str}: {value_str}]─┴")

        parts.append("── 50Ω Load")
        return "".join(parts)

    def __repr__(self) -> str:
        comp_str = ", ".join(
            f"{c.component_type.value[0].upper()}={c.value or '?'}" for c in self.components
        )
        return f"MatchingNetwork(topology={self.topology.value}, components=[{comp_str}])"
