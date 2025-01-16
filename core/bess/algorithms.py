"""Battery optimization algorithm for maximizing profit from electricity price variations.

The algorithm finds and executes profitable charge/discharge cycles by identifying optimal 
trading opportunities based on hourly electricity prices. It respects battery constraints 
and household consumption limits while maximizing potential savings.

Algorithm Overview:
1. Trade Discovery:
   - For each hour pair (charge_hour, discharge_hour), calculate potential profit
   - Profit = discharge_price - charge_price - cycle_cost
   - Keep trades above minimum (configurable) profit threshold
   - Sort trades by profit per kWh (most profitable first)

2. Trade Execution (iterating through profitable trades):
   a) Charge Planning:
      - Calculate maximum possible charge at charge_hour
      - Limited by max_charge_rate (e.g., 6 kWh) and remaining battery capacity
   
   b) Discharge Planning:
      - First try primary discharge at most profitable hour
      - Limited by hourly_consumption (e.g., 3.5 kWh)
      - If energy remains, look for secondary discharge opportunities in other profitable hours
      - Trade is only executed if we can find discharge opportunities for at least 80% of 
        the charged amount (e.g., for a 6 kWh charge, must find at least 4.8 kWh of discharge)
   
   c) Trade Execution:
      - If discharge plan meets the 80% threshold, apply both charge and discharges
      - Update battery state (state_of_energy) and available discharge capacities
      - Continue until battery capacity is full or no profitable trades remain

Key Features:
- Takes advantage of price variations within the same day
- Handles partial discharges when profitable (above 80% threshold)
- Prioritizes most profitable trades first
- Considers battery cycle costs

Limitations:
- Does not support potential export to grid profits

System Parameters (configurable):
- Battery Capacity:
    * total_capacity: Maximum battery level (default: 30 kWh)
    * reserved_capacity: Minimum battery level (default: 3 kWh)
- Power Limits:
    * max_charge_rate: Maximum charging power (default: 6 kWh per hour)
    * hourly_consumption: Maximum discharge rate, based on home usage (default: 5.2 kWh per hour)
- Cost Parameters:
    * cycle_cost: Battery wear cost per kWh charged (default: 0.5 SEK)
    * min_profit_threshold: Minimum profit required for trade consideration (default: 0.2 SEK/kWh)

Constraints:
- Chronological order: Can only discharge after charging
- Discharge threshold: Must find profitable discharge plan for at least 80% of charged energy
- State management: Battery level must always stay between reserved_capacity and total_capacity
- Profitable trades: Each executed trade must have positive profit after cycle costs
- Consumption limit: Cannot discharge more than hourly_consumption in any hour


Usage:
The optimize_battery function takes hourly prices and system parameters, returning a schedule
of charge/discharge actions and their expected cost impact. The schedule ensures all battery
and consumption constraints are met while maximizing potential savings.
"""

import logging

logger = logging.getLogger(__name__)


class Trade:
    """Represents a potential charge/discharge trade."""
    def __init__(self, charge_hour, discharge_hour, charge_price, discharge_price, cycle_cost):
        self.charge_hour = charge_hour
        self.discharge_hour = discharge_hour
        self.charge_price = charge_price
        self.discharge_price = discharge_price
        self.cycle_cost = cycle_cost
        self.profit_per_kwh = discharge_price - charge_price - cycle_cost

    def __repr__(self):
        return (f"Trade(c_hour={self.charge_hour}, d_hour={self.discharge_hour}, "
                f"profit={self.profit_per_kwh:.3f})")

def find_profitable_trades(prices, cycle_cost=0.5, min_profit_threshold=0.2):
    """Find all profitable trades keeping chronological order."""
    n_hours = len(prices)
    profitable_trades = []

    for charge_hour in range(n_hours):
        charge_price = prices[charge_hour]
        for discharge_hour in range(charge_hour + 1, n_hours):
            discharge_price = prices[discharge_hour]
            trade = Trade(charge_hour, discharge_hour, charge_price,
                         discharge_price, cycle_cost)
            if trade.profit_per_kwh >= min_profit_threshold:
                profitable_trades.append(trade)

    # Sort trades by profit per kWh
    profitable_trades.sort(key=lambda x: x.profit_per_kwh, reverse=True)
    return profitable_trades

def optimize_battery(prices, total_capacity=30, reserved_capacity=3,
                    cycle_cost=0.5, hourly_consumption=5.2, max_charge_rate=6):
    """Battery optimization using max charge rate with split discharges."""
    n_hours = len(prices)
    state_of_energy = [reserved_capacity] * (n_hours + 1)
    actions = [0] * n_hours

    trades = find_profitable_trades(prices, cycle_cost)
    logger.debug("Found profitable trades:")
    for trade in trades:
        logger.debug(f"  {trade}")

    discharge_capacities = {h: hourly_consumption for h in range(n_hours)}
    energy_for_discharge = total_capacity - reserved_capacity

    for primary_trade in trades:
        if energy_for_discharge <= 0:
            break

        if actions[primary_trade.charge_hour] != 0:
            continue

        # Calculate charge amount
        current_soe = state_of_energy[primary_trade.charge_hour]
        charge_amount = min(max_charge_rate, total_capacity - current_soe)

        if charge_amount <= 0:
            continue

        # Find discharge plan
        energy_to_discharge = charge_amount
        discharge_plan = []

        # KEY CHANGE: More flexible primary discharge
        remaining_capacity = discharge_capacities[primary_trade.discharge_hour]
        if remaining_capacity > 0:
            primary_discharge = min(remaining_capacity, energy_to_discharge)
            discharge_plan.append((primary_trade.discharge_hour, primary_discharge))
            energy_to_discharge -= primary_discharge
            logger.debug(f"Primary discharge planned: {primary_discharge} at hour {primary_trade.discharge_hour}")

        # Look for secondary discharge opportunities if needed
        if energy_to_discharge > 0:
            for secondary_trade in trades:
                if energy_to_discharge <= 0:
                    break
                if (secondary_trade.discharge_hour != primary_trade.discharge_hour and
                    secondary_trade.charge_hour == primary_trade.charge_hour and
                    discharge_capacities[secondary_trade.discharge_hour] > 0 and
                    secondary_trade.profit_per_kwh > 0):
                    secondary_discharge = min(
                        discharge_capacities[secondary_trade.discharge_hour],
                        energy_to_discharge
                    )
                    if secondary_discharge > 0:
                        discharge_plan.append((secondary_trade.discharge_hour, secondary_discharge))
                        energy_to_discharge -= secondary_discharge
                        logger.debug(f"Secondary discharge planned: {secondary_discharge} at hour {secondary_trade.discharge_hour}")

        # KEY CHANGE: Execute if we found a place for majority of charge
        total_discharge = sum(amount for _, amount in discharge_plan)
        if len(discharge_plan) > 0 and total_discharge >= charge_amount * 0.8:  # At least 80% can be discharged
            # Apply charge
            actions[primary_trade.charge_hour] = charge_amount
            for h in range(primary_trade.charge_hour + 1, n_hours + 1):
                state_of_energy[h] = min(state_of_energy[h] + charge_amount, total_capacity)

            # Apply discharges
            for discharge_hour, discharge_amount in discharge_plan:
                actions[discharge_hour] = (actions[discharge_hour] or 0) - discharge_amount
                discharge_capacities[discharge_hour] -= discharge_amount
                for h in range(discharge_hour + 1, n_hours + 1):
                    state_of_energy[h] = max(state_of_energy[h] - discharge_amount, reserved_capacity)

            energy_for_discharge -= charge_amount
            logger.debug(
                f"Trade executed: Charge {charge_amount:.1f} at hour "
                f"{primary_trade.charge_hour} ({primary_trade.charge_price:.3f}), "
                f"Discharges: {discharge_plan}"
            )

    # Calculate costs
    hourly_costs = []
    for hour in range(n_hours):
        current_price = prices[hour]
        action = actions[hour]
        base_cost = hourly_consumption * current_price

        if action >= 0:  # Charging or standby
            grid_cost = (hourly_consumption + action) * current_price
            battery_cost = action * cycle_cost
        else:  # Discharging
            grid_cost = max(0, hourly_consumption + action) * current_price
            battery_cost = 0

        total_cost = grid_cost + battery_cost
        hour_savings = base_cost - total_cost

        hourly_costs.append({
            "base_cost": base_cost,
            "grid_cost": grid_cost,
            "battery_cost": battery_cost,
            "total_cost": total_cost,
            "savings": hour_savings,
        })

    # Calculate total costs
    base_cost = sum(hour["base_cost"] for hour in hourly_costs)
    optimized_cost = sum(hour["total_cost"] for hour in hourly_costs)

    return {
        "state_of_energy": state_of_energy,
        "actions": actions,
        "base_cost": base_cost,
        "optimized_cost": optimized_cost,
        "cost_savings": base_cost - optimized_cost,
        "hourly_costs": hourly_costs,
    }