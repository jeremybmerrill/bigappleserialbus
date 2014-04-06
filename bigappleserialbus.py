#!/usr/bin/env python

import time
from busstop import BusStop
from onpi import is_on_pi
import yaml
import os

import logging
LOG_FILENAME = '/tmp/buses.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,)

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


#The MTA's bustime website pings every 15 seconds, so I feel comfortable doing the same.
betweenChecks = 15 #seconds

while True:
  try:
    start_time = time.time()
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
    duration = time.time() - start_time
    time.sleep(max(betweenChecks - duration, 0))
  except:
    if am_on_pi:
      #turn off all the lights.
      for stop in bus_stops:
        GPIO.output(stop.green_pin, False)
        GPIO.output(stop.red_pin, True)
      logging.exception('Got exception on main handler')

      #then blink red to signal an error condition
      while True:
        for stop in bus_stops:
          GPIO.output(stop.red_pin, True)
        time.sleep(1)
        for stop in bus_stops:
          GPIO.output(stop.red_pin, False)
        time.sleep(1)
