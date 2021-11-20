from typing import Generator
import numpy as np
from scipy.stats import skewnorm
from enum import Enum

from scipy.stats.stats import skewtest

class DelayTypes(Enum):
    UNIFORM = 0
    NORMAL = 1
    EXPONENTIAL = 2
    SQUARE = 3
    TRIANGLE_LOW_TO_HIGH = 4
    TRIANGLE_HIGH_TO_LOW = 5
    SKEWED_NORMAL = 6
    
    def random(generator):
        random = generator.randint(0,6)
        if random == 0:
            return DelayTypes.UNIFORM
        if random == 1:
            return DelayTypes.NORMAL
        if random == 2:
            return DelayTypes.EXPONENTIAL
        if random == 3:
            return DelayTypes.SQUARE
        if random == 4:
            return DelayTypes.TRIANGLE_LOW_TO_HIGH
        if random == 5:
            return DelayTypes.TRIANGLE_HIGH_TO_LOW
        if random == 6:
            return DelayTypes.SKEWED_NORMAL

#TODO: maybe add jitter for square and triangle wave
class DelayGenerator():
    rng: np.random.Generator

    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed=seed)
        np.random.seed(seed=seed)

    def delay_uniform_distribution(self, min_delay, max_delay) -> int:
        """
        returns an uniform distributed delay between min_delay and max_delay
        """
        return self.rng.integers(low=min_delay, high=max_delay+1)

    def delay_normal_distribution(self, min_delay, max_delay) -> int:
        """
        returns a normal distributed delay between min_delay and max_delay
        """
        return int(min(max_delay, max(min_delay, self.rng.normal(loc=(max_delay+min_delay)/2, scale=(max_delay+min_delay)/10))))

    def delay_exponential_distribution(self, min_delay, max_delay) -> int:
        """
        returns an exponential distributed delay between min_delay and max_delay
        """
        return int(min(max_delay, min_delay + self.rng.exponential(scale=10.0)))

    def delay_square_wave(self, min_delay, max_delay, time, half_period) -> int:
        """
        returns a delay following a square wave
        """
        low = (time // half_period + 1) % 2
        high = (time // half_period) % 2
        return low * min_delay + high * max_delay

    def delay_triangle_wave(self, min_delay, max_delay, time, step, direction=True) -> int:
        """
        returns a delay following a triangle wave. If direction is set to True the wave goes from low to high.
        If direction is set to False the wave goes from high to low.
        """
        if (direction):
            return min(max_delay, min_delay + step * (time % np.ceil(((max_delay - min_delay)/step + 1)))) 
        else:
            return max(min_delay, max_delay - step * (time % np.ceil(((max_delay - min_delay)/step + 1)))) 
    def delay_skewed_normal_distribution(self, min_delay, max_delay):
        """
        returns a normal distributed delay between min_delay and max_delay
        """
        return int(max(min_delay, min(max_delay, skewnorm.rvs(10, loc=25, scale=20.0))))