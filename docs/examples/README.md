# Example: RF Impedance Matching Workflow

This directory contains example S-parameter files for demonstrating the
RF Impedance Matching Tool.

## Files

- `wifi_antenna.s2p` - Sample WiFi antenna (2.4 GHz band)
- `cap_10pF.s2p` - Sample 10pF capacitor (Murata style)
- `ind_4n7.s2p` - Sample 4.7nH inductor (Murata style)

## Quick Start

### 1. Load and View Device

```bash
snp-tool load docs/examples/wifi_antenna.s2p
```

Output:
```
Device: wifi_antenna.s2p
Ports: 2
Frequency range: 2.0 - 2.8 GHz
Center frequency: 2.4 GHz
Impedance at center: (35.2 - 25.1j) Ω
Reflection coefficient: 0.35 (-9.0 dB)
VSWR: 2.08
```

### 2. Import Component Library

```bash
snp-tool library docs/examples/
```

Output:
```
Library loaded: 2 components
  Capacitors: 1
  Inductors: 1
Frequency coverage: 1 MHz - 6 GHz
```

### 3. Optimize Matching Network

```bash
snp-tool optimize docs/examples/wifi_antenna.s2p \
  --library docs/examples/ \
  --topology L-section \
  --target-frequency 2.4e9
```

Output:
```
Optimization Results
====================
Topology: L-section
Target: 2.4 GHz

Selected Components:
  1. SERIES: cap_10pF.s2p (10 pF)
  2. SHUNT: ind_4n7.s2p (4.7 nH)

Performance:
  Impedance after matching: (48.5 + 2.3j) Ω
  Reflection coefficient: 0.05 (-26.0 dB)
  VSWR: 1.10

Status: ✓ SUCCESS (50Ω ± 10Ω achieved)
```

### 4. Export Results

```bash
# Export schematic
snp-tool export schematic output/matching_schematic.txt

# Export cascaded S-parameters
snp-tool export s2p output/matched_device.s2p
```

## Python API Example

```python
from snp_tool.parsers.touchstone import TouchstoneParser
from snp_tool.parsers.component_library import ComponentLibraryParser
from snp_tool.optimizer.grid_search import GridSearchOptimizer

# Load device
parser = TouchstoneParser()
device = parser.parse("docs/examples/wifi_antenna.s2p")

# Load component library
lib_parser = ComponentLibraryParser()
library = lib_parser.parse_folder("docs/examples/")

# Optimize
optimizer = GridSearchOptimizer(device, library)
result = optimizer.optimize(
    topology="L-section",
    target_frequency=2.4e9,
)

# Print results
print(f"Success: {result.success}")
print(f"VSWR: {result.optimization_metrics['vswr_at_center']:.2f}")
print(f"Components: {len(result.matching_network.components)}")
```

## Expected Results

For the WiFi antenna example with L-section matching:

| Metric | Before | After |
|--------|--------|-------|
| Impedance | 35 - j25 Ω | ~50 Ω |
| VSWR | 2.08 | < 1.5 |
| Return Loss | 9 dB | > 20 dB |

## Troubleshooting

If optimization fails:
1. Check frequency coverage - components must cover device frequency range
2. Try different topology (Pi-section for better bandwidth)
3. Add more components to the library
