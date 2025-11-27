# T059: Benchmark optimization performance
"""Performance benchmarks for optimization operations.

Target: < 5 sec single-freq, < 30 sec multi-freq (SC-003)
"""
import time
import pytest
from pathlib import Path

from snp_tool.parsers import touchstone
from snp_tool.parsers import component_library as comp_lib_parser
from snp_tool.optimizer.grid_search import GridSearchOptimizer


class TestOptimizationPerformance:
    """Benchmark optimization operations."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        return Path(__file__).parent.parent / "fixtures"

    @pytest.fixture
    def device(self, fixtures_dir: Path):
        return touchstone.parse(str(fixtures_dir / "sample_device.s2p"))

    @pytest.fixture
    def library(self, fixtures_dir: Path):
        return comp_lib_parser.parse_folder(str(fixtures_dir))

    def test_single_freq_optimization_under_5_seconds(self, device, library):
        """SC-003: Single-frequency optimization in < 5 sec."""
        optimizer = GridSearchOptimizer(device, library)

        start = time.perf_counter()
        result = optimizer.optimize(
            topology="L-section",
            target_frequency=device.center_frequency,
        )
        elapsed = time.perf_counter() - start

        print(f"\nSingle-freq optimization: {elapsed:.2f}s")
        print(f"  Combinations evaluated: {result.combinations_evaluated}")
        if result.success:
            print(f"  Best VSWR: {result.optimization_metrics.get('vswr_at_center', 'N/A'):.3f}")

        assert elapsed < 5.0, f"Optimization time {elapsed:.2f}s exceeds 5s target"

    def test_multi_freq_optimization_under_30_seconds(self, device, library):
        """SC-003: Multi-frequency (bandwidth) optimization in < 30 sec."""
        optimizer = GridSearchOptimizer(device, library)

        start = time.perf_counter()
        result = optimizer.optimize(
            topology="L-section",
            frequency_range=(device.frequencies[0], device.frequencies[-1]),
        )
        elapsed = time.perf_counter() - start

        print(f"\nMulti-freq optimization: {elapsed:.2f}s")
        print(f"  Combinations evaluated: {result.combinations_evaluated}")
        if result.success:
            print(f"  Best max VSWR: {result.optimization_metrics.get('max_vswr_in_band', 'N/A'):.3f}")

        assert elapsed < 30.0, f"Optimization time {elapsed:.2f}s exceeds 30s target"

    def test_grid_search_scaling(self, device, library):
        """Benchmark grid search with varying component counts."""
        optimizer = GridSearchOptimizer(device, library)

        # Get component counts
        caps = library.get_by_type("capacitor")
        inds = library.get_by_type("inductor")
        total_combos = len(caps) * len(inds)

        print(f"\nGrid search scaling:")
        print(f"  Capacitors: {len(caps)}")
        print(f"  Inductors: {len(inds)}")
        print(f"  Total combinations: {total_combos}")

        start = time.perf_counter()
        result = optimizer.optimize(
            topology="L-section",
            target_frequency=device.center_frequency,
        )
        elapsed = time.perf_counter() - start

        combos = result.combinations_evaluated or 1
        combos_per_sec = combos / elapsed if elapsed > 0 else 0
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Throughput: {combos_per_sec:.0f} combos/sec")

        # Extrapolate for 2500 combinations (50x50)
        time_for_2500 = 2500 / combos_per_sec if combos_per_sec > 0 else float("inf")
        print(f"  Estimated time for 2500 combos: {time_for_2500:.2f}s")

        # Relaxed assertion for small test libraries
        assert elapsed < 60.0, f"Time {elapsed:.2f}s exceeds limit"

    def test_cascade_performance(self, device, library):
        """Benchmark S-parameter cascade operations."""
        from snp_tool.optimizer.cascader import cascade_with_topology

        caps = library.get_by_type("capacitor")
        inds = library.get_by_type("inductor")

        if not caps or not inds:
            pytest.skip("Need components for cascade benchmark")

        cap = caps[0]
        ind = inds[0]

        # Benchmark cascade
        times = []
        for _ in range(100):
            start = time.perf_counter()
            cascade_with_topology(
                device.s_parameters,
                [cap.s_parameters, ind.s_parameters],
                ["series", "shunt"],
                device.frequencies,
                device.reference_impedance,
                [cap.frequency, ind.frequency],
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\nCascade benchmark: avg={avg_time*1000:.2f}ms, max={max_time*1000:.2f}ms")
        assert avg_time < 0.1, f"Cascade time {avg_time*1000:.2f}ms exceeds 100ms target"
