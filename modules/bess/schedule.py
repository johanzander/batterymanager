"""Generic battery schedule representation with hourly granularity."""

import logging

logger = logging.getLogger(__name__)


def create_interval(start_time, end_time, state, action, state_of_energy):
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
        self.timestamps = []
        self.actions = []
        self.state_of_energy = []
        self.intervals = []
        self.optimization_results = {}

    def set_optimization_results(self, actions, state_of_energy, results):
        """Set optimization results and create hourly intervals."""
        self.actions = [float(action) for action in actions]
        self.state_of_energy = [float(level) for level in state_of_energy]
        self.optimization_results = results
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

    def get_hour_settings(self, hour):
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

    def get_daily_intervals(self):
        """Get all hourly intervals for the day."""
        return self.intervals

    def _log_schedule(self):
        """Print current schedule in formatted table."""
        if not self.intervals:
            logger.warning("No schedule has been calculated yet")
            return

        lines = [
            "\nBattery Schedule (Hourly Intervals):",
            "═" * 80,
            "{:<10} {:<10} {:<12} {:<10} {:<12}".format(
                "StartTime", "EndTime", "State", "Action", "BattLevel"
            ),
            "─" * 80,
        ]

        def format_interval(i):
            return "{:<10} {:<10} {:<12} {:<10.2f} {:<12.1f}".format(
                i["start_time"],
                i["end_time"],
                i["state"],
                i["action"],
                i["state_of_energy"],
            )

        lines.extend(format_interval(interval) for interval in self.intervals)
        lines.append("═" * 80)
        logger.info("\n".join(lines))
