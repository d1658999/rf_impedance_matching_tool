"""Custom exceptions for SNP Tool.

All exceptions include context for actionable error messages per Constitution V.
"""

from typing import List, Optional


class SNPToolError(Exception):
    """Base exception for all SNP Tool errors."""

    def __init__(self, message: str, context: Optional[dict] = None):
        self.message = message
        self.context = context or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} [{context_str}]"
        return self.message


class TouchstoneFormatError(SNPToolError):
    """Raised when a Touchstone file has invalid format."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ):
        context = {}
        if file_path:
            context["file"] = file_path
        if line_number:
            context["line"] = line_number
        super().__init__(message, context)


class FrequencyGapError(SNPToolError):
    """Raised when frequency coverage has gaps (Q4 clarification: reject, don't interpolate)."""

    def __init__(
        self,
        message: str,
        component_name: Optional[str] = None,
        missing_frequencies: Optional[List[float]] = None,
    ):
        context = {}
        if component_name:
            context["component"] = component_name
        if missing_frequencies:
            # Format frequencies in GHz for readability
            freq_str = ", ".join(f"{f/1e9:.3f} GHz" for f in missing_frequencies[:5])
            if len(missing_frequencies) > 5:
                freq_str += f"... (+{len(missing_frequencies) - 5} more)"
            context["missing_freqs"] = freq_str
        super().__init__(message, context)


class InvalidPortMappingError(SNPToolError):
    """Raised when port mapping is invalid for multi-port files."""

    def __init__(
        self,
        message: str,
        num_ports: Optional[int] = None,
        requested_ports: Optional[tuple] = None,
    ):
        context = {}
        if num_ports:
            context["num_ports"] = num_ports
        if requested_ports:
            context["requested"] = f"{requested_ports[0]}→{requested_ports[1]}"
        super().__init__(message, context)


class ComponentNotFoundError(SNPToolError):
    """Raised when a component cannot be found in the library."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        library_path: Optional[str] = None,
    ):
        context = {}
        if query:
            context["query"] = query
        if library_path:
            context["library"] = library_path
        super().__init__(message, context)


class OptimizationError(SNPToolError):
    """Raised when optimization fails to find a solution."""

    def __init__(
        self,
        message: str,
        topology: Optional[str] = None,
        target_frequency: Optional[float] = None,
        best_reflection: Optional[float] = None,
    ):
        context = {}
        if topology:
            context["topology"] = topology
        if target_frequency:
            context["target_freq"] = f"{target_frequency/1e9:.3f} GHz"
        if best_reflection is not None:
            context["best_reflection"] = f"{best_reflection:.4f}"
        super().__init__(message, context)


class ExportError(SNPToolError):
    """Raised when export operation fails."""

    def __init__(
        self,
        message: str,
        export_path: Optional[str] = None,
        export_format: Optional[str] = None,
    ):
        context = {}
        if export_path:
            context["path"] = export_path
        if export_format:
            context["format"] = export_format
        super().__init__(message, context)


class SessionError(SNPToolError):
    """Raised when session save/load operation fails."""

    def __init__(
        self,
        message: str,
        session_file: Optional[str] = None,
        session_version: Optional[str] = None,
    ):
        context = {}
        if session_file:
            context["file"] = session_file
        if session_version:
            context["version"] = session_version
        super().__init__(message, context)
