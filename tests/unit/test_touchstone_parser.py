"""Unit tests for Touchstone parser."""

import pytest
import numpy as np
from pathlib import Path

from snp_tool.parsers.touchstone import parse, extract_impedance
from snp_tool.models import SNPFile
from snp_tool.utils.exceptions import TouchstoneFormatError


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestTouchstoneParser:
    """Tests for Touchstone file parsing."""

    def test_parse_s2p_file(self):
        """Test parsing a standard S2P file."""
        file_path = FIXTURES_DIR / "sample_device.s2p"
        snp = parse(str(file_path))

        assert isinstance(snp, SNPFile)
        assert snp.num_ports == 2
        assert len(snp.frequency) == 51
        assert snp.frequency[0] == pytest.approx(2.0e9, rel=1e-3)
        assert snp.frequency[-1] == pytest.approx(2.5e9, rel=1e-3)
        assert snp.reference_impedance == 50.0

    def test_parse_s2p_extracts_s_parameters(self):
        """Test that S-parameters are correctly extracted."""
        file_path = FIXTURES_DIR / "sample_device.s2p"
        snp = parse(str(file_path))

        assert "s11" in snp.s_parameters
        assert "s12" in snp.s_parameters
        assert "s21" in snp.s_parameters
        assert "s22" in snp.s_parameters

        # All S-params should have same length as frequency
        for key, values in snp.s_parameters.items():
            assert len(values) == len(snp.frequency)

    def test_parse_s2p_magnitude_angle_format(self):
        """Test parsing magnitude/angle format (MA)."""
        file_path = FIXTURES_DIR / "sample_device.s2p"
        snp = parse(str(file_path))

        # S11 at first point: 0.75 @ -45°
        # In complex form: 0.75 * (cos(-45°) + j*sin(-45°))
        s11_0 = snp.s11[0]
        assert np.abs(s11_0) == pytest.approx(0.75, rel=1e-2)

    def test_parse_component_file(self):
        """Test parsing a component S2P file."""
        file_path = FIXTURES_DIR / "components" / "Murata_CAP_10pF.s2p"
        snp = parse(str(file_path))

        assert snp.num_ports == 2
        assert len(snp.frequency) == 11
        assert snp.reference_impedance == 50.0

    def test_parse_nonexistent_file_raises_error(self):
        """Test that parsing nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse("/nonexistent/file.s2p")

    def test_center_frequency(self):
        """Test center frequency calculation."""
        file_path = FIXTURES_DIR / "sample_device.s2p"
        snp = parse(str(file_path))

        # Center should be mean of frequency range
        expected_center = (snp.frequency[0] + snp.frequency[-1]) / 2
        assert snp.center_frequency == pytest.approx(expected_center, rel=1e-3)

    def test_frequency_range(self):
        """Test frequency range property."""
        file_path = FIXTURES_DIR / "sample_device.s2p"
        snp = parse(str(file_path))

        min_freq, max_freq = snp.frequency_range
        assert min_freq == pytest.approx(2.0e9, rel=1e-3)
        assert max_freq == pytest.approx(2.5e9, rel=1e-3)


class TestImpedanceCalculation:
    """Tests for impedance extraction from S-parameters."""

    def test_impedance_from_s11_matched(self):
        """Test impedance calculation for matched case (S11 ≈ 0)."""
        # S11 = 0 means Z = Z0 (perfect match)
        s11 = np.array([0.0 + 0.0j])
        z = extract_impedance(s11, 50.0)

        assert z[0].real == pytest.approx(50.0, rel=1e-3)
        assert z[0].imag == pytest.approx(0.0, abs=1e-3)

    def test_impedance_from_s11_open_circuit(self):
        """Test impedance calculation for open circuit (S11 ≈ 1)."""
        # S11 = 1 means Z → ∞ (open circuit)
        s11 = np.array([0.99 + 0.0j])
        z = extract_impedance(s11, 50.0)

        assert z[0].real > 1000  # Very high impedance

    def test_impedance_from_s11_short_circuit(self):
        """Test impedance calculation for short circuit (S11 ≈ -1)."""
        # S11 = -1 means Z → 0 (short circuit)
        s11 = np.array([-0.99 + 0.0j])
        z = extract_impedance(s11, 50.0)

        assert z[0].real < 1  # Very low impedance

    def test_impedance_at_frequency(self):
        """Test impedance calculation at specific frequency."""
        file_path = Path(__file__).parent.parent / "fixtures" / "sample_device.s2p"
        snp = parse(str(file_path))

        # Get impedance at center frequency
        center = snp.center_frequency
        z = snp.impedance_at_frequency(center)

        assert isinstance(z, complex)
        # Should be non-zero
        assert abs(z) > 0

    def test_impedance_trajectory(self):
        """Test getting impedance at all frequencies."""
        file_path = Path(__file__).parent.parent / "fixtures" / "sample_device.s2p"
        snp = parse(str(file_path))

        trajectory = snp.get_impedance_trajectory()

        assert len(trajectory) == len(snp.frequency)
        assert all(isinstance(z, (complex, np.complexfloating)) for z in trajectory)
