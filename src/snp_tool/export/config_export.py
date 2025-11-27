"""Component configuration export functionality.

Implements Task 3.1.2: Export component configurations in JSON/YAML/CSV formats.
"""

import json
import csv
from pathlib import Path
from typing import List, Union, Dict, Any
from datetime import datetime

from ..models.component import MatchingComponent
from ..utils.exceptions import SNPToolError


def export_config(components: List[MatchingComponent],
                  output_path: Union[str, Path],
                  format: str = 'json',
                  metadata: Dict[str, Any] = None) -> None:
    """Export component configuration to file.
    
    Args:
        components: List of matching components to export
        output_path: Path to output file
        format: Export format ('json', 'yaml', or 'csv')
        metadata: Optional metadata (source network, export date, tool version)
        
    Raises:
        SNPToolError: If export fails or format is invalid
    """
    output_path = Path(output_path)
    format = format.lower()
    
    # Prepare metadata
    if metadata is None:
        metadata = {}
    
    metadata.setdefault('export_date', datetime.now().isoformat())
    metadata.setdefault('tool_version', '0.1.0')
    metadata.setdefault('component_count', len(components))
    
    try:
        if format == 'json':
            _export_json(components, output_path, metadata)
        elif format == 'yaml':
            _export_yaml(components, output_path, metadata)
        elif format == 'csv':
            _export_csv(components, output_path, metadata)
        else:
            raise SNPToolError(f"Unsupported export format: {format}")
            
    except SNPToolError:
        raise
    except Exception as e:
        raise SNPToolError(f"Failed to export configuration: {e}")


def _export_json(components: List[MatchingComponent], 
                 output_path: Path,
                 metadata: Dict[str, Any]) -> None:
    """Export to JSON format."""
    data = {
        'metadata': metadata,
        'components': [
            {
                'id': comp.id,
                'port': comp.port,
                'type': comp.component_type.value,
                'value': comp.value,
                'value_display': comp.value_display,
                'placement': comp.placement.value,
                'order': comp.order,
                'created_at': comp.created_at.isoformat()
            }
            for comp in components
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)


def _export_yaml(components: List[MatchingComponent],
                 output_path: Path, 
                 metadata: Dict[str, Any]) -> None:
    """Export to YAML format."""
    try:
        import yaml
    except ImportError:
        raise SNPToolError("PyYAML not installed. Install with: pip install pyyaml")
    
    data = {
        'metadata': metadata,
        'components': [
            {
                'id': comp.id,
                'port': comp.port,
                'type': comp.component_type.value,
                'value': comp.value,
                'value_display': comp.value_display,
                'placement': comp.placement.value,
                'order': comp.order,
                'created_at': comp.created_at.isoformat()
            }
            for comp in components
        ]
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _export_csv(components: List[MatchingComponent],
                output_path: Path,
                metadata: Dict[str, Any]) -> None:
    """Export to CSV format for spreadsheet compatibility."""
    with open(output_path, 'w', newline='') as f:
        # Write metadata as comments
        f.write(f"# Export Date: {metadata.get('export_date', 'N/A')}\n")
        f.write(f"# Tool Version: {metadata.get('tool_version', 'N/A')}\n")
        f.write(f"# Source Network: {metadata.get('source_network', 'N/A')}\n")
        f.write(f"# Component Count: {metadata.get('component_count', len(components))}\n")
        f.write("#\n")
        
        writer = csv.DictWriter(f, fieldnames=[
            'id', 'port', 'type', 'value', 'value_display', 
            'placement', 'order', 'created_at'
        ])
        writer.writeheader()
        
        for comp in components:
            writer.writerow({
                'id': comp.id,
                'port': comp.port,
                'type': comp.component_type.value,
                'value': comp.value,
                'value_display': comp.value_display,
                'placement': comp.placement.value,
                'order': comp.order,
                'created_at': comp.created_at.isoformat()
            })
