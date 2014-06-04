from datetime import datetime, timedelta
import time
from trajectory import Trajectory
from itertools import tee, izip
from collections import OrderedDict

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import orm

# from pylab import plot,show
from numpy import vstack,array
from numpy.random import rand
from scipy.cluster.vq import kmeans,vq

default_bus_speed = 4 # m/s ~= 8 miles per hour

#sometimes the bus, at the terminal where it starts, reports itself as, e.g. 0.2 meters along the route.
#this is used to decide that, yes, it's still at the start of the route.
max_gps_error = 20 #meters


class Bus:
  def __init__(self, number, journey, route_name, session):
    self.number = number
    self.time_location_pairs = []

    self.stop_time_pairs = OrderedDict() #store time along the route
    self.start_time = None
    self.stops = []
    self.previous_distance_to_next_stop = 0
    self.db_session = session
    self.route_name = route_name

    self.first_projected_arrival = 0
    self.first_projected_arrival_speeds = 0
    self.set_trajectory_points(journey)

  def add_observed_position(self, journey, recorded_at_str):
    """tk"""
    #TODO: refactor this method, use a previous_observed_position object
    # or a single list of dicts() holding all the relevant info from each prevoiusly observed position

    recorded_at = datetime.strptime(recorded_at_str[:19], "%Y-%m-%dT%H:%M:%S")
    distance_from_call = journey["MonitoredCall"]["Extensions"]["Distances"]["DistanceFromCall"]
    next_stop_ref = journey["OnwardCalls"]["OnwardCall"][0]["StopPointRef"]
    presentable_distance = journey["OnwardCalls"]["OnwardCall"][0]["Extensions"]["Distances"]["PresentableDistance"]
    distance_to_next_stop
    
    # as soon as the bus starts moving from its start point. 
    # (Don't count as its start_time time it spends going the opposite direction)
    if not self.start_time and next_stop_ref in self.stops and self.stops.index(next_stop_ref) > 0:
      self.start_time = recorded_at

    #only insert a new time pair if the recorded_at time is different OR time_location_pairs is empty
    if not (self.time_location_pairs and self.time_location_pairs[0][0] == recorded_at):
      self.time_location_pairs.insert(0, [recorded_at, distance_from_call])

      #TODO: right now, self.stop_time_pairs isn't created if the bus was already on route when the script was started
      # we still want to make predictions about these buses, using the data that we gather.
      # so find a different way to keep track of whether the bus can be saved to the db, and populate self.stop_time pairs
      # no matter what.

      # skip this bit if
      # - self.stop_time_pairs is false, because then this bus was init'ed when it was already on route
      #    and so the data is guaranteed to be invalid, so don't bother recording it
      # - we're at a stop that already has data -- i.e. that we've already visited
      # - the recorded_at time hasn't changed -- i.e. the bus hasn't updated its position
      if self.stop_time_pairs and (not self.stop_time_pairs[next_stop_ref]):
        prev_stop_ref = self.stops[self.stops.index(next_stop_ref)-1]

        #TODO loop over all previous stop_time_pairs that are None
        #if we've passed the next stop (i.e. the first key with None as its value), interpolate its value
        if self.stops.index(next_stop_ref) > 0 and self.stop_time_pairs[prev_stop_ref] is None:
          this_location = self.time_location_pairs[0]
          previous_location = self.time_location_pairs[1]

          distance_traveled = previous_location[1] - this_location[1]
          distance_to_missed_stop_from_previous_check = self.previous_distance_to_next_stop #TODO: erase this line
          time_elapsed = this_location[0] - previous_location[0]
          time_to_missed_stop = time_elapsed.seconds * (distance_to_missed_stop_from_previous_check / distance_traveled) 
          interpolated_prev_stop_arrival_time = timedelta(seconds=time_to_missed_stop) + previous_location[0]
          self.stop_time_pairs[prev_stop_ref] = interpolated_prev_stop_arrival_time
          print("%(bus_name)s add_observed_position interpolated; next stop: %(stop_ref)s, so prev_stop: %(prev_stop)s" % 
                {'bus_name': self.number, 'stop_ref': next_stop_ref, 'prev_stop': prev_stop_ref})
          print("distance: prev: %(prev_loc)fm, this: %(this_loc)fm; prev_dist: %(prev_dist)f" % 
            {'prev_loc': previous_location[1], 'this_loc': this_location[1], 'prev_dist': self.previous_distance_to_next_stop})
          print("time: elapsed: %(el)fs, to next stop: %(tonext)fs; interpolated: %(interp)s" % 
            {'el': time_elapsed.seconds, 'tonext': time_to_missed_stop, 'interp': interpolated_prev_stop_arrival_time.strftime("%H:%M:%S")})
        
        #if we're at a stop, add it to the stop_time_pairs 
        # (being at_stop and needing to interpolate the previous stop are not mutually exclusive.)
        # Buses often lay over at the first stop, so we record the *last* time it as at the stop.
        if self.stops.index(next_stop_ref) > 0 and presentable_distance == "at stop":
          self.stop_time_pairs[next_stop_ref] = recorded_at
          print("%(bus_name)s add_observed_position at stop" % {'bus_name': self.number})
        elif self.stops.index(next_stop_ref) == 1 and self.stop_time_pairs[self.stops[0]] is None: # try something diff: self.previous_presentable_distance == "at stop":
          previous_location = self.time_location_pairs[1]
          self.stop_time_pairs[prev_stop_ref] = previous_location[0]
          print("%(bus_name)s add_observed_position at stop" % {'bus_name': self.number})
        else:
          print("%(bus_name)s add_observed_position passes 2 (not at a new stop)" % {'bus_name': self.number})
          pass
      else:
        print("%(bus_name)s add_observed_position passes 1 (the next stop is already set)" % {'bus_name': self.number})
        pass
    else:
      print("%(bus_name)s add_observed_position passes 0 (last %(rec)s; now: %(now)s )" % 
          {'bus_name': self.number, 'rec': self.time_location_pairs[0][0], 'now': datetime.now()})
      pass
    self.previous_distance_to_next_stop = journey["OnwardCalls"]["OnwardCall"][0]["Extensions"]["Distances"]["DistanceFromCall"]
    self.previous_presentable_distance = presentable_distance
    print([(stop_ref, self.stop_time_pairs[stop_ref].strftime("%H:%M:%S")) if self.stop_time_pairs[stop_ref] else (stop_ref,) for stop_ref in self.stops ])


  # this just fills in the keys to self.stop_time_pairs and members of self.stops
  # called only on init.
  def set_trajectory_points(self, journey):
    #set stop_time_pairs to false if the bus is already on route when it's inited.
    if journey["OnwardCalls"]["OnwardCall"][0]["Extensions"]["Distances"]["CallDistanceAlongRoute"] > max_gps_error:
      print("%(bus_name)s was not at start, not setting traj points" % {'bus_name': self.number})
      return

    print("%(bus_name)s at start" % {'bus_name': self.number}, journey["OnwardCalls"]["OnwardCall"][0]["Extensions"]["Distances"]["CallDistanceAlongRoute"] )

    for index, onward_call in enumerate(journey["OnwardCalls"]["OnwardCall"]):
      stop_ref = onward_call["StopPointRef"]
      if stop_ref not in self.stops:
        i = stop_ref #IntermediateStop(self.route_name, stop_ref, onward_call["StopPointName"])
        self.stops.append(i)
        self.stop_time_pairs[i] = None
      if index == 0:
        self.stop_time_pairs[i] = self.start_time
      if stop_ref == journey["MonitoredCall"]["StopPointRef"]:
        break

  # called when we're done with the bus (i.e. it's passed the stop we're interested in)
  def convert_to_trajectory(self, route_name, stop_id):
    #TODO: in some cases, discard the bus, return None
    print("%(bus_name)s converting to trajectory" % {'bus_name': self.number})
    if not self.stop_time_pairs:
      return None
    segment_intervals = self.segment_intervals()
    if None in segment_intervals: # not ready to be converted to trajectory; because a stop doesn't have time data.
      return None
    print("%(bus_name)s segment_intervals: " % {'bus_name': self.number})
    print(segment_intervals)
    traj = Trajectory(route_name, stop_id, self.start_time)
    traj.set_segment_intervals(segment_intervals)
    print("converted to trajectory with " + str(len(segment_intervals)) + " segment intervals" )
    return traj

  def segment_intervals(self):
    if not self.stop_time_pairs:
      return None
    times = []
    segment_intervals = []
    for stop in self.stops:
      times.append(self.stop_time_pairs[stop])
    for time1, time2 in pairwise(times):
      if time1 is not None and time2 is not None:
        segment_intervals.append((time2 - time1).seconds)
      else:
        segment_intervals.append(None)
    return segment_intervals  

  def find_similar_trajectories(self):
    trajs = self.db_session.query(Trajectory.segment0,Trajectory.segment1,Trajectory.segment2,Trajectory.segment3,Trajectory.segment4,
      Trajectory.segment5,Trajectory.segment6,Trajectory.segment7,Trajectory.segment8,Trajectory.segment9,Trajectory.segment10,
      Trajectory.segment11,Trajectory.segment12,Trajectory.segment13,Trajectory.segment14,Trajectory.segment15,
      Trajectory.segment16,Trajectory.segment17,Trajectory.segment18,Trajectory.segment19,Trajectory.segment20,
      Trajectory.segment21,Trajectory.segment22,Trajectory.segment23,Trajectory.segment24,Trajectory.segment25,
      Trajectory.segment26,Trajectory.segment27,Trajectory.segment28,Trajectory.segment29,Trajectory.segment30,
      Trajectory.segment31,Trajectory.segment32,Trajectory.segment33,Trajectory.segment34,Trajectory.segment35,
      Trajectory.segment36,Trajectory.segment37,Trajectory.segment38,Trajectory.segment39).filter(Trajectory.route_name==self.route_name)
    
    truncate_trajs_to = trajs[0].index(None)
    trajs = [traj[:truncate_trajs_to] for traj in trajs]

    segment_intervals = self.segment_intervals()
    if segment_intervals is None or all([seg is None for seg in  segment_intervals]):
      return {'similar': [], 'seconds_away': -1}
    #truncate to last defined point of this bus (i.e. where it is now) to find similar trajectories _so far_.
    print('segment_intervals', segment_intervals)
    last_defined_segment_index = segment_intervals.index(None) if None in segment_intervals else len(segment_intervals) #TODO: last defined segment
    truncated_trajectories = array([traj[:last_defined_segment_index] for traj in trajs]) #TODO: check for off-by-one here
    centroids,_ = kmeans(truncated_trajectories,5) #TODO: 5 is a magic number. choose it better.
    indexes,_ = vq(truncated_trajectories,centroids)

    truncated_segment_intervals = segment_intervals[:last_defined_segment_index]
    my_cluster_index, _ = vq(array([truncated_segment_intervals]), centroids)
    my_cluster_index = my_cluster_index[0]
    similar_trajectories = [traj for idx, traj in enumerate(trajs) if idx == my_cluster_index]

    # average time-to-home-stop of the similar trajectories
    remaining_times_on_similar_trajectories = [sum(traj[last_defined_segment_index:]) for traj in similar_trajectories]
    seconds_away = sum(remaining_times_on_similar_trajectories) / len(similar_trajectories)
    return {'similar': similar_trajectories, 'seconds_away': seconds_away}




#TODO: erase all of this

# trajs = session.query(Trajectory.segment0,Trajectory.segment1,Trajectory.segment2,Trajectory.segment3,Trajectory.segment4,
#       Trajectory.segment5,Trajectory.segment6,Trajectory.segment7,Trajectory.segment8,Trajectory.segment9,Trajectory.segment10,
#       Trajectory.segment11,Trajectory.segment12,Trajectory.segment13,Trajectory.segment14,Trajectory.segment15,
#       Trajectory.segment16,Trajectory.segment17,Trajectory.segment18,Trajectory.segment19,Trajectory.segment20,
#       Trajectory.segment21,Trajectory.segment22,Trajectory.segment23,Trajectory.segment24,Trajectory.segment25,
#       Trajectory.segment26,Trajectory.segment27,Trajectory.segment28,Trajectory.segment29,Trajectory.segment30,
#       Trajectory.segment31,Trajectory.segment32,Trajectory.segment33,Trajectory.segment34,Trajectory.segment35,
#       Trajectory.segment36,Trajectory.segment37,Trajectory.segment38,Trajectory.segment39).filter(Trajectory.route_name=='b65')



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
