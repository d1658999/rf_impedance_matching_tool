# CLI Interface Contract

**Version**: 1.0  
**Date**: 2025-11-27  
**Purpose**: Define command-line interface for RF Impedance Matching Optimizer

## Command Structure

**Base Command**: `snp-tool [OPTIONS] COMMAND [ARGS]`

**Global Options**:
- `--log-level {DEBUG,INFO,WARNING,ERROR}`: Set logging verbosity (default: INFO)
- `--json`: Output results in JSON format (for automation)
- `--help`: Show help message

---

## Commands

### 1. load

**Purpose**: Load S-parameter file (FR-001)

**Usage**:
```bash
snp-tool load <filepath> [OPTIONS]
```

**Arguments**:
- `filepath`: Path to Touchstone SNP file (required)

**Options**:
- `--format {text|json}`: Output format (default: text)
- `--validate-only`: Only validate file, don't load into session

**Output** (text format):
```
✓ Loaded 2-port network from antenna.s2p
  Frequency range: 1.00 GHz - 3.00 GHz (201 points)
  Impedance: 50.0 Ω
  Format: MA (Magnitude/Angle)
```

**Output** (JSON format):
```json
{
  "status": "success",
  "network": {
    "filepath": "/path/to/antenna.s2p",
    "port_count": 2,
    "frequency_range_ghz": [1.0, 3.0],
    "frequency_points": 201,
    "impedance_normalization": 50.0,
    "format_type": "MA"
  }
}
```

**Error Cases**:
- Exit code 1: File not found
- Exit code 2: Validation error (with detailed report per FR-012)

**Error Output** (validation failure):
```
✗ Validation errors in antenna.s2p:
  Line 15: Invalid frequency value 'abc' (expected number)
  Line 23: Missing S21 parameter
  Line 45: S-parameter magnitude > 1.0 (passive network violation)

Suggested fixes:
  - Ensure frequency column contains numeric values
  - Check S-parameter matrix completeness
  - Verify passive network constraints
```

---

### 2. info

**Purpose**: Display current network information

**Usage**:
```bash
snp-tool info [OPTIONS]
```

**Options**:
- `--components`: Include component list
- `--metrics`: Include impedance metrics

**Output**:
```
Network: antenna.s2p (2 ports)
Frequency: 1.00 - 3.00 GHz (201 points)
Impedance: 50.0 Ω

Components (Port 1):
  1. Capacitor 10.00pF (series)
  2. Inductor 5.00nH (shunt)

Metrics (Port 1 @ 2.4 GHz):
  Input Impedance: 48.5 - j12.3 Ω
  VSWR: 1.42
  Return Loss: -15.3 dB
  Reflection Coefficient: 0.172 ∠ -65°
```

---

### 3. add-component

**Purpose**: Add matching component to port (FR-003, FR-005)

**Usage**:
```bash
snp-tool add-component --port <N> --type <cap|ind> --value <val> --placement <series|shunt> [OPTIONS]
```

**Arguments**:
- `--port <N>`: Port number (1-indexed, required)
- `--type {cap|ind}`: Component type (capacitor or inductor, required)
- `--value <val>`: Component value in engineering notation (e.g., 10pF, 2.2nH, required)
- `--placement {series|shunt}`: Series or shunt configuration (required)

**Options**:
- `--show-result`: Display updated S-parameters after addition

**Output**:
```
✓ Added capacitor 10.00pF to Port 1 (series)
  Component order: 1 of 5 (max)
  
Updated metrics (Port 1 @ 2.4 GHz):
  VSWR: 2.15 → 1.42 (improved)
  Return Loss: -9.5 dB → -15.3 dB (improved)
```

**Constraints**:
- Max 5 components per port (FR-003)
- Value must be physically realizable (1fF-100µF caps, 1pH-100mH ind)

**Error Cases**:
- Exit code 3: Max components exceeded
- Exit code 4: Invalid component value
- Exit code 5: Port number out of range

---

### 4. remove-component

**Purpose**: Remove matching component

**Usage**:
```bash
snp-tool remove-component --port <N> --index <I>
```

**Arguments**:
- `--port <N>`: Port number (required)
- `--index <I>`: Component index (0-based, required)

**Output**:
```
✓ Removed component 2 from Port 1
  Remaining components: 1
```

---

### 5. optimize

**Purpose**: Run automated impedance matching optimization (FR-006, FR-008, FR-017)

**Usage**:
```bash
snp-tool optimize --port <N> [OPTIONS]
```

**Arguments**:
- `--port <N>`: Port to optimize (required)

**Options**:
- `--target-impedance <Z>`: Target impedance in ohms (default: 50.0)
- `--freq-min <F>`: Minimum frequency for optimization (e.g., 2.0GHz)
- `--freq-max <F>`: Maximum frequency for optimization (e.g., 2.5GHz)
- `--weights <W>`: Comma-separated metric weights (default: "return_loss=0.7,bandwidth=0.2,component_count=0.1")
- `--mode {ideal|standard}`: Optimization mode (default: ideal)
  - `ideal`: Continuous component values
  - `standard`: E12/E24/E96 series values
- `--series {E12|E24|E96}`: Standard component series (default: E24, only with --mode standard)
- `--max-components <N>`: Max components to use (default: 5)
- `--solutions <N>`: Number of top solutions to return (default: 3)

**Output**:
```
Optimizing Port 1 for 50.0 Ω impedance...
Frequency range: 2.0 - 2.5 GHz
Mode: ideal values
Weights: return_loss=70%, bandwidth=20%, component_count=10%

[====================> ] 85% (iteration 127/150)

✓ Optimization complete (converged after 142 iterations)

Top 3 Solutions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solution 1 (Score: 0.123)
  Components:
    - Capacitor 10.35pF (series)
    - Inductor 4.82nH (shunt)
  Metrics:
    Return Loss: -18.5 dB
    VSWR: 1.28
    Bandwidth: 350 MHz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solution 2 (Score: 0.145)
  Components:
    - Capacitor 12.10pF (series)
    - Inductor 5.20nH (shunt)
    - Capacitor 2.50pF (series)
  Metrics:
    Return Loss: -17.2 dB
    VSWR: 1.35
    Bandwidth: 400 MHz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[...]

Apply solution? [1-3 / N]: 
```

**JSON Output** (`--json` flag):
```json
{
  "status": "success",
  "optimization": {
    "port": 1,
    "target_impedance": 50.0,
    "frequency_range_ghz": [2.0, 2.5],
    "mode": "ideal",
    "iterations": 142,
    "converged": true
  },
  "solutions": [
    {
      "rank": 1,
      "score": 0.123,
      "components": [
        {"type": "capacitor", "value": "10.35pF", "placement": "series"},
        {"type": "inductor", "value": "4.82nH", "placement": "shunt"}
      ],
      "metrics": {
        "return_loss_db": -18.5,
        "vswr": 1.28,
        "bandwidth_hz": 350000000.0
      }
    }
  ]
}
```

**Performance Target**: <30 seconds for single-port, 2-component matching (SC-004)

---

### 6. apply-solution

**Purpose**: Apply optimization solution to network

**Usage**:
```bash
snp-tool apply-solution --solution <N>
```

**Arguments**:
- `--solution <N>`: Solution number from optimization (required)

**Output**:
```
✓ Applied Solution 1
  Added 2 components to Port 1
```

---

### 7. export

**Purpose**: Export optimized network (FR-010, FR-011)

**Usage**:
```bash
snp-tool export [OPTIONS]
```

**Options**:
- `--snp <filepath>`: Export cascaded S-parameters to SNP file
- `--config <filepath>`: Export component configuration to JSON
- `--format {json|yaml|csv}`: Component config format (default: json)

**Output**:
```
✓ Exported cascaded S-parameters to matched_network.s2p
✓ Exported component configuration to components.json
```

**Component Config (JSON)**:
```json
{
  "export_date": "2025-11-27T12:35:00Z",
  "source_network": "/path/to/antenna.s2p",
  "components": [
    {
      "port": 1,
      "type": "capacitor",
      "value": "10.00pF",
      "placement": "series",
      "order": 0
    },
    {
      "port": 1,
      "type": "inductor",
      "value": "5.00nH",
      "placement": "shunt",
      "order": 1
    }
  ]
}
```

---

### 8. save-session

**Purpose**: Save work session (FR-020)

**Usage**:
```bash
snp-tool save-session <filepath>
```

**Arguments**:
- `filepath`: Session file path (e.g., my_design.snp-session)

**Output**:
```
✓ Session saved to my_design.snp-session
  Components: 2
  Optimization: completed (3 solutions)
```

---

### 9. load-session

**Purpose**: Load work session (FR-021)

**Usage**:
```bash
snp-tool load-session <filepath> [OPTIONS]
```

**Arguments**:
- `filepath`: Session file path

**Options**:
- `--verify`: Verify SNP file checksum

**Output**:
```
✓ Session loaded from my_design.snp-session
  Created: 2025-11-27 12:30:00
  SNP file: /path/to/antenna.s2p (verified)
  Components: 2
  Best solution: Score 0.123 (2 components)
```

**Error Cases**:
- Exit code 6: Session file not found
- Exit code 7: Version incompatible
- Exit code 8: SNP file not found or checksum mismatch

---

### 10. plot

**Purpose**: Generate plots (Smith chart, rectangular)

**Usage**:
```bash
snp-tool plot --type {smith|mag|phase|vswr} [OPTIONS]
```

**Arguments**:
- `--type {smith|mag|phase|vswr}`: Plot type (required)

**Options**:
- `--port <N>`: Port to plot (default: 1)
- `--output <filepath>`: Save to file (PNG, PDF, SVG)
- `--show`: Display interactive plot

**Output**:
```
✓ Generated Smith chart for Port 1
  Saved to smith_chart.png
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | File not found |
| 2 | SNP validation error |
| 3 | Max components exceeded |
| 4 | Invalid component value |
| 5 | Port out of range |
| 6 | Session file not found |
| 7 | Session version incompatible |
| 8 | SNP file checksum mismatch |
| 9 | Optimization failed |
| 10 | General error |

---

## Batch Processing Example

```bash
#!/bin/bash
# Batch optimize multiple SNP files

for file in *.s2p; do
    echo "Processing $file..."
    
    snp-tool load "$file" --json > /dev/null
    snp-tool optimize --port 1 \
        --target-impedance 50 \
        --mode standard \
        --series E24 \
        --weights "return_loss=0.8,component_count=0.2" \
        --json > "results/${file%.s2p}_optimization.json"
    
    snp-tool apply-solution --solution 1
    snp-tool export --snp "matched/${file%.s2p}_matched.s2p" \
                    --config "matched/${file%.s2p}_components.json"
    
    echo "✓ Complete: $file"
done
```

---

## JSON Schema for Automation

All JSON outputs follow consistent structure:
```json
{
  "status": "success|error",
  "message": "Human-readable message",
  "data": { /* Command-specific data */ },
  "errors": [ /* Array of errors if status=error */ ]
}
```

---

## Logging Output (--log-level DEBUG)

```
2025-11-27 12:34:56 - snp_tool.parsers - INFO - Loading SNP file: antenna.s2p
2025-11-27 12:34:56 - snp_tool.parsers - DEBUG - Detected Touchstone format: MA, 50 ohms
2025-11-27 12:34:56 - snp_tool.parsers - DEBUG - Parsed 201 frequency points
2025-11-27 12:34:57 - snp_tool.core - INFO - Added capacitor 10pF to port 1 (series)
2025-11-27 12:34:57 - snp_tool.core - DEBUG - S-parameter recalculation: 15ms
2025-11-27 12:35:00 - snp_tool.optimizer - INFO - Starting optimization (target: 50 ohms)
2025-11-27 12:35:15 - snp_tool.optimizer - DEBUG - Iteration 100: best_score=0.145
2025-11-27 12:35:23 - snp_tool.optimizer - INFO - Optimization converged (142 iterations)
```

---

## Implementation Notes

- CLI uses `click` library for command parsing (standard Python CLI framework)
- Controller pattern: CLI commands call `ImpedanceMatchingController` methods (shared with GUI)
- Output formatters in `snp_tool/cli/output.py` handle text vs JSON formatting
- Progress bars for long operations (optimize) using `click.progressbar()` or `rich` library
- Structured logging via `python-json-logger` (JSON format for automation)

---

## Next Steps

1. Implement CLI commands in `src/snp_tool/cli/commands.py`
2. Implement output formatters in `src/snp_tool/cli/output.py`
3. Write integration tests for each command in `tests/integration/test_cli_workflow.py`
4. Verify contract compliance with acceptance scenarios from spec.md
