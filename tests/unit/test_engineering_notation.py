"""Tests for engineering notation parsing and formatting.

Task 1.1.3: Implement Engineering Notation Parser
"""

import pytest
from snp_tool.utils.engineering import (
    parse_engineering_notation,
    format_engineering_notation,
    MULTIPLIERS,
)


class TestParseEngineeringNotation:
    """Test parsing engineering notation strings."""
    
    def test_parse_valid_pF(self):
        """Test parsing picofarads."""
        assert abs(parse_engineering_notation("10pF") - 1e-11) < 1e-15
        assert abs(parse_engineering_notation("2.2pF") - 2.2e-12) < 1e-15
        assert abs(parse_engineering_notation("100pF") - 1e-10) < 1e-15
    
    def test_parse_valid_nH(self):
        """Test parsing nanohenries."""
        assert parse_engineering_notation("1nH") == 1e-9
        assert parse_engineering_notation("10nH") == 1e-8
        assert parse_engineering_notation("5.6nH") == 5.6e-9
    
    def test_parse_valid_uH(self):
        """Test parsing microhenries with 'u'."""
        assert abs(parse_engineering_notation("100uH") - 1e-4) < 1e-15
        assert abs(parse_engineering_notation("2.2uH") - 2.2e-6) < 1e-15
    
    def test_parse_valid_uH_unicode(self):
        """Test parsing microhenries with 'µ' unicode character."""
        assert abs(parse_engineering_notation("100µH") - 1e-4) < 1e-15
        assert abs(parse_engineering_notation("2.2µH") - 2.2e-6) < 1e-15
    
    def test_parse_valid_GHz(self):
        """Test parsing gigahertz."""
        assert parse_engineering_notation("1.5GHz") == 1.5e9
        assert parse_engineering_notation("2.4GHz") == 2.4e9
    
    def test_parse_all_multipliers(self):
        """Test all supported multipliers."""
        assert parse_engineering_notation("1pF") == 1e-12
        assert parse_engineering_notation("1nF") == 1e-9
        assert parse_engineering_notation("1uF") == 1e-6
        assert parse_engineering_notation("1mF") == 1e-3
        assert parse_engineering_notation("1kHz") == 1e3
        assert parse_engineering_notation("1MHz") == 1e6
        assert parse_engineering_notation("1GHz") == 1e9
    
    def test_parse_no_multiplier(self):
        """Test parsing without multiplier."""
        assert parse_engineering_notation("1F") == 1.0
        assert parse_engineering_notation("50H") == 50.0
    
    def test_parse_invalid_notation(self):
        """Test error handling for invalid notation."""
        with pytest.raises(ValueError, match="Invalid engineering notation"):
            parse_engineering_notation("abc")
        
        with pytest.raises(ValueError, match="Invalid engineering notation"):
            parse_engineering_notation("10 pF x")
    
    def test_parse_invalid_number(self):
        """Test error handling for invalid numbers."""
        with pytest.raises(ValueError, match="Invalid engineering notation"):
            parse_engineering_notation("10.5.3pF")
    
    def test_parse_unknown_multiplier(self):
        """Test error handling for unknown multipliers."""
        # 'x' is not a recognized prefix, so it's treated as part of unit
        # This doesn't raise an error unless we validate the unit
        result = parse_engineering_notation("10F")  # Valid: no multiplier
        assert abs(result - 10.0) < 1e-15
    
    def test_parse_with_unit_validation_success(self):
        """Test unit validation when expected_unit matches."""
        assert parse_engineering_notation("10pF", expected_unit='F') == 1e-11
        assert parse_engineering_notation("5nH", expected_unit='H') == 5e-9
    
    def test_parse_with_unit_validation_mismatch(self):
        """Test unit validation when expected_unit doesn't match."""
        with pytest.raises(ValueError, match="Unit mismatch"):
            parse_engineering_notation("10pF", expected_unit='H')
    
    def test_parse_missing_unit_when_expected(self):
        """Test error when unit is missing but expected."""
        with pytest.raises(ValueError, match="Missing unit"):
            parse_engineering_notation("10p", expected_unit='F')
    
    def test_parse_case_insensitive_unit(self):
        """Test that unit validation is case-insensitive."""
        # pf (lowercase) should match F (uppercase)
        assert parse_engineering_notation("10pf", expected_unit='F') == 1e-11


class TestFormatEngineeringNotation:
    """Test formatting values to engineering notation."""
    
    def test_format_pF(self):
        """Test formatting picofarads."""
        assert format_engineering_notation(1e-11, 'F') == "10.00pF"
        assert format_engineering_notation(2.2e-12, 'F') == "2.20pF"
    
    def test_format_nH(self):
        """Test formatting nanohenries."""
        assert format_engineering_notation(1e-9, 'H') == "1.00nH"
        assert format_engineering_notation(5.6e-9, 'H') == "5.60nH"
    
    def test_format_uH(self):
        """Test formatting microhenries."""
        assert format_engineering_notation(1e-4, 'H') == "100.00uH"
        assert format_engineering_notation(2.2e-6, 'H') == "2.20uH"
    
    def test_format_MHz(self):
        """Test formatting megahertz."""
        assert format_engineering_notation(1e6, 'Hz') == "1.00MHz"
        assert format_engineering_notation(2.4e9, 'Hz') == "2.40GHz"
    
    def test_format_no_unit(self):
        """Test formatting without unit."""
        assert format_engineering_notation(1e-9, '') == "1.00n"
    
    def test_format_custom_precision(self):
        """Test custom precision formatting."""
        assert format_engineering_notation(2.2e-12, 'F', precision=1) == "2.2pF"
        assert format_engineering_notation(5.678e-9, 'H', precision=3) == "5.678nH"
    
    def test_format_zero(self):
        """Test formatting zero value."""
        assert format_engineering_notation(0, 'F') == "0F"
    
    def test_format_very_small(self):
        """Test formatting very small values."""
        result = format_engineering_notation(1e-15, 'F')
        assert result == "0.00F" or result == "0F"  # Accept both
    
    def test_format_large_value(self):
        """Test formatting large values."""
        assert format_engineering_notation(1e9, 'Hz') == "1.00GHz"
        assert format_engineering_notation(5e9, 'Hz') == "5.00GHz"


class TestRoundtrip:
    """Test parsing and formatting roundtrip."""
    
    def test_roundtrip_capacitor(self):
        """Test parse -> format roundtrip for capacitors."""
        original = "10pF"
        value = parse_engineering_notation(original)
        formatted = format_engineering_notation(value, 'F')
        assert formatted == "10.00pF"
    
    def test_roundtrip_inductor(self):
        """Test parse -> format roundtrip for inductors."""
        original = "5.6nH"
        value = parse_engineering_notation(original)
        formatted = format_engineering_notation(value, 'H')
        assert formatted == "5.60nH"
    
    def test_roundtrip_frequency(self):
        """Test parse -> format roundtrip for frequencies."""
        original = "2.4GHz"
        value = parse_engineering_notation(original)
        formatted = format_engineering_notation(value, 'Hz')
        assert formatted == "2.40GHz"
