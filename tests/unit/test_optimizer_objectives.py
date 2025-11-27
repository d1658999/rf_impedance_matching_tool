"""Tests for multi-metric weighted objective functions.

Per tasks.md Task 2.2.1:
- Test objective function single metric (return loss only)
- Test objective function weighted (multiple metrics)
- Test objective function component count penalty
- Test objective function bandwidth calculation
- Test normalization to comparable scales
"""

import pytest
import numpy as np
from datetime import datetime
from snp_tool.optimizer.objectives import (
    calculate_bandwidth,
    normalize_metric,
    weighted_objective,
)
from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType


class TestCalculateBandwidth:
    """Test bandwidth calculation from impedance trajectory."""
    
    def test_bandwidth_all_points_meet_threshold(self):
        """All frequency points meet VSWR threshold."""
        # Create impedances close to 50Ω (good match)
        frequencies = np.linspace(1e9, 2e9, 11)  # 1-2 GHz
        impedances = np.full(11, 50.0 + 1.0j)  # Near-perfect match
        
        bandwidth = calculate_bandwidth(
            impedances, frequencies, target_impedance=50.0, vswr_threshold=2.0
        )
        
        # All points should be in band
        expected_bw = 2e9 - 1e9  # 1 GHz
        assert bandwidth == pytest.approx(expected_bw, rel=0.01)
    
    def test_bandwidth_no_points_meet_threshold(self):
        """No frequency points meet VSWR threshold."""
        frequencies = np.linspace(1e9, 2e9, 11)
        # Very mismatched impedance (VSWR >> 2.0)
        impedances = np.full(11, 5.0 + 0.0j)  # Very poor match
        
        bandwidth = calculate_bandwidth(
            impedances, frequencies, target_impedance=50.0, vswr_threshold=2.0
        )
        
        assert bandwidth == 0.0
    
    def test_bandwidth_partial_band(self):
        """Only some frequency points meet threshold."""
        frequencies = np.array([1.0e9, 1.5e9, 2.0e9, 2.5e9, 3.0e9])
        # Good match in middle, poor at edges
        impedances = np.array([
            10.0 + 5.0j,   # Poor
            45.0 + 5.0j,   # Good
            50.0 + 2.0j,   # Excellent
            48.0 + 6.0j,   # Good
            20.0 + 10.0j,  # Poor
        ])
        
        bandwidth = calculate_bandwidth(
            impedances, frequencies, target_impedance=50.0, vswr_threshold=2.0
        )
        
        # Should cover middle band (approximately 1.5-2.5 GHz = 1 GHz)
        assert bandwidth > 0.5e9  # At least 500 MHz
        assert bandwidth < 2.0e9  # Less than full span


class TestNormalizeMetric:
    """Test metric normalization to 0-1 scale."""
    
    def test_normalize_at_minimum(self):
        """Value at minimum should normalize to 0.0."""
        normalized = normalize_metric(0.0, min_val=0.0, max_val=10.0)
        assert normalized == 0.0
    
    def test_normalize_at_maximum(self):
        """Value at maximum should normalize to 1.0."""
        normalized = normalize_metric(10.0, min_val=0.0, max_val=10.0)
        assert normalized == 1.0
    
    def test_normalize_at_midpoint(self):
        """Value at midpoint should normalize to 0.5."""
        normalized = normalize_metric(5.0, min_val=0.0, max_val=10.0)
        assert normalized == pytest.approx(0.5, abs=0.01)
    
    def test_normalize_clips_below_minimum(self):
        """Values below minimum clip to 0.0."""
        normalized = normalize_metric(-5.0, min_val=0.0, max_val=10.0)
        assert normalized == 0.0
    
    def test_normalize_clips_above_maximum(self):
        """Values above maximum clip to 1.0."""
        normalized = normalize_metric(15.0, min_val=0.0, max_val=10.0)
        assert normalized == 1.0
    
    def test_normalize_invalid_range_returns_zero(self):
        """Invalid range (min >= max) returns 0.0."""
        normalized = normalize_metric(5.0, min_val=10.0, max_val=10.0)
        assert normalized == 0.0


class TestWeightedObjective:
    """Test weighted multi-metric objective function."""
    
    def test_objective_single_metric_return_loss(self):
        """Test with return loss only (other weights zero)."""
        frequencies = np.linspace(2.0e9, 3.0e9, 11)
        
        # Excellent match (high return loss)
        good_impedances = np.full(11, 50.0 + 0.5j)
        
        # Poor match (low return loss)
        poor_impedances = np.full(11, 20.0 + 10.0j)
        
        components = []  # No components
        weights = {'return_loss': 1.0, 'vswr': 0.0, 'bandwidth': 0.0, 'component_count': 0.0}
        
        good_cost = weighted_objective(good_impedances, frequencies, components, weights, 50.0)
        poor_cost = weighted_objective(poor_impedances, frequencies, components, weights, 50.0)
        
        # Good match should have lower cost
        assert good_cost < poor_cost
    
    def test_objective_weighted_multiple_metrics(self):
        """Test with multiple metrics weighted."""
        frequencies = np.linspace(2.0e9, 3.0e9, 11)
        impedances = np.full(11, 50.0 + 2.0j)  # Decent match
        
        # 2 components
        components = [
            MatchingComponent(
                id="comp1",
                port=1,
                component_type=ComponentType.CAPACITOR,
                value=10e-12,
                placement=PlacementType.SERIES,
                created_at=datetime.utcnow(),
                order=0,
            ),
            MatchingComponent(
                id="comp2",
                port=1,
                component_type=ComponentType.INDUCTOR,
                value=5e-9,
                placement=PlacementType.SHUNT,
                created_at=datetime.utcnow(),
                order=1,
            ),
        ]
        
        weights = {
            'return_loss': 0.5,
            'vswr': 0.2,
            'bandwidth': 0.2,
            'component_count': 0.1,
        }
        
        cost = weighted_objective(impedances, frequencies, components, weights, 50.0)
        
        # Cost should be a reasonable value between 0 and 1
        assert 0.0 <= cost <= 1.0
    
    def test_objective_component_count_penalty(self):
        """More components should increase cost."""
        frequencies = np.linspace(2.0e9, 3.0e9, 11)
        impedances = np.full(11, 50.0 + 1.0j)  # Same impedance for both cases
        
        # 1 component
        components_1 = [
            MatchingComponent(
                id="comp1",
                port=1,
                component_type=ComponentType.CAPACITOR,
                value=10e-12,
                placement=PlacementType.SERIES,
                created_at=datetime.utcnow(),
                order=0,
            ),
        ]
        
        # 3 components
        components_3 = components_1 + [
            MatchingComponent(
                id="comp2",
                port=1,
                component_type=ComponentType.INDUCTOR,
                value=5e-9,
                placement=PlacementType.SHUNT,
                created_at=datetime.utcnow(),
                order=1,
            ),
            MatchingComponent(
                id="comp3",
                port=1,
                component_type=ComponentType.CAPACITOR,
                value=22e-12,
                placement=PlacementType.SERIES,
                created_at=datetime.utcnow(),
                order=2,
            ),
        ]
        
        weights = {'return_loss': 0.0, 'vswr': 0.0, 'bandwidth': 0.0, 'component_count': 1.0}
        
        cost_1 = weighted_objective(impedances, frequencies, components_1, weights, 50.0)
        cost_3 = weighted_objective(impedances, frequencies, components_3, weights, 50.0)
        
        # More components = higher cost
        assert cost_3 > cost_1
    
    def test_objective_bandwidth_calculation(self):
        """Higher bandwidth should decrease cost."""
        # Wide frequency range - good match across entire band
        freq_wide = np.linspace(1.0e9, 4.0e9, 31)
        impedances_wide = np.full(31, 50.0 + 3.0j)  # VSWR ~1.14 (meets threshold)
        
        # Narrow frequency range - poor match so narrower usable bandwidth
        freq_narrow = np.linspace(2.0e9, 2.5e9, 11)
        # Mix of good and poor impedances to reduce effective bandwidth
        impedances_narrow = np.array([
            20.0 + 10.0j,  # Poor
            45.0 + 5.0j,   # OK
            50.0 + 2.0j,   # Good
            50.0 + 1.0j,   # Good
            50.0 + 2.0j,   # Good
            50.0 + 1.0j,   # Good
            50.0 + 2.0j,   # Good
            45.0 + 5.0j,   # OK
            20.0 + 10.0j,  # Poor
            15.0 + 8.0j,   # Poor
            25.0 + 12.0j,  # Poor
        ])
        
        components = []
        weights = {'return_loss': 0.0, 'vswr': 0.0, 'bandwidth': 1.0, 'component_count': 0.0}
        
        cost_wide = weighted_objective(impedances_wide, freq_wide, components, weights, 50.0)
        cost_narrow = weighted_objective(impedances_narrow, freq_narrow, components, weights, 50.0)
        
        # Wider usable bandwidth = lower cost
        assert cost_wide < cost_narrow
    
    def test_objective_default_weights(self):
        """Test that default weights are applied if not specified."""
        frequencies = np.linspace(2.0e9, 3.0e9, 11)
        impedances = np.full(11, 50.0 + 1.0j)
        components = []
        
        # Empty weights dict should use defaults
        cost = weighted_objective(impedances, frequencies, components, {}, 50.0)
        
        # Should return a valid cost
        assert 0.0 <= cost <= 1.0
    
    def test_objective_normalized_metrics_in_range(self):
        """All normalized metrics should be in [0, 1] range."""
        frequencies = np.linspace(2.0e9, 3.0e9, 11)
        
        # Test with various impedance qualities
        for impedance_val in [50.0 + 0.1j, 30.0 + 10.0j, 70.0 + 5.0j]:
            impedances = np.full(11, impedance_val)
            components = []
            weights = {'return_loss': 0.25, 'vswr': 0.25, 'bandwidth': 0.25, 'component_count': 0.25}
            
            cost = weighted_objective(impedances, frequencies, components, weights, 50.0)
            
            # Cost should always be normalized
            assert 0.0 <= cost <= 1.0


class TestObjectiveEdgeCases:
    """Test edge cases and error handling."""
    
    def test_perfect_match_low_cost(self):
        """Perfect 50Ω match should give very low cost."""
        frequencies = np.linspace(2.0e9, 3.0e9, 11)
        # Perfect match
        impedances = np.full(11, 50.0 + 0.0j)
        components = []
        weights = {'return_loss': 1.0, 'vswr': 0.0, 'bandwidth': 0.0, 'component_count': 0.0}
        
        cost = weighted_objective(impedances, frequencies, components, weights, 50.0)
        
        # Should be very low cost (near 0.0)
        assert cost < 0.1
    
    def test_very_poor_match_high_cost(self):
        """Very poor match should give high cost."""
        frequencies = np.linspace(2.0e9, 3.0e9, 11)
        # Terrible match
        impedances = np.full(11, 5.0 + 0.0j)
        components = []
        weights = {'return_loss': 1.0, 'vswr': 0.0, 'bandwidth': 0.0, 'component_count': 0.0}
        
        cost = weighted_objective(impedances, frequencies, components, weights, 50.0)
        
        # Should be high cost (near 1.0)
        assert cost > 0.7
    
    def test_zero_components_zero_component_cost(self):
        """Zero components should give zero component count cost."""
        frequencies = np.linspace(2.0e9, 3.0e9, 11)
        impedances = np.full(11, 50.0 + 1.0j)
        components = []  # Empty
        weights = {'return_loss': 0.0, 'vswr': 0.0, 'bandwidth': 0.0, 'component_count': 1.0}
        
        cost = weighted_objective(impedances, frequencies, components, weights, 50.0)
        
        # Zero components = zero cost
        assert cost == 0.0
