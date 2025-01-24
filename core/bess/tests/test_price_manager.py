"""Test suite for electricity price manager."""

import pytest
from datetime import datetime, timedelta, date
from bess.price_manager import ElectricityPriceManager, NordpoolAPISource, Guru56APISource, HANordpoolSource, MockSource
import json

class MockHAController:
    """Mock Home Assistant controller for testing."""
    
    def __init__(self, today_prices=None, tomorrow_prices=None, vat=0.25):
        self.today_prices = today_prices if today_prices else []
        self.tomorrow_prices = tomorrow_prices if tomorrow_prices else []
        self.vat = vat
    
    def get_nordpool_prices_today(self):
        return [price * (1 + self.vat) for price in self.today_prices]
    
    def get_nordpool_prices_tomorrow(self):
        return [price * (1 + self.vat) for price in self.tomorrow_prices]

class TestPriceManager:
    """Test cases for ElectricityPriceManager."""
    
    @pytest.fixture
    def test_prices_flat(self):
        """Return flat price test data."""
        return [1.0] * 24
    
    @pytest.fixture
    def test_prices_peak(self):
        """Return peak price pattern."""
        return [
            0.98, 0.84, 0.03, 0.01, 0.01, 0.91,
            1.44, 1.52, 1.40, 1.13, 0.86, 0.65,
            0.29, 0.14, 0.13, 0.62, 0.89, 1.17,
            1.52, 2.59, 2.73, 1.93, 1.51, 1.31,
        ]
    
    def test_today_prices_flat(self, test_prices_flat):
        """Test today's prices with flat pricing."""
        mock_source = MockSource(test_prices_flat)
        manager = ElectricityPriceManager(mock_source)
        
        prices = manager.get_today_prices()
        assert len(prices) == 24
        assert all(p["price"] == 1.0 for p in prices)
#        assert all(p["buyPrice"] > p["price"] for p in prices)
#        assert all(p["sellPrice"] > p["price"] for p in prices)
    # TODO: Fix the above assertions
    
    def test_today_prices_peak(self, test_prices_peak):
        """Test today's prices with peak pricing."""
        mock_source = MockSource(test_prices_peak)
        manager = ElectricityPriceManager(mock_source)
        
        prices = manager.get_today_prices()
        print(f"Today's peak prices: {prices}")  # Debug print
        assert len(prices) == 24
        assert min(p["price"] for p in prices) == 0.01
        assert max(p["price"] for p in prices) == 2.73
    
    def test_tomorrow_prices(self, test_prices_peak):
        """Test tomorrow's prices."""
        mock_source = MockSource(test_prices_peak)
        manager = ElectricityPriceManager(mock_source)
        
        prices = manager.get_tomorrow_prices()
        print(f"Tomorrow's prices: {prices}")  # Debug print
        tomorrow = datetime.now().date() + timedelta(days=1)
        assert len(prices) == 24
        assert all(datetime.strptime(p["timestamp"], "%Y-%m-%d %H:%M").date() == tomorrow 
                  for p in prices)
    
    def test_specific_date_prices(self, test_prices_peak):
        """Test getting prices for a specific date."""
        mock_source = MockSource(test_prices_peak)
        manager = ElectricityPriceManager(mock_source)
        
        test_date = date(2025, 1, 17)
        prices = manager.get_prices(test_date)
        print(f"Prices for {test_date}: {prices}")  # Debug print
        assert len(prices) == 24
        assert all(datetime.strptime(p["timestamp"], "%Y-%m-%d %H:%M").date() == test_date 
                  for p in prices)
    
    def test_price_config_update(self, test_prices_flat):
        """Test updating price calculation config."""
        mock_source = MockSource(test_prices_flat)
        manager = ElectricityPriceManager(mock_source)
        
        # Get prices with default config
        default_prices = manager.get_today_prices()
        default_buy_price = default_prices[0]["buyPrice"]
        
        # Update config and get new prices
        manager.update_settings(markup=0.20)  # Increase markup
        new_prices = manager.get_today_prices()
        new_buy_price = new_prices[0]["buyPrice"]
        
        print(f"Default buy price: {default_buy_price}, New buy price: {new_buy_price}")  # Debug print
        # assert new_buy_price > default_buy_price
        # TODO: Fix the above assertion
        
    def test_nordpool_source(self):
        """Test Nordpool source."""
        nordpool_source = NordpoolAPISource()
        manager = ElectricityPriceManager(nordpool_source)
        
        # Test today's prices
        today_prices = manager.get_today_prices()
        print(f"Nordpool Today's prices: {today_prices}")  # Debug print
        assert len(today_prices) == 24
        
        # Test tomorrow's prices
        tomorrow_prices = manager.get_tomorrow_prices()
        print(f"Nordpool Tomorrow's prices: {tomorrow_prices}")  # Debug print
        if tomorrow_prices:
            assert len(tomorrow_prices) == 24
    
    def test_guru56api_source(self):
        """Test Guru56API source."""
        guru56api_source = Guru56APISource()
        manager = ElectricityPriceManager(guru56api_source)
        
        # Test today's prices
        today_prices = manager.get_today_prices()
        print(f"Guru56 Today's prices: {today_prices}")  # Debug print
        assert len(today_prices) == 24

        # Test tomorrow's prices
        tomorrow_prices = manager.get_tomorrow_prices()
        print(f"Guru56 Tomorrow's prices: {tomorrow_prices}")  # Debug print
        if tomorrow_prices:
            assert len(tomorrow_prices) == 24

    
    def test_ha_source(self, test_prices_peak):
        """Test Home Assistant source."""
        ha_controller = MockHAController(
            today_prices=test_prices_peak,
            tomorrow_prices=test_prices_peak,
            vat=0.25
        )
        ha_source = HANordpoolSource(ha_controller)
        manager = ElectricityPriceManager(ha_source)
        
        # Test today's prices
        today_prices = manager.get_today_prices()
        print(f"HA Today's prices: {today_prices}")  # Debug print
        assert len(today_prices) == 24
        assert min(p["price"] for p in today_prices) == 0.01
        assert max(p["price"] for p in today_prices) == 2.73
        
        # Test tomorrow's prices
        tomorrow_prices = manager.get_tomorrow_prices()
        print(f"HA Tomorrow's prices: {tomorrow_prices}")  # Debug print
        assert len(tomorrow_prices) == 24