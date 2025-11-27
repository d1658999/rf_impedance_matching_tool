"""
S-Parameter Network entity.

Represents an RF network characterized by frequency-dependent scattering parameters.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class SParameterNetwork:
    """S-Parameter Network entity from data-model.md."""
    
    filepath: Path
    port_count: int
    frequencies: np.ndarray
    s_parameters: np.ndarray
    impedance_normalization: float
    frequency_unit: str
    format_type: str
    loaded_at: datetime
    checksum: str
    
    # Computed properties (cached, lazy-loaded)
    _impedance_matrix: Optional[np.ndarray] = field(default=None, init=False, repr=False)
    _admittance_matrix: Optional[np.ndarray] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Validate network after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate network integrity per data-model.md validation rules."""
        # Rule: port_count must match S-parameter matrix dimensions
        if self.s_parameters.shape[1] != self.port_count or self.s_parameters.shape[2] != self.port_count:
            raise ValueError(
                f"port_count {self.port_count} does not match S-parameter dimensions "
                f"{self.s_parameters.shape[1]}x{self.s_parameters.shape[2]}"
            )
        
        # Rule: frequencies must be monotonically increasing
        if len(self.frequencies) > 1:
            if not np.all(self.frequencies[1:] > self.frequencies[:-1]):
                raise ValueError("Frequencies must be monotonically increasing")
        
        # Rule: frequencies and S-parameters must have matching length
        if self.frequencies.shape[0] != self.s_parameters.shape[0]:
            raise ValueError(
                f"Frequency count {self.frequencies.shape[0]} does not match "
                f"S-parameter frequency dimension {self.s_parameters.shape[0]}"
            )
        
        # Rule: impedance_normalization must be positive
        if self.impedance_normalization <= 0:
            raise ValueError(f"Impedance normalization must be positive, got {self.impedance_normalization}")
        
        # Rule: frequency_unit must be valid
        if self.frequency_unit not in ['Hz', 'kHz', 'MHz', 'GHz']:
            raise ValueError(f"Invalid frequency_unit '{self.frequency_unit}', must be Hz/kHz/MHz/GHz")
        
        # Rule: format_type must be valid
        if self.format_type not in ['RI', 'MA', 'DB']:
            raise ValueError(f"Invalid format_type '{self.format_type}', must be RI/MA/DB")
    
    def get_impedance_at_frequency(self, freq_hz: float, port: int) -> complex:
        """Calculate input impedance at specific frequency and port."""
        # Find closest frequency index
        idx = np.argmin(np.abs(self.frequencies - freq_hz))
        
        # Get S11 (or Snn for port n)
        s_nn = self.s_parameters[idx, port-1, port-1]
        
        # Convert S11 to impedance: Z = Z0 * (1 + S11) / (1 - S11)
        z = self.impedance_normalization * (1 + s_nn) / (1 - s_nn)
        return z
