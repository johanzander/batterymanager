"""Integration tests for battery management system."""

from datetime import datetime

import pytest

from bess.battery_manager import BatteryManager
from bess.growatt_schedule import GrowattScheduleManager


class MockHomeAssistantController:
    """Mock HA controller for testing."""

    def __init__(self):
        """Initialize with mock state."""
        self.settings = {
            "grid_charge": False,
            "discharge_rate": 0,
            "segments": {},
        }

    def grid_charge_enabled(self) -> bool:
        """Get grid charge state."""
        return self.settings["grid_charge"]

    def set_grid_charge(self, enable: bool) -> None:
        """Set grid charge state."""
        self.settings["grid_charge"] = enable

    def get_discharging_power_rate(self) -> int:
        """Get discharge power rate."""
        return self.settings["discharge_rate"]

    def set_discharging_power_rate(self, rate: int) -> None:
        """Set discharge power rate."""
        self.settings["discharge_rate"] = rate

    def set_inverter_time_segment(
        self,
        segment_id: int,
        batt_mode: str,
        start_time: str,
        end_time: str,
        enabled: bool,
    ) -> None:
        """Set TOU segment configuration."""
        self.settings["segments"][segment_id] = {
            "batt_mode": batt_mode,
            "start_time": start_time,
            "end_time": end_time,
            "enabled": enabled,
        }

    def disable_all_tou_settings(self) -> None:
        """Clear all TOU segments."""
        self.settings["segments"] = {}


class TestSystemIntegration:
    """Integration tests between system components."""

    @pytest.fixture
    def system(self):
        """Provide complete system setup."""
        controller = MockHomeAssistantController()
        schedule_manager = GrowattScheduleManager()
        battery_manager = BatteryManager()
        return controller, schedule_manager, battery_manager

    def test_schedule_application(
        self, system, test_prices_2024_08_16, test_consumption_low
    ):
        """Test complete schedule optimization and application."""
        controller, schedule_manager, battery_manager = system

        # Set up test data
        prices = [
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "price": p,
                "buyPrice": p * 1.25,
                "sellPrice": p * 0.8,
            }
            for p in test_prices_2024_08_16
        ]

        # Configure and optimize
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption_low,
            max_charging_power_rate=40,
        )

        # Generate schedule
        schedule = battery_manager.optimize_schedule()
        schedule_manager.apply_schedule(schedule)

        # Apply daily TOU settings
        controller.disable_all_tou_settings()
        daily_settings = schedule_manager.get_daily_TOU_settings()

        for segment in daily_settings:
            controller.set_inverter_time_segment(
                segment_id=segment["segment_id"],
                batt_mode=segment["batt_mode"],
                start_time=segment["start_time"],
                end_time=segment["end_time"],
                enabled=segment["enabled"],
            )

        # Verify segment application
        segments = controller.settings["segments"]
        assert len(segments) <= schedule_manager.max_intervals

        # Apply and verify hourly settings
        for hour in range(24):
            settings = schedule_manager.get_hourly_settings(hour)
            controller.set_grid_charge(settings["grid_charge"])
            controller.set_discharging_power_rate(settings["discharge_rate"])

            assert controller.grid_charge_enabled() == settings["grid_charge"]
            assert controller.get_discharging_power_rate() == settings["discharge_rate"]

    def test_schedule_updates(
        self, system, test_prices_2024_08_16, test_consumption_low
    ):
        """Test schedule updates over multiple periods."""
        controller, schedule_manager, battery_manager = system

        prices = [
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "price": p,
                "buyPrice": p * 1.25,
                "sellPrice": p * 0.8,
            }
            for p in test_prices_2024_08_16
        ]

        # Initial schedule
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption_low,
            max_charging_power_rate=40,
        )
        schedule = battery_manager.optimize_schedule()
        schedule_manager.apply_schedule(schedule)

        initial_intervals = schedule_manager.current_schedule.get_daily_intervals()

        # Update with new consumption
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption_low * 1.5,
            max_charging_power_rate=40,
        )
        new_schedule = battery_manager.optimize_schedule()
        schedule_manager.apply_schedule(new_schedule)

        updated_intervals = schedule_manager.current_schedule.get_daily_intervals()

        # Verify schedule adapted
        assert len(updated_intervals) > 0
        assert initial_intervals != updated_intervals

        # Verify settings still apply correctly
        daily_settings = schedule_manager.get_daily_TOU_settings()
        for segment in daily_settings:
            controller.set_inverter_time_segment(
                segment_id=segment["segment_id"],
                batt_mode=segment["batt_mode"],
                start_time=segment["start_time"],
                end_time=segment["end_time"],
                enabled=segment["enabled"],
            )

        settings = schedule_manager.get_hourly_settings(12)  # Test mid-day
        controller.set_grid_charge(settings["grid_charge"])
        controller.set_discharging_power_rate(settings["discharge_rate"])

        assert controller.grid_charge_enabled() == settings["grid_charge"]
        assert controller.get_discharging_power_rate() == settings["discharge_rate"]
