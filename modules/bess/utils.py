# import logging
from typing import List

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from .constants import BATTERY_CHARGE_CYCLE_COST_SEK

def plot_multiple_graphs(
    dfs: List[pd.DataFrame], titles: List[str], nrows: int, ncols: int, filename: str
) -> None:
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(15, 10))

    if nrows == 1 and ncols == 1:
        axes = [axes]  # Convert single Axes object to a list
    else:
        axes = axes.flatten()  # Flatten the 2D array of axes for easy iteration

    for i, (df, title) in enumerate(zip(dfs, titles)):
        if i >= len(axes):
            break  # Prevent accessing out of bounds index

        ax = axes[i]
        minmax = df.copy()
        minmax.reset_index(inplace=True)
        min_indexes = minmax[minmax["MinMax"] == "min"].index.tolist()
        max_indexes = minmax[minmax["MinMax"] == "max"].index.tolist()

        ax.step(
            df.index,
            df["ElectricityPrice"],
            label="Electricity Price (Nordpool)",
            color="blue",
            zorder=1,
            where="post",
        )
        ax.step(
            df.index,
            df["ElectricityPriceBuy"],
            label="Electricity Price (Buy)",
            color="red",
            zorder=1,
            where="post",
            linestyle=":",
        )
        ax.scatter(
            df.index[min_indexes],
            df["ElectricityPrice"].iloc[min_indexes],
            color="green",
            label="Min Price (Nordpool)",
            zorder=2,
        )
        ax.scatter(
            df.index[max_indexes],
            df["ElectricityPrice"].iloc[max_indexes],
            color="red",
            label="Max Price (Nordpool)",
            zorder=2,
        )

        profit = df["Earning"].sum().round(2)

        charge_label = 0
        discharge_label = 0

        for j in range(len(df["State"])):
            if df["State"].iloc[j] == "charging":
                if charge_label == 0:
                    ax.fill_between(
                        df.index[j : j + 2],
                        df["ElectricityPriceBuy"].iloc[j],
                        df["ElectricityPriceBuy"].iloc[j]
                        + BATTERY_CHARGE_CYCLE_COST_SEK,
                        label="Battery Charge Cycle Cost",
                        color="grey",
                        alpha=0.3,
                        zorder=0,
                    )
                    ax.fill_between(
                        df.index[j : j + 2],
                        0,
                        df["ElectricityPriceBuy"].iloc[j],
                        label="Charging (Buy Price)",
                        color="red",
                        alpha=0.3,
                        zorder=0,
                    )
                    charge_label = 1
                else:
                    ax.fill_between(
                        df.index[j : j + 2],
                        df["ElectricityPriceBuy"].iloc[j],
                        df["ElectricityPriceBuy"].iloc[j]
                        + BATTERY_CHARGE_CYCLE_COST_SEK,
                        color="grey",
                        alpha=0.3,
                        zorder=0,
                    )
                    ax.fill_between(
                        df.index[j : j + 2],
                        0,
                        df["ElectricityPriceBuy"].iloc[j],
                        color="red",
                        alpha=0.3,
                        zorder=0,
                    )
            elif df["State"].iloc[j] == "discharging":
                if discharge_label == 0:
                    ax.fill_between(
                        df.index[j : j + 2],
                        0,
                        df["ElectricityPriceBuy"].iloc[j],
                        label="Discharging (Buy Price)",
                        color="green",
                        alpha=0.3,
                        zorder=0,
                    )
                    discharge_label = 1
                else:
                    ax.fill_between(
                        df.index[j : j + 2],
                        0,
                        df["ElectricityPriceBuy"].iloc[j],
                        color="green",
                        alpha=0.3,
                        zorder=0,
                    )

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H"))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.grid(which="both", axis="x", linestyle="--", linewidth=0.5)

        ax.set_xlabel("Time")
        ax.set_ylabel("Electricity Price (SEK / kWh)")
        ax.legend()

    #        ax.set_title(
    #            f"{title}, Profit: {profit} SEK",
    #            bbox=dict(facecolor="yellow", alpha=0.5),
    #           pad=10,
    #      )

    plt.tight_layout()
    plt.savefig(f"{filename}.svg", format="svg")
    plt.show()
    plt.close(fig)


def plot_multiple_graphs_old(
    dfs: List[pd.DataFrame], titles: List[str], nrows: int, ncols: int, filename: str
) -> None:
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(15, 10))

    if nrows == 1 and ncols == 1:
        axes = [axes]  # Convert single Axes object to a list
    else:
        axes = axes.flatten()  # Flatten the 2D array of axes for easy iteration

    for i, (df, title) in enumerate(zip(dfs, titles)):
        if i >= len(axes):
            break  # Prevent accessing out of bounds index

        ax = axes[i]
        minmax = df.copy()
        minmax.reset_index(inplace=True)
        min_indexes = minmax[minmax["MinMax"] == "min"].index.tolist()
        max_indexes = minmax[minmax["MinMax"] == "max"].index.tolist()

        ax.step(
            df.index,
            df["ElectricityPrice"],
            label="Electricity Price (Nordpool)",
            color="blue",
            zorder=1,
            where="post",
        )
        ax.step(
            df.index,
            df["ElectricityPriceBuy"],
            label="Electricity Price (Buy)",
            color="red",
            zorder=1,
            where="post",
            linestyle=":",
        )
        ax.step(
            df.index,
            df["ElectricityPriceSell"],
            label="Electricity Price (Sell)",
            color="green",
            zorder=1,
            where="post",
            linestyle=":",
        )
        ax.scatter(
            df.index[min_indexes],
            df["ElectricityPrice"].iloc[min_indexes],
            color="green",
            label="Min Price (Nordpool)",
            zorder=2,
        )
        ax.scatter(
            df.index[max_indexes],
            df["ElectricityPrice"].iloc[max_indexes],
            color="red",
            label="Max Price (Nordpool)",
            zorder=2,
        )

        profit = df["Earning"].sum().round(2)

        charge_label = 0
        discharge_label = 0

        for j in range(len(df["State"])):
            if df["State"].iloc[j] == "charging":
                if charge_label == 0:
                    ax.fill_between(
                        df.index[j : j + 2],
                        df["ElectricityPriceBuy"].iloc[j],
                        df["ElectricityPriceBuy"].iloc[j]
                        + BATTERY_CHARGE_CYCLE_COST_SEK,
                        label="Battery Charge Cycle Cost",
                        color="grey",
                        alpha=0.3,
                        zorder=0,
                    )
                    ax.fill_between(
                        df.index[j : j + 2],
                        0,
                        df["ElectricityPriceBuy"].iloc[j],
                        label="Charging (Buy Price)",
                        color="red",
                        alpha=0.3,
                        zorder=0,
                    )
                    charge_label = 1
                else:
                    ax.fill_between(
                        df.index[j : j + 2],
                        df["ElectricityPriceBuy"].iloc[j],
                        df["ElectricityPriceBuy"].iloc[j]
                        + BATTERY_CHARGE_CYCLE_COST_SEK,
                        color="grey",
                        alpha=0.3,
                        zorder=0,
                    )
                    ax.fill_between(
                        df.index[j : j + 2],
                        0,
                        df["ElectricityPriceBuy"].iloc[j],
                        color="red",
                        alpha=0.3,
                        zorder=0,
                    )
            elif df["State"].iloc[j] == "discharging":
                if discharge_label == 0:
                    ax.fill_between(
                        df.index[j : j + 2],
                        0,
                        df["ElectricityPriceSell"].iloc[j],
                        label="Discharging (Sell Price)",
                        color="green",
                        alpha=0.3,
                        zorder=0,
                    )
                    discharge_label = 1
                else:
                    ax.fill_between(
                        df.index[j : j + 2],
                        0,
                        df["ElectricityPriceSell"].iloc[j],
                        color="green",
                        alpha=0.3,
                        zorder=0,
                    )

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H"))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.grid(which="both", axis="x", linestyle="--", linewidth=0.5)

        ax.set_xlabel("Time")
        ax.set_ylabel("Electricity Price (SEK / kWh)")
        ax.legend()

        ax.set_title(
            f"{title}, Profit: {profit} SEK",
            bbox=dict(facecolor="yellow", alpha=0.5),
            pad=10,
        )

    plt.tight_layout()
    plt.savefig(f"{filename}.svg", format="svg")
    plt.show()
    plt.close(fig)


def get_histogram_of_daily_spreads(df_electricity_price):
    # Ensure the index is a datetime index
    df_electricity_price.index = pd.to_datetime(df_electricity_price.index)

    # Get the start and end date times from the index range
    start_date = df_electricity_price.index.min().strftime("%Y-%m-%d")
    end_date = df_electricity_price.index.max().strftime("%Y-%m-%d")

    # Dictionary to store the counts of price spreads
    price_spread_counts = {}

    # Loop through each day
    for day, group in df_electricity_price.groupby(df_electricity_price.index.date):
        # Calculate the price spread for the day
        price_spread = group["ElectricityPrice"].max() - group["ElectricityPrice"].min()
        price_spread = round(price_spread / 0.25) * 0.25  # Round to nearest 0.25 SEK

        # Update the counts in the dictionary
        if price_spread in price_spread_counts:
            price_spread_counts[price_spread] += 1
        else:
            price_spread_counts[price_spread] = 1

    # Convert the dictionary to a DataFrame
    df_price_spread_counts = pd.DataFrame(
        list(price_spread_counts.items()),
        columns=["Price Spread (SEK)", "Number of Days"],
    )

    # Plot the histogram
    plt.figure(figsize=(10, 6))
    bars = plt.bar(
        df_price_spread_counts["Price Spread (SEK)"],
        df_price_spread_counts["Number of Days"],
        width=0.2,
        edgecolor="black",
        alpha=0.7,
    )

    # Color bars with x values larger than 2 in green and add a label
    for bar in bars:
        if bar.get_x() + bar.get_width() / 2 > 2:
            bar.set_color("green")
            bar.set_label("Profitable")
        else:
            bar.set_color("blue")
            bar.set_label("Non-profitable")

    # Add the title and labels
    plt.title(
        f"Number of Days with Each Price Spread between {start_date} and {end_date}"
    )
    plt.xlabel("Price Spread (SEK)")
    plt.ylabel("Number of Days")
    plt.grid(True)

    # Add legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())

    # Show the plot
    plt.savefig("daily.png")
    plt.show()

    # Print and return the DataFrame
    print(df_price_spread_counts)
    return df_price_spread_counts


# Function to get daily max spreads
def get_daily_max_spreads(df_electricity_price):
    # List to store the results
    daily_spreads = []

    # Loop through each day
    for day, group in df_electricity_price.groupby(df_electricity_price.index.date):
        # Calculate the price spread for the day
        price_spread = group["ElectricityPrice"].max() - group["ElectricityPrice"].min()

        # Append the result to the list
        daily_spreads.append({"Date": day, "Max Spread (SEK)": price_spread})

    # Convert the list to a DataFrame
    df_daily_spreads = pd.DataFrame(daily_spreads)

    # Set the 'Date' column as the index
    df_daily_spreads.set_index("Date", inplace=True)

    # Print and return the DataFrame
    print("Spreads: ")
    print(df_daily_spreads)
    return df_daily_spreads


def get_histogram_of_monthly_spreads(df_electricity_price):
    # Ensure the index is a datetime index
    df_electricity_price.index = pd.to_datetime(df_electricity_price.index)

    # Dictionary to store the counts of price spreads for each month
    monthly_price_spread_counts = {}
    max_spread = 0  # Variable to track the maximum price spread
    max_days = 0  # Variable to track the maximum number of days

    # Loop through each month
    for month, group in df_electricity_price.groupby(
        df_electricity_price.index.to_period("M")
    ):
        # Dictionary to store the counts of price spreads for the current month
        price_spread_counts = {}

        # Loop through each day in the current month
        for day, day_group in group.groupby(group.index.date):
            # Calculate the price spread for the day
            price_spread = (
                day_group["ElectricityPrice"].max()
                - day_group["ElectricityPrice"].min()
            )
            price_spread = (
                round(price_spread / 0.25) * 0.25
            )  # Round to nearest 0.25 SEK

            # Update the counts in the dictionary
            if price_spread in price_spread_counts:
                price_spread_counts[price_spread] += 1
            else:
                price_spread_counts[price_spread] = 1

            # Update the maximum price spread
            max_spread = max(price_spread, max_spread)

        # Update the maximum number of days
        max_days = max(max_days, *(price_spread_counts.values()))

        # Store the counts for the current month
        monthly_price_spread_counts[month] = price_spread_counts

    # Plot the histograms for each month
    plt.figure(figsize=(15, 10))
    for i, (month, price_spread_counts) in enumerate(
        monthly_price_spread_counts.items(), 1
    ):
        df_price_spread_counts = pd.DataFrame(
            list(price_spread_counts.items()),
            columns=["Price Spread (SEK)", "Number of Days"],
        )

        plt.subplot(3, 4, i)  # Adjust the subplot grid as needed
        colors = [
            "orange" if spread < 1 else "blue" if 1 <= spread <= 2 else "green"
            for spread in df_price_spread_counts["Price Spread (SEK)"]
        ]
        plt.bar(
            df_price_spread_counts["Price Spread (SEK)"],
            df_price_spread_counts["Number of Days"],
            color=colors,
            width=0.2,
            edgecolor="black",
            alpha=0.7,
        )
        plt.title(f"Price Spread for {month}")
        plt.xlabel("Price Spread (SEK)")
        plt.ylabel("Number of Days")
        plt.grid(True)
        plt.xlim(0, max_spread + 0.5)  # Set x-axis limits to fit the largest spread
        plt.ylim(0, max_days + 1)  # Set y-axis limits to fit the largest number of days

    plt.tight_layout()
    plt.savefig("monthly.png")
    plt.show()

    # Print and return the DataFrame for each month
    for month, price_spread_counts in monthly_price_spread_counts.items():
        df_price_spread_counts = pd.DataFrame(
            list(price_spread_counts.items()),
            columns=["Price Spread (SEK)", "Number of Days"],
        )
        print(f"\nPrice Spread Counts for {month}:")
        print(df_price_spread_counts)

    return monthly_price_spread_counts


def print_to_terminal(df, columns_to_print):
    columns = [col for col in columns_to_print if col in df.columns]
    print(df[columns].round(3))


#    profit = df["Earning"].sum().round(2)
#    print(f"Profit {profit}  SEK")


def print_to_excel(df, columns_to_print, filename):
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"

    # Ensure datetimes are timezone-unaware
    df_to_save = df[columns_to_print].copy()
    df_to_save.index = df_to_save.index.tz_localize(None)

    # Save to Excel
    with pd.ExcelWriter(filename) as writer:
        df_to_save.to_excel(writer, sheet_name="Sheet1")
