from datetime import datetime, timedelta
import time
from trajectory import Trajectory
from itertools import tee

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import orm

default_bus_speed = 4 # m/s ~= 8 miles per hour

class Bus:
  def __init__(self, number, journey):
    self.number = number
    self.time_location_pairs = []

    self.stop_time_pairs = {} #store time along the route
    self.start_time = None
    self.stops = []
    self.previous_distance_to_next_stop = 0

    self.first_projected_arrival = 0
    self.set_trajectory_points(journey)

  # def add_observed_position(self, recorded_at_str, distance_from_call):
  #   recorded_at = datetime.strptime(recorded_at_str[:19], "%Y-%m-%dT%H:%M:%S")
  #   if not (self.time_location_pairs and self.time_location_pairs[0][0] == recorded_at):
  #     #only insert a new time pair if the recorded_at time is different
  #     self.time_location_pairs.insert(0, [recorded_at, distance_from_call])
  #   self.time_location_pairs = self.time_location_pairs[0:distance_to_track]

  def add_observed_position(self, journey, recorded_at_str):
    """tk"""
    recorded_at = datetime.strptime(recorded_at_str[:19], "%Y-%m-%dT%H:%M:%S")
    distance_from_call = journey["MonitoredCall"]["Extensions"]["Distances"]["DistanceFromCall"]
    next_stop_ref = journey["OnwardCalls"]["OnwardCall"][0]["StopPointRef"]
    if not self.start_time:
      self.start_time = recorded_at

    #only insert a new time pair if the recorded_at time is different
    if not (self.time_location_pairs and self.time_location_pairs[0][0] == recorded_at):
      self.time_location_pairs.insert(0, [recorded_at, distance_from_call])

    # skip this bit if
    # - self.stop_time_pairs is false, because then this bus was init'ed when it was already on route
    #    and so the data is guaranteed to be invalid, so don't bother recording it
    # - we're at a stop that already has data -- i.e. that we've already visited
    # - the recorded_at time hasn't changed -- i.e. the bus hasn't updated its position
    if self.stop_time_pairs and not self.stop_time_pairs[next_stop_ref] and (self.time_location_pairs and self.time_location_pairs[0][0] != recorded_at):
      #if we're at a stop, add it to the thing
      if journey["OnwardCalls"]["OnwardCall"][0]["Extensions"]["Distances"]["PresentableDistance"] == "at stop":
        self.stop_time_pairs[next_stop_ref] = recorded_at
      #if we've passed the next stop (i.e. the first key with None as its value), interpolate its value
      elif self.stops[self.stops.index(next_stop_ref)-1] is None:
        #interpolate
        this_location = self.time_location_pairs[0]
        previous_location = self.time_location_pairs[1]

        distance_traveled = previous_location[1] - this_location[1] #TODO: record previous_distance_to_next_stop
        distance_to_missed_stop_from_previous_check = previous_location[1] - self.previous_distance_to_next_stop
        time_elapsed = this_location[0] - previous_location[0]
        interpolated_prev_stop_arrival_time = (time_elapsed * (distance_to_missed_stop_from_previous_check / distance_traveled) ) + previous_location[0]
        self.stop_time_pairs[next_stop_ref] = interpolated_prev_stop_arrival_time
      else:
        pass
    self.previous_distance_to_next_stop = journey["OnwardCalls"]["OnwardCall"][0]["Extensions"]["Distances"]["DistanceFromCall"]


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

  # this just fills in the keys to self.stop_time_pairs and members of self.stops
  # called only on init.
  def set_trajectory_points(self, journey):
    for onward_call in journey["OnwardCalls"]["OnwardCall"]:
      #TODO: set stop_time_pairs to false if the bus is already on route when it's inited.

      stop_ref = onward_call["StopPointRef"]
      if stop_ref not in self.stop_time_pairs:
        i = stop_ref #IntermediateStop(self.route_name, stop_ref, onward_call["StopPointName"])
        self.stops.append(i)
        self.stop_time_pairs[i] = None
      if stop_ref == journey["MonitoredCall"]["StopPointRef"]:
        break

  # called when we're done with the bus (i.e. it's passed the stop we're interested in)
  def convert_to_trajectory(self, route_name, stop_id):
    #TODO: in some cases, discard the bus, return None
    times = []
    segment_intervals = []
    for stop in self.stops:
      times.append(self.stop_time_pairs[stop])
    for time1, time2 in pairwise(times):
      segment_intervals.append((time2 - time1).seconds)
    traj = Trajectory(route_name, stop_id, self.start_time)
    traj.set_segment_intervals(segment_intervals)



def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)
