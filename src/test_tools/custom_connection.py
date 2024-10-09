# This work is licensed under the MIT license.
# Copyright (c) 2013-2023 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
#
# Connect Example
#
# This example shows how to connect to a WiFi network.

import network
import time
from machine import LED

SSID = "WIFI-Amorth"  # Network SSID
KEY = "LitografiaAmorth-1967"  # Network key


led = LED("LED_GREEN")

for i in range(3):
    led.on()
    time.sleep_ms(100)
    led.off()
    time.sleep_ms(900)


# Init wlan module and connect to network
print("booting network.WLAN(network.STA_IF)")
wlan = network.WLAN(network.STA_IF)
print("booting wlan.active(True)")
wlan.active(True)
print("booting wlan.connect(SSID, KEY)")
wlan.connect(SSID, KEY)

while not wlan.isconnected():
    print('Trying to connect to "{:s}"...'.format(SSID))
    time.sleep_ms(1000)

# We should have a valid IP now via DHCP
print("WiFi Connected ", wlan.ifconfig())
