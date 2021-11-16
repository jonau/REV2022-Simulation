import itertools
import random
from database import commit, insert_table, write_statistics
from measure_time import clear_measurements, print_measurements
from simulation_objects import RuleFunction, State
from base_model import BaseModelSimulationEnvironment
from distributed_model import DistributedModelSimulationEnvironment
from error_model import ErrorModelSimulationEnvironment

from base_model import SimulationParameters

# make simulation deterministic
random.seed(0)

max_number_of_nodes = 10
max_number_of_variables_per_node = 1
max_number_of_dependencies_per_node = max_number_of_variables_per_node*max_number_of_nodes
stop_time = 50000


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
    initial_state = State(0)

    return SimulationParameters(number_of_nodes, number_of_variables_per_node, rule_function_per_node, initial_state)

for i in range(1000):
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

    # The Method should detect an error: false negative testing
    env = ErrorModelSimulationEnvironment(parameters, fault_space=control_fault_space)
    env.run(stop_time)
    write_statistics('control_', env, simulation_reference)

    # The Method should not detect any error: false positive testing
    env = ErrorModelSimulationEnvironment(parameters, fault_space=infrastructure_fault_space)
    env.run(stop_time)
    write_statistics('infrastructure_', env, simulation_reference)

    commit()

print_measurements()
clear_measurements()