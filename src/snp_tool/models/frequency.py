"""
Frequency Point entity.

Represents a single frequency value with associated S-parameters
and impedance values for all ports.
"""

from dataclasses import dataclass
from typing import Dict

import numpy as np


@dataclass
class FrequencyPoint:
    """Frequency Point entity from data-model.md."""
    
    frequency_hz: float
    s_parameters: np.ndarray  # Shape: [port_count, port_count]
    impedances: Dict[int, complex]  # {port_number: impedance}
    vswr_values: Dict[int, float]  # {port_number: VSWR}
    return_loss_db: Dict[int, float]  # {port_number: return_loss}
    
    def get_impedance(self, port: int) -> complex:
        """Get impedance for specific port."""
        return self.impedances.get(port, 0j)
    
    def get_reflection_coefficient(self, port: int, z0: float = 50.0) -> complex:
        """Calculate reflection coefficient Gamma.
        
        Gamma = (Z - Z0) / (Z + Z0)
        """
        z = self.get_impedance(port)
        gamma = (z - z0) / (z + z0)
        return gamma
