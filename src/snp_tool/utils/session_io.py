"""Session I/O functionality for save/load work sessions.

Implements Task 3.2.1: Session save/load with complete state preservation.
"""

import json
import hashlib
from pathlib import Path
from typing import Union, Dict, Any, Optional
from datetime import datetime

from ..models.session import WorkSession
from ..models.network import SParameterNetwork
from ..models.component import MatchingComponent, ComponentType, PlacementType
from ..utils.exceptions import SNPToolError, SessionError


def save_session(session: WorkSession, 
                 output_path: Union[str, Path]) -> None:
    """Save work session to JSON file.
    
    Args:
        session: WorkSession object to save
        output_path: Path to output session file
        
    Raises:
        SessionError: If save fails
        
    Performance:
        <3 seconds for save (SC-012)
    """
    output_path = Path(output_path)
    
    try:
        # Calculate SNP file checksum if file exists
        snp_checksum = None
        if session.snp_filepath and session.snp_filepath.exists():
            snp_checksum = _calculate_file_checksum(session.snp_filepath)
        
        # Serialize session to dictionary
        session_data = {
            'version': '1.0',
            'id': session.id,
            'created_at': session.created_at.isoformat(),
            'modified_at': session.modified_at.isoformat(),
            'snp_filepath': str(session.snp_filepath) if session.snp_filepath else None,
            'snp_file_checksum': snp_checksum,
            'components': [
                {
                    'id': comp.id,
                    'port': comp.port,
                    'component_type': comp.component_type.value,
                    'value': comp.value,
                    'placement': comp.placement.value,
                    'order': comp.order,
                    'created_at': comp.created_at.isoformat()
                }
                for comp in session.components
            ],
            'optimization_settings': session.optimization_settings
        }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(session_data, f, indent=2)
            
    except Exception as e:
        raise SessionError(f"Failed to save session: {e}")


def load_session(filepath: Union[str, Path],
                 verify_checksum: bool = True) -> WorkSession:
    """Load work session from JSON file.
    
    Args:
        filepath: Path to session file
        verify_checksum: If True, verify SNP file checksum matches
        
    Returns:
        WorkSession object with restored state
        
    Raises:
        SessionError: If load fails or checksum verification fails
        
    Performance:
        <3 seconds for load (SC-012)
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise SessionError(f"Session file not found: {filepath}")
    
    try:
        # Load JSON data
        with open(filepath, 'r') as f:
            session_data = json.load(f)
        
        # Validate version
        version = session_data.get('version', '1.0')
        if version != '1.0':
            raise SessionError(f"Unsupported session version: {version}")
        
        # Verify SNP file checksum if requested
        snp_filepath = session_data.get('snp_filepath')
        if verify_checksum and snp_filepath:
            snp_path = Path(snp_filepath)
            if not snp_path.exists():
                raise SessionError(f"SNP file not found: {snp_filepath}")
            
            actual_checksum = _calculate_file_checksum(snp_path)
            expected_checksum = session_data.get('snp_file_checksum')
            if expected_checksum and actual_checksum != expected_checksum:
                raise SessionError(
                    f"SNP file checksum mismatch. "
                    f"Expected {expected_checksum}, got {actual_checksum}. "
                    f"File may have been modified."
                )
        
        # Reconstruct components
        components = [
            MatchingComponent(
                id=comp_data['id'],
                port=comp_data['port'],
                component_type=ComponentType(comp_data['component_type']),
                value=comp_data['value'],
                placement=PlacementType(comp_data['placement']),
                order=comp_data['order'],
                created_at=datetime.fromisoformat(comp_data['created_at'])
            )
            for comp_data in session_data.get('components', [])
        ]
        
        # Create WorkSession object
        session = WorkSession(
            id=session_data['id'],
            snp_filepath=Path(snp_filepath) if snp_filepath else None,
            components=components,
            optimization_settings=session_data.get('optimization_settings', {}),
            created_at=datetime.fromisoformat(session_data['created_at']),
            modified_at=datetime.fromisoformat(session_data['modified_at'])
        )
        
        return session
        
    except SessionError:
        raise
    except Exception as e:
        raise SessionError(f"Failed to load session: {e}")


def _calculate_file_checksum(filepath: Path) -> str:
    """Calculate MD5 checksum of file.
    
    Args:
        filepath: Path to file
        
    Returns:
        MD5 checksum as hex string
    """
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            md5.update(chunk)
    return md5.hexdigest()


def migrate_session(session_data: Dict[str, Any], 
                    from_version: str,
                    to_version: str = '1.0') -> Dict[str, Any]:
    """Migrate session data between versions.
    
    Args:
        session_data: Session data dictionary
        from_version: Source version
        to_version: Target version
        
    Returns:
        Migrated session data
        
    Note:
        Future-proofing for version compatibility. Currently only v1.0 exists.
    """
    if from_version == to_version:
        return session_data
    
    # Placeholder for future migrations
    raise SessionError(f"Migration from {from_version} to {to_version} not supported")
