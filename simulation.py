from dataclasses import dataclass
import itertools
import random
from database import commit, insert_table, write_statistics
from delay_functions import DelayTypes
from error_model import ErrorSimulationModel, Statistics
from simulation_objects import RuleFunction
from base_model import BaseModelSimulationEnvironment, ParameterCategories
from distributed_model import DistributedModelSimulationEnvironment, SimulationParameters
from typing import Dict, Set

from base_model import SimulationParameters

max_number_of_nodes = 10
max_number_of_variables_per_node = 5
max_number_of_dependencies_per_node = 5 
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

    return SimulationParameters(number_of_nodes, number_of_variables_per_node, rule_function_per_node, initial_state, 
                                20, 100, delay_type, random.randint(0, 1000000), ParameterCategories.UNKNOWN)

def check_for_timeout(env, parameters, lock) -> bool:
    if env.timed_out:
        parameters.category = ParameterCategories.TIMEOUT
        lock.acquire()
        insert_table('simulation', cls=parameters)
        commit()
        lock.release()
        return True
    else:
        return False

def start_simulating(database_lock, seed, good_simulations, bad_simulations, faulty_simulations, timed_out_simulations):

    # make simulation deterministic by starting with the given seed
    random.seed(seed)

    while True:

        parameters = get_random_parameters(max_number_of_nodes, max_number_of_variables_per_node,
                                        max_number_of_dependencies_per_node)

        # set new random seed to make the simulation run depend only on the generated parameters
        random.seed(parameters.seed)

        # we use the local states of the nodes since the global state cannot 
        # be accessed by a node during execution for fault classification
        env = BaseModelSimulationEnvironment(parameters)
        env.run(stop_time)
        if check_for_timeout(env, parameters, database_lock):
            timed_out_simulations.value += 1
            continue
        base_model_states=set()
        for reached_state in env.nodes[0].reached_states:
            base_model_states.add(reached_state)

        env = DistributedModelSimulationEnvironment(parameters)
        env.run(stop_time)
        if check_for_timeout(env, parameters, database_lock):
            timed_out_simulations.value += 1
            continue
        distributed_model_states=set()
        for reached_state in env.nodes[0].reached_states:
            distributed_model_states.add(reached_state)

        # BEGIN OF SIMULATION CHECKING ####################################################################
        shared_states = base_model_states.intersection(distributed_model_states)
            
        control_fault_space = set(random.choices(list(shared_states), k=max(1,len(shared_states)//2)))

        # a control fault is not detectable by token / hard to detect by timestamp if it is resolved in under min_delay*2 timesteps
        not_detectable: Dict[int, bool] = dict() 
        for control_fault in control_fault_space:
            error_node = env.nodes[0]
            not_detectable[control_fault] = True
            if control_fault in error_node.reached_states:
                for i in range(len(error_node.state_history)):
                    if error_node.state_history[i][0] == control_fault:
                        j = i
                        while error_node.state_history[j][0] in control_fault_space and j+1 < len(error_node.state_history):
                            j += 1
                        if error_node.state_history[j][1] - error_node.state_history[i][1] > 2 * parameters.min_delay:
                            not_detectable[control_fault] = False
                            break

        invalid: Set[int] = set()
        for control_fault in control_fault_space:
            if not_detectable[control_fault]:
                invalid.add(control_fault)
        
        if len(control_fault_space) == len(invalid):
            parameters.category = ParameterCategories.BAD
        # END OF SIMULATION CHECKING ######################################################################

        if parameters.category == ParameterCategories.UNKNOWN:
            parameters.category = ParameterCategories.GOOD

        infrastructure_states = list(distributed_model_states.difference(base_model_states))
        infrastructure_fault_space = set(random.choices(infrastructure_states, k=len(infrastructure_states)//2))

        c_env = ErrorSimulationModel(parameters, fault_space=control_fault_space)
        c_env.run(stop_time)
        if check_for_timeout(c_env, parameters, database_lock):
            timed_out_simulations.value += 1
            continue
        control_fault_model_states=set()
        for reached_state in c_env.nodes[0].reached_states:
            control_fault_model_states.add(reached_state)
        if not control_fault_model_states == distributed_model_states:
            print(control_fault_model_states.difference(distributed_model_states))
            print(distributed_model_states.difference(control_fault_model_states))
            parameters.category = ParameterCategories.FAULTY

        i_env = ErrorSimulationModel(parameters, fault_space=infrastructure_fault_space)
        i_env.run(stop_time)
        if check_for_timeout(i_env, parameters, database_lock):
            timed_out_simulations.value += 1
            continue
        infrastructure_fault_model_states=set()
        for reached_state in i_env.nodes[0].reached_states:
            infrastructure_fault_model_states.add(reached_state)
        if not infrastructure_fault_model_states == distributed_model_states:
            print(infrastructure_fault_model_states.difference(distributed_model_states))
            print(distributed_model_states.difference(infrastructure_fault_model_states))
            parameters.category = ParameterCategories.FAULTY

        if parameters.category == ParameterCategories.GOOD:
            good_simulations.value += 1
        elif parameters.category == ParameterCategories.BAD:
            bad_simulations.value += 1
        elif parameters.category == ParameterCategories.FAULTY:
            faulty_simulations.value += 1
        
        database_lock.acquire()
        simulation_reference=insert_table('simulation', cls=parameters) 
        write_statistics('control_', c_env, simulation_reference)
        write_statistics('infrastructure_', i_env, simulation_reference)
        commit()
        database_lock.release()