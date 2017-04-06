from __future__ import print_function

import datetime
import sys
import time

from bluepy.btle import BTLEException
from bluepy.sensortag import SensorTag


# configurations to be set accordingly


def enable_sensors(tag):
    """Enable sensors so that readings can be made."""
    tag.IRtemperature.enable()
    tag.accelerometer.enable()
    tag.humidity.enable()
    tag.magnetometer.enable()
    tag.barometer.enable()
    tag.gyroscope.enable()
    tag.keypress.enable()
    tag.lightmeter.enable()
    # tag.battery.enable()

    # Some sensors (e.g., temperature, accelerometer) need some time for initialization.
    # Not waiting here after enabling a sensor, the first read value might be empty or incorrect.
    time.sleep(1.0)

def disable_sensors(tag):
    """Disable sensors to improve battery life."""
    tag.IRtemperature.disable()
    tag.accelerometer.disable()
    tag.humidity.disable()
    tag.magnetometer.disable()
    tag.barometer.disable()
    tag.gyroscope.disable()
    tag.keypress.disable()
    tag.lightmeter.disable()
    # tag.battery.disable()


def get_readings(tag):
    """Get sensor readings and collate them in a dictionary."""
    try:
        enable_sensors(tag)
        readings = {}
        # IR sensor
        readings["ir_temp"], readings["ir"] = tag.IRtemperature.read()
        # humidity sensor
        readings["humidity_temp"], readings["humidity"] = tag.humidity.read()
        # barometer
        readings["baro_temp"], readings["pressure"] = tag.barometer.read()
        # luxmeter
        readings["light"] = tag.lightmeter.read()
        # battery
        # readings["battery"] = tag.battery.read()
        disable_sensors(tag)

        # round to 2 decimal places for all readings
        readings = {key: round(value, 2) for key, value in readings.items()}
        return readings

    except BTLEException as e:
        print("Unable to take sensor readings.")
        print(e)
        return {}


def reconnect(tag):
    try:
        tag.connect(tag.deviceAddr, tag.addrType)

    except Exception as e:
        print("Unable to reconnect to SensorTag.")
        raise e

    
