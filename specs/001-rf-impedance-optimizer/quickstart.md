# Quickstart Guide: RF Impedance Matching Optimizer

**Version**: 0.1.0  
**Date**: 2025-11-27

## Overview

The RF Impedance Matching Optimizer is a Python tool for analyzing S-parameter files and designing impedance matching networks. It provides both CLI (automation/scripting) and GUI (interactive design) interfaces with Smith chart and rectangular plot visualizations.

---

## Installation

### Prerequisites

- Python 3.9 or later
- pip (Python package installer)

### Install from Source

```bash
# Clone repository
cd rf_impedance_matching_tool

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with all dependencies (CLI + GUI + dev tools)
pip install -e .[all]

# Or install only CLI (no GUI dependencies)
pip install -e .
```

### Verify Installation

```bash
snp-tool --help
```

Expected output:
```
Usage: snp-tool [OPTIONS] COMMAND [ARGS]...

  RF Impedance Matching Optimizer CLI

Commands:
  load             Load S-parameter file
  info             Display current network information
  add-component    Add matching component to port
  optimize         Run automated impedance matching
  export           Export optimized network
  save-session     Save work session
  load-session     Load work session
  plot             Generate plots
```

---

## CLI Quick Start

### 1. Load an S-Parameter File

```bash
# Load S2P file from network analyzer
snp-tool load antenna.s2p
```

Output:
```
✓ Loaded 2-port network from antenna.s2p
  Frequency range: 1.00 GHz - 3.00 GHz (201 points)
  Impedance: 50.0 Ω
  Format: MA (Magnitude/Angle)
```

### 2. View Network Information

```bash
snp-tool info --components --metrics
```

Output:
```
Network: antenna.s2p (2 ports)
Frequency: 1.00 - 3.00 GHz (201 points)
Impedance: 50.0 Ω

Metrics (Port 1 @ 2.4 GHz):
  Input Impedance: 35.2 + j18.5 Ω
  VSWR: 2.15
  Return Loss: -9.5 dB
  Reflection Coefficient: 0.387 ∠ 48°
```

### 3. Add Matching Components

Add a series capacitor:
```bash
snp-tool add-component --port 1 --type cap --value 10pF --placement series
```

Add a shunt inductor:
```bash
snp-tool add-component --port 1 --type ind --value 5nH --placement shunt
```

Output:
```
✓ Added capacitor 10.00pF to Port 1 (series)
  Component order: 1 of 5 (max)
  
Updated metrics (Port 1 @ 2.4 GHz):
  VSWR: 2.15 → 1.42 (improved)
  Return Loss: -9.5 dB → -15.3 dB (improved)
```

### 4. Run Automated Optimization

```bash
snp-tool optimize --port 1 \
    --target-impedance 50 \
    --freq-min 2.0GHz \
    --freq-max 2.5GHz \
    --weights "return_loss=0.7,bandwidth=0.2,component_count=0.1" \
    --mode ideal \
    --solutions 3
```

Output:
```
Optimizing Port 1 for 50.0 Ω impedance...
Frequency range: 2.0 - 2.5 GHz
Mode: ideal values

[====================> ] 100% (converged after 142 iterations)

✓ Optimization complete

Top 3 Solutions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solution 1 (Score: 0.123)
  Components:
    - Capacitor 10.35pF (series)
    - Inductor 4.82nH (shunt)
  Metrics:
    Return Loss: -18.5 dB
    VSWR: 1.28
    Bandwidth: 350 MHz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[...]

Apply solution? [1-3 / N]: 1
```

### 5. Export Results

Export cascaded S-parameters:
```bash
snp-tool export --snp matched_antenna.s2p --config components.json
```

Output:
```
✓ Exported cascaded S-parameters to matched_antenna.s2p
✓ Exported component configuration to components.json
```

Component configuration file (`components.json`):
```json
{
  "export_date": "2025-11-27T12:35:00Z",
  "source_network": "/path/to/antenna.s2p",
  "components": [
    {
      "port": 1,
      "type": "capacitor",
      "value": "10.35pF",
      "placement": "series",
      "order": 0
    },
    {
      "port": 1,
      "type": "inductor",
      "value": "4.82nH",
      "placement": "shunt",
      "order": 1
    }
  ]
}
```

### 6. Save Session for Later

```bash
snp-tool save-session my_antenna_match.snp-session
```

Output:
```
✓ Session saved to my_antenna_match.snp-session
  Components: 2
  Optimization: completed (3 solutions)
```

### 7. Reload Session

```bash
snp-tool load-session my_antenna_match.snp-session --verify
```

Output:
```
✓ Session loaded from my_antenna_match.snp-session
  Created: 2025-11-27 12:30:00
  SNP file: /path/to/antenna.s2p (verified)
  Components: 2
  Best solution: Score 0.123 (2 components)
```

---

## GUI Quick Start

### Launch GUI

```bash
snp-tool-gui
```

### GUI Workflow

1. **Load SNP File**:
   - File → Open SNP File
   - Select your .s1p, .s2p, or .s4p file
   - Network information displays in left panel

2. **Add Matching Components**:
   - Use Component Panel on right side
   - Select port, component type (capacitor/inductor)
   - Enter value in engineering notation (e.g., "10pF", "5nH")
   - Choose placement (series/shunt)
   - Click "Add Component"
   - Smith chart and rectangular plots update in real-time

3. **Run Optimization**:
   - Click "Optimize" button
   - Set target impedance (default 50Ω)
   - Adjust frequency range and weights
   - Choose mode (ideal or standard E-series values)
   - Click "Run Optimization"
   - View top solutions in results panel

4. **Apply Solution**:
   - Select best solution from list
   - Click "Apply Solution"
   - Components automatically added to network
   - Plots update to show matched network

5. **Export Results**:
   - File → Export → Cascaded S-Parameters
   - File → Export → Component Configuration
   - Save matched network for use in other tools

6. **Save Session**:
   - File → Save Session
   - Resume work later with File → Load Session

---

## CLI Examples

### Example 1: Standard Component Optimization

Optimize using E24 series components:

```bash
snp-tool load filter.s2p
snp-tool optimize --port 1 \
    --target-impedance 50 \
    --mode standard \
    --series E24 \
    --weights "return_loss=0.8,component_count=0.2"
snp-tool apply-solution --solution 1
snp-tool export --snp matched_filter.s2p
```

### Example 2: JSON Output for Automation

```bash
snp-tool load antenna.s2p --json > load_result.json
snp-tool optimize --port 1 \
    --target-impedance 50 \
    --json > optimization_result.json

# Parse JSON and apply best solution automatically
python << EOF
import json
with open('optimization_result.json') as f:
    result = json.load(f)
if result['status'] == 'success':
    print(f"Best score: {result['solutions'][0]['score']}")
EOF
```

### Example 3: Batch Processing

Process multiple SNP files:

```bash
#!/bin/bash
for file in *.s2p; do
    echo "Processing $file..."
    snp-tool load "$file"
    snp-tool optimize --port 1 --target-impedance 50 --mode standard
    snp-tool apply-solution --solution 1
    snp-tool export --snp "matched/${file%.s2p}_matched.s2p"
done
```

### Example 4: Generate Smith Chart

```bash
snp-tool load antenna.s2p
snp-tool plot --type smith --port 1 --output smith_chart.png
```

---

## Component Value Format

The tool accepts engineering notation for component values:

| Input | Numeric Value | Description |
|-------|---------------|-------------|
| `10pF` | 10e-12 F | 10 picofarads |
| `2.2nH` | 2.2e-9 H | 2.2 nanohenries |
| `100uH` | 100e-6 H | 100 microhenries |
| `1.5GHz` | 1.5e9 Hz | 1.5 gigahertz |

**Supported Prefixes**:
- `p` (pico, 10^-12)
- `n` (nano, 10^-9)
- `u` or `µ` (micro, 10^-6)
- `m` (milli, 10^-3)
- `k` (kilo, 10^3)
- `M` (mega, 10^6)
- `G` (giga, 10^9)

---

## Optimization Modes

### Ideal Values Mode

```bash
snp-tool optimize --mode ideal
```

- Finds optimal component values without constraints
- Values can be any positive number
- Best for theoretical analysis
- May not be realizable with standard components

### Standard Values Mode

```bash
snp-tool optimize --mode standard --series E24
```

- Constrains optimization to standard E-series component values
- **E12**: 12 values per decade (10% tolerance)
- **E24**: 24 values per decade (5% tolerance)
- **E96**: 96 values per decade (1% tolerance)
- Results directly usable with off-the-shelf components

---

## Optimization Weights

Control optimization priorities with weights (must sum to ~1.0):

```bash
--weights "return_loss=0.7,bandwidth=0.2,component_count=0.1"
```

**Available Metrics**:
- `return_loss`: Minimize reflection (higher return loss dB = better)
- `vswr`: Minimize VSWR (1.0 = perfect match)
- `bandwidth`: Maximize frequency range meeting impedance target
- `component_count`: Minimize number of components (simpler design)

**Example Weight Combinations**:

| Goal | Weights |
|------|---------|
| Best match (narrow band) | `return_loss=0.9,component_count=0.1` |
| Wide bandwidth | `bandwidth=0.6,return_loss=0.3,component_count=0.1` |
| Simple design | `component_count=0.5,return_loss=0.4,bandwidth=0.1` |
| Balanced | `return_loss=0.4,vswr=0.3,bandwidth=0.2,component_count=0.1` |

---

## Troubleshooting

### Error: "Maximum 5 components per port"

You've reached the limit of 5 components per port. Remove existing components or start fresh:

```bash
# Start over
snp-tool load antenna.s2p  # Reloads original file (clears components)
```

### Error: "SNP file validation failed"

The SNP file has format errors. Use `--validate-only` to see detailed report:

```bash
snp-tool load antenna.s2p --validate-only
```

Fix indicated errors in your SNP file (check line numbers in error report).

### Error: "Session version incompatible"

Session file was created with different tool version. Try loading with:

```bash
snp-tool load-session old_session.snp-session
# Tool will attempt automatic migration
```

If migration fails, start fresh and manually recreate the design.

### Optimization Not Converging

If optimization takes too long or doesn't converge:

1. **Reduce max components**: `--max-components 2`
2. **Narrow frequency range**: Focus on specific band
3. **Simplify weights**: Use fewer metrics
4. **Try ideal mode first**: Then snap to standard values manually

---

## Performance Tips

1. **Large SNP files** (>5000 freq points):
   - Load time may exceed 5 seconds
   - Component addition may be slower
   - Consider downsampling frequency points externally

2. **Optimization speed**:
   - Fewer components optimize faster
   - Narrower frequency range optimizes faster
   - Ideal mode faster than standard mode

3. **Batch processing**:
   - Use `--json` flag for machine-readable output
   - Disable interactive prompts with scripts
   - Process files in parallel if independent

---

## Next Steps

- **Learn More**: See `contracts/cli-interface.md` for complete CLI reference
- **API Integration**: See `contracts/core-api.md` for Python API usage
- **Data Model**: See `data-model.md` for understanding internal structure
- **Development**: See `plan.md` for implementation details

---

## Getting Help

```bash
# General help
snp-tool --help

# Command-specific help
snp-tool load --help
snp-tool optimize --help

# Logging for debugging
snp-tool --log-level DEBUG load antenna.s2p
```

---

## Example Session

Complete workflow from start to finish:

```bash
# Load network
$ snp-tool load antenna.s2p
✓ Loaded 2-port network from antenna.s2p
  Frequency range: 2.0 GHz - 3.0 GHz (101 points)

# Check initial state
$ snp-tool info --metrics
Metrics (Port 1 @ 2.5 GHz):
  VSWR: 3.21 (poor match)
  Return Loss: -5.1 dB

# Optimize
$ snp-tool optimize --port 1 --target-impedance 50 --mode standard --series E24
Optimizing... 100% complete
✓ Found 3 solutions
Best solution: VSWR 1.32, Components: 2

# Apply and export
$ snp-tool apply-solution --solution 1
✓ Applied solution (2 components)

$ snp-tool export --snp matched.s2p --config components.json
✓ Exported results

# Save for later
$ snp-tool save-session my_design.snp-session
✓ Session saved

# Generate visualization
$ snp-tool plot --type smith --port 1 --output before_after_smith.png
✓ Smith chart saved
```

**Result**: Antenna impedance matched from VSWR 3.21 to 1.32 using 2 standard E24 components!

---

## Conclusion

You're now ready to use the RF Impedance Matching Optimizer for:
- ✅ Loading and analyzing S-parameter files
- ✅ Manually adding matching components
- ✅ Automated optimization with multi-metric goals
- ✅ Exporting matched networks
- ✅ Session persistence for iterative design

Happy matching! 🎯📡
