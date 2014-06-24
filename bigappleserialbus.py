#!/usr/bin/env python

import time
from busstop import BusStop
from onpi import is_on_pi
import yaml
import os

import logging
LOG_FILENAME = '/tmp/buses.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from busstop import Base

if __name__ == "__main__":

  #database crap
  engine = create_engine('sqlite:///buses.db') #only creates the file if it doesn't exist already
  Base.metadata.create_all(engine)
  Base.metadata.bind = engine
   
  DBSession = sessionmaker(bind=engine)
  session = DBSession()

  am_on_pi = is_on_pi()

  if am_on_pi:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    print("am running on a Raspberry Pi")

  config_file_path = os.path.join(os.path.dirname(__file__), "config.yaml")
  config = yaml.load(open(config_file_path, 'r'))
  bus_stops = []
  for busName, info in config["stops"].items():
    stop_id = info["stop"]
    #find or create stop
    stop = session.query(BusStop).filter(BusStop.stop_id == stop_id).filter(BusStop.route_name == busName).first()
    if not stop:
      stop = BusStop(busName, stop_id) #TODO: needs kwargs?
      session.add(stop)
    stop.add_attributes(info["distance"], info["redPin"], info["greenPin"], session)

    bus_stops.append(stop)
    if am_on_pi:
      GPIO.setup(stop.green_pin, GPIO.OUT)
      GPIO.setup(stop.red_pin, GPIO.OUT)

      #cycle the lights.
      GPIO.output(stop.red_pin, True)
      time.sleep(2)
      GPIO.output(stop.red_pin, False)
      GPIO.output(stop.green_pin, True)
      time.sleep(2)
      GPIO.output(stop.green_pin, False)

  #The MTA's bustime website pings every 15 seconds, so I feel comfortable doing the same.
  betweenChecks = 15 #seconds

  while True:
    try:
      start_time = time.time()
      pins = {}
      for stop in bus_stops:
        print("checking %(route_name)s (%(count)i buses on route)" % 
          {'route_name': stop.route_name, 'count': len(stop.buses_on_route) })
        busCheck, trajectories = stop.check()
        for traj in [traj for traj in trajectories if traj]:
          session.add(traj)
        for pin, val in busCheck.items():
          pins[pin] = val
      for pin, val in pins.items():
        if am_on_pi:
          GPIO.output(pin, val)
        if val:
          if am_on_pi:
            print("illuminating pin #%(pinNum)d" % {'pinNum': pin})
          # else:
          #   print("would illuminate pin #%(pinNum)d" % {'pinNum': pin})
      session.commit()
      duration = time.time() - start_time
      time.sleep(max(betweenChecks - duration, 0))
    except:
      session.commit()
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
          time.sleep(5)
          for stop in bus_stops:
            GPIO.output(stop.red_pin, False)
          time.sleep(5)
      else:
        raise
        break
