"""Contains pytest fixtures for testing price patterns and consumption values."""

import pytest


@pytest.fixture
def test_prices_tomorrow():
    """Return prices for tomorrow."""
    return [
        0.9800,
        0.8400,
        0.0300,
        0.0100,
        0.0100,
        0.9100,
        1.4400,
        1.5200,
        1.4000,
        1.1300,
        0.8600,
        0.6500,
        0.2900,
        0.1400,
        0.1300,
        0.6200,
        0.8900,
        1.1700,
        1.5200,
        2.5900,
        2.7300,
        1.9300,
        1.5100,
        1.3100,
    ]


@pytest.fixture
def test_prices(request):
    """Provide the requested test consumption."""
    return request.getfixturevalue(request.param)


@pytest.fixture
def test_prices_flat():
    """Return flat price test data."""
    return [1.0] * 24


@pytest.fixture
def test_prices_peak():
    """Return peak price test data."""
    return [
        0.98,
        0.84,
        0.03,
        0.01,
        0.01,
        0.91,
        1.44,
        1.52,
        1.40,
        1.13,
        0.86,
        0.65,
        0.29,
        0.14,
        0.13,
        0.62,
        0.89,
        1.17,
        1.52,
        2.59,
        2.73,
        1.93,
        1.51,
        1.31,
    ]


@pytest.fixture
def test_prices_2024_08_16():
    """Return price pattern from 2024-08-16."""
    return [
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


@pytest.fixture
def test_prices_2025_01_05():
    """Return price pattern from 2025-01-05."""
    return [
        0.780,
        0.790,
        0.800,
        0.830,
        0.950,
        0.970,
        1.160,
        1.170,
        1.220,
        1.280,
        1.210,
        1.300,
        1.200,
        1.130,
        0.980,
        0.740,
        0.730,
        0.950,
        0.920,
        0.740,
        0.530,
        0.530,
        0.500,
        0.400,
    ]

@pytest.fixture
def test_prices_2025_01_12():
    """Return Nordpool prices for given date."""
    return [
        0.357,
        0.301,
        0.289,
        0.349,
        0.393,
        0.405,
        0.412,
        0.418,
        0.447,
        0.605,
        0.791,
        0.919,
        0.826,
        0.779,
        1.066,
        1.332,
        1.492,
        1.583,
        1.677,
        1.612,
        1.514,
        1.277,
        0.829,
        0.481,
    ]

@pytest.fixture
def test_prices_2025_01_13():
    """Return Nordpool prices for given date."""
    return [
        0.477,
        0.447,
        0.450,
        0.438,
        0.433,
        0.422,
        0.434,
        0.805,
        1.180,
        0.654,
        0.454,
        0.441,
        0.433,
        0.425,
        0.410,
        0.399,
        0.402,
        0.401,
        0.379,
        0.347,
        0.067,
        0.023,
        0.018,
        0.000,
    ]
    
@pytest.fixture
def test_consumption(request):
    """Provide the requested test consumption."""
    return request.getfixturevalue(request.param)


@pytest.fixture
def test_consumption_none():
    """Provide no test consumption data."""
    return 0.3  # TODO: Change to 0.0 once div by zero error is fixed


@pytest.fixture
def test_consumption_low():
    """Provide low test consumption data."""
    return 3.5


@pytest.fixture
def test_consumption_medium():
    """Provide medium test consumption data."""
    return 5.2


@pytest.fixture
def test_consumption_high():
    """Provide high test consumption data."""
    return 8.0


@pytest.fixture
def test_charging_power_rate():
    """Provide charging power rate."""
    return 40
