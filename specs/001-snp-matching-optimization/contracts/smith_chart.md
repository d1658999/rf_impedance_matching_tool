# Contract: Smith Chart Visualization

**Module**: `snp_tool.visualization.smith_chart`  
**Purpose**: Render Smith Chart plots for impedance visualization

---

## Function: `plot_impedance_trajectory(snp_file: SNPFile, title: str = None) -> matplotlib.Figure`

**Input**:
- `snp_file`: SNPFile object with impedance data
- `title`: (optional) Plot title

**Output**: matplotlib Figure object

**Behavior**:
1. Create normalized Smith Chart (50Ω reference)
2. Plot impedance locus (curve connecting all frequency points)
3. Color code by frequency (rainbow gradient: red=low freq, blue=high freq)
4. Add frequency labels at key points (start, center, end)
5. Display legend with frequency range
6. Return figure (caller can display with plt.show() or save to file)

**Example**:
```python
from snp_tool.visualization import SmithChartPlotter

plotter = SmithChartPlotter()
fig = plotter.plot_impedance_trajectory(device, title="Device Impedance")
fig.savefig("device_smith.png")
```

---

## Function: `plot_comparison(before: SNPFile, after: MatchingNetwork, title: str = None) -> matplotlib.Figure`

**Input**:
- `before`: SNPFile (original device impedance)
- `after`: MatchingNetwork (matched device impedance)
- `title`: (optional) Plot title

**Output**: matplotlib Figure (2 subplots side by side, or overlaid)

**Behavior**:
1. Create Smith Chart with 2 subplots: "Before Matching" | "After Matching"
2. Subplot 1: Plot before impedance locus (red curve)
3. Subplot 2: Plot after impedance locus (green curve, should be near center 50Ω)
4. Add annotations:
   - Before: "Worst VSWR: X.XX @ freq Y GHz"
   - After: "Best VSWR: X.XX @ freq Y GHz"
5. Optional: Overlay both on single Smith Chart with different colors
6. Return figure

**Example**:
```python
fig = plotter.plot_comparison(device, matched_network, title="Matching Result")
fig.savefig("comparison.png")
```

---

## Class: `InteractiveSmithChart` (PyQt6 Widget)

**Purpose**: Embedded Smith Chart in GUI with interactive frequency cursor

**Attributes**:
- `figure`: matplotlib Figure
- `canvas`: FigureCanvas (for embedding in PyQt)
- `frequency_cursor`: Current hovered frequency
- `frequency_label`: Display label

**Methods**:

### `set_data(snp_file: SNPFile, comparison: MatchingNetwork = None)`
Load impedance data for interactive plot

### `on_hover(x: float, y: float)`
Handle mouse hover event; update frequency cursor and labels

### `set_frequency(freq: float)`
Manually set frequency cursor to specific frequency; update visualization

**Behavior**:
1. Display Smith Chart with impedance trajectory
2. On mouse hover: Detect nearest frequency point
3. Display frequency and impedance at cursor:
   - "Frequency: 2.34 GHz"
   - "Impedance: (45.2 + 5.3j) Ω"
   - "VSWR: 1.12"
   - "Return Loss: 17.3 dB"
4. If comparison provided: Show both before/after at same frequency
5. Update in real-time as user moves cursor

**Example** (GUI code):
```python
from snp_tool.visualization import InteractiveSmithChart
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

# Create Smith Chart widget
chart = InteractiveSmithChart()
chart.set_data(device, matched_network)

# Embed in window
window = QMainWindow()
layout = QVBoxLayout()
layout.addWidget(chart)
window.setLayout(layout)
window.show()
```

---

## Function: `calculate_metrics(impedance: complex, frequency: float) -> dict`

**Input**:
- `impedance`: Complex impedance at a frequency
- `frequency`: Frequency in Hz (for display purposes)

**Output**: Dictionary with RF metrics

**Calculation**:
```python
s11 = (impedance - 50) / (impedance + 50)  # Reflection coefficient
vswr = (1 + abs(s11)) / (1 - abs(s11))
return_loss_dB = -20 * log10(abs(s11))

return {
    'frequency': frequency,
    'impedance': impedance,
    's11_magnitude': abs(s11),
    's11_angle_deg': angle(s11) * 180 / pi,
    'vswr': vswr,
    'return_loss_dB': return_loss_dB
}
```

**Example**:
```python
metrics = calculate_metrics((50.1 + 0.2j), 2.25e9)
# → {'frequency': 2.25e9, 'impedance': (50.1+0.2j), 's11_magnitude': 0.004, 'vswr': 1.008, ...}
```

---

## Visualization Notes

- **Normalized Smith Chart**: Center = 50Ω, top = 0Ω (open), bottom = ∞Ω (short)
- **Frequency Coloring**: Hue = frequency (red for low, blue for high)
- **Axis Labels**: Real part (top), Imaginary part (left)
- **Resolution**: Generate at matplotlib default DPI; support export to PNG/PDF

