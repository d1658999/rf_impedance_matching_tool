"""
Optimization Solution entity.

Represents a complete impedance matching solution with component values,
port assignments, and performance metrics.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

from snp_tool.models.component import MatchingComponent


@dataclass
class OptimizationSolution:
    """Optimization Solution entity from data-model.md."""
    
    id: str
    components: List[MatchingComponent]
    metrics: Dict[str, float]
    score: float  # Weighted objective score (lower is better)
    mode: str  # 'ideal' or 'standard_values'
    target_impedance: float
    frequency_range: Tuple[float, float]  # (min_hz, max_hz)
    created_at: datetime
    
    @property
    def return_loss_db(self) -> float:
        """Return loss in dB (more negative is better)."""
        return self.metrics.get('return_loss_db', 0.0)
    
    @property
    def vswr(self) -> float:
        """Voltage Standing Wave Ratio (closer to 1.0 is better)."""
        return self.metrics.get('vswr', float('inf'))
    
    @property
    def bandwidth_hz(self) -> float:
        """Bandwidth in Hz where performance criteria are met."""
        return self.metrics.get('bandwidth_hz', 0.0)
