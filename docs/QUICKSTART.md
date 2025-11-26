# RF Impedance Matching Tool - Quick Start Guide

This guide covers the essential steps to get started with the RF impedance matching tool.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd rf_impedance_matching_tool

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## CLI Usage

### Load and View a Device SNP File

```bash
# Load a 2-port device file
python -m snp_tool --load device.s2p

# Load a multi-port file with port mapping
python -m snp_tool --load device.s3p --port-mapping 0 2
```

### Import Component Library

```bash
# Import a folder of vendor component .s2p files
python -m snp_tool --library ./murata_design_kit/
```

### Optimize Matching Network

```bash
# Basic optimization with L-section topology
python -m snp_tool --load device.s2p --library ./components/ --optimize

# Specify topology
python -m snp_tool --load device.s2p --library ./components/ --optimize --topology Pi-section

# Specify frequency range (in Hz)
python -m snp_tool --load device.s2p --library ./components/ --optimize \
    --frequency-range 2.4e9 2.5e9
```

### Full Workflow Example

```bash
python -m snp_tool \
    --load tests/fixtures/sample_device.s2p \
    --library tests/fixtures/sample_components/ \
    --optimize \
    --topology L-section \
    --output results/
```

## Python API Usage

### Load and Parse SNP Files

```python
from snp_tool.parsers.touchstone import parse_touchstone

# Load a device
device = parse_touchstone("device.s2p")

# Access data
print(f"Ports: {device.num_ports}")
print(f"Frequency range: {device.frequency.min()/1e9:.2f} - {device.frequency.max()/1e9:.2f} GHz")
print(f"Center frequency: {device.center_frequency/1e9:.2f} GHz")

# Get impedance at specific frequency
z = device.impedance_at_frequency(2.4e9)
print(f"Impedance at 2.4 GHz: {z.real:.1f} + {z.imag:.1f}j Ω")
```

### Import Component Library

```python
from snp_tool.parsers.component_library import parse_component_folder

# Import component library
library = parse_component_folder("./vendor_components/")

# Search for components
caps = library.search("capacitor 10pF")
inds = library.get_inductors()

print(f"Found {len(caps)} matching capacitors")
print(f"Total inductors: {len(inds)}")
```

### Optimize Matching Network

```python
from snp_tool.parsers.touchstone import parse_touchstone
from snp_tool.parsers.component_library import parse_component_folder
from snp_tool.optimizer.grid_search import GridSearchOptimizer

# Load device and library
device = parse_touchstone("device.s2p")
library = parse_component_folder("./components/")

# Create optimizer and run
optimizer = GridSearchOptimizer(device, library)
result = optimizer.optimize(topology="L-section")

# Check results
if result.success:
    print("Optimization successful!")
    print(f"VSWR at center: {result.optimization_metrics['vswr_at_center']:.3f}")
    print(f"Return loss: {result.optimization_metrics['return_loss_at_center_dB']:.1f} dB")
    
    # Get selected components
    for comp in result.matching_network.components:
        print(f"  - {comp.part_number}: {comp.value}")
else:
    print("Optimization did not meet target")
```

### Bandwidth Optimization

```python
from snp_tool.optimizer.bandwidth_optimizer import BandwidthOptimizer

# For wide-band matching
optimizer = BandwidthOptimizer(device, library)
result = optimizer.optimize(
    topology="Pi-section",
    frequency_range=(2.4e9, 2.5e9),
    vswr_target=2.0
)

print(f"Max VSWR in band: {result.optimization_metrics['max_vswr_in_band']:.3f}")
print(f"Bandwidth (VSWR<2): {result.optimization_metrics['bandwidth_hz']/1e6:.1f} MHz")
```

### Export Results

```python
# Export schematic
result.export_schematic("matching_network.txt")

# Export cascaded S-parameters
result.export_s_parameters("matched_device.s2p")
```

### Smith Chart Visualization

```python
from snp_tool.visualization.smith_chart import SmithChartPlotter, plot_smith_chart

# Quick plot
fig = plot_smith_chart(device, title="Device Impedance", colormap="viridis")
fig.savefig("smith_chart.png")

# Custom plotting
plotter = SmithChartPlotter(reference_impedance=50.0)
fig, ax = plotter.create_figure()

# Plot original device
plotter.plot_impedance_trajectory(device, ax=ax, color="blue", label="Original")

# Plot matched device (if available)
if result.success:
    plotter.plot_comparison(device, result.matching_network, ax=ax)

ax.legend()
fig.savefig("comparison.png")
```

## GUI Mode (Optional)

If PyQt6 is installed, you can use the graphical interface:

```bash
# Install PyQt6
pip install PyQt6

# Run GUI
python -m snp_tool.gui
```

The GUI provides:
- File browser for loading device and library
- Topology selection dropdown
- Real-time Smith Chart visualization
- Results table with metrics
- Export functionality

## Common Workflows

### RF Engineer Matching Workflow

1. **Load main device** - The PA, LNA, or antenna to be matched
2. **Import vendor library** - Murata, TDK, or other design kit .s2p files
3. **Select topology** - L-section (2 components), Pi/T-section (3 components)
4. **Run optimization** - Grid search finds optimal component combination
5. **Verify results** - Check VSWR, return loss, Smith Chart
6. **Export** - Save schematic and S-parameters for simulation

### Typical Results

For a well-designed matching network:
- VSWR at center frequency: < 1.5 (good), < 2.0 (acceptable)
- Return loss: > 15 dB (good), > 10 dB (acceptable)
- Impedance: 50Ω ± 10Ω at center frequency

## Troubleshooting

### "No components found with frequency coverage"
- Ensure component .s2p files cover the device frequency range
- Check that component files are valid Touchstone format

### Optimization takes too long
- Reduce component library size
- Use L-section topology (fewer combinations)
- Limit frequency range for optimization

### Poor matching results
- Try different topologies (Pi-section often better for bandwidth)
- Check if source impedance is far from 50Ω (may need multi-stage matching)
- Verify component frequency coverage matches device
