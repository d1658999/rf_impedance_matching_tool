# T060: Comprehensive error handling
"""Error handler providing actionable error messages for all operations.

Per Constitution V: Users never see cryptic exceptions; all errors have context.
"""
from __future__ import annotations
from typing import Optional, Callable, Any
from pathlib import Path
import functools
import traceback

from .logging import get_logger
from .exceptions import (
    SNPToolError,
    TouchstoneFormatError,
    FrequencyGapError,
    InvalidPortMappingError,
    ComponentNotFoundError,
    OptimizationError,
    ExportError,
)


logger = get_logger()


def format_user_error(error: Exception, operation: str = "") -> str:
    """Format an exception into a user-friendly error message.

    Args:
        error: The exception that occurred
        operation: Description of what operation was being performed

    Returns:
        User-friendly error message with actionable advice
    """
    if isinstance(error, TouchstoneFormatError):
        return _format_touchstone_error(error, operation)
    elif isinstance(error, FrequencyGapError):
        return _format_frequency_error(error, operation)
    elif isinstance(error, InvalidPortMappingError):
        return _format_port_error(error, operation)
    elif isinstance(error, ComponentNotFoundError):
        return _format_component_error(error, operation)
    elif isinstance(error, OptimizationError):
        return _format_optimization_error(error, operation)
    elif isinstance(error, ExportError):
        return _format_export_error(error, operation)
    elif isinstance(error, FileNotFoundError):
        return _format_file_not_found(error, operation)
    elif isinstance(error, PermissionError):
        return _format_permission_error(error, operation)
    elif isinstance(error, SNPToolError):
        return f"Error: {error.message}\n\nContext: {error.context}"
    else:
        return _format_generic_error(error, operation)


def _format_touchstone_error(error: TouchstoneFormatError, operation: str) -> str:
    """Format Touchstone file parsing errors."""
    msg = [f"Invalid Touchstone file format: {error.message}"]

    if error.context.get("file"):
        msg.append(f"  File: {error.context['file']}")
    if error.context.get("line"):
        msg.append(f"  Line: {error.context['line']}")

    msg.append("\nPossible causes:")
    msg.append("  • File may be corrupted or incomplete")
    msg.append("  • File may not be a valid Touchstone (.snp, .s2p) format")
    msg.append("  • File may have unsupported S-parameter format")

    msg.append("\nSuggestions:")
    msg.append("  • Verify the file opens correctly in RF simulation software")
    msg.append("  • Check that the file has proper header (e.g., '# Hz S DB R 50')")
    msg.append("  • Ensure S-parameter data is complete and properly formatted")

    return "\n".join(msg)


def _format_frequency_error(error: FrequencyGapError, operation: str) -> str:
    """Format frequency coverage errors."""
    msg = [f"Frequency coverage issue: {error.message}"]

    if error.context.get("component"):
        msg.append(f"  Component: {error.context['component']}")
    if error.context.get("missing_freqs"):
        msg.append(f"  Missing frequencies: {error.context['missing_freqs']}")

    msg.append("\nThis component cannot be used for matching because it lacks data")
    msg.append("at frequencies required by the device being matched.")

    msg.append("\nSuggestions:")
    msg.append("  • Use a different component with wider frequency coverage")
    msg.append("  • Check if vendor provides extended frequency model")
    msg.append("  • Narrow the device frequency range to match component coverage")

    return "\n".join(msg)


def _format_port_error(error: InvalidPortMappingError, operation: str) -> str:
    """Format port mapping errors."""
    msg = [f"Invalid port mapping: {error.message}"]

    if error.context.get("num_ports"):
        msg.append(f"  Available ports: 1-{error.context['num_ports']}")
    if error.context.get("requested"):
        msg.append(f"  Requested mapping: {error.context['requested']}")

    msg.append("\nSuggestions:")
    msg.append("  • Check the number of ports in your .snp file")
    msg.append("  • Use valid port numbers (0-indexed or 1-indexed depending on format)")
    msg.append("  • For 2-port devices (.s2p), omit port mapping")

    return "\n".join(msg)


def _format_component_error(error: ComponentNotFoundError, operation: str) -> str:
    """Format component search errors."""
    msg = [f"Component not found: {error.message}"]

    if error.context.get("query"):
        msg.append(f"  Search query: '{error.context['query']}'")
    if error.context.get("library"):
        msg.append(f"  Library path: {error.context['library']}")

    msg.append("\nSuggestions:")
    msg.append("  • Check your search query for typos")
    msg.append("  • Try a broader search (e.g., 'capacitor' instead of 'capacitor 10pF')")
    msg.append("  • Verify the component library folder contains .s2p files")
    msg.append("  • Re-import the component library")

    return "\n".join(msg)


def _format_optimization_error(error: OptimizationError, operation: str) -> str:
    """Format optimization failure errors."""
    msg = [f"Optimization failed: {error.message}"]

    if error.context.get("topology"):
        msg.append(f"  Topology: {error.context['topology']}")
    if error.context.get("target_freq"):
        msg.append(f"  Target frequency: {error.context['target_freq']}")
    if error.context.get("best_reflection"):
        msg.append(f"  Best reflection achieved: {error.context['best_reflection']}")

    msg.append("\nPossible causes:")
    msg.append("  • Device impedance may be too far from 50Ω to match with available components")
    msg.append("  • Component library may lack suitable values")
    msg.append("  • Selected topology may not be appropriate for this device")

    msg.append("\nSuggestions:")
    msg.append("  • Try a different topology (L-section, Pi-section, T-section)")
    msg.append("  • Add more components to the library")
    msg.append("  • Narrow the frequency range for optimization")
    msg.append("  • Check if the device S-parameters are correct")

    return "\n".join(msg)


def _format_export_error(error: ExportError, operation: str) -> str:
    """Format export operation errors."""
    msg = [f"Export failed: {error.message}"]

    if error.context.get("path"):
        msg.append(f"  Output path: {error.context['path']}")
    if error.context.get("format"):
        msg.append(f"  Format: {error.context['format']}")

    msg.append("\nSuggestions:")
    msg.append("  • Verify the output directory exists and is writable")
    msg.append("  • Check available disk space")
    msg.append("  • Try exporting to a different location")

    return "\n".join(msg)


def _format_file_not_found(error: FileNotFoundError, operation: str) -> str:
    """Format file not found errors."""
    filename = str(error.filename) if error.filename else "Unknown"
    msg = [f"File not found: {filename}"]

    msg.append("\nSuggestions:")
    msg.append("  • Verify the file path is correct")
    msg.append("  • Check that the file exists")
    msg.append("  • Use absolute paths to avoid confusion")

    return "\n".join(msg)


def _format_permission_error(error: PermissionError, operation: str) -> str:
    """Format permission errors."""
    filename = str(error.filename) if error.filename else "Unknown"
    msg = [f"Permission denied: {filename}"]

    msg.append("\nSuggestions:")
    msg.append("  • Check file/directory permissions")
    msg.append("  • Try running with appropriate privileges")
    msg.append("  • Verify the file is not locked by another program")

    return "\n".join(msg)


def _format_generic_error(error: Exception, operation: str) -> str:
    """Format generic errors."""
    error_type = type(error).__name__
    msg = [f"An error occurred: {error_type}"]
    msg.append(f"  {str(error)}")

    if operation:
        msg.append(f"\nDuring: {operation}")

    msg.append("\nIf this problem persists, please check:")
    msg.append("  • Your input files are valid")
    msg.append("  • All required dependencies are installed")
    msg.append("  • You have the latest version of snp_tool")

    return "\n".join(msg)


def handle_errors(operation: str = ""):
    """Decorator to catch and format errors for CLI/GUI operations.

    Args:
        operation: Description of the operation being performed

    Returns:
        Decorated function that handles errors gracefully
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {operation or func.__name__}: {str(e)}")
                user_msg = format_user_error(e, operation)
                print(f"\n{user_msg}")

                # Re-raise for non-user-facing code
                if hasattr(func, '_reraise_errors') and func._reraise_errors:
                    raise

                return None
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for error handling with cleanup.

    Usage:
        with ErrorContext("loading device file") as ctx:
            device = parser.parse(file_path)
            ctx.result = device
    """

    def __init__(self, operation: str, reraise: bool = False):
        self.operation = operation
        self.reraise = reraise
        self.result = None
        self.error = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error = exc_val
            logger.error(f"Error during {self.operation}: {str(exc_val)}")
            user_msg = format_user_error(exc_val, self.operation)
            print(f"\n{user_msg}")

            if self.reraise:
                return False  # Re-raise the exception
            return True  # Suppress the exception

        return False
