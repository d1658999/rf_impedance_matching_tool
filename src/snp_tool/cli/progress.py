# T061: Progress reporting for long operations
"""Progress reporting for CLI and GUI operations.

Provides progress bars and status updates during optimization and file operations.
"""
from __future__ import annotations
from typing import Optional, Iterator, Callable, Any
import sys
import time


class ProgressReporter:
    """Simple progress reporter for CLI operations.

    Usage:
        with ProgressReporter(total=100, description="Optimizing") as progress:
            for i in range(100):
                # do work
                progress.update(1)
    """

    def __init__(
        self,
        total: int,
        description: str = "Processing",
        show_percentage: bool = True,
        show_eta: bool = True,
        bar_width: int = 40,
        stream=None,
    ):
        """Initialize progress reporter.

        Args:
            total: Total number of items to process
            description: Description of the operation
            show_percentage: Whether to show percentage
            show_eta: Whether to show estimated time remaining
            bar_width: Width of the progress bar in characters
            stream: Output stream (default: stderr)
        """
        self.total = max(total, 1)
        self.description = description
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.bar_width = bar_width
        self.stream = stream or sys.stderr

        self.current = 0
        self.start_time: Optional[float] = None
        self._last_update = 0.0

    def __enter__(self):
        self.start_time = time.time()
        self._render()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._finish()
        return False

    def update(self, n: int = 1) -> None:
        """Update progress by n items.

        Args:
            n: Number of items completed
        """
        self.current = min(self.current + n, self.total)

        # Throttle updates to avoid excessive rendering
        now = time.time()
        if now - self._last_update >= 0.1 or self.current >= self.total:
            self._render()
            self._last_update = now

    def set_description(self, description: str) -> None:
        """Update the description text.

        Args:
            description: New description
        """
        self.description = description
        self._render()

    def _render(self) -> None:
        """Render the progress bar to stream."""
        percent = self.current / self.total
        filled = int(self.bar_width * percent)
        bar = "█" * filled + "░" * (self.bar_width - filled)

        parts = [f"\r{self.description}: [{bar}]"]

        if self.show_percentage:
            parts.append(f" {percent * 100:5.1f}%")

        if self.show_eta and self.start_time and self.current > 0:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            parts.append(f" ETA: {self._format_time(remaining)}")

        self.stream.write("".join(parts))
        self.stream.flush()

    def _finish(self) -> None:
        """Finalize progress display."""
        self.current = self.total
        self._render()

        # Show completion time
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.stream.write(f" (completed in {self._format_time(elapsed)})\n")
        else:
            self.stream.write("\n")

        self.stream.flush()

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as human-readable time.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted string (e.g., "1m 30s", "45s", "< 1s")
        """
        if seconds < 1:
            return "< 1s"
        elif seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            m, s = divmod(int(seconds), 60)
            return f"{m}m {s}s"
        else:
            h, remainder = divmod(int(seconds), 3600)
            m, s = divmod(remainder, 60)
            return f"{h}h {m}m"


def progress_iterator(
    iterable: Iterator,
    total: Optional[int] = None,
    description: str = "Processing",
) -> Iterator:
    """Wrap an iterator with progress reporting.

    Args:
        iterable: Iterator to wrap
        total: Total number of items (if known)
        description: Description of the operation

    Yields:
        Items from the iterator
    """
    if total is None:
        # Try to get length
        try:
            total = len(iterable)
        except TypeError:
            total = 0

    if total == 0:
        # Unknown total, just yield items
        yield from iterable
        return

    with ProgressReporter(total=total, description=description) as progress:
        for item in iterable:
            yield item
            progress.update(1)


class SpinnerReporter:
    """Spinner for indeterminate progress operations.

    Usage:
        with SpinnerReporter("Loading components") as spinner:
            load_components()
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, description: str = "Processing", stream=None):
        self.description = description
        self.stream = stream or sys.stderr
        self._frame_idx = 0
        self._running = False
        self._start_time: Optional[float] = None

    def __enter__(self):
        self._start_time = time.time()
        self._running = True
        self._render()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._running = False
        self._finish(success=exc_type is None)
        return False

    def spin(self) -> None:
        """Advance the spinner by one frame."""
        if self._running:
            self._frame_idx = (self._frame_idx + 1) % len(self.FRAMES)
            self._render()

    def _render(self) -> None:
        """Render the spinner."""
        frame = self.FRAMES[self._frame_idx]
        self.stream.write(f"\r{frame} {self.description}...")
        self.stream.flush()

    def _finish(self, success: bool = True) -> None:
        """Finalize spinner display."""
        symbol = "✓" if success else "✗"
        elapsed = time.time() - self._start_time if self._start_time else 0

        self.stream.write(f"\r{symbol} {self.description}")
        if elapsed >= 0.1:
            self.stream.write(f" ({elapsed:.1f}s)")
        self.stream.write("\n")
        self.stream.flush()
