def optimize_battery_WORKING(
    prices,
    total_capacity=30,
    reserved_capacity=3,
    cycle_cost=0.5,
    hourly_consumption=3.5,
    max_charge_rate=6,
):
    """Battery optimization charging max during low prices, discharging up to consumption."""
    n_hours = len(prices)
    state_of_energy = [reserved_capacity] * (n_hours + 1)
    actions = [0] * n_hours

    # Sort hours by price for initial indices
    price_indices = [(price, hour) for hour, price in enumerate(prices)]
    sorted_indices = sorted(price_indices, key=lambda x: x[0])

    low_idx = 0
    high_idx = len(sorted_indices) - 1
    energy_to_discharge = 0  # Track total energy that needs to be discharged

    # Calculate minimum required profit threshold
    min_profit_threshold = 0.5

    # First pass: Identify and charge during lowest price hours
    while low_idx < high_idx:
        low_price, low_hour = sorted_indices[low_idx]
        high_price, high_hour = sorted_indices[high_idx]

        if high_hour <= low_hour:
            low_idx += 1
            continue

        profit = high_price - low_price - cycle_cost
        logger.debug(f"Profit: {profit}, High price: {high_price}, Low price: {low_price}")

        if profit < min_profit_threshold:
            low_idx += 1  # Change: Move to the next low price hour if profit is below threshold
            continue

        # Calculate max possible charge for this hour
        current_soe = state_of_energy[low_hour]
        space_available = total_capacity - current_soe
        charge_amount = min(max_charge_rate, space_available, total_capacity - reserved_capacity - energy_to_discharge)


        if charge_amount > 0:
            # Apply charge
            actions[low_hour] = charge_amount
            # Update SOE after charge
            for h in range(low_hour + 1, n_hours + 1):
                state_of_energy[h] = min(state_of_energy[h] + charge_amount, total_capacity)
            energy_to_discharge += charge_amount

        logger.debug(f"Charging at hour {low_hour}: charge_amount={charge_amount}, state_of_energy={state_of_energy[low_hour + 1]}")
        low_idx += 1

    # Second pass: Distribute discharge across highest price hours
    remaining_discharge = energy_to_discharge
    high_idx = len(sorted_indices) - 1

    while remaining_discharge > 0 and high_idx >= 0:
        high_price, high_hour = sorted_indices[high_idx]

        # Check if this hour has already been processed
        if actions[high_hour] != 0:
            high_idx -= 1
            continue

        # Find charging hours that came before this hour
        valid_charge_exists = False
        for h in range(high_hour):
            if actions[h] > 0:
                valid_charge_exists = True
                break

        if not valid_charge_exists:
            high_idx -= 1
            continue

        # Calculate discharge amount for this hour
        discharge_amount = min(
            hourly_consumption,  # Limited by consumption
            remaining_discharge  # Limited by energy available
        )

        if discharge_amount > 0:
            actions[high_hour] = -discharge_amount
            # Update SOE after discharge
            for h in range(high_hour + 1, n_hours + 1):
                state_of_energy[h] = max(state_of_energy[h] - discharge_amount, reserved_capacity)
            remaining_discharge -= discharge_amount

        logger.debug(f"Discharging at hour {high_hour}: discharge_amount={discharge_amount}, state_of_energy={state_of_energy[high_hour + 1]}, remaining_discharge={remaining_discharge}")
        if remaining_discharge > 0:
            high_idx -= 1

    # Calculate costs
    hourly_costs = []
    for hour in range(n_hours):
        current_price = prices[hour]
        action = actions[hour]

        # Base cost without battery
        base_cost = hourly_consumption * current_price

        # Calculate costs with battery
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
    base_cost = 0
    optimized_cost = 0
    for hour in hourly_costs:
        base_cost += hour["base_cost"]
        optimized_cost += hour["total_cost"]

    return {
        "state_of_energy": state_of_energy,
        "actions": actions,
        "base_cost": base_cost,
        "optimized_cost": optimized_cost,
        "cost_savings": base_cost - optimized_cost,
        "hourly_costs": hourly_costs,
    }




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

def find_profitable_trades_2(prices, cycle_cost=0.5, min_profit_threshold=0.2):
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

def optimize_battery_best_of_the_best(prices, total_capacity=30, reserved_capacity=3,
                    cycle_cost=0.5, hourly_consumption=5.2, max_charge_rate=6):
    """Battery optimization using max charge rate with split discharges."""
    n_hours = len(prices)
    state_of_energy = [reserved_capacity] * (n_hours + 1)
    actions = [0] * n_hours

    trades = find_profitable_trades_2(prices, cycle_cost)
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

        # Execute if we can discharge all energy
        if energy_to_discharge <= 0:
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
            logger.debug(f"Trade executed: Charge {charge_amount} at hour {primary_trade.charge_hour}")

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