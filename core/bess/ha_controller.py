"""Home Assistant pyscript Controller."""


class HomeAssistantController:
    """A class for interacting with Inverter controls via Home Assistant."""

    def __init__(self):
        """Initialize the Controller with default values."""
        self.df_batt_schedule = None
        self.max_attempts = 4
        self.retry_delay = 4  # seconds
        self.test_mode = False

    def service_call_with_retry(self, service_domain, service_name, **kwargs):
        """Call the service and retry upon failure."""
        if self.test_mode:
            log.info(
                "[TEST MODE] Would call service %s.%s with args: %s",
                service_domain,
                service_name,
                kwargs,
            )
            return

        for attempt in range(self.max_attempts):
            try:
                service.call(service_domain, service_name, **kwargs)
                log.debug(
                    "Service call %s.%s succeeded on attempt %d/%d",
                    service_domain,
                    service_name,
                    attempt + 1,
                    self.max_attempts,
                )
                return  # Success, exit function
            except Exception as e:
                if attempt < self.max_attempts - 1:  # Not the last attempt
                    log.warning(
                        "Service call %s.%s failed on attempt %d/%d: %s. Retrying in %d seconds...",
                        service_domain,
                        service_name,
                        attempt + 1,
                        self.max_attempts,
                        str(e),
                        self.retry_delay,
                    )
                    task.sleep(self.retry_delay)
                else:  # Last attempt failed
                    log.error(
                        "Service call %s.%s failed on final attempt %d/%d: %s",
                        service_domain,
                        service_name,
                        attempt + 1,
                        self.max_attempts,
                        str(e),
                    )
                    raise  # Re-raise the last exception

    def get_estimated_consumption(self) -> float:
        """Get the estimated hourly consumption in kWh."""
        return float(state.get("sensor.average_grid_import_power")) / 1000  # noqa: F821

    def get_battery_soc(self) -> int:
        """Get the battery state of charge (SOC)."""
        return int(state.get("sensor.rkm0d7n04x_statement_of_charge_soc"))

    def get_charge_stop_soc(self) -> int:
        """Get the charge stop state of charge (SOC)."""
        return int(state.get("number.rkm0d7n04x_charge_stop_soc"))

    def set_charge_stop_soc(self, charge_stop_soc: int):
        """Set the charge stop state of charge (SOC)."""

        self.service_call_with_retry(
            "number",
            "set_value",
            entity_id="number.rkm0d7n04x_charge_stop_soc",
            value=charge_stop_soc,
            blocking=True,
        )

    def get_discharge_stop_soc(self) -> int:
        """Get the discharge stop state of charge (SOC)."""
        return int(state.get("number.rkm0d7n04x_discharge_stop_soc"))

    def set_discharge_stop_soc(self, discharge_stop_soc: int):
        """Set the charge stop state of charge (SOC)."""

        self.service_call_with_retry(
            "number",
            "set_value",
            entity_id="number.rkm0d7n04x_discharge_stop_soc",
            value=discharge_stop_soc,
            blocking=True,
        )

    def get_charging_power_rate(self) -> int:
        """Get the charging power rate."""
        return int(state.get("number.rkm0d7n04x_charging_power_rate"))

    def set_charging_power_rate(self, rate: int):
        """Set the charging power rate."""

        self.service_call_with_retry(
            "number",
            "set_value",
            entity_id="number.rkm0d7n04x_charging_power_rate",
            value=rate,
            blocking=True,
        )

    def get_discharging_power_rate(self) -> int:
        """Get the discharging power rate."""
        return int(state.get("number.rkm0d7n04x_discharging_power_rate"))

    def set_discharging_power_rate(self, rate: int):
        """Set the discharging power rate."""

        self.service_call_with_retry(
            "number",
            "set_value",
            entity_id="number.rkm0d7n04x_discharging_power_rate",
            value=rate,
            blocking=True,
        )

    def battery_scheduling_enabled(self) -> bool:
        """Return True if battery scheduling is enabled."""
        return state.get("input_boolean.battery_scheduling") == "on"  # noqa: F821

    def set_grid_charge(self, enable: bool):
        """Enable or disable grid charging."""
        if enable:
            log.info("Enabling grid charge")
            self.service_call_with_retry(
                "switch",
                "turn_on",
                entity_id="switch.rkm0d7n04x_charge_from_grid",
                blocking=True,
            )
        else:
            log.info("Disabling grid charge")
            self.service_call_with_retry(
                "switch",
                "turn_off",
                entity_id="switch.rkm0d7n04x_charge_from_grid",
                blocking=True,
            )

    def grid_charge_enabled(self) -> bool:
        """Return True if grid charging is enabled."""
        return state.get("switch.rkm0d7n04x_charge_from_grid") == "on"

    def set_inverter_time_segment(
        self,
        segment_id: int,
        batt_mode: str,
        start_time: int,
        end_time: int,
        enabled: bool,
    ):
        """Set the inverter time segment with retry logic."""
        log.info(
            "Setting inverter time segment: segment_id=%d, batt_mode=%s, start_time=%s, end_time=%s, enabled=%s",
            segment_id,
            batt_mode,
            start_time,
            end_time,
            enabled,
        )

        self.service_call_with_retry(
            "growatt_server",
            "update_tlx_inverter_time_segment",
            segment_id=segment_id,
            batt_mode=batt_mode,
            start_time=start_time,
            end_time=end_time,
            enabled=enabled,
            blocking=True,
        )

    def print_inverter_status(self):
        """Print the battery settings and consumption prediction."""
        test_mode_str = "[TEST MODE] " if self.test_mode else ""
        log.info(
            "\n\n===================================\n"
            "%sInverter Settings\n"
            "===================================\n"
            "Discharge Scheduling Enabled: %5s\n"
            "Charge from Grid Enabled:     %5s\n"
            "State of Charge (SOC):       %5d%%\n"
            "Charge Stop SOC:             %5d%%\n"
            "Charging Power Rate:         %5d%%\n"
            "Discharging Power Rate:      %5d%%\n"
            "Discharge Stop SOC:          %5d%%\n",
            test_mode_str,
            self.battery_scheduling_enabled(),
            self.grid_charge_enabled(),
            self.get_battery_soc(),
            self.get_charge_stop_soc(),
            self.get_charging_power_rate(),
            self.get_discharging_power_rate(),
            self.get_discharge_stop_soc(),
        )

    def set_test_mode(self, enabled: bool):
        """Enable or disable test mode."""
        self.test_mode = enabled
        log.info("%s test mode", "Enabled" if enabled else "Disabled")

    def disable_all_TOU_settings(self):
        """Clear the Time of Use (TOU) settings."""

        for segment_id in range(1, 9):
            self.set_inverter_time_segment(
                segment_id=segment_id,
                batt_mode="battery-first",
                start_time="00:00",
                end_time="23:59",
                enabled=False,
            )

    def get_nordpool_prices_today(self) -> list[float]:
        """Get today's Nordpool prices from Home Assistant sensor.
        
        Returns:
            List of hourly prices for today (24 values)
        """
        try:
            prices = state.get("sensor.nordpool_kwh_se4_sek_2_10_025.today")
            if not prices:
                raise ValueError("No prices available from Nordpool sensor")
            return prices
        except Exception as e:
            log.error("Error getting today's Nordpool prices: %s", str(e))
            return []

    def get_nordpool_prices_tomorrow(self) -> list[float]:
        """Get tomorrow's Nordpool prices from Home Assistant sensor.
        
        Returns:
            List of hourly prices for tomorrow (24 values)
        """
        try:
            prices = state.get("sensor.nordpool_kwh_se4_sek_2_10_025.tomorrow")
            if not prices:
                raise ValueError("No prices available for tomorrow yet")
            return prices
        except Exception as e:
            log.error("Error getting tomorrow's Nordpool prices: %s", str(e))
            return []