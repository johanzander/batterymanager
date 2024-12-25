"""Run the BESS algorithm using Italian parameters and plot the results."""

import datetime

import logging

from modules.bess.bess import BatteryManager, get_growatt_time_schedule

from modules.bess.nordpoolPrices import NordpoolPrices
from modules.bess.utils import plot_multiple_graphs, print_to_terminal, print_to_excel
import pandas as pd

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

def TestPrices():
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range(
                start=datetime.datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),
                periods=len(electricity_prices_2024_08_16),
                freq="h",
            ),
            "ElectricityPrice": electricity_prices_2024_08_16,
        }
    )


if __name__ == "__main__":
#    df_electricity_prices = NordpoolPrices().iloc[0:24]
    df_electricity_prices = TestPrices()

    manager = BatteryManager()
    manager.set_electricity_prices(df_electricity_prices)
    manager.set_prediction_data(estimated_consumption_per_hour_kwh=3.5, max_charging_power_rate=40)
    df_results = manager.calculate_schedule()

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
        "GridCharge"
    ]

    print_to_terminal(df_results, columns_to_print)
    growatt_TOU_settings = get_growatt_time_schedule(df_results)
    print_to_terminal(growatt_TOU_settings, columns_to_print)
    
    if not df_results["State"].eq("standby").all():
        print(f"Arbitrage profitable, calculating discharge schedule.")
    else:
        print("Arbitrage not profitable, no discharge schedule calculated")

    exit()
    
    df_results.set_index("Timestamp", inplace=True)
    df_results["Date"] = df_results.index.date
    grouped = df_results.groupby("Date")

    daily_dfs = []
    titles = []
    for date, daily_df in df_results.resample("D"):
        if not daily_df.empty:
            date_str = str(date.date())
            logging.info("Processing data for %s", date_str)
            print_to_terminal(daily_df, columns_to_print)
            print_to_excel(daily_df, columns_to_print, date_str)
            daily_dfs.append(daily_df)
            titles.append(str(date.date()))
#            plot_multiple_graphs(daily_dfs, titles, nrows=1, ncols=1, filename=date_str)


