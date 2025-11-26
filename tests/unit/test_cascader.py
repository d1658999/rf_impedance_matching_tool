"""Unit tests for ABCD cascader."""

import pytest
import numpy as np

from snp_tool.optimizer.cascader import (
    cascade_networks,
    s_to_abcd,
    abcd_to_s,
    cascade_with_topology,
)


class TestABCDConversion:
    """Tests for S-parameter to ABCD conversion."""

    def test_identity_s_to_abcd(self):
        """Test that thru (S12=S21=1, S11=S22=0) gives identity ABCD."""
        s_params = {
            "s11": np.array([0.0 + 0j]),
            "s12": np.array([1.0 + 0j]),
            "s21": np.array([1.0 + 0j]),
            "s22": np.array([0.0 + 0j]),
        }

        abcd = s_to_abcd(s_params, z0=50.0)

        # Identity ABCD = [[1, 0], [0, 1]]
        assert abcd[0, 0, 0] == pytest.approx(1.0, rel=1e-3)
        assert abcd[0, 0, 1] == pytest.approx(0.0, abs=1e-3)
        assert abcd[0, 1, 0] == pytest.approx(0.0, abs=1e-3)
        assert abcd[0, 1, 1] == pytest.approx(1.0, rel=1e-3)

    def test_abcd_to_s_identity(self):
        """Test that identity ABCD gives thru S-parameters."""
        abcd = np.zeros((1, 2, 2), dtype=np.complex128)
        abcd[0, 0, 0] = 1.0
        abcd[0, 0, 1] = 0.0
        abcd[0, 1, 0] = 0.0
        abcd[0, 1, 1] = 1.0

        s = abcd_to_s(abcd, z0=50.0)

        # Thru: S11=S22=0, S12=S21=1
        assert np.abs(s["s11"][0]) == pytest.approx(0.0, abs=1e-3)
        assert np.abs(s["s21"][0]) == pytest.approx(1.0, rel=1e-3)

    def test_roundtrip_conversion(self):
        """Test S → ABCD → S roundtrip preserves values."""
        # Create some realistic S-parameters
        s_params = {
            "s11": np.array([0.3 + 0.4j]),
            "s12": np.array([0.2 + 0.1j]),
            "s21": np.array([0.2 + 0.1j]),
            "s22": np.array([0.3 - 0.4j]),
        }

        abcd = s_to_abcd(s_params, z0=50.0)
        s_back = abcd_to_s(abcd, z0=50.0)

        # Should get same S-parameters back
        for key in ["s11", "s21", "s12", "s22"]:
            assert np.abs(s_back[key][0] - s_params[key][0]) < 0.01


class TestCascade:
    """Tests for network cascading."""

    def test_cascade_identity(self):
        """Test cascading two identity networks."""
        identity = {
            "s11": np.array([0.0 + 0j]),
            "s12": np.array([1.0 + 0j]),
            "s21": np.array([1.0 + 0j]),
            "s22": np.array([0.0 + 0j]),
        }

        frequency = np.array([1e9])
        result = cascade_networks([identity, identity], frequency)

        # Identity × Identity = Identity
        assert np.abs(result["s11"][0]) == pytest.approx(0.0, abs=1e-3)
        assert np.abs(result["s21"][0]) == pytest.approx(1.0, rel=1e-3)

    def test_cascade_single_network(self):
        """Test that single network cascade returns same network."""
        s_params = {
            "s11": np.array([0.5 + 0j]),
            "s12": np.array([0.5 + 0j]),
            "s21": np.array([0.5 + 0j]),
            "s22": np.array([0.5 + 0j]),
        }

        frequency = np.array([1e9])
        result = cascade_networks([s_params], frequency)

        for key in ["s11", "s21", "s12", "s22"]:
            assert result[key][0] == pytest.approx(s_params[key][0], rel=1e-6)

    def test_cascade_multiple_frequencies(self):
        """Test cascading works for multiple frequency points."""
        n_freqs = 10

        network1 = {
            "s11": 0.1 * np.ones(n_freqs, dtype=np.complex128),
            "s12": 0.9 * np.ones(n_freqs, dtype=np.complex128),
            "s21": 0.9 * np.ones(n_freqs, dtype=np.complex128),
            "s22": 0.1 * np.ones(n_freqs, dtype=np.complex128),
        }

        network2 = {
            "s11": 0.2 * np.ones(n_freqs, dtype=np.complex128),
            "s12": 0.8 * np.ones(n_freqs, dtype=np.complex128),
            "s21": 0.8 * np.ones(n_freqs, dtype=np.complex128),
            "s22": 0.2 * np.ones(n_freqs, dtype=np.complex128),
        }

        frequency = np.linspace(1e9, 2e9, n_freqs)
        result = cascade_networks([network1, network2], frequency)

        # Result should have same number of frequency points
        assert len(result["s11"]) == n_freqs
        assert len(result["s21"]) == n_freqs


class TestCascadeWithTopology:
    """Tests for topology-aware cascading."""

    def test_cascade_series_series(self):
        """Test cascading two series components."""
        device = {
            "s11": np.array([0.5 + 0j]),
            "s12": np.array([0.5 + 0j]),
            "s21": np.array([0.5 + 0j]),
            "s22": np.array([0.5 + 0j]),
        }

        comp1 = {
            "s11": np.array([0.2 + 0j]),
            "s12": np.array([0.8 + 0j]),
            "s21": np.array([0.8 + 0j]),
            "s22": np.array([0.2 + 0j]),
        }

        comp2 = {
            "s11": np.array([0.3 + 0j]),
            "s12": np.array([0.7 + 0j]),
            "s21": np.array([0.7 + 0j]),
            "s22": np.array([0.3 + 0j]),
        }

        frequency = np.array([1e9])
        result = cascade_with_topology(
            device,
            [comp1, comp2],
            ["series", "series"],
            frequency,
        )

        # Should produce valid S-parameters
        assert len(result["s11"]) == 1
        assert np.abs(result["s11"][0]) <= 1.0  # Valid S-parameter magnitude

    def test_cascade_series_shunt(self):
        """Test L-section topology (series-shunt)."""
        device = {
            "s11": np.array([0.5 + 0j]),
            "s12": np.array([0.5 + 0j]),
            "s21": np.array([0.5 + 0j]),
            "s22": np.array([0.5 + 0j]),
        }

        comp1 = {
            "s11": np.array([0.2 + 0.1j]),
            "s12": np.array([0.8 + 0j]),
            "s21": np.array([0.8 + 0j]),
            "s22": np.array([0.2 - 0.1j]),
        }

        comp2 = {
            "s11": np.array([0.3 - 0.1j]),
            "s12": np.array([0.7 + 0j]),
            "s21": np.array([0.7 + 0j]),
            "s22": np.array([0.3 + 0.1j]),
        }

        frequency = np.array([1e9])
        result = cascade_with_topology(
            device,
            [comp1, comp2],
            ["series", "shunt"],  # L-section
            frequency,
        )

        # Should produce valid result
        assert "s11" in result
        assert "s21" in result
