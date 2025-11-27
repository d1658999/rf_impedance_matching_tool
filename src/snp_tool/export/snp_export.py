"""SNP file export functionality.

Implements Task 3.1.1: Export cascaded S-parameters to SNP file format.
"""

from pathlib import Path
from typing import Union
import numpy as np
import skrf as rf

from ..models.network import SParameterNetwork
from ..utils.exceptions import SNPToolError


def export_snp(network: Union[SParameterNetwork, rf.Network], 
               output_path: Union[str, Path],
               format_type: str = 'auto') -> None:
    """Export S-parameter network to Touchstone SNP file.
    
    Args:
        network: S-parameter network to export (SParameterNetwork or scikit-rf Network)
        output_path: Path to output file
        format_type: Format type ('RI', 'MA', 'DB', or 'auto' to preserve original)
        
    Raises:
        SNPToolError: If export fails or network is invalid
        
    Performance:
        Accuracy within 0.1 dB magnitude, 1 degree phase (SC-007)
    """
    output_path = Path(output_path)
    
    try:
        # Convert SParameterNetwork to scikit-rf Network if needed
        if hasattr(network, 'to_scikit_rf_network'):
            skrf_network = network.to_scikit_rf_network()
            original_format = network.format_type if format_type == 'auto' else format_type
            original_freq_unit = network.frequency_unit if hasattr(network, 'frequency_unit') else 'GHz'
        else:
            skrf_network = network
            original_format = format_type if format_type != 'auto' else 'MA'
            original_freq_unit = 'GHz'
        
        # Validate network before export
        try:
            if skrf_network.s is None or len(skrf_network.s) == 0:
                raise SNPToolError("Cannot export empty network")
        except AttributeError:
            raise SNPToolError("Cannot export empty network")
        
        # Write to file using scikit-rf's Touchstone export
        # The write_touchstone method preserves accuracy (SC-007)
        skrf_network.write_touchstone(
            str(output_path),
            form=original_format.lower() if original_format != 'DB' else 'db'
        )
        
    except SNPToolError:
        raise
    except Exception as e:
        raise SNPToolError(f"Failed to export SNP file: {e}")


def get_export_accuracy(original: rf.Network, exported: rf.Network) -> dict:
    """Verify export accuracy meets SC-007 requirements.
    
    Args:
        original: Original network
        exported: Exported and re-loaded network
        
    Returns:
        Dictionary with max magnitude error (dB) and max phase error (degrees)
    """
    # Calculate magnitude difference in dB
    mag_orig = np.abs(original.s)
    mag_export = np.abs(exported.s)
    mag_diff_db = 20 * np.log10(mag_export / (mag_orig + 1e-12))  # Avoid div by zero
    max_mag_error = np.max(np.abs(mag_diff_db))
    
    # Calculate phase difference in degrees
    phase_orig = np.angle(original.s, deg=True)
    phase_export = np.angle(exported.s, deg=True)
    phase_diff = phase_export - phase_orig
    # Normalize to -180 to 180
    phase_diff = (phase_diff + 180) % 360 - 180
    max_phase_error = np.max(np.abs(phase_diff))
    
    return {
        'max_magnitude_error_db': max_mag_error,
        'max_phase_error_deg': max_phase_error,
        'meets_sc007': max_mag_error < 0.1 and max_phase_error < 1.0
    }
