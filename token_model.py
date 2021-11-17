from typing import List, Set
from simulation_objects import Node
from distributed_model import DistributedModelSimulationEnvironment, Statistics
from base_model import Event, SimulationParameters
from dataclasses import dataclass

@dataclass
class Token:
    node_id: int
    token_id: int

@dataclass
class TokenFault:
    token: Token
    received_from: List[int]

class TokenErrorNode(Node):
    next_token_id: int
    token_faults: List[TokenFault]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_faults = []
        self.tokens = []
        self.next_token_id = 0

class TokenErrorModelEvent(Event):
    token: Token

class TokenErrorModelSimulationEnvironment(DistributedModelSimulationEnvironment):
    nodes: List[TokenErrorNode]
    token_statistics: List[Statistics]
    token_statistics_active_time_step: Statistics

    def __init__(self, parameters: SimulationParameters, fault_space: Set[int] = None):

        super().__init__(parameters)
        self.fault_space = fault_space
        self.number_of_variables = sum(parameters.number_of_variables_per_node)

        self.token_statistics = []
        self.token_statistics_active_time_step = Statistics()
        self.token_statistics_active_time_step.time = self.time

    def create_node_hook(self, *args, **kwargs):
        return TokenErrorNode(*args, **kwargs)

    def send_variable_hook(self, time, sending_node, receiving_node, variable, value):
        event = TokenErrorModelEvent()

        if sending_node != receiving_node:
            # Bandwidth for sending the new delay
            self.token_statistics_active_time_step.band_width_used += 1+(self.number_of_variables-1).bit_length()

        return event

    def handle_event(self, time: int, event: TokenErrorModelEvent):
        """
        Will be called for every event.
        """
        super().handle_event(time, event)

        node = self.nodes[event.to_node]
            
        if hasattr(event, "token"):
            if event.token.node_id == node.id:
                for token_fault in node.token_faults:
                    if event.token == token_fault.token:
                        token_fault.received_from.append(event.from_node)
            else:
                token_event = TokenErrorModelEvent()
                token_event.changed_variable = None
                token_event.from_node = node.id
                token_event.to_node = event.token.node_id
                token_event.token = event.token
                self.token_statistics_active_time_step.band_width_used += 32 * 2
                delay = self.get_delay(token_event.from_node, token_event.to_node)
                self.create_event(time+delay, token_event)


    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """

        error_node = self.nodes[0]
        
        if error_node.local_state.int_representation in self.fault_space:
            token = Token(error_node.id, error_node.next_token_id)
            error_node.next_token_id += 1
            for node in self.nodes:
                if not node == error_node:
                    token_event = TokenErrorModelEvent()
                    token_event.changed_variable = None
                    token_event.from_node = error_node.id
                    token_event.to_node = node.id
                    token_event.token = token
                    self.token_statistics_active_time_step.band_width_used += 32 * 2
                    delay = self.get_delay(token_event.from_node, token_event.to_node)
                    self.create_event(time+delay, token_event)
            error_node.token_faults.append(TokenFault(token, [error_node.id]))
            for token_fault in list(error_node.token_faults):
                if len(token_fault.received_from) == len(self.nodes):
                    self.token_statistics_active_time_step.error_detected = True
                    error_node.token_faults.remove(token_fault)
        else:
            error_node.token_faults.clear()

        super().handle_time_step(time, events_occured)

        self.token_statistics_active_time_step.time = time
        self.token_statistics.append(self.token_statistics_active_time_step)
        self.token_statistics_active_time_step = Statistics()