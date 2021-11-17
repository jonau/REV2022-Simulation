from dataclasses import dataclass
from os import wait
from typing import Dict, List, Set, Tuple
from simulation_objects import Node
from distributed_model import DistributedModelSimulationEnvironment, Statistics
from base_model import Event, SimulationParameters

@dataclass
class Delay:
    from_node: int
    to_node: int
    value: int

class TimestampErrorNode(Node):
    # List of estimated wait times
    timestamp_faults: List[int]
    delays: List[Delay]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delays = []
        self.timestamp_faults = []

class TimestampErrorModelEvent(Event):
    timestamp: int
    changed_delay: Delay


class TimestampErrorModelSimulationEnvironment(DistributedModelSimulationEnvironment):
    nodes: List[TimestampErrorNode]
    timestamp_statistics: List[Statistics]
    timestamp_statistics_active_time_step: Statistics

    def __init__(self, parameters: SimulationParameters, fault_space: Set[int] = None):

        super().__init__(parameters)
        self.fault_space = fault_space
        self.number_of_variables = sum(parameters.number_of_variables_per_node)

        self.timestamp_statistics = []
        self.timestamp_statistics_active_time_step = Statistics()
        self.timestamp_statistics_active_time_step.time = self.time
        for node in self.nodes:
            for i in range(len(self.nodes)):
                for j in range(len(self.nodes)):
                    if i == j:
                        node.delays.append(Delay(i,j,1)) # constant delay of 1 from a node to itself
                    else:
                        node.delays.append(Delay(i,j,0)) # could also be an estimate for the delay instead of 0

    def create_node_hook(self, *args, **kwargs):
        return TimestampErrorNode(*args, **kwargs)

    def send_variable_hook(self, time: int, sending_node: TimestampErrorNode, receiving_node: TimestampErrorNode, variable, value) -> TimestampErrorModelEvent:
        event=TimestampErrorModelEvent()

        event.timestamp = time
        if sending_node != receiving_node:
            # Bandwidth need for the variable
            self.timestamp_statistics_active_time_step.band_width_used += 1+(self.number_of_variables-1).bit_length()
            # Bandwidth for the timestamp
            self.timestamp_statistics_active_time_step.band_width_used += 32
        
        return event

    def handle_event(self, time: int, event: TimestampErrorModelEvent):
        """
        Will be called for every event.
        """
        super().handle_event(time, event)

        node = self.nodes[event.to_node]

        if event.timestamp == None:
            for delay in node.delays:
                if delay.from_node == event.changed_delay.from_node and delay.to_node == event.changed_delay.to_node:
                    delay.value = event.changed_delay.value
                    return

        new_delay = time - event.timestamp
        for delay in node.delays:
            if delay.from_node == event.from_node and delay.to_node == event.to_node:
                if not delay.value == new_delay:
                    delay.value = new_delay # here also max or average could be used
                    for _node in self.nodes:
                        if not node == _node:
                            timestamp_event = TimestampErrorModelEvent()
                            timestamp_event.changed_variable = None
                            timestamp_event.changed_delay = delay
                            timestamp_event.from_node = node.id
                            timestamp_event.to_node = _node.id
                            timestamp_event.timestamp = None
                            timestamp_event_delay = self.get_delay(node.id, _node.id)
                            self.create_event(time + timestamp_event_delay, timestamp_event)
                            # 2*bits for representing the from_node and to_node and 32 bit for delay
                            self.timestamp_statistics_active_time_step.band_width_used += 32+(len(self.nodes)-1).bit_length()*2


    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """

        error_node = self.nodes[0]

        for i in range(len(error_node.timestamp_faults)):
            error_node.timestamp_faults[i] -= 1

        if error_node.local_state.int_representation in self.fault_space:
            wait_time = 0
            for delay in error_node.delays:
                wait_time += delay.value
            wait_time = wait_time // len(self.nodes) #TODO: check if this calculation is model conform and correct
            error_node.timestamp_faults.append(wait_time)
            for timestamp_fault in list(error_node.timestamp_faults):
                if timestamp_fault == 0:
                    self.timestamp_statistics_active_time_step.error_detected = True
                    error_node.timestamp_faults.remove(timestamp_fault)
        else:
            error_node.timestamp_faults.clear()

        super().handle_time_step(time, events_occured)

        self.timestamp_statistics_active_time_step.time = time
        self.timestamp_statistics.append(self.timestamp_statistics_active_time_step)
        self.timestamp_statistics_active_time_step = Statistics()