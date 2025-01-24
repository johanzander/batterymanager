# Battery constants
BATTERY_STORAGE_SIZE_KWH = 30.0
BATTERY_MIN_SOC = 10  # percentage
BATTERY_MAX_SOC = 100  # percentage
BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW = 15.0
BATTERY_CHARGE_CYCLE_COST_SEK = 0.50
BATTERY_DEFAULT_CHARGING_POWER_RATE = 40  # percentage

# Electricity price constants
MARKUP_RATE = 0.08  # 8 öre/kWh
VAT_MULTIPLIER = 1.25  # 25% VAT
ADDITIONAL_COSTS = 1.03  # överföringsavgift + energiskatt + moms
TAX_REDUCTION = 0.6518  # skattereduktion + förlustersättning

# Area options
AREA_OPTIONS = ["SE1", "SE2", "SE3", "SE4"]
DEFAULT_AREA = "SE4"

# Default settings
DEFAULT_BATTERY_SETTINGS = {
    "totalCapacity": BATTERY_STORAGE_SIZE_KWH,
    "reservedCapacity": BATTERY_MIN_SOC / 100 * BATTERY_STORAGE_SIZE_KWH,
    "estimatedConsumption": 4.5,
    "maxChargeDischarge": BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW,
    "chargeCycleCost": BATTERY_CHARGE_CYCLE_COST_SEK,
    "chargingPowerRate": BATTERY_DEFAULT_CHARGING_POWER_RATE
}

DEFAULT_ELECTRICITY_SETTINGS = {
    "useActualPrice": False,
    "fees": MARKUP_RATE,
    "vat": VAT_MULTIPLIER,
    "additionalCosts": ADDITIONAL_COSTS,
    "area": DEFAULT_AREA
}