"""
SNP File Validator.

Provides detailed validation reports per FR-012 with line numbers and suggested corrections.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np


@dataclass
class ValidationError:
    """Represents a single validation error."""
    
    line_number: Optional[int]
    error_type: str
    message: str
    suggested_fix: str


@dataclass
class ValidationReport:
    """Validation report with errors and suggestions."""
    
    errors: List[ValidationError] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Returns True if no errors found."""
        return len(self.errors) == 0
    
    def __str__(self) -> str:
        """Human-readable format."""
        if self.is_valid:
            return "✓ PASS: File is valid"
        
        output = ["✗ FAIL: Validation errors found\n"]
        for error in self.errors:
            line_info = f"Line {error.line_number}: " if error.line_number else ""
            output.append(f"{line_info}[{error.error_type}] {error.message}")
            output.append(f"  → Suggestion: {error.suggested_fix}\n")
        
        return "\n".join(output)
    
    def to_json(self) -> Dict[str, Any]:
        """JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "errors": [
                {
                    "line_number": e.line_number,
                    "error_type": e.error_type,
                    "message": e.message,
                    "suggested_fix": e.suggested_fix
                }
                for e in self.errors
            ]
        }


def validate_snp_file(filepath: Path) -> ValidationReport:
    """
    Validate SNP file with detailed error reporting (FR-012).
    
    Checks:
    - File is not empty
    - Has valid Touchstone header
    - Frequencies are monotonically increasing
    - All values are numeric
    - Passive network constraint (|S| <= 1.0)
    - Correct number of columns for port count
    
    Args:
        filepath: Path to SNP file
        
    Returns:
        ValidationReport with errors and suggestions
    """
    report = ValidationReport()
    
    # Check file exists and is not empty
    if not filepath.exists():
        report.errors.append(ValidationError(
            line_number=None,
            error_type="FileNotFound",
            message=f"File '{filepath}' does not exist",
            suggested_fix="Check file path is correct"
        ))
        return report
    
    content = filepath.read_text()
    if not content.strip():
        report.errors.append(ValidationError(
            line_number=None,
            error_type="EmptyFile",
            message="File is empty",
            suggested_fix="Add valid Touchstone data"
        ))
        return report
    
    lines = content.split('\n')
    
    # Parse header
    header_line = None
    header_line_num = None
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith('!'):
            if stripped.startswith('#'):
                header_line = stripped
                header_line_num = i
                break
    
    if not header_line:
        report.errors.append(ValidationError(
            line_number=None,
            error_type="MissingHeader",
            message="No Touchstone header found (should start with #)",
            suggested_fix="Add header line like: # GHz S RI R 50"
        ))
        return report
    
    # Extract port count from filename
    match = re.search(r's(\d+)p', filepath.name, re.IGNORECASE)
    if not match:
        port_count = 2  # Default to 2-port
    else:
        port_count = int(match.group(1))
    
    # Expected columns: freq + (2*port_count)^2 for RI format
    expected_cols = 1 + (2 * port_count * port_count)
    
    # Parse data lines
    data_lines = []
    frequencies = []
    
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith('!') or stripped.startswith('#'):
            continue
        
        # Try to parse as data line
        parts = stripped.split()
        
        if len(parts) < expected_cols:
            if len(parts) > 0:
                report.errors.append(ValidationError(
                    line_number=i,
                    error_type="ColumnCountError",
                    message=f"Expected {expected_cols} columns, got {len(parts)}",
                    suggested_fix=f"Add missing columns (should have frequency + {expected_cols-1} S-parameter values)"
                ))
            continue
        
        # Validate all values are numeric
        for j, value in enumerate(parts[:expected_cols]):
            try:
                float_val = float(value)
                if j == 0:
                    frequencies.append(float_val)
            except ValueError:
                report.errors.append(ValidationError(
                    line_number=i,
                    error_type="NumericError",
                    message=f"Value '{value}' cannot be parsed as float",
                    suggested_fix="Replace with numeric value (e.g., 0.5)"
                ))
                break
        else:
            # All values parsed successfully
            data_lines.append((i, parts))
    
    if not data_lines:
        report.errors.append(ValidationError(
            line_number=None,
            error_type="NoData",
            message="No valid data lines found",
            suggested_fix="Add frequency and S-parameter data lines"
        ))
        return report
    
    # Check frequency monotonicity
    if len(frequencies) > 1:
        for i in range(len(frequencies) - 1):
            if frequencies[i] >= frequencies[i + 1]:
                report.errors.append(ValidationError(
                    line_number=data_lines[i + 1][0],
                    error_type="FrequencyError",
                    message=f"Frequency {frequencies[i+1]} is not greater than previous {frequencies[i]}",
                    suggested_fix="Sort frequencies in ascending order"
                ))
                break
    
    # Check passive network constraint (|S| <= 1.0)
    for line_num, parts in data_lines:
        # Parse S-parameters (skip frequency)
        s_values = []
        for j in range(1, len(parts), 2):
            if j + 1 < len(parts):
                try:
                    real = float(parts[j])
                    imag = float(parts[j + 1])
                    magnitude = np.sqrt(real**2 + imag**2)
                    s_values.append(magnitude)
                except (ValueError, IndexError):
                    continue
        
        # Check for violations
        for mag in s_values:
            if mag > 1.0:
                report.errors.append(ValidationError(
                    line_number=line_num,
                    error_type="PassiveViolation",
                    message=f"S-parameter magnitude {mag:.2f} exceeds 1.0 (active device)",
                    suggested_fix="Verify measurement is correct, passive devices must have |S| <= 1.0"
                ))
                break
    
    return report
