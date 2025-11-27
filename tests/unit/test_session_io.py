"""Tests for session I/O functionality (Task 3.2.1)."""

import pytest
import json
from pathlib import Path
from datetime import datetime
import hashlib

from snp_tool.utils.session_io import save_session, load_session, _calculate_file_checksum
from snp_tool.models.session import WorkSession
from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
from snp_tool.utils.exceptions import SessionError


class TestSessionSaveLoad:
    """Test session save/load functionality."""
    
    @pytest.fixture
    def sample_session(self, tmp_path):
        """Create sample session for testing."""
        # Create a dummy SNP file
        snp_file = tmp_path / "test.s2p"
        snp_file.write_text("! Test SNP file\n# GHz S RI R 50\n1.0 0.1 0.2 0.3 0.4\n")
        
        components = [
            MatchingComponent(
                id="comp1",
                port=1,
                component_type=ComponentType.CAPACITOR,
                value=10e-12,
                placement=PlacementType.SERIES,
                order=0,
                created_at=datetime(2025, 1, 1, 12, 0, 0)
            )
        ]
        
        session = WorkSession(
            id="test-session-123",
            snp_filepath=snp_file,
            components=components,
            optimization_settings={'target_impedance': 50.0},
            created_at=datetime(2025, 1, 1, 10, 0, 0),
            modified_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        
        return session
    
    def test_save_session(self, tmp_path, sample_session):
        """Test save session creates JSON file."""
        output_file = tmp_path / "session.json"
        save_session(sample_session, output_file)
        
        assert output_file.exists()
        
        # Verify JSON structure
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert data['version'] == '1.0'
        assert data['id'] == 'test-session-123'
        assert len(data['components']) == 1
        assert data['optimization_settings']['target_impedance'] == 50.0
    
    def test_load_session(self, tmp_path, sample_session):
        """Test load session restores complete state."""
        session_file = tmp_path / "session.json"
        save_session(sample_session, session_file)
        
        loaded_session = load_session(session_file, verify_checksum=True)
        
        assert loaded_session.id == sample_session.id
        assert loaded_session.created_at == sample_session.created_at
        assert loaded_session.modified_at == sample_session.modified_at
        assert loaded_session.optimization_settings == sample_session.optimization_settings
        assert len(loaded_session.components) == 1
        assert loaded_session.components[0].id == 'comp1'
    
    def test_session_roundtrip(self, tmp_path, sample_session):
        """Test save → load → identical state (SC-012)."""
        session_file = tmp_path / "roundtrip.json"
        
        # Save
        save_session(sample_session, session_file)
        
        # Load
        loaded_session = load_session(session_file, verify_checksum=True)
        
        # Verify identical
        assert loaded_session.id == sample_session.id
        assert loaded_session.snp_filepath == sample_session.snp_filepath
        assert loaded_session.components[0].value == sample_session.components[0].value
    
    def test_load_session_checksum_verification(self, tmp_path, sample_session):
        """Test checksum verification detects file changes."""
        session_file = tmp_path / "session.json"
        save_session(sample_session, session_file)
        
        # Modify SNP file to break checksum
        sample_session.snp_filepath.write_text("! Modified file\n")
        
        with pytest.raises(SessionError, match="checksum mismatch"):
            load_session(session_file, verify_checksum=True)
    
    def test_load_session_skip_checksum(self, tmp_path, sample_session):
        """Test loading without checksum verification."""
        session_file = tmp_path / "session.json"
        save_session(sample_session, session_file)
        
        # Modify SNP file
        sample_session.snp_filepath.write_text("! Modified file\n")
        
        # Should succeed without verification
        loaded_session = load_session(session_file, verify_checksum=False)
        assert loaded_session.id == sample_session.id
    
    def test_load_missing_file_raises_error(self, tmp_path):
        """Test loading nonexistent file raises error."""
        with pytest.raises(SessionError, match="Session file not found"):
            load_session(tmp_path / "nonexistent.json")
    
    def test_load_missing_snp_file_raises_error(self, tmp_path, sample_session):
        """Test loading session with missing SNP file raises error."""
        session_file = tmp_path / "session.json"
        save_session(sample_session, session_file)
        
        # Remove SNP file
        sample_session.snp_filepath.unlink()
        
        with pytest.raises(SessionError, match="SNP file not found"):
            load_session(session_file, verify_checksum=True)
    
    def test_version_field_enables_future_migration(self, tmp_path, sample_session):
        """Test version field is saved for future compatibility."""
        session_file = tmp_path / "session.json"
        save_session(sample_session, session_file)
        
        with open(session_file, 'r') as f:
            data = json.load(f)
        
        assert 'version' in data
        assert data['version'] == '1.0'
    
    def test_save_session_with_optimization_results(self, tmp_path):
        """Test saving session with optimization results."""
        snp_file = tmp_path / "test.s2p"
        snp_file.write_text("! Test\n")
        
        session = WorkSession(
            id="opt-session",
            snp_filepath=snp_file,
            components=[],
            optimization_settings={'score': 0.95, 'iterations': 100},
            created_at=datetime.now(),
            modified_at=datetime.now()
        )
        
        session_file = tmp_path / "opt_session.json"
        save_session(session, session_file)
        
        loaded = load_session(session_file, verify_checksum=False)
        assert loaded.optimization_settings['score'] == 0.95
        assert loaded.optimization_settings['iterations'] == 100


class TestSessionPerformance:
    """Test session I/O performance (SC-012)."""
    
    def test_session_save_performance(self, tmp_path):
        """Test session save completes in <3 seconds."""
        snp_file = tmp_path / "perf_test.s2p"
        snp_file.write_text("! Perf test\n# GHz S RI R 50\n" + "1.0 0.1 0.2 0.3 0.4\n" * 1000)
        
        # Create session with many components
        components = [
            MatchingComponent(
                id=f"comp{i}",
                port=1,
                component_type=ComponentType.CAPACITOR,
                value=10e-12,
                placement=PlacementType.SERIES,
                order=i,
                created_at=datetime.now()
            )
            for i in range(5)
        ]
        
        session = WorkSession(
            id="perf-test",
            snp_filepath=snp_file,
            components=components,
            optimization_settings={},
            created_at=datetime.now(),
            modified_at=datetime.now()
        )
        
        session_file = tmp_path / "perf_session.json"
        
        # Benchmark should complete quickly
        import time
        start = time.time()
        save_session(session, session_file)
        duration = time.time() - start
        
        assert duration < 3.0, f"Save took {duration}s, expected <3s (SC-012)"
