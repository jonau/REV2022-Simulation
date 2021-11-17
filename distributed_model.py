from dataclasses import dataclass
from base_model import BaseModelSimulationEnvironment, Event, SimulationParameters
import random
from delay_functions import DelayGenerator, DelayTypes

@dataclass
class DistributedSimulationParameters(SimulationParameters):
    min_delay: int
    max_delay: int
    delay_type: DelayTypes
    seed: int

class Statistics:
    time: int = 0
    error_detected: bool = False
    band_width_used: int = 0

class DistributedModelSimulationEnvironment(BaseModelSimulationEnvironment):
    def __init__(self, parameters: DistributedSimulationParameters):
        super().__init__(parameters)

        if hasattr(parameters, "delay_type"):
            self.delay_type = parameters.delay_type
        else:
            self.delay_type = DelayTypes.UNIFORM

        if hasattr(parameters, "min_delay"):
            self.min_delay = parameters.min_delay
        else:
            self.min_delay = 1

        if hasattr(parameters, "max_delay"):
            self.max_delay = parameters.max_delay
        else:
            self.max_delay = 10
            
        if hasattr(parameters, "seed"):
            self.delay_generator = DelayGenerator(parameters.seed)
        else:
            self.delay_generator = DelayGenerator()
        
        self.last_event = 0

    def get_delay(self, sending_node, receiving_node):
        """
        Returns the delay between two nodes
        """
        if sending_node == receiving_node:
            return 1
        elif self.delay_type == DelayTypes.UNIFORM:
            return self.delay_generator.delay_uniform_distribution(self.min_delay, self.max_delay)
        elif self.delay_type == DelayTypes.NORMAL:
            return self.delay_generator.delay_normal_distribution(self.min_delay, self.max_delay)
        elif self.delay_type == DelayTypes.EXPONENTIAL:
            return self.delay_generator.delay_exponential_distribution(self.min_delay, self.max_delay)
        elif self.delay_type == DelayTypes.SQUARE:
            return self.delay_generator.delay_square_wave(self.min_delay, self.max_delay, self.time, 10) #TODO: maybe add dynamic parameter for half_period
        elif self.delay_type == DelayTypes.TRIANGLE_LOW_TO_HIGH:
            return self.delay_generator.delay_triangle_wave(self.min_delay, self.max_delay, self.time, 1, True) #TODO: maybe add dynamic parameter for step
        elif self.delay_type == DelayTypes.TRIANGLE_HIGH_TO_LOW:
            return self.delay_generator.delay_triangle_wave(self.min_delay, self.max_delay, self.time, 1, False) #TODO: maybe add dynamic parameter for step

    def handle_event(self, time: int, event: Event):
        """
        Will be called for every event.
        """
        super().handle_event(time, event)

    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """
        super().handle_time_step(time, events_occured)

        if events_occured:
            self.last_event = time
        elif time - self.last_event > 2 * self.max_delay:
            self.stop()
