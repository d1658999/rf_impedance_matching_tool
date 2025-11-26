"""SNP Tool - RF Impedance Matching Optimization.

A tool for RF engineers to load vendor S-parameter design kits and automatically
optimize impedance matching networks using grid search.
"""

__version__ = "0.1.0"

from .models import (
    SNPFile,
    ComponentModel,
    ComponentType,
    MatchingNetwork,
    Topology,
    OptimizationResult,
    ComponentLibrary,
)
from .parsers import parse, parse_folder
from .optimizer import GridSearchOptimizer, GridSearchConfig

__all__ = [
    "__version__",
    "SNPFile",
    "ComponentModel",
    "ComponentType",
    "MatchingNetwork",
    "Topology",
    "OptimizationResult",
    "ComponentLibrary",
    "parse",
    "parse_folder",
    "GridSearchOptimizer",
    "GridSearchConfig",
]
