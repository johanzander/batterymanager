
from datetime import datetime, timedelta
from nordpool import elspot
from zoneinfo import ZoneInfo

from modules.bess.electricityprices import calculate_prices

def fetch_nordpool_prices(area: str = "SE4", currency: str = "SEK") -> list[dict]:
    """Fetch electricity prices for today and tomorrow for a specified area.

    Args:
        area: The Nordpool area code (default: "SE4")
        currency: The currency for prices (default: "SEK")

    Returns:
        List of dictionaries containing hourly prices with timestamps

    """
    prices_spot = elspot.Prices(currency=currency)

    # Get today and tomorrow in UTC
    today = datetime.now().astimezone(ZoneInfo("UTC"))
    tomorrow = today + timedelta(hours=24)

    # Fetch prices
    today_data = prices_spot.hourly(areas=[area], end_date=today)
    today_values = today_data["areas"][area]["values"]

    # Try to get tomorrow's prices
    tomorrow_values = []
    try:
        tomorrow_data = prices_spot.hourly(areas=[area], end_date=tomorrow)
        if tomorrow_data is not None:
            tomorrow_values = tomorrow_data["areas"][area]["values"]
    except KeyError:
        pass  # Tomorrow's prices not available yet

    # Combine and process values
    values = today_values
    #values = tomorrow_values
    # values = today_values + tomorrow_values

    result = []

    for item in values:
        # Convert timestamp to Stockholm time
        timestamp = datetime.fromisoformat(str(item["start"])).astimezone(
            ZoneInfo("Europe/Stockholm")
        )

        # Convert price from SEK/MWh to SEK/kWh and calculate buy/sell prices
        base_price = item["value"] / 1000
        prices = calculate_prices(base_price)

        result.append(
            {
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M"),
                **prices,  # Unpacks price, buy_price, and sell_price
            }
        )

    return result


def print_price_table(prices: list[dict], title: str = "Electricity Prices"):
    """Print electricity prices in a formatted table.

    Args:
        prices: List of price dictionaries
        title: Table title to display

    """
    # Define column widths
    time_width = 16
    price_width = 10

    # Print header
    print(f"\n{title}")
    print("-" * (time_width + 3 * price_width + 4))
    print(
        f"{'Time':<{time_width}} {'Base':>{price_width}} {'Buy':>{price_width}} {'Sell':>{price_width}}"
    )
    print("-" * (time_width + 3 * price_width + 4))

    # Print each hour's prices
    for price in prices:
        time = price["timestamp"].split()[1]  # Extract just the time HH:MM
        print(
            f"{time:<{time_width}} "
            f"{price['price']:>{price_width}.4f} "
            f"{price['buy_price']:>{price_width}.4f} "
            f"{price['sell_price']:>{price_width}.4f}"
        )
    print("-" * (time_width + 3 * price_width + 4))
