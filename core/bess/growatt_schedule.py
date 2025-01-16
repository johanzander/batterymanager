"""Growatt schedule management module for TOU (Time of Use) and hourly controls."""

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_detailed_interval(
    segment_id: int,
    batt_mode: str,
    start_time: str,
    end_time: str,
    enabled: bool,
    grid_charge: bool,
    discharge_rate: int,
) -> dict:
    """Create a detailed Growatt interval dictionary for overview purposes."""
    return {
        "segment_id": segment_id,
        "batt_mode": batt_mode,
        "start_time": start_time,
        "end_time": end_time,
        "enabled": enabled,
        "grid_charge": grid_charge,
        "discharge_rate": discharge_rate,
    }


def create_tou_interval(
    segment_id: int,
    start_time: str,
    end_time: str,
) -> dict:
    """Create a simplified Growatt TOU interval dictionary."""
    return {
        "segment_id": segment_id,
        "batt_mode": "battery-first",
        "start_time": start_time,
        "end_time": end_time,
        "enabled": True,
    }


class GrowattScheduleManager:
    """Creates Growatt-specific schedules from generic battery schedule."""

    def __init__(self):
        """Initialize the schedule manager."""
        self.max_intervals = 8  # Growatt supports up to 8 TOU intervals
        self.current_schedule = None
        self.detailed_intervals = []  # For overview display
        self.tou_intervals = []  # For actual TOU settings

    def apply_schedule(self, schedule):
        """Convert generic schedule to Growatt-specific intervals."""
        self.current_schedule = schedule
        self._consolidate_and_convert()
        self._log_growatt_schedule()
        self._log_daily_TOU_settings()

    def _consolidate_and_convert(self):
        """Convert hourly schedule to consolidated Growatt intervals."""
        if not self.current_schedule or not (
            hourly_intervals := self.current_schedule.get_daily_intervals()
        ):
            return

        # Create detailed intervals for overview
        detailed = []
        current_state = hourly_intervals[0]["state"]
        start_time = hourly_intervals[0]["start_time"]

        for hour, interval in enumerate(hourly_intervals[1:], 1):
            if interval["state"] != current_state:
                detailed.append(
                    create_detailed_interval(
                        len(detailed) + 1,
                        "load-first"
                        if current_state == "discharging"
                        else "battery-first",
                        start_time,
                        f"{hour-1:02d}:59",
                        True,
                        current_state == "charging",
                        100 if current_state == "discharging" else 0,
                    )
                )
                current_state = interval["state"]
                start_time = interval["start_time"]

        # Add last detailed interval
        detailed.append(
            create_detailed_interval(
                len(detailed) + 1,
                "load-first" if current_state == "discharging" else "battery-first",
                start_time,
                "23:59",
                True,
                current_state == "charging",
                100 if current_state == "discharging" else 0,
            )
        )

        self.detailed_intervals = detailed

        # Create simplified TOU intervals (consolidating consecutive battery-first periods)
        tou = []
        current_start = None

        for i, interval in enumerate(self.detailed_intervals):
            if interval["batt_mode"] == "battery-first":
                if current_start is None:
                    current_start = interval["start_time"]
            elif current_start is not None:
                # End of a battery-first sequence
                tou.append(
                    create_tou_interval(
                        len(tou) + 1,
                        current_start,
                        self.detailed_intervals[i - 1]["end_time"],
                    )
                )
                current_start = None

        # Handle last interval if it was battery-first
        if current_start is not None:
            tou.append(
                create_tou_interval(
                    len(tou) + 1,
                    current_start,
                    self.detailed_intervals[-1]["end_time"],
                )
            )

        self.tou_intervals = tou

    def get_daily_TOU_settings(self):
        """Get Growatt-specific TOU settings (battery-first intervals only)."""
        if not self.tou_intervals:
            return []

        # Return only battery-first intervals up to max_intervals
        return self.tou_intervals[: self.max_intervals]

    def get_hourly_settings(self, hour):
        """Get Growatt-specific settings for a given hour."""
        if not self.current_schedule:
            return {"grid_charge": False, "discharge_rate": 0}

        # special case where we only have one 'battery-first' interval, let's force charge
#        if len(self.detailed_intervals) == 1 and self.detailed_intervals[0]["batt_mode"] == "battery-first":
#            return {"grid_charge": True, "discharge_rate": 0}

        settings = self.current_schedule.get_hour_settings(hour)
        return {
            "grid_charge": settings["state"] == "charging",
            "discharge_rate": 100 if settings["state"] == "discharging" else 0,
        }

    def _log_growatt_schedule(self):
        """Log the current Growatt schedule with full details."""
        if not self.detailed_intervals:
            return

        col_widths = {
            "segment": 8,
            "start": 9,
            "end": 8,
            "mode": 15,
            "enabled": 8,
            "grid": 10,
            "discharge": 10,
        }
        total_width = (
            sum(col_widths.values()) + len(col_widths) - 1
        )  # -1 for last space

        header_format = (
            "{:>" + str(col_widths["segment"]) + "} "
            "{:>" + str(col_widths["start"]) + "} "
            "{:>" + str(col_widths["end"]) + "} "
            "{:>" + str(col_widths["mode"]) + "} "
            "{:>" + str(col_widths["enabled"]) + "} "
            "{:>" + str(col_widths["grid"]) + "} "
            "{:>" + str(col_widths["discharge"]) + "}"
        )

        lines = [
            "\n\nGrowatt Daily Schedule Overview:",
            "═" * total_width,
            header_format.format(
                "Segment",
                "StartTime",
                "EndTime",
                "BatteryMode",
                "Enabled",
                "GridChrg",
                "DischRate",
            ),
            "─" * total_width,
        ]

        interval_format = (
            "{segment_id:>" + str(col_widths["segment"]) + "} "
            "{start_time:>" + str(col_widths["start"]) + "} "
            "{end_time:>" + str(col_widths["end"]) + "} "
            "{batt_mode:>" + str(col_widths["mode"]) + "} "
            "{enabled!s:>" + str(col_widths["enabled"]) + "} "
            "{grid_charge!s:>" + str(col_widths["grid"]) + "} "
            "{discharge_rate:>" + str(col_widths["discharge"]) + "}"
        )
        formatted_intervals = [
            interval_format.format(**interval) for interval in self.detailed_intervals
        ]
        lines.extend(formatted_intervals)
        lines.append("═" * total_width)
        logger.info("\n".join(lines))

    def _log_daily_TOU_settings(self):
        """Log the final simplified TOU settings."""
        daily_settings = self.get_daily_TOU_settings()
        if not daily_settings:
            return

        col_widths = {"segment": 8, "start": 9, "end": 8, "mode": 15, "enabled": 8}
        total_width = (
            sum(col_widths.values()) + len(col_widths) - 1
        )  # -1 for last space

        header_format = (
            "{:>" + str(col_widths["segment"]) + "} "
            "{:>" + str(col_widths["start"]) + "} "
            "{:>" + str(col_widths["end"]) + "} "
            "{:>" + str(col_widths["mode"]) + "} "
            "{:>" + str(col_widths["enabled"]) + "}"
        )

        lines = [
            "\n\nGrowatt TOU Settings:",
            "═" * total_width,
            header_format.format(
                "Segment",
                "StartTime",
                "EndTime",
                "BatteryMode",
                "Enabled",
            ),
            "─" * total_width,
        ]

        setting_format = (
            "{segment_id:>" + str(col_widths["segment"]) + "} "
            "{start_time:>" + str(col_widths["start"]) + "} "
            "{end_time:>" + str(col_widths["end"]) + "} "
            "{batt_mode:>" + str(col_widths["mode"]) + "} "
            "{enabled!s:>" + str(col_widths["enabled"]) + "}"
        )
        formatted_settings = [
            setting_format.format(**setting) for setting in daily_settings
        ]
        lines.extend(formatted_settings)
        lines.append("═" * total_width)
        logger.info("\n".join(lines))
