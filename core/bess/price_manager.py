"""Electricity price manager for handling different price sources and calculations."""

from datetime import datetime, timedelta, date
#from fastapi import HTTPException
from typing import Any
import logging
from zoneinfo import ZoneInfo
import requests
import json

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

# Constants for price calculations
# Tibber's markup on Nordpool: 8 öre/kWh
MARKUP = 0.08
# överföringsavgift: 28.90 öre, energiskatt: 53.50 öre, 25% moms: 20,60 öre = 1.03 SEK
ADDITIONAL_COSTS = 1.03
# 60 öre skattereduktion + 5.18 öre förlustersättning från nätägaren
TAX_REDUCTION = 0.6518
# 25% moms
VAT_MULTIPLIER = 1.25

class _PriceConfig:
    """Internal configuration for price calculations."""
    def __init__(
        self,
        markup=MARKUP,  # 8 öre/kWh
        additional_costs=ADDITIONAL_COSTS,  # överföringsavgift + energiskatt + moms
        tax_reduction=TAX_REDUCTION,  # skattereduktion + förlustersättning
        vat_multiplier=VAT_MULTIPLIER  # 25% moms
    ):
        self.markup = markup
        self.additional_costs = additional_costs
        self.tax_reduction = tax_reduction
        self.vat_multiplier = vat_multiplier

class _PriceCalculator:
    """Internal handler for price calculations."""
    
    def __init__(self, config=None):
        self.config = config if config else _PriceConfig()
    
    def calculate_buy_sell_prices(self, base_price) -> dict[str, float]:
        """Calculate buy and sell prices from the Nordpool base price."""
        buy_price = (base_price + self.config.markup) * self.config.vat_multiplier + self.config.additional_costs
        sell_price = base_price + self.config.tax_reduction

        return {
            "price": round(base_price, 4),
            "buyPrice": round(buy_price, 4),
            "sellPrice": round(sell_price, 4),
        }

class PriceSource:
    """Base class for different price sources."""
    
    def __init__(self):
        self._calculator = _PriceCalculator()
    
    def get_prices(self, target_date=None) -> list[dict[str, Any]]:
        """Get prices for a specific date."""
        raise NotImplementedError("Subclasses must implement get_prices")

    def _update_calculator_config(self, **kwargs) -> None:
        """Update calculator configuration."""
        for key, value in kwargs.items():
            if hasattr(self._calculator.config, key):
                setattr(self._calculator.config, key, value)

class HANordpoolSource(PriceSource):
    """Price source using Home Assistant's Nordpool sensor."""
    
    def __init__(self, ha_controller):
        self._calculator = _PriceCalculator()
        self.ha_controller = ha_controller
        
    def get_prices(self, target_date=None) -> list[dict[str, Any]]:
        today = datetime.now().date()
        
        if target_date is None or target_date == today:
            prices = self.ha_controller.get_nordpool_prices_today()
        elif target_date == today + timedelta(days=1):
            prices = self.ha_controller.get_nordpool_prices_tomorrow()
        else:
            raise ValueError(f"Can only fetch today's or tomorrow's prices from HA sensor, not {target_date}")
            
        # Remove VAT from prices as they come with VAT included from HA
        prices_no_vat = []
        for price in prices:
            prices_no_vat.append(float(price) / 1.25)
        
        return self._create_price_list(prices_no_vat, target_date or today)

    def _create_price_list(self, prices, base_date) -> list[dict[str, Any]]:
        result = []
        base_timestamp = datetime.combine(base_date, datetime.min.time())
        
        for hour in range(len(prices)):
            timestamp = base_timestamp + timedelta(hours=hour)
            base_price = prices[hour]
            calculated_prices = self._calculator.calculate_buy_sell_prices(base_price)
            
            price_entry = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}
            price_entry.update(calculated_prices)
            result.append(price_entry)
        
        return result

class Spot56APISource(PriceSource):
    """Price source using the spot.56k.guru API that provides today and tomorrow's prices."""
    
    def __init__(self, area="SE4", currency="SEK"):
        self._calculator = _PriceCalculator()
        self.base_url = "https://spot.56k.guru/api/v2/hass"
        self.params = {
            "currency": currency,
            "area": area,
            "multiplier": 1,
            "extra": 0,
            "factor": 1,
            "decimals": 4
        }

    def get_prices(self, target_date=None) -> list[dict[str, Any]]:
        """Get electricity prices for today or tomorrow.
        
        Args:
            target_date: The date to get prices for. Must be either today or tomorrow.
            
        Returns:
            List of hourly prices with timestamps
            
        Raises:
            ValueError: If target_date is not today or tomorrow
        """
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        if target_date and target_date not in (today, tomorrow):
            raise ValueError("Spot56k API only provides prices for today and tomorrow")
            
        response = requests.get(self.base_url, params=self.params)
        logger.debug(f"Request URL: {response.url}")
        logger.debug(f"Request Params: {response.request.body}")
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response Data: {json.dumps(data, indent=2)}")
        
        result = []
        for item in data["data"]:
            timestamp = datetime.fromisoformat(item["st"]).astimezone(ZoneInfo("Europe/Stockholm"))
            
            # If target_date specified, only include matching prices
            if target_date and timestamp.date() != target_date:
                continue
                
            base_price = float(item["p"])
            calculated_prices = self._calculator.calculate_buy_sell_prices(base_price)
            
            price_entry = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}
            price_entry.update(calculated_prices)
            result.append(price_entry)
        
        logger.debug(f"Processed prices: {result}")
        return result
    
    
class NordpoolAPISource(PriceSource):
    """Price source using the Nord Pool Group API."""
    
    def __init__(self, area="SE4", currency="SEK"):
        super().__init__()  # Ensure the base class initializer is called
        self.base_url = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
        self.params = {
            "market": "DayAhead",
            "deliveryArea": area,
            "currency": currency
        }
    
    def get_prices(self, target_date=None) -> list[dict[str, Any]]:
        if target_date is None:
            target_date = datetime.now().date()
        
        self.params["date"] = target_date.strftime("%Y-%m-%d")
        
        response = requests.get(self.base_url, params=self.params, headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://data.nordpoolgroup.com",
            "Referer": "https://data.nordpoolgroup.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15"
        })
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch prices: {response.status_code} {response.text}")
            raise RuntimeError(f"Failed to fetch prices: {response.status_code} {response.text}")
        
        try:
            response_content = response.content
   #         logger.debug("Response Content Type: %s", response.headers.get('Content-Type'))
  #          logger.debug("Response Content:")
 #           logger.debug(response_content)
            response_str = response_content.decode('utf-8')
#            logger.debug(response_str)

            # Filter out lines starting with '>' or '<'
            filtered_lines = [line for line in response_str.splitlines() if not line.startswith(('>', '<'))]
            filtered_response_str = '\n'.join(filtered_lines)
            
            if not filtered_response_str.strip():
                logger.error("Empty response content")
                raise ValueError("Empty response content")
            
            data = json.loads(filtered_response_str)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}")
            raise ValueError(f"JSON decoding failed: {e}")
        except Exception as e:
            logger.error(f"Failed to decode response: {e}")
            raise RuntimeError(f"Failed to decode response: {e}")
        
        prices = []
        for entry in data.get("multiAreaEntries", []):
            delivery_start = entry.get("deliveryStart")
            price = entry.get("entryPerArea", {}).get("SE4")
            if delivery_start is not None and price is not None:
                prices.append(float(price)/1000)
        
        if not prices:
            logger.error("No prices found in the JSON response")
            raise ValueError("No prices found in the JSON response")
        
        result = []
        base_timestamp = datetime.combine(target_date, datetime.min.time())
        
        for hour, base_price in enumerate(prices):
            timestamp = base_timestamp + timedelta(hours=hour)
            calculated_prices = self._calculator.calculate_buy_sell_prices(base_price)
            
            price_entry = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}
            price_entry.update(calculated_prices)
            result.append(price_entry)
        
        return sorted(result, key=lambda x: x["timestamp"])

        
class ElectricityPriceManager:
    """Main class for managing electricity prices from different sources."""
    
    def __init__(self, price_source):
        self._price_source = price_source
    
    def get_today_prices(self) -> list[dict[str, Any]]:
        """Get electricity prices for today.
        
        Returns:
            List of dictionaries containing timestamp and prices:
            [
                {
                    "timestamp": "2025-01-17 00:00",
                    "price": 0.5000,      # Base Nordpool price
                    "buy_price": 0.7500,  # Price when buying from grid
                    "sell_price": 0.4000  # Price when selling to grid
                },
                ...
            ]
        """
        return self._price_source.get_prices(datetime.now().date())

    def get_tomorrow_prices(self) -> list[dict[str, Any]]:
        """Get electricity prices for tomorrow.
        
        Returns:
            List of dictionaries containing timestamp and prices for tomorrow
        """
        tomorrow = datetime.now().date() + timedelta(days=1)
        return self._price_source.get_prices(tomorrow)
    
    def get_prices(self, target_date: date) -> list[dict[str, Any]]:
        """Get electricity prices for a specific date.
        
        Args:
            target_date: The date to get prices for
            
        Returns:
            List of dictionaries containing timestamp and prices
        """
        return self._price_source.get_prices(target_date)
    
    def update_price_config(self, 
                          markup=None,
                          additional_costs=None,
                          tax_reduction=None,
                          vat_multiplier=None) -> None:
        """Update price calculation configuration.
        
        Args:
            markup: Markup on Nordpool price (öre/kWh)
            additional_costs: Additional fixed costs (SEK/kWh)
            tax_reduction: Tax reduction and loss compensation (SEK/kWh)
            vat_multiplier: VAT multiplier (e.g., 1.25 for 25% VAT)
        """
        updates = {}
        if markup is not None:
            updates['markup'] = markup
        if additional_costs is not None:
            updates['additional_costs'] = additional_costs
        if tax_reduction is not None:
            updates['tax_reduction'] = tax_reduction
        if vat_multiplier is not None:
            updates['vat_multiplier'] = vat_multiplier
            
        self._price_source._update_calculator_config(**updates)
    
    def print_price_table(self, prices, title="Electricity Prices") -> None:
        """Print electricity prices in a formatted table."""
        time_width = 16
        price_width = 10

        print(f"\n{title}")
        print("-" * (time_width + 3 * price_width + 4))
        print(
            f"{'Time':<{time_width}} {'Base':>{price_width}} {'Buy':>{price_width}} {'Sell':>{price_width}}"
        )
        print("-" * (time_width + 3 * price_width + 4))

        for price in prices:
            time = price["timestamp"].split()[1]
            print(
                f"{time:<{time_width}} "
                f"{price['price']:>{price_width}.4f} "
                f"{price['buyPrice']:>{price_width}.4f} "
                f"{price['sellPrice']:>{price_width}.4f}"
            )
        print("-" * (time_width + 3 * price_width + 4))
        