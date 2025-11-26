# Contract: Touchstone Parser

**Module**: `snp_tool.parsers.touchstone`  
**Purpose**: Parse .snp/.s2p Touchstone format files and extract S-parameters

---

## Function: `parse(file_path: str, port_mapping: tuple = None) -> SNPFile`

**Input**:
- `file_path`: Path to .snp or .s2p file
- `port_mapping`: (optional) Tuple (source_port, load_port) for multi-port files (default: None for auto-select)

**Output**: `SNPFile` object (see data-model.md)

**Raises**:
- `FileNotFoundError`: File does not exist
- `TouchstoneFormatError`: File format invalid or unrecognized
- `FrequencyGapError`: Non-monotonic or duplicate frequencies
- `InvalidPortMappingError`: Specified ports out of range

**Behavior**:
1. Open file, read header (format line: `# [frequency unit] S [parameter format] R [reference impedance]`)
2. Parse frequency unit (Hz, kHz, MHz, GHz) and convert to Hz
3. Parse S-parameter format (dB/angle, linear/phase, real/imaginary)
4. Parse data lines, build S-matrix dictionary
5. If multi-port (S3P, S4P):
   - If `port_mapping` provided: Extract 2×2 submatrix for specified port pair
   - If `port_mapping=None`: Assume ports 0→1 (raise error if ambiguous)
6. Validate frequency array (sorted, monotonic, no gaps)
7. Return SNPFile object with extracted metadata

**Example**:
```python
from snp_tool.parsers import TouchstoneParser

# 2-port file
device = TouchstoneParser.parse("device.s2p")
# → SNPFile(num_ports=2, frequency=[...], s_parameters={...})

# 3-port file with manual port selection
device = TouchstoneParser.parse("complex.s3p", port_mapping=(0, 2))
# → SNPFile(num_ports=2, source_port=0, load_port=2, frequency=[...])
```

---

## Function: `extract_impedance(s_parameters: dict, frequency: ndarray, reference_impedance: float = 50.0) -> ndarray`

**Input**:
- `s_parameters`: Dictionary with 's11' key (complex array)
- `frequency`: Frequency points array
- `reference_impedance`: Reference impedance (default 50Ω)

**Output**: Complex impedance array (same length as frequency)

**Formula**: `Z = Z0 * (1 + S11) / (1 - S11)`

**Example**:
```python
impedance = TouchstoneParser.extract_impedance(s_params, frequency, 50.0)
# → array([40.2+15.3j, 35.1+22.4j, ...])
```

---

## Function: `validate_frequency_coverage(frequency_grid: list) -> bool`

**Input**: Frequency grid to validate (sorted list of floats)

**Output**: True if valid (no gaps, monotonic), False otherwise

**Raises**: `FrequencyGapError` if gaps detected

**Example**:
```python
try:
    TouchstoneParser.validate_frequency_coverage([2.0e9, 2.1e9, 2.2e9, ...])
except FrequencyGapError as e:
    print(f"Missing frequencies: {e.missing_frequencies}")
```

