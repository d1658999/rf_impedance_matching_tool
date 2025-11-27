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
            click.echo(f"  {i}. {comp.component_type.value.capitalize()} {comp.value_display} ({comp.placement_type.value})")
    
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
            fig = plot_smith_chart(network, port=port, title=f"Smith Chart - Port {port}")
        elif plot_type == 'vswr':
            from ..visualization.rectangular import plot_vswr
            fig = plot_vswr(network, port=port)
        elif plot_type == 'return-loss':
            from ..visualization.rectangular import plot_return_loss
            fig = plot_return_loss(network, port=port)
        elif plot_type == 's-parameters':
            from ..visualization.rectangular import plot_s_parameters
            fig = plot_s_parameters(network, port=port)
        
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


if __name__ == '__main__':
    cli()
