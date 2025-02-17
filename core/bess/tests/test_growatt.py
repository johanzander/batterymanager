# tests/test_growatt.py

"""Tests for Growatt schedule management."""

import pytest
from bess.growatt_schedule import GrowattScheduleManager
from bess.settings import BatterySettings

@pytest.fixture
def battery_settings():
    """Provide battery settings."""
    return BatterySettings()

@pytest.fixture
def schedule_manager():
    """Provide schedule manager instance."""
    return GrowattScheduleManager()

class TestIntervalConversion:
    """Tests for schedule to TOU interval conversion."""
    
    def test_simple_intervals(self, schedule_manager, create_test_schedule):
        """Test conversion of simple charging/discharging pattern."""
        # Charge in morning, discharge in evening
        actions = [0.0] * 24
        actions[4] = 6.0  # Charge at 04:00
        actions[18] = -5.2  # Discharge at 18:00
        
        schedule = create_test_schedule(actions)
        schedule_manager.apply_schedule(schedule)
        intervals = schedule_manager.get_daily_TOU_settings()
        
        # Should create battery-first interval for charging hour
        assert any(i["start_time"] == "04:00" and i["batt_mode"] == "battery-first" 
                  for i in intervals)
        # Other times should be load-first
        
    def test_wake_up_periods(self, schedule_manager, create_test_schedule):
        """Test insertion of wake-up periods before charging."""
        actions = [0.0] * 24
        actions[6] = 6.0  # Charge after idle
        
        schedule = create_test_schedule(actions)
        schedule_manager.apply_schedule(schedule)
        detailed = schedule_manager.detailed_intervals
        
        # Should find wake-up period before charge
        wake_periods = [i for i in detailed 
                       if i["batt_mode"] == "load-first" and 
                          i["end_time"] == "05:59"]
        assert len(wake_periods) > 0

class TestHourlySettings:
    """Tests for hourly schedule settings."""
    
    def test_charging_settings(self, schedule_manager, create_test_schedule):
        """Test settings during charging hours."""
        actions = [0.0] * 24
        actions[4] = 6.0  # Charging at hour 4
        
        schedule = create_test_schedule(actions)
        schedule_manager.apply_schedule(schedule)
        
        settings = schedule_manager.get_hourly_settings(4)
        assert settings["grid_charge"] is True
        assert settings["discharge_rate"] == 0
        
    def test_discharging_settings(self, schedule_manager, create_test_schedule):
        """Test settings during discharging hours."""
        actions = [0.0] * 24
        actions[18] = -5.2  # Discharging at hour 18
        
        schedule = create_test_schedule(actions)
        schedule_manager.apply_schedule(schedule)
        
        settings = schedule_manager.get_hourly_settings(18)
        assert settings["grid_charge"] is False
        assert settings["discharge_rate"] == 100
        
    def test_standby_settings(self, schedule_manager, create_test_schedule):
        """Test settings during standby hours."""
        actions = [0.0] * 24
        
        schedule = create_test_schedule(actions)
        schedule_manager.apply_schedule(schedule)
        
        settings = schedule_manager.get_hourly_settings(12)
        assert settings["grid_charge"] is False
        assert settings["discharge_rate"] == 0
        
    @pytest.mark.parametrize("hour", [-1, 24, 25])
    def test_invalid_hours(self, schedule_manager, create_test_schedule, hour):
        """Test settings for invalid hours."""
        actions = [0.0] * 24
        schedule = create_test_schedule(actions)
        schedule_manager.apply_schedule(schedule)
        
        settings = schedule_manager.get_hourly_settings(hour)
        assert settings["grid_charge"] is False
        assert settings["discharge_rate"] == 0

class TestGrowattConstraints:
    """Tests for Growatt-specific constraints."""
    
    def test_max_intervals(self, schedule_manager, create_test_schedule):
        """Test maximum number of TOU intervals constraint."""
        # Create alternating pattern to generate many intervals
        actions = [0.0] * 24
        for i in range(0, 24, 2):
            actions[i] = 6.0
        
        schedule = create_test_schedule(actions)
        schedule_manager.apply_schedule(schedule)
        intervals = schedule_manager.get_daily_TOU_settings()
        
        assert len(intervals) <= schedule_manager.max_intervals
        
    def test_end_of_day(self, schedule_manager, create_test_schedule):
        """Test end of day handling."""
        actions = [0.0] * 24
        actions[23] = 6.0  # Action at last hour
        
        schedule = create_test_schedule(actions)
        schedule_manager.apply_schedule(schedule)
        detailed = schedule_manager.detailed_intervals
        
        # Last regular interval should end at 23:44
        assert any(i["end_time"] == "23:44" for i in detailed)
        
        # Should have final load-first period
        last_interval = detailed[-1]
        assert last_interval["start_time"] == "23:45"
        assert last_interval["end_time"] == "23:59"
        assert last_interval["batt_mode"] == "load-first"

class TestBatterySettings:
    """Tests using battery settings."""
    
    def test_custom_settings(self, create_test_schedule):
        """Test manager with custom battery settings."""
        settings = BatterySettings()
        settings.max_charge_power_kw = 8.0  # Different max charge rate
        
        manager = GrowattScheduleManager()
        actions = [0.0] * 24
        actions[12] = 8.0  # Use new max rate
        
        schedule = create_test_schedule(actions)
        manager.apply_schedule(schedule)
        
        settings = manager.get_hourly_settings(12)
        assert settings["grid_charge"] is True