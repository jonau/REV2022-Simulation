from typing import Dict, List, Set
from simulation_objects import Node, State
from distributed_model import DistributedModelSimulationEnvironment
from base_model import Event, SimulationParameters
import itertools

class ErrorNode(Node):
    full_state: Set[State]
    full_state_dict: Dict[int, State]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_state_dict=dict()
        self.full_state=set()

class ErrorModelEvent(Event):
    full_state: Set[State]

class Statistics:
    time: int = 0
    error_detected: bool = False
    band_width_used: int = 0


class ErrorModelSimulationEnvironment(DistributedModelSimulationEnvironment):
    nodes: List[ErrorNode]
    full_state_statistics: List[Statistics] = []
    full_state_statistics_active_time_step=Statistics

    def __init__(self, parameters: SimulationParameters, fault_space: Set[int] = None):
        super().__init__(parameters)
        self.fault_space = fault_space
        self.number_of_variables = sum(parameters.number_of_variables_per_node)

        self.full_state_errors=set()
        self.full_state_statistics_active_time_step=Statistics()
        self.full_state_statistics_active_time_step.time=self.time

    def create_node_hook(self, *args, **kwargs):
        return ErrorNode(*args, **kwargs)

    def send_variable_hook(self, time: int, sending_node: ErrorNode, receiving_node: ErrorNode, variable, value) -> ErrorModelEvent:
        event=ErrorModelEvent()
        # Full State Transfer Data #############################################
        event.full_state=sending_node.full_state
        if sending_node != receiving_node:
            # Bandwidth need for the variable
            self.full_state_statistics_active_time_step.band_width_used+=1+(self.number_of_variables.bit_length()-1)
            # Bandwidth for the full state transfer
            self.full_state_statistics_active_time_step.band_width_used+=len(sending_node.full_state)*(self.number_of_variables.bit_length()-1)
        
        return event

    def handle_event(self, time: int, event: ErrorModelEvent):
        """
        Will be called for every event.
        """
        super().handle_event(time, event)
        # Full State Transfer Handling #########################################
        node=self.nodes[event.to_node]
        node.full_state_dict[event.changed_variable[0]]=event.full_state

    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """
        for node in self.nodes:
            global_sub_state=node.global_sub_state()
            node.full_state=set()
            for state in itertools.chain([node.local_state],*node.full_state_dict.values()):
                node.full_state.add(State(state).overwrite(global_sub_state))
            error_check=[state in self.fault_space for state in node.full_state]
            if all(error_check):
                self.full_state_statistics_active_time_step.error_detected=True

        super().handle_time_step(time, events_occured)

        self.full_state_statistics_active_time_step.time=time
        self.full_state_statistics.append(self.full_state_statistics_active_time_step)
        self.full_state_statistics_active_time_step=Statistics()