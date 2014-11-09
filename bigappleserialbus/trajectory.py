#!/usr/bin/env python

__author__ = 'Jeremy B. Merrill'
__email__ = 'jeremybmerrill@gmail.com'
__license__ = 'Apache'
__version__ = '0.1'

from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Trajectory(Base):
  __tablename__ = 'trajectories'
  traj_id = Column(Integer, primary_key=True)
  end_stop_id = Column(String(10), nullable=False)
  route_name = Column(String(250), nullable=False)
  start_time = Column(DateTime, nullable=False)
  segment0 = Column(Integer, nullable=True)
  segment1 = Column(Integer, nullable=True)
  segment2 = Column(Integer, nullable=True)
  segment3 = Column(Integer, nullable=True)
  segment4 = Column(Integer, nullable=True)
  segment5 = Column(Integer, nullable=True)
  segment6 = Column(Integer, nullable=True)
  segment7 = Column(Integer, nullable=True)
  segment8 = Column(Integer, nullable=True)
  segment9 = Column(Integer, nullable=True)
  segment10 = Column(Integer, nullable=True)
  segment11 = Column(Integer, nullable=True)
  segment12 = Column(Integer, nullable=True)
  segment13 = Column(Integer, nullable=True)
  segment14 = Column(Integer, nullable=True)
  segment15 = Column(Integer, nullable=True)
  segment16 = Column(Integer, nullable=True)
  segment17 = Column(Integer, nullable=True)
  segment18 = Column(Integer, nullable=True)
  segment19 = Column(Integer, nullable=True)
  segment20 = Column(Integer, nullable=True)
  segment21 = Column(Integer, nullable=True)
  segment22 = Column(Integer, nullable=True)
  segment23 = Column(Integer, nullable=True)
  segment24 = Column(Integer, nullable=True)
  segment25 = Column(Integer, nullable=True)
  segment26 = Column(Integer, nullable=True)
  segment27 = Column(Integer, nullable=True)
  segment28 = Column(Integer, nullable=True)
  segment29 = Column(Integer, nullable=True)
  segment30 = Column(Integer, nullable=True)
  segment31 = Column(Integer, nullable=True)
  segment32 = Column(Integer, nullable=True)
  segment33 = Column(Integer, nullable=True)
  segment34 = Column(Integer, nullable=True)
  segment35 = Column(Integer, nullable=True)
  segment36 = Column(Integer, nullable=True)
  segment37 = Column(Integer, nullable=True)
  segment38 = Column(Integer, nullable=True)
  segment39 = Column(Integer, nullable=True)
  green_light_time = Column(DateTime, nullable=True)
  red_light_time = Column(DateTime, nullable=True)

  def __init__(self, route_name, stop_id, start_time):
    self.route_name = route_name
    self.end_stop_id = stop_id
    self.start_time = start_time

  def set_segment_intervals(self, segment_intervals):
    for index, segment_interval in enumerate(segment_intervals):
      column = "segment" + str(index)
      setattr(self, column, segment_interval)

  def __repr__(self):
    return ', '.join(map(str, [self.segment0, self.segment1, self.segment2, self.segment3, self.segment4, self.segment5, self.segment6, self.segment7, self.segment8, self.segment9, self.segment10, self.segment11, self.segment12, self.segment13, self.segment14, self.segment15, self.segment16, self.segment17, self.segment18, self.segment19, self.segment20, self.segment21, self.segment22, self.segment23, self.segment24, self.segment25, self.segment26, self.segment27, self.segment28, self.segment29, self.segment30, self.segment31, self.segment32, self.segment33, self.segment34, self.segment35, self.segment36, self.segment37, self.segment38, self.segment39]))
  # @staticmethod
  # def to_time_vector(trajectory_time):
  #   return (trajectory_time.weekday(), (trajectory_time.hour * 2) + (trajectory_time.minute / 30) )