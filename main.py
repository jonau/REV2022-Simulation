from multiprocessing import Manager, Process, Value, cpu_count
import random
import signal
from typing import List
import time

from simulation import start_simulating

random.seed(0)

class SimulationProcess:
    process: Process
    seed: int
    good_simulation_count: Value
    bad_simulation_count: Value
    faulty_simulation_count: Value
    timed_out_simulation_count: Value


stopped = False
def sigint_handler(signum, frame):
        global stopped 
        stopped = True

if __name__ == "__main__":
    signal.signal(signal.SIGBREAK, sigint_handler)
    signal.signal(signal.SIGINT, sigint_handler)
    simulation_process_count = input(f"\nEnter the desired amount of Processes (max {cpu_count()}): ")
    if not simulation_process_count.isnumeric():
        print(simulation_process_count, "is not a number")
        exit(-1)
    else:
        print(f"\nStarting {min(cpu_count(), int(simulation_process_count))} Simulation Processes\n")
        simulation_process_count = min(cpu_count(), int(simulation_process_count))

    simulation_processes: List[SimulationProcess] = []
    process_manager = Manager()
    database_lock = process_manager.Lock()

    for i in range(simulation_process_count):
        simulation_process = SimulationProcess()
        simulation_process.seed = random.randint(0,1000000)
        simulation_process.good_simulation_count = process_manager.Value('I', 0)
        simulation_process.bad_simulation_count = process_manager.Value('I', 0)
        simulation_process.faulty_simulation_count = process_manager.Value('I', 0)
        simulation_process.timed_out_simulation_count = process_manager.Value('I', 0)
        args = (database_lock, simulation_process.seed, simulation_process.good_simulation_count, simulation_process.bad_simulation_count, 
                simulation_process.faulty_simulation_count, simulation_process.timed_out_simulation_count)
        simulation_process.process = Process(target=start_simulating, args=args)
        simulation_processes.append(simulation_process)
        simulation_process.process.start()

    while not stopped:
        good = sum([p.good_simulation_count.value for p in simulation_processes])
        bad = sum([p.bad_simulation_count.value for p in simulation_processes])
        faulty = sum([p.faulty_simulation_count.value for p in simulation_processes])
        timed_out = sum([p.timed_out_simulation_count.value for p in simulation_processes])
        print(f"\rSimulations: {good} good, {bad} bad, {faulty} faulty and {timed_out} timed out", end="")
        time.sleep(10)
        if stopped:
            print("\n\nStopping Simulation Processes\n")

    database_lock.acquire()
    for i in range(simulation_process_count):
        simulation_processes[i].process.terminate()
        simulation_processes[i].process.join()
        print(f"Simulation Process {i} was terminated")
    database_lock.release()

    good = sum([p.good_simulation_count.value for p in simulation_processes])
    bad = sum([p.bad_simulation_count.value for p in simulation_processes])
    faulty = sum([p.faulty_simulation_count.value for p in simulation_processes])
    timed_out = sum([p.timed_out_simulation_count.value for p in simulation_processes])
    print(f"\nTotal Simulations: {good} good, {bad} bad, {faulty} faulty and {timed_out} timed out")