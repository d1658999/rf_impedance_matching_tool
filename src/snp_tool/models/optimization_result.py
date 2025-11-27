"""Optimization Result entity representing a complete matching solution.

Per data-model.md: Represents the complete solution returned by the optimizer.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json
import numpy as np

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .snp_file import SNPFile
    from .matching_network import MatchingNetwork, Topology
else:
    from .snp_file import SNPFile
    from .matching_network import MatchingNetwork, Topology


@dataclass
class OptimizationResult:
    """Complete optimization result with solution and metrics.

    Attributes:
        matching_network: The optimized matching network
        main_device: Input device being matched
        topology_selected: Selected topology
        frequency_range: Tuple of (start_freq, end_freq) used for optimization
        optimization_target: 'single-frequency' or 'bandwidth'
        center_frequency: Target frequency for optimization
        optimization_metrics: Dict of computed metrics
        success: Whether optimization met success criteria
        component_library_size: Number of components searched
        export_paths: Dict of exported file paths
        error_message: Error message if optimization failed
        combinations_evaluated: Number of component combinations evaluated
    """

    matching_network: Optional[MatchingNetwork] = None
    main_device: Optional[SNPFile] = None
    topology_selected: Optional[Topology] = None
    frequency_range: tuple = (0.0, 0.0)  # (start_freq, end_freq)
    center_frequency: float = 0.0
    optimization_metrics: Dict = field(default_factory=dict)
    optimization_target: str = "single-frequency"
    success: bool = False
    component_library_size: int = 0
    export_paths: Dict[str, str] = field(default_factory=dict)
    error_message: str = ""
    combinations_evaluated: int = 0

    def __post_init__(self) -> None:
        """Compute metrics if not provided."""
        if not self.optimization_metrics:
            self._compute_metrics()

    def _compute_metrics(self) -> None:
        """Compute optimization metrics from matching network."""
        if not self.matching_network.cascaded_s_parameters:
            return

        try:
            # Reflection at center frequency
            gamma = self.matching_network.reflection_coefficient_at_frequency(self.center_frequency)
            vswr = self.matching_network.vswr_at_frequency(self.center_frequency)
            return_loss = self.matching_network.return_loss_db_at_frequency(self.center_frequency)

            # Band metrics
            max_vswr, max_vswr_freq = self.matching_network.get_max_vswr_in_band()
            min_vswr, min_vswr_freq = self.matching_network.get_min_vswr_in_band()

            # Impedance at center
            impedance = self.matching_network.impedance_at_frequency(self.center_frequency)

            self.optimization_metrics = {
                "reflection_coefficient_at_center": gamma,
                "vswr_at_center": vswr,
                "return_loss_at_center_dB": return_loss,
                "max_vswr_in_band": max_vswr,
                "max_vswr_frequency": max_vswr_freq,
                "min_vswr_in_band": min_vswr,
                "min_vswr_frequency": min_vswr_freq,
                "impedance_at_center": impedance,
                "impedance_real": impedance.real,
                "impedance_imag": impedance.imag,
            }

            # Check success criteria: 50Ω ± 10Ω or VSWR < 2.0
            target_z = self.matching_network.reference_impedance
            z_error = abs(impedance - target_z)
            self.success = z_error <= 10.0 or vswr < 2.0

        except Exception:
            pass

    def export_schematic(self, path: str) -> str:
        """Export component list and topology as text file.

        Args:
            path: Output file path

        Returns:
            Path to exported file
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "RF Impedance Matching Network",
            "=" * 40,
            f"Device File: {self.main_device.file_path}",
            f"Topology: {self.topology_selected.value}",
            f"Target Frequency: {self.center_frequency / 1e9:.3f} GHz",
            f"Frequency Range: [{self.frequency_range[0]/1e9:.3f}, {self.frequency_range[1]/1e9:.3f}] GHz",
            "",
            "Components:",
            "-" * 40,
        ]

        for i, (comp, order) in enumerate(
            zip(self.matching_network.components, self.matching_network.component_order)
        ):
            lines.extend(
                [
                    f"Component {i + 1} ({order.upper()}):",
                    f"  Manufacturer: {comp.manufacturer}",
                    f"  Part Number: {comp.part_number}",
                    f"  Type: {comp.component_type.value}",
                    f"  Value: {comp.value or 'N/A'}",
                    f"  S2P File: {comp.s2p_file_path}",
                    "",
                ]
            )

        lines.extend(
            [
                "Schematic:",
                "-" * 40,
                self.matching_network.get_schematic_text(),
                "",
                "Metrics:",
                "-" * 40,
            ]
        )

        if self.optimization_metrics:
            for key, value in self.optimization_metrics.items():
                if isinstance(value, float):
                    if "frequency" in key.lower():
                        lines.append(f"  {key}: {value / 1e9:.3f} GHz")
                    elif "dB" in key or "return_loss" in key:
                        lines.append(f"  {key}: {value:.2f} dB")
                    elif "vswr" in key.lower():
                        lines.append(f"  {key}: {value:.3f}")
                    else:
                        lines.append(f"  {key}: {value:.4f}")
                elif isinstance(value, complex):
                    lines.append(f"  {key}: {value.real:.2f} + {value.imag:.2f}j Ω")
                else:
                    lines.append(f"  {key}: {value}")

        lines.extend(
            [
                "",
                f"Optimization Success: {'YES' if self.success else 'NO'}",
                f"Components Searched: {self.component_library_size}",
            ]
        )

        output_path.write_text("\n".join(lines))
        self.export_paths["schematic_txt"] = str(output_path)
        return str(output_path)

    def export_s_parameters(self, path: str) -> str:
        """Export cascaded S-parameters as Touchstone .s2p file.

        Args:
            path: Output file path

        Returns:
            Path to exported file
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"! Cascaded S-parameters: {self.main_device.file_path} + matching network",
            f"! Topology: {self.topology_selected.value}",
            f"! Target: {self.center_frequency / 1e9:.3f} GHz",
            "! Generated by SNP Tool",
            "!",
            "# GHz S MA R 50",
        ]

        # Export S-parameters
        freq = self.matching_network.frequency
        s11 = self.matching_network.s11

        # Get S21 if available, otherwise use S11 as placeholder
        s21 = self.matching_network.cascaded_s_parameters.get("s21", s11)
        s12 = self.matching_network.cascaded_s_parameters.get("s12", s21)
        s22 = self.matching_network.cascaded_s_parameters.get("s22", s11)

        for i in range(len(freq)):
            f_ghz = freq[i] / 1e9
            # Convert to magnitude/angle format
            s11_mag = np.abs(s11[i])
            s11_ang = np.angle(s11[i], deg=True)
            s21_mag = np.abs(s21[i])
            s21_ang = np.angle(s21[i], deg=True)
            s12_mag = np.abs(s12[i])
            s12_ang = np.angle(s12[i], deg=True)
            s22_mag = np.abs(s22[i])
            s22_ang = np.angle(s22[i], deg=True)

            lines.append(
                f"{f_ghz:.6f}  {s11_mag:.6f} {s11_ang:.2f}  "
                f"{s21_mag:.6f} {s21_ang:.2f}  "
                f"{s12_mag:.6f} {s12_ang:.2f}  "
                f"{s22_mag:.6f} {s22_ang:.2f}"
            )

        output_path.write_text("\n".join(lines))
        self.export_paths["s_parameters_s2p"] = str(output_path)
        return str(output_path)

    def to_dict(self) -> dict:
        """Convert result to dictionary for JSON export."""
        return {
            "device_file": self.main_device.file_path,
            "topology": self.topology_selected.value,
            "frequency_range_ghz": [f / 1e9 for f in self.frequency_range],
            "center_frequency_ghz": self.center_frequency / 1e9,
            "optimization_target": self.optimization_target,
            "success": self.success,
            "components": [
                {
                    "manufacturer": c.manufacturer,
                    "part_number": c.part_number,
                    "type": c.component_type.value,
                    "value": c.value,
                    "order": o,
                }
                for c, o in zip(
                    self.matching_network.components, self.matching_network.component_order
                )
            ],
            "metrics": {
                k: (v.real if isinstance(v, complex) else v)
                for k, v in self.optimization_metrics.items()
            },
            "component_library_size": self.component_library_size,
            "export_paths": self.export_paths,
        }

    def __repr__(self) -> str:
        status = "✓ SUCCESS" if self.success else "✗ FAILED"
        vswr = self.optimization_metrics.get("vswr_at_center", "N/A")
        if isinstance(vswr, float):
            vswr = f"{vswr:.3f}"
        return (
            f"OptimizationResult({status}, "
            f"topology={self.topology_selected.value}, "
            f"VSWR={vswr})"
        )
