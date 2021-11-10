from base_model import BaseModelSimulationEnvironment, Event, SimulationParameters
import random


class DistributedModelSimulationEnvironment(BaseModelSimulationEnvironment):
    def __init__(self, parameters: SimulationParameters):
        super().__init__(parameters)
        if hasattr(parameters, "max_delay"):
            self.max_delay = parameters.max_delay
        else:
            self.max_delay = 10

    def get_delay(self, sending_node, receiving_node):
        """
        Returns the delay between two nodes
        """
        if sending_node==receiving_node:
            return 1
        return random.randint(1, self.max_delay)

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
