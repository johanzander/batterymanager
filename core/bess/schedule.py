"""Generic battery schedule representation with hourly granularity."""

import logging

from .savings_calculator import HourlyResult, SavingsCalculator

logger = logging.getLogger(__name__)


def create_interval(
    start_time: str, end_time: str, state: str, action: float, state_of_energy: float
) -> dict:
    """Create an interval dictionary with all required fields."""
    return {
        "start_time": start_time,
        "end_time": end_time,
        "state": state,
        "action": float(action),
        "state_of_energy": float(state_of_energy),
    }


class Schedule:
    """Generic battery schedule representation with hourly granularity."""

    def __init__(self):
        """Initialize schedule state."""
        self.actions: list[float] = []
        self.state_of_energy: list[float] = []
        self.intervals: list[dict] = []
        self.hourly_results: list[HourlyResult] = []
        self.calc: SavingsCalculator = None
        self.optimization_results = None

    def set_optimization_results(
        self,
        actions: list[float],
        state_of_energy: list[float],
        prices: list[float],
        cycle_cost: float,
        hourly_consumption: float,
    ):
        """Set optimization results and calculate costs."""
        self.actions = [float(action) for action in actions]
        self.state_of_energy = [float(level) for level in state_of_energy]

        self.calc = SavingsCalculator(cycle_cost, hourly_consumption)
        self.hourly_results = self.calc.calculate_hourly_results(
            prices=prices, actions=self.actions, battery_levels=self.state_of_energy
        )

        schedule_data = self.calc.format_schedule_data(self.hourly_results)
        self.optimization_results = {
            "actions": self.actions,
            "state_of_energy": self.state_of_energy,
            "base_cost": schedule_data["summary"]["baseCost"],
            "optimized_cost": schedule_data["summary"]["optimizedCost"],
            "cost_savings": schedule_data["summary"]["savings"],
            "hourly_costs": [
                {
                    "base_cost": r.base_cost,
                    "grid_cost": r.grid_cost,
                    "battery_cost": r.battery_cost,
                    "total_cost": r.total_cost,
                    "savings": r.savings,
                }
                for r in self.hourly_results
            ],
        }

        self._create_hourly_intervals()

    def _create_hourly_intervals(self):
        """Create one interval per hour."""
        self.intervals = [
            create_interval(
                start_time=f"{hour:02d}:00",
                end_time=f"{hour:02d}:59",
                state="charging"
                if self.actions[hour] > 0
                else "discharging"
                if self.actions[hour] < 0
                else "standby",
                action=self.actions[hour],
                state_of_energy=self.state_of_energy[hour],
            )
            for hour in range(len(self.actions))
        ]

    def get_hour_settings(self, hour: int) -> dict:
        """Get settings for a specific hour."""
        if hour < 0 or hour >= len(self.intervals):
            return {
                "state": "standby",
                "action": 0.0,
                "state_of_energy": float(
                    self.state_of_energy[0] if self.state_of_energy else 0.0
                ),
            }
        return {
            "state": self.intervals[hour]["state"],
            "action": self.intervals[hour]["action"],
            "state_of_energy": self.intervals[hour]["state_of_energy"],
        }

    def get_daily_intervals(self) -> list[dict]:
        """Get all hourly intervals for the day."""
        return self.intervals

    def get_schedule_data(self) -> dict:
        """Get complete schedule data."""
        if not self.calc or not self.hourly_results:
            raise ValueError(
                "Schedule not fully initialized - missing cost calculations"
            )
        return self.calc.format_schedule_data(self.hourly_results)
