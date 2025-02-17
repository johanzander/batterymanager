# tests/test_system.py

"""Integration tests for BatterySystemManager."""

import pytest
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TestSchedulePreparation:
    """Tests for schedule preparation."""
    
    def test_prepare_with_defaults(self, system):
        """Test schedule preparation using default prices."""
        schedule = system.prepare_schedule()
        assert schedule is not None
        
    def test_prepare_with_explicit_prices(self, system, flat_prices):
        """Test schedule preparation with explicitly provided prices."""
        schedule = system.prepare_schedule(flat_prices)
        assert schedule is not None
        
    def test_prepare_with_peak_prices(self, system, peak_prices):
        """Test schedule preparation with varying prices."""
        schedule = system.prepare_schedule(peak_prices)
        assert schedule is not None

class TestHourValidation:
    """Tests for hour validation and processing."""
    
    @pytest.mark.parametrize("hour", [0, 12, 23])
    def test_valid_hours(self, system, hour, flat_prices):
        """Test operations with valid hours."""
        schedule = system.prepare_schedule(flat_prices)
        system.update_state(hour)
        system.apply_schedule(hour)
        system.verify_inverter_settings(hour)
        
    @pytest.mark.parametrize("hour", [-1, 24, 25])
    def test_invalid_hours(self, system, hour):
        """Test error handling with invalid hours."""
        with pytest.raises(ValueError, match="Invalid hour"):
            system.update_state(hour)

class TestSettingsManagement:
    """Tests for settings management."""
    
    def test_get_settings(self, system):
        """Test retrieving all settings."""
        settings = system.get_settings()
        assert "battery" in settings
        assert "consumption" in settings
        assert "home" in settings
        assert "price" in settings
        
    def test_update_settings(self, system):
        """Test updating settings."""
        # Get initial settings for baseline
        initial = system.get_settings()
        
        # Update only specific values
        new_settings = {
            "price": {
                "markupRate": 0.12
            }
        }
        
        system.update_settings(new_settings)
        current = system.get_settings()
        
        # Updated value should change
        assert current["price"]["markupRate"] == 0.12
        # Non-updated values should remain the same
        assert current["consumption"]["defaultHourly"] == initial["consumption"]["defaultHourly"]

class TestSystemBehavior:
    """Tests for system behavior with different price patterns."""
    
    def test_flat_price_behavior(self, system, flat_prices):
        """Test system behavior with flat prices."""
        schedule = system.prepare_schedule(flat_prices)
        schedule_data = schedule.get_schedule_data()
        # No trading should occur with flat prices
        assert schedule_data["summary"]["savings"] == 0
        
    def test_peak_price_behavior(self, system, peak_prices):
        """Test system behavior with peak prices."""
        schedule = system.prepare_schedule(peak_prices)
        schedule_data = schedule.get_schedule_data()
        # Peak prices should result in trading and savings
        assert schedule_data["summary"]["savings"] > 0

    def FIXME_test_consumption_impact(self, system, peak_prices):
        """Test impact of different consumption levels."""
        # Test with high consumption setting
        system.update_settings({
            "consumption": {"defaultHourly": 8.0}
        })
        schedule_high = system.prepare_schedule(peak_prices)
        savings_high = schedule_high.get_schedule_data()["summary"]["savings"]
        
        # Test with low consumption setting
        system.update_settings({
            "consumption": {"defaultHourly": 2.0}
        })
        schedule_low = system.prepare_schedule(peak_prices)
        savings_low = schedule_low.get_schedule_data()["summary"]["savings"]
        
        # Higher consumption should result in less savings potential
        assert savings_high < savings_low