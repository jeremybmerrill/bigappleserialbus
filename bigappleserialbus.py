#!/usr/bin/env python

import time
from busstop import BusStop
from onpi import is_on_pi
import yaml

am_on_pi = is_on_pi()

if am_on_pi:
  import RPi.GPIO as GPIO
  GPIO.setmode(GPIO.BCM)
  print("am running on a Raspberry Pi")


config = yaml.load(open("config.yaml", 'r'))
bus_stops = []
for busName, info in config["stops"].items():
  stop = BusStop(busName, info["stop"], info["distance"], info["redPin"], info["greenPin"])
  bus_stops.append(stop)
  if am_on_pi:
    GPIO.setup(stop.green_pin, GPIO.OUT)
    GPIO.setup(stop.red_pin, GPIO.OUT)


betweenChecks = 60 #seconds

while True:
  pins = {}
  for bus in bus_stops:
    print("checking " + bus.route_name)
    busCheck = bus.check()
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