"""
Port Configuration entity.

Represents the state of a single port including reference impedance,
added components, and current impedance characteristics.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from snp_tool.models.component import MatchingComponent


@dataclass
class PortConfiguration:
    """Port Configuration entity from data-model.md."""
    
    port_number: int
    reference_impedance: float
    components: List[MatchingComponent] = field(default_factory=list)
    
    # Current state (recomputed when components change)
    current_impedance: Optional[complex] = None
    vswr: Optional[float] = None
    return_loss_db: Optional[float] = None
    
    def __post_init__(self):
        """Validate port after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate port configuration per data-model.md validation rules."""
        # Rule: port_number >= 1
        if self.port_number < 1:
            raise ValueError(f"Port number must be >= 1, got {self.port_number}")
        
        # Rule: reference_impedance > 0
        if self.reference_impedance <= 0:
            raise ValueError(f"Reference impedance must be positive, got {self.reference_impedance}")
        
        # Rule: max 5 components per port (FR-003)
        if len(self.components) > 5:
            raise ValueError(
                f"Maximum 5 components per port (FR-003), got {len(self.components)}"
            )
        
        # Rule: components must have unique order values
        orders = [c.order for c in self.components]
        if len(orders) != len(set(orders)):
            raise ValueError("Components must have unique order values within same port")
    
    def add_component(self, component: MatchingComponent) -> None:
        """Add component, validating max 5 constraint (FR-003)."""
        if len(self.components) >= 5:
            raise ValueError(
                f"Maximum 5 components per port (FR-003). Cannot add component to port {self.port_number}."
            )
        
        # Validate component belongs to this port
        if component.port != self.port_number:
            raise ValueError(
                f"Component port {component.port} does not match PortConfiguration port {self.port_number}"
            )
        
        self.components.append(component)
    
    def remove_component(self, component_id: str) -> None:
        """Remove component by ID."""
        self.components = [c for c in self.components if c.id != component_id]
