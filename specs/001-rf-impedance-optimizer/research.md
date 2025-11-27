# Research & Technology Decisions: RF Impedance Matching Optimizer

**Phase**: 0 (Research & Technology Foundation)  
**Date**: 2025-11-27  
**Status**: Complete

## Overview

This document resolves all NEEDS CLARIFICATION items from the Technical Context section of plan.md and establishes technology foundation for implementation.

---

## 1. Optimization Algorithm Selection

### Decision: scipy.optimize.differential_evolution with custom multi-objective wrapper

### Context
Need to optimize weighted combination of:
- Return loss (minimize reflection coefficient)
- VSWR (minimize voltage standing wave ratio)
- Bandwidth (maximize frequency range meeting impedance target)
- Component count (minimize for simplicity/cost)

Constraints:
- Max 5 components per port
- Component values from E12/E24/E96 series (standard mode) or continuous (ideal mode)
- Physical realizability (1pF-100uF caps, 1nH-100mH inductors)

### Alternatives Considered

| Algorithm | Pros | Cons | Verdict |
|-----------|------|------|---------|
| **scipy.optimize.differential_evolution** | Global optimizer, handles non-linear problems, good for discrete search spaces, built-in constraint handling | May be slow for high-dimensional problems | ✅ **Selected** |
| scipy.optimize.minimize (SLSQP) | Fast for smooth problems, gradient-based | Requires continuous values, may get stuck in local minima | ❌ Poor for discrete component selection |
| Genetic Algorithm (DEAP library) | Excellent for multi-objective, handles discrete values naturally | Additional dependency, more complex setup | ❌ Adds dependency |
| Particle Swarm (pyswarm) | Good for continuous problems | Less effective for discrete component selection | ❌ Not optimal for E-series |

### Rationale

**differential_evolution** provides:
1. **Global search**: Avoids local minima common in RF matching optimization
2. **Constraint handling**: Built-in bounds and constraint functions for max 5 components, value ranges
3. **No gradient required**: Impedance matching landscape is non-smooth (discrete component changes cause discontinuities)
4. **Scipy integration**: Already a project dependency (no new libs)

**Implementation Strategy**:
```python
from scipy.optimize import differential_evolution

def objective_function(component_values, weights, network, target_impedance):
    """
    Multi-metric weighted objective function.
    
    Args:
        component_values: Flat array of component values and types
        weights: Dict of metric weights (return_loss, vswr, bandwidth, component_count)
        network: SParameterNetwork object
        target_impedance: Target impedance (e.g., 50 ohms)
    
    Returns:
        Weighted scalar cost (minimize)
    """
    # Decode component_values into MatchingComponent objects
    components = decode_components(component_values)
    
    # Apply components to network
    modified_network = apply_components(network, components)
    
    # Calculate metrics
    return_loss = calculate_return_loss(modified_network, target_impedance)
    vswr = calculate_vswr(modified_network, target_impedance)
    bandwidth = calculate_bandwidth(modified_network, target_impedance, threshold=-10)  # dB
    component_count = len(components)
    
    # Weighted combination (lower is better)
    cost = (
        weights['return_loss'] * return_loss +
        weights['vswr'] * (vswr - 1.0) +  # VSWR=1 is ideal
        weights['bandwidth'] * (1.0 / (bandwidth + 1e-9)) +  # Higher BW = lower cost
        weights['component_count'] * component_count
    )
    
    return cost

# For standard component mode (E12/E24/E96):
def snap_to_standard_series(value, series='E24'):
    """Snap continuous value to nearest standard component value."""
    e_series = get_e_series_values(series)
    return min(e_series, key=lambda x: abs(x - value))

# Optimize
result = differential_evolution(
    objective_function,
    bounds=component_bounds,  # [(min_val, max_val) for each component]
    args=(weights, network, target_impedance),
    maxiter=1000,
    popsize=15,
    strategy='best1bin',
    mutation=(0.5, 1.0),
    recombination=0.7
)
```

**Performance Target**: <30 seconds for single-port matching with up to 2 components (SC-004)

**Validation Approach**: Performance benchmark tests comparing against brute-force search on small problems (2-3 components) to verify solution quality.

---

## 2. Scipy Version and Integration

### Decision: scipy>=1.9.0

### Context
- Optimization engine depends on scipy.optimize.differential_evolution
- Must integrate with numpy>=1.21.0 and scikit-rf>=0.29.0

### Version Compatibility Matrix

| scipy | numpy | scikit-rf | Python | Notes |
|-------|-------|-----------|--------|-------|
| 1.9.0 | >=1.21 | >=0.29 | 3.9-3.11 | ✅ Compatible, differential_evolution stable |
| 1.10.0 | >=1.21 | >=0.29 | 3.9-3.12 | ✅ Latest stable, improved optimizer performance |
| 1.11.0 | >=1.23 | >=0.29 | 3.9-3.12 | ✅ Newest, may have minor API changes |

### Rationale
- **scipy 1.9.0**: Minimum version with stable differential_evolution API
- **scipy 1.10.0+**: Recommended for performance improvements in optimization
- No breaking changes in scipy.optimize between 1.9-1.11 for our use case

### Dependency Specification
Add to `pyproject.toml`:
```toml
dependencies = [
    "numpy>=1.21.0",
    "scipy>=1.9.0",  # For optimization algorithms
    "scikit-rf>=0.29.0",
    "matplotlib>=3.5.0",
]
```

### Integration Notes
- scikit-rf uses scipy for some internal calculations (compatible with scipy>=1.9)
- No conflicts between numpy/scipy/scikit-rf in specified version ranges
- All packages support Python 3.9-3.12

---

## 3. Structured Logging Strategy

### Decision: Python standard logging with JSON formatter via python-json-logger

### Context
Constitution requires observability/debuggability for:
- Optimization convergence tracking
- S-parameter transformation decisions
- Component cascading calculations
- Error diagnostics

### Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Standard logging + python-json-logger** | Minimal dependency, flexible, production-ready | Requires wrapper for convenience | ✅ **Selected** |
| structlog | Rich features, context binding | Additional dependency | ❌ Overkill for scope |
| Custom JSON logging | No dependencies | Reinventing wheel | ❌ Not pragmatic |

### Implementation

**Add dependency**:
```toml
dependencies = [
    "python-json-logger>=2.0.0",  # JSON log formatting
]
```

**Logging Module** (`src/snp_tool/utils/logging.py`):
```python
import logging
from pythonjsonlogger import jsonlogger

def setup_logger(name: str, level: str = 'INFO', json_format: bool = False) -> logging.Logger:
    """
    Configure structured logger.
    
    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, output JSON; else human-readable
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    handler = logging.StreamHandler()
    
    if json_format:
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Usage in optimizer
logger = setup_logger('snp_tool.optimizer', level='DEBUG', json_format=True)

logger.info('Starting optimization', extra={
    'port': 1,
    'target_impedance': 50.0,
    'weights': {'return_loss': 0.7, 'bandwidth': 0.2, 'component_count': 0.1}
})

logger.debug('Optimization iteration', extra={
    'iteration': 42,
    'best_cost': 0.123,
    'components': [{'type': 'capacitor', 'value': '10pF', 'placement': 'series'}]
})
```

**Log Format**:
- **Human-readable** (default for CLI): `2025-11-27 12:34:56 - snp_tool.optimizer - INFO - Starting optimization`
- **JSON** (for automation/parsing):
```json
{
  "asctime": "2025-11-27T12:34:56",
  "name": "snp_tool.optimizer",
  "levelname": "INFO",
  "message": "Starting optimization",
  "port": 1,
  "target_impedance": 50.0,
  "weights": {"return_loss": 0.7, "bandwidth": 0.2, "component_count": 0.1}
}
```

**Key Logging Points**:
1. **SNP file parsing**: validation errors, file metadata
2. **Component addition**: component details, S-parameter changes
3. **Optimization**: iteration progress, convergence criteria, final solution
4. **Export**: file paths, export format, component list

### Performance Consideration
- Logging overhead negligible for optimization (<1% time)
- JSON formatting slightly slower than text but acceptable
- CLI can use `--log-level` flag to control verbosity

---

## 4. Smith Chart Library

### Decision: Use scikit-rf built-in Smith chart plotting

### Context
FR-015 requires Smith chart visualization; matplotlib has smith chart capabilities through various approaches.

### Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **scikit-rf Network.plot_s_smith()** | Built-in, RF-focused, handles complex impedance automatically | Less customization than raw matplotlib | ✅ **Selected** |
| matplotlib-smithchart library | Dedicated Smith chart lib | Additional dependency | ❌ Unnecessary |
| Custom matplotlib polar projection | Full control | Requires manual Smith chart math (complex) | ❌ Reinventing wheel |

### Rationale
scikit-rf provides:
1. **Native Smith chart plotting**: `network.plot_s_smith()` method
2. **Automatic impedance normalization**: Handles 50Ω, 75Ω systems
3. **Matplotlib backend**: Fully customizable if needed
4. **No extra dependencies**: Already using scikit-rf

### Implementation Example
```python
import matplotlib.pyplot as plt
from skrf import Network

# Load or create network
network = Network('antenna.s2p')

# Plot S11 on Smith chart
fig, ax = plt.subplots(figsize=(8, 8))
network.plot_s_smith(m=0, n=0, ax=ax, label='Port 1 (S11)', marker='o')

# Add matching network components (after cascading)
matched_network = cascade_components(network, components)
matched_network.plot_s_smith(m=0, n=0, ax=ax, label='After Matching', marker='x')

plt.legend()
plt.title('Impedance Matching: Before vs After')
plt.grid(True, alpha=0.3)
plt.savefig('smith_chart.png', dpi=150)
plt.show()
```

**For GUI integration (PyQt6)**:
```python
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class SmithChartWidget(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        fig = Figure(figsize=(6, 6))
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
    
    def plot_network(self, network, label='Network'):
        self.ax.clear()
        network.plot_s_smith(m=0, n=0, ax=self.ax, label=label)
        self.ax.legend()
        self.draw()
```

**Additional Charts** (FR-015 rectangular plots):
- Magnitude/phase vs frequency: `network.plot_s_mag()`, `network.plot_s_deg()`
- VSWR: Custom calculation + matplotlib line plot
- Return loss: `20 * log10(abs(S11))` vs frequency

---

## 5. Session File Format

### Decision: JSON format with versioning

### Context
FR-020/FR-021 require session save/load with:
- SNP file reference (path)
- All matching components (type, value, placement, port)
- Optimization settings (weights, target impedance, frequency range)
- Current analysis results (optional, for caching)

### Alternatives Considered

| Format | Pros | Cons | Verdict |
|--------|------|------|---------|
| **JSON** | Human-readable, widely supported, easy parsing, version control friendly | Slightly verbose | ✅ **Selected** |
| YAML | More human-friendly than JSON | Requires PyYAML dependency | ❌ Unnecessary dependency |
| Pickle | Python-native, compact | Binary (not human-readable), Python-specific, version fragile | ❌ Not pragmatic |
| Custom binary | Compact, fast | Requires custom parser, not human-readable | ❌ Overengineering |

### Rationale
JSON provides:
1. **Human-readable**: Engineers can inspect/edit session files
2. **Version control friendly**: Text-based diffs
3. **Standard library**: `json` module built-in (no dependencies)
4. **Extensible**: Easy to add fields in future versions
5. **Cross-platform**: Compatible with all systems

### Session File Schema

**File: `my_design.snp-session` (custom extension for clarity)**

```json
{
  "version": "1.0",
  "created": "2025-11-27T12:34:56Z",
  "tool_version": "0.1.0",
  
  "snp_file": {
    "path": "/path/to/antenna.s2p",
    "checksum_md5": "abc123...",
    "loaded_at": "2025-11-27T12:30:00Z"
  },
  
  "network": {
    "port_count": 2,
    "frequency_range": {"min_ghz": 1.0, "max_ghz": 3.0},
    "impedance_normalization": 50.0
  },
  
  "components": [
    {
      "id": "comp_1",
      "port": 1,
      "type": "capacitor",
      "value": "10e-12",
      "value_display": "10pF",
      "placement": "series",
      "added_at": "2025-11-27T12:31:00Z"
    },
    {
      "id": "comp_2",
      "port": 1,
      "type": "inductor",
      "value": "5e-9",
      "value_display": "5nH",
      "placement": "shunt",
      "added_at": "2025-11-27T12:32:00Z"
    }
  ],
  
  "optimization": {
    "target_impedance": 50.0,
    "frequency_range": {"min_ghz": 2.0, "max_ghz": 2.5},
    "weights": {
      "return_loss": 0.7,
      "vswr": 0.0,
      "bandwidth": 0.2,
      "component_count": 0.1
    },
    "mode": "standard_values",
    "component_series": "E24",
    "last_run": "2025-11-27T12:35:00Z",
    "best_solution": {
      "components": ["comp_1", "comp_2"],
      "metrics": {
        "return_loss_db": -15.3,
        "vswr": 1.42,
        "bandwidth_mhz": 250.0
      },
      "score": 0.123
    }
  },
  
  "gui_state": {
    "selected_plot": "smith_chart",
    "zoom_level": 1.0,
    "window_geometry": {"x": 100, "y": 100, "width": 1200, "height": 800}
  }
}
```

**Version Compatibility**:
- `version` field enables migration for future schema changes
- Edge case (spec.md): Loading old version sessions → attempt migration or warn user

**Implementation** (`src/snp_tool/utils/session_io.py`):
```python
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import hashlib

SESSION_VERSION = "1.0"

def save_session(filepath: Path, session_data: Dict[str, Any]) -> None:
    """Save session to JSON file."""
    session_data['version'] = SESSION_VERSION
    session_data['saved_at'] = datetime.utcnow().isoformat() + 'Z'
    
    with open(filepath, 'w') as f:
        json.dump(session_data, f, indent=2)

def load_session(filepath: Path) -> Dict[str, Any]:
    """
    Load session from JSON file.
    
    Raises:
        FileNotFoundError: if session file doesn't exist
        ValueError: if version incompatible
    """
    with open(filepath, 'r') as f:
        session_data = json.load(f)
    
    version = session_data.get('version', '0.0')
    if version != SESSION_VERSION:
        # Attempt migration or warn
        session_data = migrate_session(session_data, from_version=version)
    
    return session_data

def compute_snp_checksum(filepath: Path) -> str:
    """Compute MD5 checksum of SNP file to detect changes."""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()
```

**Performance Target**: <3 seconds for save/load (SC-012)

---

## 6. Component Cascading Mathematics

### Decision: Use scikit-rf Network.cascade() with ABCD parameter conversion

### Context
FR-003/FR-004 require real-time S-parameter recalculation when adding series/shunt lumped elements (capacitors, inductors) to ports. Need to cascade component networks with original network.

### Mathematical Background

**Component Representations**:
- **Series element**: Z-parameter (impedance matrix)
- **Shunt element**: Y-parameter (admittance matrix)
- **Cascading**: ABCD parameters (transmission/chain parameters)

**Conversion Chain**:
1. S-parameters (network analyzer data) → ABCD parameters
2. Series component (Z) → ABCD parameters
3. Shunt component (Y) → ABCD parameters
4. Cascade ABCD matrices (matrix multiplication)
5. ABCD parameters → S-parameters (final result)

### Implementation Strategy

**Use scikit-rf**: Handles all conversions and cascading internally

```python
from skrf import Network, media
import numpy as np

def create_series_capacitor(freq_array_hz: np.ndarray, capacitance_f: float, z0: float = 50.0) -> Network:
    """
    Create series capacitor network.
    
    Args:
        freq_array_hz: Frequency points in Hz
        capacitance_f: Capacitance in Farads (e.g., 10e-12 for 10pF)
        z0: Characteristic impedance (default 50 ohms)
    
    Returns:
        Network object representing series capacitor
    """
    # Impedance of capacitor: Z = 1 / (j * 2*pi*f * C)
    omega = 2 * np.pi * freq_array_hz
    z_cap = 1.0 / (1j * omega * capacitance_f)
    
    # Create 2-port Z-matrix for series element
    # [V1]   [z_cap  z_cap ] [I1]
    # [V2] = [z_cap  z_cap ] [I2]
    z_matrix = np.zeros((len(freq_array_hz), 2, 2), dtype=complex)
    z_matrix[:, 0, 0] = z_cap
    z_matrix[:, 0, 1] = z_cap
    z_matrix[:, 1, 0] = z_cap
    z_matrix[:, 1, 1] = z_cap
    
    # Convert Z-parameters to Network
    from skrf.network import Network
    from skrf.frequency import Frequency
    
    freq_obj = Frequency.from_f(freq_array_hz / 1e9, unit='GHz')  # Convert Hz to GHz
    network = Network(frequency=freq_obj, z=z_matrix, z0=z0)
    
    return network

def create_shunt_capacitor(freq_array_hz: np.ndarray, capacitance_f: float, z0: float = 50.0) -> Network:
    """
    Create shunt capacitor network.
    
    Args:
        freq_array_hz: Frequency points in Hz
        capacitance_f: Capacitance in Farads
        z0: Characteristic impedance
    
    Returns:
        Network object representing shunt capacitor
    """
    # Admittance of capacitor: Y = j * 2*pi*f * C
    omega = 2 * np.pi * freq_array_hz
    y_cap = 1j * omega * capacitance_f
    
    # Create 2-port Y-matrix for shunt element
    # [I1]   [y_cap  -y_cap] [V1]
    # [I2] = [-y_cap  y_cap] [V2]
    y_matrix = np.zeros((len(freq_array_hz), 2, 2), dtype=complex)
    y_matrix[:, 0, 0] = y_cap
    y_matrix[:, 0, 1] = -y_cap
    y_matrix[:, 1, 0] = -y_cap
    y_matrix[:, 1, 1] = y_cap
    
    from skrf.network import Network
    from skrf.frequency import Frequency
    
    freq_obj = Frequency.from_f(freq_array_hz / 1e9, unit='GHz')
    network = Network(frequency=freq_obj, y=y_matrix, z0=z0)
    
    return network

def create_series_inductor(freq_array_hz: np.ndarray, inductance_h: float, z0: float = 50.0) -> Network:
    """Create series inductor network."""
    omega = 2 * np.pi * freq_array_hz
    z_ind = 1j * omega * inductance_h
    
    z_matrix = np.zeros((len(freq_array_hz), 2, 2), dtype=complex)
    z_matrix[:, 0, 0] = z_ind
    z_matrix[:, 0, 1] = z_ind
    z_matrix[:, 1, 0] = z_ind
    z_matrix[:, 1, 1] = z_ind
    
    from skrf.network import Network
    from skrf.frequency import Frequency
    
    freq_obj = Frequency.from_f(freq_array_hz / 1e9, unit='GHz')
    network = Network(frequency=freq_obj, z=z_matrix, z0=z0)
    
    return network

def create_shunt_inductor(freq_array_hz: np.ndarray, inductance_h: float, z0: float = 50.0) -> Network:
    """Create shunt inductor network."""
    omega = 2 * np.pi * freq_array_hz
    y_ind = 1.0 / (1j * omega * inductance_h)
    
    y_matrix = np.zeros((len(freq_array_hz), 2, 2), dtype=complex)
    y_matrix[:, 0, 0] = y_ind
    y_matrix[:, 0, 1] = -y_ind
    y_matrix[:, 1, 0] = -y_ind
    y_matrix[:, 1, 1] = y_ind
    
    from skrf.network import Network
    from skrf.frequency import Frequency
    
    freq_obj = Frequency.from_f(freq_array_hz / 1e9, unit='GHz')
    network = Network(frequency=freq_obj, y=y_matrix, z0=z0)
    
    return network

def apply_component_to_network(network: Network, component: MatchingComponent) -> Network:
    """
    Apply matching component to network by cascading.
    
    Args:
        network: Original S-parameter network
        component: MatchingComponent object (type, value, placement, port)
    
    Returns:
        New network with component applied
    """
    freq_hz = network.frequency.f  # Frequency array in Hz
    z0 = network.z0[0, 0]  # Characteristic impedance
    
    # Create component network
    if component.type == 'capacitor' and component.placement == 'series':
        comp_network = create_series_capacitor(freq_hz, component.value, z0)
    elif component.type == 'capacitor' and component.placement == 'shunt':
        comp_network = create_shunt_capacitor(freq_hz, component.value, z0)
    elif component.type == 'inductor' and component.placement == 'series':
        comp_network = create_series_inductor(freq_hz, component.value, z0)
    elif component.type == 'inductor' and component.placement == 'shunt':
        comp_network = create_shunt_inductor(freq_hz, component.value, z0)
    else:
        raise ValueError(f"Invalid component: {component}")
    
    # Cascade: original_network ** comp_network
    # scikit-rf uses ** operator for cascading
    cascaded = network ** comp_network
    
    return cascaded
```

**For multiple components on same port** (FR-003: cascaded combinations):
```python
def apply_multiple_components(network: Network, components: List[MatchingComponent]) -> Network:
    """
    Apply multiple components in sequence (cascaded).
    
    Components are applied in order: first component closest to original network.
    """
    result = network
    for component in components:
        result = apply_component_to_network(result, component)
    return result
```

**Performance Optimization**:
- scikit-rf cascading is vectorized (NumPy)
- For 1000 frequency points: ~10-50ms per component
- Total for 5 components: <250ms (well within <1 second target, SC-002)

**Validation**:
- Unit tests comparing against hand-calculated ABCD matrices
- Integration tests with known matching network examples from RF textbooks
- Numerical precision tests (ensure accuracy within 0.1 dB, SC-007)

---

## 7. PyQt6 Architecture for Dual CLI/GUI

### Decision: Model-View-Controller (MVC) pattern with shared Core layer

### Context
FR-019 requires CLI and GUI to produce identical computation results by sharing a common core engine.

### Architecture Pattern

```
┌─────────────────────────────────────────────────────┐
│                 Interface Layer                     │
│  ┌──────────────┐              ┌─────────────────┐  │
│  │  CLI Module  │              │   GUI Module    │  │
│  │  (commands)  │              │   (PyQt6 UI)    │  │
│  └──────┬───────┘              └────────┬────────┘  │
│         │                               │           │
│         └───────────┬───────────────────┘           │
│                     │                               │
├─────────────────────┼───────────────────────────────┤
│              Controller Layer                       │
│         ┌───────────▼───────────┐                   │
│         │  Application Logic    │                   │
│         │  (workflow control)   │                   │
│         └───────────┬───────────┘                   │
│                     │                               │
├─────────────────────┼───────────────────────────────┤
│                 Core Layer (Shared)                 │
│  ┌──────────────────┼────────────────────────────┐  │
│  │                  │                            │  │
│  │  ┌───────────┐   │    ┌──────────────────┐   │  │
│  │  │  Models   │   │    │  Core Engine     │   │  │
│  │  │ (entities)│   │    │  (computation)   │   │  │
│  │  └───────────┘   │    └──────────────────┘   │  │
│  │                  │                            │  │
│  │  ┌───────────────▼─────────────┐             │  │
│  │  │       Parsers               │             │  │
│  │  │  (SNP file, validation)     │             │  │
│  │  └─────────────────────────────┘             │  │
│  │                                               │  │
│  │  ┌─────────────────────────────┐             │  │
│  │  │     Optimizer               │             │  │
│  │  │  (algorithms, objectives)   │             │  │
│  │  └─────────────────────────────┘             │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Implementation Guidelines

**1. Core Layer (100% shared)**:
- `models/`: Data classes (SParameterNetwork, MatchingComponent, etc.)
- `parsers/`: SNP file parsing and validation
- `core/`: S-parameter calculations, impedance transformations
- `optimizer/`: Optimization algorithms
- **No UI dependencies**: Pure Python logic, testable independently

**2. Controller Layer**:
```python
# src/snp_tool/controller.py
class ImpedanceMatchingController:
    """
    Application controller managing workflow logic.
    Shared by CLI and GUI interfaces.
    """
    
    def __init__(self):
        self.network: Optional[SParameterNetwork] = None
        self.components: List[MatchingComponent] = []
        self.session: Optional[WorkSession] = None
    
    def load_snp_file(self, filepath: Path) -> SParameterNetwork:
        """Load and validate SNP file (FR-001)."""
        from snp_tool.parsers.touchstone import parse_snp
        self.network = parse_snp(filepath)
        return self.network
    
    def add_component(self, port: int, comp_type: str, value: float, placement: str) -> SParameterNetwork:
        """Add component and recalculate (FR-003, FR-004)."""
        from snp_tool.models.component import MatchingComponent
        from snp_tool.core.network_calc import apply_component_to_network
        
        component = MatchingComponent(
            port=port,
            type=comp_type,
            value=value,
            placement=placement
        )
        
        # Validate max 5 components per port
        port_components = [c for c in self.components if c.port == port]
        if len(port_components) >= 5:
            raise ValueError(f"Maximum 5 components per port (port {port} already has {len(port_components)})")
        
        self.components.append(component)
        self.network = apply_component_to_network(self.network, component)
        
        return self.network
    
    def optimize(self, port: int, target_impedance: float, weights: Dict[str, float], mode: str = 'ideal') -> List[OptimizationSolution]:
        """Run optimization (FR-006)."""
        from snp_tool.optimizer.engine import run_optimization
        solutions = run_optimization(
            network=self.network,
            port=port,
            target_impedance=target_impedance,
            weights=weights,
            mode=mode
        )
        return solutions
    
    def save_session(self, filepath: Path) -> None:
        """Save work session (FR-020)."""
        from snp_tool.utils.session_io import save_session
        session_data = {
            'snp_file': str(self.network.filepath),
            'components': [c.to_dict() for c in self.components],
            # ... other session data
        }
        save_session(filepath, session_data)
```

**3. CLI Interface**:
```python
# src/snp_tool/cli/commands.py
import click
from pathlib import Path
from snp_tool.controller import ImpedanceMatchingController

controller = ImpedanceMatchingController()

@click.group()
def cli():
    """RF Impedance Matching Optimizer CLI."""
    pass

@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
def load(filepath):
    """Load SNP file."""
    try:
        network = controller.load_snp_file(Path(filepath))
        click.echo(f"Loaded {network.port_count}-port network")
        click.echo(f"Frequency range: {network.frequency_range}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
@click.option('--port', type=int, required=True)
@click.option('--type', type=click.Choice(['cap', 'ind']), required=True)
@click.option('--value', type=str, required=True)
@click.option('--placement', type=click.Choice(['series', 'shunt']), required=True)
def add_component(port, type, value, placement):
    """Add matching component."""
    from snp_tool.utils.engineering import parse_engineering_notation
    value_numeric = parse_engineering_notation(value)
    
    network = controller.add_component(port, type, value_numeric, placement)
    click.echo(f"Added {type} ({value}) to port {port} ({placement})")
```

**4. GUI Interface**:
```python
# src/snp_tool/gui/mainwindow.py
from PyQt6.QtWidgets import QMainWindow
from snp_tool.controller import ImpedanceMatchingController
from snp_tool.gui.widgets.smith_chart_widget import SmithChartWidget
from snp_tool.gui.widgets.component_panel import ComponentPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Shared controller (same as CLI)
        self.controller = ImpedanceMatchingController()
        
        # UI widgets
        self.smith_chart = SmithChartWidget()
        self.component_panel = ComponentPanel()
        
        # Connect signals
        self.component_panel.component_added.connect(self.on_component_added)
        
        self.setup_ui()
    
    def on_component_added(self, port, comp_type, value, placement):
        """Handle component addition from GUI."""
        try:
            # Use same controller method as CLI
            network = self.controller.add_component(port, comp_type, value, placement)
            
            # Update visualization
            self.smith_chart.plot_network(network)
        except Exception as e:
            self.show_error_dialog(str(e))
```

**Benefits of This Architecture**:
1. **FR-019 compliance**: CLI and GUI use identical controller → identical results
2. **Testability**: Core layer tested independently of UI
3. **Maintainability**: Business logic changes propagate to both interfaces automatically
4. **Extensibility**: Future interfaces (web, API) can reuse controller

---

## 8. Engineering Notation Parsing

### Decision: Custom regex parser (no additional dependencies)

### Context
FR-005 requires parsing engineering notation (10pF, 2.2nH, 100uH, 1.5MHz) for component values and frequencies.

### Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Custom regex parser** | No dependencies, full control, lightweight | Requires validation testing | ✅ **Selected** |
| pint library | Full unit handling, dimension checking | Heavy dependency for simple use case | ❌ Overkill |

### Implementation

**Module**: `src/snp_tool/utils/engineering.py`

```python
import re
from typing import Union

# Engineering notation multipliers
MULTIPLIERS = {
    'p': 1e-12,  # pico
    'n': 1e-9,   # nano
    'u': 1e-6,   # micro (μ)
    'µ': 1e-6,   # micro (alternative)
    'm': 1e-3,   # milli
    'k': 1e3,    # kilo
    'M': 1e6,    # mega
    'G': 1e9,    # giga
}

# Unit suffixes for validation
CAPACITANCE_UNITS = ['F', 'f']  # Farad
INDUCTANCE_UNITS = ['H', 'h']   # Henry
FREQUENCY_UNITS = ['Hz', 'hz']  # Hertz

def parse_engineering_notation(value_str: str, expected_unit: str = None) -> float:
    """
    Parse engineering notation string to numeric value.
    
    Args:
        value_str: String like "10pF", "2.2nH", "1.5GHz"
        expected_unit: Optional unit validation ('F', 'H', 'Hz')
    
    Returns:
        Numeric value in base units (Farads, Henrys, Hz)
    
    Raises:
        ValueError: if parsing fails or unit mismatch
    
    Examples:
        >>> parse_engineering_notation("10pF")
        1e-11  # 10 * 1e-12
        >>> parse_engineering_notation("2.2nH")
        2.2e-9
        >>> parse_engineering_notation("100uH")
        1e-4  # 100 * 1e-6
        >>> parse_engineering_notation("1.5GHz")
        1.5e9
    """
    # Pattern: number + optional multiplier + unit
    pattern = r'^(\d+\.?\d*)\s*([pnuµmkMG]?)([A-Za-z]+)?$'
    match = re.match(pattern, value_str.strip())
    
    if not match:
        raise ValueError(f"Invalid engineering notation: '{value_str}'")
    
    number_str, multiplier, unit = match.groups()
    
    # Parse number
    try:
        number = float(number_str)
    except ValueError:
        raise ValueError(f"Invalid number in '{value_str}'")
    
    # Apply multiplier
    if multiplier:
        if multiplier not in MULTIPLIERS:
            raise ValueError(f"Unknown multiplier '{multiplier}' in '{value_str}'")
        number *= MULTIPLIERS[multiplier]
    
    # Validate unit if expected
    if expected_unit:
        if not unit:
            raise ValueError(f"Missing unit in '{value_str}' (expected {expected_unit})")
        if unit.upper() != expected_unit.upper():
            raise ValueError(f"Unit mismatch: expected {expected_unit}, got {unit}")
    
    return number

def format_engineering_notation(value: float, unit: str = '', precision: int = 2) -> str:
    """
    Format numeric value as engineering notation string.
    
    Args:
        value: Numeric value in base units
        unit: Unit suffix ('F', 'H', 'Hz')
        precision: Decimal places
    
    Returns:
        Engineering notation string
    
    Examples:
        >>> format_engineering_notation(1e-11, 'F')
        '10.00pF'
        >>> format_engineering_notation(2.2e-9, 'H')
        '2.20nH'
    """
    # Find appropriate multiplier
    for prefix, multiplier in sorted(MULTIPLIERS.items(), key=lambda x: -x[1]):
        if abs(value) >= multiplier:
            scaled = value / multiplier
            return f"{scaled:.{precision}f}{prefix}{unit}"
    
    # No multiplier needed
    return f"{value:.{precision}f}{unit}"
```

**Usage in CLI/GUI**:
```python
# Parse user input
from snp_tool.utils.engineering import parse_engineering_notation

value_str = "10pF"  # From CLI argument or GUI text field
capacitance_farads = parse_engineering_notation(value_str, expected_unit='F')
# Result: 1e-11

# Display to user
from snp_tool.utils.engineering import format_engineering_notation

capacitance = 1e-11
display = format_engineering_notation(capacitance, 'F')
# Result: "10.00pF"
```

**Error Handling**:
```python
try:
    value = parse_engineering_notation("10XF")  # Invalid multiplier
except ValueError as e:
    print(f"Error: {e}")
    # Error: Unknown multiplier 'X' in '10XF'
```

**Testing**:
- Unit tests with pytest for all valid/invalid inputs
- Edge cases: "0pF", "1000000nH" (large numbers), "0.001pF" (very small)

---

## Summary of Technology Decisions

| Decision Area | Choice | Version/Details | Rationale |
|--------------|--------|-----------------|-----------|
| **Optimization Algorithm** | scipy.optimize.differential_evolution | scipy>=1.9.0 | Global optimizer, handles discrete spaces, no extra deps |
| **Scipy Version** | scipy>=1.9.0 | Compatible with numpy>=1.21, scikit-rf>=0.29 | Stable API, optimization performance |
| **Logging** | python-json-logger | >=2.0.0 | Structured JSON logs, minimal dependency |
| **Smith Chart** | scikit-rf built-in plotting | Via Network.plot_s_smith() | No extra deps, RF-focused |
| **Session Format** | JSON with versioning | Standard library json module | Human-readable, version control friendly |
| **Component Cascading** | scikit-rf Network.cascade() | ABCD parameter conversion | Proven, vectorized, accurate |
| **Architecture** | MVC with shared Core | Controller pattern | FR-019 compliance (identical results) |
| **Engineering Notation** | Custom regex parser | No dependencies | Lightweight, full control |

---

## Dependencies Update

**Add to `pyproject.toml`**:
```toml
dependencies = [
    "numpy>=1.21.0",
    "scipy>=1.9.0",              # For optimization algorithms
    "scikit-rf>=0.29.0",
    "matplotlib>=3.5.0",
    "python-json-logger>=2.0.0", # For structured logging
]
```

**Total New Dependencies**: 2 (scipy, python-json-logger)
- scipy: Essential for optimization (core feature)
- python-json-logger: Minimal, improves observability (constitution requirement)

**No additional dependencies** for Smith charts, session files, engineering notation, or architecture (all use standard library or existing deps).

---

## Next Steps

1. ✅ **Phase 0 Complete**: All technology decisions documented
2. ➡️ **Phase 1**: Proceed to data model design (data-model.md)
3. ➡️ **Phase 1**: Define API contracts (contracts/)
4. ➡️ **Phase 1**: Write quickstart guide (quickstart.md)
5. ➡️ **Phase 1**: Update agent context with new technologies

**Gate Status**: Ready to proceed to Phase 1 design
