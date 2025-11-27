# T065: Architecture Documentation

## System Overview

The RF Impedance Matching Tool is a Python application for optimizing RF matching networks using S-parameter data from Touchstone files.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
├─────────────────────┬───────────────────────────────────────────┤
│     CLI (main.py)   │            GUI (PyQt6)                    │
└─────────────────────┴───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Application                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │   Parsers     │  │   Optimizer   │  │  Visualization    │   │
│  │               │  │               │  │                   │   │
│  │ • Touchstone  │  │ • Grid Search │  │ • Smith Chart     │   │
│  │ • Component   │  │ • Cascader    │  │ • Interactive     │   │
│  │   Library     │  │ • Metrics     │  │   Widget          │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Models                              │
├─────────────────────────────────────────────────────────────────┤
│  SNPFile │ ComponentModel │ MatchingNetwork │ OptimizationResult│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Utilities                                │
├─────────────────────────────────────────────────────────────────┤
│  RF Math │ Smith Chart Math │ Logging │ Exceptions             │
└─────────────────────────────────────────────────────────────────┘
```

## Component Interactions

### Data Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ .s2p     │────▶│ Parser   │────▶│ SNPFile  │────▶│ Optimizer│
│ Files    │     │          │     │ Objects  │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                        │               │
                                        ▼               ▼
                                  ┌──────────┐   ┌──────────────┐
                                  │ Component │   │ Optimization │
                                  │ Library   │   │ Result       │
                                  └──────────┘   └──────────────┘
                                                        │
                                        ┌───────────────┼───────────────┐
                                        ▼               ▼               ▼
                                  ┌──────────┐   ┌──────────┐   ┌──────────┐
                                  │ Smith    │   │ Schematic│   │ S2P      │
                                  │ Chart    │   │ Export   │   │ Export   │
                                  └──────────┘   └──────────┘   └──────────┘
```

### Optimization Flow

```
1. Load Device
   │
   ▼
2. Load Component Library
   │
   ▼
3. Filter by Frequency Coverage
   │
   ▼
4. Grid Search Enumeration
   │
   ├──▶ For each combination:
   │    │
   │    ├──▶ Build Matching Network
   │    │
   │    ├──▶ Convert S to ABCD matrices
   │    │
   │    ├──▶ Cascade ABCD matrices
   │    │
   │    ├──▶ Convert back to S-parameters
   │    │
   │    └──▶ Calculate reflection coefficient
   │
   ▼
5. Return Best Solution
```

## Module Structure

```
src/snp_tool/
├── __init__.py           # Package initialization
├── main.py               # CLI entry point
│
├── models/               # Data entities
│   ├── snp_file.py       # SNPFile: S-parameter data container
│   ├── component.py      # ComponentModel: Single component
│   ├── component_library.py  # ComponentLibrary: Component catalog
│   ├── matching_network.py   # MatchingNetwork: Cascaded network
│   └── optimization_result.py # OptimizationResult: Solution
│
├── parsers/              # File parsers
│   ├── touchstone.py     # TouchstoneParser: .snp file parser
│   └── component_library.py  # ComponentLibraryParser: folder scanner
│
├── optimizer/            # Optimization algorithms
│   ├── grid_search.py    # GridSearchOptimizer: brute-force search
│   ├── cascader.py       # S-parameter cascade (ABCD method)
│   ├── metrics.py        # RF metrics (VSWR, return loss, etc.)
│   ├── topology.py       # Topology builders (L, Pi, T sections)
│   └── bandwidth_optimizer.py  # Multi-frequency optimization
│
├── visualization/        # Plotting
│   ├── smith_chart.py    # SmithChartPlotter: static plots
│   └── smith_chart_widget.py  # InteractiveSmithChart: PyQt6 widget
│
├── gui/                  # PyQt6 GUI
│   └── app.py            # Main application window
│
├── cli/                  # CLI utilities
│   └── progress.py       # Progress reporting
│
└── utils/                # Utilities
    ├── rf_math.py        # RF calculations (impedance, etc.)
    ├── smith_chart_math.py   # Smith Chart coordinate transforms
    ├── component_metadata.py # Component type/value inference
    ├── logging.py        # Structured logging
    ├── exceptions.py     # Custom exceptions
    └── error_handler.py  # User-friendly error formatting
```

## Key Design Decisions

### 1. Grid Search Algorithm

**Decision**: Use brute-force grid search instead of gradient-based optimization.

**Rationale**:
- Deterministic and reproducible results
- Works well with discrete component values
- Simple to implement and debug
- Performance acceptable for typical library sizes (< 10,000 combinations)

### 2. ABCD Matrix Cascading

**Decision**: Use ABCD (transmission) matrices for network cascading.

**Rationale**:
- ABCD matrices can be simply multiplied for cascaded networks
- Handles series and shunt components naturally
- Well-established RF engineering practice

### 3. Frequency Coverage Rejection

**Decision**: Reject components that don't cover all device frequencies (no interpolation).

**Rationale**:
- Interpolation introduces errors
- Users expect accurate results from measured S-parameters
- Clear feedback on why components are rejected

### 4. Separation of Concerns

**Decision**: Keep parsers, models, optimizer, and visualization separate.

**Rationale**:
- Independent testing
- Easy to extend (new topologies, new optimizers)
- Clear data contracts between modules

## Extension Points

### Adding New Topologies

1. Add topology enum value to `Topology` in `matching_network.py`
2. Implement builder function in `topology.py`
3. Add search method in `grid_search.py`

### Adding New Optimization Algorithms

1. Create new optimizer class implementing same interface as `GridSearchOptimizer`
2. Must accept `device` and `component_library`
3. Must return `OptimizationResult`

### Adding New Export Formats

1. Add method to `OptimizationResult` class
2. Follow existing pattern: `export_<format>(path) -> str`

## Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| numpy | Numerical operations | ≥1.20 |
| scikit-rf | S-parameter handling | ≥0.25 |
| matplotlib | Plotting | ≥3.5 |
| PyQt6 | GUI framework | ≥6.0 |
| pytest | Testing | ≥7.0 |
