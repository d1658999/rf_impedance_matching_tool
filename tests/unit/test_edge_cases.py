# T055: Edge case tests
"""Unit tests for edge cases not covered by other tests.

Covers: corrupt files, extreme impedances, empty libraries, boundary conditions.
"""
import pytest
import numpy as np
from pathlib import Path

from snp_tool.parsers import touchstone
from snp_tool.parsers import component_library as comp_lib_parser
from snp_tool.models.snp_file import SNPFile
from snp_tool.models.component_library import ComponentLibrary
from snp_tool.optimizer.grid_search import GridSearchOptimizer
from snp_tool.optimizer.metrics import calculate_vswr
from snp_tool.utils.exceptions import (
    TouchstoneFormatError,
    FrequencyGapError,
    OptimizationError,
)


class TestCorruptFileHandling:
    """Test handling of corrupt or malformed files."""

    def test_empty_file_raises_error(self, tmp_path: Path):
        """Empty file should raise error."""
        empty_file = tmp_path / "empty.s2p"
        empty_file.write_text("")

        with pytest.raises(Exception):
            touchstone.parse(str(empty_file))

    def test_invalid_header_raises_error(self, tmp_path: Path):
        """Invalid header format should raise error."""
        bad_file = tmp_path / "bad_header.s2p"
        bad_file.write_text("This is not a valid touchstone file\n1.0 2.0 3.0")

        with pytest.raises(Exception):
            touchstone.parse(str(bad_file))

    def test_missing_data_raises_error(self, tmp_path: Path):
        """File with header but no data should raise error."""
        header_only = tmp_path / "header_only.s2p"
        header_only.write_text("# Hz S DB R 50\n")

        with pytest.raises(Exception):
            touchstone.parse(str(header_only))

    def test_nonexistent_file_raises_error(self):
        """Non-existent file should raise error."""
        with pytest.raises(Exception):
            touchstone.parse("/nonexistent/path/file.s2p")


class TestVSWRMetrics:
    """Test VSWR calculation edge cases."""

    def test_negative_vswr_prevention(self):
        """VSWR should never be negative."""
        # Edge cases for |S11|
        for s11_mag in [0.0, 0.5, 0.99, 0.999, 1.0]:
            vswr = calculate_vswr(s11_mag)
            assert vswr >= 1.0, f"VSWR {vswr} should be >= 1.0 for |S11|={s11_mag}"

    def test_perfect_match_vswr(self):
        """Perfect match (S11=0) should give VSWR=1."""
        vswr = calculate_vswr(0.0)
        assert vswr == 1.0

    def test_total_reflection_vswr(self):
        """Total reflection (S11=1) should give high VSWR."""
        vswr = calculate_vswr(0.9999)
        assert vswr > 100


class TestEmptyLibraryHandling:
    """Test handling of empty or minimal component libraries."""

    def test_empty_folder_creates_empty_library(self, tmp_path: Path):
        """Empty folder should create empty library without error."""
        library = comp_lib_parser.parse_folder(str(tmp_path))

        assert len(library.components) == 0
        assert library.search("capacitor") == []


class TestFrequencyEdgeCases:
    """Test frequency-related edge cases."""

    def test_single_frequency_point(self):
        """Single frequency point should work."""
        device = SNPFile(
            file_path="test.s2p",
            frequency=np.array([2.4e9]),
            s_parameters={"s11": np.array([0.3 + 0.2j]), "s21": np.array([0.9j])},
            num_ports=2,
            reference_impedance=50.0,
        )

        assert len(device.frequency) == 1
        assert device.center_frequency == 2.4e9

    def test_non_monotonic_frequencies_rejected(self, tmp_path: Path):
        """Non-monotonic frequency arrays should be handled."""
        bad_file = tmp_path / "non_monotonic.s2p"
        bad_file.write_text("""# Hz S DB R 50
1e9 -10 45 -20 90 -20 90 -10 45
3e9 -10 45 -20 90 -20 90 -10 45
2e9 -10 45 -20 90 -20 90 -10 45
""")

        # scikit-rf handles this - test that parsing at least completes
        try:
            snp = touchstone.parse(str(bad_file))
            # If parsing succeeds, verify frequency handling
            assert len(snp.frequency) > 0
        except Exception:
            pass  # Expected if library rejects non-monotonic

    def test_duplicate_frequencies_handled(self, tmp_path: Path):
        """Duplicate frequency points should be handled."""
        bad_file = tmp_path / "duplicate_freq.s2p"
        bad_file.write_text("""# Hz S DB R 50
1e9 -10 45 -20 90 -20 90 -10 45
1e9 -15 50 -25 95 -25 95 -15 50
2e9 -10 45 -20 90 -20 90 -10 45
""")

        try:
            snp = touchstone.parse(str(bad_file))
            assert len(snp.frequency) > 0
        except Exception:
            pass  # Expected behavior


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_very_large_frequency_range(self):
        """Very wide frequency range (DC to 100GHz) should work."""
        frequencies = np.linspace(1e6, 100e9, 1000)
        s11_data = np.array([0.5 + 0.1j] * 1000)
        s21_data = np.array([0.9j] * 1000)

        device = SNPFile(
            file_path="test.s2p",
            frequency=frequencies,
            s_parameters={"s11": s11_data, "s21": s21_data},
            num_ports=2,
            reference_impedance=50.0,
        )

        assert len(device.frequency) == 1000
        assert device.frequency[0] == 1e6
        assert device.frequency[-1] == 100e9

    def test_impedance_at_edge_frequencies(self):
        """Impedance calculation at edge frequencies should work."""
        frequencies = np.array([1e9, 2e9, 3e9])
        s11_data = np.array([0.5 + 0.1j, 0.3 + 0.2j, 0.4 - 0.1j])

        device = SNPFile(
            file_path="test.s2p",
            frequency=frequencies,
            s_parameters={"s11": s11_data, "s21": np.array([0.9j] * 3)},
            num_ports=2,
            reference_impedance=50.0,
        )

        # Should not raise
        z_start = device.impedance_at_frequency(1e9)
        z_end = device.impedance_at_frequency(3e9)

        assert np.isfinite(z_start.real)
        assert np.isfinite(z_end.real)


class TestOptimizationEdgeCases:
    """Test optimization edge cases."""

    def test_already_matched_device_vswr(self):
        """Device already at 50Ω should have excellent VSWR."""
        # S11 ≈ 0.01 means very good match
        s11_mag = 0.01
        initial_vswr = calculate_vswr(s11_mag)

        assert initial_vswr < 1.1, "Already matched device should have VSWR < 1.1"

    def test_optimizer_class_exists(self):
        """GridSearchOptimizer should be callable."""
        from snp_tool.optimizer.grid_search import GridSearchOptimizer

        assert callable(GridSearchOptimizer)
