"""CLI commands for SNP Tool.

Implements Click-based CLI interface following Task 1.3.3.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click

from ..controller import ImpedanceMatchingController
from ..parsers.touchstone import parse as parse_snp
from ..validators.snp_validator import validate_snp_file
from ..utils.exceptions import SNPToolError


# Create a context object to share state between commands
class CLIContext:
    """CLI context to share state between commands."""
    
    def __init__(self):
        self.controller = ImpedanceMatchingController()
        self.network_file = None
        

@click.group()
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), 
              default='INFO', help='Set logging verbosity')
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
@click.pass_context
def cli(ctx, log_level, json_output):
    """RF Impedance Matching Optimizer CLI."""
    ctx.ensure_object(CLIContext)
    ctx.obj.json_output = json_output
    ctx.obj.log_level = log_level
    
    # Suppress logging when JSON output is requested
    if json_output:
        import logging
        logging.getLogger('snp_tool').setLevel(logging.CRITICAL)


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--validate-only', is_flag=True, help='Only validate file, don\'t load')
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
@click.pass_context
def load(ctx, filepath, validate_only, json_output):
    """Load S-parameter file."""
    # Configure logging before any parsing
    if json_output:
        import logging
        logging.getLogger('snp_tool').setLevel(logging.CRITICAL)
        # Also configure the global logger if it exists
        from ..utils.logging import configure_logging
        configure_logging(verbose=False, json_output=False)
        logging.getLogger().setLevel(logging.CRITICAL)
    
    try:
        filepath = Path(filepath)
        
        # Validate file first
        validation_report = validate_snp_file(filepath)
        
        if not validation_report.is_valid:
            if json_output:
                output = {
                    "status": "error",
                    "errors": [
                        {"line": e.line_number, "message": e.message, "type": e.error_type}
                        for e in validation_report.errors
                    ]
                }
                click.echo(json.dumps(output, indent=2))
            else:
                click.echo(f"✗ Validation errors in {filepath.name}:")
                for error in validation_report.errors:
                    click.echo(f"  Line {error.line_number}: {error.message}")
            return sys.exit(2)
        
        if validate_only:
            if json_output:
                click.echo(json.dumps({"status": "success", "message": "File is valid"}, indent=2))
            else:
                click.echo(f"✓ {filepath.name} is valid")
            return
        
        # Load the network
        network = parse_snp(filepath)
        ctx.obj.controller.load_network(network, str(filepath))
        ctx.obj.network_file = filepath
        
        if json_output:
            freq_range_ghz = [
                network.frequency[0] / 1e9,
                network.frequency[-1] / 1e9
            ]
            output = {
                "status": "success",
                "network": {
                    "filepath": str(filepath),
                    "port_count": network.num_ports,
                    "frequency_range_ghz": freq_range_ghz,
                    "frequency_points": len(network.frequency),
                    "impedance_normalization": network.reference_impedance,
                    "format_type": "RI"  # Default for now
                }
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"✓ Loaded {network.num_ports}-port network from {filepath.name}")
            click.echo(f"  Frequency range: {network.frequency[0]/1e9:.2f} GHz - {network.frequency[-1]/1e9:.2f} GHz ({len(network.frequency)} points)")
            click.echo(f"  Impedance: {network.reference_impedance} Ω")
            
    except FileNotFoundError:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": "File not found"}, indent=2))
        else:
            click.echo(f"✗ File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            click.echo(f"✗ Error loading file: {e}")
        sys.exit(1)


@cli.command()
@click.option('--components', is_flag=True, help='Include component list')
@click.option('--metrics', is_flag=True, help='Include impedance metrics')
@click.pass_context
def info(ctx, components, metrics):
    """Display current network information."""
    controller = ctx.obj.controller
    
    if controller.network is None:
        click.echo("✗ No network loaded. Use 'load' command first.")
        sys.exit(1)
    
    network = controller.network
    
    click.echo(f"\nNetwork: {ctx.obj.network_file.name if ctx.obj.network_file else 'Unknown'} ({network.num_ports} ports)")
    click.echo(f"Frequency: {network.frequency[0]/1e9:.2f} - {network.frequency[-1]/1e9:.2f} GHz ({len(network.frequency)} points)")
    click.echo(f"Impedance: {network.reference_impedance} Ω")
    
    if components and controller.components:
        click.echo(f"\nComponents (Port 1):")
        for i, comp in enumerate(controller.components, 1):
            click.echo(f"  {i}. {comp.component_type.value.capitalize()} {comp.value_display} ({comp.placement.value})")
    
    if metrics:
        # Get metrics at center frequency
        center_idx = len(network.frequency) // 2
        center_freq = network.frequency[center_idx]
        metrics_data = controller.get_metrics()
        
        if metrics_data:
            click.echo(f"\nMetrics (Port 1 @ {center_freq/1e9:.2f} GHz):")
            if 'vswr' in metrics_data:
                vswr_at_center = metrics_data['vswr'][center_idx] if hasattr(metrics_data['vswr'], '__getitem__') else metrics_data['vswr']
                click.echo(f"  VSWR: {vswr_at_center:.2f}")
            if 'return_loss_db' in metrics_data:
                rl_at_center = metrics_data['return_loss_db'][center_idx] if hasattr(metrics_data['return_loss_db'], '__getitem__') else metrics_data['return_loss_db']
                click.echo(f"  Return Loss: {rl_at_center:.1f} dB")


@cli.command('add-component')
@click.option('--port', type=int, required=True, help='Port number (1-indexed)')
@click.option('--type', 'comp_type', type=click.Choice(['cap', 'ind']), required=True, help='Component type')
@click.option('--value', required=True, help='Component value (e.g., 10pF, 2.2nH)')
@click.option('--placement', type=click.Choice(['series', 'shunt']), required=True, help='Series or shunt')
@click.option('--show-result', is_flag=True, help='Display updated S-parameters')
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
@click.pass_context
def add_component(ctx, port, comp_type, value, placement, show_result, json_output):
    """Add matching component to port."""
    controller = ctx.obj.controller
    
    if controller.network is None:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": "No network loaded"}, indent=2))
        else:
            click.echo("✗ No network loaded. Use 'load' command first.")
        sys.exit(1)
    
    try:
        # Add component using controller
        controller.add_component(
            port=port,
            component_type=comp_type,
            value=value,
            placement=placement
        )
        
        if json_output:
            output = {
                "status": "success",
                "component": {
                    "port": port,
                    "type": comp_type,
                    "value": value,
                    "placement": placement,
                    "order": len(controller.components)
                }
            }
            click.echo(json.dumps(output, indent=2))
        else:
            comp_name = "capacitor" if comp_type == "cap" else "inductor"
            click.echo(f"✓ Added {comp_name} {value} to Port {port} ({placement})")
            click.echo(f"  Component order: {len(controller.components)} of 5 (max)")
            
            if show_result:
                metrics = controller.get_metrics()
                if metrics:
                    click.echo("\nUpdated metrics:")
                    click.echo(f"  VSWR: {metrics.get('vswr', 'N/A')}")
                    
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            click.echo(f"✗ Error adding component: {e}")
        
        # Determine appropriate exit code
        if "max" in str(e).lower() or "limit" in str(e).lower():
            sys.exit(3)  # Max components exceeded
        elif "invalid" in str(e).lower() or "value" in str(e).lower():
            sys.exit(4)  # Invalid component value
        elif "port" in str(e).lower():
            sys.exit(5)  # Port out of range
        else:
            sys.exit(1)


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--type', 'plot_type', type=click.Choice(['smith', 'vswr', 'return-loss', 's-parameters']),  
              default='smith', help='Plot type')
@click.option('--output', type=click.Path(), help='Save plot to file (PNG, PDF, SVG)')
@click.option('--show', is_flag=True, help='Display interactive plot')
@click.option('--port', type=int, default=1, help='Port to plot (default: 1)')
@click.pass_context
def plot(ctx, filepath, plot_type, output, show, port):
    """Generate plots from S-parameter file."""
    try:
        filepath = Path(filepath)
        
        # Load network
        network = parse_snp(filepath)
        
        # Generate requested plot
        if plot_type == 'smith':
            from ..visualization.smith_chart import plot_smith_chart
            fig = plot_smith_chart(network, title=f"Smith Chart - {filepath.name}")
        elif plot_type == 'vswr':
            from ..visualization.rectangular import plot_vswr
            fig, _ = plot_vswr(network, port=port)
        elif plot_type == 'return-loss':
            from ..visualization.rectangular import plot_return_loss
            fig, _ = plot_return_loss(network, port=port)
        elif plot_type == 's-parameters':
            from ..visualization.rectangular import plot_magnitude
            fig, _ = plot_magnitude(network, s_params=[(port-1, port-1)])
        
        # Save to file if requested
        if output:
            output_path = Path(output)
            fig.savefig(output_path, dpi=300, bbox_inches='tight')
            click.echo(f"✓ Plot saved to {output_path}")
        
        # Show interactive plot if requested
        if show:
            import matplotlib.pyplot as plt
            plt.show()
        
        # If neither output nor show, save to default location
        if not output and not show:
            default_name = f"{filepath.stem}_{plot_type}_{port}.png"
            fig.savefig(default_name, dpi=300, bbox_inches='tight')
            click.echo(f"✓ Plot saved to {default_name}")
            
    except FileNotFoundError:
        click.echo(f"✗ File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error generating plot: {e}")
        sys.exit(1)


@cli.command()
@click.option('--port', type=int, default=1, help='Port to optimize (default: 1)')
@click.option('--target-impedance', type=float, default=50.0, help='Target impedance in ohms (default: 50)')
@click.option('--freq-min', type=float, help='Minimum frequency (Hz)')
@click.option('--freq-max', type=float, help='Maximum frequency (Hz)')
@click.option('--mode', type=click.Choice(['ideal', 'standard']), default='ideal', 
              help='Optimization mode: ideal (continuous values) or standard (E-series)')
@click.option('--series', type=click.Choice(['E12', 'E24', 'E96']), default='E24',
              help='Component series for standard mode (default: E24)')
@click.option('--weights', type=str, default='return_loss=0.7,bandwidth=0.2,component_count=0.1',
              help='Metric weights (return_loss,bandwidth,vswr,component_count)')
@click.option('--max-components', type=int, default=3, help='Maximum components (default: 3)')
@click.option('--solutions', type=int, default=3, help='Number of solutions to return (default: 3)')
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
@click.pass_context
def optimize(ctx, port, target_impedance, freq_min, freq_max, mode, series, weights, 
             max_components, solutions, json_output):
    """Run automated impedance matching optimization.
    
    Optimizes component values for best impedance match based on weighted metrics.
    
    Example:
        snp-tool optimize --port 1 --target-impedance 50 --mode standard --series E24
    """
    try:
        controller = ctx.obj.controller
        
        # Ensure network is loaded
        if not controller.network:
            if json_output:
                click.echo(json.dumps({"status": "error", "message": "No network loaded. Use 'load' command first."}, indent=2))
            else:
                click.echo("✗ No network loaded. Use 'snp-tool load <file>' first.")
            sys.exit(1)
        
        # Parse weights
        weight_dict = {}
        for pair in weights.split(','):
            key, value = pair.split('=')
            weight_dict[key.strip()] = float(value.strip())
        
        # Determine frequency range
        if not freq_min or not freq_max:
            # Use full frequency range from network
            freq_min = freq_min or float(controller.network.frequencies[0])
            freq_max = freq_max or float(controller.network.frequencies[-1])
        
        # Show progress if not JSON mode
        if not json_output:
            click.echo(f"Optimizing Port {port} for {target_impedance}Ω impedance...")
            click.echo(f"  Frequency range: {freq_min/1e9:.2f} - {freq_max/1e9:.2f} GHz")
            click.echo(f"  Mode: {mode}")
            if mode == 'standard':
                click.echo(f"  Component series: {series}")
            click.echo(f"  Max components: {max_components}")
            click.echo(f"  Weights: {weight_dict}")
            click.echo("\nRunning optimization...")
        
        # Progress callback
        progress_bar = None
        def progress_callback(xk, convergence):
            if not json_output and progress_bar:
                progress_bar.update(1)
            return False  # Don't terminate
        
        # Create progress bar
        if not json_output:
            with click.progressbar(length=100, label='Optimizing') as progress_bar:
                # Run optimization through controller
                from ..optimizer.engine import OptimizationConfig, run_optimization
                
                config = OptimizationConfig(
                    port=port,
                    target_impedance=target_impedance,
                    frequency_range=(freq_min, freq_max),
                    weights=weight_dict,
                    mode='standard_values' if mode == 'standard' else 'ideal',
                    series=series,
                    max_components=max_components
                )
                
                results = run_optimization(controller.network, config, progress_callback=progress_callback)
        else:
            # No progress bar for JSON mode
            from ..optimizer.engine import OptimizationConfig, run_optimization
            
            config = OptimizationConfig(
                port=port,
                target_impedance=target_impedance,
                frequency_range=(freq_min, freq_max),
                weights=weight_dict,
                mode='standard_values' if mode == 'standard' else 'ideal',
                series=series,
                max_components=max_components
            )
            
            results = run_optimization(controller.network, config)
        
        # Get top N solutions
        top_solutions = results[:solutions]
        
        # Output results
        if json_output:
            output = {
                "status": "success",
                "solutions": [
                    {
                        "rank": i + 1,
                        "score": sol.score,
                        "components": [
                            {
                                "port": comp.port,
                                "type": comp.component_type.value,
                                "value": comp.value,
                                "value_display": comp.value_display,
                                "placement": comp.placement.value
                            }
                            for comp in sol.components
                        ],
                        "metrics": sol.metrics
                    }
                    for i, sol in enumerate(top_solutions)
                ]
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"\n✓ Optimization complete! Found {len(top_solutions)} solutions:\n")
            
            for i, sol in enumerate(top_solutions, 1):
                click.echo(f"Solution {i} (score: {sol.score:.4f}):")
                click.echo(f"  Components ({len(sol.components)}):")
                for comp in sol.components:
                    click.echo(f"    - {comp.component_type.value.capitalize()} {comp.value_display} ({comp.placement.value}) on Port {comp.port}")
                click.echo(f"  Metrics:")
                for key, value in sol.metrics.items():
                    click.echo(f"    - {key}: {value:.3f}")
                click.echo()
            
            # Prompt to apply solution
            if click.confirm("\nApply best solution to network?"):
                best = top_solutions[0]
                for comp in best.components:
                    controller.add_component(comp.port, comp.component_type, comp.value, comp.placement)
                click.echo("✓ Best solution applied to network")
                
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            click.echo(f"✗ Optimization error: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--snp', type=click.Path(), help='Export cascaded S-parameters to SNP file')
@click.option('--config', type=click.Path(), help='Export component configuration to JSON/YAML')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml', 'csv']), 
              default='json', help='Configuration export format (default: json)')
@click.option('--json', 'json_output', is_flag=True, help='Output status in JSON format')
@click.pass_context
def export(ctx, snp, config, output_format, json_output):
    """Export optimized network and component configuration.
    
    Examples:
        snp-tool export --snp matched.s2p --config components.json
        snp-tool export --config components.yaml --format yaml
    """
    try:
        controller = ctx.obj.controller
        
        # Ensure network is loaded
        if not controller.network:
            if json_output:
                click.echo(json.dumps({"status": "error", "message": "No network loaded"}, indent=2))
            else:
                click.echo("✗ No network loaded. Use 'snp-tool load <file>' first.")
            sys.exit(1)
        
        exported_files = []
        
        # Export SNP file if requested
        if snp:
            from ..export.snp_export import export_snp
            snp_path = Path(snp)
            export_snp(controller.network, snp_path)
            exported_files.append(str(snp_path))
            if not json_output:
                click.echo(f"✓ Exported S-parameters to {snp_path}")
        
        # Export component configuration if requested
        if config:
            from ..export.config_export import export_components
            config_path = Path(config)
            export_components(controller.components, config_path, output_format)
            exported_files.append(str(config_path))
            if not json_output:
                click.echo(f"✓ Exported component configuration to {config_path}")
        
        # JSON output
        if json_output:
            output = {
                "status": "success",
                "exported_files": exported_files
            }
            click.echo(json.dumps(output, indent=2))
        
        # No export requested
        if not snp and not config:
            if json_output:
                click.echo(json.dumps({"status": "error", "message": "No export target specified. Use --snp or --config"}, indent=2))
            else:
                click.echo("✗ No export target specified. Use --snp or --config option.")
            sys.exit(1)
            
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            click.echo(f"✗ Export error: {e}")
        sys.exit(1)


@cli.command()
@click.argument('session_file', type=click.Path())
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
@click.pass_context
def save_session(ctx, session_file, json_output):
    """Save current work session to file.
    
    Saves network state, components, and optimization results for later restoration.
    
    Example:
        snp-tool save-session my_design.session
    """
    try:
        controller = ctx.obj.controller
        
        # Ensure network is loaded
        if not controller.network:
            if json_output:
                click.echo(json.dumps({"status": "error", "message": "No network loaded"}, indent=2))
            else:
                click.echo("✗ No network loaded. Nothing to save.")
            sys.exit(1)
        
        # Create session file
        from ..utils.session_io import save_session as save_session_file
        from ..models.session import WorkSession
        
        session = WorkSession(
            snp_filepath=Path(controller.network_file) if controller.network_file else None,
            components=controller.components,
            optimization_results=getattr(controller, 'optimization_results', None),
            metadata={
                'target_impedance': getattr(controller, 'target_impedance', 50.0),
                'optimization_config': getattr(controller, 'optimization_config', {})
            }
        )
        
        save_session_file(session, session_file)
        
        if json_output:
            output = {
                "status": "success",
                "session_file": str(session_file),
                "components_count": len(controller.components)
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"✓ Session saved to {session_file}")
            click.echo(f"  Components: {len(controller.components)}")
            if controller.network:
                click.echo(f"  Network: {controller.network.ports} ports, {len(controller.network.frequencies)} frequency points")
            
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            click.echo(f"✗ Error saving session: {e}")
        sys.exit(1)


@cli.command()
@click.argument('session_file', type=click.Path(exists=True))
@click.option('--verify', is_flag=True, help='Verify SNP file checksum')
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
@click.pass_context
def load_session(ctx, session_file, verify, json_output):
    """Load previously saved work session.
    
    Restores network state, components, and optimization results from session file.
    
    Example:
        snp-tool load-session my_design.session --verify
    """
    try:
        controller = ctx.obj.controller
        
        # Load session
        from ..utils.session_io import load_session as load_session_file
        
        session = load_session_file(session_file, verify_checksum=verify)
        
        # Restore session to controller
        # Note: Controller needs load_from_session method
        if hasattr(controller, 'load_from_session'):
            controller.load_from_session(session)
        else:
            # Fallback: load network and components manually
            if session.snp_filepath:
                from ..parsers.touchstone import parse as parse_snp
                controller.network = parse_snp(session.snp_filepath)
                controller.network_file = str(session.snp_filepath)
            
            # Restore components
            controller.components = session.components
        
        if json_output:
            output = {
                "status": "success",
                "session_file": str(session_file),
                "snp_file": str(session.snp_filepath) if session.snp_filepath else None,
                "components_count": len(session.components),
                "created_at": session.created_at.isoformat() if hasattr(session, 'created_at') else None
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"✓ Session loaded from {session_file}")
            if session.snp_filepath:
                click.echo(f"  Network file: {session.snp_filepath}")
            click.echo(f"  Components: {len(session.components)}")
            if verify:
                click.echo(f"  ✓ SNP file checksum verified")
            
    except FileNotFoundError as e:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": f"Session file not found: {session_file}"}, indent=2))
        else:
            click.echo(f"✗ Session file not found: {session_file}")
        sys.exit(1)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            click.echo(f"✗ Error loading session: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    cli()
