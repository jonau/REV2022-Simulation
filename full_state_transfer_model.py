from typing import Dict, List, Set
from simulation_objects import Node, State
from distributed_model import DistributedModelSimulationEnvironment, Statistics
from base_model import Event, SimulationParameters
import itertools

class FullStateTransferErrorNode(Node):
    full_state: Set[State]
    full_state_dict: Dict[int, State]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_state_dict = dict()
        self.full_state = set()

class FullStateTransferErrorModelEvent(Event):
    full_state: Set[State]


class FullStateTransferSimulationEnvironment(DistributedModelSimulationEnvironment):
    nodes: List[FullStateTransferErrorNode]
    full_state_statistics: List[Statistics]
    full_state_statistics_active_time_step: Statistics

    def __init__(self, parameters: SimulationParameters, fault_space: Set[int] = None):

        super().__init__(parameters)
        self.fault_space = fault_space
        self.number_of_variables = sum(parameters.number_of_variables_per_node)

        self.full_state_statistics = []
        self.full_state_statistics_active_time_step = Statistics()
        self.full_state_statistics_active_time_step.time = self.time

    def create_node_hook(self, *args, **kwargs):
        return FullStateTransferErrorNode(*args, **kwargs)

    def send_variable_hook(self, time: int, sending_node: FullStateTransferErrorNode, receiving_node: FullStateTransferErrorNode, variable, value) -> FullStateTransferErrorModelEvent:
        event=FullStateTransferErrorModelEvent()

        # Full State Transfer Data #############################################
        event.full_state = sending_node.full_state
        if sending_node != receiving_node:
            # Bandwidth need for the variable
            # The variables need one bit to transmit the status and the number of bits necessary to represent the position of the variable
            # Example: we have 8 varaibles: (number_of_variables-1).bit_length = 3 bits to represent the position - in total 4 bits of information
            self.full_state_statistics_active_time_step.band_width_used += 1+(self.number_of_variables-1).bit_length()
            # Bandwidth for the full state transfer
            # To transmit the set of state we need the number of states in the set len(sending_node.full_state), for which each state is encoded with number_of_variables bits to represent a full state vector
            self.full_state_statistics_active_time_step.band_width_used += len(sending_node.full_state)*self.number_of_variables
        
        return event

    def handle_event(self, time: int, event: FullStateTransferErrorModelEvent):
        """
        Will be called for every event.
        """
        super().handle_event(time, event)

        node = self.nodes[event.to_node]

        # Full State Transfer Handling #########################################
        node.full_state_dict[event.changed_variable[0]] = event.full_state


    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """

        error_node = self.nodes[0]
        
        for node in self.nodes:
            # Full State Transfer
            global_sub_state = node.global_sub_state()
            node.full_state = set()
            for state in itertools.chain([node.local_state],*node.full_state_dict.values()):
                node.full_state.add(State(state).overwrite(global_sub_state))

        # Full State Transfer Error Check
        error_check = [state in self.fault_space for state in error_node.full_state]
        if all(error_check):
            self.full_state_statistics_active_time_step.error_detected = True

        super().handle_time_step(time, events_occured)

        self.full_state_statistics_active_time_step.time = time
        self.full_state_statistics.append(self.full_state_statistics_active_time_step)
        self.full_state_statistics_active_time_step = Statistics()