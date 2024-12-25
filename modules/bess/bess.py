import logging

import numpy as np
import pandas as pd

# from modules.bess.utils import print_to_terminal
from .constants import (
    ADDITIONAL_ELECTRICITY_COSTS_SEK_PER_KWH,
    BATTERY_CHARGE_CYCLE_COST_SEK,
    BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW,
    BATTERY_MIN_SOC,
    BATTERY_STORAGE_SIZE_KWH,
    MINIMUM_PROFIT_PER_CYCLE,
    TAX_REDUCTION_SOLD_ELECTRICITY,
    TIBBER_MARKUP_SEK_PER_KWH,
)


class BatteryManager:
    """A class for managing a Battery Energy Storage System."""

    def __init__(self):
        """Initialize the BatteryManager with default values."""
        self.df = None
        self.charge_rate_hour_kwh = 0
        self.discharge_rate_hour_kwh = 0

    def set_electricity_prices(self, df: pd.DataFrame):
        """Set the electricity prices and initialize related data in the DataFrame."""
        self.df = df
        # Initialize electricity prices
        self.df["ElectricityPrice"] = df["ElectricityPrice"]
        self.df["ElectricityPriceBuy"] = (
            df["ElectricityPrice"] + TIBBER_MARKUP_SEK_PER_KWH
        ) * 1.25 + ADDITIONAL_ELECTRICITY_COSTS_SEK_PER_KWH
        self.df["ElectricityPriceSell"] = (
            df["ElectricityPrice"] + TAX_REDUCTION_SOLD_ELECTRICITY
        )
        self.electricity_price_nordpool = self.df["ElectricityPrice"].values
        self.electricity_price_buy = self.df["ElectricityPriceBuy"].values
        self.electricity_price_sell = self.df["ElectricityPriceSell"].values

        # Initialize arrays to store charge/discharge actions and Battery SOE
        self.df["Battery SOE"] = np.zeros(len(df))
        self.df["Charge"] = np.zeros(len(df))
        self.df["Discharge"] = np.zeros(len(df))
        self.df["Profitable"] = np.zeros(len(df))
        self.df["Earning"] = np.zeros(len(df))
        self.df["State"] = ["standby"] * len(df)

        self.df.reset_index(inplace=True)

    def charge_battery(self, hour: int, requested_charge_kwh: float) -> float:
        """Charge the battery at the specified hour."""
        actual_charge_kwh = min(
            requested_charge_kwh,
            BATTERY_STORAGE_SIZE_KWH - self.df.at[hour, "Battery SOE"],
        )
        logging.info(
            "charge_battery    hour %02d: SOE: %.1f kW, %.1f kW",
            hour,
            self.df.at[hour, "Battery SOE"],
            actual_charge_kwh,
        )
        if actual_charge_kwh > 0:
            self.df.at[hour, "State"] = "charging"
            self.df.at[hour, "Charge"] += actual_charge_kwh
            for h in range(hour, len(self.df)):
                self.df.at[h, "Battery SOE"] += actual_charge_kwh
        else:
            logging.warning("Battery full, cannot charge more")
        return actual_charge_kwh

    def discharge_battery(self, hour: int, requested_discharge_kwh: float) -> float:
        """Discharge the battery at the specified hour."""
        actual_discharge_kwh = min(
            requested_discharge_kwh, self.df.at[hour, "Battery SOE"]
        )
        #        actual_discharge_kwh = max(actual_discharge_kwh, self.battery_min_capacity_kwh)
        if actual_discharge_kwh > 0:
            logging.info(
                "discharge_battery hour %02d: SOE: %0.1f kW, %0.1f kW",
                hour,
                self.df.at[hour, "Battery SOE"],
                actual_discharge_kwh,
            )
            self.df.at[hour, "State"] = "discharging"
            self.df.at[hour, "Discharge"] -= actual_discharge_kwh
            for h in range(hour, len(self.df)):
                self.df.at[h, "Battery SOE"] -= actual_discharge_kwh
        else:
            logging.warning("No energy in battery to discharge")
        return actual_discharge_kwh

    def interval_profit_self_consumption(self, min_index: int, max_index: int):
        """Check if the interval is profitable for self consumption."""
        return (
            self.electricity_price_buy[max_index]
            - self.electricity_price_buy[min_index]
            - BATTERY_CHARGE_CYCLE_COST_SEK
        )

    def set_prediction_data(
        self,
        estimated_consumption_per_hour_kwh: float,
        max_charging_power_rate: float,
    ):
        """Set the prediction data for the battery manager."""
        self.estimated_energy_consumption_per_hour_kwh = (
            estimated_consumption_per_hour_kwh
        )
        self.battery_capacity_to_use_kwh = float(
            BATTERY_STORAGE_SIZE_KWH * (1 - BATTERY_MIN_SOC / 100)
        )
        self.battery_min_capacity_kwh = float(
            BATTERY_STORAGE_SIZE_KWH - self.battery_capacity_to_use_kwh
        )
        self.hours_of_energy = float(
            self.battery_capacity_to_use_kwh
            / self.estimated_energy_consumption_per_hour_kwh
        )
        self.discharge_rate_hour_kwh = float(
            self.battery_capacity_to_use_kwh / self.hours_of_energy
        )
        self.charging_power_rate = max_charging_power_rate
        self.charging_power_kw = float(
            self.charging_power_rate * BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW / 100
        )
        self.hours_to_full_charge = float(
            self.battery_capacity_to_use_kwh / self.charging_power_kw
        )
        self.charge_rate_hour_kwh = self.charging_power_kw
        logging.info(
            "\n=============================================== \n"
            "         Consumption prediction set \n"
            "=============================================== \n"
            " estimated_energy_consumption_per_hour_kwh=%4.1f\n"
            " battery_capacity_kwh =                    %4.1f\n"
            " battery_capacity_to_use_kwh =             %4.1f\n"
            " battery_min_capacity_kwh =                %4.1f\n"
            " charging_power_rate =                    %4d%%\n"
            " charging_power_kw =                       %4.1f\n"
            " hours_to_full_charge =                    %4.1f\n"
            " hours_of_energy =                         %4.1f\n"
            " discharge_rate_hour_kwh =                 %4.1f\n",
            self.estimated_energy_consumption_per_hour_kwh,
            BATTERY_STORAGE_SIZE_KWH,
            self.battery_capacity_to_use_kwh,
            self.battery_min_capacity_kwh,
            self.charging_power_rate,
            self.charging_power_kw,
            self.hours_to_full_charge,
            self.hours_of_energy,
            self.discharge_rate_hour_kwh,
        )

    def calculate_schedule(self) -> pd.DataFrame:
        """Calculate the schedule for charging and discharging the battery."""
        hours_sorted = (
            self.df["ElectricityPrice"].sort_values(ascending=True).index.tolist()
        )
        low_index = 0
        high_index = len(hours_sorted) - 1

        logging.debug("\nLowest price hours: %s\n", hours_sorted)
        while low_index < high_index:
            low_price_hour = hours_sorted[low_index]
            high_price_hour = hours_sorted[high_index]
            low_price = self.df.at[low_price_hour, "ElectricityPrice"]
            high_price = self.df.at[high_price_hour, "ElectricityPrice"]
            price_diff = high_price - low_price - BATTERY_CHARGE_CYCLE_COST_SEK
            if price_diff < 0:
                logging.debug(
                    "Not profitable: Low price hour %02d: %.1f, High price hour %02d: %.1f, Price diff: %.2f",
                    low_price_hour,
                    low_price,
                    high_price_hour,
                    high_price,
                    price_diff,
                )
                break
            logging.debug(
                "Low price hour %02d: %.1f, High price hour %02d: %.1f, Price diff: %.2f",
                low_price_hour,
                low_price,
                high_price_hour,
                high_price,
                price_diff,
            )
            # Try to charge the battery for max charge at the lowest price hour
            actual_charge = self.charge_battery(
                low_price_hour, self.charge_rate_hour_kwh
            )
            # Try to discharge the battery for max discharge at the highest price hour
            to_be_discharged = actual_charge
            while to_be_discharged > 0:
                requested_discharge = min(
                    self.estimated_energy_consumption_per_hour_kwh, to_be_discharged
                )
                to_be_discharged -= self.discharge_battery(
                    high_price_hour, requested_discharge
                )
                logging.debug(
                    "Discharge %.1f kWh, remaining to be discharged %.1f kWh",
                    requested_discharge,
                    to_be_discharged,
                )
                logging.debug("Remaining to be discharged: %.1f kWh", to_be_discharged)
                if to_be_discharged > 0:
                    # could not discharge the full amount, find the next highest price hour
                    high_index -= 1
                    high_price_hour = hours_sorted[high_index]

            low_index += 1
            high_index -= 1

        for hour in range(len(self.df)):
            self.df.at[hour, "StartTime"] = f"{hour:02d}:00"
            self.df.at[hour, "EndTime"] = f"{hour:02d}:59"
            battery_discharge_rate = abs(
                float(self.df.at[hour, "Discharge"])
                / BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW
                * 100
            )
            self.df.at[hour, "Discharge Power Rate"] = battery_discharge_rate
            self.df.at[hour, "GridCharge"] = self.df.at[hour, "State"] == "charging"

        return self.df


def get_growatt_time_schedule(df: pd.DataFrame):
    """Return a schedule that can be used with Growatts TOU settings."""
    intervals = []
    current_interval = None

    for i, row in df.iterrows():
        if current_interval is None:
            current_interval = {
                "StartTime": row["StartTime"],
                "State": row["State"],
                "GridCharge": row["State"] == "charging",
                "GrowattState": "load-first"
                if row["State"] == "discharging"
                else "battery-first",
            }
        elif row["State"] != current_interval["State"]:
            current_interval["EndTime"] = df.iloc[i - 1]["EndTime"]
            intervals.append(current_interval)
            current_interval = {
                "StartTime": row["StartTime"],
                "State": row["State"],
                "GridCharge": row["State"] == "charging",
                "GrowattState": "load-first"
                if row["State"] == "discharging"
                else "battery-first",
            }

    if current_interval is not None:
        current_interval["EndTime"] = df.iloc[-1]["EndTime"]
        intervals.append(current_interval)

    return pd.DataFrame(
        intervals,
        columns=["StartTime", "EndTime", "State", "GridCharge", "GrowattState"],
    )
