# T066: API Reference

## Overview

The RF Impedance Matching Tool provides a Python API for programmatic access to all functionality.

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from snp_tool.parsers.touchstone import TouchstoneParser
from snp_tool.parsers.component_library import ComponentLibraryParser
from snp_tool.optimizer.grid_search import GridSearchOptimizer

# Load device
device = TouchstoneParser().parse("device.s2p")

# Load library
library = ComponentLibraryParser().parse_folder("./components")

# Optimize
result = GridSearchOptimizer(device, library).optimize(topology="L-section")
```

---

## Parsers

### TouchstoneParser

Parses Touchstone (.snp, .s1p, .s2p, .s3p, ...) files.

```python
from snp_tool.parsers.touchstone import TouchstoneParser

parser = TouchstoneParser()
snp_file = parser.parse(
    file_path: str | Path,
    port_mapping: tuple[int, int] | None = None
) -> SNPFile
```

**Parameters**:
- `file_path`: Path to Touchstone file
- `port_mapping`: For multi-port files, select 2-port subnetwork (optional)

**Returns**: `SNPFile` object

**Example**:
```python
# Load 2-port file
device = parser.parse("antenna.s2p")

# Load 3-port file, extract ports 0→2
device = parser.parse("filter.s3p", port_mapping=(0, 2))
```

---

### ComponentLibraryParser

Parses a folder of component S-parameter files.

```python
from snp_tool.parsers.component_library import ComponentLibraryParser

parser = ComponentLibraryParser()
library = parser.parse_folder(
    folder_path: str | Path,
    recursive: bool = True
) -> ComponentLibrary
```

**Parameters**:
- `folder_path`: Path to folder containing .s2p files
- `recursive`: Search subdirectories (default: True)

**Returns**: `ComponentLibrary` object

**Example**:
```python
library = parser.parse_folder("./murata_components")
print(f"Loaded {len(library)} components")
```

---

## Models

### SNPFile

Container for S-parameter data.

```python
from snp_tool.models.snp_file import SNPFile
```

**Attributes**:
- `frequencies: np.ndarray` - Frequency points (Hz)
- `s_parameters: np.ndarray` - S-parameter matrix [freq, port, port]
- `num_ports: int` - Number of ports
- `reference_impedance: float` - Reference impedance (default: 50Ω)
- `file_path: str | None` - Source file path

**Properties**:
- `frequency_range: tuple[float, float]` - (min_freq, max_freq) in Hz
- `center_frequency: float` - Center of frequency range
- `impedance_at_center: complex` - Impedance at center frequency
- `vswr_at_center: float` - VSWR at center frequency

**Methods**:
```python
def impedance_at_frequency(freq: float) -> complex
def s11_at_frequency(freq: float) -> complex
```

---

### ComponentModel

Single component (capacitor or inductor).

```python
from snp_tool.models.component import ComponentModel, ComponentType
```

**Attributes**:
- `s2p_file_path: str` - Source file path
- `manufacturer: str` - Manufacturer name
- `part_number: str` - Part number
- `component_type: ComponentType` - CAPACITOR or INDUCTOR
- `value: str | None` - Nominal value (e.g., "10pF")
- `frequency: np.ndarray` - Frequency points
- `s_parameters: np.ndarray` - S-parameter data

**Methods**:
```python
def validate_frequency_coverage(device_frequencies: np.ndarray) -> bool
def impedance_at_frequency(freq: float) -> complex
```

---

### ComponentLibrary

Catalog of components with search and filtering.

```python
from snp_tool.models.component_library import ComponentLibrary
```

**Methods**:
```python
def search(query: str) -> list[ComponentModel]
def get_by_type(component_type: str) -> list[ComponentModel]
def validate_frequency_coverage(
    frequencies: np.ndarray
) -> tuple[list[ComponentModel], list[ComponentModel]]
```

**Example**:
```python
# Search
caps = library.search("capacitor 10pF")

# Get by type
inductors = library.get_by_type("inductor")

# Filter by frequency
valid, invalid = library.validate_frequency_coverage(device.frequencies)
```

---

### MatchingNetwork

Cascaded matching network.

```python
from snp_tool.models.matching_network import MatchingNetwork, Topology
```

**Attributes**:
- `components: list[ComponentModel]` - Components in network
- `topology: Topology` - L_SECTION, PI_SECTION, or T_SECTION
- `component_order: list[str]` - Connection order (e.g., ["series", "shunt"])
- `frequency: np.ndarray` - Frequency points
- `cascaded_s_parameters: dict` - Cascaded S-parameters

**Properties**:
- `s11: np.ndarray` - Input reflection coefficient vs frequency

**Methods**:
```python
def reflection_coefficient_at_frequency(freq: float) -> float
def vswr_at_frequency(freq: float) -> float
def return_loss_db_at_frequency(freq: float) -> float
def impedance_at_frequency(freq: float) -> complex
def get_schematic_text() -> str
```

---

### OptimizationResult

Complete optimization solution.

```python
from snp_tool.models.optimization_result import OptimizationResult
```

**Attributes**:
- `matching_network: MatchingNetwork` - Optimized network
- `main_device: SNPFile` - Input device
- `topology_selected: Topology` - Selected topology
- `success: bool` - Whether optimization met criteria
- `optimization_metrics: dict` - Performance metrics
- `error_message: str` - Error description if failed
- `combinations_evaluated: int` - Number of combinations tested

**Methods**:
```python
def export_schematic(path: str) -> str
def export_s_parameters(path: str) -> str
def to_dict() -> dict
```

**Metrics dictionary**:
```python
{
    "reflection_coefficient_at_center": 0.05,
    "vswr_at_center": 1.10,
    "return_loss_at_center_dB": 26.0,
    "impedance_at_center": (48.5+2.3j),
    "max_vswr_in_band": 1.25,
    "min_vswr_in_band": 1.05,
}
```

---

## Optimizer

### GridSearchOptimizer

Brute-force grid search optimizer.

```python
from snp_tool.optimizer.grid_search import GridSearchOptimizer
```

**Constructor**:
```python
optimizer = GridSearchOptimizer(
    device: SNPFile,
    component_library: ComponentLibrary,
    config: GridSearchConfig | None = None
)
```

**Methods**:
```python
def optimize(
    topology: str | Topology = "L-section",
    frequency_range: tuple[float, float] | None = None,
    target_frequency: float | None = None
) -> OptimizationResult
```

**Example**:
```python
optimizer = GridSearchOptimizer(device, library)

# Single-frequency optimization
result = optimizer.optimize(
    topology="L-section",
    target_frequency=2.4e9
)

# Bandwidth optimization
result = optimizer.optimize(
    topology="Pi-section",
    frequency_range=(2.0e9, 2.8e9)
)
```

---

## Visualization

### SmithChartPlotter

Static Smith Chart plots.

```python
from snp_tool.visualization.smith_chart import SmithChartPlotter
```

**Methods**:
```python
def plot_impedance_trajectory(
    snp_file: SNPFile,
    title: str = "Impedance Trajectory"
) -> matplotlib.Figure

def plot_comparison(
    before: SNPFile,
    after: MatchingNetwork,
    title: str = "Before vs After Matching"
) -> matplotlib.Figure

def save_figure(fig: Figure, path: str) -> str
```

**Example**:
```python
plotter = SmithChartPlotter()
fig = plotter.plot_impedance_trajectory(device)
plotter.save_figure(fig, "smith_chart.png")
```

---

## Metrics

### RF Calculations

```python
from snp_tool.optimizer.metrics import (
    reflection_coefficient,
    vswr,
    return_loss_db,
    impedance_from_s11,
    calculate_vswr,
)
```

**Functions**:
```python
def reflection_coefficient(
    impedance: complex,
    reference_impedance: float = 50.0
) -> float

def vswr(
    impedance: complex,
    reference_impedance: float = 50.0
) -> float

def return_loss_db(
    impedance: complex,
    reference_impedance: float = 50.0
) -> float

def impedance_from_s11(
    s11: complex,
    reference_impedance: float = 50.0
) -> complex

def calculate_vswr(s11_magnitude: float) -> float
```

---

## Exceptions

```python
from snp_tool.utils.exceptions import (
    SNPToolError,           # Base exception
    TouchstoneFormatError,  # Invalid file format
    FrequencyGapError,      # Component frequency coverage issue
    InvalidPortMappingError,# Invalid port mapping
    ComponentNotFoundError, # Component search failed
    OptimizationError,      # Optimization failed
    ExportError,            # Export operation failed
)
```

All exceptions include context information for debugging:
```python
try:
    parser.parse("bad_file.s2p")
except TouchstoneFormatError as e:
    print(f"Error: {e.message}")
    print(f"File: {e.context.get('file')}")
    print(f"Line: {e.context.get('line')}")
```

---

## Logging

```python
from snp_tool.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging(level="DEBUG", log_file="debug.log")

# Get logger in your code
logger = get_logger()
logger.info("Starting optimization", target_freq="2.4 GHz")
```
