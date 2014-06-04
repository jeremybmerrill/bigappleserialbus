import os
import json
import urllib2
from httplib import BadStatusLine
from datetime import datetime, timedelta
import time
from socket import error as SocketError
from bus import Bus
from trajectory import Trajectory, Base


from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy import orm
# from sqlalchemy import create_engine


time_to_get_ready = 240 # seconds
time_to_go = 180 #seconds
seconds_to_sidewalk = 60 #seconds

greencode = '\033[92m'
redcode = '\033[91m'
yellowcode = '\033[93m'
bluecode = "\033[34m"
endcolor = '\033[0m'

green_notice = greencode + "[green]" + endcolor + " "
red_notice = redcode + "[red]" + endcolor + " "
fail_notice = yellowcode + "[FAIL]" + endcolor + " "
remove_notice = bluecode + "[removed]" + endcolor + " "
apikey_path = os.path.join(os.path.dirname(__file__), "apikey.txt")
mta_api_key = open(apikey_path, 'r').read().strip()

errors = {}


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

  @orm.reconstructor
  def init_on_load(self):
    self.lineRef = "MTA NYCT_" + self.route_name.upper()
    self.buses_on_route = {}
    self.previous_stops = [] #TODO: get these from the db somehow
    if self.errors_serialized:
      self.errors = map(float, self.errors_serialized.split(","))
    else:
      self.errors = []

  # non-persistant attributes
  def add_attributes(self, stop_seconds_away, red_pin, green_pin, session):
    self.red_pin = red_pin
    self.green_pin = green_pin
    self.too_late_to_catch_the_bus = stop_seconds_away + seconds_to_sidewalk
    self.time_to_get_ready = stop_seconds_away + (time_to_get_ready + time_to_go) + seconds_to_sidewalk
    self.time_to_go = stop_seconds_away + time_to_go + seconds_to_sidewalk
    self.db_session = session

    #get previous stops using "&StopMonitoringDetailLevel=calls"


  def check(self):
    vehicle_activities = self.get_locations()
    turn_on_red_pin = False
    turn_on_green_pin = False
    new_buses = {}
    trajectories = []
    for activity in vehicle_activities:
      journey = activity["MonitoredVehicleJourney"]

      #TODO: unless we have all of them.
      # self.set_previous_calls(journey)

      vehicle_ref = journey["VehicleRef"]
      if vehicle_ref in self.buses_on_route:
        new_buses[vehicle_ref] = self.buses_on_route[vehicle_ref]
      else:
        new_buses[vehicle_ref] = Bus(vehicle_ref, journey, self.route_name, self.db_session)
      active_bus = new_buses[vehicle_ref]

      active_bus.add_observed_position(journey, activity["RecordedAtTime"])
    print( map(lambda b: b.number, new_buses.values()))

    for bus_key, bus in self.buses_on_route.items():
      #for buses that just passed us (and that ever got close enough to have a projected arrival time):
      if bus_key not in new_buses.keys() and bus.first_projected_arrival != 0.0:
        similar_error = bus.first_projected_arrival - time.time()
        speeds_error  = bus.first_projected_arrival_speeds - time.time()
        #TODO: lol, when my comptuer goes to sleep, it picks up when it's done, so we get unrealistic errors

        # if self.route_name not in errors:
        #   errors[self.route_name] = {}
        # errors[self.route_name][vehicle_ref] = error
        # print(errors[self.route_name].values())
        self.errors.append(speeds_error)
        avg_error = sum(self.errors) / len(self.errors)
        median_error = sorted(self.errors)[len(self.errors) / 2]


        error_early_late_speed = "early" if speeds_error > 0 else "late"
        error_early_late_sim = "early" if similar_error > 0 else "late"

        avg_early_late = "early" if avg_error > 0 else "late"
        median_early_late = "early" if median_error > 0 else "late"

        print(remove_notice + "original projection for %(veh)s was incorrect, bus was %(sec)f seconds %(early_late)s by speed; %(secsim)f %(earlylatesim)s by similarity" % 
            {'sec': int(abs(speeds_error)), 'early_late': error_early_late_speed, 'veh': bus.number,
             'secsim': int(abs(similar_error)), 'earlylatesim': error_early_late_sim })
        print("bus %(name)s is, on average, %(avg_error)f seconds %(avg_early_late)s; median %(med)f %(median_early_late)s" % 
          {'avg_error': int(abs(avg_error)), 'name': self.route_name, 'med': int(abs(median_error)), 
          'avg_early_late': avg_early_late, 'median_early_late': median_early_late})
        # print self.errors
        trajectories.append(bus.convert_to_trajectory(self.route_name, self.stop_id)) #calculate the right columns.
    self.buses_on_route = new_buses


    for vehicle_ref, bus in self.buses_on_route.items():
      speeds_seconds_away = bus.get_seconds_away()
      minutes_away = str(bus.get_minutes_away())[2:7]
      meters_away = bus.get_meters_away()
      miles_away = meters_to_miles(meters_away)
      speed = bus.get_speed_mps()
      mph = bus.get_speed_mph()

      similar_trajectories = bus.find_similar_trajectories()
      similar_seconds_away = similar_trajectories['seconds_away']
      print("bus %(name)s: %(sec)i secs away; %(secsim)i secs away from %(cnt)i similar trajectories" % 
        {'name': self.route_name, 'sec': speeds_seconds_away, 'secsim': similar_seconds_away,
         'cnt':len(similar_trajectories['similar']) } )

      if speeds_seconds_away < self.too_late_to_catch_the_bus:
        # too close, won't make it.
        print(fail_notice + "bus %(name)s/%(veh)s is %(dist)fmi away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': miles_away, 'speed': mph, 'mins': minutes_away, 
            'now': str(datetime.now().time())[0:8], 'veh': vehicle_ref
          })
        continue
      if speeds_seconds_away < self.time_to_go:
        turn_on_red_pin = True
        print(red_notice + "bus %(name)s/%(veh)s is %(dist)fmi away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': miles_away, 'speed': mph, 'mins': minutes_away, 
            'now': str(datetime.now().time())[0:8], 'veh': vehicle_ref
          })
        if bus.first_projected_arrival == 0.0:
          bus.first_projected_arrival = time.time() + similar_seconds_away
          bus.first_projected_arrival_speeds = time.time() + speeds_seconds_away
        continue 
        # if a bus is within Time_to_go, it's necessarily within Time_to_get_ready, but I don't 
        # want it to trip the green pin too
      if speeds_seconds_away < self.time_to_get_ready:
        print(green_notice + "bus %(name)s/%(veh)s is %(dist)fmi away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': miles_away, 'speed': mph, 'mins': minutes_away, 
            'now': str(datetime.now().time())[0:8], 'veh': vehicle_ref
          })
        turn_on_green_pin = True
        # but if a second bus is close, I do want the green to go
        # even if there's a red bus nearby.

        #for calculating error:
        if bus.first_projected_arrival == 0.0:
          bus.first_projected_arrival = time.time() + similar_seconds_away
          bus.first_projected_arrival_speeds = time.time() + speeds_seconds_away
    self.prep_for_writing()
    return ({self.green_pin: turn_on_green_pin, self.red_pin: turn_on_red_pin}, trajectories)

  def prep_for_writing(self):
    #TODO: remove
    self.errors_serialized = ','.join(map(str, self.errors))

  def get_locations(self):
    # line
    # http://api.prod.obanyc.com/api/siri/stop-monitoring.json?key=whatever&LineRef=MTA%20NYCT_B65
    # stop
    # http://api.prod.obanyc.com/api/siri/stop-monitoring.json?key=whatever&MonitoringRef=306495&LineRef=MTA%20NYCT_B65

    requestUrl = "http://bustime.mta.info/api/siri/stop-monitoring.json?key=%(key)s&OperatorRef=MTA&MonitoringRef=%(stop)s&StopMonitoringDetailLevel=%(onw)s" %\
            {'key': self.mta_key, 'stop': self.stop_id, 'onw': 'calls'}
    for i in xrange(0,4):
      try:
        response = urllib2.urlopen(requestUrl)
        break
      except (urllib2.URLError, SocketError, BadStatusLine):
        response = None
        time.sleep(10)

    if not response:
      raise urllib2.URLError("Couldn't reach BusTime servers...")

    jsonresp = response.read()
    resp = json.loads(jsonresp)
    return resp["Siri"]["ServiceDelivery"]["StopMonitoringDelivery"][0]["MonitoredStopVisit"]

  def __repr__(self):
    return "<BusStop %(route)s #%(stop_id)s >" % {"route" : self.route_name, "number" : self.stop_id }


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