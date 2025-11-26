"""Grid search optimizer for impedance matching.

Per contracts/grid_optimizer.md and Q1 clarification: Implement grid search
algorithm (brute-force enumeration, deterministic, MVP-aligned).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from itertools import product
import time
import numpy as np
from numpy.typing import NDArray

from ..models.snp_file import SNPFile
from ..models.component import ComponentModel, ComponentType
from ..models.component_library import ComponentLibrary
from ..models.matching_network import MatchingNetwork, Topology
from ..models.optimization_result import OptimizationResult
from .cascader import cascade_with_topology
from .metrics import reflection_coefficient_from_s11, vswr_from_s11, impedance_from_s11
from ..utils.logging import get_logger
from ..utils.exceptions import OptimizationError


@dataclass
class GridSearchConfig:
    """Configuration for grid search optimization."""

    topology: Topology = Topology.L_SECTION
    frequency_range: Optional[Tuple[float, float]] = None
    target_frequency: Optional[float] = None
    max_components: int = 2
    vswr_target: float = 2.0
    impedance_tolerance: float = 10.0
    reference_impedance: float = 50.0


class GridSearchOptimizer:
    """Grid search optimizer for impedance matching networks.

    Per Q1 clarification: Uses brute-force enumeration of all component combinations,
    deterministic and reproducible results.
    """

    def __init__(
        self,
        device: SNPFile,
        component_library: ComponentLibrary,
        config: Optional[GridSearchConfig] = None,
    ):
        """Initialize optimizer.

        Args:
            device: Main device to be matched
            component_library: Library of available components
            config: Optional configuration (uses defaults if not provided)
        """
        self.device = device
        self.library = component_library
        self.config = config or GridSearchConfig()
        self.logger = get_logger()

        # Track optimization metrics
        self.search_iterations = 0
        self.search_duration = 0.0

    def optimize(
        self,
        topology: Optional[Topology] = None,
        frequency_range: Optional[Tuple[float, float]] = None,
        target_frequency: Optional[float] = None,
    ) -> OptimizationResult:
        """Run grid search optimization.

        Args:
            topology: Network topology (L-section, Pi-section, T-section)
            frequency_range: (start_freq, end_freq) in Hz
            target_frequency: Target frequency for optimization (default: center)

        Returns:
            OptimizationResult with best solution
        """
        topology = topology or self.config.topology
        freq_range = frequency_range or self.config.frequency_range or self.device.frequency_range
        target_freq = target_frequency or self.config.target_frequency

        if target_freq is None:
            target_freq = (freq_range[0] + freq_range[1]) / 2

        self.logger.info(
            f"Starting grid search optimization",
            topology=topology.value,
            target_freq=f"{target_freq/1e9:.3f} GHz",
            components=len(self.library),
        )

        # Filter components by frequency coverage
        valid_components, invalid = self.library.validate_frequency_coverage(
            self.device.frequency
        )

        if not valid_components:
            raise OptimizationError(
                "No components have valid frequency coverage",
                topology=topology.value,
                target_frequency=target_freq,
            )

        self.logger.info(
            f"Components with valid frequency coverage: {len(valid_components)} "
            f"(rejected: {len(invalid)})"
        )

        # Separate by type
        capacitors = [c for c in valid_components if c.component_type == ComponentType.CAPACITOR]
        inductors = [c for c in valid_components if c.component_type == ComponentType.INDUCTOR]

        self.logger.debug(f"Available: {len(capacitors)} capacitors, {len(inductors)} inductors")

        # Run grid search based on topology
        start_time = time.time()

        if topology == Topology.L_SECTION:
            result = self._search_l_section(
                capacitors, inductors, freq_range, target_freq
            )
        elif topology == Topology.PI_SECTION:
            result = self._search_pi_section(
                capacitors, inductors, freq_range, target_freq
            )
        elif topology == Topology.T_SECTION:
            result = self._search_t_section(
                capacitors, inductors, freq_range, target_freq
            )
        else:
            raise OptimizationError(f"Unsupported topology: {topology.value}")

        self.search_duration = time.time() - start_time

        # Update result with search metrics
        if result.optimization_metrics:
            result.optimization_metrics["grid_search_iterations"] = self.search_iterations
            result.optimization_metrics["grid_search_duration_sec"] = self.search_duration

        self.logger.info(
            f"Optimization complete",
            iterations=self.search_iterations,
            duration=f"{self.search_duration:.2f}s",
            success=result.success,
        )

        return result

    def _search_l_section(
        self,
        capacitors: List[ComponentModel],
        inductors: List[ComponentModel],
        freq_range: Tuple[float, float],
        target_freq: float,
    ) -> OptimizationResult:
        """Search L-section topologies (series-shunt configurations).

        Tries:
        - Series C, Shunt L
        - Series L, Shunt C
        - Series C, Shunt C
        - Series L, Shunt L
        """
        best_result = None
        best_reflection = float("inf")

        all_components = capacitors + inductors

        # L-section configurations: (comp1, comp2, order)
        configurations = [
            (capacitors, inductors, ["series", "shunt"]),  # Series C, Shunt L
            (inductors, capacitors, ["series", "shunt"]),  # Series L, Shunt C
            (capacitors, capacitors, ["series", "shunt"]),  # Series C, Shunt C
            (inductors, inductors, ["series", "shunt"]),  # Series L, Shunt L
        ]

        for comp1_list, comp2_list, order in configurations:
            if not comp1_list or not comp2_list:
                continue

            for comp1, comp2 in product(comp1_list, comp2_list):
                self.search_iterations += 1

                try:
                    # Build matching network
                    network, reflection = self._evaluate_combination(
                        [comp1, comp2], order, target_freq
                    )

                    if reflection < best_reflection:
                        best_reflection = reflection
                        best_result = self._create_result(
                            network, freq_range, target_freq, Topology.L_SECTION
                        )

                except Exception as e:
                    self.logger.debug(f"Combination failed: {str(e)}")
                    continue

        if best_result is None:
            raise OptimizationError(
                "No valid L-section solution found",
                topology="L-section",
                target_frequency=target_freq,
            )

        return best_result

    def _search_pi_section(
        self,
        capacitors: List[ComponentModel],
        inductors: List[ComponentModel],
        freq_range: Tuple[float, float],
        target_freq: float,
    ) -> OptimizationResult:
        """Search Pi-section topologies (shunt-series configurations)."""
        best_result = None
        best_reflection = float("inf")

        configurations = [
            (capacitors, inductors, ["shunt", "series"]),
            (inductors, capacitors, ["shunt", "series"]),
        ]

        for comp1_list, comp2_list, order in configurations:
            if not comp1_list or not comp2_list:
                continue

            for comp1, comp2 in product(comp1_list, comp2_list):
                self.search_iterations += 1

                try:
                    network, reflection = self._evaluate_combination(
                        [comp1, comp2], order, target_freq
                    )

                    if reflection < best_reflection:
                        best_reflection = reflection
                        best_result = self._create_result(
                            network, freq_range, target_freq, Topology.PI_SECTION
                        )

                except Exception:
                    continue

        if best_result is None:
            raise OptimizationError(
                "No valid Pi-section solution found",
                topology="Pi-section",
                target_frequency=target_freq,
            )

        return best_result

    def _search_t_section(
        self,
        capacitors: List[ComponentModel],
        inductors: List[ComponentModel],
        freq_range: Tuple[float, float],
        target_freq: float,
    ) -> OptimizationResult:
        """Search T-section topologies (series-shunt-series)."""
        best_result = None
        best_reflection = float("inf")

        # T-section: 3 components (series-shunt-series)
        all_components = capacitors + inductors

        # Limit search space for 3-component networks
        for comp1, comp2, comp3 in product(all_components, all_components, all_components):
            self.search_iterations += 1

            order = ["series", "shunt", "series"]

            try:
                network, reflection = self._evaluate_combination(
                    [comp1, comp2, comp3], order, target_freq
                )

                if reflection < best_reflection:
                    best_reflection = reflection
                    best_result = self._create_result(
                        network, freq_range, target_freq, Topology.T_SECTION
                    )

            except Exception:
                continue

        if best_result is None:
            raise OptimizationError(
                "No valid T-section solution found",
                topology="T-section",
                target_frequency=target_freq,
            )

        return best_result

    def _evaluate_combination(
        self,
        components: List[ComponentModel],
        order: List[str],
        target_freq: float,
    ) -> Tuple[MatchingNetwork, float]:
        """Evaluate a component combination.

        Args:
            components: List of components to cascade
            order: Connection order (['series', 'shunt'] etc.)
            target_freq: Target frequency for evaluation

        Returns:
            Tuple of (MatchingNetwork, reflection_coefficient)
        """
        # Extract S-parameters
        device_s = self.device.s_parameters
        component_s_list = [c.s_parameters for c in components]
        component_freqs = [c.frequency for c in components]

        # Cascade networks
        cascaded = cascade_with_topology(
            device_s,
            component_s_list,
            order,
            self.device.frequency,
            self.device.reference_impedance,
            component_frequencies=component_freqs,
        )

        # Find target frequency index
        target_idx = np.argmin(np.abs(self.device.frequency - target_freq))

        # Get reflection coefficient at target frequency
        s11_at_target = cascaded["s11"][target_idx]
        reflection = float(np.abs(s11_at_target))

        # Create matching network object
        network = MatchingNetwork(
            components=components,
            topology=Topology.L_SECTION,  # Will be overwritten
            component_order=order,
            frequency=self.device.frequency,
            cascaded_s_parameters=cascaded,
            reference_impedance=self.device.reference_impedance,
        )

        return network, reflection

    def _create_result(
        self,
        network: MatchingNetwork,
        freq_range: Tuple[float, float],
        target_freq: float,
        topology: Topology,
    ) -> OptimizationResult:
        """Create optimization result from matching network."""
        # Update topology
        network.topology = topology

        return OptimizationResult(
            matching_network=network,
            main_device=self.device,
            topology_selected=topology,
            frequency_range=freq_range,
            center_frequency=target_freq,
            optimization_target="single-frequency",
            component_library_size=len(self.library),
        )
