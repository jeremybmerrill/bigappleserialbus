import json
import urllib2
from datetime import datetime, timedelta

time_to_get_ready = 240 # seconds
time_to_go = 180 #seconds
seconds_to_sidewalk = 60 #seconds
default_bus_speed = 5 # m/s ~= 11 miles per hour


greencode = '\033[92m'
redcode = '\033[91m'
endcolor = '\033[0m'

green_notice = greencode + "[green]" + endcolor + " "
red_notice = redcode + "[red]" + endcolor + " "

mta_key = open("apikey.txt", 'r').read().strip()

class BusStop:
  def __init__(self, route_name, number, stop_seconds_away, red_pin, green_pin):
    self.route_name = route_name
    self.red_pin = red_pin
    self.green_pin = green_pin
    self.too_late_to_catch_the_bus = stop_seconds_away + seconds_to_sidewalk
    self.time_to_get_ready = stop_seconds_away + (time_to_get_ready + time_to_go) + seconds_to_sidewalk
    self.time_to_go = stop_seconds_away + time_to_go + seconds_to_sidewalk
    self.monitoringRef = number
    self.lineRef = "MTA NYCT_" + route_name.upper()
    self.mta_key = mta_key
    self.buses_on_route = {}

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
      active_bus.add_stop(activity["RecordedAtTime"], distance_from_call)
    
    self.buses_on_route = new_buses

    for bus in self.buses_on_route.values():
      seconds_away = bus.get_seconds_away()
      minutes_away = str(bus.get_minutes_away())[2:7]
      metersAway = bus.get_meters_away()
      speed = bus.get_speed()
      mph = bus.get_speed_mph()


      if seconds_away < self.too_late_to_catch_the_bus:
        # too close, won't make it.
        continue
      if seconds_away < self.time_to_go:
        turn_on_red_pin = True
        print(red_notice + "bus %(name)s is %(dist)fm away, traveling at %(speed)f mph; computed to be %(mins)s away" % 
          {'name': self.route_name, 'dist': metersAway, 'speed': mph, 'mins': minutes_away})
        continue # if a bus is within Time_to_go, it's necessarily within Time_to_get_ready, but I don't 
                 # want it to trip the green pin too
      if seconds_away < self.time_to_get_ready:
        print(green_notice + "bus %(name)s is %(dist)fm away, traveling at %(speed)f mph; computed to be %(mins)s away" % 
          {'name': self.route_name, 'dist': metersAway, 'speed': mph, 'mins': minutes_away})
        turn_on_green_pin = True
                 # but if a second bus is close, I do want the green to go
                 # even if there's a red bus nearby.
    return {self.green_pin: turn_on_green_pin, self.red_pin: turn_on_red_pin}

  def get_locations(self):
    # line
    # http://api.prod.obanyc.com/api/siri/stop-monitoring.json?key=***REMOVED***&LineRef=MTA%20NYCT_B65
    # stop
    # http://api.prod.obanyc.com/api/siri/stop-monitoring.json?key=***REMOVED***&MonitoringRef=306495&LineRef=MTA%20NYCT_B65

    requestUrl = "http://bustime.mta.info/api/siri/stop-monitoring.json?key=%(key)s&OperatorRef=MTA&MonitoringRef=%(stop)s" %\
            {'key': self.mta_key, 'stop': self.monitoringRef}
    response = urllib2.urlopen(requestUrl)
    jsonresp = response.read()
    resp = json.loads(jsonresp)
    return resp["Siri"]["ServiceDelivery"]["StopMonitoringDelivery"][0]["MonitoredStopVisit"]

  # def get_distance(self, activity):
  #   journey = activity["MonitoredVehicleJourney"]
  #   recordedAt = activity["RecordedAtTime"]
  #   distances = journey["MonitoredCall"]["Extensions"]["Distances"]
  #   distance_from_call = distances["DistanceFromCall"] # meters, it turns out
  #     # PresentableDistance
  #     # StopsFromCall
  #   return distance_from_call
  def __repr__(self):
    return "<BusStop %(route)s #%(number)s >" % {"route" : self.route_name, "number" : self.monitoringRef }


class Bus:
  def __init__(self, number):
    self.number = number
    self.time_location_pairs = []

  def add_stop(self, time, distance_from_call):
    time_seconds = datetime.strptime(time[:19], "%Y-%m-%dT%H:%M:%S")
    if not (self.time_location_pairs and self.time_location_pairs[0][0] == time_seconds):
      #only insert a new time pair if the time is different
      self.time_location_pairs.insert(0, [time_seconds, distance_from_call])
    self.time_location_pairs = self.time_location_pairs[0:10]

  def get_meters_away(self):
    return self.time_location_pairs[0][1]

  def get_seconds_away(self):
    speed = self.get_speed()
    if speed == 0.0:
      return 6000 # a big number of seconds
    return self.get_meters_away() / speed

  def get_minutes_away(self):
    return timedelta(seconds=self.get_seconds_away())

  def get_speed_mph(self):
    return (self.get_speed() * (60 * 60)) / 1609.34

  def get_speed(self):
    #meters per second
    if len(self.time_location_pairs) < 2:
      return default_bus_speed
    long_term = self.naive_speed(0, 9)
    medium_term = self.naive_speed(0, 3)
    short_term = self.naive_speed(0, 1)
    #weighted average
    meters_per_second = ((short_term * 3) + (medium_term * 2) + long_term) / 6
    miles_per_hour = (meters_per_second / 1609.34) * (60 * 60)
    return meters_per_second

  def naive_speed(self, start_index, end_index):
    if end_index >= len(self.time_location_pairs):
      end_index = len(self.time_location_pairs) - 1

    start = self.time_location_pairs[start_index]
    end = self.time_location_pairs[end_index]
    distance = float(abs(start[1] - end[1]))
    time = abs(start[0] - end[0])
    print("%(start_dist)f - %(end_dist)f / %(time)i" % {'start_dist': start[1], 'end_dist': end[1], 'time':time.seconds})
    print(self.time_location_pairs)
    return distance / float(time.seconds)

