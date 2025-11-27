# T064: Debugging Guide

This guide helps you troubleshoot common issues with the RF Impedance Matching Tool.

## Enabling Verbose Logging

### CLI Mode

```bash
# Enable debug logging
snp-tool --verbose load device.s2p

# Enable trace logging (most detailed)
snp-tool --log-level DEBUG load device.s2p

# Save logs to file
snp-tool --log-file debug.log optimize device.s2p --library ./components
```

### Python API

```python
from snp_tool.utils.logging import setup_logging

# Enable debug logging
setup_logging(level="DEBUG")

# Or with file output
setup_logging(level="DEBUG", log_file="debug.log")
```

## Common Issues

### 1. "No components have valid frequency coverage"

**Cause**: Components in your library don't cover the device's frequency range.

**Diagnosis**:
```python
from snp_tool.parsers.touchstone import TouchstoneParser
from snp_tool.parsers.component_library import ComponentLibraryParser

device = TouchstoneParser().parse("device.s2p")
library = ComponentLibraryParser().parse_folder("./components")

print(f"Device freq range: {device.frequency[0]/1e9:.2f} - {device.frequency[-1]/1e9:.2f} GHz")

for comp in library.components:
    f_min, f_max = comp.frequency[0], comp.frequency[-1]
    print(f"{comp.part_number}: {f_min/1e9:.2f} - {f_max/1e9:.2f} GHz")
```

**Solution**:
- Use components with wider frequency coverage
- Narrow the device optimization frequency range

### 2. "Invalid Touchstone format"

**Cause**: S-parameter file is malformed or incomplete.

**Diagnosis**:
```bash
# Check file header
head -5 problematic_file.s2p

# Expected format:
# ! Comment lines start with !
# # Hz S DB R 50
# freq S11_mag S11_ang S21_mag S21_ang S12_mag S12_ang S22_mag S22_ang
```

**Common issues**:
- Missing option line (`# Hz S DB R 50`)
- Incomplete S-parameter data
- Non-numeric values
- Unsupported frequency unit

### 3. "Optimization failed to find solution"

**Cause**: Device impedance too far from 50Ω for available components.

**Diagnosis**:
```python
# Check device impedance
device = TouchstoneParser().parse("device.s2p")
print(f"Device impedance at center: {device.impedance_at_center}")
print(f"VSWR before matching: {device.vswr_at_center:.2f}")
```

**Solutions**:
1. Try different topology:
   - L-section: Simple, narrow-band
   - Pi-section: Better for high-Q matching
   - T-section: More flexibility

2. Add more components:
   ```bash
   # Import additional vendor libraries
   snp-tool library ./murata_caps ./tdk_inductors
   ```

3. Check if device is already matched:
   ```python
   if device.vswr_at_center < 1.5:
       print("Device already well-matched!")
   ```

### 4. Slow Optimization

**Cause**: Large component library causing many combinations.

**Diagnosis**:
```python
caps = len(library.get_by_type("capacitor"))
inds = len(library.get_by_type("inductor"))
combos = caps * inds
print(f"L-section combinations: {combos}")
# Should be < 10,000 for fast optimization
```

**Solutions**:
- Filter library by frequency range before optimization
- Use single-frequency optimization first
- Reduce library to relevant component values

## Log Message Reference

| Log Level | Message Pattern | Meaning |
|-----------|----------------|---------|
| DEBUG | `Parsing file: {path}` | Loading S-parameter file |
| DEBUG | `Found {n} frequency points` | File parsing progress |
| INFO | `Components with valid frequency coverage: {n}` | Filtered components |
| INFO | `Starting grid search optimization` | Optimization began |
| INFO | `Optimization complete` | Finished with result |
| WARNING | `Component {name} rejected: frequency gap` | Coverage issue |
| ERROR | `Optimization failed: {reason}` | No solution found |

## Performance Profiling

```python
import cProfile
import pstats

# Profile optimization
cProfile.run('''
optimizer.optimize(topology="L-section")
''', 'opt_profile.stats')

# Analyze results
stats = pstats.Stats('opt_profile.stats')
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

## Reporting Bugs

When reporting issues, include:

1. **Log output** with `--verbose` flag
2. **S-parameter files** (device and components)
3. **Python version**: `python --version`
4. **Package version**: `pip show snp-tool`
5. **Stack trace** if available

## Contact

- GitHub Issues: [Project Repository]
- Documentation: [Project Wiki]
