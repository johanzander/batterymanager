"""Provides helper functions to interact with InfluxDB for fetching sensor data.

The module includes functionality to parse responses, handle timezones, and process sensor readings.
This module is designed to run within the Pyscript environment.
"""

from datetime import datetime
import logging
from zoneinfo import ZoneInfo

import requests

_LOGGER = logging.getLogger(__name__)


def get_sensor_data(sensors_list, end_time=None):
    """Get sensor data for each hour of today with incremental values for cumulative sensors."""
    # Set up timezone
    local_tz = ZoneInfo("Europe/Stockholm")

    # Determine end time
    if end_time is None:
        end_time = datetime.now(local_tz)
    elif end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=local_tz)

    try:
        # Try to get from Home Assistant configuration
        influxdb_config = pyscript.config.get("influxdb", {})  # type: ignore  # noqa: PGH003
    except (NameError, AttributeError) as e:
        # Log the error and return if we can't access pyscript config
        _LOGGER.error(
            "Failed to access pyscript config: %s, using default InfluxDB settings", e
        )
        return {"status": "error", "message": "Failed to access configuration"}

    url = influxdb_config.get("url", "")
    username = influxdb_config.get("username", "")
    password = influxdb_config.get("password", "")

    # Validate required configuration
    if not url or not username or not password:
        _LOGGER.error(
            "InfluxDB configuration is incomplete. URL: %s, Username: %s",
            url,
            username,
        )
        return {"status": "error", "message": "Incomplete InfluxDB configuration"}

    headers = {
        "Content-type": "application/vnd.flux",
        "Accept": "application/csv",
    }

    # Format times for InfluxDB query
    end_str = end_time.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    sensor_filter = " or ".join(
        [f'r["_measurement"] == "sensor.{sensor}"' for sensor in sensors_list]
    )

    # Query each sensor separately to get all readings between start and end
    flux_query = f"""from(bucket: "home_assistant/autogen")
                    |> range(start: 0, stop: {end_str})
                    |> filter(fn: (r) => {sensor_filter})
                    |> filter(fn: (r) => r["_field"] == "value")
                    |> filter(fn: (r) => r["domain"] == "sensor")
                    |> last()
                    """

    response = task.executor(  # noqa: F821, PGH003 # type: ignore
        requests.post,
        url=url,
        auth=(username, password),
        headers=headers,
        data=flux_query,
        timeout=10,
    )

    if response.status_code == 204:
        _LOGGER.warning("No data found for the requested sensors")
        return {}

    if response.status_code != 200:
        _LOGGER.error("Error from InfluxDB: %s", response.status_code)
        return {}

    sensor_readings = parse_influxdb_response(response.text)
    return {"status": "success", "data": sensor_readings}


def parse_influxdb_response(response_text):
    """Parse InfluxDB response to extract the latest measurement for each sensor."""
    readings = {}
    lines = response_text.strip().split("\n")

    # Skip metadata rows (lines starting with '#')
    data_lines = [line for line in lines if not line.startswith("#")]

    # Process each data line
    for line in data_lines:
        parts = line.split(",")
        try:
            # Ensure the line has enough parts and the value can be converted to float
            if len(parts) < 9 or parts[6] == "_value":
                continue

            # Extract sensor name (_measurement) and value (_value)
            sensor_name = parts[
                10
            ].strip()  # _measurement is the 11th column (index 10)
            value = float(parts[6].strip())  # _value is the 7th column (index 6)

            # Store the value in the readings dictionary with the sensor name
            readings[sensor_name] = value
        except (IndexError, ValueError) as e:
            _LOGGER.error("Failed to parse line: %s, error: %s", line, e)
            continue

    _LOGGER.debug("Parsed response: %s", readings)
    return readings
