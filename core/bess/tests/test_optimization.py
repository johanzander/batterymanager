# tests/test_optimization.py

"""Tests for optimization logic."""

import pytest
from bess.algorithms import optimize_battery

class TestOptimizationBasics:
    """Basic optimization functionality tests."""
    
    def test_flat_prices(self, system, flat_prices):
        """Test optimization with flat prices - should not trade."""
        system.price_settings.use_actual_price = False
        schedule = system.prepare_schedule(flat_prices)
        
        schedule_data = schedule.get_schedule_data()
        assert schedule is not None
        assert all(a == 0 for a in schedule.actions), "Expected no trades with flat prices"
        assert schedule_data["summary"]["savings"] == 0
        
    @pytest.mark.parametrize("consumption_level", [3.5, 5.2, 8.0])
    def test_consumption_levels(self, system, peak_prices, consumption_level):
        """Test optimization with different consumption levels."""
        system.price_settings.use_actual_price = False
        system.consumption_settings.default_hourly = consumption_level
        schedule = system.prepare_schedule(peak_prices)
        
        schedule_data = schedule.get_schedule_data()
        assert schedule is not None
        if consumption_level <= 5.2:  # We know these levels should give savings
            assert schedule_data["summary"]["savings"] > 0

class TestHistoricalPatterns:
    """Tests with known historical price patterns."""
        
    def test_pattern_2024_08_16(self, system, test_prices_2024_08_16):
        """Test pattern with high price spread."""
        # Base case cost:                 127.95 SEK
        # Optimized cost:                  83.13 SEK
        # Total savings:                   44.81 SEK
        # Savings percentage:               35.0 %
        # Total energy charged:             30.0 kWh
        # Total energy discharged:          30.0 kWh        

        system.price_settings.use_actual_price = False
        system._consumption_manager.set_predictions([5.2] * 24)        
        system._controller.settings["battery_soc"] = 10  # Start at min SOC
        
        # Run optimization
        schedule = system.prepare_schedule(test_prices_2024_08_16)
        schedule_data = schedule.get_schedule_data()
        
        # Check total energy traded
        total_charge = sum(a for a in schedule.actions if a > 0)
        total_discharge = -sum(a for a in schedule.actions if a < 0)
        
        print(f"\nExpected values:")
        print(f"Savings: 44.81 SEK")
        print(f"Total charged: 30.0 kWh")
        print(f"Total discharged: 30.0 kWh")
        print(f"\nActual values:")
        print(f"Savings: {schedule_data['summary']['savings']:.2f} SEK")
        print(f"Total charged: {total_charge:.1f} kWh")
        print(f"Total discharged: {total_discharge:.1f} kWh")
        
        # Verify exact match with expected values
        assert abs(schedule_data["summary"]["savings"] - 44.81) < 1e-2
        assert abs(total_charge - 30.0) < 1e-1
        assert abs(total_discharge - 30.0) < 1e-1
        
    def test_pattern_2025_01_05(self, system, test_prices_2025_01_05):
        """Test pattern with insufficient price spread."""
        system.price_settings.use_actual_price = False
        system._consumption_manager.set_predictions([5.2] * 24)
        schedule = system.prepare_schedule(test_prices_2025_01_05)        
        schedule_data = schedule.get_schedule_data()

        assert schedule_data["summary"]["savings"] == 0
        assert all(action == 0.0 for action in schedule.actions), "Expected no trades"
        
    def test_pattern_2025_01_12(self, system, test_prices_2025_01_12):
        """Test pattern with evening peak."""
        # Base case cost:                 104.80 SEK
        # Optimized cost:                  82.26 SEK
        # Total savings:                   22.54 SEK
        # Savings percentage:               21.5 %
        # Total energy charged:             27.0 kWh
        # Total energy discharged:          27.0 kWh
        system.price_settings.use_actual_price = False
        system._consumption_manager.set_predictions([5.2] * 24)        
        system._controller.settings["battery_soc"] = 10  # Start at min SOC

        schedule = system.prepare_schedule(test_prices_2025_01_12)        
        schedule_data = schedule.get_schedule_data()
        
        assert abs(schedule_data["summary"]["savings"] - 22.54) < 1e-2
        
        charges = sum(a for a in schedule.actions if a > 0)
        discharges = -sum(a for a in schedule.actions if a < 0)
        
        assert abs(charges - 27.0) < 1e-1
        assert abs(discharges - 27.0) < 1e-1
        
    def test_pattern_2025_01_13(self, system, test_prices_2025_01_13):
        """Test pattern with very low price period."""
        # Base case cost:                  51.68 SEK
        # Optimized cost:                  50.48 SEK
        # Total savings:                    1.20 SEK
        # Savings percentage:                2.3 %
        # Total energy charged:              6.0 kWh
        # Total energy discharged:           5.2 kWh
        system.price_settings.use_actual_price = False
        system._consumption_manager.set_predictions([5.2] * 24)
        system._controller.settings["battery_soc"] = 10  # Start at min SOC

        schedule = system.prepare_schedule(test_prices_2025_01_13)                
        schedule_data = schedule.get_schedule_data()
        
        assert abs(schedule_data["summary"]["savings"] - 1.20) < 1e-2
        

class TestConstraints:
    """Tests for optimization constraints."""
    
    def test_battery_capacity(self, system, peak_prices):
        """Test battery capacity constraints."""
        system.price_settings.use_actual_price = False
        schedule = system.prepare_schedule(peak_prices)
        
        # Check battery levels stay within limits
        min_level = system.battery_settings.total_capacity * (system.battery_settings.min_soc / 100)
        for soe in schedule.state_of_energy:
            assert min_level <= soe <= system.battery_settings.total_capacity, \
                f"Battery level {soe} outside limits [{min_level}, {system.battery_settings.total_capacity}]"
            
    def test_charge_rate(self, system, peak_prices):
        """Test charging rate constraints."""
        system.price_settings.use_actual_price = False
        schedule = system.prepare_schedule(peak_prices)
        
        # Check charging rates
        max_rate = system.battery_settings.max_charge_power_kw * (system.battery_settings.charging_power_rate / 100)
        for action in schedule.actions:
            assert abs(action) <= max_rate + 1e-6, \
                f"Action {action} exceeds max rate {max_rate}"
            
    def test_consumption_limits(self, system, peak_prices):
        """Test consumption limit constraints."""
        consumption_level = 4.0
        system.price_settings.use_actual_price = False
        system._consumption_manager.set_predictions([consumption_level] * 24)
        schedule = system.prepare_schedule(peak_prices)
        
        # Check discharge doesn't exceed consumption
        for hour, action in enumerate(schedule.actions):
            if action < 0:  # Discharging
                assert abs(action) <= consumption_level + 1e-6, \
                    f"Discharge {abs(action)} exceeds consumption limit {consumption_level} at hour {hour}"

class TestProfitability:
    """Tests for profit calculations."""
    
    def test_min_profit_threshold(self, system, peak_prices):
        """Test minimum profit threshold."""
        system.price_settings.use_actual_price = False
        schedule = system.prepare_schedule(peak_prices)
        
        # Extract prices we used for optimization
        prices = [
            entry["price"] if not system.price_settings.use_actual_price else entry["buyPrice"]
            for entry in peak_prices
        ]
        
        remaining_discharge = {}  # Track discharge volumes by hour
        cycle_cost = (
            system.battery_settings.charge_cycle_cost / system.price_settings.vat_multiplier 
            if not system.price_settings.use_actual_price
            else system.battery_settings.charge_cycle_cost
        )
        
        # First collect all discharges
        for hour, action in enumerate(schedule.actions):
            if action < 0:  # Discharging
                remaining_discharge[hour] = abs(action)
                
        # Then verify each charge's profitability
        for charge_hour, action in enumerate(schedule.actions):
            if action > 0:  # Charging
                charge_cost = prices[charge_hour] * action
                cycle_cost_total = cycle_cost * action
                total_profit = 0
                volume_accounted = 0
                
                # Find discharges for this charge
                for discharge_hour, volume in remaining_discharge.items():
                    if discharge_hour > charge_hour:  # Only look at future discharges
                        discharge_price = prices[discharge_hour]
                        usable_volume = min(action - volume_accounted, volume)
                        if usable_volume > 0:
                            profit = (discharge_price - prices[charge_hour]) * usable_volume
                            total_profit += profit
                            volume_accounted += usable_volume
                            remaining_discharge[discharge_hour] -= usable_volume
                
                # Verify total profit meets threshold
                if volume_accounted > 0:  # If we found matching discharges
                    profit_per_kwh = (total_profit - cycle_cost_total) / action
                    assert profit_per_kwh >= 0.2, \
                        f"Trade starting at hour {charge_hour} has profit {profit_per_kwh:.3f} below threshold"
                        
class TestStateOfCharge:
    """Tests for State of Charge (SOC) optimization behavior."""
    
    def test_initial_soc_behavior(self):
        """Test that initial SOC directly affects state_of_energy."""
        # Setup test parameters
        prices = [1.0] * 24  # Flat prices
        hourly_consumption = [4.5] * 24
        total_capacity = 30.0
        min_soc = 10
        reserved_capacity = total_capacity * (min_soc / 100)
        
        # Test different initial SOC values
        test_socs = [20, 50, 80]
        for initial_soc in test_socs:
            expected_energy = total_capacity * (initial_soc / 100)
            result = optimize_battery(
                prices=prices,
                total_capacity=total_capacity,
                reserved_capacity=reserved_capacity,
                cycle_cost=0.5,
                hourly_consumption=hourly_consumption,
                max_charge_power=6.0,
                min_profit_threshold=0.2,
                initial_soc=initial_soc
            )
            assert abs(result["state_of_energy"][0] - expected_energy) < 1e-6, (
                f"Initial state of energy {result['state_of_energy'][0]} does not match "
                f"expected {expected_energy} for {initial_soc}% SOC"
            )

    def test_soc_limits_trading(self):
        """Test that SOC properly limits trading opportunities."""
        prices = [0.1] * 12 + [3.0] * 12  # Low then high prices
        hourly_consumption = [4.5] * 24
        total_capacity = 30.0
        min_soc = 10
        reserved_capacity = total_capacity * (min_soc / 100)
        
        # Test with low initial SOC
        low_soc_result = optimize_battery(
            prices=prices,
            total_capacity=total_capacity,
            reserved_capacity=reserved_capacity,
            cycle_cost=0.5,
            hourly_consumption=hourly_consumption,
            max_charge_power=6.0,
            min_profit_threshold=0.2,
            initial_soc=20  # Start at 20% SOC
        )
        
        # Test with high initial SOC
        high_soc_result = optimize_battery(
            prices=prices,
            total_capacity=total_capacity,
            reserved_capacity=reserved_capacity,
            cycle_cost=0.5,
            hourly_consumption=hourly_consumption,
            max_charge_power=6.0,
            min_profit_threshold=0.2,
            initial_soc=80  # Start at 80% SOC
        )