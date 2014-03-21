#!/usr/bin/env python

import time
from busstop import BusStop
from onpi import is_on_pi
import yaml
import os

am_on_pi = is_on_pi()

if am_on_pi:
  import RPi.GPIO as GPIO
  GPIO.setmode(GPIO.BCM)
  print("am running on a Raspberry Pi")

config_file_path = os.path.join(os.path.dirname(__file__), "config.yaml")
config = yaml.load(open(config_file_path, 'r'))
bus_stops = []
for busName, info in config["stops"].items():
  stop = BusStop(busName, info["stop"], info["distance"], info["redPin"], info["greenPin"])
  bus_stops.append(stop)
  if am_on_pi:
    GPIO.setup(stop.green_pin, GPIO.OUT)
    GPIO.setup(stop.red_pin, GPIO.OUT)

    #cycle the lights.
    GPIO.output(stop.green_pin, True)
    time.sleep(2)
    GPIO.output(stop.green_pin, False)
    GPIO.output(stop.red_pin, True)
    time.sleep(2)
    GPIO.output(stop.red_pin, False)


betweenChecks = 60 #seconds

while True:
  try:
    pins = {}
    for stop in bus_stops:
      print("checking " + stop.route_name)
      busCheck = stop.check()
      for pin, val in busCheck.items():
        pins[pin] = val
    for pin, val in pins.items():
      if am_on_pi:
        GPIO.output(pin, val)
      if val:
        if am_on_pi:
          print("illuminating pin #%(pinNum)d" % {'pinNum': pin})
        else:
          print("would illuminate pin #%(pinNum)d" % {'pinNum': pin})
    time.sleep(betweenChecks)
  except:
    #turn off all the lights.
    if am_on_pi:
      for stop in bus_stops:
        GPIO.output(stop.green_pin, False)
        GPIO.output(stop.red_pin, False)
    raise