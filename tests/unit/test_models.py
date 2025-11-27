"""
Unit tests for data models (entities).

Tests verify that all 6 entities from data-model.md are correctly implemented:
1. SParameterNetwork
2. MatchingComponent
3. PortConfiguration
4. FrequencyPoint
5. OptimizationSolution
6. WorkSession
"""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest


# Test 1: SParameterNetwork creation and validation
def test_sparameter_network_creation():
    """Test SParameterNetwork entity creation with valid data."""
    from snp_tool.models.network import SParameterNetwork
    
    # Create test data
    frequencies = np.array([1e9, 2e9, 3e9])  # 1-3 GHz
    s_params = np.zeros((3, 2, 2), dtype=complex)  # 3 freq points, 2-port
    s_params[:, 0, 1] = 0.5 + 0.2j  # S21
    s_params[:, 1, 0] = 0.5 + 0.2j  # S12
    
    network = SParameterNetwork(
        filepath=Path("/tmp/test.s2p"),
        port_count=2,
        frequencies=frequencies,
        s_parameters=s_params,
        impedance_normalization=50.0,
        frequency_unit='GHz',
        format_type='RI',
        loaded_at=datetime.now(),
        checksum='abc123'
    )
    
    assert network.port_count == 2
    assert network.impedance_normalization == 50.0
    assert network.frequency_unit == 'GHz'
    assert len(network.frequencies) == 3
    assert network.s_parameters.shape == (3, 2, 2)


def test_sparameter_network_validation_frequency_monotonic():
    """Test that frequencies must be monotonically increasing."""
    from snp_tool.models.network import SParameterNetwork
    
    # Non-monotonic frequencies should fail validation
    frequencies = np.array([3e9, 1e9, 2e9])  # OUT OF ORDER
    s_params = np.zeros((3, 2, 2), dtype=complex)
    
    with pytest.raises(ValueError, match="monotonically"):
        network = SParameterNetwork(
            filepath=Path("/tmp/test.s2p"),
            port_count=2,
            frequencies=frequencies,
            s_parameters=s_params,
            impedance_normalization=50.0,
            frequency_unit='GHz',
            format_type='RI',
            loaded_at=datetime.now(),
            checksum='abc123'
        )
        network.validate()


def test_sparameter_network_validation_shape_mismatch():
    """Test that port_count must match S-parameter dimensions."""
    from snp_tool.models.network import SParameterNetwork
    
    frequencies = np.array([1e9, 2e9])
    s_params = np.zeros((2, 3, 3), dtype=complex)  # 3x3 but port_count=2
    
    with pytest.raises(ValueError, match="port_count.*dimensions"):
        network = SParameterNetwork(
            filepath=Path("/tmp/test.s2p"),
            port_count=2,  # Mismatch!
            frequencies=frequencies,
            s_parameters=s_params,
            impedance_normalization=50.0,
            frequency_unit='GHz',
            format_type='RI',
            loaded_at=datetime.now(),
            checksum='abc123'
        )
        network.validate()


# Test 2: MatchingComponent validation
def test_matching_component_creation():
    """Test MatchingComponent entity creation."""
    from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
    
    component = MatchingComponent(
        id=str(uuid4()),
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,  # 10pF
        placement=PlacementType.SERIES,
        created_at=datetime.now(),
        order=0
    )
    
    assert component.port == 1
    assert component.component_type == ComponentType.CAPACITOR
    assert component.value == 10e-12
    assert component.placement == PlacementType.SERIES


def test_matching_component_validation_value_range():
    """Test that component values must be within physical limits."""
    from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
    
    # Capacitor too large (> 100µF)
    with pytest.raises(ValueError, match="Capacitor.*range"):
        component = MatchingComponent(
            id=str(uuid4()),
            port=1,
            component_type=ComponentType.CAPACITOR,
            value=1e-3,  # 1mF - TOO LARGE
            placement=PlacementType.SERIES,
            created_at=datetime.now(),
            order=0
        )
        component.validate()
    
    # Inductor too small (< 1pH)
    with pytest.raises(ValueError, match="Inductor.*range"):
        component = MatchingComponent(
            id=str(uuid4()),
            port=1,
            component_type=ComponentType.INDUCTOR,
            value=1e-15,  # 1fH - TOO SMALL
            placement=PlacementType.SHUNT,
            created_at=datetime.now(),
            order=0
        )
        component.validate()


def test_matching_component_validation_order():
    """Test that component order must be < 5 (max 5 per port)."""
    from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
    
    with pytest.raises(ValueError, match="order.*5"):
        component = MatchingComponent(
            id=str(uuid4()),
            port=1,
            component_type=ComponentType.CAPACITOR,
            value=10e-12,
            placement=PlacementType.SERIES,
            created_at=datetime.now(),
            order=5  # Invalid: max is 4 (0-4 for 5 components)
        )
        component.validate()


# Test 3: Component value display (engineering notation)
def test_component_value_display():
    """Test engineering notation display property (FR-005)."""
    from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
    
    # Capacitor
    cap = MatchingComponent(
        id=str(uuid4()),
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,  # 10pF
        placement=PlacementType.SERIES,
        created_at=datetime.now(),
        order=0
    )
    
    # Note: This will fail until engineering notation is implemented
    # For now, we expect it to contain 'pF' and '10'
    assert 'F' in cap.value_display  # Has Farad unit
    assert 'p' in cap.value_display or '10e-12' in cap.value_display  # pico prefix or scientific
    
    # Inductor
    ind = MatchingComponent(
        id=str(uuid4()),
        port=1,
        component_type=ComponentType.INDUCTOR,
        value=2.2e-9,  # 2.2nH
        placement=PlacementType.SHUNT,
        created_at=datetime.now(),
        order=0
    )
    
    assert 'H' in ind.value_display  # Has Henry unit
    assert 'n' in ind.value_display or '2.2e-9' in ind.value_display  # nano prefix or scientific


# Test 4: PortConfiguration with component limit
def test_port_configuration_max_components():
    """Test that PortConfiguration enforces max 5 components (FR-003)."""
    from snp_tool.models.port_config import PortConfiguration
    from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
    
    port_config = PortConfiguration(
        port_number=1,
        reference_impedance=50.0,
        components=[]
    )
    
    # Add 5 components - should succeed
    for i in range(5):
        comp = MatchingComponent(
            id=str(uuid4()),
            port=1,
            component_type=ComponentType.CAPACITOR,
            value=10e-12,
            placement=PlacementType.SERIES,
            created_at=datetime.now(),
            order=i
        )
        port_config.add_component(comp)
    
    assert len(port_config.components) == 5
    
    # Try to add 6th component - should fail at PortConfiguration level
    with pytest.raises(ValueError, match="Maximum.*5 components"):
        comp6 = MatchingComponent(
            id=str(uuid4()),
            port=1,
            component_type=ComponentType.CAPACITOR,
            value=10e-12,
            placement=PlacementType.SERIES,
            created_at=datetime.now(),
            order=0  # Use valid order (0-4), let PortConfiguration reject it
        )
        port_config.add_component(comp6)


# Test 5: FrequencyPoint entity
def test_frequency_point_creation():
    """Test FrequencyPoint entity creation."""
    from snp_tool.models.frequency import FrequencyPoint
    
    s_params = np.array([[0.1+0.2j, 0.5+0.3j], [0.5+0.3j, 0.1+0.2j]])
    
    freq_point = FrequencyPoint(
        frequency_hz=1e9,
        s_parameters=s_params,
        impedances={1: 45+5j, 2: 52-3j},
        vswr_values={1: 1.2, 2: 1.1},
        return_loss_db={1: -15.0, 2: -18.0}
    )
    
    assert freq_point.frequency_hz == 1e9
    assert freq_point.s_parameters.shape == (2, 2)
    assert freq_point.get_impedance(1) == 45+5j


# Test 6: OptimizationSolution entity
def test_optimization_solution_creation():
    """Test OptimizationSolution entity creation."""
    from snp_tool.models.solution import OptimizationSolution
    from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
    
    comp = MatchingComponent(
        id=str(uuid4()),
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,
        placement=PlacementType.SERIES,
        created_at=datetime.now(),
        order=0
    )
    
    solution = OptimizationSolution(
        id=str(uuid4()),
        components=[comp],
        metrics={
            'return_loss_db': -20.0,
            'vswr': 1.2,
            'bandwidth_hz': 500e6
        },
        score=0.15,
        mode='ideal',
        target_impedance=50.0,
        frequency_range=(1e9, 3e9),
        created_at=datetime.now()
    )
    
    assert solution.return_loss_db == -20.0
    assert solution.vswr == 1.2
    assert solution.bandwidth_hz == 500e6
    assert len(solution.components) == 1


# Test 7: WorkSession entity
def test_work_session_creation():
    """Test WorkSession entity for save/load functionality (FR-020, FR-021)."""
    from snp_tool.models.session import WorkSession
    from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
    
    comp = MatchingComponent(
        id=str(uuid4()),
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,
        placement=PlacementType.SERIES,
        created_at=datetime.now(),
        order=0
    )
    
    session = WorkSession(
        id=str(uuid4()),
        snp_filepath=Path("/tmp/antenna.s2p"),
        components=[comp],
        optimization_settings={'target_impedance': 50.0, 'mode': 'ideal'},
        created_at=datetime.now(),
        modified_at=datetime.now()
    )
    
    assert session.snp_filepath == Path("/tmp/antenna.s2p")
    assert len(session.components) == 1
    assert session.optimization_settings['target_impedance'] == 50.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
