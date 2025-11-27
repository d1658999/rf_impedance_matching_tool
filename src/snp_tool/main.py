"""CLI entry point for SNP Tool.

Per quickstart.md: Provides CLI interface for loading files, importing libraries,
and running optimization.
"""

from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from . import __version__
from .models import SNPFile, ComponentLibrary, Topology
from .parsers import parse as parse_touchstone
from .parsers import parse_folder
from .optimizer import GridSearchOptimizer, GridSearchConfig
from .utils.logging import configure_logging, get_logger
from .utils.exceptions import SNPToolError


def main(args: Optional[list] = None) -> int:
    """Main CLI entry point.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success)
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Configure logging
    logger = configure_logging(
        verbose=parsed_args.verbose,
        json_output=parsed_args.json,
    )

    try:
        return run_command(parsed_args, logger)
    except SNPToolError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        if parsed_args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="snp-tool",
        description="RF Impedance Matching Optimization Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  snp-tool --load device.s2p
  snp-tool --load device.s2p --library components/
  snp-tool --load device.s2p --library components/ --optimize --topology L-section
  snp-tool --load device.s3p --port-mapping 0 2 --library components/ --optimize
        """,
    )
    
    # Version
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Input options
    parser.add_argument(
        "--load", "-l",
        metavar="FILE",
        help="Load main device .snp file",
    )
    parser.add_argument(
        "--port-mapping", "-p",
        nargs=2,
        type=int,
        metavar=("SRC", "LOAD"),
        help="Port mapping for multi-port files (e.g., 0 1)",
    )
    parser.add_argument(
        "--library", "-L",
        metavar="DIR",
        help="Import component library from directory",
    )
    parser.add_argument(
        "--search", "-s",
        metavar="QUERY",
        help="Search component library (e.g., 'capacitor 10pF')",
    )

    # Optimization options
    parser.add_argument(
        "--optimize", "-O",
        action="store_true",
        help="Run automatic matching optimization",
    )
    parser.add_argument(
        "--topology", "-t",
        choices=["L-section", "Pi-section", "T-section"],
        default="L-section",
        help="Matching topology (default: L-section)",
    )
    parser.add_argument(
        "--frequency-range", "-f",
        nargs=2,
        type=str,
        metavar=("START", "END"),
        help="Frequency range (e.g., '2.0G 2.5G' or '2000M 2500M')",
    )
    parser.add_argument(
        "--target-frequency",
        type=str,
        metavar="FREQ",
        help="Target frequency for optimization",
    )

    # Export options
    parser.add_argument(
        "--export-schematic",
        metavar="FILE",
        help="Export schematic to text file",
    )
    parser.add_argument(
        "--export-s2p",
        metavar="FILE",
        help="Export cascaded S-parameters to .s2p file",
    )

    # Output options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    return parser


def run_command(args, logger) -> int:
    """Execute the command based on parsed arguments."""
    device = None
    library = None
    result = None

    # Load device file
    if args.load:
        port_mapping = tuple(args.port_mapping) if args.port_mapping else None
        device = parse_touchstone(args.load, port_mapping=port_mapping)

        if not args.json:
            print_device_info(device)

    # Load component library
    if args.library:
        library = parse_folder(args.library)

        if not args.json:
            print_library_info(library)

        # Handle search
        if args.search:
            results = library.search(args.search)
            if not args.json:
                print_search_results(results, args.search)
            else:
                print(json.dumps([{
                    "manufacturer": c.manufacturer,
                    "part_number": c.part_number,
                    "type": c.component_type.value,
                    "value": c.value,
                } for c in results], indent=2))
            return 0

    # Run optimization
    if args.optimize:
        if device is None:
            logger.error("--load required for optimization")
            return 1
        if library is None:
            logger.error("--library required for optimization")
            return 1

        # Parse topology
        topology_map = {
            "L-section": Topology.L_SECTION,
            "Pi-section": Topology.PI_SECTION,
            "T-section": Topology.T_SECTION,
        }
        topology = topology_map.get(args.topology, Topology.L_SECTION)

        # Parse frequency range
        freq_range = None
        if args.frequency_range:
            freq_range = (
                parse_frequency(args.frequency_range[0]),
                parse_frequency(args.frequency_range[1]),
            )

        target_freq = None
        if args.target_frequency:
            target_freq = parse_frequency(args.target_frequency)

        # Run optimization
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(
            topology=topology,
            frequency_range=freq_range,
            target_frequency=target_freq,
        )

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print_optimization_result(result)

        # Export if requested
        if args.export_schematic:
            path = result.export_schematic(args.export_schematic)
            logger.info(f"Exported schematic to: {path}")

        if args.export_s2p:
            path = result.export_s_parameters(args.export_s2p)
            logger.info(f"Exported S-parameters to: {path}")

    # If only device loaded (no optimization), show detailed info
    if device and not args.optimize and not args.library:
        if args.json:
            print(json.dumps({
                "file": device.file_path,
                "num_ports": device.num_ports,
                "frequency_range_ghz": [f / 1e9 for f in device.frequency_range],
                "num_points": device.num_frequency_points,
                "center_frequency_ghz": device.center_frequency / 1e9,
            }, indent=2))

    return 0


def print_device_info(device: SNPFile) -> None:
    """Print device information."""
    print("\nSNP File Loaded")
    print("=" * 40)
    print(f"File: {device.file_path}")
    print(f"Ports: {device.num_ports}")
    print(f"Frequency Range: {device.frequency[0]/1e9:.3f} - {device.frequency[-1]/1e9:.3f} GHz")
    print(f"Frequency Points: {device.num_frequency_points}")
    print(f"Reference Impedance: {device.reference_impedance} Ω")
    print()

    # Show impedance at key frequencies
    print("Impedance Trajectory:")
    indices = [0, len(device.frequency) // 2, -1]
    for idx in indices:
        freq = device.frequency[idx]
        z = device.impedance_at_frequency(freq)
        rl = device.get_return_loss_db()[idx]
        print(f"  @ {freq/1e9:.3f} GHz: {z.real:.1f} + {z.imag:.1f}j Ω (RL: {rl:.1f} dB)")


def print_library_info(library: ComponentLibrary) -> None:
    """Print library information."""
    print("\nComponent Library Indexed")
    print("=" * 40)
    print(f"Folder: {library.library_path}")
    print(f"Components Found: {library.num_components}")
    print(f"  - Capacitors: {library.num_capacitors}")
    print(f"  - Inductors: {library.num_inductors}")

    summary = library.get_summary()
    if "frequency_range_ghz" in summary:
        fr = summary["frequency_range_ghz"]
        print(f"  - Frequency Range: {fr[0]:.3f} - {fr[1]:.3f} GHz")
    print()


def print_search_results(results: list, query: str) -> None:
    """Print search results."""
    print(f"\nSearch Results: \"{query}\"")
    print("=" * 40)
    print(f"Found: {len(results)} components\n")

    for i, comp in enumerate(results[:10], 1):
        print(f"{i}. {comp.part_number} ({comp.manufacturer})")
        print(f"   Type: {comp.component_type.value}")
        print(f"   Value: {comp.value or 'N/A'}")
        fr = comp.frequency_range
        print(f"   Frequency: {fr[0]/1e9:.3f} - {fr[1]/1e9:.3f} GHz")
        print()

    if len(results) > 10:
        print(f"... and {len(results) - 10} more")


def print_optimization_result(result) -> None:
    """Print optimization result."""
    print("\nOptimization Result")
    print("=" * 40)
    print(f"Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    print(f"Topology: {result.topology_selected.value}")
    print()

    print("Selected Components:")
    for i, (comp, order) in enumerate(
        zip(result.matching_network.components, result.matching_network.component_order)
    ):
        print(f"  Stage {i+1} ({order.upper()}):")
        print(f"    {comp.manufacturer} {comp.part_number}")
        print(f"    Type: {comp.component_type.value}, Value: {comp.value or 'N/A'}")
    print()

    print("Metrics:")
    metrics = result.optimization_metrics
    if metrics:
        print(f"  Reflection at center: {metrics.get('reflection_coefficient_at_center', 'N/A'):.4f}")
        print(f"  VSWR at center: {metrics.get('vswr_at_center', 'N/A'):.3f}")
        print(f"  Return Loss: {metrics.get('return_loss_at_center_dB', 'N/A'):.1f} dB")
        print(f"  Max VSWR in band: {metrics.get('max_vswr_in_band', 'N/A'):.3f}")
        z = metrics.get('impedance_at_center')
        if z:
            print(f"  Impedance at center: {z.real:.1f} + {z.imag:.1f}j Ω")
        print(f"  Iterations: {metrics.get('grid_search_iterations', 'N/A')}")
        print(f"  Duration: {metrics.get('grid_search_duration_sec', 'N/A'):.2f} sec")
    print()

    print("Schematic:")
    print(f"  {result.matching_network.get_schematic_text()}")


def parse_frequency(freq_str: str) -> float:
    """Parse frequency string to Hz.

    Accepts:
    - Plain numbers (assumed Hz)
    - Numbers with suffix: 1G, 2.4G, 100M, 1000k
    """
    freq_str = freq_str.strip().upper()

    multipliers = {
        "G": 1e9,
        "GHZ": 1e9,
        "M": 1e6,
        "MHZ": 1e6,
        "K": 1e3,
        "KHZ": 1e3,
        "HZ": 1,
    }

    for suffix, mult in multipliers.items():
        if freq_str.endswith(suffix):
            num_str = freq_str[: -len(suffix)]
            return float(num_str) * mult

    # Default: assume Hz
    return float(freq_str)


if __name__ == "__main__":
    sys.exit(main())
