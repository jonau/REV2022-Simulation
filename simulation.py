from dataclasses import dataclass
import itertools
import random

from pandas.core import base
from database import commit, insert_table, write_statistics, database_name
from delay_functions import DelayTypes
from error_model import ErrorSimulationModel
from evaluation import evaluate_statistics
from simulation_objects import Node, RuleFunction, State
from base_model import BaseModelSimulationEnvironment
from distributed_model import DistributedModelSimulationEnvironment, SimulationParameters, Statistics
from typing import Dict, Set

from base_model import SimulationParameters

# make simulation deterministic
random.seed(0)

max_number_of_nodes = 10
max_number_of_variables_per_node = 1
max_number_of_dependencies_per_node = max_number_of_variables_per_node*max_number_of_nodes
stop_time = 50000

@dataclass
class SimulationStatistics:
    full_state_statistics: Statistics
    timestamp_statistics: Statistics
    token_statistics: Statistics

# TODO: generate parameters for distributed experiments
def get_random_parameters(max_number_of_nodes: int, max_number_of_variables_per_node: int,
                          max_number_of_dependencies_per_node: int) -> SimulationParameters:
    """
    Randomly generates a simulation parameters object
    """
    number_of_nodes = random.randint(2, max_number_of_nodes)
    number_of_variables_per_node = [random.randint(1, max_number_of_variables_per_node) for i in range(number_of_nodes)]
    number_of_variables = sum(number_of_variables_per_node)
    number_of_dependencies_per_node = [random.randint(1, min(max_number_of_dependencies_per_node, number_of_variables))
                                       for i in range(number_of_nodes)]
    dependencies_per_node = [
        list(itertools.repeat(True, number_of_dependencies_per_node[i])) +
        list(itertools.repeat(False, number_of_variables - number_of_dependencies_per_node[i]))
        for i in range(number_of_nodes)]
    for dep in dependencies_per_node:
        random.shuffle(dep)
    rule_function_per_node = [
        RuleFunction(
            [random.randint(0, pow(2, number_of_dependencies_per_node[i]+1)-1)
             for j in range(number_of_variables_per_node[i])],
            dependencies_per_node[i]) for i in range(number_of_nodes)]
    initial_state = 0

    delay_type = DelayTypes.random(random)

    return SimulationParameters(number_of_nodes, number_of_variables_per_node, rule_function_per_node, initial_state, 20, 100, delay_type, random.randint(0, 1000000))

debug = False
def print_debug(string):
    if debug:
        print(string)

simulation_count = 1000
s_index = 0
print(f"Simulations finished: {s_index} of {simulation_count}", end="\r")
while s_index < simulation_count:
    parameters = get_random_parameters(max_number_of_nodes, max_number_of_variables_per_node,
                                    max_number_of_dependencies_per_node)

    print_debug(f"Number of Nodes:                    {parameters.number_of_nodes}")
    print_debug(f"Number of Variables:                {parameters.number_of_variables_per_node}")

    env = BaseModelSimulationEnvironment(parameters)
    env.run(stop_time)
    # we use the local states of the nodes since the global state cannot 
    # be accessed by a node during execution for fault classification
    base_model_states=set()
    for node in env.nodes:
        for reached_state in node.reached_states:
            base_model_states.add(reached_state)
    print_debug(f"Number of Base Model States:        {len(base_model_states)}")

    env = DistributedModelSimulationEnvironment(parameters)
    env.run(stop_time)
    distributed_model_states=set()
    for node in env.nodes:
        for reached_state in node.reached_states:
            distributed_model_states.add(reached_state)
    print_debug(f"Number of Distributed Model States: {len(distributed_model_states)}")

    shared_states = base_model_states.intersection(distributed_model_states)
    control_fault_space = set(random.choices(list(shared_states), k=max(1,len(shared_states)//2)))
    print_debug(f"Control Faults:                     {control_fault_space}\n")

    # BEGIN OF SIMULATION CHECKING ####################################################################
    print_debug("Checking Simulation for Problems\n")

    simulation_faulty = False
    if len(base_model_states.intersection(distributed_model_states)) == 0:
        print_debug("No base model state in distributed model states\n")
        simulation_faulty = True

    not_detectable: Dict[int, bool] = dict() # a control fault is not detectable by token / hard to detect by timestamp if it is resolved in under min_delay*2 timesteps
    for control_fault in control_fault_space:
        error_node = env.nodes[0]
        not_detectable[control_fault] = True
        if control_fault in error_node.reached_states:
            for i in range(len(error_node.state_history)):
                if error_node.state_history[i][0] == control_fault:
                    j = i
                    while error_node.state_history[j][0] in control_fault_space and j+1 < len(error_node.state_history):
                        j += 1
                    if error_node.state_history[j][1] - error_node.state_history[i][1] > 2 * parameters.min_delay: # maybe >=
                        not_detectable[control_fault] = False
                        break

    invalid: Set[int] = set()
    for control_fault in control_fault_space:
        if env.nodes[0].state_history[0][0] == control_fault:
            invalid.add(control_fault)
        if not_detectable[control_fault]:
            invalid.add(control_fault)
    
    if len(control_fault_space) == len(invalid):
        print_debug("No valid Control Faults\n")
        simulation_faulty = True
    else:
        print_debug(f"Valid Control Faults:               {control_fault_space.difference(invalid)}")

    if simulation_faulty:
        print_debug(f"Simulation discarded: Error with States or Control Faults\n")
        continue

    print_debug("\nContinuing with Error Simulation\n")
    # END OF SIMULATION CHECKING ######################################################################

    simulation_reference=insert_table('simulation', cls=parameters)

    infrastructure_states = list(distributed_model_states.difference(base_model_states))
    infrastructure_fault_space = set(random.choices(infrastructure_states, k=len(infrastructure_states)//2))

    c_env = ErrorSimulationModel(parameters, fault_space=control_fault_space)
    c_env.run(stop_time)
    control_fault_model_states=set()
    for node in env.nodes:
        for reached_state in node.reached_states:
            control_fault_model_states.add(reached_state)
    if not control_fault_model_states == distributed_model_states:
        print_debug(f"Simulation {s_index} discarded: Control Fault Model States and Distributed Model States don't match\n")
        continue

    i_env = ErrorSimulationModel(parameters, fault_space=infrastructure_fault_space)
    i_env.run(stop_time)
    infrastructure_fault_model_states=set()
    for node in env.nodes:
        for reached_state in node.reached_states:
            infrastructure_fault_model_states.add(reached_state)
    if not infrastructure_fault_model_states == distributed_model_states:
        print_debug(f"Simulation {s_index} discarded: Infrastructure Fault Model States and Distributed Model States don't match\n")
        continue

    write_statistics('control_', c_env, simulation_reference)
    write_statistics('infrastructure_', i_env, simulation_reference)

    print(f"Simulations finished: {s_index+1} of {simulation_count}", end="\r")

    commit()
    s_index += 1

print(f"Simulations finished: {simulation_count} of {simulation_count}")

evaluate_statistics(database_name)