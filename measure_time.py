import time
import numpy

__measurements = dict()

def define_measurement(id, name):
    __measurements[id] = [name, time.time(), []]

def measurent_begin(id):
    __measurements[id][1] = time.time()

def measurent_end(id):
    __measurements[id][2].append(time.time() - __measurements[id][1])

def print_measurements():
    for key in __measurements:
        if len(__measurements[key][2]) > 0:
            print(f"Measurement {__measurements[key][0]}:")
            print(f"Min:    {min(__measurements[key][2])}")
            print(f"Max:    {max(__measurements[key][2])}")
            print(f"Avg:    {numpy.average(__measurements[key][2])}")
            print(f"Total:  {sum(__measurements[key][2])}\n")
        else:
            print(f"No Measurement for {__measurements[key][0]}\n")

def clear_measurements():
    __measurements.clear()