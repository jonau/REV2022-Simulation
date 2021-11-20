from dataclasses import dataclass
from typing import Dict, List, Set
from delay_functions import DelayGenerator
from simulation_objects import Node, State
from distributed_model import DistributedModelSimulationEnvironment
from base_model import Event, SimulationParameters
import numpy
import itertools

class Statistics:
    time: int = 0
    error_detected: bool = False
    band_width_used: int = 0
    memory_used: int = 0

@dataclass
class Delay:
    from_node: int
    to_node: int
    value: int

@dataclass
class Token:
    node_id: int
    token_id: int

@dataclass
class TokenFault:
    token: Token
    received_from: List[int]

class ErrorNode(Node):
    full_state: Set[State]
    full_state_dict: Dict[int, State]

    delays: List[Delay]
    timestamp_faults: List[int]

    next_token_id: int
    token_faults: List[TokenFault]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_state = set()
        self.full_state_dict = dict()
        
        self.delays = []
        self.timestamp_faults = []

        self.token_faults = []
        self.tokens = []
        self.next_token_id = 0

class ErrorModelEvent(Event):
    full_state: Set[State]

    timestamp: int
    changed_delay: Delay

    token: Token

    def __init__(self):
        super().__init__()
        self.token = None
        self.timestamp = None


class ErrorSimulationModel(DistributedModelSimulationEnvironment):
    nodes: List[ErrorNode]
    special_delay_generator: DelayGenerator

    full_state_statistics: List[Statistics]
    full_state_statistics_active_time_step: Statistics

    timestamp_statistics: List[Statistics]
    timestamp_statistics_active_time_step: Statistics

    token_statistics: List[Statistics]
    token_statistics_active_time_step: Statistics

    def __init__(self, parameters: SimulationParameters, fault_space: Set[int] = None):

        super().__init__(parameters)
        self.fault_space = fault_space
        self.number_of_variables = sum(parameters.number_of_variables_per_node)
        self.special_delay_generator = DelayGenerator(parameters.seed)

        self.full_state_statistics = []
        self.full_state_statistics_active_time_step = Statistics()
        self.full_state_statistics_active_time_step.time = self.time

        self.timestamp_statistics = []
        self.timestamp_statistics_active_time_step = Statistics()
        self.timestamp_statistics_active_time_step.time = self.time
        estimated_delay = 1 # set an estimate used for all unknown delays
        for node in self.nodes:
            for i in range(len(self.nodes)):
                for j in range(len(self.nodes)):
                    if i == j:
                        node.delays.append(Delay(i,j,1)) # constant delay of 1 from a node to itself
                    else:
                        node.delays.append(Delay(i,j,estimated_delay)) # could also be an estimate for the delay instead of 0

        self.token_statistics = []
        self.token_statistics_active_time_step = Statistics()
        self.token_statistics_active_time_step.time = self.time

    def create_node_hook(self, *args, **kwargs):
        return ErrorNode(*args, **kwargs)

    def send_variable_hook(self, time: int, sending_node: ErrorNode, receiving_node: ErrorNode, variable, value) -> ErrorModelEvent:
        event=ErrorModelEvent()

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
        
        # Timestamp Data #######################################################
        event.timestamp = time
        if sending_node != receiving_node:
            # Bandwidth need for the variable
            self.timestamp_statistics_active_time_step.band_width_used += 1+(self.number_of_variables-1).bit_length()
            # Bandwidth for the timestamp
            self.timestamp_statistics_active_time_step.band_width_used += 32

        # Token Data ###########################################################
        if sending_node != receiving_node:
            # Bandwidth for sending the variable
            self.token_statistics_active_time_step.band_width_used += 1+(self.number_of_variables-1).bit_length()

        return event

    def handle_event(self, time: int, event: ErrorModelEvent):
        """
        Will be called for every event.
        """
        super().handle_event(time, event)

        node = self.nodes[event.to_node]

        # Special Event Handling ###############################################
        if event.changed_variable == None:
            if not event.token == None:
                if event.token.node_id == node.id:
                    for token_fault in node.token_faults:
                        if event.token == token_fault.token:
                            token_fault.received_from.append(event.from_node)
                else:
                    token_event = ErrorModelEvent()
                    token_event.changed_variable = None
                    token_event.from_node = node.id
                    token_event.to_node = event.token.node_id
                    token_event.token = event.token
                    self.token_statistics_active_time_step.band_width_used += 32 * 2
                    delay = self.get_delay(token_event.from_node, token_event.to_node, self.special_delay_generator)
                    self.create_event(time+delay, token_event)
            elif event.timestamp == None:
                for delay in node.delays:
                    if delay.from_node == event.changed_delay.from_node and delay.to_node == event.changed_delay.to_node:
                        delay.value = event.changed_delay.value
            return

        # Full State Transfer Handling #########################################
        node.full_state_dict[event.changed_variable[0]] = event.full_state

        # Timestamp Handling ###################################################
        new_delay = time - event.timestamp
        for delay in node.delays:
            if delay.from_node == event.from_node and delay.to_node == event.to_node:
                if not delay.value == new_delay:
                    delay.value = new_delay # here also max or average could be used
                    for _node in self.nodes:
                        if not node == _node:
                            timestamp_event = ErrorModelEvent()
                            timestamp_event.changed_variable = None
                            timestamp_event.changed_delay = delay
                            timestamp_event.from_node = node.id
                            timestamp_event.to_node = _node.id
                            timestamp_event.timestamp = None
                            timestamp_event_delay = self.get_delay(node.id, _node.id, self.special_delay_generator)
                            self.create_event(time + timestamp_event_delay, timestamp_event)
                            # 2*bits for representing the from_node and to_node and 32 bits for delay
                            self.timestamp_statistics_active_time_step.band_width_used += 32+(len(self.nodes)-1).bit_length()*2
            

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

        # Timestamp Error Check
        for i in range(len(error_node.timestamp_faults)):
            error_node.timestamp_faults[i] -= 1

        if error_node.local_state.int_representation in self.fault_space:
            wait_time = int(numpy.average([delay.value for delay in error_node.delays])) * len(self.nodes)
            error_node.timestamp_faults.append(wait_time)
            for timestamp_fault in list(error_node.timestamp_faults):
                if timestamp_fault == 0:
                    self.timestamp_statistics_active_time_step.error_detected = True
                    error_node.timestamp_faults.remove(timestamp_fault)
        else:
            error_node.timestamp_faults.clear()

        # Token Error Check
        if error_node.local_state.int_representation in self.fault_space:
            token = Token(error_node.id, error_node.next_token_id)
            error_node.next_token_id += 1
            for node in self.nodes:
                if not node == error_node:
                    token_event = ErrorModelEvent()
                    token_event.changed_variable = None
                    token_event.from_node = error_node.id
                    token_event.to_node = node.id
                    token_event.token = token
                    self.token_statistics_active_time_step.band_width_used += 32 * 2
                    delay = self.get_delay(token_event.from_node, token_event.to_node, self.special_delay_generator)
                    self.create_event(time+delay, token_event)
            error_node.token_faults.append(TokenFault(token, [error_node.id]))
            for token_fault in list(error_node.token_faults):
                if len(token_fault.received_from) == len(self.nodes):
                    self.token_statistics_active_time_step.error_detected = True
                    error_node.token_faults.remove(token_fault)
        else:
            error_node.token_faults.clear()

        super().handle_time_step(time, events_occured)

        self.full_state_statistics_active_time_step.time = time
        # variables + full states
        self.full_state_statistics_active_time_step.memory_used = self.number_of_variables * (len(error_node.full_state) + 1)
        self.full_state_statistics.append(self.full_state_statistics_active_time_step)
        self.full_state_statistics_active_time_step = Statistics()

        self.timestamp_statistics_active_time_step.time = time
        # variables + delays for all connections + timestamp faults
        self.timestamp_statistics_active_time_step.memory_used = self.number_of_variables 
        self.timestamp_statistics_active_time_step.memory_used += 32 * len(self.nodes) * len(self.nodes)
        self.timestamp_statistics_active_time_step.memory_used += 32 * len(error_node.timestamp_faults)
        self.timestamp_statistics.append(self.timestamp_statistics_active_time_step)
        self.timestamp_statistics_active_time_step = Statistics()

        self.token_statistics_active_time_step.time = time
        # variables + token faults (id, received_from list)
        self.token_statistics_active_time_step.memory_used = self.number_of_variables
        self.token_statistics_active_time_step.memory_used += (32 + len(self.nodes)) * len(error_node.token_faults)
        self.token_statistics.append(self.token_statistics_active_time_step)
        self.token_statistics_active_time_step = Statistics()