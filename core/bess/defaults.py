"""Module with default values for battery storage and electricity pricing."""

# Battery default values
BATTERY_STORAGE_SIZE_KWH = 30.0
BATTERY_MIN_SOC = 10  # percentage
BATTERY_MAX_SOC = 100  # percentage
BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW = 15.0
BATTERY_CHARGE_CYCLE_COST_SEK = 0.50
BATTERY_DEFAULT_CHARGING_POWER_RATE = 40  # percentage

# Electricity price default values
USE_ACTUAL_PRICE = False
MARKUP_RATE = 0.08  # 8 öre/kWh
VAT_MULTIPLIER = 1.25  # 25% VAT
ADDITIONAL_COSTS = (
    1.03  # överföringsavgift: 28.90 öre, energiskatt: 53.50 öre + 25% moms
)
TAX_REDUCTION = 0.6518  # 60 öre skattereduktion + 5.18 öre förlustersättning

MIN_PROFIT = 0.2  # Minimim profit (SEK/kWh) to consider a charge/discharge cycle

# Home default values
HOME_HOURLY_CONSUMPTION_KWH = 4.5

# Area options
DEFAULT_AREA = "SE4"
