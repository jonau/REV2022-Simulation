from typing import Dict, List, Set, Tuple
from simulation_objects import Node, State
from distributed_model import DistributedModelSimulationEnvironment
from base_model import Event, SimulationParameters
from measure_time import define_measurement, measurent_begin, measurent_end
import itertools
from dataclasses import dataclass

# checking runtime
define_measurement(0, "Full State Transfer Send Hook")
define_measurement(1, "Timestamp Send Hook")
define_measurement(2, "Token Send Hook")
define_measurement(3, "Full State Transfer Event Hook")
define_measurement(4, "Timestamp Event Hook")
define_measurement(5, "Token Event Hook")
define_measurement(6, "Full State Transfer Error Check")
define_measurement(7, "Timestamp Error Check")
define_measurement(8, "Token Error Check")

@dataclass
class Token:
    node_id: int
    token_id: int

@dataclass
class TokenFault:
    token: Token
    sent_to: List[int]
    received_from: List[int]

class ErrorNode(Node):
    full_state: Set[State]
    full_state_dict: Dict[int, State]

    # Timestamps
    timestamp_faults: List[int]
    # Parameter -> Timestamp
    timestamp_dict: Dict[int, int]                      
    # List of Delays to between all Nodes
    delays: List[int]                                   
    # Delay_id -> New_Delay and List, which contains all Node_ids to which this change has been sent
    changed_delays: Dict[int, Tuple[int, List[int]]]     
                                                         
    # Token
    next_token_id: int
    # Token_Fault = Token_id -> (List of Node_ids to which the token was sent, List of Node_ids of which an answer was received)
    token_faults: List[TokenFault]
    tokens: List[Token]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_state_dict = dict()
        self.full_state = set()
        self.timestamp_dict = dict()
        self.delays = []
        self.changed_delays = dict()
        self.timestamp_faults = []
        self.token_faults = []
        self.tokens = []
        self.next_token_id = 0

class ErrorModelEvent(Event):
    full_state: Set[State]
    timestamp: int
    changed_delays: List[Tuple[int, int]]
    tokens: List[Token]

class Statistics:
    time: int = 0
    error_detected: bool = False
    band_width_used: int = 0


class ErrorModelSimulationEnvironment(DistributedModelSimulationEnvironment):
    nodes: List[ErrorNode]
    full_state_statistics: List[Statistics]
    full_state_statistics_active_time_step: Statistics

    # Timestamps
    timestamp_statistics: List[Statistics]
    timestamp_statistics_active_time_step: Statistics

    # Token
    token_statistics: List[Statistics]
    token_statistics_active_time_step: Statistics

    def __init__(self, parameters: SimulationParameters, fault_space: Set[int] = None):

        super().__init__(parameters)
        self.fault_space = fault_space
        self.number_of_variables = sum(parameters.number_of_variables_per_node)

        self.full_state_errors = set()
        self.full_state_statistics = []
        self.full_state_statistics_active_time_step = Statistics()
        self.full_state_statistics_active_time_step.time = self.time

        # Timestamps
        self.timestamp_statistics = []
        self.timestamp_statistics_active_time_step = Statistics()
        self.timestamp_statistics_active_time_step.time = self.time
        for node in self.nodes:
            node.timestamp_dict[node.id] = 0
            node.delays = [0]*(len(self.nodes)*len(self.nodes))
            for i in range(len(self.nodes)):
                for j in range(len(self.nodes)):
                    if i == j:
                        node.delays[i*len(self.nodes) + j] = 1 # constant delay of 1 from a node to itself
                    else:
                        node.delays[i*len(self.nodes) + j] = 0 # could also be an estimate for the delay instead of 0

        # Token
        self.token_statistics = []
        self.token_statistics_active_time_step = Statistics()
        self.token_statistics_active_time_step.time = self.time

    def create_node_hook(self, *args, **kwargs):
        return ErrorNode(*args, **kwargs)

    def send_variable_hook(self, time: int, sending_node: ErrorNode, receiving_node: ErrorNode, variable, value) -> ErrorModelEvent:
        event=ErrorModelEvent()

        measurent_begin(0)
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
        measurent_end(0)

        measurent_begin(1)
        # Timestamps Data ######################################################
        event.timestamp = time
        event.changed_delays = []
        to_remove = []
        if sending_node != receiving_node:
            # Bandwidth need for the variable
            self.timestamp_statistics_active_time_step.band_width_used += 1+(self.number_of_variables-1).bit_length()
            # Bandwidth for the timestamp
            self.timestamp_statistics_active_time_step.band_width_used += 32
            for key in sending_node.changed_delays.keys():
                if not receiving_node.id in sending_node.changed_delays[key][1]:
                    sending_node.changed_delays[key][1].append(receiving_node.id)
                    self.timestamp_statistics_active_time_step.band_width_used += 32
                    event.changed_delays.append((key, sending_node.changed_delays[key][0]))
                    if len(sending_node.changed_delays[key][1]) == len(self.nodes):
                        to_remove.append(key)
        for key in to_remove:
            sending_node.changed_delays.pop(key, None)
        measurent_end(1)

        measurent_begin(2)
        # Token Data ###########################################################
        event.tokens = []

        if sending_node != receiving_node:
            self.token_statistics_active_time_step.band_width_used += 1+(self.number_of_variables-1).bit_length()
            for token_fault in sending_node.token_faults:
                if not receiving_node.id in token_fault.sent_to:
                    event.tokens.append(token_fault.token)
                    # Bandwidth for token: 2 * 32 bit assuming 2 32bit ids
                    self.token_statistics_active_time_step.band_width_used += 32 * 2
                    token_fault.sent_to.append(receiving_node.id)
        
        for token in list(sending_node.tokens):
            if token.node_id == receiving_node.id:
                event.tokens.append(token)
                self.token_statistics_active_time_step.band_width_used += 32 * 2
                sending_node.tokens.remove(token)
        measurent_end(2)
        
        return event

    def handle_event(self, time: int, event: ErrorModelEvent):
        """
        Will be called for every event.
        """
        super().handle_event(time, event)

        node = self.nodes[event.to_node]

        measurent_begin(3)
        # Full State Transfer Handling #########################################
        node.full_state_dict[event.changed_variable[0]] = event.full_state
        measurent_end(3)

        measurent_begin(4)
        # Timestamps Handling ##################################################
        delay = time - event.timestamp
        node.timestamp_dict[event.changed_variable[0]] = event.timestamp
        index = event.from_node * len(self.nodes) + event.to_node
        if node.delays[index] != delay:
            node.delays[index] = delay   # here also max or avg could be used instead of accepting newest value
            node.changed_delays[index] = ((delay, [node.id]))
        for changed_delay in event.changed_delays:
            node.delays[changed_delay[0]] = changed_delay[1]
        measurent_end(4)

        measurent_begin(5)
        # Token Handling #######################################################
        for token in event.tokens:
            if token.node_id == node.id:
                for token_fault in node.token_faults:
                    if token == token_fault.token:
                        token_fault.received_from.append(event.from_node)
            else:
                node.tokens.append(token)
        measurent_end(5)


    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """

        error_node = self.nodes[0]
        measurent_begin(6)
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
        measurent_end(6)

        measurent_begin(7)
        # Timestamps
        for i in range(len(error_node.timestamp_faults)):
            error_node.timestamp_faults[i] -= 1

        # Timestamp Error Check
        if error_node.local_state.int_representation in self.fault_space:
            wait_time = sum(error_node.delays) // len(self.nodes) #TODO: check if this calculation is model conform and correct
            error_node.timestamp_faults.append(wait_time)
            for timestamp_fault in list(error_node.timestamp_faults):
                if timestamp_fault == 0:
                    self.timestamp_statistics_active_time_step.error_detected = True
                    error_node.timestamp_faults.remove(timestamp_fault)
        else:
            error_node.timestamp_faults.clear()
        measurent_end(7)

        measurent_begin(8)
        # Token Error Check
        if error_node.local_state.int_representation in self.fault_space:
            token = Token(error_node.id, error_node.next_token_id)
            error_node.next_token_id += 1
            error_node.token_faults.append(TokenFault(token, [error_node.id], [error_node.id]))
            for token_fault in list(error_node.token_faults):
                if len(token_fault.received_from) >= 0.5 * len(self.nodes):
                    self.token_statistics_active_time_step.error_detected = True
                    error_node.token_faults.remove(token_fault)
        else:
            error_node.token_faults.clear()
        measurent_end(8)

        super().handle_time_step(time, events_occured)

        self.full_state_statistics_active_time_step.time = time
        self.full_state_statistics.append(self.full_state_statistics_active_time_step)
        self.full_state_statistics_active_time_step = Statistics()

        # Timestamps
        self.timestamp_statistics_active_time_step.time = time
        self.timestamp_statistics.append(self.timestamp_statistics_active_time_step)
        self.timestamp_statistics_active_time_step = Statistics()

        # Token
        self.token_statistics_active_time_step.time = time
        self.token_statistics.append(self.token_statistics_active_time_step)
        self.token_statistics_active_time_step = Statistics()