"""Battery Manager module."""

import datetime
from zoneinfo import ZoneInfo

import bess
from bess.constants import (
    ADDITIONAL_ELECTRICITY_COSTS_SEK_PER_KWH,
    BATTERY_MIN_SOC,
    BATTERY_STORAGE_SIZE_KWH,
    TAX_REDUCTION_SOLD_ELECTRICITY,
    TIBBER_MARKUP_SEK_PER_KWH,
)
import pandas as pd


class BatteryManager:
    """A dummy class for demonstration purposes."""

    def __init__(self):
        """Initialize the BatteryManager with default values."""
        self.electricity_prices_df: pd.DataFrame = None
        # Battery settings
        self.battery_scheduling_enabled = False
        self.grid_charge_enabled = False
        self.charge_stop_soc = 0
        self.charging_power_rate = 0
        self.discharging_power_rate = 0
        self.discharge_stop_soc = 0
        # Predicted energy consumption
        self.estimated_energy_consumption_per_hour_kwh = 0
        self.battery_capacity_to_use = 0
        self.hours_of_energy = 0
        self.discharge_rate_hour_kwh = 0

    def fetch_predicted_consumption(self):
        """Fetch the predicted energy consumption."""
        self.estimated_energy_consumption_per_hour_kwh = 4.5
        self.battery_capacity_to_use = float(
            BATTERY_STORAGE_SIZE_KWH * (1 - BATTERY_MIN_SOC / 100)
        )
        self.hours_of_energy = int(
            BATTERY_STORAGE_SIZE_KWH / self.estimated_energy_consumption_per_hour_kwh
        )
        self.discharge_rate_hour_kwh = float(
            self.battery_capacity_to_use / self.hours_of_energy
        )

    def fetch_electricity_prices(self):
        """Update the electricity prices and store them in a pandas DataFrame."""
        # Fetch current electricity price from Nordpool sensor's today attribute
        today_electricity_price = sensor.nordpool_kwh_se4_sek_2_10_025.today  # noqa: F821

        # Create a pandas DataFrame with the electricity prices
        self.electricity_prices_df = pd.DataFrame(
            {
                "Timestamp": range(len(today_electricity_price)),
                "ElectricityPrice": today_electricity_price,
            }
        )

        self.electricity_prices_df["ElectricityPriceBuy"] = (
            self.electricity_prices_df["ElectricityPrice"] + TIBBER_MARKUP_SEK_PER_KWH
        ) * 1.25 + ADDITIONAL_ELECTRICITY_COSTS_SEK_PER_KWH
        self.electricity_prices_df["ElectricityPriceSell"] = (
            self.electricity_prices_df["ElectricityPrice"]
            + TAX_REDUCTION_SOLD_ELECTRICITY
        )

        log.info(  # noqa: F821
            "\n------------------\nElectricity prices\n------------------\n%s",
            self.electricity_prices_df,
        )

    def fetch_battery_settings(self):
        """Update the battery status from the state."""
        self.battery_scheduling_enabled = (
            state.get("input_boolean.battery_scheduling") == "on"  # noqa: F821
        )
        self.grid_charge_enabled = (
            state.get("switch.rkm0d7n04x_charge_from_grid") == "on"  # noqa: F821
        )
        self.charge_stop_soc = int(state.get("number.rkm0d7n04x_charge_stop_soc"))  # noqa: F821
        self.charging_power_rate = int(
            state.get("number.rkm0d7n04x_charging_power_rate")  # noqa: F821
        )
        self.discharging_power_rate = int(
            state.get("number.rkm0d7n04x_discharging_power_rate")  # noqa: F821
        )
        self.discharge_stop_soc = int(state.get("number.rkm0d7n04x_discharge_stop_soc"))  # noqa: F821

    def print_status(self):
        """Print the battery settings and consumption prediction."""
        log.info(  # noqa: F821
            "\n------------------------\n"
            "Battery Settings\n"
            "------------------------\n"
            "Discharge Scheduling Enabled:   %s\n"
            "Charge from Grid:               %s\n"
            "Charge Stop SOC:                %3d%%\n"
            "Charging Power Rate:            %3d%%\n"
            "Discharging Power Rate:         %3d%%\n"
            "Discharge Stop SOC:             %3d%%\n"
            "\n------------------------\n"
            "Consumption Prediction\n"
            "------------------------\n"
            "Estimated Consumption per Hour: %3.1f kWh\n"
            "Battery Capacity to Use:       %3.1f kWh\n"
            "Hours of Energy:                %3d hours\n"
            "Discharge Rate per Hour:        %3.1f kWh\n",
            self.battery_scheduling_enabled,
            self.grid_charge_enabled,
            self.charge_stop_soc,
            self.charging_power_rate,
            self.discharging_power_rate,
            self.discharge_stop_soc,
            self.estimated_energy_consumption_per_hour_kwh,
            self.battery_capacity_to_use,
            self.hours_of_energy,
            self.discharge_rate_hour_kwh,
        )

    def is_arbitrage_profitable(self) -> bool:
        """Determine if arbitrage is profitable."""
        df_res = bess.bess_algorithm_italian(self.electricity_prices_df)
        profit = df_res["Earning"].sum()
        log.info("Earnings for interval: %d SEK", profit)  # noqa: F821
        return profit > 0

    def enable_discharge_schedule(self, enable: bool):
        """Enable or disable discharge scheduling."""
        if enable:
            service.call(  # noqa: F821
                "input_boolean",
                "turn_on",
                entity_id="input_boolean.battery_scheduling",
            )
            self.calculate_discharge_schedule()
        else:
            service.call(  # noqa: F821
                "input_boolean",
                "turn_off",
                entity_id="input_boolean.battery_scheduling",
            )

    def calculate_discharge_schedule(self):
        """Calculate the discharge schedule based on electricity prices."""

        battery_charge_kwh = BATTERY_STORAGE_SIZE_KWH
        battery_soc = 99.0

        battery_charge_kwh_per_hour = [0] * 24
        battery_soc_per_hour = [0] * 24

        # Find the self.hours_of_energy hours with the highest prices
        highest_price_hours = self.electricity_prices_df.nlargest(
            self.hours_of_energy, "ElectricityPrice"
        ).index.tolist()

        schedule_log = []
        for hour in range(24):
            if hour in highest_price_hours:
                battery_charge_kwh -= self.discharge_rate_hour_kwh
                battery_soc = (battery_charge_kwh / BATTERY_STORAGE_SIZE_KWH) * 100

            battery_charge_kwh_per_hour[hour] = battery_charge_kwh
            battery_soc_per_hour[hour] = battery_soc

            schedule_log.append(
                f"Hour: {hour:02d}, Battery Charge Target (kWh): {battery_charge_kwh:5.1f}, Battery SOC Target (%): {battery_soc:5.1f}"
            )

        log.info(  # noqa: F821
            "\n=====================================================\n"
            "Discharge schedule:\n"
            "Highest %s price hours: %s\n"
            "%s\n"
            "=======================================================",
            self.hours_of_energy,
            ", ".join([f"{hour:02d}" for hour in highest_price_hours]),
            "\n".join(schedule_log),
        )

    def update_grid_charge_schedule(self):
        """Update the grid charge schedule based on the current hour."""
        # Fetch current hour
        current_hour = datetime.datetime.now().hour

        # Fetch current grid charge setting
        grid_charge_enabled = state.get("switch.rkm0d7n04x_charge_from_grid") == "on"  # noqa: F821

        # Check if current hour is between 11:00 and 06:00
        if current_hour >= 23 or current_hour < 6:
            if not grid_charge_enabled:
                log.info("Enabling grid charge")  # noqa: F821
                switch.turn_on(entity_id="switch.rkm0d7n04x_charge_from_grid")  # noqa: F821
        elif grid_charge_enabled:
            log.info("Disabling grid charge")  # noqa: F821
            switch.turn_off(entity_id="switch.rkm0d7n04x_charge_from_grid")  # noqa: F821


bm = BatteryManager()


@time_trigger("startup")  # noqa: F821
def run_on_startup():
    """Run automatically on startup or reload."""
    file_save_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.info("BatteryManager initializing, version: %s", file_save_date)  # noqa: F821
    scheduler()


@time_trigger("cron(*/1 * * * *)")  # noqa: F821
def scheduler():
    """Run automatically once on startup or reload and then every 5 minutes."""
    bm.fetch_electricity_prices()
    bm.fetch_battery_settings()
    bm.fetch_predicted_consumption()
    bm.print_status()
    bm.update_grid_charge_schedule()

    if bm.is_arbitrage_profitable():
        bm.enable_discharge_schedule(True)
    else:
        bm.enable_discharge_schedule(False)

    if not bm.battery_scheduling_enabled:
        log.info("Scheduling disabled")  # noqa: F821
        return

    # Fetch current hour
    local_tz = ZoneInfo("Europe/Stockholm")  # Replace with your local timezone
    current_time = datetime.datetime.now(local_tz)
    current_hour = current_time.strftime("%H")

    current_soc = int(state.get("sensor.rkm0d7n04x_state_of_charge_soc"))  # noqa: F821
    current_discharge_stop_soc = int(state.get("number.rkm0d7n04x_discharge_stop_soc"))  # noqa: F821

    target_discharge_stop_soc = int(
        float(state.get(f"input_number.discharge_stop_soc_{current_hour}"))  # noqa: F821
    )

    log.info(  # noqa: F821
        "\nCurrent hour:                    %2d\n"
        "Current SOC:                    %3d%%\n"
        "Discharge Stop SOC:             %3d%%\n"
        "Discharge Target SOC:           %3d%%\n",
        int(current_hour),
        int(current_soc),
        int(current_discharge_stop_soc),
        int(target_discharge_stop_soc),
    )

    if target_discharge_stop_soc != current_discharge_stop_soc:
        log.info("Updating inverter setting:")  # noqa: F821
        target_discharge_stop_soc = min(
            target_discharge_stop_soc, bm.charge_stop_soc - 1
        )
        log.info(
            "Adjusted target discharge stop SOC to %3d%% to be lower than charge stop SOC",
            target_discharge_stop_soc,
        )

        service.call(  # noqa: F821
            "number",
            "set_value",
            entity_id="number.rkm0d7n04x_discharge_stop_soc",
            value=target_discharge_stop_soc,
        )
        log.info(" - discharge_stop_soc       %2d%%", int(target_discharge_stop_soc))  # noqa: F821
    else:
        log.info("Nothing to do, not discharging battery")  # noqa: F821
