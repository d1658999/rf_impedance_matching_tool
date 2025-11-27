"""
Unit tests for SNP file validator.

Tests verify FR-012: Detailed validation reports with line numbers and suggested corrections.
"""

import pytest
from pathlib import Path
import numpy as np

from snp_tool.validators.snp_validator import (
    validate_snp_file,
    ValidationReport,
    ValidationError as ValError
)


def test_validate_valid_file(tmp_path):
    """Test validation of a valid SNP file - should pass with no errors."""
    # Create a valid S2P file
    valid_s2p = tmp_path / "valid.s2p"
    valid_s2p.write_text("""! Valid S2P file
# GHz S RI R 50
1.0 0.1 0.05 0.9 0.05 0.9 -0.05 0.1 -0.05
2.0 0.12 0.06 0.88 0.06 0.88 -0.06 0.12 -0.06
3.0 0.15 0.08 0.85 0.08 0.85 -0.08 0.15 -0.08
""")
    
    report = validate_snp_file(valid_s2p)
    
    assert report.is_valid
    assert len(report.errors) == 0
    assert "PASS" in str(report)


def test_validate_frequency_monotonicity(tmp_path):
    """Test detection of non-monotonic frequencies with line numbers."""
    non_monotonic = tmp_path / "bad_freq.s2p"
    non_monotonic.write_text("""! Non-monotonic frequencies
# GHz S RI R 50
1.0 0.1 0.05 0.9 0.05 0.9 -0.05 0.1 -0.05
3.0 0.15 0.08 0.85 0.08 0.85 -0.08 0.15 -0.08
2.0 0.12 0.06 0.88 0.06 0.88 -0.06 0.12 -0.06
""")
    
    report = validate_snp_file(non_monotonic)
    
    assert not report.is_valid
    assert len(report.errors) > 0
    
    # Check that error includes line number
    freq_error = next((e for e in report.errors if "frequency" in e.message.lower()), None)
    assert freq_error is not None
    assert freq_error.line_number is not None
    assert freq_error.line_number > 0
    assert "sort" in freq_error.suggested_fix.lower() or "order" in freq_error.suggested_fix.lower() or "ascend" in freq_error.suggested_fix.lower()


def test_validate_non_numeric_sparams(tmp_path):
    """Test detection of non-numeric S-parameters with line number and suggested fix."""
    bad_values = tmp_path / "non_numeric.s2p"
    bad_values.write_text("""! Non-numeric S-parameters
# GHz S RI R 50
1.0 0.1 0.05 0.9 0.05 0.9 -0.05 0.1 -0.05
2.0 INVALID 0.06 0.88 0.06 0.88 -0.06 0.12 -0.06
3.0 0.15 0.08 0.85 0.08 0.85 -0.08 0.15 -0.08
""")
    
    report = validate_snp_file(bad_values)
    
    assert not report.is_valid
    assert len(report.errors) > 0
    
    # Check error details
    numeric_error = next((e for e in report.errors if "numeric" in e.message.lower() or "invalid" in e.message.lower()), None)
    assert numeric_error is not None
    assert numeric_error.line_number == 4  # Line with INVALID
    assert "INVALID" in numeric_error.message
    assert "numeric" in numeric_error.suggested_fix.lower() or "number" in numeric_error.suggested_fix.lower()


def test_validate_passive_violation(tmp_path):
    """Test detection of passive network violations (|S| > 1.0)."""
    passive_violation = tmp_path / "active.s2p"
    passive_violation.write_text("""! S-parameters with |S| > 1.0 (active device)
# GHz S RI R 50
1.0 0.1 0.05 0.9 0.05 0.9 -0.05 0.1 -0.05
2.0 1.5 0.0 0.88 0.06 0.88 -0.06 0.12 -0.06
3.0 0.15 0.08 0.85 0.08 0.85 -0.08 0.15 -0.08
""")
    
    report = validate_snp_file(passive_violation)
    
    assert not report.is_valid
    
    # Check for passive violation error
    passive_error = next((e for e in report.errors if "passive" in e.message.lower() or "|s|" in e.message.lower() or "magnitude" in e.message.lower()), None)
    assert passive_error is not None
    assert passive_error.line_number == 4  # Line with |S11| = 1.5
    assert "1.5" in passive_error.message or "greater" in passive_error.message.lower()


def test_validation_report_to_string():
    """Test human-readable formatting of ValidationReport."""
    report = ValidationReport()
    report.errors.append(ValError(
        line_number=10,
        error_type="FrequencyError",
        message="Frequency 2.5 GHz is less than previous 3.0 GHz",
        suggested_fix="Sort frequencies in ascending order"
    ))
    report.errors.append(ValError(
        line_number=15,
        error_type="NumericError",
        message="Value 'BAD' cannot be parsed as float",
        suggested_fix="Replace with numeric value (e.g., 0.5)"
    ))
    
    report_str = str(report)
    
    # Check format includes all important information
    assert "FAIL" in report_str or "ERROR" in report_str
    assert "Line 10" in report_str
    assert "Line 15" in report_str
    assert "FrequencyError" in report_str
    assert "NumericError" in report_str
    assert "Sort frequencies" in report_str
    assert "Replace with numeric" in report_str


def test_validation_report_to_json():
    """Test JSON serialization of ValidationReport."""
    report = ValidationReport()
    report.errors.append(ValError(
        line_number=10,
        error_type="FrequencyError",
        message="Frequency not monotonic",
        suggested_fix="Sort ascending"
    ))
    
    json_output = report.to_json()
    
    assert "is_valid" in json_output
    assert "errors" in json_output
    assert json_output["is_valid"] is False
    assert len(json_output["errors"]) == 1
    assert json_output["errors"][0]["line_number"] == 10
    assert json_output["errors"][0]["error_type"] == "FrequencyError"


def test_validate_missing_frequency(tmp_path):
    """Test detection of missing frequency column."""
    missing_freq = tmp_path / "missing_freq.s2p"
    missing_freq.write_text("""! Missing frequency
# GHz S RI R 50
0.1 0.05 0.9 0.05 0.9 -0.05 0.1 -0.05
0.12 0.06 0.88 0.06 0.88 -0.06 0.12 -0.06
""")
    
    report = validate_snp_file(missing_freq)
    
    assert not report.is_valid
    # Should detect column count mismatch (8 expected for 2-port, got 7)


def test_validate_empty_file(tmp_path):
    """Test validation of empty file."""
    empty = tmp_path / "empty.s2p"
    empty.write_text("")
    
    report = validate_snp_file(empty)
    
    assert not report.is_valid
    assert any("empty" in e.message.lower() for e in report.errors)


def test_validate_no_data_lines(tmp_path):
    """Test file with header but no data."""
    no_data = tmp_path / "no_data.s2p"
    no_data.write_text("""! Only header
# GHz S RI R 50
""")
    
    report = validate_snp_file(no_data)
    
    assert not report.is_valid
    assert any("no data" in e.message.lower() or "valid data" in e.message.lower() for e in report.errors)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
