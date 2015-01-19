import numpy as np
import matplotlib.pyplot as plt
import os
from trajectory import Trajectory, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sklearn.decomposition import PCA
from scipy.stats.stats import pearsonr
from sklearn.neighbors.kde import KernelDensity

sqlite_db_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../buses.db")
engine = create_engine('sqlite:///' + sqlite_db_path) #only creates the file if it doesn't exist already
Base.metadata.create_all(engine)
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
db_session = DBSession()

route_name = "b65"
end_stop_id = "MTA_308054"

traj_objects = db_session.query(Trajectory.start_time, Trajectory.segment0,Trajectory.segment1,Trajectory.segment2,Trajectory.segment3,Trajectory.segment4,
  Trajectory.segment5,Trajectory.segment6,Trajectory.segment7,Trajectory.segment8,Trajectory.segment9,Trajectory.segment10,
  Trajectory.segment11,Trajectory.segment12,Trajectory.segment13,Trajectory.segment14,Trajectory.segment15,
  Trajectory.segment16,Trajectory.segment17,Trajectory.segment18,Trajectory.segment19,Trajectory.segment20,
  Trajectory.segment21,Trajectory.segment22,Trajectory.segment23,Trajectory.segment24,Trajectory.segment25,
  Trajectory.segment26,Trajectory.segment27,Trajectory.segment28,Trajectory.segment29,Trajectory.segment30,
  Trajectory.segment31,Trajectory.segment32,Trajectory.segment33,Trajectory.segment34,Trajectory.segment35,
  Trajectory.segment36,Trajectory.segment37,Trajectory.segment38,Trajectory.segment39).filter(Trajectory.route_name==route_name).filter(Trajectory.end_stop_id == end_stop_id)
end_index = traj_objects[0].index(None)

unfiltered_trajs_with_time = [traj[:end_index] for traj in traj_objects ] # remove start_time item and Nones
unfiltered_trajs = [traj[1:] for traj in unfiltered_trajs_with_time]
trajs_with_time = [traj for traj in unfiltered_trajs_with_time if not any(map(lambda x: x != None and (x > 300 or x < 20), traj[1:])) ]

trajs = [traj for traj in unfiltered_trajs if not any(map(lambda x: x != None and (x > 300 or x < 20), traj)) ]

start_times = [traj[0] for traj in traj_objects if not any(map(lambda x: x != None and (x > 300 or x < 20), traj[1:]))]
colors = []


def histogram_lengths(): 
  trip_lengths = [sum(traj) for traj in trajs]
  plt.hist(trip_lengths, bins=50)
  plt.show()

def histogram_segments():
  segments = [item for sublist in trajs for item in sublist]
  plt.hist(segments, bins=50)
  plt.show()


def rs_by_split_point():
  for n in xrange(1,10):
    split_point = n/10.0
    x = [sum(traj[:int(len(traj) * split_point)]) for traj in trajs]
    y = [sum(traj[int(len(traj) * split_point):]) for traj in trajs]
    print(n, pearsonr(x,y)[0])

def rs_by_previous(n=5):
  rs = []
  for i in xrange(n, len(trajs[0])):
    x = [sum(traj[i-n:i]) for traj in trajs]
    y = [sum(traj[i:]) for traj in trajs] #dependent
    rs.append(pearsonr(x,y)[0])
  return rs

def rs_by_day_and_time():
  # -0.135908180745 correlation between total route time (on b65, downtownbound) and being a weekend
  #  0.0.20212506141277539 correlation between total route time (on b65, downtownbound) and being rush hour (7,8,9, 17,18,19) on a weekday
  x = [int(start_time.weekday() in [5,6]) for start_time in start_times] #independent
  y = [sum(traj) for traj in trajs] #dependent
  #TODO: how much variation is there weekend to weekday?
  print( "weekend/day", pearsonr(x,y)[0])

  x = [int(start_time.hour in [7,8,9, 17,18,19] and start_time.weekday() not in [5,6]) for start_time in start_times] #independent. rush hour?
  y = [sum(traj) for traj in trajs] #dependent
  print( "rush hour (weekdays)", pearsonr(x,y)[0]  )


def chart_by_day():
  #
  # On average, trips on the weekend take less time than trips on weekdays
  # 1337 sec versus 1446 sec
  # 
  weekend_times = [sum(traj[1:]) for traj in trajs_with_time if traj[0].weekday() in [5,6]]
  weekday_times = [sum(traj[1:]) for traj in trajs_with_time if traj[0].weekday() not in [5,6]]
  weekend = sum(weekend_times) / float(len(weekend_times))
  weekday = sum(weekday_times) / float(len(weekday_times))
  print("weekend: ", weekend, "weekday: ", weekday)
  x = np.linspace(min(weekend_times + weekday_times), max(weekend_times + weekday_times), 100).reshape(-1, 1)

  kde_weekend = KernelDensity(bandwidth=100).fit(np.array(weekend_times).reshape(-1, 1))
  density_weekend = np.exp(kde_weekend.score_samples(x))

  kde_weekday = KernelDensity(bandwidth=100).fit(np.array(weekday_times).reshape(-1, 1))
  density_weekday = np.exp(kde_weekday.score_samples(x))

  plt.plot(x, density_weekend, 'r')
  plt.plot(x, density_weekday, 'b')
  plt.xlabel("Time start to Grand Ave: red: weekend, blue, weekday")
  plt.ylabel("Density")
  plt.show()

def chart_by_time():
  weekday_amrush = [sum(traj[1:]) for traj in trajs_with_time if traj[0].weekday() not in [5,6] and traj[0].hour in [7,8,9]]
  weekday_pmrush = [sum(traj[1:]) for traj in trajs_with_time if traj[0].weekday() not in [5,6] and traj[0].hour in [17,18,19]]
  weekday_midday = [sum(traj[1:]) for traj in trajs_with_time if traj[0].weekday() not in [5,6] and traj[0].hour in [10,11,12,13,14,15,16]]
  weekday_night = [sum(traj[1:]) for traj in trajs_with_time if traj[0].weekday() not in [5,6] and traj[0].hour in [20,21,22,23,0,1,2,3,4,5,6]]
  weekend = [sum(traj[1:]) for traj in trajs_with_time if traj[0].weekday() in [5,6]]

  weekday_amrush_avg = sum(weekday_amrush) / float(len(weekday_amrush))
  weekday_pmrush_avg = sum(weekday_pmrush) / float(len(weekday_pmrush))
  weekday_midday_avg = sum(weekday_midday) / float(len(weekday_midday))
  weekday_night_avg = sum(weekday_night) / float(len(weekday_night))
  weekend_avg = sum(weekend) / float(len(weekend))


  print("weekday_amrush_avg: ", weekday_amrush_avg,
        "weekday_pmrush_avg: ", weekday_pmrush_avg,
        "weekday_midday_avg: ", weekday_midday_avg,
        "weekday_night_avg: ", weekday_night_avg,
        "weekend_avg: ", weekend_avg)

  x = np.linspace(min(weekday_amrush+weekday_pmrush+weekday_midday+weekday_night+weekend), max(weekday_amrush+weekday_pmrush+weekday_midday+weekday_night+weekend), 100).reshape(-1, 1)
  kde_weekday_amrush = KernelDensity(bandwidth=70).fit(np.array(weekday_amrush).reshape(-1, 1))
  density_weekday_amrush = np.exp(kde_weekday_amrush.score_samples(x))
  kde_weekday_pmrush = KernelDensity(bandwidth=70).fit(np.array(weekday_pmrush).reshape(-1, 1))
  density_weekday_pmrush = np.exp(kde_weekday_pmrush.score_samples(x))
  kde_weekday_midday = KernelDensity(bandwidth=70).fit(np.array(weekday_midday).reshape(-1, 1))
  density_weekday_midday = np.exp(kde_weekday_midday.score_samples(x))
  kde_weekday_night = KernelDensity(bandwidth=70).fit(np.array(weekday_night).reshape(-1, 1))
  density_weekday_night = np.exp(kde_weekday_night.score_samples(x))
  kde_weekend = KernelDensity(bandwidth=70).fit(np.array(weekend).reshape(-1, 1))
  density_weekend = np.exp(kde_weekend.score_samples(x))

  plt.plot(x, density_weekday_amrush, 'r')
  plt.plot(x, density_weekday_pmrush, 'y')
  plt.plot(x, density_weekday_midday, 'g')
  plt.plot(x, density_weekday_night, 'b')
  plt.plot(x, density_weekend, 'm')
  plt.xlabel("Time start to endpoint")
  plt.ylabel("Density")
  plt.show()



def scatter_halves():
  split_point = 8/10.0

  x = [sum(traj[:int(len(traj) * split_point)]) for traj in trajs]
  y = [sum(traj[int(len(traj) * split_point):]) for traj in trajs]
  # colors = np.random.rand(N)
  # area = np.pi * (15 * np.random.rand(N))**2 # 0 to 15 point radiuses

  plt.scatter(x, 
              y, 
              # s=area, 
              # c=colors, 
              alpha=0.5)
  plt.show()

def do_pca():
  pca = PCA(n_components=2)
  pca.fit(np.array(trajs))
  reduced_trajs = pca.transform(trajs)
  print(reduced_trajs)
  reduced_trajs = reduced_trajs.T.tolist()
  plt.scatter(reduced_trajs[0], reduced_trajs[1], alpha=0.5)
  plt.show()

def per_segment_length():
  avg_segment_times = [sum(segment_vals)/float(len(segment_vals)) for segment_vals in np.array(trajs).T]
  plt.scatter(list(xrange(0, len(avg_segment_times))), avg_segment_times)
  plt.plot(list(xrange(0, len(avg_segment_times))), avg_segment_times, 'g')

  too_long_segments = [sum([1 for n in segment_vals if n > 300]) for segment_vals in np.array(raw_trajs).T]
  print(too_long_segments)
  plt.scatter(list(xrange(0, len(too_long_segments))), too_long_segments)
  plt.plot(list(xrange(0, len(too_long_segments))), too_long_segments, 'r')

  too_short_segments = [sum([1 for n in segment_vals if n < 20]) for segment_vals in np.array(raw_trajs).T]
  print(too_short_segments)
  plt.scatter(list(xrange(0, len(too_short_segments))), too_short_segments)
  plt.plot(list(xrange(0, len(too_short_segments))), too_short_segments, 'b')

  plt.show()


# print(rs_by_previous())

# per_segment_length()
# rs_by_day_and_time()
chart_by_time()
# for i in xrange(3,9):
#   rs = rs_by_previous(i)
#   print(i, sum(rs)/len(rs))

# # histogram_lengths()

#TODO: histogram segment times per segment (i.e. Classon to Grand, Franklin to Classon, etc.)