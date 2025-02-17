"""Module for battery schedule savings calculations."""


class HourlyResult:
    """Results for a single hour."""

    def __init__(
        self,
        hour: int,
        price: float,
        base_consumption: float,
        battery_action: float,
        battery_level: float,
        base_cost: float,
        grid_cost: float,
        battery_cost: float,
        total_cost: float,
        savings: float,
    ):
        """Init function."""
        self.hour = hour
        self.price = price
        self.base_consumption = base_consumption
        self.battery_action = battery_action
        self.battery_level = battery_level
        self.base_cost = base_cost
        self.grid_cost = grid_cost
        self.battery_cost = battery_cost
        self.total_cost = total_cost
        self.savings = savings

    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "hour": f"{self.hour:02d}:00",
            "price": self.price,
            "consumption": self.base_consumption,
            "batteryLevel": self.battery_level,
            "action": self.battery_action,
            "gridCost": self.grid_cost,
            "batteryCost": self.battery_cost,
            "totalCost": self.total_cost,
            "baseCost": self.base_cost,
            "savings": self.savings,
        }


class SavingsCalculator:
    """Calculates costs and savings for battery schedule."""

    def __init__(self, cycle_cost: float, hourly_consumption: list[float]):
        """Init function."""
        self.cycle_cost = cycle_cost
        self.hourly_consumption = hourly_consumption

    def calculate_hourly_results(
        self, prices: list[float], actions: list[float], battery_levels: list[float]
    ) -> list[HourlyResult]:
        """Calculate detailed results for each hour."""
        results = []

        for hour in range(len(actions)):
            price = prices[hour]
            action = actions[hour]
            battery_level = battery_levels[hour]

            # Calculate base case (no battery)
            base_cost = self.hourly_consumption[hour] * price

            # Calculate with battery
            if action >= 0:  # Charging or standby
                total_consumption = self.hourly_consumption[hour] + action
                grid_cost = total_consumption * price
                battery_cost = action * self.cycle_cost
            else:  # Discharging
                remaining_consumption = (
                    self.hourly_consumption[hour] + action
                )  # action is negative
                grid_cost = remaining_consumption * price
                battery_cost = 0

            total_cost = grid_cost + battery_cost
            savings = base_cost - total_cost

            results.append(
                HourlyResult(
                    hour=hour,
                    price=price,
                    base_consumption=self.hourly_consumption[hour],
                    battery_action=action,
                    battery_level=battery_level,
                    base_cost=base_cost,
                    grid_cost=grid_cost,
                    battery_cost=battery_cost,
                    total_cost=total_cost,
                    savings=savings,
                )
            )

        return results

    def calculate_summary(self, hourly_results: list[HourlyResult]) -> dict:
        """Calculate summary metrics from hourly results."""
        total_base_cost = 0
        total_grid_cost = 0
        total_battery_cost = 0
        total_savings = 0
        total_charged = 0
        total_discharged = 0

        for r in hourly_results:
            total_base_cost += r.base_cost
            total_grid_cost += r.grid_cost
            total_battery_cost += r.battery_cost
            total_savings += r.savings
            if r.battery_action > 0:
                total_charged += r.battery_action
            elif r.battery_action < 0:
                total_discharged += -r.battery_action

        total_optimized_cost = total_grid_cost + total_battery_cost
        cycle_count = (
            min(total_charged, total_discharged) / 30
        )  # Assuming 30kWh capacity
        return {
            "baseCost": total_base_cost,
            "optimizedCost": total_optimized_cost,
            "gridCosts": total_grid_cost,
            "batteryCosts": total_battery_cost,
            "savings": total_savings,
            "cycleCount": cycle_count,
        }

    def format_schedule_data(self, hourly_results: list[HourlyResult]) -> dict:
        """Format complete schedule data for API response."""
        return {
            "hourlyData": [r.to_dict() for r in hourly_results],
            "summary": self.calculate_summary(hourly_results),
        }