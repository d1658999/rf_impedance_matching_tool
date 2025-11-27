# T057: Benchmark file load performance
"""Performance benchmarks for file loading operations.

Target: Load .snp file (100 freq points) in < 2 sec (SC-001)
"""
import time
import pytest
from pathlib import Path

from snp_tool.parsers import touchstone


class TestLoadPerformance:
    """Benchmark file load operations."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        return Path(__file__).parent.parent / "fixtures"

    def test_load_s2p_under_2_seconds(self, fixtures_dir: Path):
        """SC-001: Load .snp file in < 2 sec."""
        s2p_file = fixtures_dir / "sample_device.s2p"

        # Warm-up run
        touchstone.parse(str(s2p_file))

        # Timed run (average of 10)
        times = []
        for _ in range(10):
            start = time.perf_counter()
            touchstone.parse(str(s2p_file))
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\nLoad benchmark: avg={avg_time*1000:.2f}ms, max={max_time*1000:.2f}ms")
        assert max_time < 2.0, f"Load time {max_time:.3f}s exceeds 2s target"

    def test_load_100_frequency_points(self, fixtures_dir: Path):
        """Verify parsing handles 100+ frequency points efficiently."""
        s2p_file = fixtures_dir / "sample_device.s2p"

        start = time.perf_counter()
        snp = touchstone.parse(str(s2p_file))
        elapsed = time.perf_counter() - start

        print(f"\nParsed {len(snp.frequencies)} freq points in {elapsed*1000:.2f}ms")
        assert elapsed < 2.0, f"Load time {elapsed:.3f}s exceeds 2s target"

    def test_batch_load_multiple_files(self, fixtures_dir: Path):
        """Benchmark loading multiple component files."""
        s2p_files = list(fixtures_dir.glob("*.s2p"))

        start = time.perf_counter()
        for f in s2p_files:
            touchstone.parse(str(f))
        elapsed = time.perf_counter() - start

        per_file = elapsed / len(s2p_files) if s2p_files else 0
        print(f"\nLoaded {len(s2p_files)} files in {elapsed*1000:.2f}ms ({per_file*1000:.2f}ms/file)")
        assert per_file < 2.0, f"Per-file load time {per_file:.3f}s exceeds 2s target"
