import delay_functions
import numpy

min_delay = 20
max_delay = 100
half_period = 5
step = 1
time = 0

ud_values = []
nd_values = []
ed_values = []
sw_values = []
twlh_values = []
twhl_values = []

for i in range(0,1000000):
    ud_values.append(delay_functions.delay_uniform_distribution(min_delay, max_delay))
    nd_values.append(delay_functions.delay_normal_distribution(min_delay, max_delay))
    ed_values.append(delay_functions.delay_exponential_distribution(min_delay, max_delay))
    sw_values.append(delay_functions.delay_square_wave(min_delay, max_delay, time, half_period))
    twlh_values.append(delay_functions.delay_triangle_wave(min_delay, max_delay, time, step, True))
    twhl_values.append(delay_functions.delay_triangle_wave(min_delay, max_delay, time, step, False))
    time += 1

print(f"Uniform Distribution:\nMin:{numpy.min(ud_values)}\nMax:{numpy.max(ud_values)}\nAvg:{numpy.average(ud_values)}\n")
print(f"Normal Distribution:\nMin:{numpy.min(nd_values)}\nMax:{numpy.max(nd_values)}\nAvg:{numpy.average(nd_values)}\n")
print(f"Exponential Distribution:\nMin:{numpy.min(ed_values)}\nMax:{numpy.max(ed_values)}\nAvg:{numpy.average(ed_values)}\n")
print(f"Square Wave:\nMin:{numpy.min(sw_values)}\nMax:{numpy.max(sw_values)}\nAvg:{numpy.average(sw_values)}\n")
print(f"Triangle Wave Low to High:\nMin:{numpy.min(twlh_values)}\nMax:{numpy.max(twlh_values)}\nAvg:{numpy.average(twlh_values)}\n")
print(f"Triangle Wave High to Low:\nMin:{numpy.min(twhl_values)}\nMax:{numpy.max(twhl_values)}\nAvg:{numpy.average(twhl_values)}\n")