"""Electricity price management with configurable sources and calculations."""
from datetime import date, datetime, timedelta
import logging
from typing import Any, List
from zoneinfo import ZoneInfo
import requests
import json

logger = logging.getLogger(__name__)

class PriceConfig:
    """Price calculation configuration."""
    def __init__(self):
        self.use_actual_price = False
        self.markup = 0.08  # Default markup (8 öre/kWh)
        self.additional_costs = 1.03  # Default additional costs
        self.tax_reduction = 0.6518  # Default tax reduction
        self.vat_multiplier = 1.25  # Default VAT (25%)
        self.area = "SE4"  # Default area

class PriceCalculator:
    """Core price calculation logic."""
    def __init__(self, config: PriceConfig):
        self.config = config

    def calculate_prices(self, base_price: float) -> dict[str, float]:
        """Calculate all price variants from base price."""
        if self.config.use_actual_price:
            buy_price = (base_price + self.config.markup) * self.config.vat_multiplier + self.config.additional_costs
        else:
            buy_price = base_price

        sell_price = base_price + self.config.tax_reduction

        return {
            "price": round(base_price, 4),
            "buyPrice": round(buy_price, 4),
            "sellPrice": round(sell_price, 4),
        }

class PriceSource:
    """Base class for price sources."""
    def get_prices(self, target_date: date, area: str) -> list[dict[str, Any]]:
        """Get prices for date."""
        raise NotImplementedError

    def _create_price_list(self, prices: List[float], base_date: date) -> list[dict[str, Any]]:
        result = []
        base_timestamp = datetime.combine(base_date, datetime.min.time())
        
        for hour in range(len(prices)):
            timestamp = base_timestamp + timedelta(hours=hour)
            base_price = prices[hour]
            calculated_prices = self.calculator.calculate_prices(base_price)
            
            price_entry = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}
            price_entry.update(calculated_prices)
            result.append(price_entry)
        
        return result

class MockSource(PriceSource):
    """Mocked price source."""
    def __init__(self, test_prices: List[float]):
        self.test_prices = test_prices
        config = PriceConfig()
        self.calculator = PriceCalculator(config)

    def set_test_prices(self, test_prices: List[float]):
        self.test_prices = test_prices

    def get_prices(self, target_date: date, area: str) -> list[dict[str, Any]]:
        return self._create_price_list(self.test_prices, target_date)

class NordpoolAPISource(PriceSource):
    """Nord Pool Group API price source."""
    def __init__(self):
        config = PriceConfig()
        self.calculator = PriceCalculator(config)
        self.base_url = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
        self.params = {
            "market": "DayAhead",
            "currency": "SEK"
        }

    def get_prices(self, target_date: date, area: str) -> list[dict[str, Any]]:
        params = {
            "market": "DayAhead",
            "deliveryArea": area,
            "currency": "SEK",
            "date": target_date.strftime("%Y-%m-%d")
        }

        logger.warning("Requesting prices with URL: %s and params: %s", self.base_url, params)
        
        response = requests.get(
            self.base_url,
            params=params,
            headers={
            "Accept": "application/json",
#            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://data.nordpoolgroup.com",
            "Referer": "https://data.nordpoolgroup.com/",
            "User-Agent": "Mozilla/5.0"
            }
        )
        logger.warning("Received response: %s", response.text)

        if response.status_code == 204:
            logger.warning("No prices found for date %s", target_date)
            return []

        if response.status_code != 200:
            logger.warning("Failed to fetch prices for date %s, err: %s", target_date, str({response.status_code}))
            raise RuntimeError(f"Failed to fetch prices: {response.status_code}")
        
        filtered_lines = [line for line in response.text.splitlines() 
                         if not line.startswith((">", "<"))]
        data = json.loads("\n".join(filtered_lines))

        prices = []
        for entry in data.get("multiAreaEntries", []):
            if entry.get("deliveryStart") and entry.get("entryPerArea", {}).get(area):
                prices.append(float(entry["entryPerArea"][area]) / 1000)

        if not prices:
            raise ValueError("No prices found in response")

        return self._create_price_list(prices, target_date)

class Guru56APISource(PriceSource):
    """Spot56k.guru API price source."""
    def __init__(self):
        config = PriceConfig()
        self.calculator = PriceCalculator(config)
        self.base_url = "https://spot.56k.guru/api/v2/hass"

    def get_prices(self, target_date: date, area: str) -> list[dict[str, Any]]:
        params = {
            "currency": "SEK",
            "area": area,
            "multiplier": 1,
            "decimals": 4
        }

        today = datetime.now().date()
        if target_date not in (today, today + timedelta(days=1)):
            raise ValueError("Can only fetch today or tomorrow's prices")

        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()

        result = []
        for item in data["data"]:
            timestamp = datetime.fromisoformat(item["st"]).astimezone(ZoneInfo("Europe/Stockholm"))

            if timestamp.date() == target_date:
                base_price = float(item["p"])
                price_entry = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}
                price_entry.update(self.calculator.calculate_prices(base_price))
                result.append(price_entry)

        return result

class HANordpoolSource(PriceSource):
    """Price source using Home Assistant's Nordpool sensor."""
    def __init__(self, ha_controller):
        self.ha_controller = ha_controller
        config = PriceConfig()
        self.calculator = PriceCalculator(config)
        
    def get_prices(self, target_date=None, area: str = "SE4") -> list[dict[str, Any]]:
        today = datetime.now().date()
        
        if target_date is None or target_date == today:
            prices = self.ha_controller.get_nordpool_prices_today()
        elif target_date == today + timedelta(days=1):
            prices = self.ha_controller.get_nordpool_prices_tomorrow()
        else:
            raise ValueError(f"Can only fetch today's or tomorrow's prices from HA sensor, not {target_date}")
            
        prices_no_vat = []
        for price in prices:
            prices_no_vat.append(float(price) / 1.25)
        
        return self._create_price_list(prices_no_vat, target_date or today)

class ElectricityPriceManager:
    """Main interface for electricity price management."""
    def __init__(self, source: PriceSource):
        self.config = PriceConfig()
        self.calculator = PriceCalculator(self.config)
        self.source = source

    def get_today_prices(self) -> list[dict[str, Any]]:
        """Get today's prices."""
        return self.source.get_prices(target_date=datetime.now().date(), area=self.config.area)

    def get_tomorrow_prices(self) -> list[dict[str, Any]]:
        """Get tomorrow's prices."""
        return self.source.get_prices(target_date=datetime.now().date() + timedelta(days=1), area=self.config.area)

    def get_prices(self, target_date: date) -> list[dict[str, Any]]:
        """Get prices for specific date."""
        return self.source.get_prices(target_date=target_date, area=self.config.area)

    def get_settings(self) -> dict:
        """Get current settings."""
        return {
            "useActualPrice": self.config.use_actual_price,
            "markupRate": self.config.markup,
            "vatMultiplier": self.config.vat_multiplier,
            "additionalCosts": self.config.additional_costs,
            "taxReduction": self.config.tax_reduction,
            "area": self.config.area,
        }

    def update_settings(self, use_actual_price=None, markup=None, vat=None, 
                        additional_costs=None, tax_reduction=None, area=None) -> None:
        """Update settings."""
        if use_actual_price is not None:
            self.config.use_actual_price = use_actual_price
        if markup is not None:
            self.config.markup = markup
        if vat is not None:
            self.config.vat_multiplier = vat
        if additional_costs is not None:
            self.config.additional_costs = additional_costs
        if tax_reduction is not None:
            self.config.tax_reduction = tax_reduction
        if area is not None:
            self.config.area = area

        # Update source calculator config
        self.source.calculator.config = self.config