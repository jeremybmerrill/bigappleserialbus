#!/usr/bin/env python
from operator import itemgetter
import time
from busstop import BusStop
from onpi import is_on_pi
import yaml
import os
from ticker import Ticker
import traceback

from terminal_colors import green_code, red_code, yellow_code, blue_code, end_color

import logging
LOG_FILENAME = '/tmp/buses.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from busstop import Base



class BigAppleSerialBus:
  is_on_pi = False
  lights = {}

  #The MTA's bustime website pings every 15 seconds, so I feel comfortable doing the same.
  between_checks = 15 #seconds
  between_status_updates = 3 #seconds

  def __init__(self):
    self.is_on_pi = is_on_pi()
    self.__init_db__()
    self.bus_stops = []

    if self.is_on_pi:
      import RPi.GPIO as GPIO
      GPIO.setmode(GPIO.BCM)
      logging.debug("am running on a Raspberry Pi")

    self.__init_stops__()
    self.__cycle_lights__()
    self.__init_ticker__()

  def __init_stops__(self):
    config_file_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    config = yaml.load(open(config_file_path, 'r'))
    for info in sorted(config["stops"], cmp=lambda x, y: (-1 * cmp(x["stop"], y["stop"])) if x["route_name"] == y["route_name"] else cmp(x["route_name"], y["route_name"]) ):
      busName = info["route_name"]
      stop_id = info["stop"]
      #find or create stop
      stop = self.session.query(BusStop).filter(BusStop.stop_id == stop_id).filter(BusStop.route_name == busName).first()
      if not stop:
        stop = BusStop(busName, stop_id) #TODO: needs kwargs?
        self.session.add(stop)
      stop.add_attributes(info["distance"], self.session)

      self.bus_stops.append(stop)
      if self.is_on_pi:
        from light import Light
        #create the lights
        self.lights[stop] = {}
        self.lights[stop]['red'] = Light(info["redPin"])
        self.lights[stop]['green'] = Light(info["greenPin"])

  def check_buses(self):
    for stop in self.bus_stops:
      logging.debug("checking %(route_name)s (%(count)i buses on route)" % 
        {'route_name': stop.route_name, 'count': len(stop.buses_on_route) })
      trajectories = stop.check()
      for traj in [traj for traj in trajectories if traj]:
        self.session.add(traj)

      self.convert_to_lights(stop)
    self.session.commit()

  def broadcast_status(self):
    if self.is_on_pi:
      self.update_lights()
    print(' '.join([stop.status() for stop in self.bus_stops]))

  def convert_to_lights(self, bus_stop):
    if not self.is_on_pi:
      return
    if bus_stop.status_error:
      [light.toggle() for light in self.lights[bus_stop]]
    else:
      if bus_stop.bus_is_near:
        self.lights[bus_stop]['green'].on()
      else:
        self.lights[bus_stop]['green'].off()
      if bus_stop.bus_is_imminent:
        self.lights[bus_stop]['red'].on()
      else:
        self.lights[bus_stop]['red'].off()

  def update_lights(self):
    if not self.is_on_pi:
      return
    for bus_stop in self.bus_stops:
      self.convert_to_lights(bus_stop)

  def __init_db__(self):
    """do database crap"""
    engine = create_engine('sqlite:///buses.db') #only creates the file if it doesn't exist already
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
     
    DBSession = sessionmaker(bind=engine)
    self.session = DBSession()

  def __cycle_lights__(self):
    flat_lights = [item for sublist in [d.values() for d in self.lights.values()] for item in sublist]
    for light in flat_lights:
      light.on()
      time.sleep(2)
      light.off()

  def __init_ticker__(self):
    ticker = Ticker()
    ticker.register(self.check_buses, self.between_checks)
    ticker.register(self.broadcast_status, self.between_status_updates)
    ticker.global_error(self.__global_error__)
    ticker.start()

  def __global_error__(self, error):
    self.session.commit()
    logging.exception('Error:')
    if self.is_on_pi:
      light_pairs = self.lights.values()
      #turn off all the lights.
      for red_light in [light_pair['red'] for light_pair in light_pairs]:
        red_light.off()

      #then blink red to signal a global error condition
      while True:
        for red_light in [light_pair['red'] for light_pair in light_pairs]:
          red_light.on()
        time.sleep(5)
        for red_light in [light_pair['red'] for light_pair in light_pairs]:
          red_light.off()
        time.sleep(5)
    else:
      raise error

if __name__ == "__main__":
  BigAppleSerialBus()