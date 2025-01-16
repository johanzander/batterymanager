"""Home Assistant pyscript Battery Manager for Growatt Inverter/Battery."""

from datetime import datetime

import bess

# Initialize components
controller = bess.HomeAssistantController()
battery_manager = bess.BatteryManager()
growatt_schedule = bess.GrowattScheduleManager()

# Set to True to enable test mode (no actual changes will be made)
TEST_MODE = True

def optimize_schedule():
    """Optimize battery charging schedule based on electricity prices."""
    battery_manager.set_prediction_data(
        estimated_consumption_per_hour_kwh=4.5,
        #        estimated_consumption_per_hour_kwh=controller.get_estimated_consumption(),
        max_charging_power_rate=controller.get_charging_power_rate(),
    )

    # Generate and print schedule
    schedule = battery_manager.optimize_schedule()

    # Apply schedule to Growatt
    growatt_schedule.apply_schedule(schedule)
    growatt_schedule.get_daily_TOU_settings()


def dry_run():
    """Show the schedule for today and tomorrow, but don't update any settings."""

    log.info("\n -= Todays schedule =- ")
    nordpool_prices = sensor.nordpool_kwh_se4_sek_2_10_025.today
    if not nordpool_prices:
        log.warning("No prices available from Nordpool sensor")
        return

    # Remove VAT from prices
    nordpool_prices_ex_vat = [float(price) / 1.25 for price in nordpool_prices]
    electricity_prices = bess.add_timestamps_and_prices(nordpool_prices_ex_vat)

    # Configure battery manager
    battery_manager.set_electricity_prices(electricity_prices)
    optimize_schedule()

    log.info("\n -= Tomorrows schedule =- ")
    nordpool_prices = sensor.nordpool_kwh_se4_sek_2_10_025.tomorrow
    if not nordpool_prices:
        log.warning("No prices available for tomorrow yet")
        return

    # Remove VAT from prices
    nordpool_prices_ex_vat = [float(price) / 1.25 for price in nordpool_prices]
    electricity_prices = bess.add_timestamps_and_prices(nordpool_prices_ex_vat)

    # Configure battery manager
    battery_manager.set_electricity_prices(electricity_prices)
    optimize_schedule()


@time_trigger("startup")
def run_on_startup() -> None:
    """Run automatically on startup or reload."""
    file_save_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.info("BatteryManager initializing, version: %s", file_save_date)

    controller.set_test_mode(TEST_MODE)
    log.info("Running in %s mode", "TEST" if TEST_MODE else "NORMAL")

    dry_run()
    run_prepare_todays_daily_schedule()
#    growatt_schedule._log_growatt_schedule()
    run_hourly_task()


@time_trigger("cron(55 23 * * *)")
def run_prepare_next_days_daily_schedule() -> None:
    """Run at 23:55 to update TOU settings for next day."""
    log.info("Preparing next day's schedule")

    try:
        nordpool_prices = sensor.nordpool_kwh_se4_sek_2_10_025.tomorrow
        if not nordpool_prices:
            log.warning("No prices available from Nordpool sensor")
            return

        # Remove VAT from prices
        nordpool_prices_ex_vat = [float(price) / 1.25 for price in nordpool_prices]
        electricity_prices = bess.add_timestamps_and_prices(nordpool_prices_ex_vat)

        # Configure battery manager
        battery_manager.set_electricity_prices(electricity_prices)

        optimize_schedule()

        TOU_settings = growatt_schedule.get_daily_TOU_settings()

        # Apply TOU settings to inverter
        controller.disable_all_TOU_settings()

        # Apply battery-first segments
        for segment in TOU_settings:
            if segment["enabled"]:
                controller.set_inverter_time_segment(
                    segment_id=segment["segment_id"],
                    batt_mode=segment["batt_mode"],
                    start_time=segment["start_time"],
                    end_time=segment["end_time"],
                    enabled=True,
                )
    except Exception as e:
        log.error("Error preparing next day's schedule: %s", e)


def run_prepare_todays_daily_schedule() -> None:
    """Run at 23:55 to update TOU settings for next day."""
    log.info("Preparing next day's schedule")

    try:
        nordpool_prices = sensor.nordpool_kwh_se4_sek_2_10_025.today
        if not nordpool_prices:
            log.warning("No prices available from Nordpool sensor")
            return

        # Remove VAT from prices
        nordpool_prices_ex_vat = [float(price) / 1.25 for price in nordpool_prices]
        electricity_prices = bess.add_timestamps_and_prices(nordpool_prices_ex_vat)

        # Configure battery manager
        battery_manager.set_electricity_prices(electricity_prices)

        optimize_schedule()

        TOU_settings = growatt_schedule.get_daily_TOU_settings()

        # Apply TOU settings to inverter
        controller.disable_all_TOU_settings()

        # Apply battery-first segments
        for segment in TOU_settings:
            if segment["enabled"]:
                controller.set_inverter_time_segment(
                    segment_id=segment["segment_id"],
                    batt_mode=segment["batt_mode"],
                    start_time=segment["start_time"],
                    end_time=segment["end_time"],
                    enabled=True,
                )
    except Exception as e:
        log.error("Error preparing next day's schedule: %s", e)


@time_trigger("cron(0 * * * *)")
def run_hourly_task() -> None:
    """Run every hour to update inverter settings."""
    log.info("Running hourly task")

    # Apply hourly settings
    current_hour = datetime.now().hour

    hourly_settings = growatt_schedule.get_hourly_settings(current_hour)
    grid_charge_enabled = bool(hourly_settings["grid_charge"])
    discharge_rate = int(hourly_settings["discharge_rate"])
    log.info("Hourly settings for %s: grid_charge=%s, discharge_rate=%d", current_hour, grid_charge_enabled, discharge_rate)

    if current_hour < 5 or current_hour >= 0:
    # check if we should force charge the battery during night, despite arbitrage not profitable
        TOU_settings = growatt_schedule.get_daily_TOU_settings()
        if len(TOU_settings) == 1 and TOU_settings[0].get('batt_mode') == 'battery-first':
            log.info("No schedule set, force charging battery")
            grid_charge_enabled = True

    # Configure Growatt inverter hourly settings
    controller.set_grid_charge(grid_charge_enabled)
    controller.set_discharging_power_rate(discharge_rate)
