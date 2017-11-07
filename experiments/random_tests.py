import numpy as np
import matplotlib.pyplot as plt


x = [{'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '647.44'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '464.12'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '497.88'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '559.98'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '808.64'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '965.87'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '539.53'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '556.87'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '735.74'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '911.24'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '468.50'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '604.51'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '533.40'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '932.73'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '945.61'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '475.72'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '664.10'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '659.31'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '603.71'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '970.53'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '733.48'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '540.53'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '465.30'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '465.13'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '645.03'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '442.02'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '850.96'},
     {'number_of_RT_flows': 2, 'measurement_rates': 45, 'max_latency': '475.99'},
     {'number_of_RT_flows': 3, 'measurement_rates': 45, 'max_latency': '465.93'},
     {'number_of_RT_flows': 4, 'measurement_rates': 45, 'max_latency': '662.85'}]

print x

tt = (item for item in x if item["number_of_RT_flows"] == 2).next()

#print tt

number_of_flow_list = [2, 3, 4]
exp_data = [] # 2D list : row : # of flows, col: experimental samples
test_cases = 10

for nf in range(len(number_of_flow_list)):
     j = 0
     exp_data.append([])
     for i, dd in enumerate(x):
          # print dd
          if dd['number_of_RT_flows'] == number_of_flow_list[nf]:
               print "in if {}".format(nf)
               exp_data[nf].append(dd['max_latency'])



print exp_data

print exp_data[1][2]

plt.hold(True)
colors = np.random.rand(len(number_of_flow_list))

for i in range(len(number_of_flow_list)):
     for j in range(test_cases):
          plt.scatter(i, exp_data[i][j], alpha=0.5)


plt.show()
