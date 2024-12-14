"""Module containing an algorithm for optimizing battery storage operations."""

import logging

import numpy as np
import pandas as pd

from .constants import (
    BATTERY_CHARGE_CYCLE_COST_SEK,
    BATTERY_STORAGE_SIZE_KWH,
    MAX_CHARGE_DISCHARGE_RATE_KW,
    MINIMUM_PROFIT_PER_CYCLE,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configure logging
log = logging.getLogger(__name__)


def bess_algorithm_italian(df: pd.DataFrame) -> pd.DataFrame:
    # This algorithm is based on the research paper: A Novel Operating Strategy for Customer-Side Energy
    # Storages in Presence of Dynamic Electricity Prices. Step 1-4 is more or less straight from the paper,
    # while we add a 5th step to find a secondary low/high pair for each cycle since we cannot charge /
    # discharge the full battery in one hour. Since we know max discharge / charge rate is 15kw and battery
    # capacity is 30kWh, we look only for one additional charge/discharge hour per cycle. A generic
    # implementation would need to calculate the number of hours to charge/discharge depending on parameterized
    # battery capacity.

    # Stage 1: This is a preliminary stage, in which the input data are provided.
    # In this stage the min/max values are derived.

    logging.info(" KUKEN() ")

    # Initialize electricity prices
    electricity_price_nordpool = df["ElectricityPrice"].values
    electricity_price_buy = df["ElectricityPriceBuy"].values
    electricity_price_sell = df["ElectricityPriceSell"].values

    # Initialize arrays to store charge/discharge actions and battery state of charge
    df["Battery State of Charge"] = np.zeros(len(df))
    df["Electricity Bought"] = np.zeros(len(df))
    df["Electricity Sold"] = np.zeros(len(df))
    df["Earning"] = np.zeros(len(df))
    df["State"] = ["standby"] * len(df)

    df.reset_index(inplace=True)

    def find_mins_and_max_indexes():
        """Find local minima and maxima indexes in the electricity price data."""
        local_minima = []
        local_maxima = []
        increasing = None  # None means we haven't determined the trend yet
        potential_max_index = None
        potential_min_index = None

        for i in range(1, len(electricity_price_nordpool)):
            if electricity_price_nordpool[i] > electricity_price_nordpool[i - 1]:
                if increasing is False:  # Was decreasing, now increasing
                    local_minima.append(
                        potential_min_index
                        if potential_min_index is not None
                        else i - 1
                    )
                    logging.info(
                        "Found local minima at index %s",
                        potential_min_index
                        if potential_min_index is not None
                        else i - 1,
                    )
                    potential_min_index = None
                increasing = True
                potential_max_index = None
            elif electricity_price_nordpool[i] < electricity_price_nordpool[i - 1]:
                if increasing is True:  # Was increasing, now decreasing
                    local_maxima.append(
                        potential_max_index
                        if potential_max_index is not None
                        else i - 1
                    )
                    logging.info(
                        "Found local maxima at index %s",
                        potential_max_index
                        if potential_max_index is not None
                        else i - 1,
                    )
                    potential_max_index = None
                increasing = False
                potential_min_index = None
            else:  # electricity_price_nordpool[i] == electricity_price_nordpool[i - 1]
                if increasing is True:
                    potential_max_index = (
                        i - 1 if potential_max_index is None else potential_max_index
                    )
                elif increasing is False:
                    potential_min_index = (
                        i - 1 if potential_min_index is None else potential_min_index
                    )

        # Handle edge cases for the first and last elements
        if electricity_price_nordpool[0] < electricity_price_nordpool[1]:
            local_minima.insert(0, 0)
            logging.info("Found local minima at index 0")
        elif electricity_price_nordpool[0] > electricity_price_nordpool[1]:
            local_maxima.insert(0, 0)
            logging.info("Found local maxima at index 0")

        if electricity_price_nordpool[-1] < electricity_price_nordpool[-2]:
            local_minima.append(len(electricity_price_nordpool) - 1)
            logging.info("Found local minima at the last index")
        elif electricity_price_nordpool[-1] > electricity_price_nordpool[-2]:
            local_maxima.append(len(electricity_price_nordpool) - 1)
            logging.info("Found local maxima at the last index")

        # Ensure the series starts with a minima and ends with a maxima
        if local_maxima and local_minima and local_maxima[0] < local_minima[0]:
            logging.info("Series starts with a max, removing %s", local_maxima[0])
            local_maxima = local_maxima[1:]

        if local_minima and local_maxima and local_minima[-1] > local_maxima[-1]:
            logging.info("Series ends with a min, removing %s", local_minima[-1])
            local_minima = local_minima[:-1]

        return local_minima, local_maxima

    def charge_battery(hour: int) -> None:
        """Charge the battery at the specified hour."""
        charge_amount = min(
            MAX_CHARGE_DISCHARGE_RATE_KW,
            BATTERY_STORAGE_SIZE_KWH - df.at[hour, "Battery State of Charge"],
        )
        if charge_amount > 0:
            charge_amount = min(
                MAX_CHARGE_DISCHARGE_RATE_KW,
                BATTERY_STORAGE_SIZE_KWH - df.at[hour, "Battery State of Charge"],
            )
            df.at[hour, "Electricity Bought"] = charge_amount
            df.loc[hour:, "Battery State of Charge"] += charge_amount
            df.at[hour, "Earning"] = -charge_amount * df.at[hour, "ElectricityPriceBuy"]
            df.at[hour, "State"] = "charging"
        else:
            logging.warning("Battery full, cannot charge more")

    def discharge_battery(hour: int) -> None:
        """Discharge the battery at the specified hour."""
        discharge_amount = min(
            MAX_CHARGE_DISCHARGE_RATE_KW, df.at[hour, "Battery State of Charge"]
        )
        if discharge_amount > 0:
            df.at[hour, "Electricity Sold"] = discharge_amount
            df.loc[hour:, "Battery State of Charge"] -= discharge_amount
            battery_wear_costs = discharge_amount * BATTERY_CHARGE_CYCLE_COST_SEK
            df.at[hour, "Earning"] = (
                discharge_amount * df.at[hour, "ElectricityPriceSell"]
                - battery_wear_costs
            )
            df.at[hour, "State"] = "discharging"
        else:
            logging.warning("No energy in battery to discharge")

    def interval_is_profitable(min_index: int, max_index: int):
        """Check if the interval between min_index and max_index is profitable."""
        profit = (
            electricity_price_sell[max_index]
            - electricity_price_buy[min_index]
            - BATTERY_CHARGE_CYCLE_COST_SEK
        )
        profitable = profit > MINIMUM_PROFIT_PER_CYCLE
        logging.info(
            "Interval [%s:%s], profit: %.2f SEK/kWh, profitable: %s",
            min_index,
            max_index,
            profit,
            profitable,
        )
        return profitable

    # Stage 2: In this stage, the algorithm inspects the consecutive min/max value pairs one at a time.
    # If the min/max interval is profitable (condition 7), the state is set to 'active' and the algorithm
    # continues to inspect the next min/max value pair. Thus, it iterates over all min/max pairs as long as
    # they are profitable. If the min/max interval is NOT profitable, the state is set to 'potential' and
    # the algorithm continues to stage 3.

    # Stage 3: This stage is activated only if condition (7) is not satisfied.
    # Here the algorithm checks all the possible couples of min/max values that remain in 'potential' state,
    # identifying the couple whose gap is maximum. When the maximum gap has been identified, the algorithm
    # checks if the interval is profitable (condition 7). If profitable, it sets the state to active,
    # then moving to the next pair of consecutive min/max values (restarting from step 2)
    # If (7) is not satisfied, the corresponding timeslots retain the state of potential and the algorithm
    # moves to the next pair of min/max RTP values, switching their status to potential (restarting from step 3).
    # The procedure ends when the last couple of min/max RTP values is counted (i=24 i.e. k = N and j = M).

    min_indexes, max_indexes = find_mins_and_max_indexes()
    stage = 2

    df["MinMax"] = ""
    df.loc[min_indexes, "MinMax"] = "min"
    df.loc[max_indexes, "MinMax"] = "max"

    logging.debug("Min Indexes: %s", min_indexes)
    logging.debug("Max Indexes: %s", max_indexes)

    min_index = None
    max_index = None
    potential_intervals = []

    # Iterate over every min/max pair
    for index in range(len(min_indexes)):
        if stage == 2:
            logging.info(" ---- Stage 2 ---- ")

            min_index = min_indexes[index]
            max_index = max_indexes[index]

            if interval_is_profitable(min_index, max_index):
                charge_battery(min_index)
                discharge_battery(max_index)
            else:
                df.at[min_index, "State"] = "potential"
                df.at[max_index, "State"] = "potential"
                potential_intervals.append((min_index, max_index))
                stage = 3

        elif stage == 3:
            logging.info(" ---- Stage 3 ---- ")

            potential_intervals.append((min_indexes[index], max_indexes[index]))

            # Find the couple with the maximum gap
            min_price = float("inf")
            max_price = float("-inf")
            for interval in potential_intervals:
                min_index, max_index = interval

                # Find the minimum price within the potential interval
                min_price = min(electricity_price_buy[min_index], min_price)

                # Find the maximum price within the potential interval
                if (
                    electricity_price_sell[max_index] > max_price
                    and min_index < max_index
                ):
                    max_price = electricity_price_sell[max_index]

            # If both minimum and maximum prices are found, check if the interval matches
            if min_price != float("inf") and max_price != float("-inf"):
                # If the interval matches the minimum and maximum prices, set the state to charging and discharging
                if interval_is_profitable(min_index, max_index):
                    charge_battery(min_index)
                    discharge_battery(max_index)
                    potential_intervals.remove(interval)
                    stage = 2
                else:
                    df.at[min_index, "State"] = "potential"
                    df.at[max_index, "State"] = "potential"

    # Stage 4: For all local min, Set the state to charging. For all local max, set the state to discharging.
    # For each charge/discharge interval, find the second cheapest hour, the second highest hour, check if they are
    # profitable. If yes, set their state to charging, discharging as well, otherwise do nothing.
    # Do this for all charge/discharge intervals. The next cheapest min should be between the max intervals and the
    # next highest max should be between the min intervals.

    logging.debug(" --- Stage 4 --- ")
    # Find the second cheapest hour within each charge cycle, i.e. between two max indexes
    # Except first time, where first max index should be 0

    second_cheapest_hours, second_highest_hours = [], []

    for index in range(len(max_indexes)):
        second_min_index = 0
        if index == 0:
            max_index_1 = 0
        else:
            max_index_1 = max_indexes[index - 1]
        max_index_2 = max_indexes[index]

        # Find the second cheapest hour between max_index_1 and max_index_2
        interval_prices = electricity_price_buy[max_index_1:max_index_2]
        if len(interval_prices) > 1:
            sorted_indices = np.argsort(interval_prices)
            second_min_index = max_index_1 + sorted_indices[1]
            second_cheapest_hours.append(second_min_index)
            logging.debug(
                "   Second lowest index between max interval [%s : %s]: %s",
                max_index_1,
                max_index_2,
                second_min_index,
            )

    # Find the second highest hour within each discharge cycle
    for index in range(len(min_indexes)):
        second_max_index = 0
        min_index_1 = min_indexes[index]
        if index + 1 < len(min_indexes):
            min_index_2 = min_indexes[index + 1]
        else:
            min_index_2 = len(electricity_price_sell) - 1

        # Find the second highest hour between min_index_1 and min_index_2
        interval_prices = electricity_price_sell[min_index_1:min_index_2]
        if len(interval_prices) > 1:
            sorted_indices = np.argsort(interval_prices)[::-1]
            indx = 1
            if len(sorted_indices) > 2:
                while (
                    electricity_price_sell[sorted_indices[1]]
                    == electricity_price_sell[sorted_indices[indx + 1]]
                ):
                    indx = indx + 1
            second_max_index = min_index_1 + sorted_indices[indx]
            second_highest_hours.append(second_max_index)
            logging.debug(
                "   Second highest index between min interval [%s : %s]: %s",
                min_index_1,
                min_index_2,
                second_max_index,
            )

    # Iterate over the content and call charge_battery(cheap) and discharge_battery(high)
    for cheap_hour, expensive_hour in zip(second_cheapest_hours, second_highest_hours):
        if interval_is_profitable(cheap_hour, expensive_hour):
            charge_battery(cheap_hour)
            discharge_battery(expensive_hour)

    df.set_index("Timestamp", inplace=True)
    return df
