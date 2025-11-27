"""
Work Session entity.

Represents a saved design state for session persistence (FR-020, FR-021).
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from snp_tool.models.component import MatchingComponent


@dataclass
class WorkSession:
    """Work Session entity from data-model.md."""
    
    id: str
    snp_filepath: Path
    components: List[MatchingComponent]
    optimization_settings: Dict[str, Any]
    created_at: datetime
    modified_at: datetime
