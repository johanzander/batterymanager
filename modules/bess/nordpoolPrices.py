"""Fetches and processes Nordpool electricity prices for today and tomorrow for the SE4 area."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from nordpool import elspot
import pandas as pd


def NordpoolPrices():
    """Fetch and process Nordpool electricity prices for today and tomorrow for the SE4 area.

    Returns:
        pd.DataFrame: A DataFrame containing the combined electricity prices with timestamps in Stockholm local time.

    """
    prices_spot = elspot.Prices(currency="SEK")

    today = datetime.now()
    tomorrow = datetime.today() + timedelta(hours=24)

    # Convert dates to UTC
    today = today.astimezone(ZoneInfo("UTC"))
    tomorrow = tomorrow.astimezone(ZoneInfo("UTC"))

    # Fetch hourly Elspot prices for SE4
    today_data = prices_spot.hourly(areas=["SE4"], end_date=today)
    try:
        tomorrow_data = prices_spot.hourly(areas=["SE4"], end_date=tomorrow)
        if tomorrow_data is not None:
            tomorrow_values = tomorrow_data["areas"]["SE4"]["values"]
        else:
            print("Tomorrow's prices are not available yet.")
            tomorrow_values = []
    except KeyError:
        print("Tomorrow's prices are not available yet.")
        tomorrow_values = []

    # Extract the values
    today_values = today_data["areas"]["SE4"]["values"]

    # Create DataFrames
    df_today = pd.DataFrame(today_values)
    df_tomorrow = pd.DataFrame(tomorrow_values)

    # Combine the DataFrames
    df = pd.concat([df_today, df_tomorrow])

    # Convert the 'start' column to datetime
    df["Timestamp"] = pd.to_datetime(df["start"])

    # Convert UTC to local time (Stockholm)
    df["Timestamp"] = df["Timestamp"].dt.tz_convert(ZoneInfo("Europe/Stockholm"))

    # Set the 'start' datetime as the index
    df.set_index("Timestamp", inplace=True)

    # Drop the 'end' column
    df.drop(columns=["start", "end"], inplace=True)

    df["value"] = df["value"] / 1000

    # Rename the 'value' column to something more descriptive
    df.rename(columns={"value": "ElectricityPrice"}, inplace=True)

    return df


def NordPoolTestPrices():

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
