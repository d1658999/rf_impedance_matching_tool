"""Unit tests for RF metrics calculation."""

import pytest
import numpy as np

from snp_tool.optimizer.metrics import (
    reflection_coefficient,
    vswr,
    return_loss_db,
    reflection_coefficient_from_s11,
    vswr_from_s11,
    return_loss_from_s11,
    impedance_from_s11,
    is_matched,
)


class TestReflectionCoefficient:
    """Tests for reflection coefficient calculation."""

    def test_matched_impedance(self):
        """Test Γ = 0 for matched impedance."""
        gamma = reflection_coefficient(50.0 + 0j, 50.0)
        assert gamma == pytest.approx(0.0, abs=1e-10)

    def test_open_circuit(self):
        """Test Γ = 1 for open circuit (high impedance)."""
        gamma = reflection_coefficient(1e6 + 0j, 50.0)
        assert gamma == pytest.approx(1.0, rel=1e-3)

    def test_short_circuit(self):
        """Test Γ = 1 for short circuit (low impedance)."""
        gamma = reflection_coefficient(0.001 + 0j, 50.0)
        assert gamma == pytest.approx(1.0, rel=1e-3)

    def test_complex_impedance(self):
        """Test reflection coefficient for complex impedance."""
        # Z = 100 + 50j Ω
        z = 100 + 50j
        gamma = reflection_coefficient(z, 50.0)

        # Calculate expected: Γ = (Z - Z0) / (Z + Z0)
        expected = abs((z - 50) / (z + 50))
        assert gamma == pytest.approx(expected, rel=1e-6)

    def test_array_input(self):
        """Test with array of impedances."""
        z = np.array([50.0, 100.0, 25.0])
        gamma = reflection_coefficient(z, 50.0)

        assert len(gamma) == 3
        assert gamma[0] == pytest.approx(0.0, abs=1e-10)  # Matched
        assert gamma[1] > 0  # 100Ω > 50Ω
        assert gamma[2] > 0  # 25Ω < 50Ω


class TestVSWR:
    """Tests for VSWR calculation."""

    def test_matched_vswr(self):
        """Test VSWR = 1.0 for matched impedance."""
        v = vswr(50.0 + 0j, 50.0)
        assert v == pytest.approx(1.0, rel=1e-3)

    def test_vswr_formula(self):
        """Test VSWR = (1 + |Γ|) / (1 - |Γ|)."""
        # For Z = 100Ω, Γ = (100-50)/(100+50) = 50/150 = 1/3
        # VSWR = (1 + 1/3) / (1 - 1/3) = (4/3) / (2/3) = 2.0
        v = vswr(100.0 + 0j, 50.0)
        assert v == pytest.approx(2.0, rel=1e-3)

    def test_vswr_always_ge_1(self):
        """Test VSWR is always ≥ 1."""
        impedances = [10, 25, 50, 100, 200, 500]
        for z in impedances:
            v = vswr(z + 0j, 50.0)
            assert v >= 1.0


class TestReturnLoss:
    """Tests for return loss calculation."""

    def test_matched_return_loss(self):
        """Test high return loss for matched impedance."""
        # Perfect match → Γ = 0 → RL = ∞ (capped at 100 dB)
        rl = return_loss_db(50.0 + 0j, 50.0)
        assert rl > 60  # Very high return loss

    def test_return_loss_formula(self):
        """Test RL = -20 * log10(|Γ|)."""
        # For |Γ| = 0.1, RL = -20 * log10(0.1) = 20 dB
        # Z for |Γ| = 0.1: solve (Z-50)/(Z+50) = 0.1
        # 0.1(Z+50) = Z-50 → 0.1Z + 5 = Z - 50 → 55 = 0.9Z → Z = 61.11
        z = 61.11 + 0j
        rl = return_loss_db(z, 50.0)
        # Γ = 11.11/111.11 ≈ 0.1
        assert rl == pytest.approx(20.0, rel=0.1)

    def test_return_loss_positive(self):
        """Test return loss is always positive."""
        impedances = [10, 25, 75, 100, 200]
        for z in impedances:
            rl = return_loss_db(z + 0j, 50.0)
            assert rl > 0


class TestFromS11:
    """Tests for metrics calculated directly from S11."""

    def test_reflection_from_s11(self):
        """Test |Γ| = |S11|."""
        s11 = 0.3 + 0.4j  # |S11| = 0.5
        gamma = reflection_coefficient_from_s11(s11)
        assert gamma == pytest.approx(0.5, rel=1e-6)

    def test_vswr_from_s11(self):
        """Test VSWR from S11."""
        s11 = 0.3 + 0j  # |S11| = 0.3
        # VSWR = (1 + 0.3) / (1 - 0.3) = 1.3/0.7 ≈ 1.857
        v = vswr_from_s11(s11)
        assert v == pytest.approx(1.857, rel=1e-2)

    def test_impedance_from_s11(self):
        """Test Z = Z0 * (1 + S11) / (1 - S11)."""
        # S11 = 0 → Z = 50Ω
        z = impedance_from_s11(0.0 + 0j, 50.0)
        assert z.real == pytest.approx(50.0, rel=1e-6)
        assert z.imag == pytest.approx(0.0, abs=1e-6)

        # S11 = 1/3 → Z = Z0 * (4/3) / (2/3) = Z0 * 2 = 100Ω
        z = impedance_from_s11(1 / 3 + 0j, 50.0)
        assert z.real == pytest.approx(100.0, rel=1e-3)


class TestIsMatched:
    """Tests for matching detection."""

    def test_perfect_match(self):
        """Test perfect 50Ω match is detected."""
        assert is_matched(50.0 + 0j, 50.0)

    def test_within_tolerance(self):
        """Test impedance within tolerance is matched."""
        assert is_matched(55.0 + 0j, 50.0, tolerance=10.0)
        assert is_matched(45.0 + 0j, 50.0, tolerance=10.0)
        # 35Ω is outside ±10Ω tolerance but has VSWR = 1.43 which is < 2.0
        # So it's still considered "matched" by VSWR criterion
        # Test with 20Ω which has VSWR = 2.5 (> 2.0)
        assert not is_matched(20.0 + 0j, 50.0, tolerance=10.0, vswr_threshold=2.0)

    def test_vswr_threshold(self):
        """Test VSWR threshold matching."""
        # Z = 100Ω has VSWR = 2.0
        assert is_matched(100.0 + 0j, 50.0, vswr_threshold=2.0)
        assert is_matched(100.0 + 0j, 50.0, vswr_threshold=2.1)

    def test_complex_impedance_match(self):
        """Test complex impedance matching."""
        # 50 + 5j is within 10Ω of 50
        assert is_matched(50.0 + 5j, 50.0, tolerance=10.0)
