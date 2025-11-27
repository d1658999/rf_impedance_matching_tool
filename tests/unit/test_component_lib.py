"""
Tests for E-series component library (Task 2.1.1).

Tests E12, E24, E96 series generation and snap-to-standard functionality.
"""

import pytest
import numpy as np
from snp_tool.core.component_lib import (
    ESeries,
    generate_e_series,
    get_standard_values,
    snap_to_standard,
    validate_e_series_properties,
    E12_VALUES,
    E24_VALUES,
    E96_VALUES,
)


class TestESeriesGeneration:
    """Test E-series value generation."""
    
    def test_e12_series_correct_count(self):
        """E12 should have 12 values per decade."""
        assert len(E12_VALUES) == 12
    
    def test_e24_series_correct_count(self):
        """E24 should have 24 values per decade."""
        assert len(E24_VALUES) == 24
    
    def test_e96_series_correct_count(self):
        """E96 should have 96 values per decade."""
        assert len(E96_VALUES) == 96
    
    def test_e12_validation(self):
        """E12 series should pass validation."""
        assert validate_e_series_properties(ESeries.E12)
    
    def test_e24_validation(self):
        """E24 series should pass validation."""
        assert validate_e_series_properties(ESeries.E24)
    
    def test_e96_validation(self):
        """E96 series should pass validation."""
        assert validate_e_series_properties(ESeries.E96)


class TestGenerateESeries:
    """Test generate_e_series function."""
    
    def test_generate_e12_single_decade(self):
        """Generate E12 values in single decade (1pF to 10pF inclusive)."""
        values = generate_e_series(ESeries.E12, 1e-12, 10e-12, 'F')
        
        # Should have 12 or 13 values (depending on boundary inclusion)
        assert len(values) in [12, 13]
        
        # First should be 1pF
        assert np.isclose(values[0], 1e-12)
        
        # Last should be 8.2pF or 10pF
        assert np.isclose(values[-1], 8.2e-12) or np.isclose(values[-1], 10e-12)
    
    def test_generate_e24_multi_decade(self):
        """Generate E24 values across multiple decades."""
        values = generate_e_series(ESeries.E24, 1e-12, 100e-12, 'F')
        
        # Should have approximately 24 * 2 = 48 values (boundary effects may add 1)
        assert 48 <= len(values) <= 50
        
        # Values should be sorted
        assert values == sorted(values)
    
    def test_generate_values_monotonic(self):
        """Generated values should be monotonically increasing."""
        values = generate_e_series(ESeries.E96, 1e-9, 1e-6, 'H')
        
        for i in range(len(values) - 1):
            assert values[i] < values[i+1]
    
    def test_generate_respects_min_max(self):
        """Generated values should respect min and max bounds."""
        min_val = 10e-12
        max_val = 47e-12
        values = generate_e_series(ESeries.E24, min_val, max_val, 'F')
        
        assert all(min_val <= v <= max_val for v in values)


class TestGetStandardValues:
    """Test get_standard_values function."""
    
    def test_get_capacitor_defaults(self):
        """Get standard capacitor values with defaults (1pF to 100µF)."""
        values = get_standard_values(ESeries.E12, 'capacitor')
        
        # Should have many values across wide range
        assert len(values) > 50
        
        # Min should be ~1pF
        assert values[0] >= 1e-12
        assert values[0] < 10e-12
        
        # Max should be ~100µF
        assert values[-1] <= 100e-6
        assert values[-1] > 10e-6
    
    def test_get_inductor_defaults(self):
        """Get standard inductor values with defaults (1nH to 100mH)."""
        values = get_standard_values(ESeries.E24, 'inductor')
        
        # Should have many values
        assert len(values) > 50
        
        # Min should be ~1nH
        assert values[0] >= 1e-9
        assert values[0] < 10e-9
    
    def test_get_with_custom_range(self):
        """Get values with custom decade range."""
        values = get_standard_values(
            ESeries.E24,
            'capacitor',
            decade_range=('pF', 'nF')
        )
        
        # Range: 1pF to 1nF = 1e-12 to 1e-9
        assert values[0] >= 1e-12
        assert values[-1] <= 1e-9
    
    def test_e96_has_more_values_than_e12(self):
        """E96 should have more values than E12 for same range."""
        e12 = get_standard_values(ESeries.E12, 'capacitor', ('pF', 'nF'))
        e96 = get_standard_values(ESeries.E96, 'capacitor', ('pF', 'nF'))
        
        assert len(e96) > len(e12)


class TestSnapToStandard:
    """Test snap_to_standard function."""
    
    def test_snap_exact_match(self):
        """Snapping exact E24 value should return same value."""
        # 12pF is in E24
        exact_value = 12e-12
        snapped = snap_to_standard(exact_value, ESeries.E24, 'capacitor')
        
        assert np.isclose(snapped, exact_value, rtol=0.01)
    
    def test_snap_12_7_pf_to_12_pf(self):
        """12.7pF should snap to 12pF (nearest E24)."""
        value = 12.7e-12
        snapped = snap_to_standard(value, ESeries.E24, 'capacitor')
        
        # 12pF is nearest E24 value
        assert np.isclose(snapped, 12e-12, rtol=0.01)
    
    def test_snap_to_e12_gives_fewer_options(self):
        """Snapping to E12 should give coarser values than E24."""
        # Test value between E12 values but on E24
        value = 13e-12  # 13pF is in E24 but not E12
        
        e12_snap = snap_to_standard(value, ESeries.E12, 'capacitor')
        e24_snap = snap_to_standard(value, ESeries.E24, 'capacitor')
        
        # E24 should snap to exact match or very close
        assert np.isclose(e24_snap, 13e-12, rtol=0.05)
        # E12 should snap to nearest (12 or 15), with tolerance for floating point
        assert np.isclose(e12_snap, 12e-12, rtol=0.01) or np.isclose(e12_snap, 15e-12, rtol=0.01)
    
    def test_snap_inductor_works(self):
        """Snap to standard should work for inductors."""
        value = 2.7e-9  # 2.7nH
        snapped = snap_to_standard(value, ESeries.E12, 'inductor')
        
        # Should snap to standard value
        assert snapped in get_standard_values(ESeries.E12, 'inductor')
    
    def test_snap_very_small_value(self):
        """Snapping very small value should work."""
        value = 1.5e-12  # 1.5pF
        snapped = snap_to_standard(value, ESeries.E24, 'capacitor')
        
        # Should snap to 1.5pF (in E24) or nearest
        assert np.isclose(snapped, 1.5e-12, rtol=0.1)
    
    def test_snap_very_large_value(self):
        """Snapping very large value should work."""
        value = 47e-6  # 47µF
        snapped = snap_to_standard(value, ESeries.E24, 'capacitor')
        
        # Should snap to 47µF or nearest E24 value
        standard_values = get_standard_values(ESeries.E24, 'capacitor')
        assert snapped in standard_values


class TestDecadeRange:
    """Test decade range functionality."""
    
    def test_pf_to_uf_range(self):
        """Test pF to µF decade range."""
        values = get_standard_values(
            ESeries.E12,
            'capacitor',
            decade_range=('pF', 'µF')
        )
        
        # Should span from picofarads to microfarads
        assert values[0] < 10e-12   # Less than 10pF
        assert values[-1] >= 1e-6   # At least 1µF (boundary inclusive)
    
    def test_nh_to_mh_range(self):
        """Test nH to mH decade range."""
        values = get_standard_values(
            ESeries.E24,
            'inductor',
            decade_range=('nH', 'mH')
        )
        
        # Should span from nanohenries to millihenries
        assert values[0] < 10e-9   # Less than 10nH
        assert values[-1] >= 1e-3  # At least 1mH (boundary inclusive)
    
    def test_configurable_ranges(self):
        """Different ranges should give different value sets."""
        narrow = get_standard_values(
            ESeries.E24,
            'capacitor',
            decade_range=('pF', 'nF')
        )
        
        wide = get_standard_values(
            ESeries.E24,
            'capacitor',
            decade_range=('pF', 'µF')
        )
        
        # Wide range should have more values
        assert len(wide) > len(narrow)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_series_raises(self):
        """Invalid E-series should raise ValueError."""
        with pytest.raises(ValueError):
            generate_e_series("E48", 1e-12, 1e-9, 'F')  # E48 doesn't exist
    
    def test_invalid_component_type_raises(self):
        """Invalid component type should raise ValueError."""
        with pytest.raises(ValueError):
            get_standard_values(ESeries.E24, 'resistor')
    
    def test_min_greater_than_max_returns_empty(self):
        """Min > max should return empty list."""
        values = generate_e_series(ESeries.E12, 1e-9, 1e-12, 'F')
        assert len(values) == 0
    
    def test_very_narrow_range(self):
        """Very narrow range should work."""
        values = generate_e_series(ESeries.E96, 10e-12, 12e-12, 'F')
        
        # Should find a few E96 values in this range
        assert len(values) >= 2
        assert all(10e-12 <= v <= 12e-12 for v in values)


class TestRealWorldScenarios:
    """Test realistic optimization scenarios."""
    
    def test_optimize_antenna_matching(self):
        """Typical antenna matching: need ~10-50pF capacitors."""
        # Optimizer finds optimal value: 37.2pF
        optimal_value = 37.2e-12
        
        # Snap to E24 standard
        standard_value = snap_to_standard(optimal_value, ESeries.E24, 'capacitor')
        
        # Should snap to 36pF or 39pF (both in E24)
        assert standard_value in [36e-12, 39e-12]
    
    def test_lna_matching_inductors(self):
        """LNA matching might need small inductors (~1-10nH)."""
        optimal = 3.7e-9  # 3.7nH
        
        e24_value = snap_to_standard(optimal, ESeries.E24, 'inductor')
        e96_value = snap_to_standard(optimal, ESeries.E96, 'inductor')
        
        # E96 should give closer match
        error_e24 = abs(e24_value - optimal) / optimal
        error_e96 = abs(e96_value - optimal) / optimal
        
        assert error_e96 <= error_e24
    
    def test_all_e24_capacitor_values_accessible(self):
        """All E24 capacitor values should be accessible."""
        values = get_standard_values(ESeries.E24, 'capacitor')
        
        # Check a few expected E24 values exist
        expected_values = [1e-12, 1.2e-12, 2.2e-12, 10e-12, 100e-12, 1e-9, 10e-9]
        
        for expected in expected_values:
            # Find closest value
            closest = min(values, key=lambda v: abs(v - expected))
            # Should be very close (within 1%)
            assert abs(closest - expected) / expected < 0.01
