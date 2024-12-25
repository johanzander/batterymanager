"""Constants used for battery energy storage system (BESS) calculations."""

# Battery storage size in kWh
BATTERY_STORAGE_SIZE_KWH = 30

# Minimum state of charge (SOC) in percent
BATTERY_MIN_SOC = 10

# Maximum charge/discharge rate in kW: 2500W / battery * 6 batteries
BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW = 15

# Cost for a 1 kWh battery charge/discharge cycle in SEK
BATTERY_CHARGE_CYCLE_COST_SEK = 0.50

# Minimum profit per cycle in SEK
# Example: 0.1: Don't charge / discharge unless we make for least 10 öre / kWh (3 SEK / 30kWh)
MINIMUM_PROFIT_PER_CYCLE = 0.1

# Tibber's markup on Nordpool in SEK per kWh
TIBBER_MARKUP_SEK_PER_KWH = 0.08

# Additional costs for buying 1 kWh of electricity in SEK
# - överföringsavgift: 28.90 öre, energiskatt: 53.50 öre, 25% moms: 20,60 öre = 1.03 SEK
ADDITIONAL_ELECTRICITY_COSTS_SEK_PER_KWH = 1.03

# Tax reduction from electricity sale in SEK
# - 60 öre skattereduktion + 5.18 öre förlustersättning från nätägaren
TAX_REDUCTION_SOLD_ELECTRICITY = 0.6518
