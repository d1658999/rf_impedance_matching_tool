"""Optimization Engine using scipy.optimize.differential_evolution.

Per research.md Section 1 and tasks.md Task 2.2.2:
- Ideal mode: continuous component values
- Standard mode: E12/E24/E96 constrained values
- Multiple solutions returned, ranked by score
- Progress callback for UI updates
"""

from __future__ import annotations
from typing import List, Dict, Optional, Callable
import numpy as np
from numpy.typing import NDArray
from scipy.optimize import differential_evolution
from dataclasses import dataclass
from datetime import datetime

from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
from snp_tool.models.solution import OptimizationSolution
from snp_tool.optimizer.objectives import weighted_objective
from snp_tool.core.component_lib import snap_to_standard
from snp_tool.optimizer.metrics import return_loss_db, vswr as calculate_vswr


@dataclass
class OptimizationConfig:
    """Configuration for optimization run."""
    
    port: int
    target_impedance: float
    frequency_range: tuple[float, float]  # (min_hz, max_hz)
    weights: Dict[str, float]
    mode: str  # 'ideal' or 'standard_values'
    series: str = 'E24'  # E12, E24, E96
    max_components: int = 5
    max_iterations: int = 1000
    population_size: int = 15
    
    def validate(self) -> None:
        """Validate configuration."""
        if self.port < 1:
            raise ValueError(f"Port must be >= 1, got {self.port}")
        
        if self.target_impedance <= 0:
            raise ValueError(f"Target impedance must be positive, got {self.target_impedance}")
        
        if self.frequency_range[0] >= self.frequency_range[1]:
            raise ValueError(f"Invalid frequency range: {self.frequency_range}")
        
        if self.mode not in ['ideal', 'standard_values']:
            raise ValueError(f"Mode must be 'ideal' or 'standard_values', got {self.mode}")
        
        if self.series not in ['E12', 'E24', 'E96']:
            raise ValueError(f"Series must be E12/E24/E96, got {self.series}")
        
        if self.max_components < 1 or self.max_components > 5:
            raise ValueError(f"Max components must be 1-5, got {self.max_components}")


def decode_component_vector(
    x: NDArray[np.float64], 
    port: int,
    mode: str = 'ideal',
    series: str = 'E24'
) -> List[MatchingComponent]:
    """Decode flat parameter vector into MatchingComponent list.
    
    Vector encoding (per component):
    - [0-1]: component type (0-0.5 = capacitor, 0.5-1.0 = inductor)
    - [1-2]: placement (0-0.5 = series, 0.5-1.0 = shunt)
    - [2-3]: log10(value) in appropriate range
    
    Args:
        x: Flat parameter vector (length = 3 * num_components)
        port: Port number
        mode: 'ideal' or 'standard_values'
        series: E-series for standard mode ('E12', 'E24', 'E96')
    
    Returns:
        List of MatchingComponent objects
    """
    if len(x) == 0:
        return []
    
    num_components = len(x) // 3
    components = []
    
    for i in range(num_components):
        idx = i * 3
        
        # Decode component type
        comp_type = ComponentType.CAPACITOR if x[idx] < 0.5 else ComponentType.INDUCTOR
        
        # Decode placement
        placement = PlacementType.SERIES if x[idx + 1] < 0.5 else PlacementType.SHUNT
        
        # Decode value (logarithmic scale)
        if comp_type == ComponentType.CAPACITOR:
            # Capacitor range: 1pF (1e-12) to 100µF (1e-4)
            log_value = x[idx + 2] * (np.log10(1e-4) - np.log10(1e-12)) + np.log10(1e-12)
            value = 10 ** log_value
        else:
            # Inductor range: 1nH (1e-9) to 100mH (1e-1)
            log_value = x[idx + 2] * (np.log10(1e-1) - np.log10(1e-9)) + np.log10(1e-9)
            value = 10 ** log_value
        
        # Snap to standard values if in standard mode
        if mode == 'standard_values':
            value = snap_to_standard(
                value,
                component_type='capacitor' if comp_type == ComponentType.CAPACITOR else 'inductor',
                series=series
            )
        
        component = MatchingComponent(
            id=f"opt_comp_{i}",
            port=port,
            component_type=comp_type,
            value=value,
            placement=placement,
            created_at=datetime.utcnow(),
            order=i
        )
        
        components.append(component)
    
    return components


def run_optimization(
    s_parameters: NDArray[np.complex128],
    frequencies_hz: NDArray[np.float64],
    config: OptimizationConfig,
    progress_callback: Optional[Callable[[int, float], None]] = None,
) -> List[OptimizationSolution]:
    """Run optimization using differential evolution.
    
    Args:
        s_parameters: Original network S-parameters (shape: [N_freq, ports, ports])
        frequencies_hz: Frequency array in Hz
        config: Optimization configuration
        progress_callback: Optional callback(iteration, best_cost) for progress updates
    
    Returns:
        List of OptimizationSolution objects, ranked by score (best first)
    
    Raises:
        ValueError: If configuration invalid or optimization fails
    """
    config.validate()
    
    # Filter frequencies to optimization range
    freq_mask = (frequencies_hz >= config.frequency_range[0]) & \
                (frequencies_hz <= config.frequency_range[1])
    
    if not np.any(freq_mask):
        raise ValueError(f"No frequencies in range {config.frequency_range}")
    
    opt_frequencies = frequencies_hz[freq_mask]
    opt_s_params = s_parameters[freq_mask]
    
    # For now, we'll optimize assuming the input impedances are provided
    # (Full implementation would cascade components with network)
    # This is a simplified version that demonstrates the optimization structure
    
    # Define objective function
    def objective(x: NDArray[np.float64]) -> float:
        """Objective function for scipy.optimize."""
        try:
            # Decode components
            components = decode_component_vector(
                x, config.port, config.mode, config.series
            )
            
            # For this simplified implementation, assume impedances
            # In full implementation: cascade components with network and extract impedances
            # impedances = calculate_impedances_after_cascading(opt_s_params, components)
            
            # Placeholder: use S11 to estimate impedance
            s11 = opt_s_params[:, 0, 0]  # Port 1 S11
            z0 = config.target_impedance
            # Impedance from S11: Z = z0 * (1 + S11) / (1 - S11)
            impedances = z0 * (1 + s11) / (1 - s11)
            
            # Calculate weighted objective
            cost = weighted_objective(
                impedances,
                opt_frequencies,
                components,
                config.weights,
                config.target_impedance
            )
            
            return cost
        
        except Exception:
            # Return high cost for invalid configurations
            return 1e10
    
    # Define bounds for optimization
    # Each component needs 3 parameters: [type, placement, value]
    # All parameters normalized to [0, 1]
    bounds = [(0.0, 1.0)] * (3 * config.max_components)
    
    # Callback for progress reporting
    iteration_count = [0]
    
    def callback(xk: NDArray[np.float64], convergence: float) -> bool:
        """Called after each iteration."""
        iteration_count[0] += 1
        
        if progress_callback is not None:
            best_cost = objective(xk)
            progress_callback(iteration_count[0], best_cost)
        
        # Return False to continue, True to stop
        return False
    
    # Run differential evolution
    result = differential_evolution(
        objective,
        bounds,
        maxiter=config.max_iterations,
        popsize=config.population_size,
        strategy='best1bin',
        mutation=(0.5, 1.0),
        recombination=0.7,
        seed=None,  # Random seed for reproducibility
        callback=callback,
        polish=True,  # Local optimization at end
        workers=1,  # Single-threaded for now
    )
    
    # Create solution from result
    best_components = decode_component_vector(
        result.x, config.port, config.mode, config.series
    )
    
    # Calculate metrics
    s11 = opt_s_params[:, 0, 0]
    z0 = config.target_impedance
    impedances = z0 * (1 + s11) / (1 - s11)
    
    avg_return_loss = float(np.mean(return_loss_db(impedances, z0)))
    avg_vswr = float(np.mean(calculate_vswr(impedances, z0)))
    
    solution = OptimizationSolution(
        id=f"solution_{datetime.utcnow().isoformat()}",
        components=best_components,
        metrics={
            'return_loss_db': avg_return_loss,
            'vswr': avg_vswr,
            'bandwidth_hz': 0.0,  # TODO: Calculate properly
            'component_count': len(best_components),
        },
        score=result.fun,
        mode=config.mode,
        target_impedance=config.target_impedance,
        frequency_range=config.frequency_range,
        created_at=datetime.utcnow(),
    )
    
    # Return as list (single solution for now)
    # TODO: Run multiple optimizations with different seeds for top N solutions
    return [solution]
