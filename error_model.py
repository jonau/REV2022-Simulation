from typing import Dict, List, Set, Tuple
from simulation_objects import Node, State
from distributed_model import DistributedModelSimulationEnvironment
from base_model import Event, SimulationParameters
import itertools

class ErrorNode(Node):
    full_state: Set[State]
    full_state_dict: Dict[int, State]
    timestamp_dict: Dict[int, int]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_state_dict=dict()
        self.full_state=set()
        self.timestamp_dict = dict()

class ErrorModelEvent(Event):
    full_state: Set[State]
    timestamp: int

class Statistics:
    time: int = 0
    error_detected: bool = False
    band_width_used: int = 0


class ErrorModelSimulationEnvironment(DistributedModelSimulationEnvironment):
    nodes: List[ErrorNode]
    full_state_statistics: List[Statistics] = []
    full_state_statistics_active_time_step: Statistics

    # Timestamps
    timestamp_faults: List[Tuple[Node, State, int]]
    timestamp_statistics: List[Statistics] = []
    timestamp_statistics_active_time_step: Statistics

    def __init__(self, parameters: SimulationParameters, fault_space: Set[int] = None):
        super().__init__(parameters)
        self.fault_space = fault_space
        self.number_of_variables = sum(parameters.number_of_variables_per_node)

        self.full_state_errors = set()
        self.full_state_statistics_active_time_step = Statistics()
        self.full_state_statistics_active_time_step.time = self.time

        # Timestamps
        self.timestamp_faults = []
        self.timestamp_statistics_active_time_step = Statistics()
        self.timestamp_statistics_active_time_step.time = self.time

    def create_node_hook(self, *args, **kwargs):
        return ErrorNode(*args, **kwargs)

    def send_variable_hook(self, time: int, sending_node: ErrorNode, receiving_node: ErrorNode, variable, value) -> ErrorModelEvent:
        event=ErrorModelEvent()

        # Full State Transfer Data #############################################
        event.full_state = sending_node.full_state
        if sending_node != receiving_node:
            # Bandwidth need for the variable
            self.full_state_statistics_active_time_step.band_width_used += 1+(self.number_of_variables.bit_length()-1) # Todo: Check if the -1 is correct
            # Bandwidth for the full state transfer
            self.full_state_statistics_active_time_step.band_width_used += len(sending_node.full_state)*(self.number_of_variables.bit_length()-1) # Todo: Redo the calculation correctly

        # Timestamps Data ######################################################
        event.timestamp = time
        if sending_node != receiving_node:
            # Bandwidth need for the variable
            self.timestamp_statistics_active_time_step.band_width_used += 1+(self.number_of_variables.bit_length()-1) # Todo: Check if the -1 is correct
            # Bandwidth for the timestamp
            self.timestamp_statistics_active_time_step.band_width_used += 32
        
        return event

    def handle_event(self, time: int, event: ErrorModelEvent):
        """
        Will be called for every event.
        """
        super().handle_event(time, event)
        # Full State Transfer Handling #########################################
        node = self.nodes[event.to_node]
        node.full_state_dict[event.changed_variable[0]] = event.full_state

        # Timestamps Handling ##################################################
        node.timestamp_dict[event.changed_variable[0]] = event.timestamp

    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """
        # Timestamps
        for timestamp_fault in self.timestamp_faults:
            timestamp_fault_temp = list(timestamp_fault)
            timestamp_fault_temp[2] -= 1
            timestamp_fault = tuple(timestamp_fault_temp)

        for node in self.nodes:
            # Full State Transfer
            global_sub_state = node.global_sub_state()
            node.full_state = set()
            for state in itertools.chain([node.local_state],*node.full_state_dict.values()):
                node.full_state.add(State(state).overwrite(global_sub_state))
            error_check = [state in self.fault_space for state in node.full_state]
            if all(error_check):
                self.full_state_statistics_active_time_step.error_detected = True

            # Timestamp 
            if node.local_state.int_representation in self.fault_space:
                wait_time = 0
                for key in node.timestamp_dict.keys():
                    wait_time += time - node.timestamp_dict[key]
                self.timestamp_faults.append((node, node.local_state, wait_time))
                for timestamp_fault in self.timestamp_faults:
                    if timestamp_fault[0] == node and timestamp_fault[1] == node.local_state and timestamp_fault[2] == 0:
                        self.timestamp_statistics_active_time_step.error_detected = True
                        self.timestamp_faults.remove(timestamp_fault)
            else:
                for timestamp_fault in self.timestamp_faults:
                    if timestamp_fault[0] == node:
                        self.timestamp_faults.remove(timestamp_fault)

            for timestamp_fault in self.timestamp_faults:
                if timestamp_fault[0] == 0:
                    self.timestamp_faults.remove(timestamp_fault)



        super().handle_time_step(time, events_occured)

        self.full_state_statistics_active_time_step.time = time
        self.full_state_statistics.append(self.full_state_statistics_active_time_step)
        self.full_state_statistics_active_time_step = Statistics()

        # Timestamps
        self.timestamp_statistics_active_time_step.time = time
        self.timestamp_statistics.append(self.timestamp_statistics_active_time_step)
        self.timestamp_statistics_active_time_step = Statistics()