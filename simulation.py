from dataclasses import dataclass
import itertools
import random
from database import commit, insert_table, write_statistics, database_name
from delay_functions import DelayTypes
from evaluation import evaluate_statistics
from simulation_objects import RuleFunction, State
from base_model import BaseModelSimulationEnvironment
from distributed_model import DistributedModelSimulationEnvironment, DistributedSimulationParameters, Statistics
from full_state_transfer_model import FullStateTransferSimulationEnvironment
from timestamp_model import Delay, TimestampErrorModelSimulationEnvironment
from token_model import TokenErrorModelSimulationEnvironment

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
                          max_number_of_dependencies_per_node: int) -> DistributedSimulationParameters:
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
    initial_state = State(0)

    delay_type = DelayTypes.random(random)

    return DistributedSimulationParameters(number_of_nodes, number_of_variables_per_node, rule_function_per_node, initial_state, 20, 100, delay_type, random.randint(0, 1000000))

for i in range(5000):
    print("Simulation {}".format(i))

    parameters = get_random_parameters(max_number_of_nodes, max_number_of_variables_per_node,
                                    max_number_of_dependencies_per_node)

    print(f"Number of Nodes:        {parameters.number_of_nodes}")
    print(f"Number of Variables:    {parameters.number_of_variables_per_node}\n")

    simulation_reference=insert_table('simulation', cls=parameters)

    env = BaseModelSimulationEnvironment(parameters)
    env.run(stop_time)
    base_model_states=env.state_space

    env = DistributedModelSimulationEnvironment(parameters)
    env.run(stop_time)
    distributed_model_states=env.state_space

    control_fault_space = set(random.choices(list(base_model_states), k=1))
    infrastructure_states = list(distributed_model_states.difference(base_model_states))
    infrastructure_fault_space = set(random.choices(infrastructure_states, k=len(infrastructure_states)//2))

    statistics = SimulationStatistics(full_state_statistics=None, timestamp_statistics=None, token_statistics=None)

    # The Method should detect an error: false negative testing
    env = FullStateTransferSimulationEnvironment(parameters, fault_space=control_fault_space)
    env.run(stop_time)
    statistics.full_state_statistics = env.full_state_statistics
    env = TimestampErrorModelSimulationEnvironment(parameters, fault_space=infrastructure_fault_space)
    env.run(stop_time)
    statistics.timestamp_statistics = env.timestamp_statistics
    env = TokenErrorModelSimulationEnvironment(parameters, fault_space=control_fault_space)
    env.run(stop_time)
    statistics.token_statistics = env.token_statistics
    write_statistics('control_', statistics, simulation_reference)

    # The Method should not detect any error: false positive testing
    env = FullStateTransferSimulationEnvironment(parameters, fault_space=infrastructure_fault_space)
    env.run(stop_time)
    statistics.full_state_statistics = env.full_state_statistics
    env = TimestampErrorModelSimulationEnvironment(parameters, fault_space=infrastructure_fault_space)
    env.run(stop_time)
    statistics.timestamp_statistics = env.timestamp_statistics
    env = TokenErrorModelSimulationEnvironment(parameters, fault_space=infrastructure_fault_space)
    env.run(stop_time)
    statistics.token_statistics = env.token_statistics
    write_statistics('infrastructure_', statistics, simulation_reference)

    commit()