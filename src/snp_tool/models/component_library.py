"""Component Library catalog for searchable component index.

Per data-model.md: Searchable index of imported vendor component files.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import re
import numpy as np
from numpy.typing import NDArray

from .component import ComponentModel, ComponentType


@dataclass
class ComponentLibrary:
    """Searchable catalog of vendor components.

    Attributes:
        library_path: Root folder path containing .s2p files
        components: List of all loaded components
        index_by_type: Index of components by type (capacitor/inductor)
        index_by_manufacturer: Index by manufacturer
        index_by_value: Index by nominal value
    """

    library_path: str
    components: List[ComponentModel] = field(default_factory=list)
    index_by_type: Dict[ComponentType, List[ComponentModel]] = field(default_factory=dict)
    index_by_manufacturer: Dict[str, List[ComponentModel]] = field(default_factory=dict)
    index_by_value: Dict[str, List[ComponentModel]] = field(default_factory=dict)
    _frequency_coverage: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize indexes."""
        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        """Rebuild all indexes from components list."""
        self.index_by_type = {ct: [] for ct in ComponentType}
        self.index_by_manufacturer = {}
        self.index_by_value = {}
        self._frequency_coverage = {}

        for comp in self.components:
            # Index by type
            self.index_by_type[comp.component_type].append(comp)

            # Index by manufacturer
            mfr = comp.manufacturer.lower()
            if mfr not in self.index_by_manufacturer:
                self.index_by_manufacturer[mfr] = []
            self.index_by_manufacturer[mfr].append(comp)

            # Index by value
            if comp.value:
                value_key = comp.value.lower()
                if value_key not in self.index_by_value:
                    self.index_by_value[value_key] = []
                self.index_by_value[value_key].append(comp)

            # Track frequency coverage
            self._frequency_coverage[comp.part_number] = comp.frequency_range

    def add_component(self, component: ComponentModel) -> None:
        """Add a component to the library."""
        self.components.append(component)
        self._rebuild_indexes()

    def get_capacitors(self) -> List[ComponentModel]:
        """Get all capacitors."""
        return self.index_by_type.get(ComponentType.CAPACITOR, [])

    def get_inductors(self) -> List[ComponentModel]:
        """Get all inductors."""
        return self.index_by_type.get(ComponentType.INDUCTOR, [])

    def get_by_manufacturer(self, manufacturer: str) -> List[ComponentModel]:
        """Get components by manufacturer."""
        return self.index_by_manufacturer.get(manufacturer.lower(), [])

    def get_by_type_and_value(
        self, component_type: ComponentType, value: str
    ) -> List[ComponentModel]:
        """Get components by type and value.

        Args:
            component_type: CAPACITOR or INDUCTOR
            value: Value string (e.g., '10pF', '1nH')

        Returns:
            List of matching components
        """
        type_comps = self.index_by_type.get(component_type, [])
        value_lower = value.lower()

        return [c for c in type_comps if c.value and c.value.lower() == value_lower]

    def search(self, query: str) -> List[ComponentModel]:
        """Search components by query string.

        Supports queries like:
        - "capacitor 10pF"
        - "Murata inductor"
        - "10pF"
        - "capacitor"

        Args:
            query: Search query

        Returns:
            List of matching components
        """
        query_lower = query.lower().strip()
        tokens = query_lower.split()

        if not tokens:
            return list(self.components)

        results = set(range(len(self.components)))

        for token in tokens:
            token_matches = set()

            # Check if token is a type
            if token in ("capacitor", "cap", "c"):
                token_matches.update(
                    i
                    for i, c in enumerate(self.components)
                    if c.component_type == ComponentType.CAPACITOR
                )
            elif token in ("inductor", "ind", "l"):
                token_matches.update(
                    i
                    for i, c in enumerate(self.components)
                    if c.component_type == ComponentType.INDUCTOR
                )
            else:
                # Check manufacturer
                for i, c in enumerate(self.components):
                    if token in c.manufacturer.lower():
                        token_matches.add(i)

                # Check part number
                for i, c in enumerate(self.components):
                    if token in c.part_number.lower():
                        token_matches.add(i)

                # Check value
                for i, c in enumerate(self.components):
                    if c.value and token in c.value.lower():
                        token_matches.add(i)

            # Intersect with existing results
            results = results.intersection(token_matches)

        return [self.components[i] for i in sorted(results)]

    def validate_frequency_coverage(
        self, device_frequency_grid: NDArray[np.float64], tolerance: float = 0.01
    ) -> Tuple[List[ComponentModel], List[Tuple[ComponentModel, List[float]]]]:
        """Validate which components cover the device frequency range.

        Per Q4 clarification: Reject components with frequency gaps.

        Args:
            device_frequency_grid: Device frequency points
            tolerance: Relative tolerance for frequency matching (default 1%)

        Returns:
            Tuple of (valid_components, invalid_with_missing_freqs)
        """
        valid = []
        invalid = []

        for comp in self.components:
            is_valid, missing_freqs = comp.validate_frequency_coverage(
                device_frequency_grid, tolerance
            )
            if is_valid:
                valid.append(comp)
            else:
                invalid.append((comp, missing_freqs))

        return valid, invalid

    def filter_by_frequency_range(
        self, min_freq: float, max_freq: float
    ) -> List[ComponentModel]:
        """Filter components that cover a frequency range.

        Args:
            min_freq: Minimum frequency in Hz
            max_freq: Maximum frequency in Hz

        Returns:
            Components that cover the entire range
        """
        result = []
        for comp in self.components:
            comp_min, comp_max = comp.frequency_range
            if comp_min <= min_freq and comp_max >= max_freq:
                result.append(comp)
        return result

    @property
    def num_capacitors(self) -> int:
        """Get count of capacitors."""
        return len(self.get_capacitors())

    @property
    def num_inductors(self) -> int:
        """Get count of inductors."""
        return len(self.get_inductors())

    @property
    def num_components(self) -> int:
        """Get total component count."""
        return len(self.components)

    def get_summary(self) -> Dict:
        """Get library summary statistics."""
        summary = {
            "total_components": self.num_components,
            "capacitors": self.num_capacitors,
            "inductors": self.num_inductors,
            "manufacturers": list(self.index_by_manufacturer.keys()),
            "unique_values": len(self.index_by_value),
        }

        # Frequency range across all components
        if self.components:
            all_min = min(c.frequency_range[0] for c in self.components)
            all_max = max(c.frequency_range[1] for c in self.components)
            summary["frequency_range_ghz"] = [all_min / 1e9, all_max / 1e9]

        return summary

    def __repr__(self) -> str:
        return (
            f"ComponentLibrary(path={self.library_path}, "
            f"total={self.num_components}, "
            f"caps={self.num_capacitors}, "
            f"inds={self.num_inductors})"
        )

    def __len__(self) -> int:
        return len(self.components)

    def __iter__(self):
        return iter(self.components)
