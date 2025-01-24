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
        """Convert hourly schedule to consolidated Growatt intervals.

        This implementation handles several Growatt inverter limitations and quirks:

        1. Wake-up Issue:
           - The battery can go to sleep during inactive periods
           - When sleeping, it may not wake up automatically to start charging
           - To prevent this, we need to add a special 15-min wake-up period (load-first mode)
             just before any charging period that follows an idle period

        2. Interval Constraints:
           - Intervals cannot overlap
           - Each interval must end exactly 1 minute before the next begins
           - Example sequence:
             * 00:00-01:44 (battery-first)
             * 01:45-01:59 (wake-up period)
             * 02:00-04:59 (charging period)

        3. End of Day Handling:
           - Last regular interval must end at 23:44
           - Special load-first idle period from 23:45-23:59 is always added

        4. Interval Management:
           - Consecutive hours with same behavior are consolidated into single intervals
           - Wake-up periods are inserted by ending the current interval 15 mins early
           - Each interval's end time becomes the next interval's start time minus 1 minute
        """
        if not self.current_schedule or not (
            hourly_intervals := self.current_schedule.get_daily_intervals()
        ):
            return

        detailed = []
        start_time = hourly_intervals[0]["start_time"]

        # Initialize state tracking for the first interval
        current_action = hourly_intervals[0]["action"]
        is_charging = current_action > 0
        is_discharging = current_action < 0

        # Process all intervals except the last one
        for hour, next_interval in enumerate(hourly_intervals[1:], 1):
            next_action = next_interval["action"]
            next_is_charging = next_action > 0
            next_is_discharging = next_action < 0

            # Detect actual behavior changes by comparing:
            # - Changes in charging state (starting/stopping charging)
            # - Changes in discharging state (starting/stopping discharging)
            # - Transitions between active and idle states
            behavior_changed = (
                (is_charging != next_is_charging)  # Charging state changed
                or (is_discharging != next_is_discharging)  # Discharging state changed
                or (current_action == 0 and next_action != 0)  # Starting activity
                or (current_action != 0 and next_action == 0)  # Stopping activity
            )

            # Check if we need to add a wake-up period before the next interval
            needs_wake_up = next_is_charging and not is_charging and hour > 0

            if behavior_changed:
                # Determine appropriate end time:
                # - If wake-up needed: end 15 mins early (XX:44)
                # - If last hour: end at 23:44
                # - Otherwise: end at normal boundary (XX:59)
                end_time = (
                    f"{hour-1:02d}:44"
                    if needs_wake_up
                    else "23:44"
                    if hour == 24
                    else f"{hour-1:02d}:59"
                )

                # Add current interval if it has non-zero duration
                if start_time != end_time[:5]:  # Only add if start != end
                    detailed.append(
                        create_detailed_interval(
                            len(detailed) + 1,
                            "load-first" if is_discharging else "battery-first",
                            start_time,
                            end_time,
                            True,
                            is_charging,
                            100 if is_discharging else 0,
                        )
                    )

                # Add wake-up period if transitioning to charging state
                if needs_wake_up:
                    detailed.append(
                        create_detailed_interval(
                            len(detailed) + 1,
                            "load-first",
                            f"{hour-1:02d}:45",
                            f"{hour-1:02d}:59",
                            True,
                            False,  # No grid charge
                            0,  # No discharge
                        )
                    )

                # Start new interval at the hour boundary
                start_time = next_interval["start_time"]

            # Update state tracking for next iteration
            current_action = next_action
            is_charging = next_is_charging
            is_discharging = next_is_discharging

        # Add final regular interval if not already ending at 23:44
        if start_time != "23:44":
            detailed.append(
                create_detailed_interval(
                    len(detailed) + 1,
                    "load-first" if is_discharging else "battery-first",
                    start_time,
                    "23:44",
                    True,
                    is_charging,
                    100 if is_discharging else 0,
                )
            )

        # Add the mandatory end-of-day idle period (23:45-23:59)
        detailed.append(
            create_detailed_interval(
                len(detailed) + 1,
                "load-first",
                "23:45",
                "23:59",
                True,
                False,
                0,
            )
        )

        self.detailed_intervals = detailed

        # Create simplified TOU intervals by consolidating battery-first periods
        # Note: load-first periods are implicit (any time not covered by battery-first)
        tou = []
        current_start = None

        for i, interval in enumerate(self.detailed_intervals[:-1]):
            if interval["batt_mode"] == "battery-first":
                if current_start is None:
                    current_start = interval["start_time"]
            elif current_start is not None:
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
            last_regular_interval = self.detailed_intervals[-2]
            tou.append(
                create_tou_interval(
                    len(tou) + 1,
                    current_start,
                    last_regular_interval["end_time"],
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

        self._log_hourly_settings()
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

    def _log_hourly_settings(self):
        """Log the hourly settings for the current schedule."""
        if not self.current_schedule:
            logger.warning("No schedule available")
            return

        output = "\n -= Schedule =- \n"
        for h in range(24):
            settings = self.current_schedule.get_hour_settings(h)
            grid_charge_enabled = settings["state"] == "charging"
            discharge_rate = 100 if settings["state"] == "discharging" else 0
            output += f"Hour: {h:2d}, Grid Charge: {grid_charge_enabled}, Discharge Rate: {discharge_rate}\n"

        logger.info(output)
