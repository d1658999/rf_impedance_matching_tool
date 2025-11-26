"""Bandwidth optimization module.

T049: Implement bandwidth optimizer for multi-frequency optimization.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple, List
import numpy as np
from numpy.typing import NDArray

from snp_tool.models.snp_file import SNPFile
from snp_tool.models.component import ComponentModel
from snp_tool.models.component_library import ComponentLibrary
from snp_tool.models.matching_network import MatchingNetwork
from snp_tool.models.optimization_result import OptimizationResult
from snp_tool.optimizer.grid_search import GridSearchOptimizer
from snp_tool.optimizer.cascader import cascade_networks
from snp_tool.optimizer.metrics import vswr_from_s11


class BandwidthOptimizer:
    """Optimizer for wide-band impedance matching.

    Extends GridSearchOptimizer to optimize for minimum maximum VSWR
    across the entire frequency band, rather than at a single frequency.
    """

    def __init__(self, device: SNPFile, component_library: ComponentLibrary):
        """Initialize bandwidth optimizer.

        Args:
            device: Main device SNP file
            component_library: Library of matching components
        """
        self.device = device
        self.library = component_library
        self._base_optimizer = GridSearchOptimizer(device, component_library)

    def optimize(
        self,
        topology: str = "L-section",
        frequency_range: Optional[Tuple[float, float]] = None,
        vswr_target: float = 2.0,
        max_iterations: Optional[int] = None,
    ) -> OptimizationResult:
        """Optimize matching network for bandwidth.

        Minimizes the maximum VSWR across the frequency band.

        Args:
            topology: Network topology ('L-section', 'Pi-section', 'T-section')
            frequency_range: Optional (min_hz, max_hz) to optimize over
            vswr_target: Target VSWR threshold for "matched" (default 2.0)
            max_iterations: Maximum combinations to evaluate

        Returns:
            OptimizationResult with bandwidth metrics
        """
        start_time = time.time()

        # Get frequency indices to optimize over
        if frequency_range is not None:
            freq_min, freq_max = frequency_range
            freq_mask = (self.device.frequency >= freq_min) & (
                self.device.frequency <= freq_max
            )
            freq_indices = np.where(freq_mask)[0]
            if len(freq_indices) == 0:
                raise ValueError(f"No frequencies in range {frequency_range}")
        else:
            freq_indices = np.arange(len(self.device.frequency))

        # Get components filtered by frequency coverage
        device_freq_min = self.device.frequency.min()
        device_freq_max = self.device.frequency.max()

        capacitors = [
            c
            for c in self.library.get_capacitors()
            if c.frequency.min() <= device_freq_min and c.frequency.max() >= device_freq_max
        ]
        inductors = [
            c
            for c in self.library.get_inductors()
            if c.frequency.min() <= device_freq_min and c.frequency.max() >= device_freq_max
        ]

        if not capacitors or not inductors:
            # Fall back to base optimizer
            return self._base_optimizer.optimize(topology=topology)

        # Grid search for minimum max-VSWR
        best_result: Optional[OptimizationResult] = None
        best_max_vswr = float("inf")
        iterations = 0
        first_valid_network = None  # Keep track of first valid network for error case

        # Get component combinations based on topology
        if topology == "L-section":
            combinations = self._get_l_section_combinations(capacitors, inductors)
        elif topology == "Pi-section":
            combinations = self._get_pi_section_combinations(capacitors, inductors)
        elif topology == "T-section":
            combinations = self._get_t_section_combinations(capacitors, inductors)
        else:
            combinations = self._get_l_section_combinations(capacitors, inductors)

        if max_iterations:
            combinations = combinations[:max_iterations]

        for components in combinations:
            iterations += 1

            try:
                # Build matching network
                network = self._build_network(components, topology)

                # Track first valid network for fallback
                if first_valid_network is None:
                    first_valid_network = (network, components)

                if network.cascaded_s_parameters is None:
                    continue

                # Calculate max VSWR across band
                s11 = network.cascaded_s_parameters.get("s11")
                if s11 is None:
                    continue

                vswr_array = vswr_from_s11(s11[freq_indices])
                max_vswr = np.max(vswr_array)

                if max_vswr < best_max_vswr:
                    best_max_vswr = max_vswr
                    best_result = self._create_result(
                        network,
                        components,
                        topology,
                        freq_indices,
                        iterations,
                        start_time,
                    )

            except Exception:
                continue

        duration = time.time() - start_time

        if best_result is None and first_valid_network is not None:
            # Use first valid network as fallback
            network, components = first_valid_network
            best_result = self._create_result(
                network,
                components,
                topology,
                freq_indices,
                iterations,
                start_time,
            )

        if best_result is None:
            # Still no result - fall back to base optimizer
            return self._base_optimizer.optimize(topology=topology)

        return best_result

    def _get_l_section_combinations(
        self, capacitors: List[ComponentModel], inductors: List[ComponentModel]
    ) -> List[List[ComponentModel]]:
        """Generate L-section component combinations."""
        combinations = []

        # Cap-Ind and Ind-Cap arrangements
        for cap in capacitors:
            for ind in inductors:
                combinations.append([cap, ind])
                combinations.append([ind, cap])

        return combinations

    def _get_pi_section_combinations(
        self, capacitors: List[ComponentModel], inductors: List[ComponentModel]
    ) -> List[List[ComponentModel]]:
        """Generate Pi-section component combinations."""
        combinations = []

        # Cap-Ind-Cap arrangements
        for cap1 in capacitors:
            for ind in inductors:
                for cap2 in capacitors:
                    combinations.append([cap1, ind, cap2])

        return combinations[:1000]  # Limit to 1000 for performance

    def _get_t_section_combinations(
        self, capacitors: List[ComponentModel], inductors: List[ComponentModel]
    ) -> List[List[ComponentModel]]:
        """Generate T-section component combinations."""
        combinations = []

        # Ind-Cap-Ind arrangements
        for ind1 in inductors:
            for cap in capacitors:
                for ind2 in inductors:
                    combinations.append([ind1, cap, ind2])

        return combinations[:1000]  # Limit to 1000 for performance

    def _build_network(
        self, components: List[ComponentModel], topology: str
    ) -> MatchingNetwork:
        """Build matching network from components."""
        # Extract S-parameters at device frequencies
        s_params_list = []

        # Device S-parameters
        s_params_list.append(self.device.s_parameters)

        # Component S-parameters (interpolated to device frequencies)
        for comp in components:
            interp_s = self._interpolate_s_params(comp, self.device.frequency)
            s_params_list.append(interp_s)

        # Cascade
        cascaded = cascade_networks(s_params_list, self.device.frequency)

        # Determine component order based on topology
        if topology == "L-section":
            component_order = ["series", "shunt"]
        elif topology == "Pi-section":
            component_order = ["shunt", "series", "shunt"]
        elif topology == "T-section":
            component_order = ["series", "shunt", "series"]
        else:
            component_order = ["series"] * len(components)

        return MatchingNetwork(
            components=components,
            topology=topology,
            component_order=component_order,
            cascaded_s_parameters=cascaded,
            frequency=self.device.frequency,
        )

    def _interpolate_s_params(
        self, component: ComponentModel, target_freq: NDArray[np.float64]
    ) -> dict:
        """Interpolate component S-parameters to target frequencies."""
        result = {}

        for key, values in component.s_parameters.items():
            # Linear interpolation (magnitude and phase separately)
            mag = np.abs(values)
            phase = np.angle(values)

            interp_mag = np.interp(target_freq, component.frequency, mag)
            interp_phase = np.interp(target_freq, component.frequency, phase)

            result[key] = interp_mag * np.exp(1j * interp_phase)

        return result

    def _create_result(
        self,
        network: MatchingNetwork,
        components: List[ComponentModel],
        topology: str,
        freq_indices: NDArray[np.int64],
        iterations: int,
        start_time: float,
    ) -> OptimizationResult:
        """Create optimization result with bandwidth metrics."""
        duration = time.time() - start_time

        # Calculate metrics
        s11 = network.cascaded_s_parameters.get("s11", np.array([]))
        vswr_array = vswr_from_s11(s11)

        center_idx = len(self.device.frequency) // 2
        vswr_at_center = float(vswr_array[center_idx]) if len(vswr_array) > center_idx else float("inf")

        # Calculate bandwidth where VSWR < 2.0
        bandwidth_hz = self._calculate_bandwidth(vswr_array, target=2.0)

        from snp_tool.optimizer.metrics import (
            reflection_coefficient_from_s11,
            return_loss_from_s11,
        )

        return OptimizationResult(
            matching_network=network,
            main_device=self.device,
            component_library_size=len(self.library.components),
            topology_selected=topology,
            frequency_range=(self.device.frequency.min(), self.device.frequency.max()),
            optimization_target="bandwidth",
            center_frequency=self.device.center_frequency,
            optimization_metrics={
                "reflection_coefficient_at_center": float(
                    reflection_coefficient_from_s11(s11[center_idx])
                )
                if len(s11) > center_idx
                else 1.0,
                "vswr_at_center": vswr_at_center,
                "return_loss_at_center_dB": float(return_loss_from_s11(s11[center_idx]))
                if len(s11) > center_idx
                else 0.0,
                "max_vswr_in_band": float(np.max(vswr_array[freq_indices])),
                "bandwidth_vswr_lt_2": bandwidth_hz,
                "bandwidth_hz": bandwidth_hz,
                "grid_search_iterations": iterations,
                "grid_search_duration_sec": duration,
            },
            success=vswr_at_center <= 2.0,
        )

    def _calculate_bandwidth(
        self, vswr_array: NDArray[np.float64], target: float = 2.0
    ) -> float:
        """Calculate bandwidth where VSWR is below target.

        Args:
            vswr_array: VSWR values across frequency
            target: VSWR threshold

        Returns:
            Bandwidth in Hz where VSWR < target
        """
        matched_mask = vswr_array <= target
        if not np.any(matched_mask):
            return 0.0

        # Find contiguous regions
        freq = self.device.frequency
        matched_freqs = freq[matched_mask]

        if len(matched_freqs) < 2:
            return 0.0

        return float(matched_freqs.max() - matched_freqs.min())
