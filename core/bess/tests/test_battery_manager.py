"""Test suite for battery management system."""

from datetime import datetime
import pytest
from bess.battery_manager import BatteryManager
from bess.schedule import Schedule

parametrize_consumption = pytest.mark.parametrize(
    "test_consumption",
    [
#        "test_consumption_low",
        "test_consumption_medium",
#        "test_consumption_high",
    ],
    indirect=True,
)

parametrize_prices = pytest.mark.parametrize(
    "test_prices",
    [
        "test_prices_flat",
        "test_prices_2024_08_16",
        "test_prices_2025_01_05",
        "test_prices_2025_01_12",
        "test_prices_2025_01_13",
        "test_prices_peak",
    ],
    indirect=True,
)

class TestBatteryManager:
    """Test cases for BatteryManager."""

    @pytest.fixture
    def battery_manager(self):
        """Provide battery manager instance."""
        return BatteryManager()

    def _create_price_dicts(self, prices):
        """Create price dictionaries with timestamps."""
        return [
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "price": p,
                "buyPrice": p * 1.25,
                "sellPrice": p * 0.8,
            }
            for p in prices
        ]

    @parametrize_consumption
    def test_optimization_flat_prices(
        self,
        battery_manager,
        test_prices_flat,
        test_consumption,
        test_charging_power_rate,
    ):
        """Test optimization with flat prices."""
        prices = self._create_price_dicts(test_prices_flat)
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption,
            max_charging_power_rate=test_charging_power_rate,
        )
        schedule = battery_manager.optimize_schedule()

        # Verify schedule properties
        assert isinstance(schedule, Schedule)
        assert len(schedule.actions) == 24
        assert sum(abs(a) for a in schedule.actions) == 0  # No actions with flat prices

        # Verify intervals
        intervals = schedule.get_daily_intervals()
        assert len(intervals) == 24
        assert intervals[0]["state"] == "standby"
        assert intervals[0]["action"] == 0.0

    @parametrize_consumption
    def test_optimization_2024_08_16(
        self,
        battery_manager,
        test_prices_2024_08_16,
        test_consumption,
        test_charging_power_rate,
    ):
        """Test optimization with prices for 2024-08-16."""
        prices = self._create_price_dicts(test_prices_2024_08_16)
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption,
            max_charging_power_rate=test_charging_power_rate,
        )
        schedule = battery_manager.optimize_schedule()

        # Verify basic structure
        assert isinstance(schedule, Schedule)
        assert len(schedule.actions) == 24
        assert len(schedule.state_of_energy) == 25  # Including initial level

        # Verify optimization results
        # Base case cost:                 127.95 SEK
        # Optimized cost:                  86.13 SEK
        # Total savings:                   41.81 SEK
        # Savings percentage:               32.7 %
        # Total energy charged:             30.0 kWh
        # Total energy discharged:          30.0 kWh
        assert abs(schedule.optimization_results["cost_savings"] - 41.81) < 1e-2

        # Verify intervals are properly formed
        intervals = schedule.get_daily_intervals()
        assert len(intervals) > 0
        for interval in intervals:
            assert interval["start_time"] < interval["end_time"]
            assert interval["state"] in ["charging", "discharging", "standby"]
            assert isinstance(interval["action"], float)
            assert isinstance(interval["state_of_energy"], float)

    @parametrize_consumption
    def test_optimization_2025_01_05(
        self,
        battery_manager,
        test_prices_2025_01_05,
        test_consumption,
        test_charging_power_rate,
    ):
        """Test optimization with prices for 2025-01-05."""
        prices = self._create_price_dicts(test_prices_2025_01_05)
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption,
            max_charging_power_rate=test_charging_power_rate,
        )
        schedule = battery_manager.optimize_schedule()

        # Verify schedule properties
        assert isinstance(schedule, Schedule)
        assert len(schedule.actions) == 24
        assert all(action == 0.0 for action in schedule.actions)
        assert schedule.optimization_results["cost_savings"] == 0

        # Verify battery constraints
        state_of_energy = schedule.state_of_energy
        assert all(3.0 <= level <= 30.0 for level in state_of_energy)
        assert all(
            abs(float(b2) - float(b1)) <= 6.0
            for b1, b2 in zip(state_of_energy, state_of_energy[1:])
        )

    @parametrize_consumption
    def test_optimization_2025_01_13(
        self,
        battery_manager,
        test_prices_2025_01_13,
        test_consumption,
        test_charging_power_rate,
    ):
        """Test optimization with prices for 2025-01-13."""
        prices = self._create_price_dicts(test_prices_2025_01_13)
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption,
            max_charging_power_rate=test_charging_power_rate,
        )
        schedule = battery_manager.optimize_schedule()
        
        assert schedule.optimization_results["cost_savings"] >= 0


    @parametrize_consumption
    def test_optimization_2025_01_12(
        self,
        battery_manager,
        test_prices_2025_01_12,
        test_consumption,
        test_charging_power_rate,
    ):
        """Test optimization with prices for 2025-01-13."""
        prices = self._create_price_dicts(test_prices_2025_01_12)
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption,
            max_charging_power_rate=test_charging_power_rate,
        )
        schedule = battery_manager.optimize_schedule()
        # Base case cost:                 104.80 SEK
        # Optimized cost:                  84.96 SEK
        # Total savings:                   19.84 SEK
        # Savings percentage:               18.9 %
        # Total energy charged:             27.0 kWh
        # Total energy discharged:          27.0 kWh
        assert abs(schedule.optimization_results["cost_savings"] - 19.84) < 1e-2


    @parametrize_consumption
    def test_optimization_peak_prices(
        self,
        battery_manager,
        test_prices_peak,
        test_consumption,
        test_charging_power_rate,
    ):
        """Test optimization with peak price pattern."""
        prices = self._create_price_dicts(test_prices_peak)
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption,
            max_charging_power_rate=test_charging_power_rate,
        )
        schedule = battery_manager.optimize_schedule()

        # Verify basic structure
        assert isinstance(schedule, Schedule)
        assert len(schedule.actions) == 24

        # Should see significant charging and discharging
        assert any(a > 0 for a in schedule.actions)  # Some charging
        assert any(a < 0 for a in schedule.actions)  # Some discharging

        # Verify intervals show activity
        intervals = schedule.get_daily_intervals()
        states = [interval["state"] for interval in intervals]
        assert "charging" in states
        assert "discharging" in states
        
    @parametrize_prices
    @parametrize_consumption
    def test_savings(
        self,
        battery_manager,
        test_prices,
        test_consumption,
        test_charging_power_rate,
    ):
        """Test that ensures every saving is positive for each price pattern."""
        prices = self._create_price_dicts(test_prices)
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=test_consumption,
            max_charging_power_rate=test_charging_power_rate,
        )
        schedule = battery_manager.optimize_schedule()

        # Verify optimization results
        assert schedule.optimization_results["cost_savings"] >= 0