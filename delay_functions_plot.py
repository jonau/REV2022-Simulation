from pandas.core.frame import DataFrame
from delay_functions import DelayGenerator, DelayTypes
import pandas

import matplotlib.pyplot as plt

min_delay = 20
max_delay = 100
max_jitter = 5
seed = 0

for delay_type in DelayTypes:
    delay_generator = DelayGenerator(seed)
    data = dict()
    df: DataFrame = None
    title = None
    xlabel = None
    ylabel = None
    ylim = None
    if delay_type == DelayTypes.UNIFORM:
        title = "Uniform Distribution"
        xlabel = "Delay"
        ylabel = "Occurrence (in %)"
        ylim = (0,5)
        for i in range(min_delay, max_delay+1):
            data[i] = 0
        for i in range(100000):
            data[delay_generator.delay_uniform_distribution(min_delay, max_delay)] += 1
        for key in data.keys():
            data[key] = data[key] / 1000
    elif delay_type == DelayTypes.NORMAL:
        title = "Normal Distribution"
        xlabel = "Delay"
        ylabel = "Occurrence (in %)"
        ylim = (0,10)
        for i in range(min_delay, max_delay+1):
            data[i] = 0
        for i in range(100000):
            data[delay_generator.delay_normal_distribution(min_delay, max_delay)] += 1
        for key in data.keys():
            data[key] = data[key] / 1000
    elif delay_type == DelayTypes.EXPONENTIAL:
        title = "Exponential Distribution"
        xlabel = "Delay"
        ylabel = "Occurrence (in %)"
        ylim = (0,10)
        for i in range(min_delay, max_delay+1):
            data[i] = 0
        for i in range(100000):
            data[delay_generator.delay_exponential_distribution(min_delay, max_delay)] += 1
        for key in data.keys():
            data[key] = data[key] / 1000
    elif delay_type == DelayTypes.SQUARE:
        title = "Square Wave"
        xlabel = "Time"
        ylabel = "Delay"
        for i in range(100):
            data[i] = delay_generator.delay_square_wave(min_delay, max_delay, max_jitter, i, 10)
    elif delay_type == DelayTypes.TRIANGLE_LOW_TO_HIGH:
        title = "Triangle Wave Low to High"
        xlabel = "Time"
        ylabel = "Delay"
        for i in range(500):
            data[i] = delay_generator.delay_triangle_wave(min_delay, max_delay, max_jitter, i, 1, True)
    elif delay_type == DelayTypes.TRIANGLE_HIGH_TO_LOW:
        title = "Triangle Wave High to Low"
        xlabel = "Time"
        ylabel = "Delay"
        for i in range(500):
            data[i] = delay_generator.delay_triangle_wave(min_delay, max_delay, max_jitter, i, 1, False)
    elif delay_type == DelayTypes.SKEWED_NORMAL:
        title = "Skewed Normal Distribution"
        xlabel = "Delay"
        ylabel = "Occurrence (in %)"
        ylim = (0,10)
        for i in range(min_delay, max_delay+1):
            data[i] = 0
        for i in range(100000):
            data[delay_generator.delay_skewed_normal_distribution(min_delay, max_delay)] += 1
        for key in data.keys():
            data[key] = data[key] / 1000
    df = pandas.DataFrame.from_dict(data, orient="index")
    df.plot(title=title, xlabel=xlabel, ylabel=ylabel, ylim=ylim)
    plt.show()
    print(df)