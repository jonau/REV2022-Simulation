from typing import List, Set, Tuple
from dataclasses import dataclass
from simulation_objects import Node, RuleFunction, State
from simulation_env import SimulationEnvironment
from delay_functions import DelayTypes

@dataclass
class SimulationParameters:
    number_of_nodes: int
    number_of_variables_per_node: List[int]
    rule_functions_per_node: List[RuleFunction]
    initial_state: int
    min_delay: int
    max_delay: int
    delay_type: DelayTypes
    seed: int

class Event:
    from_node: int
    to_node: int
    changed_variable: Tuple[int, bool]

class BaseModelSimulationEnvironment(SimulationEnvironment):
    parameters: SimulationParameters
    nodes: List[Node]
    max_steady_space_time: int # only to speed up the simulation: stop simulation when the state space is large enough does not increase for that amount of time steps
    state_space: Set[int] # all states that have been reached during the simulation
    no_state_space_changes: int

    def __init__(self, parameters: SimulationParameters):
        super().__init__()

        self.parameters = parameters

        node_variable_offset = [0]
        for i in range(parameters.number_of_nodes-1):
            node_variable_offset.append(node_variable_offset[i]+parameters.number_of_variables_per_node[i])
        self.nodes = [self.create_node_hook(i, parameters.rule_functions_per_node[i], State(parameters.initial_state), node_variable_offset[i]) for i in range(parameters.number_of_nodes)]

        self.state_space={parameters.initial_state}
        self.no_state_space_changes=0

        if hasattr(parameters, "max_steady_space_time"):
            self.max_steady_space_time = parameters.max_steady_space_time
        else:
            self.max_steady_space_time = 100

    def create_node_hook(self, *args, **kwargs):
        return Node(*args, **kwargs)

    def get_global_state(self):
        state=[]
        parameter_count=0
        for i in range(len(self.nodes)):
            for j in range(self.parameters.number_of_variables_per_node[i]):
                state.append(self.nodes[i].local_state[parameter_count])
                parameter_count+=1
        return State(state)

    def get_delay(self, sending_node, receiving_node):
        """
        Returns the delay between two nodes
        """
        return 1

    def send_variable_hook(self, time, sending_node, receiving_node, variable, value):
        """
        Will be called before sending a variable. The return value will be available in the event as data
        """
        return Event()

    def send_variable(self, time, sending_node, variable, value):
        for node in self.nodes:
            delay = self.get_delay(sending_node, node)
            event=self.send_variable_hook(time, sending_node, node, variable, value)
            event.from_node = sending_node.id
            event.to_node = node.id
            event.changed_variable = (variable, value)
            self.create_event(time+delay, event)

    def handle_event(self, time: int, event: Event):
        """
        Will be called for every event.
        """
        if event.changed_variable != None:
            self.nodes[event.to_node].local_state[event.changed_variable[0]] = event.changed_variable[1]
            self.nodes[event.to_node].state_history.append((self.nodes[event.to_node].local_state.int_representation, time))
            self.nodes[event.to_node].reached_states.add(self.nodes[event.to_node].local_state.int_representation)

    def handle_time_step(self, time: int, events_occured: bool):
        """
        Will be called at the end of each time step.
        if events_occured is True, then there occured events in this time step
        """
        if events_occured:
            for node in self.nodes:
                controlled_variables = node.evaluate_rule()

                # check if variables changed
                for i in range(controlled_variables.variables):
                    if node.local_state[i+node.global_state_offset] != controlled_variables[i]:
                        self.send_variable(time, node, i+node.global_state_offset,
                                           controlled_variables[i])
        
        if events_occured:
            state=self.get_global_state().int_representation
            if state in self.state_space:
                self.no_state_space_changes+=1
                if self.no_state_space_changes>=self.max_steady_space_time:
                    self.stop()
            else:
                self.no_state_space_changes=0
                self.state_space.add(state)
