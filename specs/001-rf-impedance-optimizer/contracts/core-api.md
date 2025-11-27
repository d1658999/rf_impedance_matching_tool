# Core Computation Engine API Contract

**Version**: 1.0  
**Date**: 2025-11-27  
**Purpose**: Define core computation engine API shared by CLI and GUI interfaces

---

## Module: snp_tool.parsers.touchstone

### parse_snp()

**Purpose**: Parse Touchstone SNP file with validation (FR-001, FR-012)

**Signature**:
```python
def parse_snp(filepath: Path) -> SParameterNetwork:
    """
    Parse Touchstone SNP file and create SParameterNetwork object.
    
    Args:
        filepath: Path to SNP file (absolute or relative)
    
    Returns:
        SParameterNetwork object with loaded data
    
    Raises:
        FileNotFoundError: if file does not exist
        ValidationError: if file format invalid (includes detailed report)
    
    Performance:
        <5 seconds for files with up to 10,000 frequency points (SC-001)
    """
```

**Implementation Notes**:
- Uses scikit-rf Network.from_touchstone() for parsing
- Custom validation layer wraps scikit-rf to generate detailed error reports (FR-012)
- Validates: frequency monotonicity, S-parameter matrix completeness, passive network constraints
- Handles all Touchstone format variations (RI, MA, DB; Hz, MHz, GHz)

**Example**:
```python
from pathlib import Path
from snp_tool.parsers.touchstone import parse_snp

network = parse_snp(Path("antenna.s2p"))
print(f"Loaded {network.port_count}-port network")
print(f"Frequency range: {network.frequencies[0]/1e9:.2f} - {network.frequencies[-1]/1e9:.2f} GHz")
```

---

## Module: snp_tool.parsers.validator

### validate_snp_file()

**Purpose**: Validate SNP file and generate detailed error report (FR-012)

**Signature**:
```python
from dataclasses import dataclass
from typing import List

@dataclass
class ValidationError:
    line_number: int
    column: Optional[int]
    error_type: str
    message: str
    suggested_fix: str

@dataclass
class ValidationReport:
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    
    def to_string(self) -> str:
        """Format as human-readable report."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Format as JSON for CLI --json output."""

def validate_snp_file(filepath: Path) -> ValidationReport:
    """
    Validate SNP file format and content.
    
    Args:
        filepath: Path to SNP file
    
    Returns:
        ValidationReport with detailed error locations and suggestions
    
    Examples of detected errors:
        - Missing frequency points
        - Non-numeric values in data columns
        - S-parameter magnitude > 1.0 (passive violation)
        - Inconsistent port count
        - Invalid frequency units
    """
```

---

## Module: snp_tool.core.network_calc

### add_component()

**Purpose**: Add matching component to network and recalculate S-parameters (FR-003, FR-004)

**Signature**:
```python
def add_component(
    network: SParameterNetwork,
    component: MatchingComponent
) -> SParameterNetwork:
    """
    Cascade matching component to network and recalculate S-parameters.
    
    Args:
        network: Current S-parameter network
        component: MatchingComponent (type, value, placement, port)
    
    Returns:
        New SParameterNetwork with component applied
    
    Raises:
        ValueError: if component invalid (negative value, port out of range)
        ComponentLimitError: if port already has 5 components
    
    Performance:
        <1 second for up to 1000 frequency points (SC-002, FR-004)
    
    Implementation:
        1. Create 2-port network representing component (Z or Y parameters)
        2. Convert to S-parameters with same frequency array as network
        3. Cascade using scikit-rf Network.cascade() (ABCD matrix multiplication)
        4. Return new network object (immutable operation)
    """
```

**Example**:
```python
from snp_tool.core.network_calc import add_component
from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType

# Create component
cap = MatchingComponent(
    id="comp_1",
    port=1,
    component_type=ComponentType.CAPACITOR,
    value=10e-12,  # 10pF
    placement=PlacementType.SERIES,
    created_at=datetime.utcnow(),
    order=0
)

# Apply to network
modified_network = add_component(original_network, cap)
```

---

### apply_multiple_components()

**Purpose**: Apply multiple cascaded components (FR-003)

**Signature**:
```python
def apply_multiple_components(
    network: SParameterNetwork,
    components: List[MatchingComponent]
) -> SParameterNetwork:
    """
    Apply multiple components in cascade order.
    
    Args:
        network: Original network
        components: List of components (must be sorted by 'order' field)
    
    Returns:
        Network with all components cascaded
    
    Note:
        Components are applied in order: components[0] closest to original network,
        components[-1] closest to port termination.
    """
```

---

## Module: snp_tool.core.impedance

### calculate_impedance()

**Purpose**: Calculate input impedance from S-parameters

**Signature**:
```python
def calculate_impedance(
    s_parameters: np.ndarray,
    port: int,
    z0: float = 50.0
) -> complex:
    """
    Calculate input impedance at port from S-parameters.
    
    Args:
        s_parameters: S-parameter matrix (complex, shape [port_count, port_count])
        port: Port number (0-indexed for matrix access)
        z0: Characteristic impedance (default 50 ohms)
    
    Returns:
        Complex impedance (Z = R + jX)
    
    Formula:
        Z = z0 * (1 + S11) / (1 - S11)  # For port 1 (S11 is reflection coefficient)
    """
```

---

### calculate_vswr()

**Purpose**: Calculate VSWR from impedance or reflection coefficient

**Signature**:
```python
def calculate_vswr(
    impedance: Optional[complex] = None,
    reflection_coeff: Optional[complex] = None,
    z0: float = 50.0
) -> float:
    """
    Calculate Voltage Standing Wave Ratio.
    
    Args:
        impedance: Input impedance (provide either this or reflection_coeff)
        reflection_coeff: Reflection coefficient Gamma (alternative input)
        z0: Characteristic impedance
    
    Returns:
        VSWR (1.0 = perfect match, >1.0 = mismatch)
    
    Formula:
        Gamma = (Z - z0) / (Z + z0)
        VSWR = (1 + |Gamma|) / (1 - |Gamma|)
    """
```

---

### calculate_return_loss()

**Purpose**: Calculate return loss in dB

**Signature**:
```python
def calculate_return_loss(
    impedance: Optional[complex] = None,
    reflection_coeff: Optional[complex] = None,
    z0: float = 50.0
) -> float:
    """
    Calculate return loss in dB.
    
    Args:
        impedance: Input impedance (provide either this or reflection_coeff)
        reflection_coeff: Reflection coefficient Gamma
        z0: Characteristic impedance
    
    Returns:
        Return loss in dB (positive value, higher is better)
        e.g., -10 dB return loss → 10 dB improvement
    
    Formula:
        RL = -20 * log10(|Gamma|)
    """
```

---

### calculate_bandwidth()

**Purpose**: Calculate impedance matching bandwidth

**Signature**:
```python
def calculate_bandwidth(
    network: SParameterNetwork,
    port: int,
    target_impedance: float = 50.0,
    threshold_db: float = -10.0
) -> Tuple[float, float, float]:
    """
    Calculate bandwidth where return loss meets threshold.
    
    Args:
        network: S-parameter network
        port: Port to analyze
        target_impedance: Target impedance
        threshold_db: Return loss threshold (e.g., -10 dB)
    
    Returns:
        Tuple of (bandwidth_hz, freq_min_hz, freq_max_hz)
    
    Method:
        1. Calculate return loss vs frequency
        2. Find frequency range where RL < threshold_db
        3. Return bandwidth and frequency limits
    """
```

---

## Module: snp_tool.core.component_lib

### get_standard_values()

**Purpose**: Get standard component values from E-series

**Signature**:
```python
def get_standard_values(
    series: str = 'E24',
    decade_min: int = -12,
    decade_max: int = -6
) -> List[float]:
    """
    Get standard component values from E-series.
    
    Args:
        series: 'E12', 'E24', or 'E96'
        decade_min: Minimum decade (e.g., -12 for pico)
        decade_max: Maximum decade (e.g., -6 for micro)
    
    Returns:
        List of standard values in ascending order
    
    Example:
        E24 capacitor values from 1pF to 1µF:
        get_standard_values('E24', decade_min=-12, decade_max=-6)
        → [1e-12, 1.1e-12, 1.2e-12, ..., 8.2e-7, 9.1e-7, 1e-6]
    """
```

---

### snap_to_standard()

**Purpose**: Snap continuous value to nearest standard value

**Signature**:
```python
def snap_to_standard(
    value: float,
    series: str = 'E24'
) -> float:
    """
    Snap continuous value to nearest standard E-series value.
    
    Args:
        value: Arbitrary component value
        series: 'E12', 'E24', or 'E96'
    
    Returns:
        Nearest standard value
    
    Example:
        snap_to_standard(12.7e-12, 'E24')  # 12.7pF
        → 1.2e-11  # Nearest E24 value is 12pF
    """
```

---

## Module: snp_tool.optimizer.engine

### run_optimization()

**Purpose**: Run multi-metric weighted optimization (FR-006, FR-017)

**Signature**:
```python
from typing import Callable, Optional

@dataclass
class OptimizationConfig:
    port: int
    target_impedance: float
    frequency_range: Tuple[float, float]  # (min_hz, max_hz)
    weights: Dict[str, float]  # {metric_name: weight}
    mode: str  # 'ideal' or 'standard_values'
    component_series: str = 'E24'  # For standard_values mode
    max_components: int = 5
    max_iterations: int = 1000
    population_size: int = 15
    convergence_tolerance: float = 1e-6

def run_optimization(
    network: SParameterNetwork,
    config: OptimizationConfig,
    progress_callback: Optional[Callable[[int, float], None]] = None
) -> List[OptimizationSolution]:
    """
    Run impedance matching optimization.
    
    Args:
        network: Original S-parameter network
        config: Optimization configuration
        progress_callback: Optional callback(iteration, best_score) for progress updates
    
    Returns:
        List of OptimizationSolution objects, ranked by score (best first)
    
    Performance:
        <30 seconds for single-port, 2-component matching (SC-004)
    
    Implementation:
        Uses scipy.optimize.differential_evolution with custom objective function
        combining weighted metrics (return loss, VSWR, bandwidth, component count).
    
    Raises:
        OptimizationError: if optimization fails to converge or encounters error
    """
```

**Example**:
```python
from snp_tool.optimizer.engine import run_optimization, OptimizationConfig

config = OptimizationConfig(
    port=1,
    target_impedance=50.0,
    frequency_range=(2.0e9, 2.5e9),  # 2.0-2.5 GHz
    weights={'return_loss': 0.7, 'bandwidth': 0.2, 'component_count': 0.1},
    mode='ideal',
    max_components=2
)

solutions = run_optimization(network, config)

print(f"Found {len(solutions)} solutions")
print(f"Best solution score: {solutions[0].score:.3f}")
for comp in solutions[0].components:
    print(f"  - {comp.component_type.value} {comp.value_display} ({comp.placement.value})")
```

---

## Module: snp_tool.utils.engineering

### parse_engineering_notation()

**Purpose**: Parse engineering notation to numeric value (FR-005)

**Signature**:
```python
def parse_engineering_notation(
    value_str: str,
    expected_unit: Optional[str] = None
) -> float:
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
        parse_engineering_notation("10pF") → 1e-11
        parse_engineering_notation("2.2nH") → 2.2e-9
        parse_engineering_notation("100uH") → 1e-4
    """
```

---

### format_engineering_notation()

**Purpose**: Format numeric value as engineering notation

**Signature**:
```python
def format_engineering_notation(
    value: float,
    unit: str = '',
    precision: int = 2
) -> str:
    """
    Format numeric value as engineering notation string.
    
    Args:
        value: Numeric value in base units
        unit: Unit suffix ('F', 'H', 'Hz')
        precision: Decimal places
    
    Returns:
        Engineering notation string
    
    Examples:
        format_engineering_notation(1e-11, 'F') → "10.00pF"
        format_engineering_notation(2.2e-9, 'H') → "2.20nH"
    """
```

---

## Module: snp_tool.utils.session_io

### save_session()

**Purpose**: Save work session to file (FR-020)

**Signature**:
```python
def save_session(filepath: Path, session_data: Dict[str, Any]) -> None:
    """
    Save session to JSON file.
    
    Args:
        filepath: Session file path (recommend .snp-session extension)
        session_data: Session data dictionary (see data-model.md for schema)
    
    Raises:
        IOError: if file cannot be written
    
    Performance:
        <3 seconds (SC-012)
    """
```

---

### load_session()

**Purpose**: Load work session from file (FR-021)

**Signature**:
```python
def load_session(filepath: Path) -> Dict[str, Any]:
    """
    Load session from JSON file with version migration.
    
    Args:
        filepath: Session file path
    
    Returns:
        Session data dictionary
    
    Raises:
        FileNotFoundError: if session file doesn't exist
        ValueError: if version incompatible
    
    Version Migration:
        Automatically attempts to migrate older session formats to current version.
        Logs warnings if migration required.
    
    Performance:
        <3 seconds (SC-012)
    """
```

---

## Module: snp_tool.visualization.smith_chart

### plot_smith_chart()

**Purpose**: Generate Smith chart plot (FR-015)

**Signature**:
```python
from matplotlib.figure import Figure
from matplotlib.axes import Axes

def plot_smith_chart(
    network: SParameterNetwork,
    port: int = 0,
    ax: Optional[Axes] = None,
    label: Optional[str] = None
) -> Axes:
    """
    Plot impedance on Smith chart.
    
    Args:
        network: S-parameter network to plot
        port: Port to plot (0-indexed)
        ax: Optional matplotlib Axes (creates new if None)
        label: Optional label for legend
    
    Returns:
        matplotlib Axes object
    
    Implementation:
        Uses scikit-rf Network.plot_s_smith() for rendering.
        Customizes appearance for clarity (grid, markers, colors).
    """
```

---

## Module: snp_tool.visualization.rectangular

### plot_return_loss()

**Purpose**: Plot return loss vs frequency (FR-015)

**Signature**:
```python
def plot_return_loss(
    network: SParameterNetwork,
    port: int = 0,
    ax: Optional[Axes] = None
) -> Axes:
    """
    Plot return loss (dB) vs frequency.
    
    Args:
        network: S-parameter network
        port: Port to plot
        ax: Optional matplotlib Axes
    
    Returns:
        Axes with return loss plot
    """
```

---

### plot_vswr()

**Purpose**: Plot VSWR vs frequency (FR-015)

**Signature**:
```python
def plot_vswr(
    network: SParameterNetwork,
    port: int = 0,
    ax: Optional[Axes] = None,
    threshold: float = 2.0
) -> Axes:
    """
    Plot VSWR vs frequency.
    
    Args:
        network: S-parameter network
        port: Port to plot
        ax: Optional matplotlib Axes
        threshold: VSWR threshold line (default 2.0)
    
    Returns:
        Axes with VSWR plot (threshold line marked)
    """
```

---

## Exception Hierarchy

```python
class SNPToolError(Exception):
    """Base exception for all snp_tool errors."""

class ValidationError(SNPToolError):
    """SNP file validation error."""
    def __init__(self, message: str, report: ValidationReport):
        self.report = report
        super().__init__(message)

class ComponentLimitError(SNPToolError):
    """Max component limit exceeded."""

class OptimizationError(SNPToolError):
    """Optimization failed."""

class SessionError(SNPToolError):
    """Session save/load error."""
```

---

## Performance Contracts

| Function | Performance Target | Test Method |
|----------|-------------------|-------------|
| parse_snp() | <5s for 10k freq points | Performance benchmark test |
| add_component() | <1s for 1k freq points | Performance benchmark test |
| run_optimization() | <30s for 2-component match | Performance benchmark test |
| save_session() / load_session() | <3s | Performance benchmark test |

---

## Thread Safety

**Note**: The core computation engine is **NOT thread-safe** by design (YAGNI principle).

- All operations are synchronous and blocking
- For CLI: Single-threaded execution is sufficient
- For GUI: Run optimization in separate QThread, but ensure only one optimization at a time
- No shared mutable state across calls (immutable network operations)

**Future Enhancement**: If concurrent optimization becomes a requirement, add thread-safe wrappers.

---

## Testing Strategy

### Unit Tests (pytest)

Each module has comprehensive unit tests:

```python
# tests/unit/test_parsers.py
def test_parse_snp_valid_file():
    network = parse_snp(Path("tests/fixtures/snp_files/valid_antenna.s2p"))
    assert network.port_count == 2
    assert len(network.frequencies) == 201

def test_parse_snp_invalid_file_detailed_errors():
    with pytest.raises(ValidationError) as exc_info:
        parse_snp(Path("tests/fixtures/snp_files/invalid.s2p"))
    
    report = exc_info.value.report
    assert len(report.errors) > 0
    assert report.errors[0].line_number == 15  # Specific error location
```

### Contract Tests

Verify adherence to this API contract:

```python
# tests/contract/test_core_api.py
def test_add_component_signature():
    """Verify add_component() signature matches contract."""
    import inspect
    sig = inspect.signature(add_component)
    
    assert 'network' in sig.parameters
    assert 'component' in sig.parameters
    assert sig.return_annotation == SParameterNetwork
```

### Integration Tests

End-to-end workflows using core API:

```python
# tests/integration/test_optimization_workflow.py
def test_full_optimization_workflow():
    # Load → Optimize → Apply → Export
    network = parse_snp(Path("antenna.s2p"))
    
    config = OptimizationConfig(port=1, target_impedance=50.0, ...)
    solutions = run_optimization(network, config)
    
    assert len(solutions) > 0
    assert solutions[0].score < solutions[1].score  # Ranked correctly
    
    # Apply best solution
    for comp in solutions[0].components:
        network = add_component(network, comp)
    
    # Export
    # ... verify export successful
```

---

## Summary

This core API provides:

1. ✅ **SNP parsing with validation** (FR-001, FR-012)
2. ✅ **Component cascading** (FR-003, FR-004)
3. ✅ **Impedance calculations** (FR-002, FR-007)
4. ✅ **Optimization engine** (FR-006, FR-017)
5. ✅ **Engineering notation parsing** (FR-005)
6. ✅ **Session persistence** (FR-020, FR-021)
7. ✅ **Visualization** (FR-015)
8. ✅ **Performance contracts** (SC-001, SC-002, SC-004, SC-012)
9. ✅ **Shared by CLI and GUI** (FR-019 compliance)

**Next**: Create quickstart.md and update agent context
