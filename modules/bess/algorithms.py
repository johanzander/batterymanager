"""Battery optimization algorithm(s) for battery energy storage systems."""


def calculate_optimization_costs(
    prices: list[float],
    actions: list[float],
    state_of_energy: list[float],
    hourly_consumption: float,
    battery_cycle_cost: float,
) -> dict:
    """Calculate costs and savings for battery optimization strategies.

    Args:
        prices: List of hourly electricity prices
        actions: List of battery actions (positive for charging, negative for discharging)
        state_of_energy: List of battery state of energy levels after each action
        hourly_consumption: Base consumption per hour in kWh
        battery_cycle_cost: Cost per kWh for battery cycling

    Returns:
        Dictionary containing hourly costs and totals:
        {
            'hourly_costs': List of dictionaries with hourly cost breakdown
            'base_cost': Total cost without optimization
            'optimized_cost': Total cost with optimization
            'cost_savings': Total savings from optimization
        }

    """
    hourly_costs = []

    for hour, (price, action, soe) in enumerate(
        zip(prices, actions, state_of_energy, strict=False)
    ):
        # Calculate base case cost (without battery)
        base_cost = hourly_consumption * price

        # Calculate optimized costs based on battery action
        if action >= 0:  # Charging or standby
            # Grid cost includes both consumption and battery charging
            grid_cost = (hourly_consumption + action) * price
            # Battery cycling cost only applies to charged amount
            battery_cost = action * battery_cycle_cost
        else:  # Discharging
            # Grid cost is reduced by battery discharge
            grid_cost = (hourly_consumption + action) * price  # action is negative
            battery_cost = 0  # No battery cost for discharging

        # Calculate total cost and savings for this hour
        total_hour_cost = grid_cost + battery_cost
        hour_savings = base_cost - total_hour_cost

        hourly_costs.append(
            {
                "hour": hour,
                "price": price,
                "action": action,
                "soe": soe,
                "base_cost": base_cost,
                "grid_cost": grid_cost,
                "battery_cost": battery_cost,
                "total_cost": total_hour_cost,
                "savings": hour_savings,
            }
        )

    # Calculate totals - not using sum() as it may not be available
    base_cost = 0
    optimized_cost = 0
    for hour in hourly_costs:
        base_cost += hour["base_cost"]
        optimized_cost += hour["total_cost"]
    cost_savings = base_cost - optimized_cost

    return {
        "hourly_costs": hourly_costs,
        "base_cost": base_cost,
        "optimized_cost": optimized_cost,
        "cost_savings": cost_savings,
    }


def optimize_battery_dynamic_2(
    prices: list[float],
    total_capacity: float = 30,
    reserved_capacity: float = 3,
    cycle_cost: float = 0.5,
    hourly_consumption: float = 3.5,
    max_charge_rate: float = 6,
    use_dynamic_discharge: bool = False,  # New parameter to control the feature
    dynamic_discharge_threshold: float = 0.75,  # Configurable threshold multiplier
    dynamic_discharge_level: float = 10.0,  # Configurable level above reserve
) -> dict:
    """Dynamic optimization using price differentials.

    Args:
        prices: List of hourly electricity prices
        total_capacity: Total battery capacity in kWh
        reserved_capacity: Minimum battery level to maintain in kWh
        cycle_cost: Cost per kWh for battery cycling
        hourly_consumption: Base consumption per hour in kWh
        max_charge_rate: Maximum charge/discharge rate in kWh
        use_dynamic_discharge: Whether to use dynamic discharge thresholds
        dynamic_discharge_threshold: Multiplier for cycle cost when battery is full (0.0-1.0)
        dynamic_discharge_level: kWh above reserve capacity to trigger dynamic threshold

    """
    n_hours = len(prices)
    state_of_energy = [reserved_capacity] * (n_hours + 1)
    actions = [0] * n_hours

    def find_best_discharge_opportunity(
        current_hour: int,
        current_price: float,
        min_price_threshold: float,
        remaining_hours: int,
        hourly_consumption: float,
    ) -> tuple[int | None, float]:
        """Find best future discharge opportunity based on price differential and consumption."""
        best_diff = cycle_cost
        best_hour = None

        # Calculate maximum discharge potential based on remaining consumption
        max_discharge_potential = remaining_hours * hourly_consumption

        # Only consider charging if price is good and we can use the energy
        if current_price > min_price_threshold or max_discharge_potential < 0.1:
            return None, 0

        for future_hour in range(current_hour + 1, n_hours):
            price_diff = prices[future_hour] - current_price
            if price_diff > best_diff:
                best_diff = price_diff
                best_hour = future_hour

        return best_hour, best_diff

    # Calculate price statistics for adaptive thresholds
    avg_price = sum(prices) / len(prices)
    price_range = max(prices) - min(prices)
    min_price_threshold = avg_price - (
        price_range * 0.25
    )  # Only charge in bottom 25% of price range

    # Main optimization loop
    for hour in range(n_hours):
        current_price = prices[hour]
        current_level = state_of_energy[hour]

        # Look for charging opportunity
        best_discharge_hour, price_diff = find_best_discharge_opportunity(
            hour,
            current_price,
            min_price_threshold,
            n_hours - hour,  # remaining hours
            hourly_consumption,
        )

        if best_discharge_hour is not None:
            # Charging is profitable
            space_available = total_capacity - current_level
            if space_available > 0:
                charge_amount = min(max_charge_rate, space_available)
                actions[hour] = charge_amount
                state_of_energy[hour + 1] = current_level + charge_amount

        # Check for discharge
        elif current_level > reserved_capacity:
            # Look backward for charged energy cost
            charged_price = min(prices[:hour]) if hour > 0 else current_price
            price_difference = current_price - charged_price

            # Calculate discharge threshold based on configuration
            if use_dynamic_discharge and current_level > (
                reserved_capacity + dynamic_discharge_level
            ):
                discharge_threshold = cycle_cost * dynamic_discharge_threshold
            else:
                discharge_threshold = cycle_cost

            if price_difference > discharge_threshold:
                discharge_amount = min(
                    max_charge_rate,
                    current_level - reserved_capacity,
                    hourly_consumption,
                )
                actions[hour] = -discharge_amount
                state_of_energy[hour + 1] = current_level - discharge_amount

        # Update battery level if no action
        if actions[hour] == 0:
            state_of_energy[hour + 1] = current_level

    # Calculate costs using standardized function
    result = calculate_optimization_costs(
        prices=prices,
        actions=actions,
        state_of_energy=state_of_energy[:-1],  # Exclude last level as it's for next day
        hourly_consumption=hourly_consumption,
        battery_cycle_cost=cycle_cost,
    )

    return {
        "state_of_energy": state_of_energy,
        "actions": actions,
        "base_cost": result["base_cost"],
        "optimized_cost": result["optimized_cost"],
        "cost_savings": result["cost_savings"],
        "hourly_costs": result["hourly_costs"],
    }


def optimize_battery_dynamic_NEW(
    prices: list[float],
    total_capacity: float = 30,
    reserved_capacity: float = 3,
    cycle_cost: float = 0.5,
    hourly_consumption: float = 3.5,
    max_charge_rate: float = 6,
) -> dict:
    n_hours = len(prices)
    state_of_energy = [reserved_capacity] * (n_hours + 1)
    actions = [0] * n_hours

    def calculate_discharge_revenue(hour: int, amount: float) -> float:
        if hour >= n_hours - 1:
            return 0
        remaining_hours = n_hours - hour - 1
        max_discharge = min(amount, remaining_hours * hourly_consumption)
        if max_discharge <= 0:
            return 0
        max_future_price = max(float(p) for p in prices[hour + 1 :])
        return max_future_price * max_discharge

    for hour in range(n_hours):
        current_price = float(prices[hour])
        current_level = float(state_of_energy[hour])

        # Consider charging if space available
        space_available = total_capacity - current_level
        if space_available > 0:
            charge_amount = min(float(max_charge_rate), float(space_available))
            cost_to_charge = (current_price + cycle_cost) * charge_amount
            revenue = calculate_discharge_revenue(hour, charge_amount)

            if revenue > cost_to_charge:
                actions[hour] = charge_amount
                state_of_energy[hour + 1] = current_level + charge_amount
                continue

        # Consider discharging if above reserve
        if current_level > reserved_capacity:
            discharge_amount = min(
                float(hourly_consumption), float(current_level - reserved_capacity)
            )
            if discharge_amount > 0:
                actions[hour] = -discharge_amount
                state_of_energy[hour + 1] = current_level - discharge_amount
                continue

        state_of_energy[hour + 1] = current_level

    result = calculate_optimization_costs(
        prices=prices,
        actions=actions,
        state_of_energy=state_of_energy[:-1],
        hourly_consumption=hourly_consumption,
        battery_cycle_cost=cycle_cost,
    )

    return {
        "state_of_energy": state_of_energy,
        "actions": actions,
        "base_cost": result["base_cost"],
        "optimized_cost": result["optimized_cost"],
        "cost_savings": result["cost_savings"],
        "hourly_costs": result["hourly_costs"],
    }


def optimize_battery_dynamic(
    prices,
    total_capacity=30,
    reserved_capacity=3,
    cycle_cost=0.5,
    hourly_consumption=3.5,
    max_charge_rate=6,
):
    """Battery optimization.

    Uses only price differentials, no fixed thresholds.
    Includes detailed cost tracking for all components.

    """
    n_hours = len(prices)
    state_of_energy = [reserved_capacity] * (n_hours + 1)
    actions = [0] * n_hours
    hourly_costs = []

    def find_best_discharge_opportunity(current_hour, current_price):
        """Find best future discharge opportunity based on price differential."""
        best_diff = cycle_cost
        best_hour = None

        for future_hour in range(current_hour + 1, n_hours):
            price_diff = prices[future_hour] - current_price
            if price_diff > best_diff:
                best_diff = price_diff
                best_hour = future_hour

        return best_hour, best_diff

    # Main optimization loop
    for hour in range(n_hours):
        current_price = prices[hour]
        current_level = state_of_energy[hour]

        # Look for charging opportunity
        best_discharge_hour, price_diff = find_best_discharge_opportunity(
            hour, current_price
        )

        if best_discharge_hour is not None:
            # Charging is profitable
            space_available = total_capacity - current_level
            if space_available > 0:
                charge_amount = min(max_charge_rate, space_available)
                actions[hour] = charge_amount
                state_of_energy[hour + 1] = current_level + charge_amount

        # Check for discharge
        elif current_level > reserved_capacity:
            # Look backward for charged energy cost
            charged_price = min(prices[:hour]) if hour > 0 else current_price

            if current_price - charged_price > cycle_cost:
                discharge_amount = min(
                    hourly_consumption, current_level - reserved_capacity
                )
                actions[hour] = -discharge_amount
                state_of_energy[hour + 1] = current_level - discharge_amount

        # Update battery level if no action
        if actions[hour] == 0:
            state_of_energy[hour + 1] = current_level

        # Calculate hourly costs
        base_hour_cost = hourly_consumption * current_price
        grid_amount = hourly_consumption + max(0, actions[hour])
        if actions[hour] < 0:
            grid_amount = 0  # Using battery instead of grid
        grid_cost = grid_amount * current_price
        battery_cost = max(0, actions[hour]) * cycle_cost
        total_hour_cost = grid_cost + battery_cost
        hour_savings = base_hour_cost - total_hour_cost

        hourly_costs.append(
            {
                "base_cost": base_hour_cost,
                "grid_cost": grid_cost,
                "battery_cost": battery_cost,
                "total_cost": total_hour_cost,
                "savings": hour_savings,
            }
        )

    # Calculate total costs:
    # TODO sum not available when running from pyscript
    #    base_cost = sum(price * hourly_consumption for price in prices)
    #    optimized_cost = sum(hour['total_cost'] for hour in hourly_costs)
    base_cost = 0
    optimized_cost = 0
    for price in prices:
        base_cost += price * hourly_consumption
    for hour in hourly_costs:
        optimized_cost += hour["total_cost"]

    return {
        "state_of_energy": state_of_energy,
        "actions": actions,
        "base_cost": base_cost,
        "optimized_cost": optimized_cost,
        "cost_savings": base_cost - optimized_cost,
        "hourly_costs": hourly_costs,
    }


def optimize_battery(
    prices,
    total_capacity,
    reserved_capacity,
    cycle_cost,
    hourly_consumption,
    max_charge_rate,
):
    """Call all optimize_battery_XX functions and return the best result."""
    results = []

    # Call each optimize_battery_XX function
    results.append(
        optimize_battery_dynamic(
            prices,
            total_capacity,
            reserved_capacity,
            cycle_cost,
            hourly_consumption,
            max_charge_rate,
        )
    )
    results.append(
        optimize_battery_dynamic_2(
            prices,
            total_capacity,
            reserved_capacity,
            cycle_cost,
            hourly_consumption,
            max_charge_rate,
        )
    )
    #    results.append(
    #        optimize_battery_dynamic_NEW(
    #            prices,
    #            total_capacity,
    #            reserved_capacity,
    #            cycle_cost,
    #            hourly_consumption,
    #            max_charge_rate,
    #        )
    #    )

    # Find the result with the maximum cost savings
    return max(results, key=lambda result: result["cost_savings"])
