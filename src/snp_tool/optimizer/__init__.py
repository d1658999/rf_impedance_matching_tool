"""SNP Tool Optimizer - Grid search impedance matching."""

from .grid_search import GridSearchOptimizer, GridSearchConfig
from .cascader import cascade_networks, cascade_with_topology, s_to_abcd, abcd_to_s, interpolate_s_params
from .bandwidth_optimizer import BandwidthOptimizer
from .metrics import (
    reflection_coefficient,
    vswr,
    return_loss_db,
    reflection_coefficient_from_s11,
    vswr_from_s11,
    return_loss_from_s11,
    impedance_from_s11,
    is_matched,
)

__all__ = [
    "GridSearchOptimizer",
    "GridSearchConfig",
    "BandwidthOptimizer",
    "cascade_networks",
    "cascade_with_topology",
    "s_to_abcd",
    "abcd_to_s",
    "interpolate_s_params",
    "reflection_coefficient",
    "vswr",
    "return_loss_db",
    "reflection_coefficient_from_s11",
    "vswr_from_s11",
    "return_loss_from_s11",
    "impedance_from_s11",
    "is_matched",
]
