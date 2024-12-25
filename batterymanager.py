"""Battery Manager module."""

import datetime

import bess
import pandas as pd


class ElectricityPrices:
    """A class for managing electricity prices."""

    def __init__(self):
        self.electricity_prices_df: pd.DataFrame = None

    def get_electricity_prices(self) -> pd.DataFrame:
        """Update the electricity prices and store them in a pandas DataFrame."""
        # Fetch current electricity price from Nordpool sensor's today attribute
        #        today_electricity_price = sensor.nordpool_kwh_se4_sek_2_10_025.tomorrow  # noqa: F821
        today_electricity_price = sensor.nordpool_kwh_se4_sek_2_10_025.today  # noqa: F821
        # Test list with electricity prices
        electricity_prices_2024_08_16 = [
            0.9827,
            0.8419,
            0.0321,
            0.0097,
            0.0098,
            0.9136,
            1.4433,
            1.5162,
            1.4029,
            1.1346,
            0.8558,
            0.6485,
            0.2895,
            0.1363,
            0.1253,
            0.6200,
            0.8880,
            1.1662,
            1.5163,
            2.5908,
            2.7325,
            1.9312,
            1.5121,
            1.3056,
        ]
        #        today_electricity_price = electricity_prices_2024_08_16
        # Create a pandas DataFrame with the electricity prices
        self.electricity_prices_df = pd.DataFrame(
            {
                "Timestamp": pd.date_range(
                    start=datetime.datetime.now().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ),
                    periods=len(today_electricity_price),
                    freq="h",
                ),
                "ElectricityPrice": today_electricity_price,
            }
        )

        self.electricity_prices_df.set_index("Timestamp", inplace=True)

        self.electricity_prices_df["ElectricityPriceBuy"] = (
            self.electricity_prices_df["ElectricityPrice"]
            + bess.TIBBER_MARKUP_SEK_PER_KWH
        ) * 1.25 + bess.ADDITIONAL_ELECTRICITY_COSTS_SEK_PER_KWH
        self.electricity_prices_df["ElectricityPriceSell"] = (
            self.electricity_prices_df["ElectricityPrice"]
            + bess.TAX_REDUCTION_SOLD_ELECTRICITY
        )

        return self.electricity_prices_df


class GrowattInverterController:
    """A class for controlling a Growatt inverter."""

    def __init__(self):
        """Initialize the BatteryManager with default values."""
        self.df_batt_schedule: pd.DataFrame = None

    def get_battery_soc(self) -> int:
        """Get the battery state of charge (SOC)."""
        return int(state.get("sensor.rkm0d7n04x_statement_of_charge_soc"))

    def get_charge_stop_soc(self) -> int:
        """Get the charge stop state of charge (SOC)."""
        return int(state.get("number.rkm0d7n04x_charge_stop_soc"))

    def set_charge_stop_soc(self, charge_stop_soc: int):
        """Set the charge stop state of charge (SOC)."""
        service.call(
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
        service.call(
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
        service.call(  # noqa: F821
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
        service.call(  # noqa: F821
            "number",
            "set_value",
            entity_id="number.rkm0d7n04x_discharging_power_rate",
            value=rate,
            blocking=True,
        )

    def set_battery_scheduling(self, enable: bool):
        """Enable or disable battery discharge scheduling."""
        action = "turn_on" if enable else "turn_off"
        service.call(  # noqa: F821
            "input_boolean",
            action,
            entity_id="input_boolean.battery_scheduling",
            blocking=True,
        )

    def battery_scheduling_enabled(self) -> bool:
        """Return True if battery scheduling is enabled."""
        return state.get("input_boolean.battery_scheduling") == "on"  # noqa: F821

    def set_grid_charge(self, enable: bool):
        """Enable or disable grid charging."""
        if enable:
            log.info("Enabling grid charge")
            switch.turn_on(  # noqa: F821
                entity_id="switch.rkm0d7n04x_charge_from_grid", blocking=True
            )
        else:
            log.info("Disabling grid charge")
            switch.turn_off(  # noqa: F821
                entity_id="switch.rkm0d7n04x_charge_from_grid", blocking=True
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
        """Set the inverter time segment with the specified parameters."""
        log.info(
            "Setting inverter time segment: segment_id=%d, batt_mode=%s, start_time=%s, end_time=%s, enabled=%s",
            segment_id,
            batt_mode,
            start_time,
            end_time,
            enabled,
        )
        hass.services.async_call(
            "growatt_server",
            "update_tlx_inverter_time_segment",
            {
                "segment_id": segment_id,
                "batt_mode": batt_mode,
                "start_time": start_time,
                "end_time": end_time,
                "enabled": enabled,
            },
            True,
        )

    def print_inverter_status(self):
        """Print the battery settings and consumption prediction."""
        log.info(
            "\n------------------------\n"
            "Battery Settings\n"
            "------------------------\n"
            "Discharge Scheduling Enabled: %5s\n"
            "Charge from Grid Enabled:     %5s\n"
            "State of Charge (SOC):       %5d%%\n"
            "Charge Stop SOC:             %5d%%\n"
            "Charging Power Rate:         %5d%%\n"
            "Discharging Power Rate:      %5d%%\n"
            "Discharge Stop SOC:          %5d%%\n",
            self.battery_scheduling_enabled(),
            self.grid_charge_enabled(),
            self.get_battery_soc(),
            self.get_charge_stop_soc(),
            self.get_charging_power_rate(),
            self.get_discharging_power_rate(),
            self.get_discharge_stop_soc(),
        )

    def update_grid_charge_schedule(self):
        """Update the grid charge schedule based on the current hour."""

        current_hour = datetime.datetime.now().hour
        grid_charge_enabled = self.grid_charge_enabled()

        # Check if current hour is between 11:00 and 06:00
        if current_hour >= 23 or current_hour < 6:
            if not grid_charge_enabled:
                self.set_grid_charge(True)
        elif grid_charge_enabled:
            self.set_grid_charge(False)

    async def disable_all_TOU_settings(self):
        """Clear the Time of Use (TOU) settings."""
        self.set_grid_charge(False)
        for segment_id in range(1, 2):
            self.set_inverter_time_segment(
                segment_id=segment_id,
                batt_mode="battery-first",
                start_time="00:00",
                end_time="23:59",
                enabled=False,
            )

    async def set_TOU_settings(self, schedule: pd.DataFrame):
        """Set the Time of Use (TOU) settings based on the schedule."""
        self.disable_all_TOU_settings()
        for index, row in schedule.iterrows():
            self.set_inverter_time_segment(
                segment_id=index + 1,
                batt_mode=row["GrowattState"],
                start_time=row["StartTime"],
                end_time=row["EndTime"],
                enabled=True,
            )

    def set_hourly_settings(self, schedule: pd.DataFrame):
        """Set the inverter schedule based on the schedule."""
        current_hour = datetime.datetime.now().hour

        target_discharge_power_rate = schedule.loc[current_hour, "Discharge Power Rate"]
        current_discharge_power_rate = self.get_discharging_power_rate()
        if target_discharge_power_rate != current_discharge_power_rate:
            log.info(
                "Changing discharging power rate from %d to %d",
                current_discharge_power_rate,
                target_discharge_power_rate,
            )
            self.set_discharging_power_rate(target_discharge_power_rate)
        else:
            log.info(
                "Discharging power rate remains unchanged at %d",
                current_discharge_power_rate,
            )

        grid_charge = schedule.loc[current_hour, "GridCharge"]
        current_grid_charge = self.grid_charge_enabled()
        if grid_charge != current_grid_charge:
            log.info(
                "Changing grid charge from %s to %s",
                current_grid_charge,
                grid_charge,
            )
            self.set_grid_charge(grid_charge)
        else:
            log.info("Grid charge remains unchanged at %s", current_grid_charge)


prices = ElectricityPrices()
inverter = GrowattInverterController()
manager = bess.BatteryManager()
schedule = None

columns_to_print = [
    "StartTime",
    "EndTime",
    "ElectricityPrice",
    "State",
    "GrowattState",
    "Battery SOE",
    "Charge",
    "Discharge",
    "Discharge Power Rate",
    "GridCharge",
]


@time_trigger("startup")
def run_on_startup():
    """Run automatically on startup or reload."""
    file_save_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.info("BatteryManager initializing, version: %s", file_save_date)
    run_midnight_task()
    run_hourly_task()


def run_midnight_task():
    """Run automatically at midnight to update the TOU settings."""
    log.info("Running midnight task")

    electricity_prices = prices.get_electricity_prices()
    manager.set_electricity_prices(electricity_prices)
    charging_power_rate = inverter.get_charging_power_rate()
    manager.set_prediction_data(
        estimated_consumption_per_hour_kwh=3.5,
        max_charging_power_rate=charging_power_rate,
    )
    global schedule
    schedule = manager.calculate_schedule()
    bess.print_to_terminal(schedule, columns_to_print)
    growatt_TOU_schedule = bess.get_growatt_time_schedule(schedule)
    inverter.set_TOU_settings(growatt_TOU_schedule)
    bess.print_to_terminal(growatt_TOU_schedule, columns_to_print)


@time_trigger("cron(0 * * * *)")
def run_hourly_task():
    if datetime.datetime.now().hour == 0:
        run_midnight_task()
    """Run automatically every hour to update the grid charge schedule."""
    log.info("Running hourly task")
    inverter.print_inverter_status()
    inverter.set_hourly_settings(schedule)
