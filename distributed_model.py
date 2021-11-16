from base_model import BaseModelSimulationEnvironment, Event, SimulationParameters
import random
from delay_functions import DelayTypes, delay_exponential_distribution, delay_normal_distribution, delay_square_wave, delay_triangle_wave, delay_uniform_distribution

class DistributedSimulationParameters(SimulationParameters):
    min_delay: int
    max_delay: int
    delay_type: DelayTypes

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
        
        self.last_event = 0

    def get_delay(self, sending_node, receiving_node):
        """
        Returns the delay between two nodes
        """
        if sending_node == receiving_node:
            return 1
        elif self.delay_type == DelayTypes.UNIFORM:
            return delay_uniform_distribution(self.min_delay, self.max_delay)
        elif self.delay_type == DelayTypes.NORMAL:
            return delay_normal_distribution(self.min_delay, self.max_delay)
        elif self.delay_type == DelayTypes.EXPONENTIAL:
            return delay_exponential_distribution(self.min_delay, self.max_delay)
        elif self.delay_type == DelayTypes.SQUARE:
            return delay_square_wave(self.min_delay, self.max_delay, self.time, 10) #TODO: maybe add dynamic parameter for half_period
        elif self.delay_type == DelayTypes.TRIANGLE_LOW_TO_HIGH:
            return delay_triangle_wave(self.min_delay, self.max_delay, self.time, 1, True) #TODO: maybe add dynamic parameter for step
        elif self.delay_type == DelayTypes.TRIANGLE_HIGH_TO_LOW:
            return delay_triangle_wave(self.min_delay, self.max_delay, self.time, 1, False) #TODO: maybe add dynamic parameter for step

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
