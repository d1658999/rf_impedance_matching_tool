# SNP Tool - RF Impedance Matching Optimization

A Python tool for RF engineers to load vendor S-parameter design kits and automatically optimize impedance matching networks using grid search.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Load S-parameter files**: Parse Touchstone format (.s1p, .s2p, .s3p, .s4p) with support for multi-port extraction
- **Import vendor libraries**: Index component libraries from Murata, TDK, and other vendors
- **Automatic optimization**: Grid search algorithm finds optimal matching networks
- **Flexible topologies**: L-section, Pi-section, T-section matching networks
- **RF metrics**: VSWR, return loss, reflection coefficient calculations
- **Export results**: Schematic text files and cascaded S2P files

## Installation

### From Source

```bash
git clone https://github.com/yourorg/rf_impedance_matching_tool.git
cd rf_impedance_matching_tool

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install with dependencies
pip install -e ".[dev]"
```

### Dependencies

- Python 3.9+
- numpy
- scikit-rf (S-parameter parsing)
- matplotlib (visualization)
- PyQt6 (optional, for GUI)

## Quick Start

### GUI Mode (Recommended for Interactive Use)

```bash
# Install with GUI dependencies
pip install -e ".[gui]"

# Launch the GUI
snp-tool-gui
```

**GUI Features:**
- **File Menu → Open Device SNP**: Load your main device .s2p/.snp file
- **File Menu → Import Component Library**: Select a folder containing vendor .s2p files
- **Optimization Panel**: Select topology (L/Pi/T-section) and click "Optimize"
- **Smith Chart**: Interactive visualization with before/after comparison
- **Results Table**: View VSWR, return loss, and selected components
- **File Menu → Export Results**: Save schematic and cascaded S2P file

### CLI Usage

```bash
# Load and view a device S-parameter file
snp-tool --load device.s2p

# Import a component library
snp-tool --load device.s2p --library components/

# Run automatic matching optimization
snp-tool --load device.s2p --library components/ --optimize

# Specify topology and frequency range
snp-tool --load device.s2p --library components/ --optimize \
    --topology L-section \
    --frequency-range 2.0G 2.5G \
    --target-frequency 2.25G

# Export results
snp-tool --load device.s2p --library components/ --optimize \
    --export-schematic result.txt \
    --export-s2p cascaded.s2p

# Multi-port files: specify port mapping
snp-tool --load device.s3p --port-mapping 0 2 --library components/ --optimize
```

### Python API

```python
from snp_tool import parse, parse_folder, GridSearchOptimizer, Topology

# Load device
device = parse("device.s2p")
print(f"Center frequency: {device.center_frequency / 1e9:.3f} GHz")
print(f"Impedance at center: {device.impedance_at_frequency(device.center_frequency)}")

# Load component library
library = parse_folder("components/")
print(f"Loaded {library.num_components} components")
print(f"  Capacitors: {library.num_capacitors}")
print(f"  Inductors: {library.num_inductors}")

# Search components
caps = library.search("capacitor 10pF")
for cap in caps:
    print(f"  {cap.manufacturer} {cap.part_number}")

# Run optimization
optimizer = GridSearchOptimizer(device, library)
result = optimizer.optimize(topology=Topology.L_SECTION)

# Check result
if result.success:
    print("✓ Optimization successful!")
    print(f"VSWR at center: {result.optimization_metrics['vswr_at_center']:.3f}")
    
    # Export
    result.export_schematic("result.txt")
    result.export_s_parameters("cascaded.s2p")
```

## Supported File Formats

### Touchstone Files

- `.s1p` - 1-port S-parameters
- `.s2p` - 2-port S-parameters
- `.s3p` - 3-port S-parameters (with port mapping)
- `.s4p` - 4-port S-parameters (with port mapping)

Supported data formats:
- Magnitude/Angle (MA)
- Real/Imaginary (RI)
- dB/Angle (DB)

### Component Libraries

Place vendor `.s2p` files in a folder. The tool will:
1. Parse all `.s2p` files
2. Extract metadata from filenames (manufacturer, type, value)
3. Infer component type from S-parameters if not in filename
4. Build searchable index by type and value

Example folder structure:
```
components/
├── Murata/
│   ├── GRM_CAP_10pF.s2p
│   ├── GRM_CAP_22pF.s2p
│   └── ...
└── TDK/
    ├── MLK_IND_1nH.s2p
    ├── MLK_IND_2.2nH.s2p
    └── ...
```

## Matching Topologies

### L-Section (Series-Shunt)
```
Source ──[C/L]──┬──[C/L]──┴── 50Ω Load
                │
                GND
```

### Pi-Section (Shunt-Series)
```
Source ──┬──[C/L]──┬── 50Ω Load
         │         │
        [C/L]     [C/L]
         │         │
        GND       GND
```

### T-Section (Series-Shunt-Series)
```
Source ──[C/L]──┬──[C/L]── 50Ω Load
                │
               [C/L]
                │
               GND
```

## Development

### Running Tests

```bash
make test          # Run all tests
make coverage      # Run with coverage report
make lint          # Run linting (flake8 + black)
make format        # Format code with black
```

### Project Structure

```
src/snp_tool/
├── models/           # Data entities (SNPFile, Component, MatchingNetwork)
├── parsers/          # Touchstone and library parsing
├── optimizer/        # Grid search and ABCD cascading
├── visualization/    # Smith Chart plotting (WIP)
├── gui/              # PyQt6 GUI (P2)
└── utils/            # Logging, exceptions
```

## Roadmap

### MVP (Phase 1) ✅
- [x] Touchstone file parsing
- [x] Component library indexing
- [x] Grid search optimization
- [x] CLI interface
- [x] Export functionality

### Phase 2 (Enhancements) ✅
- [x] Interactive Smith Chart GUI (PyQt6)
- [x] Bandwidth optimization
- [x] Performance tuning

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Run `make lint` and `make test`
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [scikit-rf](https://scikit-rf.org/) - RF/Microwave network analysis
- [matplotlib](https://matplotlib.org/) - Visualization
- RF engineering community for design kit standards
