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
