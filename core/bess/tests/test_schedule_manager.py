"""Test suite for battery schedule management."""

from datetime import datetime
import pytest

from bess.bess import BatteryManager
from bess.growatt_schedule import GrowattScheduleManager
from bess.schedule import Schedule


class TestGrowattScheduleManager:
    """Test cases for GrowattScheduleManager."""

    @pytest.fixture
    def battery_manager(self):
        """Provide battery manager instance."""
        return BatteryManager()

    @pytest.fixture
    def schedule_manager(self):
        """Provide schedule manager instance."""
        return GrowattScheduleManager()

    def _create_price_dicts(self, prices):
        """Create price dictionaries with timestamps."""
        base_time = datetime.now().replace(hour=0, minute=0)
        return [
            {
                "timestamp": (base_time.replace(hour=i)).strftime("%Y-%m-%d %H:%M"),
                "price": p,
                "buy_price": p * 1.25,
                "sell_price": p * 0.8,
            }
            for i, p in enumerate(prices)
        ]

    def test_interval_conversion(
        self,
        battery_manager,
        schedule_manager,
        test_prices_2024_08_16,
        test_consumption_low,
        test_charging_power_rate,
    ):
        """Test generic to Growatt interval conversion."""
        # Set up and optimize
        prices = self._create_price_dicts(test_prices_2024_08_16)
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption_low,
            max_charging_power_rate=test_charging_power_rate,
        )
        schedule = battery_manager.optimize_schedule()

        # Get generic intervals
        generic_intervals = schedule.get_daily_intervals()
        assert len(generic_intervals) > 0

        # Each generic interval should have basic attributes
        for interval in generic_intervals:
            assert interval["start_time"] < interval["end_time"]
            assert interval["state"] in ["charging", "discharging", "standby"]
            assert isinstance(interval["action"], float)
            assert isinstance(interval["state_of_energy"], float)

        # Apply to Growatt manager
        schedule_manager.apply_schedule(schedule)

        # Test Growatt conversion
        growatt_settings = schedule_manager.get_daily_TOU_settings()
        assert len(growatt_settings) <= schedule_manager.max_intervals

        # Test conversion logic
        for generic in generic_intervals:
            # Find corresponding Growatt interval
            growatt = None
            for g in growatt_settings:
                if (
                    g["start_time"] == generic["start_time"]
                    and g["end_time"] == generic["end_time"]
                ):
                    growatt = g
                    break

            if not growatt:  # Skip if interval was combined
                continue

            # Verify conversion rules
            if generic["state"] == "charging":
                assert growatt["batt_mode"] == "battery-first"
                assert growatt["grid_charge"]
                assert growatt["discharge_rate"] == 0
            elif generic["state"] == "discharging":
                assert growatt["batt_mode"] == "load-first"
                assert not growatt["grid_charge"]
                assert growatt["discharge_rate"] == 100
            else:  # standby
                assert growatt["batt_mode"] == "battery-first"
                assert not growatt["grid_charge"]
                assert growatt["discharge_rate"] == 0

            # Verify time periods match when not combined
            assert growatt["start_time"] == generic["start_time"]
            assert growatt["end_time"] == generic["end_time"]
