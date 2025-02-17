# tests/test_consumption_manager.py

"""Tests for consumption prediction and tracking."""

import pytest
from bess.consumption_manager import ConsumptionManager
from bess.settings import ConsumptionSettings, BatterySettings

@pytest.fixture
def consumption_settings():
    """Provide test consumption settings."""
    return ConsumptionSettings()

@pytest.fixture
def battery_settings():
    """Provide test battery settings."""
    return BatterySettings()

@pytest.fixture
def consumption_manager(consumption_settings, battery_settings):
    """Provide configured consumption manager."""
    return ConsumptionManager(consumption_settings, battery_settings)

class TestBasicFunctionality:
    """Basic consumption manager functionality tests."""
    
    def test_initial_state(self, consumption_manager, consumption_settings):
        """Test initial predictions."""
        predictions = consumption_manager.get_predictions()
        assert len(predictions) == 24
        assert all(p == consumption_settings.default_hourly for p in predictions)
        
    def test_update_consumption(self, consumption_manager):
        """Test basic consumption update."""
        test_hour = 12
        test_consumption = 6.0
        consumption_manager.update_consumption(
            hour=test_hour,
            grid_import=test_consumption,
            battery_soc=50.0
        )
        
        actual = consumption_manager.get_actual_consumption(test_hour)
        assert actual == test_consumption

class TestPredictionAdaptation:
    """Tests for consumption prediction adaptation."""
    
    def test_prediction_updates(self, consumption_manager):
        """Test prediction adaptation based on actuals."""
        # Update several hours with higher consumption
        for hour in range(5):
            consumption_manager.update_consumption(
                hour=hour,
                grid_import=6.0,
                battery_soc=50.0
            )
            
        predictions = consumption_manager.get_predictions()
        default = consumption_manager.settings.default_hourly
        assert any(p > default for p in predictions[5:]), "Predictions should adapt upward"
        
    def test_battery_impact(self, consumption_manager):
        """Test battery state impact on consumption calculation."""
        hour = 1
        # Simulate charging (SOC increase)
        consumption_manager.update_consumption(
            hour=hour,
            grid_import=5.0,
            battery_soc=60.0
        )
        consumption_manager.update_consumption(
            hour=hour+1,
            grid_import=5.0,
            battery_soc=70.0  # 10% increase
        )
        
        # Check that battery charging is factored into consumption
        energy_change = consumption_manager.calculate_energy_change(hour+1)
        assert energy_change > 0  # Positive change during charging
        
        actual = consumption_manager.get_actual_consumption(hour+1)
        assert actual > 5.0  # Total consumption includes battery charging

class TestCustomSettings:
    """Tests for custom settings."""
    
    def test_custom_consumption_settings(self):
        """Test manager with custom consumption settings."""
        settings = ConsumptionSettings()
        settings.default_hourly = 8.0
        settings.min_valid = 0.5
        
        manager = ConsumptionManager(consumption_settings=settings)
        predictions = manager.get_predictions()
        
        assert all(p == 8.0 for p in predictions)
        
        # Test minimum validation
        with pytest.raises(ValueError):
            manager.set_predictions([0.3] * 24)  # Below min_valid
            
    def test_custom_battery_settings(self):
        """Test manager with custom battery settings."""
        battery_settings = BatterySettings()
        battery_settings.total_capacity = 40.0  # Larger battery
        
        manager = ConsumptionManager(battery_settings=battery_settings)
        
        # Test energy calculation with larger battery
        manager.update_consumption(hour=0, grid_import=5.0, battery_soc=50.0)
        manager.update_consumption(hour=1, grid_import=5.0, battery_soc=60.0)
        
        energy_change = manager.calculate_energy_change(1)
        assert energy_change == 4.0  # 10% of 40 kWh

class TestValidation:
    """Input validation tests."""
    
    @pytest.mark.parametrize("invalid_hour", [-1, 24, 25])
    def test_invalid_hours(self, consumption_manager, invalid_hour):
        """Test invalid hour handling."""
        with pytest.raises(ValueError, match="Invalid hour"):
            consumption_manager.update_consumption(
                hour=invalid_hour,
                grid_import=4.5,
                battery_soc=50.0
            )
            
    def test_invalid_consumption(self, consumption_manager):
        """Test invalid consumption values."""
        with pytest.raises(ValueError):
            consumption_manager.update_consumption(
                hour=0,
                grid_import=-1.0,  # Negative consumption
                battery_soc=50.0
            )
            
    @pytest.mark.parametrize("invalid_soc", [-10, 101, 150])
    def test_invalid_battery_soc(self, consumption_manager, invalid_soc):
        """Test invalid battery SOC values."""
        with pytest.raises(ValueError):
            consumption_manager.update_consumption(
                hour=0,
                grid_import=4.5,
                battery_soc=invalid_soc
            )

class TestEnvironmentIntegration:
    """Tests for environment integration."""
    
    def test_consumption_propagation(self, test_env, consumption_manager):
        """Test consumption updates through test environment."""
        initial = consumption_manager.get_predictions()[0]
        
        # Update via test_env
        test_env(consumption_level=8.0)
        
        # Verify change in consumption_manager
        after = consumption_manager.get_predictions()[0]
        assert after == 8.0, f"Consumption not updated: was {initial}, now {after}"


class TestDailyOperations:
    """Tests for daily operations."""
    
    def test_daily_reset(self, consumption_manager):
        """Test daily reset functionality."""
        # Set some consumption data
        for hour in range(3):
            consumption_manager.update_consumption(
                hour=hour,
                grid_import=8.0,
                battery_soc=50.0
            )
            
        initial_predictions = consumption_manager.get_predictions()
        
        # Reset
        consumption_manager.reset_daily()
        
        # History should be cleared but predictions maintained
        assert consumption_manager.get_actual_consumption(0) is None
        assert consumption_manager.get_predictions() == initial_predictions
        
    def test_set_predictions(self, consumption_manager):
        """Test setting predictions directly."""
        test_value = 8.0
        consumption_manager.set_predictions([test_value] * 24)
        
        predictions = consumption_manager.get_predictions()
        assert all(p == test_value for p in predictions), "Predictions not updated correctly"
        
