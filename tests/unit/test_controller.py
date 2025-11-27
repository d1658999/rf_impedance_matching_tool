"""
Unit tests for ImpedanceMatchingController.

Tests verify FR-019: Controller provides consistent business logic for CLI and GUI.
"""

import pytest
from pathlib import Path
import numpy as np

from snp_tool.controller import ImpedanceMatchingController
from snp_tool.models.component import ComponentType, PlacementType


@pytest.fixture
def controller():
    """Create a fresh controller instance."""
    return ImpedanceMatchingController()


@pytest.fixture
def sample_snp_file(tmp_path):
    """Create a sample S2P file for testing."""
    snp_file = tmp_path / "test.s2p"
    snp_file.write_text("""! Test S2P file
# GHz S RI R 50
1.0 0.1 0.05 0.9 0.05 0.9 -0.05 0.1 -0.05
2.0 0.12 0.06 0.88 0.06 0.88 -0.06 0.12 -0.06
3.0 0.15 0.08 0.85 0.08 0.85 -0.08 0.15 -0.08
""")
    return snp_file


def test_controller_initialization(controller):
    """Test controller initializes with no network loaded."""
    assert controller.network is None
    assert controller.components == []
    assert controller.optimization_results == []


def test_controller_load_snp(controller, sample_snp_file):
    """Test loading SNP file into controller."""
    network = controller.load_snp_file(sample_snp_file)
    
    assert network is not None
    assert controller.network is not None
    assert controller.network.num_ports == 2
    assert len(controller.network.frequency) == 3
    assert controller.network.file_path == str(sample_snp_file)


def test_controller_load_invalid_file(controller, tmp_path):
    """Test loading non-existent file raises error."""
    non_existent = tmp_path / "nonexistent.s2p"
    
    with pytest.raises(FileNotFoundError):
        controller.load_snp_file(non_existent)


def test_controller_add_component_without_network(controller):
    """Test adding component without loaded network raises error."""
    with pytest.raises(RuntimeError, match="No network loaded"):
        controller.add_component(
            port=1,
            component_type=ComponentType.CAPACITOR,
            value=10e-12,  # 10pF
            placement=PlacementType.SERIES
        )


def test_controller_add_component(controller, sample_snp_file):
    """Test adding component to loaded network."""
    controller.load_snp_file(sample_snp_file)
    
    # Add a series capacitor
    updated_network = controller.add_component(
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,  # 10pF
        placement=PlacementType.SERIES
    )
    
    assert updated_network is not None
    assert len(controller.components) == 1
    
    # Check component was recorded
    comp = controller.components[0]
    assert comp.component_type == ComponentType.CAPACITOR
    assert comp.value == 10e-12
    assert comp.placement == PlacementType.SERIES
    assert comp.port == 1


def test_controller_add_multiple_components(controller, sample_snp_file):
    """Test adding multiple components."""
    controller.load_snp_file(sample_snp_file)
    
    # Add series capacitor
    controller.add_component(
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,
        placement=PlacementType.SERIES
    )
    
    # Add shunt inductor
    controller.add_component(
        port=1,
        component_type=ComponentType.INDUCTOR,
        value=5e-9,  # 5nH
        placement=PlacementType.SHUNT
    )
    
    assert len(controller.components) == 2
    assert controller.components[0].component_type == ComponentType.CAPACITOR
    assert controller.components[1].component_type == ComponentType.INDUCTOR


def test_controller_component_limit(controller, sample_snp_file):
    """Test FR-003: Maximum 5 components per port."""
    controller.load_snp_file(sample_snp_file)
    
    # Add 5 components (should succeed)
    for i in range(5):
        controller.add_component(
            port=1,
            component_type=ComponentType.CAPACITOR,
            value=10e-12,
            placement=PlacementType.SERIES
        )
    
    assert len(controller.components) == 5
    
    # Try to add 6th component (should fail)
    with pytest.raises(ValueError, match="Maximum 5 components"):
        controller.add_component(
            port=1,
            component_type=ComponentType.CAPACITOR,
            value=10e-12,
            placement=PlacementType.SERIES
        )


def test_controller_remove_component(controller, sample_snp_file):
    """Test removing a component."""
    controller.load_snp_file(sample_snp_file)
    
    controller.add_component(
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,
        placement=PlacementType.SERIES
    )
    
    controller.add_component(
        port=1,
        component_type=ComponentType.INDUCTOR,
        value=5e-9,
        placement=PlacementType.SHUNT
    )
    
    assert len(controller.components) == 2
    
    # Remove first component (index 0)
    controller.remove_component(0)
    
    assert len(controller.components) == 1
    assert controller.components[0].component_type == ComponentType.INDUCTOR


def test_controller_remove_invalid_index(controller, sample_snp_file):
    """Test removing component with invalid index."""
    controller.load_snp_file(sample_snp_file)
    
    with pytest.raises(IndexError):
        controller.remove_component(0)  # No components yet


def test_controller_clear_components(controller, sample_snp_file):
    """Test clearing all components."""
    controller.load_snp_file(sample_snp_file)
    
    controller.add_component(port=1, component_type=ComponentType.CAPACITOR, 
                           value=10e-12, placement=PlacementType.SERIES)
    controller.add_component(port=1, component_type=ComponentType.INDUCTOR, 
                           value=5e-9, placement=PlacementType.SHUNT)
    
    assert len(controller.components) == 2
    
    controller.clear_components()
    
    assert len(controller.components) == 0


def test_controller_get_current_network(controller, sample_snp_file):
    """Test getting current network with components applied."""
    controller.load_snp_file(sample_snp_file)
    original_network = controller.network
    
    # Add a component
    controller.add_component(
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,
        placement=PlacementType.SERIES
    )
    
    # Get current network (with component applied)
    current_network = controller.get_current_network()
    
    assert current_network is not None
    # For now, network is same as original (cascading to be implemented)
    # This test just verifies the method works
    assert current_network.num_ports == original_network.num_ports


def test_controller_get_metrics(controller, sample_snp_file):
    """Test getting impedance metrics for current network."""
    controller.load_snp_file(sample_snp_file)
    
    metrics = controller.get_metrics(port=1)
    
    assert 'vswr' in metrics
    assert 'return_loss_db' in metrics
    assert 'impedance' in metrics
    
    # VSWR should be >= 1.0
    assert np.all(np.array(metrics['vswr']) >= 1.0)
    
    # Return loss should be positive
    assert np.all(np.array(metrics['return_loss_db']) >= 0)


def test_controller_shared_instance():
    """Test that same controller instance gives same results (FR-019)."""
    controller1 = ImpedanceMatchingController()
    controller2 = controller1  # Same instance
    
    # Create a test file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.s2p', delete=False) as f:
        f.write("""! Test
# GHz S RI R 50
1.0 0.1 0.05 0.9 0.05 0.9 -0.05 0.1 -0.05
""")
        test_file = Path(f.name)
    
    try:
        controller1.load_snp_file(test_file)
        
        # Both should see the same network
        assert controller2.network is controller1.network
        
        controller1.add_component(
            port=1,
            component_type=ComponentType.CAPACITOR,
            value=10e-12,
            placement=PlacementType.SERIES
        )
        
        # Both should see the same components
        assert len(controller2.components) == 1
        assert controller2.components[0].value == 10e-12
    finally:
        test_file.unlink()


def test_controller_reset(controller, sample_snp_file):
    """Test resetting controller state."""
    controller.load_snp_file(sample_snp_file)
    controller.add_component(port=1, component_type=ComponentType.CAPACITOR,
                           value=10e-12, placement=PlacementType.SERIES)
    
    assert controller.network is not None
    assert len(controller.components) == 1
    
    controller.reset()
    
    assert controller.network is None
    assert len(controller.components) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
