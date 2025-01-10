"""Provides functions to fetch and calculate electricity prices from Nordpool.

Generates test price data, and prints the prices in a formatted table.
"""

from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)

# Price calculation constants (SEK per kWh)

# Tibber's markup on Nordpool: 8 öre/kWh
TIBBER_MARKUP = 0.08
# överföringsavgift: 28.90 öre, energiskatt: 53.50 öre, 25% moms: 20,60 öre = 1.03 SEK
ADDITIONAL_COSTS = 1.03
# 60 öre skattereduktion + 5.18 öre förlustersättning från nätägaren
TAX_REDUCTION = 0.6518
# 25% moms
VAT_MULTIPLIER = 1.25


def calculate_prices(base_price: float) -> dict[str, float]:
    """Calculate buy and sell prices from the Nordpool base price.

    Args:
        base_price: Base electricity price from Nordpool (SEK/kWh)

    Returns:
        Dictionary containing base, buy and sell prices

    """
    buy_price = (base_price + TIBBER_MARKUP) * VAT_MULTIPLIER + ADDITIONAL_COSTS
    sell_price = base_price + TAX_REDUCTION

    return {
        "price": round(base_price, 4),
        "buy_price": round(buy_price, 4),
        "sell_price": round(sell_price, 4),
    }


def add_timestamps_and_prices(nordpool_prices):
    """Add timestamps and prices to a list of base prices."""

    # Set up base timestamp
    base_timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    result = []
    for hour in range(len(nordpool_prices)):
        timestamp = base_timestamp + timedelta(hours=hour)
        base_price = nordpool_prices[hour % 24]  # Cycle through the 24-hour pattern
        prices = calculate_prices(base_price)

        result.append(
            {
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M"),
                **prices,  # Unpacks price, buy_price, and sell_price
            }
        )
    return result

