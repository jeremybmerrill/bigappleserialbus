#!/usr/bin/env python

__author__ = 'Jeremy B. Merrill'
__email__ = 'jeremybmerrill@gmail.com'
__license__ = 'Apache'
__version__ = '0.1'

import os
import json
import urllib2
from httplib import BadStatusLine
from datetime import datetime, timedelta
import time
from socket import error as SocketError
from bus import Bus
from trajectory import Trajectory, Base
from operator import attrgetter

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy import orm
# from sqlalchemy import create_engine
from terminal_colors import green_code, red_code, yellow_code, blue_code, end_color

import logging #magically the same as the one in bigappleserialbus.py

# write_bustime_responses_for_debug = False
from onpi import is_on_pi
write_bustime_responses_for_debug = False #is_on_pi()

read_bustime_data_from_disk = (not is_on_pi()) and len(os.listdir(os.path.join(os.path.dirname(__file__), '..', 'debugjson'))) > 65


time_to_get_ready = 240 # seconds
time_to_go = 180 #seconds
seconds_to_sidewalk = 60 #seconds

green_notice = green_code + "[green]" + end_color + " "
red_notice = red_code + "[red]" + end_color + " "
fail_notice = yellow_code + "[FAIL]" + end_color + " "
remove_notice = blue_code + "[removed]" + end_color + " "
apikey_path = os.path.join(os.path.dirname(__file__), "..", "apikey.txt")
mta_api_key = open(apikey_path, 'r').read().strip()

errors = {}

class TestCompleteException(Exception):
  pass 


# store in database green-light-on times and  actual arrival times
# to calculate avg error
class BusStop(Base):
  __tablename__ = 'bus_stop'
  stop_id = Column(String(10), primary_key=True)
  route_name = Column(String(250), nullable=False)
  mta_key = mta_api_key
  errors_serialized = Column(Text(), nullable=True)

  def __init__(self, route_name, stop_id):
    self.route_name = route_name
    self.stop_id = stop_id
    self.errors = []
    self.buses_on_route = {}
    self.previous_stops = [] #TODO: get these from the db somehow
    self.session_errors = []

  @orm.reconstructor
  def init_on_load(self):
    self.lineRef = "MTA NYCT_" + self.route_name.upper()
    self.buses_on_route = {}
    self.previous_stops = [] #TODO: get these from the db somehow
    if self.errors_serialized:
      self.errors = map(float, self.errors_serialized.split(","))
    else:
      self.errors = []
    self.session_errors = []

  def add_attributes(self, stop_seconds_away, session):
    """Set non-persistant variables."""
    print(stop_seconds_away, seconds_to_sidewalk )
    self.too_late_to_catch_the_bus = stop_seconds_away + seconds_to_sidewalk
    self.time_to_get_ready = stop_seconds_away + (time_to_get_ready + time_to_go) + seconds_to_sidewalk
    self.time_to_go = stop_seconds_away + time_to_go + seconds_to_sidewalk
    self.db_session = session
    self.bus_is_near = False
    self.bus_is_imminent = False
    self.status_error = False
    if read_bustime_data_from_disk:
      files_for_this_stop = [f for f in os.listdir(os.path.join(os.path.dirname(__file__), '..', 'debugjson')) if f.split('.')[0] == self.route_name and f.split('.')[1] == self.stop_id]
      self.test_json = [os.path.join(os.path.dirname(__file__), '..', 'debugjson', name) for name in sorted(files_for_this_stop, reverse=True)]

  def check(self):
    vehicle_activities, check_timestamp, success = self.get_locations()
    if not success:
      self.status_error
      logging.debug("get locatoins failed")
      return []
    self.bus_is_imminent = False
    self.bus_is_near = False
    new_buses = {}
    trajectories = []

    #populate new buses and add their position.
    for activity in vehicle_activities:
      journey = activity["MonitoredVehicleJourney"]

      vehicle_ref = journey["VehicleRef"]
      if vehicle_ref in self.buses_on_route:
        new_buses[vehicle_ref] = self.buses_on_route[vehicle_ref]
      else:
        new_buses[vehicle_ref] = Bus(vehicle_ref, journey, self.route_name, self.stop_id, self.db_session)
      active_bus = new_buses[vehicle_ref]

      active_bus.add_observed_position(journey, activity["RecordedAtTime"])
    logging.debug(self.route_name + " buses: " + ("["+', '.join(map(lambda x: repr(x), new_buses.values())) + "]" if new_buses.values() else "[]"))

    #for buses that just passed us (and that ever got close enough to have a projected arrival time):
    #TODO: some buses disappear mid-route because their transmitter malfunctions or they're stuck or something.
    #      we should keep track of these for a bit, rather than assuming that they're done...
    for bus_key, bus_past_stop in self.buses_on_route.items():
      if bus_key not in new_buses.keys():

        # when we never get a bus's data right when it arrives at the final stop, 
        # instead, it just disappears. We need to interpolate that last position
        # uses the latest recorded_at, because that's probably the best guess we have as to when the bus arrived at our stop.
        if vehicle_activities:
          most_recent_time = sorted([activity["RecordedAtTime"] for activity in vehicle_activities])[-1]
        else:
          most_recent_time = check_timestamp
        bus_past_stop.fill_in_last_stop(most_recent_time)
        if bus_past_stop.first_projected_arrival !=datetime.min:
          similar_error = bus_past_stop.first_projected_arrival - datetime.strptime(check_timestamp[0:19], "%Y-%m-%dT%H:%M:%S")
          speeds_error  = bus_past_stop.first_projected_arrival_speeds - datetime.strptime(check_timestamp[0:19], "%Y-%m-%dT%H:%M:%S")
          
          # ugh python's timedelta handling is awful.
          # you can't have negative seconds, so -4 seconds is -1 days and 86396 seconds.
          if similar_error.days < 0:
            similar_error = int(-(-similar_error).seconds)
          else:
            similar_error = int(similar_error.seconds)
          if speeds_error.days < 0:
            speeds_error = int(-(-speeds_error).seconds)
          else:
            speeds_error = int(speeds_error.seconds)

          self.errors.append(similar_error)
          self.session_errors.append(similar_error)
          avg_error = sum(self.errors) / len(self.errors)
          median_error = sorted(self.errors)[len(self.errors) / 2]

          error_early_late_speed = "early" if speeds_error > 0 else "late"
          error_early_late_sim = "early" if similar_error > 0 else "late"

          avg_early_late = "early" if avg_error > 0 else "late"
          median_early_late = "early" if median_error > 0 else "late"

          logging.debug(remove_notice + "original projection for %(veh)s was incorrect, bus was %(sec)f seconds %(early_late)s by speed; %(secsim)f %(earlylatesim)s by similarity" % 
              {'sec': int(abs(speeds_error)), 'early_late': error_early_late_speed, 'veh': bus_past_stop.number,
               'secsim': int(abs(similar_error)), 'earlylatesim': error_early_late_sim })
          logging.debug("bus %(name)s is, on average, %(avg_error)f seconds %(avg_early_late)s; median %(med)f %(median_early_late)s" % 
            {'avg_error': int(abs(avg_error)), 'name': self.route_name, 'med': int(abs(median_error)), 
            'avg_early_late': avg_early_late, 'median_early_late': median_early_late})
          # logging.debug( self.errors)
          bus_past_stop.error = similar_error
        bus_trajectory = bus_past_stop.convert_to_trajectory(self.route_name, self.stop_id)
        print("appending trajectory in stop", bus_trajectory)
        trajectories.append(bus_trajectory) #calculate the right columns.
    
    self.buses_on_route = new_buses
    for vehicle_ref, bus in self.buses_on_route.items():
      similar_trajectories = bus.find_similar_trajectories()

      similar_seconds_away = similar_trajectories['seconds_away']
      speeds_seconds_away = bus.get_seconds_away() # instant speed-based: str(bus.get_minutes_away())[2:7]

      minutes_away = seconds_to_minutes(similar_seconds_away)
      meters_away = bus.get_meters_away()
      miles_away = meters_to_miles(meters_away)
      mph = bus.get_speed_mph()

      if similar_seconds_away <= -1:
        # it might be the case that this is the first trajectory we've seen for this bus! save it.
        continue
      else:
        logging.debug("bus %(name)s/%(veh)s: %(secsim)s away from %(cnt)i similar trajectories" % 
          {'name': self.route_name, 'secsim': str(seconds_to_minutes(similar_seconds_away))[2:8],
           'cnt':len(similar_trajectories['similar']), 'veh': vehicle_ref })

      if similar_seconds_away < self.too_late_to_catch_the_bus:
        # too close, won't make it.
        logging.debug(fail_notice + "bus %(name)s/%(veh)s is %(dist)fmi away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': miles_away, 'speed': mph, 'mins': minutes_away, 
            'now': check_timestamp[11:19], 'veh': vehicle_ref
          })
        bus.too_late()
        continue
      if similar_seconds_away < self.time_to_go:
        self.bus_is_imminent = True
        bus.imminent()
        logging.debug(red_notice + "bus %(name)s/%(veh)s is %(dist)fmi away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': miles_away, 'speed': mph, 'mins': minutes_away, 
            'now': check_timestamp[11:19], 'veh': vehicle_ref
          })
        if bus.first_projected_arrival == datetime.min:
          bus.first_projected_arrival = datetime.strptime(check_timestamp[0:19], "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=similar_seconds_away)
          bus.first_projected_arrival_speeds = datetime.strptime(check_timestamp[0:19], "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=speeds_seconds_away)
        continue 
        # if a bus is within Time_to_go, it's necessarily within Time_to_get_ready, but I don't 
        # want it to trip the green pin too
      if similar_seconds_away < self.time_to_get_ready:
        logging.debug(green_notice + "bus %(name)s/%(veh)s is %(dist)fmi away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': miles_away, 'speed': mph, 'mins': minutes_away, 
            'now': check_timestamp[11:19], 'veh': vehicle_ref
          })
        self.bus_is_near = True
        bus.near()
        # but if a second bus is close, I do want the green to go
        # even if there's a red bus nearby.

        #for calculating error:
        if bus.first_projected_arrival == datetime.min:
          bus.first_projected_arrival = datetime.strptime(check_timestamp[0:19], "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=similar_seconds_away)
          bus.first_projected_arrival_speeds = datetime.strptime(check_timestamp[0:19], "%Y-%m-%dT%H:%M:%S") + timedelta(seconds=speeds_seconds_away)

    logging.debug(self)
    self.prep_for_writing()
    return trajectories

  def prep_for_writing(self):
    #TODO: figure out a cleaner way to do this.
    self.errors = filter(lambda x: abs(x) < 3000, self.errors) #errors that big are spurious
    self.errors_serialized = ','.join(map(str, self.errors))

  def get_locations(self):
    # line
    # http://api.prod.obanyc.com/api/siri/stop-monitoring.json?key=whatever&LineRef=MTA%20NYCT_B65
    # stop
    # http://api.prod.obanyc.com/api/siri/stop-monitoring.json?key=whatever&MonitoringRef=306495&LineRef=MTA%20NYCT_B65

    requestUrl = "http://bustime.mta.info/api/siri/stop-monitoring.json?key=%(key)s&OperatorRef=MTA&MonitoringRef=%(stop)s&StopMonitoringDetailLevel=%(onw)s" %\
            {'key': self.mta_key, 'stop': self.stop_id, 'onw': 'calls'}
    # logging.debug("locations: " + requestUrl)
    resp = None
    if read_bustime_data_from_disk:
      try:
        print(len(self.test_json))
        with open(self.test_json.pop(), 'r') as jsonfile:
          resp = json.loads(jsonfile.read())
      except IndexError:
        raise TestCompleteException("test finished successfully")
    else: 
      for i in xrange(0,4):
        try:
          response = urllib2.urlopen(requestUrl)
          #this only happens if the attempt to get the data fails 4 times.
          if not response:
            raise urllib2.URLError("Couldn't reach BusTime servers...")

          jsonresp = response.read()
          try: 
            resp = json.loads(jsonresp)
          except ValueError:
            raise urllib2.URLError("Bad JSON: " + jsonresp)
          except Exception as e:
            raise e
          finally:
            if i > 0:
              logging.debug("getting data failed before, but worked this time")
            break
        except (urllib2.URLError, SocketError, BadStatusLine) as e: 
          logging.debug("getting data failed, trying again (%(i)i/4)" % {'i': i+1})
          response = None
          resp = None
          if i == 3:
            logging.debug("getting data failed 4 times (except->if branch)")
            return (None, None, False)
          time.sleep(10 * i)
      else:
        logging.debug("getting data failed 4 times (else branch)")
        return (None, None, False)
    try:
      vehicle_activities = resp["Siri"]["ServiceDelivery"]["StopMonitoringDelivery"][0]["MonitoredStopVisit"]
    except Exception as e:
      logging.debug(resp)
      raise e
    try:
      check_timestamp = resp["Siri"]["ServiceDelivery"]["ResponseTimestamp"]
    except Exception as e:
      logging.debug(resp)
      raise e

    if write_bustime_responses_for_debug:
      filename = self.route_name + "." + self.stop_id + "." + check_timestamp + ".json"
      filepath = os.path.join(os.path.dirname(__file__), "..", "debugjson", filename)
      with open(filepath, 'w') as f:
        f.write(jsonresp)
    return (vehicle_activities, check_timestamp, True)

  def status(self):
    if self.status_error:
      return yellow_code + "!!" + end_color
    line = ''
    if self.bus_is_imminent:
      line += red_code + 'R' + end_color
    else:
      line += '-'
    if self.bus_is_near:
      line += green_code + 'G' + end_color
    else:
      line += '-'
    return line

  def __repr__(self):
    return "<BusStop %(route)s #%(number)s %(status)s >" % {"route" : self.route_name, "number" : self.stop_id, 'status': self.status() }

  # potentially dead code.
  def set_previous_calls(self, journey):
    for onward_call in journey["OnwardCalls"]:
      # "Extensions": {
      #     "Distances": {
      #         "PresentableDistance": "1 stop away",
      #         "DistanceFromCall": 229.5,
      #         "StopsFromCall": 1,
      #         "CallDistanceAlongRoute": 229.49
      #     }
      # },
      # "StopPointRef": "MTA_301067",
      # "VisitNumber": 1,
      # "StopPointName": "BUFFALO AV/ST JOHNS PL"
      stop_ref = onward_call["StopPointRef"]
      if stop_ref not in self.previous_stops:
        self.previous_stops.append(IntermediateStop(self.route_name, stop_ref, onward_call["StopPointName"]))
    #stash to DB

# also potentially dead code
# class IntermediateStop(BusStop):
#   __tablename__ = 'intermediate_stop'
#   # stop_id = Column(String(10), primary_key=True)
#   # route_name = Column(String(250), nullable=False)
#   # mta_key = mta_api_key
#   # errors_serialized = Column(Text(), nullable=True)
#   stop_name = Column(String(250), nullable=False)

#   # whenever one is created, note the estimated time til bus_stop
#   # and whenever a bus arrives at the relevant stop, calculate error and stash it

def meters_to_miles(meters):
  return meters / 1609.34


def seconds_to_minutes(seconds):
  return timedelta(seconds=seconds)
