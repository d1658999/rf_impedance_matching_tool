# Quickstart Guide: SNP File Matching Optimization

**Status**: Phase 1 Design  
**Last Updated**: 2025-11-26

---

## Overview

The SNP File Matching Optimization tool helps RF engineers automatically find optimal passive component networks (impedance matching) that transform device impedance to 50Ω using vendor design kits (Murata, TDK, etc.).

**MVP Capabilities**:
1. ✅ Load device S-parameters (.snp files)
2. ✅ Import vendor component libraries (.s2p files)
3. ✅ Automatically optimize matching network using grid search
4. ✅ Visualize results on Smith Chart

---

## Installation (MVP)

```bash
# Clone repository
git clone https://github.com/yourorg/rf_impedance_matching_tool.git
cd rf_impedance_matching_tool

# Install dependencies
pip install -r requirements.txt
# or: pip install scikit-rf matplotlib numpy pytest

# Verify installation
python -m pytest tests/unit/
```

**Dependencies**:
- `scikit-rf` (S-parameter parsing, ABCD cascading)
- `numpy` (complex number math)
- `matplotlib` (Smith Chart visualization)
- `pytest` (testing)

---

## CLI Usage (MVP)

### 1. Load Main Device .snp File

```bash
python -m snp_tool.main --load device.s2p
```

**Output**:
```
SNP File Loaded
===============
File: device.s2p
Ports: 2
Frequency Range: 2.0 GHz - 2.5 GHz (51 points)
Source Port: 0 (default)
Load Port: 1 (default)

Impedance Trajectory:
  @ 2.0 GHz:   40.2 + 15.3j Ω (return loss: 5.2 dB)
  @ 2.25 GHz: 35.1 + 22.4j Ω (return loss: 2.8 dB)
  @ 2.5 GHz:   38.7 + 18.9j Ω (return loss: 4.1 dB)
```

### 2. For Multi-Port Files (S3P/S4P), Specify Ports

```bash
python -m snp_tool.main --load device.s3p --port-mapping 0 1
```

**Meaning**: Use port 0 (source) → port 1 (load)

### 3. Import Component Library

```bash
python -m snp_tool.main --library components/murata_kits
```

**Output**:
```
Component Library Indexed
==========================
Folder: components/murata_kits
Components Found: 45
  - Capacitors: 22 (1pF to 1µF, 100 MHz to 10 GHz)
  - Inductors: 23 (1nH to 10µH, 100 MHz to 10 GHz)
```

### 4. Automatic Impedance Matching (Core MVP)

```bash
python -m snp_tool.main \
  --load device.s2p \
  --library components/murata_kits \
  --optimize \
  --topology L-section \
  --frequency-range 2.0G 2.5G
```

**Output**: Optimized matching network with components and metrics

### 5. Export Optimized Design

```bash
python -m snp_tool.main \
  --load device.s2p \
  --library components/ \
  --optimize --topology L-section \
  --export-schematic matching_network.txt \
  --export-s2p cascaded_device.s2p
```

---

## Python API Usage (MVP)

```python
from snp_tool.parsers import TouchstoneParser
from snp_tool.optimizer import GridSearchOptimizer

# 1. Load device
device = TouchstoneParser.parse("device.s2p")

# 2. Run optimization
optimizer = GridSearchOptimizer(device, library)
result = optimizer.optimize(topology='L-section', frequency_range=(2.0e9, 2.5e9))

# 3. Export
result.export_schematic("solution.txt")
result.export_s_parameters("cascaded.s2p")
```

---

## Next Steps (P2)

- 🔲 PyQt6 GUI (P2)
- 🔲 Interactive Smith Chart visualization (P2)
- 🔲 Multi-frequency bandwidth optimization (P2)

