"""Multi-metric weighted objective functions for impedance matching optimization.

Per research.md Section 1 and tasks.md Task 2.2.1:
- Return loss (minimize reflection coefficient)
- VSWR (minimize voltage standing wave ratio)
- Bandwidth (maximize frequency range meeting impedance target)
- Component count (minimize for simplicity/cost)
"""

from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np
from numpy.typing import NDArray

from snp_tool.optimizer.metrics import return_loss_db, vswr as calculate_vswr
from snp_tool.models.component import MatchingComponent


def calculate_bandwidth(
    impedances: NDArray[np.complex128],
    frequencies_hz: NDArray[np.float64],
    target_impedance: float = 50.0,
    vswr_threshold: float = 2.0,
) -> float:
    """Calculate bandwidth where VSWR meets threshold.
    
    Args:
        impedances: Array of complex impedances at each frequency
        frequencies_hz: Array of frequencies in Hz
        target_impedance: Target impedance (default 50Ω)
        vswr_threshold: VSWR threshold (default 2.0)
    
    Returns:
        Bandwidth in Hz where VSWR < threshold
    """
    vswr_values = calculate_vswr(impedances, target_impedance)
    
    # Find frequency points where VSWR meets threshold
    meets_threshold = vswr_values < vswr_threshold
    
    if not np.any(meets_threshold):
        return 0.0
    
    # Calculate total bandwidth (may be multiple bands)
    freq_sorted = frequencies_hz[np.argsort(frequencies_hz)]
    meets_sorted = meets_threshold[np.argsort(frequencies_hz)]
    
    # Find continuous bands
    bandwidth = 0.0
    in_band = False
    band_start = 0.0
    
    for i, meets in enumerate(meets_sorted):
        if meets and not in_band:
            band_start = freq_sorted[i]
            in_band = True
        elif not meets and in_band:
            bandwidth += freq_sorted[i - 1] - band_start
            in_band = False
    
    # Add final band if still in band at end
    if in_band:
        bandwidth += freq_sorted[-1] - band_start
    
    return bandwidth


def normalize_metric(value: float, min_val: float, max_val: float) -> float:
    """Normalize metric value to 0-1 scale.
    
    Args:
        value: Metric value
        min_val: Minimum expected value
        max_val: Maximum expected value
    
    Returns:
        Normalized value in [0, 1]
    """
    if max_val <= min_val:
        return 0.0
    
    normalized = (value - min_val) / (max_val - min_val)
    return np.clip(normalized, 0.0, 1.0)


def weighted_objective(
    impedances: NDArray[np.complex128],
    frequencies_hz: NDArray[np.float64],
    components: List[MatchingComponent],
    weights: Dict[str, float],
    target_impedance: float = 50.0,
) -> float:
    """Calculate weighted multi-metric objective function.
    
    Lower score = better solution (minimization problem)
    
    Args:
        impedances: Array of complex impedances at each frequency
        frequencies_hz: Array of frequencies in Hz
        components: List of matching components
        weights: Dict of metric weights (return_loss, vswr, bandwidth, component_count)
        target_impedance: Target impedance (default 50Ω)
    
    Returns:
        Weighted scalar cost (minimize)
    
    Example:
        >>> weights = {'return_loss': 0.7, 'vswr': 0.0, 'bandwidth': 0.2, 'component_count': 0.1}
        >>> cost = weighted_objective(impedances, freqs, components, weights, 50.0)
    """
    # Calculate individual metrics
    avg_return_loss = np.mean(return_loss_db(impedances, target_impedance))
    avg_vswr = np.mean(calculate_vswr(impedances, target_impedance))
    bandwidth_hz = calculate_bandwidth(
        impedances, frequencies_hz, target_impedance, vswr_threshold=2.0
    )
    component_count = len(components)
    
    # Normalize metrics to comparable scales
    # Return loss: higher is better, typical range 0-40 dB
    # Invert and normalize: 0 dB (poor) → 1.0 cost, 40 dB (excellent) → 0.0 cost
    normalized_return_loss = normalize_metric(
        -avg_return_loss, min_val=-40.0, max_val=0.0
    )
    
    # VSWR: lower is better, typical range 1.0-10.0
    # Normalize: VSWR=1.0 (perfect) → 0.0 cost, VSWR=10.0 (poor) → 1.0 cost
    normalized_vswr = normalize_metric(avg_vswr - 1.0, min_val=0.0, max_val=9.0)
    
    # Bandwidth: higher is better
    # Normalize based on total frequency span
    total_span = frequencies_hz[-1] - frequencies_hz[0]
    normalized_bandwidth = normalize_metric(
        -bandwidth_hz, min_val=-total_span, max_val=0.0
    )
    
    # Component count: fewer is better, max 5 per port
    # Normalize: 0 components → 0.0 cost, 5 components → 1.0 cost
    normalized_component_count = normalize_metric(
        component_count, min_val=0.0, max_val=5.0
    )
    
    # Weighted combination (default weights if not specified)
    default_weights = {
        'return_loss': 0.7,
        'vswr': 0.0,
        'bandwidth': 0.2,
        'component_count': 0.1,
    }
    
    # Merge user weights with defaults
    merged_weights = {**default_weights, **weights}
    
    # Calculate weighted cost
    cost = (
        merged_weights.get('return_loss', 0.0) * normalized_return_loss +
        merged_weights.get('vswr', 0.0) * normalized_vswr +
        merged_weights.get('bandwidth', 0.0) * normalized_bandwidth +
        merged_weights.get('component_count', 0.0) * normalized_component_count
    )
    
    return cost


def objective_function_factory(
    network_s_params: NDArray[np.complex128],
    frequencies_hz: NDArray[np.float64],
    weights: Dict[str, float],
    target_impedance: float = 50.0,
):
    """Factory to create objective function for optimization.
    
    This creates a closure that can be passed to scipy.optimize.
    
    Args:
        network_s_params: Original network S-parameters (for cascading)
        frequencies_hz: Frequency points in Hz
        weights: Metric weights dictionary
        target_impedance: Target impedance
    
    Returns:
        Objective function that takes component_values array and returns cost
    
    Example:
        >>> obj_func = objective_function_factory(s_params, freqs, weights, 50.0)
        >>> cost = obj_func([10e-12, 5e-9])  # 10pF cap, 5nH inductor
    """
    
    def objective(component_values: NDArray[np.float64]) -> float:
        """Objective function for scipy.optimize.
        
        Args:
            component_values: Flat array of component values
        
        Returns:
            Scalar cost to minimize
        """
        # Decode component_values into MatchingComponent objects
        # (This will be implemented when we have the full optimizer)
        # For now, return a placeholder
        
        # TODO: Implement component decoding and network cascading
        # components = decode_components(component_values)
        # modified_network = apply_components(network_s_params, components)
        # impedances = calculate_impedances_from_s_params(modified_network)
        
        # Placeholder for now
        return 0.0
    
    return objective
