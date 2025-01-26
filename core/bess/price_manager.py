"""Electricity price management with configurable sources and calculations."""

from datetime import date, datetime, timedelta
import logging
from typing import Any
from zoneinfo import ZoneInfo

import requests

from .defaults import (
    ADDITIONAL_COSTS,
    DEFAULT_AREA,
    MARKUP_RATE,
    TAX_REDUCTION,
    VAT_MULTIPLIER,
)

logger = logging.getLogger(__name__)


class PriceConfig:
    """Price calculation configuration."""

    def __init__(self):
        """Init function."""
        self.markup = MARKUP_RATE
        self.additional_costs = ADDITIONAL_COSTS
        self.tax_reduction = TAX_REDUCTION
        self.vat_multiplier = VAT_MULTIPLIER
        self.area = DEFAULT_AREA


class PriceCalculator:
    """Core price calculation logic."""

    def __init__(self, config: PriceConfig):
        """Init function."""
        self.config = config

    def calculate_prices(self, base_price: float) -> dict[str, float]:
        """Calculate all price variants from base price."""
        buy_price = (
            base_price + self.config.markup
        ) * self.config.vat_multiplier + self.config.additional_costs

        sell_price = base_price + self.config.tax_reduction

        return {
            "price": round(base_price, 4),
            "buyPrice": round(buy_price, 4),
            "sellPrice": round(sell_price, 4),
        }


class PriceSource:
    """Base class for price sources."""

    def get_prices(self, target_date: date, area: str) -> list[dict[str, Any]]:
        """Get prices for the specified date and area."""
        raise NotImplementedError

    def _create_price_list(
        self, prices: list[float], base_date: date
    ) -> list[dict[str, Any]]:
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

    def __init__(self, test_prices: list[float]):
        """Init function."""
        self.test_prices = test_prices
        config = PriceConfig()
        self.calculator = PriceCalculator(config)

    def set_test_prices(self, test_prices: list[float]):
        """Set test prices for the mock source."""
        self.test_prices = test_prices

    def get_prices(self, target_date: date, area: str) -> list[dict[str, Any]]:
        """Get prices for the specified date and area."""
        return self._create_price_list(self.test_prices, target_date)


class NordpoolAPISource(PriceSource):
    """Nord Pool Group API price source."""

    def __init__(self):
        """Init function."""
        config = PriceConfig()
        self.calculator = PriceCalculator(config)
        self.base_url = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
        self.params = {"market": "DayAhead", "currency": "SEK"}

    def get_prices(self, target_date: date, area: str) -> list[dict[str, Any]]:
        """Get prices for the specified date and area."""
        params = {
            "market": "DayAhead",
            "deliveryArea": area,
            "currency": "SEK",
            "date": target_date.strftime("%Y-%m-%d"),
        }

        response = requests.get(
            self.base_url,
            params=params,
            headers={
                "Accept": "application/json",
                "Origin": "https://data.nordpoolgroup.com",
                "Referer": "https://data.nordpoolgroup.com/",
                "User-Agent": "Mozilla/5.0",
            },
        )

        if response.status_code == 204:
            logger.warning("No prices found for date %s", target_date)
            return []

        if response.status_code != 200:
            logger.warning(
                "Failed to fetch prices for date %s, err: %s",
                target_date,
                str({response.status_code}),
            )
            raise RuntimeError(f"Failed to fetch prices: {response.status_code}")

        data = response.json()
        prices = []
        for entry in data.get("multiAreaEntries", []):
            if (
                entry.get("deliveryStart")
                and entry.get("entryPerArea", {}).get(area) is not None
            ):
                price = float(entry["entryPerArea"][area]) / 1000
                prices.append(price)
                logger.debug("Processed entry: %s with price %f", entry, price)
            else:
                logger.warning("Skipping entry: %s", entry)

        if len(prices) != 24:
            logger.warning(
                "Expected 24 prices but got %d for date %s", len(prices), target_date
            )

        if not prices:
            raise ValueError("No prices found in response")

        return self._create_price_list(prices, target_date)


class Guru56APISource(PriceSource):
    """Spot56k.guru API price source."""

    def __init__(self):
        """Init function."""
        config = PriceConfig()
        self.calculator = PriceCalculator(config)
        self.base_url = "https://spot.56k.guru/api/v2/hass"

    def get_prices(self, target_date: date, area: str) -> list[dict[str, Any]]:
        """Get prices for the specified date and area."""
        params = {"currency": "SEK", "area": area, "multiplier": 1, "decimals": 4}

        today = datetime.now().date()
        if target_date not in (today, today + timedelta(days=1)):
            raise ValueError("Can only fetch today or tomorrow's prices")

        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()

        result = []
        for item in data["data"]:
            timestamp = datetime.fromisoformat(item["st"]).astimezone(
                ZoneInfo("Europe/Stockholm")
            )

            if timestamp.date() == target_date:
                base_price = float(item["p"])
                price_entry = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}
                price_entry.update(self.calculator.calculate_prices(base_price))
                result.append(price_entry)

        return result


class HANordpoolSource(PriceSource):
    """Price source using Home Assistant's Nordpool sensor."""

    def __init__(self, ha_controller):
        """Init function."""
        self.ha_controller = ha_controller
        config = PriceConfig()
        self.calculator = PriceCalculator(config)

    def get_prices(self, target_date=None, area: str = "SE4") -> list[dict[str, Any]]:
        """Get prices for the specified date and area."""
        today = datetime.now().date()

        if target_date is None or target_date == today:
            prices = self.ha_controller.get_nordpool_prices_today()
        elif target_date == today + timedelta(days=1):
            prices = self.ha_controller.get_nordpool_prices_tomorrow()
        else:
            raise ValueError(
                f"Can only fetch today's or tomorrow's prices from HA sensor, not {target_date}"
            )

        prices_no_vat = []
        for price in prices:
            prices_no_vat.append(float(price) / 1.25)

        return self._create_price_list(prices_no_vat, target_date or today)


class ElectricityPriceManager:
    """Main interface for electricity price management."""

    def __init__(self, source: PriceSource):
        """Init function."""
        self.config = PriceConfig()
        self.calculator = PriceCalculator(self.config)
        self.source = source

    def get_today_prices(self) -> list[dict[str, Any]]:
        """Get today's prices."""
        return self.source.get_prices(
            target_date=datetime.now().date(), area=self.config.area
        )

    def get_tomorrow_prices(self) -> list[dict[str, Any]]:
        """Get tomorrow's prices."""
        return self.source.get_prices(
            target_date=datetime.now().date() + timedelta(days=1), area=self.config.area
        )

    def get_prices(self, target_date: date) -> list[dict[str, Any]]:
        """Get prices for specific date."""
        return self.source.get_prices(target_date=target_date, area=self.config.area)

    def get_settings(self) -> dict:
        """Get current settings."""
        return {
            "markupRate": self.config.markup,
            "vatMultiplier": self.config.vat_multiplier,
            "additionalCosts": self.config.additional_costs,
            "taxReduction": self.config.tax_reduction,
            "area": self.config.area,
        }

    def update_settings(
        self,
        markup=None,
        vat=None,
        additional_costs=None,
        tax_reduction=None,
        area=None,
    ) -> None:
        """Update settings."""
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
