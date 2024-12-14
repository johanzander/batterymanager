"""Run the BESS algorithm using Italian parameters and plot the results."""

import logging

import logging

from modules.bess.nordpoolPrices import NordpoolPrices
from modules.bess.algorithms import bess_algorithm_italian
from modules.bess.constants import (
    ADDITIONAL_ELECTRICITY_COSTS_SEK_PER_KWH,
    TAX_REDUCTION_SOLD_ELECTRICITY,
    TIBBER_MARKUP_SEK_PER_KWH,
)
from modules.bess.utils import plot_multiple_graphs, print_to_terminal, print_to_excel


if __name__ == "__main__":
    df_electricity_prices = NordpoolPrices()
    df_electricity_prices["ElectricityPriceBuy"] = (
        df_electricity_prices["ElectricityPrice"] + TIBBER_MARKUP_SEK_PER_KWH
    ) * 1.25 + ADDITIONAL_ELECTRICITY_COSTS_SEK_PER_KWH
    df_electricity_prices["ElectricityPriceSell"] = (
        df_electricity_prices["ElectricityPrice"] + TAX_REDUCTION_SOLD_ELECTRICITY
    )

    df_results = bess_algorithm_italian(df_electricity_prices)

    # 'ElectricityPriceBuy', 'ElectricityPriceSell', 'MinMax', 'Electricity Bought',  'Electricity Sold', 'EstimatedEnergyUsage',
    columns_to_print = [
        "ElectricityPrice",
        "ElectricityPriceBuy",
        "State",
        "Battery State of Charge",
        "Earning",
    ]

    df_electricity_prices["Date"] = df_electricity_prices.index.date
    grouped = df_electricity_prices.groupby("Date")

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
            plot_multiple_graphs(daily_dfs, titles, nrows=1, ncols=1, filename=date_str)

    
