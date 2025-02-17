"""Debug tests for battery schedule adaptation data flow."""

import pytest
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def test_consumption_prediction_flow(system_with_alternating_prices, ha_controller, consumption_manager):
    """Test how consumption predictions flow through the system."""
    
    # 1. Set initial predictions and verify
    initial_predictions = [4.5] * 24
    consumption_manager.set_predictions(initial_predictions)
    assert consumption_manager.get_predictions() == initial_predictions, "Initial predictions not set correctly"
    
    # 2. Run initial schedule and log values
    initial_schedule = system_with_alternating_prices.prepare_schedule()
    logger.info("Initial Schedule:")
    logger.info("State of Energy: %s", initial_schedule.state_of_energy)
    logger.info("Actions: %s", initial_schedule.actions)
    
    # 3. Update consumption and verify manager state
    new_consumption = 2.0
    ha_controller.settings["consumption"] = new_consumption
    
    # Update several hours and verify each update
    for hour in range(8):
        consumption_manager.update_consumption(hour, new_consumption)
        actual = consumption_manager.get_actual_consumption(hour)
        assert actual == new_consumption, f"Hour {hour} consumption not updated correctly"
    
    # 4. Get updated predictions and verify they changed
    updated_predictions = consumption_manager.get_predictions()
    logger.info("Updated predictions: %s", updated_predictions)
    assert any(p != 4.5 for p in updated_predictions), "Predictions should change after updates"
    
    # 5. Run system update and check new schedule
    system_with_alternating_prices.update_state(8)
    adapted_schedule = system_with_alternating_prices.prepare_schedule()
    
    logger.info("Adapted Schedule:")
    logger.info("State of Energy: %s", adapted_schedule.state_of_energy)
    logger.info("Actions: %s", adapted_schedule.actions)
    
    # Compare schedules
    initial_actions = initial_schedule.actions
    adapted_actions = adapted_schedule.actions
    
    for hour in range(24):
        if initial_actions[hour] != adapted_actions[hour]:
            logger.info(
                "Hour %d: Initial=%.2f, Adapted=%.2f", 
                hour, initial_actions[hour], adapted_actions[hour]
            )

def test_soc_adaptation_flow(system_with_alternating_prices, ha_controller):
    """Test how SOC changes affect the optimization."""
    
    # 1. Start with low SOC and optimize
    ha_controller.settings["battery_soc"] = 20
    initial_schedule = system_with_alternating_prices.prepare_schedule()
    
    logger.info("Initial Schedule (SOC=20):")
    logger.info("State of Energy: %s", initial_schedule.state_of_energy)
    logger.info("Actions: %s", initial_schedule.actions)
    
    # 2. Change to high SOC and check impact
    ha_controller.settings["battery_soc"] = 80
    system_with_alternating_prices.update_state(8)
    adapted_schedule = system_with_alternating_prices.prepare_schedule()
    
    logger.info("Adapted Schedule (SOC=80):")
    logger.info("State of Energy: %s", adapted_schedule.state_of_energy)
    logger.info("Actions: %s", adapted_schedule.actions)
    
    # Compare energy available for trading
    total_energy_before = sum(abs(a) for a in initial_schedule.actions)
    total_energy_after = sum(abs(a) for a in adapted_schedule.actions)
    
    logger.info("Total energy traded:")
    logger.info("Before (SOC=20): %.2f", total_energy_before)
    logger.info("After (SOC=80): %.2f", total_energy_after)
    
    assert total_energy_before != total_energy_after, (
        "Energy traded should change with SOC. "
        f"Before: {total_energy_before}, After: {total_energy_after}"
    )