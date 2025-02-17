# bess_controller.py

"""Home Assistant pyscript Battery Manager for Growatt Inverter/Battery."""

from datetime import datetime

from bess import BatterySystemManager, HomeAssistantController

# Initialize system with Home Assistant controller - will automatically use HANordpoolSource
controller = HomeAssistantController()
controller.set_test_mode(True) 
system = BatterySystemManager(controller=controller)


@time_trigger("startup")
def run_on_startup():
    """Run automatically on startup or reload."""
    try:
        current_hour = datetime.now().hour
        log.info("=" * 60)
        log.info(
            "BatteryManager startup - %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Initial schedule preparation and application
        schedule = system.prepare_schedule()
        if schedule:
            system.apply_schedule(current_hour)
            system.update_state(current_hour)
            log.info("Startup sequence completed successfully")
        else:
            log.error("Failed to create initial schedule")

        log.info("=" * 60)

    except Exception as e:
        log.error("Error during startup: %s", str(e))


@time_trigger("cron(0 * * * *)")
def run_hourly_adaptation():
    """Run every hour to update predictions and optimize if needed."""
    try:
        current_hour = datetime.now().hour
        log.info("Running hourly adaptation for hour %02d:00", current_hour)

        # Update state and re-optimize
        system.update_state(current_hour)
        schedule = system.prepare_schedule()
        if schedule:
            system.apply_schedule(current_hour)
        else:
            log.error("Failed to create schedule during hourly adaptation")

    except Exception as e:
        log.error("Error in hourly adaptation: %s", str(e))


@time_trigger("cron(*/15 * * * *)")
def run_battery_monitor():
    """Run every 15 minutes to verify inverter settings match schedule."""
    try:
        current_hour = datetime.now().hour
        system.verify_inverter_settings(current_hour)
    except Exception as e:
        log.error("Error in battery monitoring: %s", str(e))


@time_trigger("cron(*/5 * * * *)")
def periodic_power_monitoring():
    """Monitor power usage and adjust battery charging power to prevent blowing fuses."""
    try:
        system.adjust_charging_power()
    except Exception as e:
        log.error("Error in power monitoring: %s", str(e))


@time_trigger("cron(55 23 * * *)")
def prepare_next_day():
    """Prepare schedule for next day at 23:55."""
    try:
        log.info("Preparing next day's schedule")
        success = system.prepare_next_day_schedule()
        if success:
            log.info("Next day's schedule set successfully")
        else:
            log.warning("Failed to set next day's schedule")
    except Exception as e:
        log.error("Error preparing next day's schedule: %s", str(e))
