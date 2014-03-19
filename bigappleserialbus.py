#!/usr/bin/env python

import time
from busstop import BusStop
from onpi import onPi
import yaml

if onPi():
  import RPi.GPIO as GPIO
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(GREEN_LED, GPIO.OUT)
  GPIO.setup(RED_LED, GPIO.OUT)


config = yaml.load(open("config.yaml", 'r'))
bus_stops = []
for busName, info in config["stops"].items():
  stop = BusStop(busName, info["stop"], info["distance"], info["redPin"], info["greenPin"])
  bus_stops.append(stop)

betweenChecks = 60 #seconds

while True:
  pins = {}
  for bus in bus_stops:
    busCheck = bus.check()
    for pin, val in busCheck.items():
      pins[pin] = val
  for pin, val in pins.items():
    if onPi():
      GPIO.output(pin, val)
    if val:
      print("illuminating pin #%(pinNum)d" % {'pinNum': pin})
  time.sleep(betweenChecks)