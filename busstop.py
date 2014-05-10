import os
import json
import urllib2
from datetime import datetime, timedelta
import time

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import orm
# from sqlalchemy import create_engine

Base = declarative_base()

time_to_get_ready = 240 # seconds
time_to_go = 180 #seconds
seconds_to_sidewalk = 60 #seconds
default_bus_speed = 4 # m/s ~= 8 miles per hour

distance_to_track = 20

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

  @orm.reconstructor
  def init_on_load(self):
    self.lineRef = "MTA NYCT_" + self.route_name.upper()
    self.buses_on_route = {}
    if self.errors_serialized:
      self.errors = map(float, self.errors_serialized.split(","))
    else:
      self.errors = []

  # non-persistant attributes
  def add_attributes(self, stop_seconds_away, red_pin, green_pin):
    self.red_pin = red_pin
    self.green_pin = green_pin
    self.too_late_to_catch_the_bus = stop_seconds_away + seconds_to_sidewalk
    self.time_to_get_ready = stop_seconds_away + (time_to_get_ready + time_to_go) + seconds_to_sidewalk
    self.time_to_go = stop_seconds_away + time_to_go + seconds_to_sidewalk


  def check(self):
    vehicle_activities = self.get_locations()
    turn_on_red_pin = False
    turn_on_green_pin = False
    new_buses = {}
    for activity in vehicle_activities:
      journey = activity["MonitoredVehicleJourney"]
      distance_from_call = journey["MonitoredCall"]["Extensions"]["Distances"]["DistanceFromCall"] # meters, it turns out

      vehicle_ref = journey["VehicleRef"]
      if vehicle_ref in self.buses_on_route:
        new_buses[vehicle_ref] = self.buses_on_route[vehicle_ref]
      else:
        new_buses[vehicle_ref] = Bus(vehicle_ref)
      active_bus = new_buses[vehicle_ref]
      active_bus.add_observed_position(activity["RecordedAtTime"], distance_from_call)
    
    print(map(lambda b: b.number, self.buses_on_route.values()), map(lambda b: b.number, new_buses.values()))

    for bus_key, bus in self.buses_on_route.items():
      #for buses that just passed us:
      if bus_key not in new_buses.keys() and bus.first_projected_arrival != 0.0:
        error = bus.first_projected_arrival - time.time()
        #TODO: lol, when my comptuer goes to sleep, it picks up when it's done, so we get unrealistic errors

        # if self.route_name not in errors:
        #   errors[self.route_name] = {}
        # errors[self.route_name][vehicle_ref] = error
        # print(errors[self.route_name].values())
        self.errors.append(error)
        avg_error = sum(self.errors) / len(self.errors)
        median_error = sorted(self.errors)[len(self.errors) / 2]


        error_early_late = "early" if error > 0 else "late"
        avg_early_late = "early" if avg_error > 0 else "late"
        median_early_late = "early" if median_error > 0 else "late"

        print(remove_notice + "original projection for %(veh)s was incorrect, bus was %(sec)f seconds %(early_late)s" % 
            {'sec': int(abs(error)), 'early_late': error_early_late, 'veh': bus.number})
        print("bus %(name)s is, on average, %(avg_error)f seconds %(avg_early_late)s; median %(med)f %(median_early_late)s" % 
          {'avg_error': int(abs(avg_error)), 'name': self.route_name, 'med': int(abs(median_error)), 
          'avg_early_late': avg_early_late, 'median_early_late': median_early_late})
        print self.errors

    self.buses_on_route = new_buses


    for vehicle_ref, bus in self.buses_on_route.items():
      seconds_away = bus.get_seconds_away()
      minutes_away = str(bus.get_minutes_away())[2:7]
      metersAway = bus.get_meters_away()
      speed = bus.get_speed_mps()
      mph = bus.get_speed_mph()

      if seconds_away < self.too_late_to_catch_the_bus:
        # too close, won't make it.
        print(fail_notice + "bus %(name)s/%(veh)s is %(dist)fm away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': metersAway, 'speed': mph, 'mins': minutes_away, 
            'now': str(datetime.now().time())[0:8], 'veh': vehicle_ref
          })
        continue
      if seconds_away < self.time_to_go:
        turn_on_red_pin = True
        print(red_notice + "bus %(name)s/%(veh)s is %(dist)fm away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': metersAway, 'speed': mph, 'mins': minutes_away, 
            'now': str(datetime.now().time())[0:8], 'veh': vehicle_ref
          })
        continue 
        # if a bus is within Time_to_go, it's necessarily within Time_to_get_ready, but I don't 
        # want it to trip the green pin too
      if seconds_away < self.time_to_get_ready:
        print(green_notice + "bus %(name)s/%(veh)s is %(dist)fm away, traveling at %(speed)f mph; computed to be %(mins)s away at %(now)s" % 
          {'name': self.route_name, 'dist': metersAway, 'speed': mph, 'mins': minutes_away, 
            'now': str(datetime.now().time())[0:8], 'veh': vehicle_ref
          })
        turn_on_green_pin = True
        # but if a second bus is close, I do want the green to go
        # even if there's a red bus nearby.

        #for debug:
        if bus.first_projected_arrival == 0:
          bus.first_projected_arrival = time.time() + seconds_away
    self.prep_for_writing()
    return {self.green_pin: turn_on_green_pin, self.red_pin: turn_on_red_pin}

  def prep_for_writing(self):
    self.errors_serialized = ','.join(map(str, self.errors))

  def get_locations(self):
    # line
    # http://api.prod.obanyc.com/api/siri/stop-monitoring.json?key=whatever&LineRef=MTA%20NYCT_B65
    # stop
    # http://api.prod.obanyc.com/api/siri/stop-monitoring.json?key=whatever&MonitoringRef=306495&LineRef=MTA%20NYCT_B65

    requestUrl = "http://bustime.mta.info/api/siri/stop-monitoring.json?key=%(key)s&OperatorRef=MTA&MonitoringRef=%(stop)s" %\
            {'key': self.mta_key, 'stop': self.stop_id}
    for i in xrange(0,4):
      try:
        response = urllib2.urlopen(requestUrl)
        break
      except urllib2.URLError: 
        response = None
        time.sleep(10)

    if not response:
      raise urllib2.URLError("Couldn't reach BusTime servers...")

    jsonresp = response.read()
    resp = json.loads(jsonresp)
    return resp["Siri"]["ServiceDelivery"]["StopMonitoringDelivery"][0]["MonitoredStopVisit"]

  def __repr__(self):
    return "<BusStop %(route)s #%(stop_id)s >" % {"route" : self.route_name, "number" : self.stop_id }


class Bus:
  def __init__(self, number):
    self.number = number
    self.time_location_pairs = []
    self.first_projected_arrival = 0

  def add_observed_position(self, time, distance_from_call):
    time_seconds = datetime.strptime(time[:19], "%Y-%m-%dT%H:%M:%S")
    if not (self.time_location_pairs and self.time_location_pairs[0][0] == time_seconds):
      #only insert a new time pair if the time is different
      self.time_location_pairs.insert(0, [time_seconds, distance_from_call])
    self.time_location_pairs = self.time_location_pairs[0:distance_to_track]

  def get_meters_away(self):
    return self.time_location_pairs[0][1]

  def get_seconds_away(self):
    speed = self.get_speed_mps()
    if speed == 0.0:
      return 6000 # a big number of seconds
    return self.get_meters_away() / speed

  def get_minutes_away(self):
    return timedelta(seconds=self.get_seconds_away())

  def get_speed_mph(self):
    return (self.get_speed_mps() * (60 * 60)) / 1609.34

  def get_speed_mps(self):
    #meters per second
    # this is a rolling weighted average over the past distance_to_track time/position values
    if len(self.time_location_pairs) < 2:
      return default_bus_speed

    centroid = 3.0
    speed_sum = 0
    weight_sum = 0
    for i, (time, location) in enumerate(self.time_location_pairs):
      if i == 0:
        continue;
      weight = centroid / (abs(i - centroid) if abs(i - centroid) > 0 else 0.5)
      weight_sum += weight
      speed_sum += self.naive_speed(0, i) * weight
    meters_per_second = speed_sum / weight_sum
    return meters_per_second

  # def old_get_speed(self):
  #   if len(self.time_location_pairs) < 2:
  #     return default_bus_speed
  #   long_term = self.naive_speed(0, 9)
  #   medium_term = self.less_naive_speed(0, 4)
  #   mid_to_short_term = self.less_naive_speed(0, 2)
  #   short_term = self.less_naive_speed(0, 1) #ignore this, since it might be stuck at a light
  #   meters_per_second = ( (mid_to_short_term * 2) + (medium_term * 2) + long_term) / 5
  #   return meters_per_second

  def naive_speed(self, start_index, end_index):
    if end_index >= len(self.time_location_pairs):
      end_index = -1

    start = self.time_location_pairs[start_index]
    end = self.time_location_pairs[end_index]
    distance = float(abs(start[1] - end[1]))
    time = abs(start[0] - end[0])
    return distance / float(time.seconds)

  def less_naive_speed(self, start_index, end_index):
    #naive speed, except don't count time the bus spends stopped
    if end_index >= len(self.time_location_pairs):
      end_index = -1

    start = self.time_location_pairs[start_index]
    end = self.time_location_pairs[end_index]
    distance = float(abs(start[1] - end[1]))
    raw_time = abs(start[0] - end[0])

    for (a_time, a_dist), (b_time, b_dist) in pairwise(self.time_location_pairs):
      if abs(a_dist - b_dist) < 20:
        raw_time -= abs(a_time - b_time)

    return distance / float(time.seconds)



  def pairwise(iterable):
      "s -> (s0,s1), (s1,s2), (s2, s3), ..."
      a, b = tee(iterable)
      next(b, None)
      return izip(a, b)