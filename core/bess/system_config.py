"""System configuration and settings module."""

from enum import Enum

from pydantic import BaseModel, Field


class AreaCode(str, Enum):
    """Valid Nordpool area codes."""

    SE1 = "SE1"
    SE2 = "SE2"
    SE3 = "SE3"
    SE4 = "SE4"


class BatterySettings(BaseModel):
    """Configurable battery settings with defaults."""

    totalCapacity: float = Field(
        30.0, title="Total Capacity", description="Total battery capacity in kWh"
    )
    reservedCapacity: float = Field(
        3.0,
        title="Reserved Capacity",
        description="Minimum reserved battery capacity in kWh",
    )
    estimatedConsumption: float = Field(
        4.5,
        title="Estimated Consumption",
        description="Estimated hourly consumption in kWh",
    )
    maxChargeDischarge: float = Field(
        15.0,
        title="Max Charge/Discharge",
        description="Maximum charge/discharge power in kW",
    )
    chargeCycleCost: float = Field(
        0.50, title="Charge Cycle Cost", description="Cost per charge cycle in SEK"
    )
    chargingPowerRate: float = Field(
        40.0,
        title="Charging Power Rate",
        description="Current charging power rate in percentage of max charge power",
    )
    useActualPrice: bool = Field(
        False,
        title="Use Actual Price",
        description="Whether to use actual buy price or Nordpool price in calculations",
    )


class ElectricityPriceSettings(BaseModel):
    """Configurable electricity pricing settings."""

    area: AreaCode = Field(
        AreaCode.SE4, title="Price Area", description="Nordpool price area"
    )
    markupRate: float = Field(
        0.08,
        title="Markup Rate",
        description="Markup on Nordpool price by electricity procider in SEK/kWh (excl VAT)",
    )
    vatMultiplier: float = Field(
        1.25,
        title="VAT Multiplier",
        description="Value Added Tax multiplier (e.g., 1.25 for 25% VAT)",
    )
    additionalCosts: float = Field(
        1.03,
        title="Additional Costs",
        description="Fixed additional costs in SEK/kWh, for example tax and grid fees",
    )
    taxReduction: float = Field(
        0.6518,
        title="Tax Reduction",
        description="Tax reduction (and loss compensation) for sold electricity in SEK/kWh",
    )
