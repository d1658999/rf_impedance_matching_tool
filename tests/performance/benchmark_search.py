# T058: Benchmark component search performance
"""Performance benchmarks for component search operations.

Target: Search 50+ components in < 1 sec per query (SC-002)
"""
import time
import pytest
from pathlib import Path

from snp_tool.parsers import component_library as comp_lib_parser
from snp_tool.parsers import touchstone


class TestSearchPerformance:
    """Benchmark component search operations."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        return Path(__file__).parent.parent / "fixtures"

    @pytest.fixture
    def library(self, fixtures_dir: Path):
        return comp_lib_parser.parse_folder(str(fixtures_dir))

    def test_search_under_1_second(self, library):
        """SC-002: Search component library in < 1 sec."""
        queries = [
            "capacitor",
            "inductor",
            "capacitor 10pF",
            "inductor 10nH",
            "Murata",
            "TDK",
        ]

        for query in queries:
            start = time.perf_counter()
            results = library.search(query)
            elapsed = time.perf_counter() - start

            print(f"\nSearch '{query}': {len(results)} results in {elapsed*1000:.2f}ms")
            assert elapsed < 1.0, f"Search time {elapsed:.3f}s exceeds 1s target"

    def test_search_by_type_performance(self, library):
        """Benchmark search by component type."""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            library.search("capacitor")
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\nType search benchmark: avg={avg_time*1000:.2f}ms, max={max_time*1000:.2f}ms")
        assert max_time < 1.0, f"Search time {max_time:.3f}s exceeds 1s target"

    def test_search_by_value_performance(self, library):
        """Benchmark search by component value."""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            library.search("10pF")
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\nValue search benchmark: avg={avg_time*1000:.2f}ms, max={max_time*1000:.2f}ms")
        assert max_time < 1.0, f"Search time {max_time:.3f}s exceeds 1s target"

    def test_filter_by_frequency_coverage(self, library, fixtures_dir: Path):
        """Benchmark frequency coverage filtering."""
        device = touchstone.parse(str(fixtures_dir / "sample_device.s2p"))

        start = time.perf_counter()
        valid_comps, invalid_comps = library.validate_frequency_coverage(
            device.frequencies
        )
        elapsed = time.perf_counter() - start

        print(f"\nFrequency filter: {len(valid_comps)} valid components in {elapsed*1000:.2f}ms")
        assert elapsed < 1.0, f"Filter time {elapsed:.3f}s exceeds 1s target"
