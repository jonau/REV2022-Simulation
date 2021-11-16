import numpy as np
from enum import Enum

class DelayTypes(Enum):
    UNIFORM = 1
    NORMAL = 2
    EXPONENTIAL = 3
    SQUARE = 4
    TRIANGLE_LOW_TO_HIGH = 5
    TRIANGLE_HIGH_TO_LOW = 6

rng = np.random.default_rng(seed=0)

def delay_uniform_distribution(min_delay, max_delay) -> int:
    """
    returns an uniform distributed delay between min_delay and max_delay
    """
    return rng.integers(low=min_delay, high=max_delay+1)

def delay_normal_distribution(min_delay, max_delay) -> int:
    """
    returns a normal distributed delay between min_delay and max_delay
    """
    return min(max_delay, max(min_delay, rng.normal(loc=30, scale=10.0)))

def delay_exponential_distribution(min_delay, max_delay) -> int:
    """
    returns an exponential distributed delay between min_delay and max_delay
    """
    return min(max_delay, min_delay + rng.exponential(scale=10.0))

def delay_square_wave(min_delay, max_delay, time, half_period) -> int:
    """
    returns a delay following a square wave
    """
    low = (time // half_period + 1) % 2
    high = (time // half_period) % 2
    return low * min_delay + high * max_delay

def delay_triangle_wave(min_delay, max_delay, time, step, direction=True) -> int:
    """
    returns a delay following a triangle wave. If direction is set to True the wave goes from low to high.
    If direction is set to False the wave goes from high to low.
    """
    if (direction):
        return min(max_delay, min_delay + step * (time % np.ceil(((max_delay - min_delay)/step + 1)))) 
    else:
        return max(min_delay, max_delay - step * (time % np.ceil(((max_delay - min_delay)/step + 1)))) 