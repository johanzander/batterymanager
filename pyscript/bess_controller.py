"""Home Assistant pyscript Battery Manager for Growatt Inverter/Battery."""

from datetime import datetime

from bess import BatterySystemManager, HomeAssistantController

TEST_MODE = True

# Let the user know
log.info(
    "Starting BESS Controller, test mode: %s", "ENABLED" if TEST_MODE else "DISABLED"
)

# Initialize controller
controller = HomeAssistantController()
controller.set_test_mode(TEST_MODE)

# Create the system
system = BatterySystemManager(controller=controller)


@time_trigger("startup")
def run_on_startup():
    """Run automatically on startup or reload."""
    current_hour = datetime.now().hour
    log.info("BatteryManager startup - Current hour: %d:00", current_hour)

    success = system.update_battery_schedule(current_hour)
    if not success:
        log.warning("Failed to create initial schedule")


@time_trigger("cron(0 * * * *)")
def run_hourly_adaptation():
    """Run every hour to update system and optimize if needed."""
    system.update_battery_schedule(datetime.now().hour)


@time_trigger("cron(55 23 * * *)")
def prepare_next_day():
    """Prepare schedule for next day at 23:55."""
    success = system.update_battery_schedule(datetime.now().hour, prepare_next_day=True)
    if not success:
        log.warning("Failed to set next day's schedule")


@time_trigger("cron(*/15 * * * *)")
def run_battery_monitor():
    """Run every 15 minutes to verify inverter settings match schedule."""
    system.verify_inverter_settings(datetime.now().hour)


@time_trigger("cron(*/5 * * * *)")
def periodic_power_monitoring():
    """Monitor power usage and adjust battery charging power to prevent blowing fuses."""
    system.adjust_charging_power()
